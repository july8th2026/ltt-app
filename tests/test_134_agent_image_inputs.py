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
    from apps.taoanh.jobs import _load_canvas_references
    first = "agent-assets/u1/first.png"
    second = "taoanh/u1/job/second.png"
    storage.put(first, io.BytesIO(_png("red")), "image/png")
    storage.put(second, io.BytesIO(_png("blue")), "image/png")
    refs = _load_canvas_references({
        "image_key": first, "image_keys": [second, first],
    }, "u1", storage)
    assert [ref["data"] for ref in refs] == [_png("red"), _png("blue")]
    assert all(ref["mime"] == "image/png" and ref["role"] == "reference" for ref in refs)
    with pytest.raises(ValueError, match="không thuộc"):
        _load_canvas_references({"image_key": first}, "u2", storage)
    with pytest.raises(ValueError, match="không còn tồn tại"):
        _load_canvas_references({"image_key": "agent-assets/u1/missing.png"}, "u1", storage)


def test_worker_sends_canvas_references_to_gemini(storage, monkeypatch):
    from apps.taoanh import jobs
    first = "agent-assets/u1/first.png"
    second = "agent-assets/u1/second.png"
    storage.put(first, io.BytesIO(_png("red")), "image/png")
    storage.put(second, io.BytesIO(_png("blue")), "image/png")
    monkeypatch.setattr(jobs, "_lay_key", lambda _model: ("test-key", None))
    seen = {}

    def fake_call(prompt, aspect, key, model, references):
        seen.update(prompt=prompt, references=references)
        return _png("green")

    monkeypatch.setattr(jobs, "_goi_gemini", fake_call)
    result = jobs.handle({
        "owner_id": "u1", "prompt": "combine wardrobe, model and location",
        "image_key": first, "image_keys": [second], "count": 1,
    })
    assert len(seen["references"]) == 2
    assert "Input image roles in order: reference, reference" in seen["prompt"]
    assert storage.exists(result["image_keys"][0])
