# Seeding QDArchive – Part 1: Data Acquisition Pipeline
By: Sajjadul Alam
    Friedrich Alexander University

## Overview
This project implements **Part 1 of the Seeding QDArchive assignment**.  
The goal is to build a pipeline that **collects qualitative research datasets**, stores them locally, and records metadata in a **SQLite database**.

Only datasets with **open licenses** are downloaded.

---

## Project Structure
qdarchive-seeding/
│
├── README.md
├── requirements.txt
├── .gitignore
│
├── data/
│ ├── downloads/ # downloaded research datasets
│ └── db/
│ ├── acquisition.sqlite
│ └── exports/
│ └── downloads.csv
│
├── scripts/
│ ├── acquire_run.py
│ └── export_csv.py
│
└── src/
└── qdarchive_seeding/
├── utils.py
├── db.py
└── acquire.py

---

## Installation

Create a virtual environment and install dependencies.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
Running the Pipeline

1. Add dataset URLs
Edit:scripts/acquire_run.py
Example: SEEDS = [
{
"qda_url": "https://example.org/project.zip",
"license": "CC-BY-4.0",
"title": "Interview Study Dataset"
}
]

2. Run acquisition
python scripts/acquire_run.py
This will:
create the SQLite database
download datasets
store files in data/downloads
save metadata in the database

3. Export metadata to CSV
CSV output:data/db/exports/downloads.csv

License Policy
License	                  Action
Open license	      Dataset downloaded
No license	        Metadata recorded only
Closed license	    Dataset skipped
Accepted licenses include CC0, CC-BY, CC-BY-SA, MIT, Apache.

Output
After running the pipeline you will have:
Downloaded datasets → data/downloads/
Metadata database → data/db/acquisition.sqlite
CSV export → data/db/exports/downloads.csv
