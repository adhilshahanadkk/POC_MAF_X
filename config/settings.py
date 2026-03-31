import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "project-fea13377-5812-4bae-9ee")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_GENAI_USE_VERTEXAI = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "true").lower() == "true"
MYSQL_URI = os.getenv("MYSQL_URI")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MSSQL_URI = os.getenv("MSSQL_URI")