import sqlite3
from datetime import datetime
from .config import DB_PATH

def insert_metadata(record, local_dir, filename, download_url):
    """
    Insert metadata of downloaded QDA file into SQLite database.
    """

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO projects (
                source_name,
                source_url,
                qda_file_url,
                download_timestamp,
                local_directory,
                qda_filename,
                license,
                doi,
                description,
                file_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Zenodo",
            record.get("links", {}).get("html", ""),
            download_url,
            datetime.now().isoformat(),
            local_dir,
            filename,
            record.get("metadata", {}).get("license", ""),
            record.get("metadata", {}).get("doi", ""),
            record.get("metadata", {}).get("description", ""),
            filename.split(".")[-1]
        ))

        conn.commit()
        conn.close()

        print("Metadata saved.")

    except Exception as e:
        print(f"Error inserting metadata: {e}")