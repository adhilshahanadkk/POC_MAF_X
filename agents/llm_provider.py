from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import GOOGLE_API_KEY, PRIMARY_MODEL

def get_llm(model_name=None, temperature=0.2):
    selected_model = model_name or PRIMARY_MODEL

    return ChatGoogleGenerativeAI(
        model=selected_model,
        google_api_key=GOOGLE_API_KEY,
        temperature=temperature
    )