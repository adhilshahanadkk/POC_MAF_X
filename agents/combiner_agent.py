from datetime import datetime
from utils.llm_retry import invoke_with_fallback
from database.mysql_connection import MYSQL_DB_NAME, MYSQL_TABLE_NAMES
from database.mssql_connection import MSSQL_DB_NAME, MSSQL_TABLE_NAMES


def combiner_node(state):
    results = state.get("multi_results", [])
    query = state.get("query")
    should_visualize = state.get("should_visualize", False)

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    combiner_context = "\n\n".join(results)
    print("combiner_context", combiner_context)

    prompt = f"""
ROLE: You are a Senior Data Synthesis Expert. Your task is to take raw outputs from multiple specialized agents and craft a polished, executive-level response for the end-user.

OBJECTIVE: Transform technical data points into a coherent, human-readable narrative. Do not explain the "process" (e.g., "Agent A did this"); instead, present the "findings" (e.g., "Based on the records, we found...").

INPUT DATA:
- Original User Query: {query}
- Agent Findings: {combiner_context}

RESPONSE GUIDELINES:
1. Tone: Professional, helpful, and grounded in data.
2. Structure:
   - Use a paragraph for the direct answer.
   - Use bullet points if there are multiple facts, dates, or comparisons to highlight.
   - Use ONLY double asterisks **value** for bolding key values.
   - Try to include a Markdown table to compare commodity metrics if multiple items are discussed.
3. Citations: Integrate citations naturally into the text (e.g., "According to the {MYSQL_DB_NAME}..." or "Market records from {MSSQL_DB_NAME} indicate...").
4. Handling Empty/Missing Data:
   - If an agent returned "no data found" or empty results, clearly state that no data was available.
   - Do NOT invent or hallucinate data that wasn't found.
   - Provide a helpful suggestion (e.g., "Try a broader date range").
5. No Placeholders: NEVER write "N/A", "Not Available", or "Unknown" in the table. If data is missing, omit that column entirely.
6. DATA INTEGRITY: If the data contains User ID or User Details (Name, Email, Country, Subscription), you MUST include these details in the first paragraph. Do not ignore user data.

CRITICAL FORMATTING RULES:
- Do NOT use ### or ## or # headers anywhere in your response.
- Do NOT add a "Sources" section.
- End your response with EXACTLY these three lines (no headers, no extra labels):

Database: <list the actual database names that were queried, e.g., {MYSQL_DB_NAME}, {MSSQL_DB_NAME}>
Table: <list the actual table names, e.g., {MYSQL_TABLE_NAMES}, {MSSQL_TABLE_NAMES}>
Timestamp: {timestamp}
"""

    answer = invoke_with_fallback(
        prompt,
        temperature=0.0
    )

    if hasattr(answer, "content"):
        answer = answer.content

    print("Combiner answer:", answer)

    return {
        "final_output": answer,
        "should_visualize": should_visualize
    }