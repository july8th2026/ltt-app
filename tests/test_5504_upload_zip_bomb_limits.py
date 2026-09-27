"""tests/test_5504_upload_zip_bomb_limits.py — ba lop chan zip bomb."""
from __future__ import annotations

import io
import zipfile

import pytest


def test_too_many_entries_is_rejected():
    from apps.prompt_ai_ommi.services import upload_zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in range(upload_zip.MAX_ENTRIES + 1):
            zf.writestr(f"img_{i}.png", b"\x89PNG")
    with pytest.raises(upload_zip.ZipImportError, match="so luong tep"):
        list(upload_zip.iter_safe_entries(buf.getvalue()))


def test_single_entry_over_the_uncompressed_cap_is_rejected():
    from apps.prompt_ai_ommi.services import upload_zip
    huge = b"\x00" * (upload_zip.MAX_ENTRY_UNCOMPRESSED + 1)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("big.png", huge)
    with pytest.raises(upload_zip.ZipImportError, match="qua lon"):
        list(upload_zip.iter_safe_entries(buf.getvalue()))


def test_suspicious_compression_ratio_is_rejected():
    """Zip bomb kinh điển: rất nhỏ khi nén, khổng lồ khi giải nén."""
    from apps.prompt_ai_ommi.services import upload_zip
    payload = b"\x00" * (2 * 1024 * 1024)   # nén cực tốt vì toàn số 0
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("suspicious.png", payload)
    with pytest.raises(upload_zip.ZipImportError, match="ti le nen"):
        list(upload_zip.iter_safe_entries(buf.getvalue()))
