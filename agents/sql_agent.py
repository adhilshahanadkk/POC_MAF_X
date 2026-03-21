import re
from datetime import datetime
from langchain_core.prompts import PromptTemplate
from database.mysql_connection import db
from agents.llm_provider import get_llm

# ---------- LLM ----------
llm = get_llm(temperature=0.0)

# ---------- SCHEMA ----------
schema_info = db.get_table_info()

# ---------- MYSQL PROMPT ----------
MYSQL_PROMPT = PromptTemplate(
    input_variables=["input", "schema"],
    template="""
You are a senior MySQL database engineer.

GOAL:
Create a syntactically correct MySQL query to solve the task based on the schema provided.

STRICT RULES:
1. Use ONLY MySQL syntax.
2. Return ONLY the raw SQL query string.
3. DO NOT use markdown code blocks (no ```sql or ```).
4. DO NOT use backticks (`) for wrapping the code.
5. Use correct table names from the schema.
6. Return only the SQL; no explanations or conversational text.

Tables available:
users(id, first_name, last_name, email, gender, country, signup_date)
subscriptions(subscription_id, user_id, commodity, start_date, end_date, plan_type)

Schema:
{schema}

User Task:
{input}

SQL Query:"""
)

def clean_sql_output(raw_query):
    """Removes markdown backticks and 'sql' identifiers from the query."""
    # Remove triple backticks and 'sql' or 'mysql' labels
    query = re.sub(r"```(?:sql|mysql)?", "", raw_query, flags=re.IGNORECASE)
    # Remove single or trailing backticks
    query = query.replace("```", "").replace("`", "")
    return query.strip()

def sql_agent_node(state):
    # 1. Identify context
    original_query = state.get("query")
    planned_task = state.get("task") 
    context_data = state.get("context_data", [])

    # 2. Construct the focused input
    if planned_task:
        execution_input = f"TASK: {planned_task}\nPREVIOUS FINDINGS: {context_data}\nORIGINAL USER QUERY: {original_query}"
    else:
        execution_input = original_query

    print(f"--- MySQL Agent: Generating SQL ---")
    
    # 3. Step One: Generate SQL string
    formatted_prompt = MYSQL_PROMPT.format(schema=schema_info, input=execution_input)
    raw_response = llm.invoke(formatted_prompt)
    raw_sql = raw_response.content if hasattr(raw_response, "content") else raw_response

    # 4. Step Two: Clean SQL string
    cleaned_sql = clean_sql_output(raw_sql)
    print(f"--- Executing Cleaned MySQL ---\n{cleaned_sql}\n---")

    # 5. Step Three: Execute against MySQL Database
    try:
        # Direct execution bypasses the problematic SQLDatabaseChain
        db_results = db.run(cleaned_sql)
    except Exception as e:
        print(f"!!! MySQL Execution Error: {e}")
        db_results = f"Error: Data retrieval failed due to SQL syntax. {str(e)}"

    # 6. Step Four: Final Citation/Formatting
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    citation_prompt = f"""
    You are a MySQL database agent.
    Based on the SQL result below, provide a clear, factual summary.
    
    Original Question: {original_query}
    Data Found: {db_results}

    Requirements:
    - List specific values like names, dates, or IDs clearly.
    - If no data was found, state that clearly.

    Return EXACT format:
    Answer: <clear summary>
    Database: user_db
    Table: user, subscription
    Timestamp: {timestamp}
    """

    llm_response = llm.invoke(citation_prompt)
    final_output = llm_response.content if hasattr(llm_response, "content") else llm_response

    return {"final_output": final_output.strip(), "should_visualize": True}





