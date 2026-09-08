"""H15.S9.2 Image Studio: edit/ref privacy, provider IDs and settlement."""
from __future__ import annotations

import base64
import io
import re

import pytest
from PIL import Image


@pytest.fixture(autouse=True)
def _moi_provider_deu_song(monkeypatch):
    """Chốt **CƠ CHẾ** của `taoanh` (quyền riêng tư ảnh tham chiếu, phân giải id
    model cũ, bút toán) — không chốt provider nào đang được phép phục vụ.

    Từ pha 04 `gemini` đã ngừng và cổng fail-closed nổ trước cả bản mock. Chốt
    production-thật nằm ở `tests/test_1000_chan_provider_da_ngung.py`.

    ⏭️ Pha 06 chuyển `taoanh` sang LTT_IMAGE ⇒ fixture này **phải biến mất** khi
    tệp được viết lại quanh động cơ mới.
    """
    import dataclasses

    from platform_core import providers

    monkeypatch.setattr(
        providers, "REGISTRY",
        {pid: dataclasses.replace(p, is_active=True)
         for pid, p in providers.REGISTRY.items()},
        raising=False)


def _png(size=(96, 64), color=(220, 20, 30)) -> bytes:
    out = io.BytesIO(); Image.new("RGB", size, color).save(out, "PNG")
    return out.getvalue()


def test_reference_validation_and_semantic_directives():
    from apps.taoanh.features import edit_directive, validate_reference
    assert validate_reference(_png(), "image/png") == ("image/png", (96, 64))
    with pytest.raises(ValueError, match="MIME"):
        validate_reference(_png(), "image/jpeg")
    text = edit_directive("semantic_inpaint", "đổi chiếc áo", [{"role": "source"}])
    assert "only the area described" in text and "preserve the rest" in text
    assert "SOURCE" in edit_directive("outpaint", "mở rộng", [{"role": "source"}])
    assert "STYLE" in edit_directive("style_transfer", "sơn dầu", [
        {"role": "source"}, {"role": "style"}])


def test_gemini_request_resolves_legacy_model_and_embeds_reference(monkeypatch):
    from apps.taoanh import jobs
    seen = {}

    class Response:
        status_code = 200
        def json(self):
            return {"candidates": [{"content": {"parts": [{"inlineData": {
                "data": base64.b64encode(b"output").decode("ascii")}}]}}]}

    def fake_post(url, **kwargs):
        seen.update(url=url, body=kwargs["json"]); return Response()

    monkeypatch.setattr("httpx.post", fake_post)
    out = jobs._goi_gemini("edit", "16:9", "test-key",
                           "gemini-3.1-flash-image-preview",
                           [{"role": "source", "mime": "image/png", "data": _png()}])
    assert out == b"output" and "/gemini-3.1-flash-image:" in seen["url"]
    parts = seen["body"]["contents"][0]["parts"]
    assert parts[2]["inlineData"]["mimeType"] == "image/png"


def test_worker_edit_reads_only_owner_refs_and_settles_by_model(tmp_path, monkeypatch):
    from apps.taoanh import jobs
    from platform_core.storage import LocalStorage, set_storage
    storage = LocalStorage(str(tmp_path / "store")); set_storage(storage)
    source = "taoanh/u1/refs/source"; storage.put(source, io.BytesIO(_png()), "image/png")
    monkeypatch.setattr(jobs, "_lay_key", lambda _model: ("key", None))
    seen = {}
    def fake_call(prompt, aspect, key, model, references):
        seen.update(prompt=prompt, references=references); return _png()
    monkeypatch.setattr(jobs, "_goi_gemini", fake_call)
    try:
        out = jobs.handle({"owner_id": "u1", "prompt": "đổi nền", "count": 2,
                           "model": "gemini-3.1-flash-image", "edit_mode": "edit",
                           "references": [{"key": source, "mime": "image/png",
                                           "role": "source"}]})
        assert out["credit_cost"] == 16 and len(out["image_keys"]) == 2
        assert seen["references"][0]["data"].startswith(b"\x89PNG")
        with pytest.raises(ValueError, match="không thuộc"):
            jobs.handle({"owner_id": "u2", "prompt": "x", "edit_mode": "edit",
                         "references": [{"key": source, "mime": "image/png",
                                         "role": "source"}]})
    finally:
        set_storage(None)


def test_edit_handoff_is_owner_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path/'edit.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-image-edit")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.models import JOB_DONE, Job
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    storage = LocalStorage(str(tmp_path / "store")); set_storage(storage)
    gen = dbmod.get_session(); db = next(gen)
    try:
        owner = tao_nguoi_dung(db, email="owner-edit@test.com",
                               password="matkhau-tot-12", is_verified=True)
        other = tao_nguoi_dung(db, email="other-edit@test.com",
                               password="matkhau-tot-12", is_verified=True)
        db.flush(); key = f"taoanh/{owner.id}/job-edit/0.png"
        job = Job(user_id=owner.id, app_slug="taoanh", job_type="taoanh.generate",
                  status=JOB_DONE, progress=100, params={"prompt": "gốc", "count": 1},
                  result={"image_keys": [key]})
        db.add(job); db.commit(); job_id = job.id
        storage.put(key, io.BytesIO(_png()), "image/png")
    finally:
        try: next(gen)
        except StopIteration: pass

    from fastapi.testclient import TestClient
    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver", follow_redirects=False)
    def login(email):
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        assert client.post("/login", data={"username": email,
            "password": "matkhau-tot-12", "csrf_token": token}).status_code == 303
    try:
        login("owner-edit@test.com")
        page = client.get(f"/taoanh/edit/{job_id}/0")
        assert page.status_code == 200 and 'name="saved_source_key"' in page.text
        assert "Đã nạp output làm ảnh nguồn" in page.text
        logout_token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        client.post("/logout", data={"csrf_token": logout_token})
        login("other-edit@test.com")
        assert client.get(f"/taoanh/edit/{job_id}/0").status_code == 404
    finally:
        client.close(); set_storage(None); dbmod.reset_engine()


def test_template_discloses_provider_privacy_and_precision_limit():
    from pathlib import Path
    src = (Path(__file__).parents[1] / "apps" / "taoanh" / "templates" / "image.html").read_text("utf-8")
    assert "enctype=\"multipart/form-data\"" in src
    assert "Ảnh tham chiếu được gửi tới Gemini" in src
    assert "chưa phải công cụ mask chính xác từng pixel" in src
    assert "saved_source_key" in src and "/edit/{{j.id}}/{{loop.index0}}" in src
