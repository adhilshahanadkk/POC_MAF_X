import re
import ast
from datetime import datetime
from langchain_core.prompts import PromptTemplate
from database.mysql_connection import db
from agents.llm_provider import get_llm
import pandas as pd
from pandasai_helper import process_with_pandasai

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
    query = re.sub(r"```(?:sql|mysql)?", "", raw_query, flags=re.IGNORECASE)
    query = query.replace("```", "").replace("`", "")
    return query.strip()

def parse_db_results(raw):
    """Parse db.run() output — handles both list and string representations."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = ast.literal_eval(raw)
            if isinstance(parsed, list):
                return parsed
        except Exception as e:
            print(f"DEBUG parse failed: {e}")
    return []

def extract_col_names_from_sql(sql):
    """Extract column names from SELECT clause."""
    select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
    col_names = None
    if select_match:
        select_clause = select_match.group(1)
        aliases = re.findall(r'AS\s+(\w+)\s*(?:,|$)', select_clause, re.IGNORECASE)
        brackets = re.findall(r'\[(\w+)\](?!\s*AS)', select_clause)
        backticks = re.findall(r'`(\w+)`', select_clause)
        plain = re.findall(r'(?:^|,)\s*(\w+)\s*(?:,|$)', select_clause)
        col_names = aliases if aliases else brackets if brackets else backticks if backticks else plain if plain else None
    return col_names

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

    # 3. Generate SQL
    formatted_prompt = MYSQL_PROMPT.format(schema=schema_info, input=execution_input)
    raw_response = llm.invoke(formatted_prompt)
    raw_sql = raw_response.content if hasattr(raw_response, "content") else raw_response
    cleaned_sql = clean_sql_output(raw_sql)
    print(f"--- Executing Cleaned MySQL ---\n{cleaned_sql}\n---")

    # 4. Execute SQL
    try:
        raw_results = db.run(cleaned_sql)
        print(f"DEBUG db_results raw type: {type(raw_results)}, value: {raw_results}")
        db_results = parse_db_results(raw_results)
        print(f"DEBUG db_results parsed type: {type(db_results)}, len: {len(db_results)}")
    except Exception as e:
        print(f"!!! MySQL Execution Error: {e}")
        db_results = []

    # 5. Timestamp
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # 6. Handle empty results
    if not db_results:
        empty_prompt = f"""
        You are a helpful data assistant. A database query was executed but returned NO results.
        
        User's original question: {original_query}
        SQL that was tried (for your context only — do NOT show this to the user): {cleaned_sql}
        
        Requirements:
        - Explain in simple, friendly language why no data was found.
        - Suggest 1-2 alternative ways the user could rephrase their question.
        - NEVER show SQL queries, code, or technical syntax to the user.
        - Keep it concise — 2-3 sentences max plus suggestions.
        
        Return EXACT format:
        Answer: <your friendly explanation and suggestions>
        Database: user_db
        Table: users, subscriptions
        Timestamp: {timestamp}
        """
        llm_response = llm.invoke(empty_prompt)
        final_text = llm_response.content if hasattr(llm_response, "content") else llm_response
        return {
            "final_output": final_text.strip(),
            "should_visualize": False
        }

    # 7. Build narrative answer
    citation_prompt = f"""
    You are a MySQL database agent.
    Based on the SQL result below, provide a clear, factual summary.
    
    Original Question: {original_query}
    Data Found: {db_results}

    Requirements:
    - List specific values like names, dates, or IDs clearly.
    - If no data was found, state that clearly.
    - NEVER include SQL queries, code, or technical database syntax in your response.

    Return EXACT format:
    Answer: <clear summary>
    Database: user_db
    Table: users, subscriptions
    Timestamp: {timestamp}
    """
    llm_response = llm.invoke(citation_prompt)
    final_output = llm_response.content if hasattr(llm_response, "content") else llm_response

    # 8. PandasAI enhancement
    print(f"✅ REACHED PANDASAI BLOCK — db_results type: {type(db_results)}, len: {len(db_results)}")

    if isinstance(db_results, list) and db_results:
        try:
            col_names = extract_col_names_from_sql(cleaned_sql)

            if isinstance(db_results[0], tuple):
                num_cols = len(db_results[0])
                if col_names and len(col_names) >= num_cols:
                    cols = col_names[:num_cols]
                else:
                    cols = [f"column_{i+1}" for i in range(num_cols)]
                df = pd.DataFrame(db_results, columns=cols)
            else:
                df = pd.DataFrame(db_results)

            print(f"✅ DataFrame created: shape={df.shape}, columns={df.columns.tolist()}")
            pandasai_response = process_with_pandasai(df, original_query)
            enhanced_answer = f"""{final_output}

📊 Enhanced Analysis:
{pandasai_response}"""
        except Exception as e:
            print(f"❌ PandasAI error: {e}")
            enhanced_answer = final_output
    else:
        enhanced_answer = final_output

    return {
        "final_output": enhanced_answer.strip(),
        "db_results": db_results,
        "sql_query": cleaned_sql,
        "should_visualize": True
    }