"""tests/test_5505_upload_zip_job_dedupe.py — end-to-end: upload -> job -> variant."""
from __future__ import annotations

import io
import json
import re
import zipfile

import pytest
from fastapi.testclient import TestClient


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _png_bytes() -> bytes:
    """PNG THẬT (không chỉ magic bytes) — `make_thumbnail` gọi Pillow, và
    Pillow từ chối một chuỗi byte giả chỉ bắt đầu bằng `\\x89PNG`.
    """
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), color=(10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


class _FakeImportZipCtx:
    """Mô phỏng đúng thứ worker thật cấp cho handler: `ctx.job_type` khớp
    `Job.job_type`, và `progress()` không làm gì (test không cần theo dõi
    tiến độ). Gọi trực tiếp `handle(params, ctx=None)` như bản đầu của plan
    sẽ KHÔNG BAO GIỜ định tuyến sang `_handle_import_zip` — `handle()` đọc
    `ctx.job_type` để chọn nhánh, và `params` của job này không tự mang một
    trường phân biệt nào (xem `apps/prompt_ai_ommi/jobs.py::handle`). Đây là
    một chỗ plan pha 5 (Task 5, Step 7) viết sai — lệch giữa test mẫu và
    hợp đồng thật của `handle()`.
    """

    job_type = "prompt_ai_ommi.import_zip"

    def progress(self, *_args, **_kwargs):
        pass


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'zip.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LTT_STORAGE", raising=False)
    monkeypatch.setenv("LTT_PROMPT_AI_OMMI_ROLLOUT", "public")
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    db = next(dbmod.get_session())
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    user = tao_nguoi_dung(db, email="zip-a@example.com",
                          password="Strong-pass-123", is_verified=True)
    credit.cap_tay(db, user.id, 500, by="test")
    db.commit(); db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-zip-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})
    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": "zip-a@example.com", "password": "Strong-pass-123",
        "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
    studio = client.get("/prompt-ai-ommi")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
    yield client, csrf
    client.close(); dbmod.reset_engine(); storage_mod._storage = None


def _resource(client, token):
    made = client.post("/prompt-ai-ommi/api/resources",
                       headers={"X-CSRF-Token": token},
                       json={"kind": "character", "name": "Nhan vat",
                             "prompt_text": "mot nhan vat"})
    return made.json()["id"]


def test_upload_zip_queues_a_job_and_does_not_extract_synchronously(api):
    client, token = api
    rid = _resource(client, token)
    same_bytes = b"\x89PNG" + b"\x00" * 200
    payload = _zip_bytes({"a.png": same_bytes, "b.png": same_bytes})

    resp = client.post(
        "/prompt-ai-ommi/api/resources/upload-zip",
        headers={"X-CSRF-Token": token},
        data={"resource_id": rid},
        files={"file": ("bo.zip", io.BytesIO(payload), "application/zip")})
    assert resp.status_code == 202, resp.text
    job_id = resp.json()["job_id"]

    from platform_core.db import get_session
    from platform_core.models import Job
    db = next(get_session())
    try:
        job = db.get(Job, job_id)
        assert job.job_type == "prompt_ai_ommi.import_zip"
        assert job.status in ("queued", "running")
    finally:
        db.close()


def test_import_job_dedupes_identical_entries_within_the_same_owner(api):
    from apps.prompt_ai_ommi import jobs as ommi_jobs
    client, token = api
    rid = _resource(client, token)
    same_bytes = _png_bytes()
    payload = _zip_bytes({"a.png": same_bytes, "b.png": same_bytes})

    resp = client.post(
        "/prompt-ai-ommi/api/resources/upload-zip",
        headers={"X-CSRF-Token": token},
        data={"resource_id": rid},
        files={"file": ("bo.zip", io.BytesIO(payload), "application/zip")})
    job_id = resp.json()["job_id"]

    from platform_core.db import get_session
    from platform_core.models import Job
    db = next(get_session())
    try:
        job = db.get(Job, job_id)
        result = ommi_jobs.handle(job.params, ctx=_FakeImportZipCtx())
    finally:
        db.close()

    assert result["created"] == 1
    assert result["deduped"] == 1
    # Bất biến kế toán (§ coordinator, 27/09): không entry nào rơi mất.
    assert result["created"] + result["deduped"] + len(result["skipped"]) == \
        result["total"]


def test_zip_with_a_traversal_entry_writes_nothing(api, tmp_path):
    client, token = api
    rid = _resource(client, token)
    payload = _zip_bytes({
        "ok.png": b"\x89PNG" + b"\x00" * 40,
        "../../thoat.png": b"\x89PNG" + b"\x00" * 40,
    })
    resp = client.post(
        "/prompt-ai-ommi/api/resources/upload-zip",
        headers={"X-CSRF-Token": token},
        data={"resource_id": rid},
        files={"file": ("evil.zip", io.BytesIO(payload), "application/zip")})
    job_id = resp.json()["job_id"]

    from apps.prompt_ai_ommi import jobs as ommi_jobs
    from apps.prompt_ai_ommi.services.upload_zip import ZipImportError
    from platform_core.db import get_session
    from platform_core.models import Job
    db = next(get_session())
    try:
        job = db.get(Job, job_id)
        with pytest.raises(ZipImportError, match="zip-slip"):
            ommi_jobs.handle(job.params, ctx=_FakeImportZipCtx())
    finally:
        db.close()


def test_import_job_skips_a_non_image_entry_and_records_it(api):
    """Ca tiêm lỗi Task 5: một entry KHÔNG phải ảnh trong ZIP hợp lệ phải
    xuất hiện trong `skipped` kèm lý do — không được làm job thất bại, và
    không được lặng lẽ biến mất khỏi kết quả.
    """
    from apps.prompt_ai_ommi import jobs as ommi_jobs
    client, token = api
    rid = _resource(client, token)
    payload = _zip_bytes({
        "anh.png": _png_bytes(),
        "doc_them.txt": b"day khong phai anh",
    })
    resp = client.post(
        "/prompt-ai-ommi/api/resources/upload-zip",
        headers={"X-CSRF-Token": token},
        data={"resource_id": rid},
        files={"file": ("mix.zip", io.BytesIO(payload), "application/zip")})
    job_id = resp.json()["job_id"]

    from platform_core.db import get_session
    from platform_core.models import Job
    db = next(get_session())
    try:
        job = db.get(Job, job_id)
        result = ommi_jobs.handle(job.params, ctx=_FakeImportZipCtx())
    finally:
        db.close()

    assert result["created"] == 1
    assert result["deduped"] == 0
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["name"] == "doc_them.txt"
    assert result["skipped"][0]["reason"].strip() != ""
    assert result["created"] + result["deduped"] + len(result["skipped"]) == \
        result["total"]
