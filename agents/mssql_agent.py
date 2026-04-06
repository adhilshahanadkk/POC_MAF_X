import re
from datetime import datetime
from langchain_core.prompts import PromptTemplate
from database.mssql_connection import db, MSSQL_DB_NAME, MSSQL_TABLE_NAMES
from agents.llm_provider import get_llm

# ---------- LLM ----------
llm = get_llm(temperature=0.0)

# ---------- SCHEMA ----------
# Fetching schema once to provide context to the LLM
schema_info = db.get_table_info()

# ---------- Helper: extract table names from a SQL query ----------
def extract_tables_from_sql(sql, known_tables):
    """Parse the SQL to find which known tables were actually referenced."""
    sql_upper = sql.upper()
    used = [t for t in known_tables if t.upper() in sql_upper]
    return ", ".join(used) if used else MSSQL_TABLE_NAMES

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
9. The dataset is historical (starting from 2006). When a user asks for 'the last 6 months' or 'current price,' do NOT use GETDATE(). Instead, always find the MAX(Date) in the table and treat that as 'Today'.
10. NEVER use LIMIT. T-SQL does not support LIMIT. Use SELECT TOP N instead (e.g., SELECT TOP 1 ... ORDER BY [Date] DESC)."

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

    # 5. Extract which tables were actually used in the query
    known_tables = [t.strip() for t in MSSQL_TABLE_NAMES.split(",")]
    used_tables = extract_tables_from_sql(cleaned_sql, known_tables)

    # 6. Step Three: Execute against Database
    try:
        # Using the underlying db.run() to execute the raw string
        db_results = db.run(cleaned_sql, fetch="all")
        print(f"DEBUG db_results: {db_results}")
    except Exception as e:
        print(f"!!! MSSQL Execution Error: {e}")
        db_results = f"Error: The generated SQL was invalid. {str(e)}"

    # 7. Step Four: Format the Final Narrative Answer
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # Handle empty results — ask LLM to explain why and suggest alternatives
    if not db_results or db_results == "[]" or db_results == []:
        empty_prompt = f"""
        You are a helpful data assistant. A database query was executed but returned NO results.
        
        User's original question: {original_query}
        SQL that was tried (for your context only — do NOT show this to the user): {cleaned_sql}
        
        Requirements:
        - Explain in simple, friendly language why no data was found.
        - Analyze the SQL logic and suggest what might be wrong (e.g., the filter might be too specific, a value might not exist in the database, a column might not contain the expected data).
        - Suggest 1-2 alternative ways the user could rephrase their question to get results.
        - NEVER show SQL queries, code, or technical syntax to the user.
        - Keep it concise — 2-3 sentences max plus suggestions.
        
        CRITICAL: Do NOT use ### or ## or # headers in your response.

        Return EXACT format (plain text, no headers):
        Answer: <your friendly explanation and suggestions>
        Database: {MSSQL_DB_NAME}
        Table: {used_tables}
        Timestamp: {timestamp}
        """
        llm_response = llm.invoke(empty_prompt)
        final_text = llm_response.content if hasattr(llm_response, "content") else llm_response
        return {"final_output": final_text.strip(), "db_results": db_results, "sql_query": cleaned_sql, "should_visualize": False}
    
    # Build a context-aware description so the LLM knows what the data represents
    task_context = f"Task/Step: {task}\n" if task else ""
    
    citation_prompt = f"""
    You are a commodity market data specialist.
    Based on the following SQL data result, provide a professional narrative answer.
    
    Original User Question: {original_query}
    {task_context}Raw Data Result: {db_results}

    Requirements:
    - Interpret the data correctly based on the task context above.
    - If the query was fetching IDs or lookups, report them as IDs — NOT as prices.
    - If the query was fetching prices/dates, present them clearly with proper formatting.
    - Include ALL rows from the result — do not skip any.
    - For price data, format like: "COMMODITY: Avg $X | Min $Y | Max $Z" where applicable.
    - Mention that the data comes from the {MSSQL_DB_NAME} database.
    - NEVER include SQL queries, code, or technical database syntax in your response. The user should only see human-readable results.

    CRITICAL: Do NOT use ### or ## or # headers in your response. Do NOT add a "Sources" section.

    Return EXACT format (plain text, no headers):
    Answer: <your explanation based on what the data actually represents>
    Database: {MSSQL_DB_NAME}
    Table: {used_tables}
    Timestamp: {timestamp}
    """

    llm_response = llm.invoke(citation_prompt)
    final_text = llm_response.content if hasattr(llm_response, "content") else llm_response

    return {"final_output": final_text.strip(), "db_results": db_results, "sql_query": cleaned_sql, "should_visualize": should_visualize}
