from agents.rag_agents.rag_agent import RAGAgent
from datetime import datetime

# Fallback instance (used only when no rag_agent is in state)
_fallback_rag = None

def _get_fallback_rag():
    global _fallback_rag
    if _fallback_rag is None:
        _fallback_rag = RAGAgent(data_path="data")
    return _fallback_rag

def rag_agent_node(state):
    query = state.get("query")
    chat_history = state.get("chat_history", [])

    # Use the server-managed RAG agent (rebuilt after uploads) if available
    rag = state.get("rag_agent")
    if rag is None:
        rag = _get_fallback_rag()

    # Include chat history as context for better answers
    if chat_history:
        history_context = "\n".join(chat_history[-10:])
        enriched_query = f"CONVERSATION HISTORY:\n{history_context}\n\nCURRENT QUESTION: {query}"
    else:
        enriched_query = query

    rag_answer = rag.run(enriched_query)

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

