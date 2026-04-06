from langchain_community.utilities import SQLDatabase
from config.settings import MSSQL_URI


def connect_mssql():
    try:
        db = SQLDatabase.from_uri(MSSQL_URI)
        db.run("SELECT 1")
        return db
    except Exception as e:
        print("Connection failed:", e)
        return None


db = connect_mssql()

if db:
    print("MSSQLConnected!")

    # Auto-detect database name and tables
    try:
        MSSQL_DB_NAME = db._engine.url.database
    except Exception:
        MSSQL_DB_NAME = "mssql_database"

    try:
        MSSQL_TABLE_NAMES = ", ".join(db.get_usable_table_names())
    except Exception:
        MSSQL_TABLE_NAMES = "unknown_tables"

else:
    print("Not connected!")

    MSSQL_DB_NAME = "mssql_database"
    MSSQL_TABLE_NAMES = "unknown_tables"