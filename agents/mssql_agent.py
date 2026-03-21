import re
from datetime import datetime
from langchain_core.prompts import PromptTemplate
from database.mssql_connection import db
from agents.llm_provider import get_llm

# ---------- LLM ----------
llm = get_llm(temperature=0.0)

# ---------- SCHEMA ----------
# Fetching schema once to provide context to the LLM
schema_info = db.get_table_info()

# ---------- MSSQL PROMPT ----------
# Refined to be extremely clear about the raw output
MSSQL_PROMPT = PromptTemplate(
    input_variables=["input", "schema"],
    template="""
You are an expert Microsoft SQL Server (T-SQL) engineer.

GOAL:
Generate a T-SQL query that answers the User Question based on the provided Schema.

STRICT RULES:
1. Use ONLY T-SQL syntax.
2. Use square brackets [] for all column and table names (e.g., [Date], [CommodityPrices]).
3. Output ONLY the raw SQL string. 
4. DO NOT use markdown code blocks (no ```sql or ```).
5. DO NOT use backticks (`).
6. If using UNION or UNION ALL, you MUST place ORDER BY only once at the very end of the entire query.
7. ORDER BY cannot appear before UNION in T-SQL.
8. If the task requires a comparison or percentage change, write a single efficient query.
9. The dataset is historical (starting from 2006). When a user asks for 'the last 6 months' or 'current price,' do NOT use GETDATE(). Instead, always find the MAX(Date) in the table and treat that as 'Today'."

Schema:
{schema}

User Question/Task:
{input}

SQL Query:"""
)

def clean_sql_output(raw_query):
    """
    Hard-strips any potential markdown or backticks if the LLM 
    hallucinates them despite instructions.
    """
    # Remove markdown code blocks
    query = re.sub(r"```(?:sql|mssql)?", "", raw_query, flags=re.IGNORECASE)
    # Remove trailing backticks
    query = query.replace("```", "").replace("`", "")
    return query.strip()

def mssql_agent_node(state):
    # 1. Get state variables
    original_query = state.get("query")
    task = state.get("task")
    context_data = state.get("context_data", [])
    # Read from state: set by the planner in multi-agent flows.
    # Defaults to False for direct single-agent MSSQL queries (avoids unnecessary charts).
    should_visualize = state.get("should_visualize", False)

    # 2. Build the focused input for SQL generation
    execution_input = f"TASK: {task}\nPREVIOUS FINDINGS: {context_data}\nORIGINAL QUESTION: {original_query}"

    print(f"--- MSSQL Agent: Generating SQL ---")
    
    # 3. Step One: Generate SQL String
    formatted_prompt = MSSQL_PROMPT.format(schema=schema_info, input=execution_input)
    raw_response = llm.invoke(formatted_prompt)
    
    # Extract content safely
    raw_sql = raw_response.content if hasattr(raw_response, "content") else raw_response
    
    # 4. Step Two: Clean the SQL String
    cleaned_sql = clean_sql_output(raw_sql)
    
    print("\n==============================")
    print("GENERATED SQL QUERY:")
    print(cleaned_sql)
    print("==============================\n")

    # 5. Step Three: Execute against Database
    try:
        # Using the underlying db.run() to execute the raw string
        db_results = db.run(cleaned_sql,fetch="all")
        print(f"DEBUG db_results: {db_results}")
    except Exception as e:
        print(f"!!! MSSQL Execution Error: {e}")
        db_results = f"Error: The generated SQL was invalid. {str(e)}"

    # 6. Step Four: Format the Final Narrative Answer
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    citation_prompt = f"""
    You are a commodity market expert.
    Based on the following SQL data result, provide a professional narrative answer.
    
    Original User Question: {original_query}
    Raw Data Result: {db_results}

    Requirements:
    - You MUST include ALL rows from the SQL result — do not skip or summarize any commodity.
    - For EVERY commodity, explicitly state its Average, Minimum, and Maximum price.
    - Format each commodity clearly like: "COPPER: Avg $9,036 | Min $7,746 | Max $10,231"
    - Mention that the data comes from the CommodityDB.
    - Do NOT omit any commodity from the result.

    Return EXACT format:
    Answer: <your full explanation with ALL commodities and their min/max/avg values>
    Database: CommodityDB
    Table: CommodityPrices
    Timestamp: {timestamp}
    """

    llm_response = llm.invoke(citation_prompt)
    final_text = llm_response.content if hasattr(llm_response, "content") else llm_response

    return {"final_output": final_text.strip(), "should_visualize": should_visualize}

