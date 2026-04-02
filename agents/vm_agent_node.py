import re
import requests
from datetime import datetime
from agents.llm_provider import get_llm
from config.settings import VM_BASE_URL

llm = get_llm(temperature=0.2)

VM_SEARCH_URL = f"{VM_BASE_URL}/search"

# Regex to strip unresolved CMS/WordPress shortcodes like [tg_reports ...], [pt_view ...]
_SHORTCODE_RE = re.compile(r'\[\w+[^\]]*\]')

# Map VM API keys (uppercase) to our internal keys (lowercase)
_KEY_MAP = {
    'ID': 'id', 'Title': 'title', 'Commodity': 'commodity',
    'Distance': 'distance', 'Content': 'document', 'image_map': 'image_map',
    # Also keep lowercase keys if the API changes back
    'id': 'id', 'title': 'title', 'commodity': 'commodity',
    'distance': 'distance', 'document': 'document',
}


def _normalize_match(m: dict) -> dict:
    """Normalize VM API keys to consistent lowercase internal keys."""
    return {_KEY_MAP.get(k, k): v for k, v in m.items()}


def _strip_shortcodes(text: str) -> str:
    """Remove unresolved CMS shortcodes and collapse extra whitespace."""
    cleaned = _SHORTCODE_RE.sub('', text)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)   # collapse blank lines
    return cleaned.strip()


def _deduplicate(matches: list) -> list:
    """Remove duplicate matches based on document content."""
    seen = set()
    unique = []
    for m in matches:
        doc = m.get('document', '').strip()
        if doc not in seen:
            seen.add(doc)
            unique.append(m)
    return unique


def _deduplicate_by_title(matches: list) -> list:
    """Remove duplicate matches based on title (better for metadata-heavy results)."""
    seen = set()
    unique = []
    for m in matches:
        title = m.get('title', '').strip()
        if title not in seen:
            seen.add(title)
            unique.append(m)
    return unique


def _search_vm(query: str, timeout: int = 30, top_k: int = 5) -> list:
    """Call the VM search API and return cleaned, deduplicated matches."""
    try:
        resp = requests.get(VM_SEARCH_URL, params={"query": query}, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        matches = [_normalize_match(m) for m in data.get("matches", [])]

        # Clean shortcodes from each document
        for m in matches:
            raw_doc = m.get('document', '')
            m['document'] = _strip_shortcodes(raw_doc)
            # If doc is empty after cleaning, use title as fallback
            if not m['document'].strip():
                m['document'] = m.get('title', '')

        # Deduplicate by title (since doc bodies are often identical)
        matches = _deduplicate_by_title(matches)
        matches = matches[:top_k]

        return matches
    except requests.ConnectionError:
        print(f"[vm_agent] ❌ Cannot connect to VM at {VM_BASE_URL}")
        return []
    except Exception as e:
        print(f"[vm_agent] ❌ Search error: {e}")
        return []


def vm_agent_node(state):
    """
    LangGraph node that:
      1. Searches the permanent VM vector store
      2. Feeds retrieved documents to the LLM
      3. Returns a grounded answer with sources
    """
    query = state.get("query", "")
    task = state.get("task", "")          # Used in multi-agent mode

    search_query = task if task else query
    print(f"\n[vm_agent] 🔍 Search query: {search_query}")

    matches = _search_vm(search_query)
    print(f"[vm_agent] 📦 Matches after cleaning/dedup: {len(matches)}")
    for i, m in enumerate(matches):
        print(f"  [{i+1}] ID={m.get('id')} | Title={m.get('title')} | Distance={m.get('distance')}")
        print(f"       Doc preview: {m.get('document', '')[:150]}...")

    if not matches:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        return {
            "final_output": (
                "I could not retrieve any results from the permanent knowledge base. "
                "The VM service may be unavailable or no relevant documents were found.\n\n"
                f"Database: VM (Permanent Knowledge Base)\n"
                f"Timestamp: {timestamp}"
            ),
            "last_agent": "vm_agent"
        }

    # ── Build context from VM matches ─────────────────────────────────────
    context_blocks = []
    for m in matches:
        block = (
            f"- Title: {m.get('title', 'N/A')}\n"
            f"  ID: {m.get('id', 'N/A')}\n"
            f"  Commodity: {m.get('commodity', 'N/A')}\n"
            f"  Relevance Score: {round(1 / (1 + m.get('distance', 0)), 4)}\n"
            f"  Content: {m.get('document', '')}"
        )
        context_blocks.append(block)

    context = "\n\n".join(context_blocks)

    prompt = f"""
You are a commodity market research assistant with access to Transgraph's permanent knowledge base.

User Query:
{search_query}

Retrieved Documents:
{context}

Instructions:

1. Understand the user query carefully:
   - Identify key entities (commodities, topics, conditions)
   - If the query includes words like "both", "and", "together", treat it as an AND condition
   - Handle synonyms (e.g., corn = maize, soybean = soya)

2. Filter the documents:
   - Only keep documents that satisfy ALL conditions in the query
   - Ignore partially matching or irrelevant documents

3. Analyze the filtered results:

   CASE A: If detailed content is available
   - Provide a clear, concise answer using facts from the documents
   - Summarize key insights

   CASE B: If only titles / metadata are available
   - List the relevant documents
   - Explain what topics they cover based on titles
   - Mention number of matching documents
   - Suggest user can explore reports for deeper insights

4. Output format:

Answer:
- Provide a clear natural language response

Matching Documents:
- ID | Title | Commodity | Reason (why it matches query)

Notes:
- Be precise and factual
- Do not hallucinate missing data
- Do not include irrelevant documents
- Always prefer correctness over completeness
"""

    print(f"\n[vm_agent] 📝 Prompt sent to LLM ({len(prompt)} chars)")
    print(f"[vm_agent] 📄 Context preview:\n{context[:500]}...\n")

    response = llm.invoke(prompt)

    # Extract text from response
    if hasattr(response, "content"):
        answer = response.content
    elif isinstance(response, str):
        answer = response
    else:
        answer = str(response)

    answer = answer.strip() if answer else "No answer generated."

    # Build sources list
    sources = []
    for m in matches:
        sources.append(
            f"{m.get('title', 'N/A')} | "
            f"ID: {m.get('id', 'N/A')} | "
            f"Distance: {round(m.get('distance', 0), 4)}"
        )
    sources_text = "\n".join(sources)

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    formatted_output = (
        f"{answer}\n\n"
        f"---\n"
        f"📚 **Sources (VM Permanent KB):**\n{sources_text}\n\n"
        f"🗄️ Database: VM (Permanent Knowledge Base)\n"
        f"🕐 Timestamp: {timestamp}"
    )

    print(f"\n[vm_agent] ✅ Final output:\n{formatted_output}\n")

    return {
        "final_output": formatted_output,
        "last_agent": "vm_agent"
    }
