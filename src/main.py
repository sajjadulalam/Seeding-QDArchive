from datetime import datetime, UTC
from pathlib import Path
from urllib.parse import urljoin, urlparse
import mimetypes
import requests
from bs4 import BeautifulSoup

from config import DOWNLOAD_DIR, QDA_EXTENSIONS
from database import init_db
from downloader import download_file, sanitize_filename
from metadata import insert_metadata
from scraper_sada import search_sada
from scraper_columbia import search_columbia


def extension_from_content_type(content_type: str) -> str:
    content_type = (content_type or "").split(";")[0].strip().lower()

    mapping = {
        "application/pdf": ".pdf",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.ms-excel": ".xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "text/csv": ".csv",
        "application/zip": ".zip",
        "application/x-zip-compressed": ".zip",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        "application/vnd.ms-powerpoint": ".ppt",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
        "video/mp4": ".mp4",
        "video/x-msvideo": ".avi",
        "text/plain": ".txt",
        "application/json": ".json",
        "application/xml": ".xml",
        "text/xml": ".xml",
    }

    if content_type in mapping:
        return mapping[content_type]

    guessed = mimetypes.guess_extension(content_type)
    return guessed or ""


def get_url_head_info(url: str) -> tuple[str, str]:
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(url, headers=headers, timeout=30, allow_redirects=True, stream=True)
        r.raise_for_status()
        content_type = (r.headers.get("Content-Type") or "").lower()
        final_url = r.url
        r.close()
        return content_type, final_url
    except Exception:
        return "", url


def extract_year(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) >= 4:
        return text[:4]
    return text


def is_qda_filetype(file_type: str) -> int:
    return 1 if file_type in QDA_EXTENSIONS else 0


def normalize_record(record: dict, source_name: str) -> dict:
    record_id = str(
        record.get("id")
        or record.get("record_id")
        or ""
    ).strip()

    title = str(record.get("title") or "").strip()
    source_url = str(record.get("url") or "").strip()
    description = str(record.get("description") or "").strip()
    year = extract_year(record.get("year") or record.get("date") or "")
    license_text = str(record.get("license") or "").strip()

    author = ""
    if record.get("author"):
        author = str(record.get("author")).strip()
    elif record.get("authors"):
        if isinstance(record["authors"], list):
            author = "; ".join(str(a).strip() for a in record["authors"] if str(a).strip())
        else:
            author = str(record["authors"]).strip()
    elif record.get("creators"):
        creators = record["creators"]
        if isinstance(creators, list):
            author = "; ".join(
                c.get("name", "").strip() if isinstance(c, dict) else str(c).strip()
                for c in creators
            ).strip("; ").strip()
        else:
            author = str(creators).strip()

    file_url = str(
        record.get("file_url")
        or record.get("download_url")
        or source_url
    ).strip()

    return {
        "source_name": source_name,
        "context_repository": source_name,
        "record_id": record_id,
        "title": title,
        "author": author,
        "year": year,
        "description": description,
        "license": license_text,
        "source_url": source_url,
        "file_url": file_url,
    }


def is_probable_file_url(url: str) -> bool:
    if not url:
        return False

    path = urlparse(url).path.lower()

    file_exts = {
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".zip", ".rar", ".7z",
        ".txt", ".rtf", ".xml", ".json", ".jpg", ".jpeg", ".png", ".mp3", ".mp4",
        ".wav", ".avi", ".mov", ".qda", ".qdpx", ".qdp", ".nvp", ".nvpx"
    }

    return any(path.endswith(ext) for ext in file_exts)


def extract_file_links_from_page(page_url: str) -> list[dict]:
    headers = {"User-Agent": "Mozilla/5.0"}
    results = []
    seen = set()

    try:
        r = requests.get(page_url, headers=headers, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"Could not open record page {page_url}: {e}")
        return results

    content_type = (r.headers.get("Content-Type") or "").lower()

    if "text/html" not in content_type and is_probable_file_url(page_url):
        filename = Path(urlparse(page_url).path).name or "downloaded_file"
        return [{"filename": filename, "url": page_url}]

    soup = BeautifulSoup(r.text, "html.parser")

    # First: prefer explicit SADA download buttons
    for link in soup.select("a.download"):
        href = (link.get("href") or "").strip()
        filename = (link.get("data-filename") or "").strip()
        extension = (link.get("data-extension") or "").strip().lower()

        if not href:
            continue

        full_url = urljoin(page_url, href)

        if not filename:
            filename = Path(urlparse(full_url).path).name or "downloaded_file"

        if extension and not filename.lower().endswith("." + extension):
            filename = f"{filename}.{extension}"

        key = (filename, full_url)
        if key in seen:
            continue
        seen.add(key)

        results.append({
            "filename": filename,
            "url": full_url
        })

    if results:
        return results

    # Fallback: generic file-link detection
    for link in soup.select("a[href]"):
        href = (link.get("href") or "").strip()
        if not href:
            continue

        full_url = urljoin(page_url, href)
        text = " ".join(link.get_text(" ", strip=True).split())
        filename = Path(urlparse(full_url).path).name.strip()

        downloadable = False

        if is_probable_file_url(full_url):
            downloadable = True

        text_lower = text.lower()
        href_lower = full_url.lower()

        strong_words = [
            "download", "pdf", "csv", "zip", "xls", "xlsx",
            "doc", "docx", "audio", "video", "mp3", "mp4", "wav", "xml"
        ]
        if any(word in text_lower for word in strong_words):
            downloadable = True

        if any(token in href_lower for token in ["/download/", "format=raw", "attachment", "bitstream", "/metadata/export/"]):
            downloadable = True

        if downloadable:
            if not filename:
                filename = sanitize_filename(text) if text else "downloaded_file"

            key = (filename, full_url)
            if key in seen:
                continue
            seen.add(key)

            results.append({
                "filename": filename,
                "url": full_url
            })

    return results


def process_record(record: dict, source_name: str):
    normalized = normalize_record(record, source_name)

    title = normalized["title"]
    source_url = normalized["source_url"]

    if not title and not source_url:
        print(f"Skipping {source_name} record: missing title and URL")
        return

    record_id = normalized["record_id"]
    safe_title = sanitize_filename(title) if title else "untitled"

    if record_id:
        folder_name = f"{record_id}_{safe_title}"
    else:
        folder_name = safe_title[:100] if safe_title else "unknown_record"

    record_folder = DOWNLOAD_DIR / source_name.lower() / folder_name[:150]
    record_folder.mkdir(parents=True, exist_ok=True)

    file_links = extract_file_links_from_page(source_url)

    if not file_links:
        print(f"No downloadable files found on [{source_name}] record page: {source_url}")
        return

    print(f"Found {len(file_links)} file(s) for [{source_name}] {title}")

    for file_info in file_links:
        original_filename = file_info["filename"]
        file_url = file_info["url"]

        content_type, final_url = get_url_head_info(file_url)

        if "text/html" in content_type:
            print(f"Skipping HTML page instead of file: {file_url}")
            continue

        safe_filename = sanitize_filename(original_filename)

        current_suffix = Path(safe_filename).suffix.lower()
        if not current_suffix:
            ext = extension_from_content_type(content_type)

            if not ext:
                ext = Path(urlparse(final_url).path).suffix.lower()

            if ext:
                safe_filename += ext

        destination = record_folder / safe_filename
        suffix = destination.suffix.lower()
        is_qda = 1 if suffix in QDA_EXTENSIONS else 0

        success = download_file(file_url, destination)

        row = {
            "source_name": normalized["source_name"],
            "source_url": normalized["source_url"],
            "context_repository": normalized["context_repository"],
            "record_id": record_id,
            "title": title,
            "author": normalized["author"],
            "year": normalized["year"],
            "uploader_name": "",
            "uploader_email": "",
            "doi": "",
            "description": normalized["description"],
            "license": normalized["license"],
            "qda_file_url": file_url if is_qda else "",
            "file_url": file_url,
            "local_directory": str(record_folder),
            "local_filename": safe_filename,
            "local_file_path": str(destination),
            "file_type": suffix,
            "is_qda_file": is_qda,
            "download_status": "success" if success else "failed",
            "downloaded_at": datetime.now(UTC).isoformat()
        }

        insert_metadata(row)

        if success:
            print(f"Downloaded [{source_name}]: {destination}")
        else:
            print(f"Failed [{source_name}]: {file_url}")


def main():
    print("Initializing database...")
    init_db()

    print("Searching SADA...")
    try:
        sada_records = search_sada(rows=None, per_page=15, max_pages=50)
        print(f"Found {len(sada_records)} SADA records")
    except Exception as e:
        print(f"Error searching SADA: {e}")
        sada_records = []

    print("Searching Columbia...")
    try:
        columbia_records = search_columbia()
        print(f"Found {len(columbia_records)} Columbia records")
    except Exception as e:
        print(f"Error searching Columbia: {e}")
        columbia_records = []

    for record in sada_records:
        process_record(record, "SADA")

    for record in columbia_records:
        process_record(record, "Columbia")

    print("Done.")


if __name__ == "__main__":
    main()