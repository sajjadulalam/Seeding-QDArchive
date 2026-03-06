from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Data folders
DOWNLOAD_DIR = BASE_DIR / "data" / "downloads"
DB_DIR = BASE_DIR / "data" / "database"
DB_PATH = DB_DIR / "Qdarchive.db"