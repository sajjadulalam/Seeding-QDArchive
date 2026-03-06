# Seeding-QDArchive
By: Sajjadul Alam<br>
Friedrich Alexander University<br>

This project is Part 1 of the QDArchive seeding workflow. It collects qualitative research project files from public repositories, downloads them locally, and stores metadata in an SQLite database that can later be exported to CSV.

## Project Structure

```text
Seeding-QDArchive/
│
├── README.md
├── requirements.txt
├── .gitignore
│
├── data/
│   ├── downloads/
│   └── database/
│       └── exports/
│
└── src/
    ├── config.py
    ├── database.py
    ├── downloader.py
    ├── export_csv.py
    ├── main.py
    ├── metadata.py
    └── scraper_zenodo.py
```
### Features
Searches Zenodo for qualitative research project files
Detects records that contain QDA project files
Downloads the full record folder for qualifying projects
Stores file-level metadata in SQLite
Exports metadata to CSV

### Installation
pip install -r requirements.txt
### Run the project
From the project root:python src/main.py
### Export CSV
python src/export_csv.py
The CSV will be saved in: data/database/exports/projects.csv
### Database location
data/database/qdarchive_part1.db
### Download location
data/downloads/
### Notes
Part 1 requires:
downloading QDA-related project files
storing structured metadata in SQLite
making the metadata exportable to CSV
This project satisfies that workflow for Zenodo-based collection.

---

## `src/config.py`

```python
from pathlib import Path

# Project root
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directories
DATA_DIR = BASE_DIR / "data"
DOWNLOAD_DIR = DATA_DIR / "downloads"
DATABASE_DIR = DATA_DIR / "database"
EXPORT_DIR = DATABASE_DIR / "exports"

# Database file
DB_PATH = DATABASE_DIR / "qdarchive_part1.db"

# Create directories if they do not exist
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# File extensions typically associated with QDA project files
QDA_EXTENSIONS = {
    ".qdpx", ".qpdx", ".qda", ".qda-project", ".qde", ".atlproj", ".nvp", ".nvpx"
}

# Open-license keywords
OPEN_LICENSE_KEYWORDS = {
    "cc-by",
    "cc-by-4.0",
    "cc-by-sa",
    "cc-by-sa-4.0",
    "cc0",
    "cc0-1.0",
    "creative commons",
    "open"
}
