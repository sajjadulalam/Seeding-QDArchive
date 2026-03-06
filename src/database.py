import sqlite3
from .config import DB_PATH

def init_db():
    """
    Initialize SQLite database and create table if not exists.
    """

    # Ensure database directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_name TEXT NOT NULL,
        source_url TEXT NOT NULL,
        qda_file_url TEXT NOT NULL,
        download_timestamp TEXT NOT NULL,
        local_directory TEXT NOT NULL,
        qda_filename TEXT NOT NULL,
        license TEXT,
        doi TEXT,
        description TEXT,
        file_type TEXT
    )
    """)

    conn.commit()
    conn.close()

    print("Database initialized successfully.")