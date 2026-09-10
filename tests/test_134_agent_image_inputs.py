"""Canvas Image nodes accept owned scalar and collection image references."""
from __future__ import annotations

import io

import pytest
from PIL import Image


def _png(color: str = "red") -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (64, 64), color).save(output, "PNG")
    return output.getvalue()


@pytest.fixture()
def storage(tmp_path):
    from platform_core.storage import LocalStorage, set_storage
    current = LocalStorage(str(tmp_path / "storage"))
    set_storage(current)
    try:
        yield current
    finally:
        set_storage(None)


def test_image_tools_expose_typed_scalar_and_collection_inputs():
    from apps.taoanh.manifest import MANIFEST
    for name in ("image.generate", "image.batch_generate"):
        spec = next(tool for tool in MANIFEST.tools if tool.name == name)
        assert spec.params_schema["image_key"]["type"] == "image"
        assert spec.params_schema["image_keys"]["type"] == "image[]"


def test_canvas_references_preserve_order_dedupe_and_verify_owner(storage):
    """🔴 Viết lại 09/09/2026 (pha 06.3). Hàm đổi tên và đổi KIỂU TRẢ VỀ —
    `_load_canvas_references` trả **bytes** cho đường nhét ảnh inline; đường
    LTT_IMAGE chỉ cần **khoá**, vì máy B tự tải bằng vé presigned (Q102).

    ⭐ Ba mệnh đề nó canh thì y nguyên: giữ thứ tự · khử trùng lặp · ảnh phải
       thuộc đúng chủ. Và trần số ảnh nay là năng lực KHAI BÁO của model.
    """
    from apps.taoanh.jobs import _MAX_REFS, _canvas_reference_keys
    first = "agent-assets/u1/first.png"
    second = "taoanh/u1/job/second.png"
    storage.put(first, io.BytesIO(_png("red")), "image/png")
    storage.put(second, io.BytesIO(_png("blue")), "image/png")

    keys = _canvas_reference_keys(
        {"image_key": first, "image_keys": [second, first]}, "u1", storage)
    assert keys == [first, second], "giu thu tu va khu trung lap"

    with pytest.raises(ValueError, match="không thuộc"):
        _canvas_reference_keys({"image_key": first}, "u2", storage)
    with pytest.raises(ValueError, match="không còn tồn tại"):
        _canvas_reference_keys(
            {"image_key": "agent-assets/u1/missing.png"}, "u1", storage)

    # ⛔ Trần là `max_refs` mà `hidream-o1` KHAI, không phải con số 8 của động cơ cũ.
    du = [f"agent-assets/u1/x{i}.png" for i in range(_MAX_REFS + 1)]
    for k in du:
        storage.put(k, io.BytesIO(_png("red")), "image/png")
    with pytest.raises(ValueError, match="tối đa"):
        _canvas_reference_keys({"image_keys": du}, "u1", storage)


def test_worker_gui_anh_tham_chieu_Canvas_bang_KHOA(storage, monkeypatch):
    """🔴 Thay `test_worker_sends_canvas_references_to_gemini`.

    Bất biến còn sống: **cả hai** ảnh Canvas tới được model, đúng thứ tự. Cơ chế
    đổi hẳn — trước là bytes inline kèm một câu *"Input image roles in order:
    …"* trong prompt; nay là danh sách khoá, và vai trò do `mode` nói.
    """
    from apps.taoanh import jobs

    first = "agent-assets/u1/first.png"
    second = "agent-assets/u1/second.png"
    storage.put(first, io.BytesIO(_png("red")), "image/png")
    storage.put(second, io.BytesIO(_png("blue")), "image/png")

    from tests.gia_dieu_phoi_anh import tiem
    gia = tiem(monkeypatch, jobs)

    result = jobs.handle({
        "owner_id": "u1", "prompt": "combine wardrobe, model and location",
        "image_key": first, "image_keys": [second], "count": 1,
        "edit_mode": "edit",
    })
    assert gia.da_goi[0]["ref_keys"] == [first, second]
    assert gia.da_goi[0]["mode"] == "edit"
    assert storage.exists(result["image_keys"][0])
