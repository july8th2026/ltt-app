"""
Tải ảnh thumbnail từ URL về thư mục temp.
Trả về đường dẫn local hoặc None nếu URL rỗng.
"""

import os
import re
import hashlib

import requests

_THUMB_DIR = "temp_thumbnails"
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


def fetch(url: str, log=None) -> str | None:
    """
    Tải thumbnail từ URL.

    - URL rỗng → trả về None (FB dùng thumbnail tự động)
    - URL là đường dẫn file local → trả về ngay
    - URL bắt đầu http(s) → tải về temp_thumbnails/
    """
    _log = log or (lambda m: None)

    if not url or not url.strip():
        return None

    url = url.strip()

    # File local
    if os.path.exists(url):
        return url

    if not url.startswith("http"):
        _log(f"Thumbnail URL không hợp lệ: {url}")
        return None

    os.makedirs(_THUMB_DIR, exist_ok=True)

    # Tên file theo hash URL → cache
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    ext = _guess_ext(url)
    dest = os.path.join(_THUMB_DIR, f"thumb_{url_hash}{ext}")

    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        _log(f"Dùng thumbnail cache: {os.path.basename(dest)}")
        return dest

    try:
        _log(f"Tải thumbnail: {url[:60]}...")
        resp = requests.get(url, timeout=30, stream=True)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        _log(f"Thumbnail OK: {os.path.basename(dest)}")
        return dest
    except Exception as e:
        _log(f"Lỗi tải thumbnail: {e} — sẽ dùng thumbnail tự động")
        if os.path.exists(dest):
            os.remove(dest)
        return None


def _guess_ext(url: str) -> str:
    path = url.split("?")[0].split("#")[0]
    ext  = os.path.splitext(path)[1].lower()
    return ext if ext in _IMAGE_EXTS else ".jpg"


def cleanup_old(max_files: int = 50):
    """Xóa thumbnail cũ nếu vượt quá max_files."""
    if not os.path.isdir(_THUMB_DIR):
        return
    files = sorted(
        [os.path.join(_THUMB_DIR, f) for f in os.listdir(_THUMB_DIR)],
        key=os.path.getmtime
    )
    for f in files[:-max_files]:
        try:
            os.remove(f)
        except Exception:
            pass
