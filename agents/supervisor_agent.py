from utils.llm_retry import invoke_with_fallback


def supervisor_node(state):
    query = state.get("query")

    # ADD MEMORY READ HERE
    history = state.get("chat_history", [])
    last_agent = state.get("last_agent", "None")
    has_uploaded_docs = state.get("has_uploaded_docs", False)
    uploaded_doc_names = state.get("uploaded_doc_names", [])

    uploaded_docs_status = "yes" if has_uploaded_docs else "no"
    uploaded_docs_list = ", ".join(uploaded_doc_names) if uploaded_doc_names else "None"

    prompt = f"""
You are the High-Level Intent Classifier and Routing Engine for a Multi-Agent ecosystem. Your goal is to analyze the user's query and map it to the single most appropriate execution agent or the orchestration layer.

User Query: {query}

### AVAILABLE AGENTS & DOMAINS:

1. **mysql_agent**: 
   - Use for: User profiles, account details, and subscription status.
   - Schema context: `user_db` (Tables: `user`, `subscription`).

2. **mssql_agent**:
   - Use for: Querying raw commodity pricing data, historical price records, and numerical data lookups.
   - Schema context: `CommodityPrices` (Tables: `commodities`).

3. **rag_agent**:
   - Use for: User-uploaded documents only (PDFs, DOCX, CSV, XLSX files).
   - Policies, manuals, documentation that the user has uploaded in this session.

4. **vm_agent**:
   - Use for: Commodity market research, technical outlooks, price forecasts, and market analysis articles.
   - This is the PERMANENT knowledge base containing Transgraph research reports, commodity trend analysis, and price outlook summaries.
   - Covers: HDPE, PP, PET, SMP, Milk, Polymer, and other commodity research.

5. **report_agent**:
   - Use for: Creating summaries, generating downloadable files, or formatting previous answers into a structured report.

6. **multi_agent**:
   - Use for: Cross-functional queries requiring data from TWO OR MORE sources (e.g., "Compare user subscription levels with commodity price trends").

Uploaded documents available: {uploaded_docs_status} 
Uploaded document names: {uploaded_docs_list}

### ROUTING LOGIC & HIERARCHY (Apply in order — first match wins)
- Rule 0 (HIGHEST PRIORITY): If uploaded documents are available (Uploaded documents available = yes), and the user's query is asking about data, content, or information that could plausibly come from those uploaded files, route to rag_agent.
- Rule 1: If the query mentions "report," "export," "summary," or "document" (and is asking to generate/download one, not asking about document content), route to report_agent.
- Rule 2: If the query requires a join or comparison between data from TWO OR MORE sources, route to multi_agent.
- Rule 3: If the query asks about commodity market analysis, technical outlook, price forecast, research articles, trends commentary, or expert analysis — route to vm_agent.
- Rule 4: If the query asks for raw commodity price data, specific price numbers, or historical price records from the database — route to mssql_agent.
- Rule 5: If the query is about a specific user or their subscription — route to mysql_agent.
- Rule 6: If the query asks "How do I..." or "What is the policy for..." — route to rag_agent.
- Rule 7: For general commodity knowledge questions that don't need raw SQL data — route to vm_agent.
- Rule 8: Route to multi_agent ONLY when the query genuinely requires data from two or more different sources. Do NOT route to multi_agent for single-source queries.

### CONSTRAINT
Return ONLY the string name of the agent. Do not include explanations, punctuation, or markdown formatting.

### USER QUERY
{query}

Return ONLY:
mysql_agent OR mssql_agent OR rag_agent OR vm_agent OR report_agent OR multi_agent
"""

    decision = invoke_with_fallback(
        prompt,
        temperature=0.3
    )

    if hasattr(decision, "content"):
        decision = decision.content

    # Handle case where decision might be a list or other non-string type
    if isinstance(decision, list):
        decision = decision[0] if decision else "rag_agent"

        if hasattr(decision, "content"):
            decision = decision.content

    # Ensure decision is a string
    if not isinstance(decision, str):
        decision = str(decision)

    decision = decision.strip().lower()

    print("Supervisor decision:", decision)

    return {"route": decision}