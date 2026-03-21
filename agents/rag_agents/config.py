from dotenv import load_dotenv
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

if not GOOGLE_API_KEY:
    raise RuntimeError(
        f"Gemini API key not found. Expected GOOGLE_API_KEY or GEMINI_API_KEY in {ENV_PATH}"
    )
