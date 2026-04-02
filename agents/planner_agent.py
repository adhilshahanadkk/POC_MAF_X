from langchain_core.prompts import PromptTemplate
from database.mssql_connection import db as db_mssql
from database.mysql_connection import db as db_mysql
from agents.llm_provider import get_llm
import json
import re


llm = get_llm(temperature=0.0)

from sqlalchemy import inspect

def get_condensed_schema(db):
    # 1. Get the list of tables you're allowed to use
    tables = db.get_usable_table_names()
    
    # 2. Get the SQLAlchemy inspector from the LangChain DB object
    # LangChain stores the inspector in ._inspector
    inspector = inspect(db._engine)
    
    summary = []
    for table in tables:
        try:
            # 3. Fetch column details for each table
            columns = inspector.get_columns(table)
            column_names = [col['name'] for col in columns]
            
            # Create the condensed string: "table_name (col1, col2, col3)"
            summary.append(f"{table} ({', '.join(column_names)})")
        except Exception as e:
            print(f"Could not skip table {table}: {e}")
            
    return " | ".join(summary)


def parse_planner_output(raw_content):
    # Method 1: Clean using Regex (Reliable for raw strings)
    # This finds everything between the first { and the last }
    match = re.search(r'\{.*\}', raw_content, re.DOTALL)
    if match:
        json_str = match.group(0)
    else:
        json_str = raw_content

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return None


planner_template = """
### ROLE
You are a Project Manager Agent. Your goal is to decompose the user's {query} into a sequential JSON execution plan for specialized agents.

### AGENT DOMAINS & SCHEMA
- mysql_agent (User Data): Profiles and subscriptions. 
    Tables: {mysql_summary}
- mssql_agent (Market Data): Raw commodity pricing data and historical price records. 
    Tables: {mssql_summary}
- rag_agent (Documentation): User-uploaded documents — policies, manuals, and files.
- vm_agent (Permanent Knowledge Base): Transgraph commodity research articles, technical outlooks, price forecasts, and market analysis reports.


### PLANNING RULES (STRICT COMPLIANCE REQUIRED)
1. **Sequential Logic**: Arrange agents in the exact order required to solve the problem. If a price depends on a user's subscription, the user data agent MUST come first.
2. **Dependency Injection**: If Agent B requires data found by Agent A, you MUST use the placeholder {{prev_result}} in Agent B's task description. Explain what specific piece of data to extract from that result.
3. **Field Specificity**: Use exact column names from the schema provided above (e.g., instead of "user's start date", use "start_date from the subscription table").
4. **Task Isolation**: Each task must be a clear "mission" that an agent can execute using only its data source and the provided context.


### OUTPUT FORMAT
Return ONLY valid JSON:
{{
  "execution_plan": [
    {{ 
      "agent": "agent_name", 
      "task": "Step-by-step instructions. If needed, mention: 'Extract [field] from {{prev_result}} to use in your query.'" 
    }}
  ],
  "should_visualize": true or false
}}

### VISUALIZATION DECISION RULES
- Set "should_visualize" to true if the final result will contain MULTIPLE numerical/categorical data points (e.g., list of users with counts, commodity prices, time-series data)
- Set "should_visualize" to false if the result will be a single value, pure text, or policy documentation

STRICTLY DONOT ADD ANY prefix tex 

### USER QUERY
{query}
"""


def planner_agent_node(state):
    query= state.get("query")
    

    planner_prompt = PromptTemplate(
    input_variables=["query", "mysql_summary", "mssql_summary"],
    template=planner_template
    )
    prompt = planner_prompt.format(
        query=query,
        mysql_summary=get_condensed_schema(db_mysql), 
        mssql_summary=get_condensed_schema(db_mssql)
    )
    #input_variables
    plan=llm.invoke(prompt)
    content = plan.content if hasattr(plan, "content") else plan

    # PARSING THE JSON
    try:
        # We need to extract the list of agents for your 'plan' key
        plan_json = parse_planner_output(content)
        # print("\n\nplan_json",plan_json)
        execution_plan = plan_json.get("execution_plan", [])
        should_visualize = plan_json.get("should_visualize", False)
        
        # If your next node expects just a list of names:
        agent_names = [step["agent"] for step in execution_plan]
        
        # If your next node expects the full tasks (Recommended):
        # return {"plan": execution_plan} 
        
        # print("Planner agent sequence:", agent_names)
        # print("full_tasks",execution_plan)
        # print("should_visualize", should_visualize)
        return {"plan": agent_names, "full_tasks": execution_plan, "should_visualize": should_visualize}

    except Exception as e:
        print(f"JSON Parsing failed: {e}. Raw content: {content}")
        # Fallback logic
        return {"plan": [], "error": "Failed to parse planner output"}
    