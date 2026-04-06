import re
import ast
from datetime import datetime
from langchain_core.prompts import PromptTemplate
from database.mssql_connection import db, MSSQL_DB_NAME, MSSQL_TABLE_NAMES
from agents.llm_provider import get_llm
import pandas as pd
from pandasai_helper import process_with_pandasai

# ---------- LLM ----------
llm = get_llm(temperature=0.0)

# ---------- SCHEMA ----------
schema_info = db.get_table_info()

# ---------- Helper: extract table names from a SQL query ----------
def extract_tables_from_sql(sql, known_tables):
    sql_upper = sql.upper()
    used = [t for t in known_tables if t.upper() in sql_upper]
    return ", ".join(used) if used else MSSQL_TABLE_NAMES

# ---------- Helper: extract column names from SQL ----------
def extract_columns_from_sql(sql):
    matches = re.findall(r'\[(\w+)\]', sql)
    return matches if matches else None

# ---------- MSSQL PROMPT ----------
MSSQL_PROMPT = PromptTemplate(
    input_variables=["input", "schema"],
    template="""
You are an expert Microsoft SQL Server (T-SQL) engineer.

GOAL:
Generate a T-SQL query that answers the User Question based on the provided Schema.

STRICT RULES:
1. Use ONLY T-SQL syntax.
2. EVERY column and table name MUST be wrapped in square brackets [] — NO EXCEPTIONS.
   - WRONG: AVG(PD.Close), PD.Open, T1.Commodityname, AM.AssetName
   - CORRECT: AVG(PD.[Close]), PD.[Open], T1.[Commodityname], AM.[AssetName]
3. Output ONLY the raw SQL string. 
4. DO NOT use markdown code blocks (no ```sql or ```).
5. DO NOT use backticks (`).
6. If using UNION or UNION ALL, you MUST place ORDER BY only once at the very end of the entire query.
7. ORDER BY cannot appear before UNION in T-SQL.
8. If the task requires a comparison or percentage change, write a single efficient query.
9. The dataset is historical (starting from 2006). When a user asks for 'the last 6 months' or 'current price,' do NOT use GETDATE(). Instead, always find the MAX(Date) in the table and treat that as 'Today'.
10. NEVER use LIMIT clause in T-SQL. Use TOP instead:
   - WRONG: SELECT * FROM table LIMIT 1
   - CORRECT: SELECT TOP 1 * FROM table
CRITICAL: The following are T-SQL reserved keywords and MUST always be wrapped in square brackets when used as column names:
   - [Close], [Open], [High], [Low], [Date], [Name], [Status], [Key], [Value], [Level], [Type], [Source], [Group], [Order], [Table], [Column], [Index]
   - WRONG: AVG(PD.Close), PD.Open, PD.High
   - CORRECT: AVG(PD.[Close]), PD.[Open], PD.[High]

Schema:
{schema}

User Question/Task:
{input}

SQL Query:"""
)

def clean_sql_output(raw_query):
    query = re.sub(r"```(?:sql|mssql)?", "", raw_query, flags=re.IGNORECASE)
    query = query.replace("```", "").replace("`", "")
    return query.strip()

    reserved = ["Close", "Open", "High", "Low", "Date", "Name", "Status",
                "Key", "Value", "Level", "Type", "Source", "Group", "Order"]
    for word in reserved:
        # Match word after dot but not already bracketed: e.g., PD.Close → PD.[Close]
        query = re.sub(
            rf'(?<=\.){word}(?!\w|\])',
            f'[{word}]',
            query
        )
    return query

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

def mssql_agent_node(state):
    # 1. Get state variables
    original_query = state.get("query")
    task = state.get("task")
    context_data = state.get("context_data", [])
    should_visualize = state.get("should_visualize", False)

    # 2. Build the focused input for SQL generation
    execution_input = f"TASK: {task}\nPREVIOUS FINDINGS: {context_data}\nORIGINAL QUESTION: {original_query}"

    print(f"--- MSSQL Agent: Generating SQL ---")

    # 3. Generate SQL
    formatted_prompt = MSSQL_PROMPT.format(schema=schema_info, input=execution_input)
    raw_response = llm.invoke(formatted_prompt)
    raw_sql = raw_response.content if hasattr(raw_response, "content") else raw_response
    cleaned_sql = clean_sql_output(raw_sql)

    print("\n==============================")
    print("GENERATED SQL QUERY:")
    print(cleaned_sql)
    print("==============================\n")

    # 4. Extract table names
    known_tables = [t.strip() for t in MSSQL_TABLE_NAMES.split(",")]
    used_tables = extract_tables_from_sql(cleaned_sql, known_tables)

    # 5. Execute SQL
    try:
        raw_results = db.run(cleaned_sql, fetch="all")
        print(f"DEBUG db_results raw type: {type(raw_results)}, value: {raw_results}")
        db_results = parse_db_results(raw_results)
        print(f"DEBUG db_results parsed type: {type(db_results)}, len: {len(db_results)}")
    except Exception as e:
        print(f"!!! MSSQL Execution Error: {e}")
        db_results = []

    # 6. Timestamp
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # 7. Handle empty results
    if not db_results:
        empty_prompt = f"""
        You are a helpful data assistant. A database query was executed but returned NO results.
        
        User's original question: {original_query}
        SQL that was tried (for your context only — do NOT show this to the user): {cleaned_sql}
        
        Requirements:
        - Explain in simple, friendly language why no data was found.
        - Analyze the SQL logic and suggest what might be wrong.
        - Suggest 1-2 alternative ways the user could rephrase their question.
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
        return {
            "final_output": final_text.strip(),
            "db_results": db_results,
            "sql_query": cleaned_sql,
            "should_visualize": False
        }

    # 8. Build narrative answer
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
    - NEVER include SQL queries, code, or technical database syntax in your response.

    CRITICAL: Do NOT use ### or ## or # headers in your response. Do NOT add a "Sources" section.

    Return EXACT format (plain text, no headers):
    Answer: <your explanation based on what the data actually represents>
    Database: {MSSQL_DB_NAME}
    Table: {used_tables}
    Timestamp: {timestamp}
    """
    llm_response = llm.invoke(citation_prompt)
    final_text = llm_response.content if hasattr(llm_response, "content") else llm_response

    # 9. PandasAI enhancement
    print(f"✅ REACHED PANDASAI BLOCK — db_results type: {type(db_results)}, len: {len(db_results)}")

    if isinstance(db_results, list) and db_results:
        try:
            # Extract column names from SELECT clause
            select_match = re.search(r'SELECT\s+(.*?)\s+FROM', cleaned_sql, re.IGNORECASE | re.DOTALL)
            col_names = None
            if select_match:
                select_clause = select_match.group(1)
                # Extract alias names (e.g., AS T1, AS price) or bracket names
                aliases = re.findall(r'AS\s+(\w+)\s*(?:,|$)', select_clause, re.IGNORECASE)
                brackets = re.findall(r'\[(\w+)\](?!\s*AS)', select_clause)
                col_names = aliases if aliases else brackets if brackets else None

            if isinstance(db_results[0], tuple):
                num_cols = len(db_results[0])
                if col_names and len(col_names) >= num_cols:
                    cols = col_names[:num_cols]
                else:
                    # Fallback: use generic but descriptive names
                    cols = [f"column_{i+1}" for i in range(num_cols)]
                df = pd.DataFrame(db_results, columns=cols)
            else:
                df = pd.DataFrame(db_results)

            print(f"✅ DataFrame created: shape={df.shape}, columns={df.columns.tolist()}")
            pandasai_response = process_with_pandasai(df, original_query)
            enhanced_answer = f"""{final_text}

📊 Enhanced Analysis:
{pandasai_response}"""
        except Exception as e:
            print(f"❌ PandasAI error: {e}")
            enhanced_answer = final_text
    else:
        enhanced_answer = final_text

    return {
        "final_output": enhanced_answer.strip(),
        "db_results": db_results,
        "sql_query": cleaned_sql,
        "should_visualize": should_visualize
    }