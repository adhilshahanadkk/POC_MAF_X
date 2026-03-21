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


db = connect_mssql()

if db:
    print("MSSQLConnected!")
else:
    print("Not connected!")