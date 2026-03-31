# Seeding QDArchive – Part 1: Data Acquisition Pipeline
By: Sajjadul Alam.<br>
    Friedrich Alexander University

## Overview
This project implements **Part 1 of the Seeding QDArchive assignment**.  
The goal is to build a pipeline that **collects qualitative research datasets**, stores them locally, and records metadata in a **SQLite database**.

Only datasets with **open licenses** are downloaded.

---

## Project Structure

```
qdarchive-seeding/
│
├── README.md
├── .gitignore
├── .github
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

## Features
Searches Zenodo for qualitative research project files
Detects records that contain QDA project files
Downloads the full record folder for qualifying projects
Stores file-level metadata in SQLite
Exports metadata to CSV

## Installation

pip install -r requirements.txt
### Run the project
From the project root: python src/main.py

![Screenshot 2026-03-31 131449](https://github.com/user-attachments/assets/04dd9fcd-3af5-420c-963e-04e26f79553c)

### Export CSV
From the project root: python src/export_csv.py

![Screenshot 2026-03-31 131449](https://github.com/user-attachments/assets/cd467511-5615-4816-877c-802098155a6b)

After running the pipeline: python src/export_csv.py
The CSV will be saved in: data/database/exports/projects.csv
### Database location
data/database/qdarchive_part1.db
### Download location
data/downloads/


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
