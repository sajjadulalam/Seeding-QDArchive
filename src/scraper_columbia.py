import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

GUIDE_URL = "https://guides.library.columbia.edu/oral_history/digital_collections"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# These phrases help find the useful links on the guide page and linked pages.
KEYWORDS = [
    "oral history",
    "digital library collection",
    "digital collections",
    "interview",
    "transcript",
    "audio",
    "video",
]

FILE_EXTS = {
    ".pdf", ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".doc", ".docx", ".txt", ".csv", ".xml", ".json", ".zip"
}


def normalize_text(value: str) -> str:
    return " ".join((value or "").split()).strip()


def looks_like_file(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in FILE_EXTS)


def extract_year_from_text(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"\b(19|20)\d{2}\b", text)
    return m.group(0) if m else ""


def is_relevant_link(text: str, href: str) -> bool:
    text_l = (text or "").lower()
    href_l = (href or "").lower()

    if any(k in text_l for k in KEYWORDS):
        return True

    if any(k.replace(" ", "_") in href_l or k.replace(" ", "-") in href_l for k in KEYWORDS):
        return True

    if looks_like_file(href):
        return True

    return False


def collect_links_from_page(url: str) -> list[dict]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"Could not fetch page: {url} -> {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    seen = set()

    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        text = normalize_text(a.get_text(" ", strip=True))
        if not href:
            continue

        full_url = urljoin(url, href)
        key = (text, full_url)
        if key in seen:
            continue

        if not is_relevant_link(text, full_url):
            continue

        seen.add(key)
        results.append({
            "title": text or full_url,
            "url": full_url,
        })

    return results


def extract_records_from_candidate_page(url: str) -> list[dict]:
    """
    Try to extract record-like links from a linked Columbia page.
    This is intentionally flexible because Columbia pages may be LibGuides,
    library content pages, resolver pages, or collection pages.
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"Could not fetch candidate page: {url} -> {e}")
        return []

    content_type = (r.headers.get("Content-Type") or "").lower()

    # Direct file URL
    if "text/html" not in content_type and looks_like_file(url):
        filename = urlparse(url).path.rsplit("/", 1)[-1] or "download"
        return [{
            "id": "",
            "title": filename,
            "url": url,
            "year": "",
            "description": "",
        }]

    soup = BeautifulSoup(r.text, "html.parser")
    records = []
    seen = set()

    # Generic record/item selectors
    candidates = soup.select(
        "a[href], h1 a[href], h2 a[href], h3 a[href], "
        "article a[href], li a[href], .views-row a[href], .card a[href]"
    )

    for a in candidates:
        href = (a.get("href") or "").strip()
        title = normalize_text(a.get_text(" ", strip=True))

        if not href:
            continue

        full_url = urljoin(url, href)
        title_l = title.lower()
        href_l = full_url.lower()

        # Keep oral-history / interview / media / transcript / file-ish links
        if not (
            any(k in title_l for k in KEYWORDS)
            or any(k.replace(" ", "-") in href_l or k.replace(" ", "_") in href_l for k in KEYWORDS)
            or looks_like_file(full_url)
        ):
            continue

        if full_url in seen:
            continue

        seen.add(full_url)

        records.append({
            "id": "",
            "title": title or full_url,
            "url": full_url,
            "year": extract_year_from_text(title),
            "description": "",
        })

    return records


def search_columbia(max_follow_links=20):
    datasets = []
    seen_urls = set()

    print(f"Fetching Columbia guide page: {GUIDE_URL}")
    guide_links = collect_links_from_page(GUIDE_URL)
    print(f"Found {len(guide_links)} relevant link(s) on guide page")

    followed = 0

    for link in guide_links:
        if followed >= max_follow_links:
            break

        candidate_url = link["url"]

        # Stay focused on Columbia/library-related targets
        if not any(host in candidate_url for host in [
            "columbia.edu",
            "library.columbia.edu",
            "guides.library.columbia.edu",
            "resolver.library.columbia.edu",
        ]):
            continue

        print(f"Following: {candidate_url}")
        followed += 1

        records = extract_records_from_candidate_page(candidate_url)

        if not records:
            # If the guide page link itself is useful, still keep it as a collection-level record
            title = link["title"]
            if candidate_url not in seen_urls:
                seen_urls.add(candidate_url)
                datasets.append({
                    "id": "",
                    "title": title,
                    "url": candidate_url,
                    "year": "",
                    "description": "",
                })
            continue

        for record in records:
            record_url = record["url"]
            if record_url in seen_urls:
                continue
            seen_urls.add(record_url)
            datasets.append(record)

    return datasets


if __name__ == "__main__":
    results = search_columbia()
    print(f"\nTotal Columbia records: {len(results)}")
    for row in results[:20]:
        print(row)