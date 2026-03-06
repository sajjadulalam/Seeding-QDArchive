# AI Coding Guidelines for Seeding QDArchive

## Project Overview
This codebase seeds a Qualitative Data Archive by scraping Zenodo for QDA project files (.qdpx, .qpdx), downloading them locally, and storing metadata in SQLite. The pipeline runs sequentially: search → filter → download → metadata insertion.

## Architecture
- **Entry Point**: `src/main.py` orchestrates the pipeline via `run_pipeline()`
- **Data Flow**: Zenodo API → scraper → downloader → metadata DB
- **Storage**: Files in `data/downloads/zenodo/{record_id}/`, metadata in `data/database/Qdarchive.db`
- **Key Components**:
  - `scraper_zenodo.py`: Searches Zenodo API with query "qdpx OR qpdx"
  - `downloader.py`: Downloads files, creates directories automatically
  - `metadata.py`: Inserts records into SQLite `projects` table
  - `database.py`: Initializes DB schema with fields like doi, license, description

## Conventions
- **File Extensions**: Only process .qdpx and .qpdx files (Qualitative Data Analysis formats)
- **Directory Structure**: Use `Path` objects from `pathlib`, resolve relative to `BASE_DIR`
- **Error Handling**: Print errors but continue processing (no exceptions raised)
- **Database**: SQLite with manual connection/commit/close pattern
- **Timestamps**: ISO format using `datetime.now().isoformat()`

## Development Workflow
- **Setup**: Create venv, activate, `pip install -r requirements.txt` (currently empty)
- **Run**: `python src/main.py` executes full pipeline
- **Data Paths**: All paths defined in `config.py`, create directories with `mkdir(parents=True, exist_ok=True)`
- **API Limits**: Zenodo requests use 30s timeout, handle 200 status only

## Code Patterns
- **Imports**: Relative imports within `src/`, config constants at top
- **Functions**: Single responsibility, e.g., `search_zenodo()` returns list of records
- **Metadata Extraction**: Access nested dicts like `record.get("metadata", {}).get("doi", "")`
- **File Saving**: Use `with open(save_path, "wb")` for binary downloads

## Extension Points
- Add new scrapers by implementing search function returning record dicts
- Extend metadata fields by altering `projects` table schema
- Support new file types by modifying extension checks in `main.py`