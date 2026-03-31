from agents.llm_provider import get_llm

llm = get_llm(temperature=0.2)

def analysis_agent_node(state):
    result = state.get("sql_result")

    explanation = llm.invoke(
        f"Explain this database result in simple language:\n{result}"
    )

    if hasattr(explanation, "content"):
        explanation = explanation.content

    return {"final_output": explanation}

