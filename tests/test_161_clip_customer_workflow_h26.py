"""H26.10A — Clip Studio phải là workflow khách hàng, không phải bảng dev."""
from __future__ import annotations

from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import platform_core.db as dbmod

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'clip-h26.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "clip-customer-h26")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.models import Job
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        owner = tao_nguoi_dung(db, email="clip-h26@example.com",
                               password="Browser-pass-123", is_verified=True)
        db.flush()
        db.add(Job(user_id=owner.id, app_slug="taoclipngan",
                   job_type="taoclipngan.render", status="queued", progress=0,
                   params={"source_filename": "customer-video.mp4",
                           "tier": "high_quality", "aspect_ratio": "9:16"}))
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass
    test_client = TestClient(__import__("server.app", fromlist=["create_app"])
                             .create_app(), base_url="https://testserver",
                             follow_redirects=False)
    page = test_client.get("/en/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert test_client.post("/en/login", data={
        "username": "clip-h26@example.com", "password": "Browser-pass-123",
        "csrf_token": token, "next": "/en/taoclipngan"}).status_code == 303
    try:
        yield test_client
    finally:
        test_client.close(); dbmod.reset_engine()


def test_clip_template_prioritises_customer_workflow():
    template = (ROOT / "apps" / "taoclipngan" / "templates" /
                "taoclipngan.html").read_text("utf-8")
    routes = (ROOT / "apps" / "taoclipngan" / "routes.py").read_text("utf-8")
    css = (ROOT / "server" / "static" / "ltt.css").read_text("utf-8")
    assert 'class="clip-advanced"' in template
    assert 'id="clip-source-summary"' in template
    assert 'id="clip-source-preview"' in template
    assert 'href="/jobs/{{ job.id }}"' in template
    assert "large-v3" not in routes
    assert ".clip-source-summary[hidden]{display:none}" in css


def test_clip_estimate_and_dynamic_labels_follow_english_locale(client):
    studio = client.get("/en/taoclipngan")
    assert studio.status_code == 200
    assert "Tự động theo thể loại" not in studio.text
    assert re.search(r"customer-video\.mp4</strong><small>[^<]* · Best · 9:16",
                     studio.text)
    assert "Waiting for processing" in studio.text
    estimate = client.post("/en/taoclipngan/estimate", data={
        "duration_s": "0", "tier": "high_quality",
        "target_clip_count": "3"})
    assert estimate.status_code == 200
    assert "Chọn video" not in estimate.text
    assert "Choose a video" in estimate.text
