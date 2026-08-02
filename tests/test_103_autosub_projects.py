"""AS1: generic AppProject plus Auto Sub owner/revision/schema API."""
from __future__ import annotations

import json
import re
import io

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def studio_api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'studio.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LTT_STORAGE", raising=False)
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
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
    a.close(); b.close(); dbmod.reset_engine(); storage_mod._storage = None


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


def test_import_and_zero_credit_transcribe_dedupe_quota(studio_api):
    a, token, *_ = studio_api
    made = a.post("/autosubvideo/api/projects", headers={"X-CSRF-Token": token},
                  json={"name": "ASR"}).json()
    imported = a.post(f"/autosubvideo/api/projects/{made['id']}/import",
        headers={"X-CSRF-Token": token}, data={"revision": 1, "language": "vi"},
        files={"transcript": ("sample.srt",
            b"1\n00:00:00,000 --> 00:00:02,000\nXin chao\n", "text/plain")})
    assert imported.status_code == 200 and imported.json()["payload"]["tracks"][0]["cues"]

    ticket = a.post("/autosubvideo/upload-url", data={"filename": "sample.mp4",
                    "content_type": "video/mp4"}).json()
    from platform_core.storage import get_storage
    get_storage().put(ticket["key"], io.BytesIO(b"fake-video"), "video/mp4")
    row = imported.json(); row["payload"]["source"] = {
        "key": ticket["key"], "filename": "sample.mp4", "duration_s": 4,
        "width": 1280, "height": 720}
    saved = a.put(f"/autosubvideo/api/projects/{made['id']}", headers={
        "X-CSRF-Token": token, "If-Match": '"2"'},
        json={"name": "ASR", "payload": row["payload"]}).json()
    queued = a.post(f"/autosubvideo/api/projects/{made['id']}/transcribe", headers={
        "X-CSRF-Token": token, "If-Match": f'"{saved["revision"]}"'},
        json={"language": "vi"})
    assert queued.status_code == 202 and queued.json()["credit"] == 0
    again = a.post(f"/autosubvideo/api/projects/{made['id']}/transcribe", headers={
        "X-CSRF-Token": token, "If-Match": f'"{saved["revision"]}"'},
        json={"language": "vi"})
    assert again.status_code == 202 and again.json()["job_id"] == queued.json()["job_id"]
    import platform_core.db as dbmod
    from platform_core import credit
    from platform_core.models import Job, User
    db = next(dbmod.get_session())
    job = db.get(Job, queued.json()["job_id"])
    assert job.params["operation"] == "transcribe" and credit.so_da_giu(db, job.id) == 0
    user = db.query(User).filter_by(email="studio-a@example.com").one()
    for index in range(11):
        db.add(Job(user_id=user.id, app_slug="autosubvideo",
                   job_type="autosubvideo.transcribe", params={"n": index}))
    db.commit(); db.close()
    blocked = a.post(f"/autosubvideo/api/projects/{made['id']}/transcribe", headers={
        "X-CSRF-Token": token, "If-Match": f'"{saved["revision"]}"'}, json={})
    assert blocked.status_code == 429


def test_transcribe_handler_updates_matching_revision(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'worker.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    import platform_core.storage as storage_mod
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    storage_mod.get_storage().put("autosubvideo/u/uploads/a.mp4", io.BytesIO(b"video"))
    from platform_core import app_projects
    from apps.autosubvideo.schemas import empty_studio_project
    db = next(dbmod.get_session())
    payload = empty_studio_project(); payload["source"] = {
        "key": "autosubvideo/u/uploads/a.mp4", "filename": "a.mp4",
        "duration_s": 4, "width": 1280, "height": 720}
    project = app_projects.create(db, user_id="u", app_slug="autosubvideo",
                                  name="p", schema_version=1, payload=payload)
    db.commit(); project_id = project.id; db.close()
    monkeypatch.setattr("platform_core.media.duration_seconds", lambda _path: 4.0)
    monkeypatch.setattr("apps.autosubvideo.transcription.transcribe_file",
        lambda *_args, **_kwargs: {"segments": [{"start": 0, "end": 2,
            "text": "Xin chào", "words": [{"start": 0, "end": 0.5,
            "word": "Xin"}]}], "language": "vi", "engine": "whisperx",
            "alignment_status": "aligned", "fallback_reason": ""})

    class Ctx:
        job_id = "job-asr"
        def progress(self, *_args): pass
        def is_cancelled(self): return False

    from apps.autosubvideo.jobs import handle
    result = handle({"operation": "transcribe", "owner_id": "u",
        "project_id": project_id, "project_revision": 1,
        "video_key": "autosubvideo/u/uploads/a.mp4", "language": "vi"}, Ctx())
    assert result["engine"] == "whisperx" and result["project_revision"] == 2
    db = next(dbmod.get_session()); updated = db.get(platform_core.models.AppProject, project_id)
    assert updated.payload["tracks"][0]["cues"][0]["text"] == "Xin chào"
    db.close(); dbmod.reset_engine(); storage_mod._storage = None


def test_whisperx_sidecar_is_isolated_pinned_and_wired_to_installers():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    requirement = (root / "requirements-whisperx.txt").read_text("ascii")
    assert "whisperx==3.8.6" in requirement
    sidecar = root / "deploy/windows/install-whisperx-sidecar.ps1"
    raw = sidecar.read_bytes(); raw.decode("ascii")
    text = raw.decode("ascii")
    assert "torch==2.8.0" in text and "cu128" in text
    for relative in ("setup/2-cai-dat.ps1", "deploy/windows/install.ps1",
                     "deploy/windows/update.ps1"):
        body = (root / relative).read_text("ascii")
        assert "install-whisperx-sidecar.ps1" in body
        assert "LTT_WHISPERX_PYTHON" in body


def test_auxiliary_cost_is_zero_but_render_never_defaults_free():
    from apps.autosubvideo.manifest import MANIFEST
    assert MANIFEST.credit_cost({"operation": "transcribe"}) == 0
    assert MANIFEST.credit_cost({"operation": "translate"}) == 0
    assert MANIFEST.credit_cost({"operation": "unknown", "duration_s": 60}) == 5
    assert MANIFEST.credit_cost({"duration_s": 60}) == 5
