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

if db:
    print("mysql Connected!")
else:
    print("Not connected!")

