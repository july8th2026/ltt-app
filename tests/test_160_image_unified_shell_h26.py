"""H26.9 — một shell Tạo ảnh AI, hai executor tương thích phía sau."""
from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'image-shell.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "image-shell-h26")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.users import tao_nguoi_dung
    from platform_core.credit import cap_tay
    gen = dbmod.get_session(); db = next(gen)
    try:
        user = tao_nguoi_dung(db, email="image-shell@example.com",
                              password="Browser-pass-123", is_verified=True)
        db.flush(); cap_tay(db, user.id, 50, by="fixture", note="H26.9")
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    from fastapi.testclient import TestClient
    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver",
                        follow_redirects=False)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    response = client.post("/login", data={
        "username": "image-shell@example.com", "password": "Browser-pass-123",
        "csrf_token": token,
    })
    assert response.status_code == 303
    return client, dbmod


def test_public_contract_keeps_two_executors_but_one_catalog_parent():
    from apps.taoanh.manifest import MANIFEST as image
    from apps.thumbnail.manifest import MANIFEST as thumbnail

    assert image.route_prefix == "/taoanh"
    assert image.job_types == ("taoanh.generate",)
    assert thumbnail.catalog_parent == image.slug
    assert thumbnail.job_types == ("thumbnail.generate",)


def test_unified_shell_does_not_import_another_apps_internals():
    image_routes = (ROOT / "apps" / "taoanh" / "routes.py").read_text("utf-8")
    thumbnail_routes = (ROOT / "apps" / "thumbnail" / "routes.py").read_text("utf-8")
    assert "from apps.thumbnail" not in image_routes
    assert "import apps.thumbnail" not in image_routes
    assert "from apps.taoanh" not in thumbnail_routes
    assert "import apps.taoanh" not in thumbnail_routes


def test_legacy_thumbnail_get_redirects_to_canonical_mode(tmp_path, monkeypatch):
    client, dbmod = _client(tmp_path, monkeypatch)
    try:
        old = client.get("/thumbnail")
        assert old.status_code == 308
        assert old.headers["location"] == "/taoanh/thumbnail"
    finally:
        client.close(); dbmod.reset_engine()


def test_canonical_thumbnail_mode_loads_authenticated_fragment(tmp_path, monkeypatch):
    client, dbmod = _client(tmp_path, monkeypatch)
    try:
        shell = client.get("/taoanh/thumbnail")
        assert shell.status_code == 200
        assert 'aria-current="page">Thumbnail YouTube' in shell.text
        assert 'hx-get="/thumbnail/studio-fragment"' in shell.text
        assert "Đang tải công cụ Thumbnail" in shell.text

        fragment = client.get("/thumbnail/studio-fragment")
        assert fragment.status_code == 200
        assert "<html" not in fragment.text.lower()
        assert 'id="image-mode-panel"' in fragment.text
        assert 'action="/thumbnail/queue"' in fragment.text
        assert "Ảnh Thumbnail của tôi" in fragment.text
    finally:
        client.close(); dbmod.reset_engine()


def test_thumbnail_fragment_submits_job_and_redirects_the_whole_shell(tmp_path,
                                                                     monkeypatch):
    client, dbmod = _client(tmp_path, monkeypatch)
    try:
        fragment = client.get("/thumbnail/studio-fragment")
        token = re.search(
            r'name="csrf_token" value="([^"]+)"', fragment.text).group(1)
        response = client.post("/thumbnail/queue", headers={"HX-Request": "true"},
                               data={"csrf_token": token, "topic": "Ảnh thử",
                                     "title": "H26.9", "count": "2",
                                     "aspect_ratio": "16:9"})
        assert response.status_code == 204
        assert response.headers["hx-redirect"] == "/taoanh/thumbnail"

        from platform_core.models import Job, User
        gen = dbmod.get_session(); db = next(gen)
        try:
            user = db.query(User).filter_by(email="image-shell@example.com").one()
            job = db.query(Job).filter_by(user_id=user.id,
                                          app_slug="thumbnail").one()
            assert job.job_type == "thumbnail.generate"
            assert job.params["count"] == 2
        finally:
            try:
                next(gen)
            except StopIteration:
                pass

        retry_fragment = client.get("/thumbnail/studio-fragment")
        retry_token = re.search(
            r'name="csrf_token" value="([^"]+)"', retry_fragment.text).group(1)
        invalid = client.post("/thumbnail/queue", headers={"HX-Request": "true"},
                              data={"csrf_token": retry_token, "topic": ""})
        assert invalid.status_code == 400
        assert "<html" not in invalid.text.lower()
        assert 'id="image-mode-panel"' in invalid.text
        assert "Chưa nhập chủ đề thumbnail" in invalid.text
    finally:
        client.close(); dbmod.reset_engine()
