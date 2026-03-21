import requests
import os
import time
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

WP_URL          = os.getenv("WP_URL", "").rstrip("/")
WP_USERNAME     = os.getenv("WP_USERNAME", "")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "")

AUTH     = (WP_USERNAME, WP_APP_PASSWORD)
HEADERS  = {"Accept": "application/json"}
PER_PAGE = 100


def html_to_text(html):
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def fetch_all(endpoint, modified_after=None):
    all_items = []
    page      = 1

    while True:
        params = {"per_page": PER_PAGE, "page": page, "status": "publish"}
        if modified_after:
            params["modified_after"] = modified_after

        try:
            response = requests.get(
                f"{WP_URL}/wp-json/wp/v2/{endpoint}",
                headers=HEADERS, auth=AUTH,
                params=params, timeout=15
            )

            if response.status_code == 400:
                break
            if response.status_code != 200:
                print(f"[Fetcher] Error {response.status_code} on {endpoint}")
                break

            items = response.json()
            if not items:
                break

            all_items.extend(items)
            print(f"[Fetcher] {endpoint} page {page} → {len(items)} items")

            if len(items) < PER_PAGE:
                break

            page += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"[Fetcher] Error: {e}")
            break

    return all_items


def convert_to_document(item):
    return {
        "id":       item.get("id"),
        "title":    html_to_text(item.get("title",   {}).get("rendered", "")),
        "content":  html_to_text(item.get("content", {}).get("rendered", "")),
        "link":     item.get("link", ""),
        "modified": item.get("modified", ""),
        "type":     item.get("type", "post")
    }


def fetch_posts(modified_after=None):
    items = fetch_all("posts", modified_after)
    docs  = [convert_to_document(i) for i in items]
    print(f"[Fetcher] Posts fetched: {len(docs)}")
    return docs


def fetch_pages(modified_after=None):
    items = fetch_all("pages", modified_after)
    docs  = [convert_to_document(i) for i in items]
    print(f"[Fetcher] Pages fetched: {len(docs)}")
    return docs


def fetch_pdfs(modified_after=None):
    all_items = []
    page = 1

    while True:
        params = {
            "mime_type": "application/pdf",
            "per_page": PER_PAGE,
            "page": page,
        }
        if modified_after:
            params["modified_after"] = modified_after

        try:
            response = requests.get(
                f"{WP_URL}/wp-json/wp/v2/media",
                headers=HEADERS, auth=AUTH,
                params=params, timeout=15
            )
            if response.status_code == 400:
                break
            if response.status_code != 200:
                print(f"[Fetcher] Error {response.status_code} on media/pdf")
                break

            items = response.json()
            if not items:
                break

            for i in items:
                if i.get("source_url", "").lower().endswith(".pdf"):
                    all_items.append({
                        "id":         i["id"],
                        "title":      i["title"]["rendered"],
                        "source_url": i["source_url"],
                        "modified":   i["modified"]
                    })

            print(f"[Fetcher] media/pdf page {page} → {len(items)} items")

            if len(items) < PER_PAGE:
                break

            page += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"[Fetcher] PDF error: {e}")
            break

    print(f"[Fetcher] PDFs fetched: {len(all_items)}")
    return all_items


def test_connection():
    if not WP_URL:
        print("[Fetcher] ERROR: WP_URL not set in .env")
        return False
    try:
        response = requests.get(
            f"{WP_URL}/wp-json/wp/v2/posts?per_page=1",
            headers=HEADERS, auth=AUTH, timeout=10
        )
        if response.status_code == 200:
            print(f"[Fetcher] ✅ WordPress connected: {WP_URL}")
            return True
        else:
            print(f"[Fetcher] ❌ Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"[Fetcher] ❌ Cannot connect: {e}")
        return False