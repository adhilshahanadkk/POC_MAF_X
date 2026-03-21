import schedule
import time
import threading
from services.rag_updater import sync_wordpress

# Module-level state to prevent duplicate threads
_lock = threading.Lock()
_started = False
_syncing = False  # Guard to prevent overlapping syncs
_vectorstore_ref = {"store": None}  # Mutable ref so thread picks up updates


def start_scheduler(vectorstore):
    """
    Start (or update) the WordPress sync scheduler.
    Safe to call multiple times — only one thread ever runs.
    Polls WordPress every 30 seconds for near-real-time sync.
    """
    global _started

    _vectorstore_ref["store"] = vectorstore  # Update the reference

    with _lock:
        if _started:
            print("[Scheduler] Already running — updated vectorstore reference")
            return
        _started = True

    def run_sync():
        global _syncing
        if _syncing:
            return  # Skip if a previous sync is still running
        _syncing = True
        store = _vectorstore_ref["store"]
        if store is None:
            print("[Scheduler] No vectorstore available — skipping sync")
            _syncing = False
            return
        try:
            sync_wordpress(store)
        except Exception as e:
            print(f"[Scheduler] Error: {e}")
        finally:
            _syncing = False

    def loop():
        run_sync()                              # Run immediately at startup
        schedule.every(30).seconds.do(run_sync)  # Then every 30 seconds
        while True:
            schedule.run_pending()
            time.sleep(5)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    print("[Scheduler] ✅ Sync scheduler started — every 30 seconds")