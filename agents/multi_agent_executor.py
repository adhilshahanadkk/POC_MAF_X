from agents.sql_agent import sql_agent_node
from agents.mssql_agent import mssql_agent_node
from agents.rag_agent_node import rag_agent_node

def execute_agents_node(state):
    # 'full_tasks' is the list of dicts: [{"agent": "...", "task": "..."}]
    plan = state.get("full_tasks", [])
    
    # context_data acts as the 'Short-term Memory' for the sequence
    # Initialize it if it doesn't exist
    if "context_data" not in state:
        state["context_data"] = []
    print(plan)
    print(f"--- Starting Execution for {len(plan)} steps ---")

    for step in plan:
        agent_type = step.get("agent")
        task_description = step.get("task")
        
        success = False
        retry_count = 0

        while retry_count < 2 and not success:
            try:
                print(f"Executing {agent_type} | Task: {task_description[:50]}...")

                # 1. Prepare the payload for the specific worker
                # We pass the Task + previous findings + original query
                worker_input = {
                    "query": state.get("query"),
                    "task": task_description,
                    "context_data": state["context_data"] 
                }

                # 2. Route to the specialized agent node
                if agent_type == "mysql_agent":
                    res = sql_agent_node(worker_input)
                elif agent_type == "mssql_agent":
                    res = mssql_agent_node(worker_input)
                elif agent_type == "rag_agent":
                    res = rag_agent_node(worker_input)
                else:
                    print(f"Unknown agent type: {agent_type}")
                    break

                # 3. Capture the finding
                finding = res.get("final_output", "No result returned.")
                
                # 4. Append to context so NEXT agent can see it
                state["context_data"].append({
                    "step_agent": agent_type,
                    "step_task": task_description,
                    "finding": finding
                })
                
                success = True

            except Exception as e:
                print(f"Error in {agent_type}: {e}. Retry {retry_count+1}/2")
                retry_count += 1

        if not success:
            state["context_data"].append({
                "step_agent": agent_type,
                "finding": f"FAILED after {retry_count} retries."
            })

    # Final results for the state
    return {"multi_results": [c["finding"] for c in state["context_data"]], "context_data": state["context_data"]}
