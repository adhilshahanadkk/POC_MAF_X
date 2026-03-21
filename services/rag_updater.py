import os
import json
import requests
import tempfile
from datetime import datetime, timezone
from services.wordpress_fetcher import fetch_posts, fetch_pages, fetch_pdfs
from langchain_community.document_loaders import PyPDFLoader


def _ingest_timestamp():
    return datetime.now(timezone.utc).strftime("%d %b %Y, %I:%M %p UTC")

LAST_SYNC_FILE = os.path.join("data", "last_sync.json")


def load_last_sync():
    if not os.path.exists(LAST_SYNC_FILE):
        print("[Updater] First run — full sync")
        return None
    try:
        with open(LAST_SYNC_FILE, "r") as f:
            ts = json.load(f).get("last_sync")
            print(f"[Updater] Last sync: {ts}")
            return ts
    except Exception:
        return None


def save_last_sync():
    os.makedirs("data", exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    with open(LAST_SYNC_FILE, "w") as f:
        json.dump({"last_sync": now}, f)
    print(f"[Updater] Sync time saved: {now}")


def add_to_chromadb(vectorstore, doc):
    doc_id = f"wp_{doc['type']}_{doc['id']}"

    # Delete old version if exists
    try:
        vectorstore.delete(ids=[doc_id])
    except Exception:
        pass

    # Add new version — use keys that rag_chain.py expects for source display
    vectorstore.add_texts(
        texts=[doc["content"]],
        metadatas=[{
            "doc_name":     doc["title"],
            "source":       doc["link"],
            "page":         "WordPress",
            "chunk_id":     f"wp_{doc['type']}_{doc['id']}",
            "ingest_time":  _ingest_timestamp(),
            "type":         doc["type"]
        }],
        ids=[doc_id]
    )
    print(f"[Updater] ✅ Added: {doc['title']}")


def sync_wordpress(vectorstore):
    print("\n[Updater] ══ WordPress Sync Started ══")
    last_sync = load_last_sync()
    total     = 0

    # Sync Posts
    for post in fetch_posts(modified_after=last_sync):
        if post["content"].strip():
            add_to_chromadb(vectorstore, post)
            total += 1

    # Sync Pages
    for page in fetch_pages(modified_after=last_sync):
        if page["content"].strip():
            add_to_chromadb(vectorstore, page)
            total += 1

    # Sync PDFs
    for pdf in fetch_pdfs(modified_after=last_sync):
        try:
            response = requests.get(pdf["source_url"], timeout=30)
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name

            loader = PyPDFLoader(tmp_path)
            pages = loader.load()
            for idx, p in enumerate(pages):
                vectorstore.add_texts(
                    texts=[p.page_content],
                    metadatas=[{
                        "doc_name":    pdf["title"],
                        "source":      pdf["source_url"],
                        "page":        str(idx + 1),
                        "chunk_id":    f"wp_pdf_{pdf['id']}_p{idx}",
                        "ingest_time": _ingest_timestamp()
                    }]
                )
            os.unlink(tmp_path)
            print(f"[Updater] ✅ PDF added: {pdf['title']}")
            total += 1

        except Exception as e:
            print(f"[Updater] ❌ PDF failed: {e}")

    save_last_sync()
    print(f"[Updater] ══ Sync Complete — {total} documents updated ══\n")
    return total