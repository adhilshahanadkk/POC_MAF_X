from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import GOOGLE_API_KEY, GOOGLE_CLOUD_PROJECT, USE_VERTEXAI

def get_llm(temperature=0.2):
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=GOOGLE_API_KEY,
        # project=GOOGLE_CLOUD_PROJECT,
        # vertexai=USE_VERTEXAI,
        temperature=temperature
    )