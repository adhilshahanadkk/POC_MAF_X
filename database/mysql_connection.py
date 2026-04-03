from langchain_community.utilities import SQLDatabase
from config.settings import MYSQL_URI


def connect_mysql():
    try:
        db = SQLDatabase.from_uri(MYSQL_URI)
        db.run("SELECT 1")
        return db
    except Exception as e:
        print("Connection failed:", e)
        return None


db = connect_mysql()

# ── Dynamically extract DB name and table names ──────────────────────────────
MYSQL_DB_NAME = "unknown_db"
MYSQL_TABLE_NAMES = "unknown"

if db:
    print("mysql Connected!")
    # Extract DB name from URI (e.g. mysql+pymysql://user:pass@host/my_database)
    try:
        from urllib.parse import urlparse
        parsed = urlparse(MYSQL_URI)
        MYSQL_DB_NAME = parsed.path.lstrip("/").split("?")[0] or "unknown_db"
    except Exception:
        pass
    # Extract table names from live schema
    try:
        MYSQL_TABLE_NAMES = ", ".join(db.get_usable_table_names())
    except Exception:
        pass
    print(f"  → DB: {MYSQL_DB_NAME}  |  Tables: {MYSQL_TABLE_NAMES}")
else:
    print("Not connected!")
