from utils.llm_retry import invoke_with_fallback

def analysis_agent_node(state):
    result = state.get("sql_result")

    explanation = invoke_with_fallback(
        f"Explain this database result in simple language:\n{result}",
        temperature=0.2
    )

    if hasattr(explanation, "content"):
        explanation = explanation.content

    return {"final_output": explanation}