# Seeding QDArchive — Project (Part 1 + Part 2 scaffold)

This repo implements the project as specified:
- **Part 1**: Acquire qualitative research project folders (open license only), store metadata in **SQLite** (exportable to CSV), and store files locally with one folder per project.
- **Part 2**: Classify entries using **ISIC Rev. 5** down to **division** level (two levels: section + division), plus optional tags.
- **Part 3**: Placeholder (future).

## Requirements
- Python 3.10+ recommended

## Setup
```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
