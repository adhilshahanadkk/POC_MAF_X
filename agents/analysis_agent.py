from langchain_google_genai import GoogleGenerativeAI
from config.settings import GOOGLE_API_KEY
from config.settings import GEMINI_MODEL

llm = GoogleGenerativeAI(
    model=GEMINI_MODEL,
    google_api_key=GOOGLE_API_KEY
)

def analysis_agent_node(state):
    result = state.get("sql_result")

    explanation = llm.invoke(
        f"Explain this database result in simple language:\n{result}"
    )

    return {"final_output": explanation}

