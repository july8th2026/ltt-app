"""tests/test_5508_thumbnail_generation.py."""
from __future__ import annotations

import io

import pytest
from PIL import Image


@pytest.fixture()
def storage(tmp_path):
    import platform_core.storage as storage_mod
    s = storage_mod.LocalStorage(str(tmp_path / "files"))
    yield s


def _png_bytes(width, height):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(200, 50, 50)).save(buf, format="PNG")
    return buf.getvalue()


def test_thumbnail_is_stored_under_a_different_key_and_fits_the_box(storage):
    from apps.prompt_ai_ommi.services import upload_zip
    original_key = "ommi/o1/r1/big.png"
    data = _png_bytes(1600, 900)
    storage.put(original_key, io.BytesIO(data), content_type="image/png")

    thumb_key = upload_zip.make_thumbnail(storage, original_key=original_key,
                                          data=data)

    assert thumb_key != original_key
    assert thumb_key.endswith("__thumb.jpg")
    assert storage.exists(original_key)
    assert storage.exists(thumb_key)

    with storage.open(original_key) as fh:
        original_still_full_size = Image.open(fh)
        original_still_full_size.load()
        assert original_still_full_size.size == (1600, 900)

    with storage.open(thumb_key) as fh:
        thumb = Image.open(fh)
        thumb.load()
        assert thumb.width <= 320 and thumb.height <= 320
        assert thumb.format == "JPEG"
