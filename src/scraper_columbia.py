import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://clio.columbia.edu"
START_URL = "https://clio.columbia.edu/catalog"

SEARCH_QUERIES = [
    "interview",
    "study time",
    "shopping",
    "oral history",
    "transcript",
    "audio",
    "video",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def extract_results_from_soup(soup, seen_urls):
    datasets = []
    new_count = 0

    result_blocks = (
        soup.select(".document") or
        soup.select("li.document") or
        soup.select("div.document") or
        soup.select("article") or
        soup.select("ol li")
    )

    for block in result_blocks:
        title_link = (
            block.select_one("a.title") or
            block.select_one("h3 a") or
            block.select_one("h2 a") or
            block.select_one("a[href*='/catalog/']")
        )

        if not title_link:
            continue

        title = " ".join(title_link.get_text(" ", strip=True).split())
        if not title:
            continue

        online_link = None

        for a in block.select("a[href]"):
            href = (a.get("href") or "").strip()
            text = " ".join(a.get_text(" ", strip=True).split()).lower()

            if not href:
                continue

            full_href = urljoin(BASE_URL, href)

            if text == "online" or "online" in text:
                online_link = full_href
                break

        if not online_link:
            for a in block.select("a[href]"):
                href = (a.get("href") or "").strip()
                if not href:
                    continue

                full_href = urljoin(BASE_URL, href)
                href_lower = full_href.lower()

                if (
                    "handle.net" in href_lower
                    or "resolver.library.columbia.edu" in href_lower
                    or "doi.org" in href_lower
                ):
                    online_link = full_href
                    break

        if not online_link:
            continue

        if online_link in seen_urls:
            continue

        seen_urls.add(online_link)
        new_count += 1

        datasets.append({
            "id": "",
            "title": title,
            "url": online_link,
            "year": "",
            "description": "",
        })

    return datasets, new_count


def find_next_page_url(soup, current_url):
    # Try common "Next" selectors
    candidates = []

    candidates.extend(soup.select("a[rel='next']"))
    candidates.extend(soup.select("a.next_page"))
    candidates.extend(soup.select("a[aria-label='Next']"))
    candidates.extend(soup.select("a"))

    for a in candidates:
        href = (a.get("href") or "").strip()
        text = " ".join(a.get_text(" ", strip=True).split()).lower()

        if not href:
            continue

        if text in {"next", "next »", "›", "»"} or "next" in text:
            return urljoin(current_url, href)

    return None


def search_columbia(max_pages=20):
    datasets = []
    seen_urls = set()

    for query in SEARCH_QUERIES:
        print(f"Columbia query: {query}")

        params = {
            "q": query,
            "datasource": "catalog",
            "source": "catalog",
            "search_field": "all_fields",
        }

        try:
            r = requests.get(START_URL, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
        except Exception as e:
            print(f"  request failed -> {e}")
            continue

        current_url = r.url
        total_new_for_query = 0
        page_no = 1

        while current_url and page_no <= max_pages:
            try:
                r = requests.get(current_url, headers=HEADERS, timeout=30)
                r.raise_for_status()
            except Exception as e:
                print(f"  page {page_no}: request failed -> {e}")
                break

            soup = BeautifulSoup(r.text, "html.parser")

            page_results, page_new = extract_results_from_soup(soup, seen_urls)
            datasets.extend(page_results)
            total_new_for_query += page_new

            print(f"  page {page_no}: {page_new} new record(s)")

            next_url = find_next_page_url(soup, r.url)
            if not next_url or next_url == current_url:
                break

            current_url = next_url
            page_no += 1

        print(f"  total for query '{query}': {total_new_for_query}")

    return datasets