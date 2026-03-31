from config.settings import GEMINI_MODEL
from agents.llm_provider import get_llm

llm = get_llm(temperature=0.3)


def supervisor_node(state):
    query = state.get("query")

    # ADD MEMORY READ HERE
    history = state.get("chat_history", [])
    last_agent = state.get("last_agent", "None")
    has_uploaded_docs = state.get("has_uploaded_docs", False) #new
    uploaded_doc_names = state.get("uploaded_doc_names", []) #new

    uploaded_docs_status = "yes" if has_uploaded_docs else "no" #new
    uploaded_docs_list = ", ".join(uploaded_doc_names) if uploaded_doc_names else "None" #new

    prompt = f"""
You are the High-Level Intent Classifier and Routing Engine for a Multi-Agent ecosystem. Your goal is to analyze the user's and map it to the single most appropriate execution agent or the orchestration layer.

user  Query : {query}

### AVAILABLE AGENTS & DOMAINS :

1. **mysql_agent**: 
   - Use for: User profiles, account details, and subscription status.
   - Schema context: `user_db` (Tables: `user`, `subscription`).

2. **mssql_agent**:
   - Use for: Financial trends, commodity pricing, and historical price fluctuations.
   - Schema context: `CommodityPrices` (Tables: `commodities`).

3. **rag_agent**:
   - - Document knowledge base
    - PDFs, DOCX, CSV, and Excel (XLSX) files
    - Policies, manuals, documentation

4. **report_agent**:
   - Use for: Creating summaries, generating downloadable files, or formatting previous answers into a structured report.

5. **multi_agent**:
   - Use for: Cross-functional queries requiring data from TWO OR MORE sources (e.g., "Compare user subscription levels with commodity price trends").

report_agent:
- Generates structured reports from system answers
- Use when user asks for report, document, summary file


Uploaded documents available: {uploaded_docs_status} 
Uploaded document names: {uploaded_docs_list}

### ROUTING LOGIC & HIERARCHY
- **Rule 1**: If the query mentions "report," "export," "summary," or "document," route to `report_agent`.
- **Rule 2**: If the query requires a join or comparison between SQL data and RAG documents, or between MySQL and MSSQL, route to `multi_agent`.
- **Rule 3**: If the query is a direct question about prices, route to `mssql_agent`.
- **Rule 4**: If the query is a direct question about a specific user or their subscription, route to `mysql_agent`.
- **Rule 5**: If the query asks "How do I..." or "What is the policy for...", route to `rag_agent`.
- **Rule 6**: If the request involves comparative analysis, volatility assessments, or multi-step mathematical aggregations (e.g., spreads, percentage changes, or trend detection), you must route to the Multi-Agent Planner. Use the planner even if the data resides in a single database to ensure the logic is decomposed into a structured analytical sequence.


### CONSTRAINT
Return ONLY the string name of the agent. Do not include explanations, punctuation, or markdown formatting.


### USER QUERY
{query}




Return ONLY:
mysql_agent OR mssql_agent OR rag_agent OR report_agent OR multi_agent

"""


    decision = llm.invoke(prompt)

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
    