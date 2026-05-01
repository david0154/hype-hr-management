"""
Local SQLite Cache — Hype HR Management

FIX for slow Firebase on Windows Python app:
  - All read operations check SQLite first (instant, <1ms)
  - Firebase is only used for writes and background sync
  - Sync runs in a background thread every SYNC_INTERVAL seconds
  - On write: saves to both Firebase AND SQLite immediately

Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
import sqlite3, threading, time, json, os, logging
from pathlib import Path

log = logging.getLogger("local_cache")

# Cache DB stored next to the executable / script
DB_PATH       = Path(os.path.dirname(os.path.abspath(__file__))).parent / "hype_cache.db"
SYNC_INTERVAL = 120   # seconds between full background syncs from Firebase


# ──────────────────────────────────────────────────────────────────
class LocalCache:
    """
    Drop-in SQLite cache for Firestore collections.

    Usage:
        cache = LocalCache()
        cache.put("employees", "EMP-0001", {...})
        rec  = cache.get("employees", "EMP-0001")    # dict or None
        all_ = cache.get_all("employees")             # list[dict]
        cache.delete("employees", "EMP-0001")
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                collection  TEXT NOT NULL,
                doc_id      TEXT NOT NULL,
                data        TEXT NOT NULL,
                synced_at   REAL DEFAULT 0,
                PRIMARY KEY (collection, doc_id)
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_col ON cache(collection)
        """)
        self._conn.commit()

    # ─ CRUD ─────────────────────────────────────────────────────────
    def put(self, collection: str, doc_id: str, data: dict):
        with self._lock:
            self._conn.execute("""
                INSERT OR REPLACE INTO cache (collection, doc_id, data, synced_at)
                VALUES (?, ?, ?, ?)
            """, (collection, doc_id, json.dumps(data, default=str), time.time()))
            self._conn.commit()

    def put_many(self, collection: str, records: list[tuple]):
        """records = [(doc_id, data_dict), ...]"""
        with self._lock:
            now = time.time()
            self._conn.executemany("""
                INSERT OR REPLACE INTO cache (collection, doc_id, data, synced_at)
                VALUES (?, ?, ?, ?)
            """, [(collection, doc_id, json.dumps(data, default=str), now)
                  for doc_id, data in records])
            self._conn.commit()

    def get(self, collection: str, doc_id: str) -> dict | None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT data FROM cache WHERE collection=? AND doc_id=?",
                (collection, doc_id))
            row = cur.fetchone()
            return json.loads(row["data"]) if row else None

    def get_all(self, collection: str,
                where_key: str = None,
                where_value=None) -> list[dict]:
        """Return all docs in collection, optionally filtered by one field."""
        with self._lock:
            cur = self._conn.execute(
                "SELECT data FROM cache WHERE collection=?", (collection,))
            rows = [json.loads(r["data"]) for r in cur.fetchall()]
        if where_key and where_value is not None:
            rows = [r for r in rows if r.get(where_key) == where_value]
        return rows

    def delete(self, collection: str, doc_id: str):
        with self._lock:
            self._conn.execute(
                "DELETE FROM cache WHERE collection=? AND doc_id=?",
                (collection, doc_id))
            self._conn.commit()

    def clear_collection(self, collection: str):
        with self._lock:
            self._conn.execute(
                "DELETE FROM cache WHERE collection=?", (collection,))
            self._conn.commit()

    def last_sync(self, collection: str) -> float:
        with self._lock:
            cur = self._conn.execute(
                "SELECT MAX(synced_at) as t FROM cache WHERE collection=?",
                (collection,))
            row = cur.fetchone()
            return row["t"] or 0.0


# ─ Singleton ───────────────────────────────────────────────────────────────
_cache_instance: LocalCache | None = None

def get_cache() -> LocalCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LocalCache()
    return _cache_instance


# ─ Background Sync Thread ──────────────────────────────────────────────────
_sync_thread: threading.Thread | None = None
_stop_sync    = threading.Event()

COLLECTIONS_TO_SYNC = [
    "employees",
    "attendance_logs",
    "sessions",
    "salary",
    "admin_users",
    "settings",
]


def _sync_worker():
    """Pull all documents from Firebase into SQLite every SYNC_INTERVAL seconds."""
    from utils.firebase_config import get_db
    log.info("[Sync] Background sync thread started")
    while not _stop_sync.is_set():
        try:
            db    = get_db()
            cache = get_cache()
            for col in COLLECTIONS_TO_SYNC:
                records = []
                for doc in db.collection(col).stream():
                    records.append((doc.id, doc.to_dict()))
                if records:
                    cache.put_many(col, records)
                    log.debug(f"[Sync] {col}: {len(records)} docs cached")
        except Exception as e:
            log.warning(f"[Sync] error: {e}")
        _stop_sync.wait(SYNC_INTERVAL)
    log.info("[Sync] stopped")


def start_background_sync():
    global _sync_thread
    if _sync_thread and _sync_thread.is_alive(): return
    _stop_sync.clear()
    _sync_thread = threading.Thread(target=_sync_worker, daemon=True, name="FirebaseSync")
    _sync_thread.start()


def stop_background_sync():
    _stop_sync.set()
