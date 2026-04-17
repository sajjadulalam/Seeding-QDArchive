"""
scraper_columbia.py
-------------------
Searches and harvests dataset records from Columbia University Academic Commons
https://academiccommons.columbia.edu

Search strategy (mirrors scraper_sada.py):
  1. For each query in SEARCH_QUERIES, call the AC search endpoint with
     f[genre_ssim][]=Dataset to filter to datasets only.
  2. For each result, fetch the individual item page to extract full metadata
     (title, description, authors, keywords, licenses, DOI, year, language).

Output dict shape exactly matches scraper_sada.py so main.py's
process_record() works without any changes.

Requires these two additions to main.py (already applied in the
accompanying main.py):

    # REPOSITORY_REGISTRY:
    "Columbia": (4, "https://academiccommons.columbia.edu", "columbia"),

    # main():
    from scraper_columbia import search_columbia
    columbia_records = search_columbia()
    for record in columbia_records:
        process_record(record, "Columbia")
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL   = "https://academiccommons.columbia.edu"
SEARCH_URL = f"{BASE_URL}/catalog"

# Search terms – server-side filtering, same pattern as SADA's SEARCH_QUERIES
SEARCH_QUERIES = [
    "Bank",
    "University",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; qdarchive-bot/1.0)"}

# Polite delay between requests (seconds)
REQUEST_DELAY = 0.3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean(text: str) -> str:
    return " ".join((text or "").split()).strip()


def _extract_year(text: str) -> str:
    m = re.search(r"\b(19|20)\d{2}\b", text or "")
    return m.group(0) if m else ""


def _fetch_item_detail(session: requests.Session, item_url: str) -> dict:
    """
    Fetch an individual Academic Commons item page and extract full metadata:
      title, description, year, doi, language,
      authors  → list[{"name": ..., "role": "AUTHOR"}]
      keywords → list[str]
      licenses → list[str]
    """
    detail = {
        "title":       "",
        "description": "",
        "year":        "",
        "doi":         "",
        "language":    "",
        "authors":     [],
        "keywords":    [],
        "licenses":    [],
    }

    try:
        r = session.get(item_url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"    Columbia detail fetch failed {item_url}: {e}")
        return detail

    soup = BeautifulSoup(r.text, "html.parser")

    # ------------------------------------------------------------------ title
    h1 = soup.select_one("h1.document-title") or soup.select_one("h1")
    if h1:
        detail["title"] = _clean(h1.get_text(" ", strip=True))

    # --------------------------------------------------------------- description
    for sel in [".description", ".abstract", '[class*="description"]',
                '[class*="abstract"]', "dd.blacklight-description_tesim"]:
        el = soup.select_one(sel)
        if el:
            detail["description"] = _clean(el.get_text(" ", strip=True))
            break

    # --------------------------------------------------------------- year / date
    for sel in ["dd.blacklight-date_ssim", "dd.blacklight-pub_date_isi",
                '[class*="date"]', "time"]:
        el = soup.select_one(sel)
        if el:
            year = _extract_year(el.get_text(" ", strip=True))
            if year:
                detail["year"] = year
                break
    if not detail["year"]:
        detail["year"] = _extract_year(soup.get_text(" ", strip=True))

    # -------------------------------------------------------------------- doi
    for a in soup.select("a[href*='doi.org']"):
        detail["doi"] = (a.get("href") or "").strip()
        break
    if not detail["doi"]:
        # Also look for DOI in metadata dt/dd pairs
        for dt in soup.select("dt"):
            if "doi" in dt.get_text().lower():
                dd = dt.find_next_sibling("dd")
                if dd:
                    text = _clean(dd.get_text(" ", strip=True))
                    if text:
                        detail["doi"] = text
                        break

    # ---------------------------------------------------------------- language
    for sel in ["dd.blacklight-language_ssim", '[class*="language"]']:
        el = soup.select_one(sel)
        if el:
            detail["language"] = _clean(el.get_text(" ", strip=True))
            break

    # ----------------------------------------------------------------- authors
    authors: list[dict] = []
    seen_names: set[str] = set()

    # AC item pages render authors in dl/dt/dd metadata blocks
    author_labels = re.compile(
        r"(author|creator|contributor|researcher|principal investigator)", re.I
    )

    for dt in soup.select("dt"):
        label = _clean(dt.get_text(" ", strip=True)).lower()
        if not author_labels.search(label):
            continue
        dd = dt.find_next_sibling("dd")
        if not dd:
            continue
        for name_el in dd.select("a, span") or [dd]:
            name = _clean(name_el.get_text(" ", strip=True))
            if name and name not in seen_names:
                seen_names.add(name)
                role = "CONTRIBUTOR" if "contributor" in label else "AUTHOR"
                authors.append({"name": name, "role": role})

    # Fallback: blacklight-specific author classes
    if not authors:
        for sel in ["dd.blacklight-author_ssim", "dd.blacklight-creator_ssim",
                    '[class*="author"]', '[class*="creator"]']:
            for el in soup.select(sel):
                for a_tag in el.select("a") or [el]:
                    name = _clean(a_tag.get_text(" ", strip=True))
                    if name and name not in seen_names:
                        seen_names.add(name)
                        authors.append({"name": name, "role": "AUTHOR"})

    detail["authors"] = authors

    # ---------------------------------------------------------------- keywords
    keywords: list[str] = []
    seen_kw: set[str] = set()

    keyword_labels = re.compile(r"(keyword|subject|tag|topic)", re.I)

    for dt in soup.select("dt"):
        label = _clean(dt.get_text(" ", strip=True)).lower()
        if not keyword_labels.search(label):
            continue
        dd = dt.find_next_sibling("dd")
        if not dd:
            continue
        raw = dd.get_text(" | ", strip=True)
        for kw in re.split(r"[,;|]+", raw):
            kw = _clean(kw)
            if kw and kw not in seen_kw:
                seen_kw.add(kw)
                keywords.append(kw)

    if not keywords:
        for sel in ["dd.blacklight-subject_ssim", "dd.blacklight-keyword_ssim",
                    '[class*="subject"]', '[class*="keyword"]']:
            for el in soup.select(sel):
                for a_tag in el.select("a") or [el]:
                    kw = _clean(a_tag.get_text(" ", strip=True))
                    if kw and kw not in seen_kw:
                        seen_kw.add(kw)
                        keywords.append(kw)

    detail["keywords"] = keywords

    # ---------------------------------------------------------------- licenses
    licenses: list[str] = []
    seen_lic: set[str] = set()

    license_labels = re.compile(r"(licen[sc]e|rights|terms)", re.I)

    for dt in soup.select("dt"):
        label = _clean(dt.get_text(" ", strip=True)).lower()
        if not license_labels.search(label):
            continue
        dd = dt.find_next_sibling("dd")
        if not dd:
            continue
        lic = _clean(dd.get_text(" ", strip=True))
        if lic and lic not in seen_lic:
            seen_lic.add(lic)
            licenses.append(lic)

    if not licenses:
        for sel in ["dd.blacklight-rights_ssim", '[href*="creativecommons"]',
                    '[class*="license"]', '[class*="rights"]']:
            for el in soup.select(sel):
                lic = _clean(el.get_text(" ", strip=True)) or (el.get("href") or "")
                if lic and lic not in seen_lic:
                    seen_lic.add(lic)
                    licenses.append(lic)

    detail["licenses"] = licenses
    return detail


# ---------------------------------------------------------------------------
# Search result page parser
# ---------------------------------------------------------------------------

def _parse_search_results(soup: BeautifulSoup, page_url: str) -> list[dict]:
    """
    Parse one search results page and return a list of
    {"id": str, "url": str, "title": str} dicts for each hit.
    Academic Commons uses Blacklight, so items are in <article> or <div>
    elements with data-document-id attributes, or plain <a> links to /doi/...
    """
    items: list[dict] = []
    seen: set[str] = set()

    # Primary: Blacklight document containers carry data-document-id
    for article in soup.select("[data-document-id]"):
        doc_id = article.get("data-document-id", "").strip()
        # Find the title link within
        a = article.select_one("h3 a, h2 a, .document-title a, a.title")
        if not a:
            a = article.select_one("a[href*='/doi/']")
        if not a:
            continue
        href  = (a.get("href") or "").strip()
        title = _clean(a.get_text(" ", strip=True))
        if not href:
            continue
        full_url = urljoin(BASE_URL, href)
        record_id = doc_id or re.sub(r"[^A-Za-z0-9\-]", "_",
                                      href.rstrip("/").split("/")[-1])
        if record_id in seen:
            continue
        seen.add(record_id)
        items.append({"id": record_id, "url": full_url, "title": title})

    # Fallback: any link to /doi/ on the page
    if not items:
        for a in soup.select("a[href*='/doi/']"):
            href  = (a.get("href") or "").strip()
            title = _clean(a.get_text(" ", strip=True))
            if not href:
                continue
            full_url  = urljoin(BASE_URL, href)
            record_id = re.sub(r"[^A-Za-z0-9\-]", "_",
                                href.rstrip("/").split("/")[-1])
            if record_id in seen:
                continue
            seen.add(record_id)
            items.append({"id": record_id, "url": full_url, "title": title})

    return items


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def search_columbia(rows: int | None = None,
                    per_page: int = 20,
                    max_pages: int = 100) -> list[dict]:
    """
    Search Columbia University Academic Commons for each query in
    SEARCH_QUERIES, fetch full metadata for each result, and return a list
    of record dicts compatible with main.py's process_record().

    Parameters
    ----------
    rows      : Maximum total records to return across all queries. None = no limit.
    per_page  : Results per search page (max 100 on AC).
    max_pages : Safety cap on pages followed per query.
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    datasets:  list[dict] = []
    seen_ids:  set[str]   = set()

    for query in SEARCH_QUERIES:
        print(f"Columbia query: {query!r}")

        for page in range(1, max_pages + 1):
            params = {
                "q":                  query,
                "per_page":           per_page,
                "page":               page,
                "f[genre_ssim][]":    "Dataset",
            }
            search_page_url = f"{SEARCH_URL}?{urlencode(params)}"

            try:
                r = session.get(SEARCH_URL, params=params, timeout=30)
                r.raise_for_status()
            except Exception as e:
                print(f"  Columbia search request failed (page {page}): {e}")
                break

            soup = BeautifulSoup(r.text, "html.parser")
            hits = _parse_search_results(soup, r.url)

            page_new = 0
            for hit in hits:
                record_id = hit["id"]
                if record_id in seen_ids:
                    continue
                seen_ids.add(record_id)
                page_new += 1

                # Fetch the full item detail page
                detail = _fetch_item_detail(session, hit["url"])
                time.sleep(REQUEST_DELAY)

                datasets.append({
                    "id":          record_id,
                    "title":       detail["title"] or hit["title"],
                    "url":         hit["url"],
                    "year":        detail["year"],
                    "description": detail["description"],
                    "doi":         detail["doi"],
                    "language":    detail["language"],
                    "license":     detail["licenses"][0] if detail["licenses"] else "",
                    "persons":     detail["authors"],
                    "keywords":    detail["keywords"],
                    "licenses":    detail["licenses"],
                })

                if rows is not None and len(datasets) >= rows:
                    return datasets

            print(f"  page {page}: {page_new} new records")

            if page_new == 0:
                break  # No new results on this page – move to next query

    return datasets


# ---------------------------------------------------------------------------
# Standalone smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    results = search_columbia(rows=5)
    print(f"\nTotal Columbia records: {len(results)}")
    for row in results[:10]:
        print(
            f"  [{row['id']}] {row['title'][:70]}\n"
            f"    doi={row['doi']}  year={row['year']}\n"
            f"    persons={len(row['persons'])}  "
            f"keywords={len(row['keywords'])}  "
            f"license={row['license'][:50]}"
        )