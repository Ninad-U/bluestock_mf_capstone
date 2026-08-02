from pathlib import Path
import sqlite3
import os


print("Current folder:")
print(os.getcwd())


try:
    # Project root (one level above scripts folder)
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    # Database location
    DB_PATH = PROJECT_ROOT / "data" / "db" / "bluestock_mf.db"

    # Schema file location
    SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"


    # Create db folder if it does not exist
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    # Create/open SQLite database
    connection = sqlite3.connect(DB_PATH)


    # Read schema file
    with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
        schema = file.read()


    # Create tables
    connection.executescript(schema)


    connection.close()


    print("\nDatabase created successfully.")
    print(f"Created at: {DB_PATH}")


except Exception as e:
    print(f"\nError: {e}")


finally:
    input("\nPress Enter to exit...")