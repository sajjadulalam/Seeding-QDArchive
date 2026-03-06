from datetime import datetime
from pathlib import Path

from config import DOWNLOAD_DIR, QDA_EXTENSIONS, OPEN_LICENSE_KEYWORDS
from database import init_db
from downloader import download_file, sanitize_filename
from metadata import insert_metadata
from scraper_zenodo import search_zenodo


def extract_year(date_text: str) -> str:
    if not date_text:
        return ""
    return str(date_text)[:4]


def get_authors(creators) -> str:
    if not creators:
        return ""
    names = []
    for creator in creators:
        name = creator.get("name", "").strip()
        if name:
            names.append(name)
    return "; ".join(names)


def get_license_text(metadata: dict) -> str:
    license_info = metadata.get("license", "")
    if isinstance(license_info, dict):
        return (
            license_info.get("id")
            or license_info.get("title")
            or license_info.get("name")
            or ""
        )
    return str(license_info).strip()


def is_open_license(license_text: str) -> bool:
    license_text = (license_text or "").strip().lower()
    if not license_text:
        return False

    for keyword in OPEN_LICENSE_KEYWORDS:
        if keyword in license_text:
            return True
    return False


def get_record_files(record: dict):
    # Zenodo responses sometimes expose files differently depending on API version
    files = record.get("files", [])
    normalized_files = []

    for file_info in files:
        filename = file_info.get("key") or file_info.get("filename") or "unknown_file"
        file_url = ""

        links = file_info.get("links", {})
        if isinstance(links, dict):
            file_url = (
                links.get("self")
                or links.get("download")
                or links.get("content")
                or ""
            )

        if not file_url:
            file_url = file_info.get("self", "")

        normalized_files.append({
            "filename": filename,
            "url": file_url
        })

    return normalized_files


def has_qda_file(files: list) -> tuple[bool, str]:
    for file_info in files:
        filename = file_info["filename"]
        suffix = Path(filename).suffix.lower()
        if suffix in QDA_EXTENSIONS:
            return True, file_info["url"]
    return False, ""


def process_record(record: dict):
    metadata = record.get("metadata", {})
    record_id = str(record.get("id", ""))
    concept_doi = record.get("conceptdoi", "") or metadata.get("doi", "")
    title = metadata.get("title", "")
    description = metadata.get("description", "")
    creators = metadata.get("creators", [])
    publication_date = metadata.get("publication_date", "") or metadata.get("date", "")
    source_url = record.get("links", {}).get("self_html", f"https://zenodo.org/records/{record_id}")
    license_text = get_license_text(metadata)

    if not is_open_license(license_text):
        print(f"Skipping record {record_id}: no open license found")
        return

    files = get_record_files(record)
    if not files:
        print(f"Skipping record {record_id}: no files found")
        return

    contains_qda, qda_file_url = has_qda_file(files)
    if not contains_qda:
        print(f"Skipping record {record_id}: no QDA file found")
        return

    record_folder = DOWNLOAD_DIR / "zenodo" / record_id
    record_folder.mkdir(parents=True, exist_ok=True)

    author_text = get_authors(creators)
    year = extract_year(publication_date)

    for file_info in files:
        original_filename = file_info["filename"]
        file_url = file_info["url"]

        if not file_url:
            print(f"Skipping file with missing URL in record {record_id}")
            continue

        safe_filename = sanitize_filename(original_filename)
        destination = record_folder / safe_filename
        suffix = destination.suffix.lower()
        is_qda = 1 if suffix in QDA_EXTENSIONS else 0

        success = download_file(file_url, destination)

        row = {
            "source_name": "Zenodo",
            "source_url": source_url,
            "context_repository": "Zenodo",
            "record_id": record_id,
            "title": title,
            "author": author_text,
            "year": year,
            "uploader_name": "",
            "uploader_email": "",
            "doi": concept_doi,
            "description": description,
            "license": license_text,
            "qda_file_url": qda_file_url,
            "file_url": file_url,
            "local_directory": str(record_folder),
            "local_filename": safe_filename,
            "local_file_path": str(destination),
            "file_type": suffix,
            "is_qda_file": is_qda,
            "download_status": "success" if success else "failed",
            "downloaded_at": datetime.utcnow().isoformat()
        }

        insert_metadata(row)

        if success:
            print(f"Downloaded: {destination}")
        else:
            print(f"Failed: {file_url}")


def main():
    print("Initializing database...")
    init_db()

    print("Searching Zenodo...")
    records = search_zenodo()

    print(f"Found {len(records)} records")

    for record in records:
        process_record(record)

    print("Done.")


if __name__ == "__main__":
    main()