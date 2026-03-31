from datetime import datetime
from agents.llm_provider import get_llm

llm = get_llm(temperature=0.0)


def combiner_node(state):
    results=state.get("multi_results", [])
    query=state.get("query")
    should_visualize = state.get("should_visualize", False)  # Inherit from planner

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    combiner_context="\n\n".join(results)
    print("combiner_context",combiner_context)

    prompt = f"""
### ROLE
You are a Senior Data Synthesis Expert. Your task is to take raw outputs from multiple specialized agents and craft a polished, executive-level response for the end-user.

### OBJECTIVE
Transform technical data points into a coherent, human-readable narrative. Do not explain the "process" (e.g., "Agent A did this"); instead, present the "findings" (e.g., "Based on the records, we found...").

### INPUT DATA
- **Original User Query**: {query}
- **Agent Findings**: {combiner_context}

### RESPONSE GUIDELINES
1. **Tone**: Professional, helpful, and grounded in data.
2. **Structure**: 
   - Use a **Paragraph** for the direct answer.
   - Use **Bullet Points** if there are multiple facts, dates, or comparisons to highlight.
   - **Clean Bolding**: Use ONLY double asterisks `**value**` for bolding.
   - **Summary Table**: try to include a Markdown table to compare commodity metrics if multiple items are discussed.- it will give user more insight.
   
3. **Citations**: Integrate citations naturally into the text (e.g., "According to the user_db..." or "Market records from CommodityDB indicate...").
4. **Handling Failures**: If any part of the data is missing or an agent failed, acknowledge it gracefully without sounding technical.
5. **No Placeholders**: NEVER write "N/A", "Not Available", or "Unknown" in the table.   ← ADD THIS
   If data is missing for a field, omit that column entirely from the table.
   Only include columns where you have actual values for ALL rows.

### OUTPUT FORMAT (STRICT)

Answer: <Provide a structured, human-like response. Use **bolding** for all key values like prices, dates, or volatility ranges for readability.

### DATA INTEGRITY RULE:
If the data contains a User ID or User Details (Name, Email, Country, Subscription), you MUST explicitly include these details in the first paragraph of your answer. Do not ignore user data to focus only on market prices. The final report depends on having both.>


Database/Document: <List all unique sources mentioned in the findings, e.g., user_db, CommodityDB>
Table: <List specific tables, e.g., user, subscription, commodities>
Timestamp: {timestamp}
"""

    answer = llm.invoke(prompt)

    if hasattr(answer, "content"):
        answer = answer.content
    print("Combiner answer:", answer)
    return {"final_output": answer, "should_visualize": should_visualize}

