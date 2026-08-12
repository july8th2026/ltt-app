"""R2 route integration — media chỉ bền vững sau hold, retry không thu lại."""
from __future__ import annotations

import io
import re

from PIL import Image


MP4 = b"\x00\x00\x00\x18ftypisom" + b"x" * 52


def _png() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (64, 64), (180, 20, 20)).save(stream, format="PNG")
    return stream.getvalue()


def _client(tmp_path, monkeypatch, *, credit_amount=100):
    from fastapi.testclient import TestClient
    import platform_core.db as dbmod
    from platform_core.credit import cap_tay
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'routes.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "upload-route-contract")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    storage = LocalStorage(str(tmp_path / "storage")); set_storage(storage)
    gen = dbmod.get_session(); db = next(gen)
    user = tao_nguoi_dung(db, email="upload-route@example.com",
                          password="Browser-pass-123", is_verified=True)
    db.flush()
    if credit_amount:
        cap_tay(db, user.id, credit_amount, by="fixture", note="R2 route")
    db.commit(); user_id = user.id; db.close()

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver",
                        follow_redirects=False)
    login = client.get("/login")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', login.text).group(1)
    assert client.post("/login", data={
        "username": "upload-route@example.com", "password": "Browser-pass-123",
        "csrf_token": csrf,
    }).status_code == 303
    return client, dbmod, storage, user_id, set_storage


def _csrf(client, path: str) -> str:
    page = client.get(path)
    assert page.status_code == 200
    return re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)


def _rows(dbmod, app_slug: str):
    from platform_core.models import Job, UploadSession
    from sqlalchemy import select
    gen = dbmod.get_session(); db = next(gen)
    try:
        jobs = list(db.execute(select(Job).where(Job.app_slug == app_slug)).scalars())
        sessions = list(db.execute(select(UploadSession).where(
            UploadSession.app_slug == app_slug)).scalars())
        return jobs, sessions
    finally:
        db.close()


def test_upscale_promote_va_retry_cung_ve_khong_giu_credit_lan_hai(
        tmp_path, monkeypatch):
    from platform_core.credit import so_du
    client, dbmod, storage, user_id, reset_storage = _client(tmp_path, monkeypatch)
    try:
        csrf = _csrf(client, "/upscalevideo")
        first = client.post("/upscalevideo/queue", data={
            "csrf_token": csrf, "duration_s": "1", "preset": "fast",
            "target_height": "1080", "codec": "h264", "ajax": "1",
        }, files={"video": ("sample.mp4", MP4, "video/mp4")})
        assert first.status_code == 200
        jobs, sessions = _rows(dbmod, "upscalevideo")
        assert len(jobs) == len(sessions) == 1 and sessions[0].status == "promoted"
        assert storage.exists(sessions[0].final_key)
        assert not storage.exists(sessions[0].staging_key)
        gen = dbmod.get_session(); db = next(gen)
        balance = so_du(db, user_id); db.close()

        replay = client.post("/upscalevideo/queue", data={
            "csrf_token": csrf, "video_key": sessions[0].staging_key,
            "duration_s": "1", "preset": "fast", "target_height": "1080",
            "codec": "h264", "ajax": "1",
        })
        assert replay.status_code == 200
        jobs, _sessions = _rows(dbmod, "upscalevideo")
        gen = dbmod.get_session(); db = next(gen)
        assert len(jobs) == 1 and so_du(db, user_id) == balance
        db.close()
    finally:
        client.close(); dbmod.reset_engine(); reset_storage(None)


def test_clip_va_image_deu_promote_input_sau_hold(tmp_path, monkeypatch):
    client, dbmod, storage, _user_id, reset_storage = _client(tmp_path, monkeypatch)
    try:
        clip_csrf = _csrf(client, "/taoclipngan")
        clip = client.post("/taoclipngan/queue", data={
            "csrf_token": clip_csrf, "duration_s": "1", "tier": "fast",
            "target_clip_count": "1", "min_clip_duration_sec": "5",
            "max_clip_duration_sec": "10", "ajax": "1",
        }, files={"video": ("clip.mp4", MP4, "video/mp4")})
        assert clip.status_code == 200

        image_csrf = _csrf(client, "/taoanh")
        image = client.post("/taoanh/queue", data={
            "csrf_token": image_csrf, "prompt": "Giữ chủ thể, đổi ánh sáng",
            "aspect_ratio": "1:1", "count": "1", "edit_mode": "edit",
        }, files={"source_image": ("source.png", _png(), "image/png")})
        assert image.status_code == 303

        for slug in ("taoclipngan", "taoanh"):
            jobs, sessions = _rows(dbmod, slug)
            assert len(jobs) == len(sessions) == 1
            assert sessions[0].status == "promoted"
            assert storage.exists(sessions[0].final_key)
            assert not storage.exists(sessions[0].staging_key)
    finally:
        client.close(); dbmod.reset_engine(); reset_storage(None)


def test_seedance_batch_mot_variant_promote_ref_sau_quote_hold(tmp_path, monkeypatch):
    client, dbmod, storage, _user_id, reset_storage = _client(
        tmp_path, monkeypatch, credit_amount=500)
    try:
        csrf = _csrf(client, "/taovideo")
        estimate = client.post("/taovideo/estimate", data={
            "model": "seedance-2.0-mini", "resolution": "480p",
            "duration": "4", "aspect_ratio": "16:9", "count": "1",
            "quote_has_video": "1",
        })
        quote = re.search(r'name="quote_id" value="([^"]+)"', estimate.text).group(1)
        queued = client.post("/taovideo/queue", data={
            "csrf_token": csrf, "prompt": "Slow camera move through a studio",
            "model": "seedance-2.0-mini", "resolution": "480p",
            "duration": "4", "aspect_ratio": "16:9", "count": "1",
            "quote_id": quote,
        }, files={"ref_videos": ("reference.mp4", MP4, "video/mp4")})
        assert queued.status_code == 303
        jobs, sessions = _rows(dbmod, "taovideo")
        assert len(jobs) == len(sessions) == 1
        assert sessions[0].status == "promoted"
        assert jobs[0].params["refs"][0]["storage_key"] == sessions[0].final_key
        assert storage.exists(sessions[0].final_key)
    finally:
        client.close(); dbmod.reset_engine(); reset_storage(None)


def test_thieu_credit_chi_de_lai_staging_co_ttl(tmp_path, monkeypatch):
    client, dbmod, storage, _user_id, reset_storage = _client(
        tmp_path, monkeypatch, credit_amount=0)
    try:
        csrf = _csrf(client, "/upscalevideo")
        response = client.post("/upscalevideo/queue", data={
            "csrf_token": csrf, "duration_s": "1", "preset": "fast",
            "target_height": "1080", "codec": "h264", "ajax": "1",
        }, files={"video": ("no-credit.mp4", MP4, "video/mp4")})
        assert response.status_code == 400
        jobs, sessions = _rows(dbmod, "upscalevideo")
        assert jobs == [] and len(sessions) == 1 and sessions[0].status == "ready"
        assert storage.exists(sessions[0].staging_key) and not sessions[0].final_key
    finally:
        client.close(); dbmod.reset_engine(); reset_storage(None)
