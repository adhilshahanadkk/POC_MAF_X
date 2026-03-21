import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
USE_VERTEXAI = os.getenv("USE_VERTEXAI", "false").lower() == "true"
MYSQL_URI = os.getenv("MYSQL_URI")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")
MSSQL_URI = os.getenv("MSSQL_URI")