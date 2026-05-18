# image_cache.py — Thread-safe in-memory image cache for employee photos
# Prevents re-downloading the same image on every dialog open.
# Developed by David | Nexuzy Lab

import threading
import io
import urllib.request
from PIL import Image, ImageTk

_cache: dict = {}   # url -> PIL.Image (RGB, already thumbnailed)
_lock = threading.Lock()


def get_photo_image(url: str, size=(80, 80), timeout=10) -> ImageTk.PhotoImage | None:
    """
    Returns an ImageTk.PhotoImage for the given URL.
    - Uses in-memory cache so same URL is only downloaded once per session.
    - Returns None on any error (caller should show placeholder).
    """
    if not url:
        return None

    with _lock:
        if url in _cache:
            img = _cache[url].copy()
            img.thumbnail(size, Image.LANCZOS)
            return ImageTk.PhotoImage(img)

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "HypeHR-Admin/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read()

        img = Image.open(io.BytesIO(data)).convert("RGB")

        with _lock:
            _cache[url] = img.copy()  # Store original, not thumbnailed

        img.thumbnail(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)

    except Exception:
        return None


def clear_url(url: str):
    """Remove a URL from cache (call after uploading a new photo)."""
    with _lock:
        _cache.pop(url, None)


def clear_all():
    """Clear entire cache."""
    with _lock:
        _cache.clear()
