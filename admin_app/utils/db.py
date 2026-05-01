"""
Unified DB Helper — Hype HR Management

All modules should use THIS file to read/write data.
Reads   → SQLite cache (fast, <1ms)
Writes  → Firebase first, then mirror to SQLite cache
Fallback→ If Firebase write fails, queued locally and retried on next sync

Developed by David | Nexuzy Lab | nexuzylab@gmail.com
"""
from utils.local_cache import get_cache
from utils.firebase_config import get_db
import logging

log = logging.getLogger("db")


def read(collection: str, doc_id: str) -> dict | None:
    """Read single doc — cache first, Firebase fallback."""
    cache = get_cache()
    data  = cache.get(collection, doc_id)
    if data is not None:
        return data
    # Cache miss — fetch from Firebase and store
    try:
        doc = get_db().collection(collection).document(doc_id).get()
        if doc.exists:
            cache.put(collection, doc_id, doc.to_dict())
            return doc.to_dict()
    except Exception as e:
        log.warning(f"[DB] Firebase read miss {collection}/{doc_id}: {e}")
    return None


def read_all(collection: str,
             where_key: str = None,
             where_value = None) -> list[dict]:
    """
    Read all docs in a collection from cache.
    If cache is empty, fetch from Firebase and populate.
    """
    cache = get_cache()
    rows  = cache.get_all(collection, where_key, where_value)
    if rows:
        return rows
    # Cold start — populate from Firebase
    try:
        q = get_db().collection(collection)
        if where_key and where_value is not None:
            q = q.where(where_key, "==", where_value)
        records = []
        for doc in q.stream():
            cache.put(collection, doc.id, doc.to_dict())
            records.append(doc.to_dict())
        return records
    except Exception as e:
        log.warning(f"[DB] Firebase read_all {collection}: {e}")
    return []


def write(collection: str, doc_id: str, data: dict, merge: bool = False):
    """
    Write to Firebase + mirror to cache.
    If Firebase fails, still saves to cache and logs for retry.
    """
    cache = get_cache()
    firebase_ok = False
    try:
        ref = get_db().collection(collection).document(doc_id)
        if merge:
            ref.set(data, merge=True)
            existing = cache.get(collection, doc_id) or {}
            existing.update(data)
            data = existing
        else:
            ref.set(data)
        firebase_ok = True
    except Exception as e:
        log.error(f"[DB] Firebase write failed {collection}/{doc_id}: {e}")
    cache.put(collection, doc_id, data)
    return firebase_ok


def delete(collection: str, doc_id: str):
    """Delete from Firebase + remove from cache."""
    try:
        get_db().collection(collection).document(doc_id).delete()
    except Exception as e:
        log.error(f"[DB] Firebase delete failed {collection}/{doc_id}: {e}")
    get_cache().delete(collection, doc_id)


def update(collection: str, doc_id: str, fields: dict):
    """Partial update (merge) — Firebase + cache."""
    write(collection, doc_id, fields, merge=True)
