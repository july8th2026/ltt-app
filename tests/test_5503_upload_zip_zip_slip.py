"""tests/test_5503_upload_zip_zip_slip.py — chan zip-slip, tu choi CA zip."""
from __future__ import annotations

import io
import zipfile

import pytest


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_zip_slip_entry_is_rejected_and_nothing_is_written(tmp_path):
    from apps.prompt_ai_ommi.services import upload_zip

    payload = _zip_bytes({
        "ok.png": b"\x89PNG" + b"\x00" * 40,
        "../../thoat.png": b"\x89PNG" + b"\x00" * 40,
    })
    dest = tmp_path / "extract"
    with pytest.raises(upload_zip.ZipImportError, match="zip-slip"):
        list(upload_zip.iter_safe_entries(payload))
    assert not dest.exists() or list(dest.iterdir()) == []
