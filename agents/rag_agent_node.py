from agents.rag_agents.rag_agent import RAGAgent
from datetime import datetime

rag_agent_instance = RAGAgent(data_path="data")

def rag_agent_node(state):
    query = state.get("query")

    rag_answer = rag_agent_instance.run(query)

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    formatted_output = f"""
Answer: {rag_answer}

Database: Document Knowledge Base
Table: Knowledge Base
Timestamp: {timestamp}
"""

    return {
        "final_output": formatted_output,
        "last_agent": "rag_agent"
    }
