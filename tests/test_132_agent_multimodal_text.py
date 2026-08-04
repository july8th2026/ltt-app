"""Canvas Text đa phương thức: ảnh/bộ ảnh -> phân tích văn bản."""
from __future__ import annotations

import base64
import io
import sys
from types import SimpleNamespace

import pytest
from PIL import Image


def _png(color=(30, 90, 180)) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (32, 24), color).save(output, "PNG")
    return output.getvalue()


def test_text_generate_declares_single_and_batch_image_inputs():
    from platform_core.agent.tools import discover_tools, validate_tool_params
    spec = discover_tools()["text.generate"]
    assert spec.params_schema["image_key"]["type"] == "image"
    assert spec.params_schema["image_keys"]["type"] == "image[]"
    assert spec.params_schema["source_text"]["type"] == "text"
    assert spec.params_schema["video_key"]["type"] == "video"
    assert validate_tool_params("text.generate", {
        "prompt": "Phân tích bố cục", "image_key": "agent-assets/u1/a.png",
    })["image_key"] == "agent-assets/u1/a.png"


def test_uploaded_asset_source_is_a_storage_locator_not_an_artifact_input():
    from platform_core.agent.validator import validate_plan
    plan = {"version": 1, "goal": "Phân tích ảnh", "budget_max_credit": 20,
            "steps": [
                {"id": "source", "tool": "asset.image", "after": [], "fanout": 1,
                 "max_retry": 0, "on_fail": "retry_same",
                 "params": {"image_key": "agent-assets/u1/source.png"}},
                {"id": "analysis", "tool": "text.generate", "after": ["source"],
                 "fanout": 1, "max_retry": 0, "on_fail": "retry_same",
                 "params": {"prompt": "Phân tích ảnh",
                            "image_key": "$source.image_key"}},
            ]}
    result = validate_plan(plan)
    assert result.valid, result.issues


def test_visual_text_cost_is_distinct_from_plain_text():
    from apps.kichban.manifest import _cost
    assert _cost({"prompt": "Viết tiêu đề"}) == 3
    assert _cost({"prompt": "Phân tích", "image_keys": ["taoanh/u1/a.png"]}) == 4
    assert _cost({"prompt": "Tóm tắt", "video_key": "agent-assets/u1/a.mp4"}) == 6


def test_visual_text_worker_embeds_owned_images(tmp_path, monkeypatch):
    from apps.kichban import jobs
    from platform_core.storage import LocalStorage, set_storage

    storage = LocalStorage(str(tmp_path / "store"))
    set_storage(storage)
    first = "agent-assets/u1/first.png"
    second = "taoanh/u1/job/second.png"
    storage.put(first, io.BytesIO(_png()), "image/png")
    storage.put(second, io.BytesIO(_png((180, 70, 20))), "image/png")
    monkeypatch.setattr(jobs, "_lay_key", lambda _model: ("test-key", None))
    seen = {}

    def fake_call(prompt, api_key, model, system, image_parts):
        seen.update(prompt=prompt, parts=image_parts, system=system)
        return "Phân tích hoàn tất"

    monkeypatch.setattr(jobs, "_goi_gemini_text", fake_call)
    try:
        result = jobs.handle({
            "owner_id": "u1", "prompt": "So sánh hai ảnh",
            "image_key": first, "image_keys": [second, first],
            "model": "gemini-2.5-flash", "format": "markdown",
        })
        assert result["text"] == "Phân tích hoàn tất"
        assert result["input_image_count"] == 2 and result["credit_cost"] == 4
        assert len(seen["parts"]) == 2
        decoded = base64.b64decode(seen["parts"][0]["inlineData"]["data"])
        assert decoded.startswith(b"\x89PNG")
    finally:
        set_storage(None)


def test_text_context_stays_separate_from_instruction():
    from apps.kichban import jobs
    assert jobs._context_text_parts({"source_text": "Nội dung nguồn"}) == [
        {"text": "Connected text context:\nNội dung nguồn"}
    ]
    with pytest.raises(ValueError, match="32.000"):
        jobs._context_text_parts({"source_text": "x" * 32001})


def test_video_context_uses_files_api_and_returns_owned_file_part(tmp_path, monkeypatch):
    from apps.kichban import jobs
    from platform_core.storage import LocalStorage, set_storage

    storage = LocalStorage(str(tmp_path / "store"))
    set_storage(storage)
    key = "agent-assets/u1/clip.mp4"
    storage.put(key, io.BytesIO(b"video-bytes"), "video/mp4")
    calls = []

    class Response:
        def __init__(self, status=200, data=None, headers=None):
            self.status_code = status
            self._data = data or {}
            self.headers = headers or {}
        def json(self):
            return self._data

    def post(url, **kwargs):
        calls.append(("post", url))
        if url.endswith("/upload/v1beta/files"):
            return Response(headers={"x-goog-upload-url": "https://upload.test/file"})
        return Response(data={"file": {"name": "files/abc", "uri": "gemini://abc",
                                        "state": "ACTIVE"}})

    fake_httpx = SimpleNamespace(post=post, get=lambda *_a, **_k: Response(),
                                 delete=lambda url, **_k: calls.append(("delete", url)),
                                 HTTPError=Exception)
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    try:
        part, name = jobs._upload_video_part({"video_key": key}, "u1", "test-key")
        assert name == "files/abc"
        assert part == {"fileData": {"mimeType": "video/mp4", "fileUri": "gemini://abc"}}
        jobs._delete_gemini_file(name, "test-key")
        assert calls[-1] == ("delete", "https://generativelanguage.googleapis.com/v1beta/files/abc")
    finally:
        set_storage(None)


def test_video_context_deletes_remote_file_when_processing_fails(tmp_path, monkeypatch):
    from apps.kichban import jobs
    from platform_core.storage import LocalStorage, set_storage

    storage = LocalStorage(str(tmp_path / "store"))
    set_storage(storage)
    key = "agent-assets/u1/clip.mp4"
    storage.put(key, io.BytesIO(b"video-bytes"), "video/mp4")
    deleted = []

    class Response:
        status_code = 200
        headers = {"x-goog-upload-url": "https://upload.test/file"}
        def __init__(self, data=None):
            self._data = data or {}
        def json(self):
            return self._data

    def post(url, **_kwargs):
        if url.endswith("/upload/v1beta/files"):
            return Response()
        return Response({"file": {"name": "files/failed", "uri": "gemini://failed",
                                   "state": "PROCESSING"}})

    fake_httpx = SimpleNamespace(
        post=post,
        get=lambda *_a, **_k: Response({"state": "FAILED"}),
        delete=lambda url, **_k: deleted.append(url),
        HTTPError=Exception,
    )
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    monkeypatch.setattr(jobs.time, "sleep", lambda _seconds: None)
    try:
        with pytest.raises(jobs.GeminiError, match="không xử lý được"):
            jobs._upload_video_part({"video_key": key}, "u1", "test-key")
        assert deleted == ["https://generativelanguage.googleapis.com/v1beta/files/failed"]
    finally:
        set_storage(None)


def test_visual_text_rejects_foreign_missing_and_invalid_assets(tmp_path):
    from apps.kichban import jobs
    from platform_core.storage import LocalStorage, set_storage

    storage = LocalStorage(str(tmp_path / "store"))
    set_storage(storage)
    storage.put("agent-assets/u2/foreign.png", io.BytesIO(_png()), "image/png")
    storage.put("agent-assets/u1/broken.png", io.BytesIO(b"not-an-image"), "image/png")
    try:
        with pytest.raises(ValueError, match="không thuộc"):
            jobs._load_image_parts({"image_key": "agent-assets/u2/foreign.png"}, "u1")
        with pytest.raises(ValueError, match="không còn tồn tại"):
            jobs._load_image_parts({"image_key": "agent-assets/u1/missing.png"}, "u1")
        with pytest.raises(ValueError, match="bị hỏng"):
            jobs._load_image_parts({"image_key": "agent-assets/u1/broken.png"}, "u1")
    finally:
        set_storage(None)
