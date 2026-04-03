from langchain_community.utilities import SQLDatabase
from config.settings import MSSQL_URI  # ← Read from settings.py



def connect_mssql():
    try:
        db = SQLDatabase.from_uri(MSSQL_URI)
        db.run("SELECT 1")
        return db
    except Exception as e:
        print("Connection failed:", e)
        return None

MSSQL_DB_NAME = "unknown_db"
MSSQL_TABLE_NAMES = "unknown"
db = connect_mssql()

if db:
    print("mssql Connected!")
    # Extract DB name from URI (e.g. mysql+pymysql://user:pass@host/my_database)
    try:
        from urllib.parse import urlparse
        parsed = urlparse(MSSQL_URI)
        MSSQL_DB_NAME = parsed.path.lstrip("/").split("?")[0] or "unknown_db"
    except Exception:
        pass
    # Extract table names from live schema
    try:
        MSSQL_TABLE_NAMES = ", ".join(db.get_usable_table_names())
    except Exception:
        pass
    print(f"  → DB: {MSSQL_DB_NAME}  |  Tables: {MSSQL_TABLE_NAMES}")
else:
    print("Not connected!")