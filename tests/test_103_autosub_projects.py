"""AS1: generic AppProject plus Auto Sub owner/revision/schema API."""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def studio_api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'studio.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    for email in ("studio-a@example.com", "studio-b@example.com"):
        tao_nguoi_dung(db, email=email, password="Strong-pass-123", is_verified=True)
    db.commit(); db.close(); dbmod.reset_engine()
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test", "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "autosub-project-test-session", "LTT_ADMIN_USERNAME": "",
        "LTT_ADMIN_PASSWORD_HASH": ""})

    def login(email):
        client = TestClient(app, base_url="https://testserver", follow_redirects=True)
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        assert client.post("/login", data={"username": email, "password": "Strong-pass-123",
            "csrf_token": token, "next": "/autosubvideo"}).status_code == 200
        studio = client.get("/autosubvideo")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
        return client, csrf

    a, token_a = login("studio-a@example.com")
    b, token_b = login("studio-b@example.com")
    yield a, token_a, b, token_b
    a.close(); b.close(); dbmod.reset_engine()


def _payload():
    return {"schema_version": 1, "active_step": "transcript",
            "source": {"key": "autosubvideo/user/uploads/a.mp4", "filename": "a.mp4",
                       "duration_s": 4, "width": 1280, "height": 720},
            "tracks": [{"id": "source", "kind": "source", "language": "vi",
                        "name": "Tiếng Việt", "visible": True, "z_index": 0,
                        "style_id": "default", "cues": [{"id": "cue-1", "start": 0,
                        "end": 4, "text": "Xin chào", "speaker": "", "words": []}]}],
            "speakers": {}, "style": {"preset": "default"},
            "output": {"resolution": "source", "format": "mp4"}}


def test_project_crud_etag_conflict_and_ownership(studio_api):
    a, token_a, b, token_b = studio_api
    assert a.post("/autosubvideo/api/projects", json={}).status_code == 400
    made = a.post("/autosubvideo/api/projects", headers={"X-CSRF-Token": token_a},
                  json={"name": "Video A", "payload": _payload()})
    assert made.status_code == 201 and made.headers["etag"] == '"1"'
    row = made.json(); project_id = row["id"]
    assert a.get("/autosubvideo/api/projects").json()["items"][0]["id"] == project_id
    assert b.get(f"/autosubvideo/api/projects/{project_id}").status_code == 404
    payload = row["payload"]; payload["active_step"] = "style"
    saved = a.put(f"/autosubvideo/api/projects/{project_id}", headers={
        "X-CSRF-Token": token_a, "If-Match": '"1"'},
        json={"name": "Video A2", "payload": payload})
    assert saved.status_code == 200 and saved.json()["revision"] == 2
    assert a.put(f"/autosubvideo/api/projects/{project_id}", headers={
        "X-CSRF-Token": token_a, "If-Match": '"1"'},
        json={"name": "stale", "payload": payload}).status_code == 409
    assert b.put(f"/autosubvideo/api/projects/{project_id}", headers={
        "X-CSRF-Token": token_b}, json={"revision": 2, "name": "steal",
        "payload": payload}).status_code == 404
    archived = a.post(f"/autosubvideo/api/projects/{project_id}/archive",
                      headers={"X-CSRF-Token": token_a}, json={})
    assert archived.status_code == 200 and archived.json()["status"] == "archived"
    assert a.put(f"/autosubvideo/api/projects/{project_id}", headers={
        "X-CSRF-Token": token_a}, json={"revision": 3, "name": "x",
        "payload": payload}).status_code == 422


def test_project_schema_rejects_duplicate_tracks_bad_timing_and_secrets(studio_api):
    a, token, *_ = studio_api
    payload = _payload(); payload["tracks"].append(dict(payload["tracks"][0]))
    assert a.post("/autosubvideo/api/projects", headers={"X-CSRF-Token": token},
                  json={"payload": payload}).status_code == 422
    payload = _payload(); payload["tracks"][0]["cues"][0]["end"] = 0
    assert a.post("/autosubvideo/api/projects", headers={"X-CSRF-Token": token},
                  json={"payload": payload}).status_code == 422
    payload = _payload(); payload["style"]["api_key"] = "must-not-persist"
    assert a.post("/autosubvideo/api/projects", headers={"X-CSRF-Token": token},
                  json={"payload": payload}).status_code == 422


def test_generic_container_limits_size_depth_and_app_scope(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'core.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core import app_projects
    db = next(dbmod.get_session())
    row = app_projects.create(db, user_id="u", app_slug="a", name="n",
                              schema_version=1, payload={"ok": True})
    assert app_projects.get_owned(db, row.id, "u", "a") is row
    with pytest.raises(app_projects.ProjectNotFound):
        app_projects.get_owned(db, row.id, "u", "b")
    with pytest.raises(app_projects.ProjectError):
        app_projects.create(db, user_id="u", app_slug="a", name="n",
                            schema_version=1, payload={"text": "x" * 1_100_000})
    deep = {}; cursor = deep
    for _ in range(34):
        cursor["x"] = {}; cursor = cursor["x"]
    with pytest.raises(app_projects.ProjectError):
        app_projects.validate_container_payload(deep)
    db.close(); dbmod.reset_engine()


def test_app_project_migration_is_single_head():
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    assert scripts.get_current_head() == "d4e5f6a7b8c9"
