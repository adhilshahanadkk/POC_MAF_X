from config.settings import FALLBACK_MODELS
from agents.llm_provider import get_llm

RETRYABLE_ERRORS = [
    "token",
    "context length",
    "rate limit",
    "resource exhausted",
    "quota exceeded",
    "timeout",
    "internal",
    "unavailable",
    "429",
    "503",
    "not subscriptable",
]

def invoke_with_fallback(messages, temperature=0.2):
    last_error = None

    for model_name in FALLBACK_MODELS:
        try:
            print(f"Trying model: {model_name}")

            llm = get_llm(
                model_name=model_name,
                temperature=temperature
            )

            response = llm.invoke(messages)

            print(f"Success with model: {model_name}")

            return response

        except Exception as e:
            error_text = str(e).lower()
            last_error = e

            print(f"Model failed: {model_name}")
            print(f"Error: {e}")

            if any(keyword in error_text for keyword in RETRYABLE_ERRORS):
                print(f"Retrying with next fallback model...")
                continue

            raise e

    raise Exception(f"All fallback models failed. Last error: {last_error}")