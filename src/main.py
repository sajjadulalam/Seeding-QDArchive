from .scraper_zenodo import search_zenodo
from .downloader import download_file
from .metadata import insert_metadata
from .database import init_db
from .config import DOWNLOAD_DIR
from pathlib import Path


def run_pipeline():

    print("Initializing database...")
    init_db()

    print("Searching Zenodo...")
    records = search_zenodo()

    if not records:
        print("No records found.")
        return

    for record in records:
        record_id = record.get("id")
        files = record.get("files", [])

        if not files:
            continue

        for file in files:
            filename = file.get("key", "")

            # Only download QDA files
            if filename.endswith((".qdpx", ".qpdx")):

                download_url = file.get("links", {}).get("self")

                if not download_url:
                    continue

                local_dir = f"zenodo/{record_id}"
                save_path = DOWNLOAD_DIR / local_dir / filename

                print(f"\nDownloading {filename}...")
                download_file(download_url, save_path)

                insert_metadata(record, local_dir, filename, download_url)

    print("\nPipeline finished successfully.")


if __name__ == "__main__":
    run_pipeline()