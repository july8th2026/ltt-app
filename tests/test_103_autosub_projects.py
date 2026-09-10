"""AS1: generic AppProject plus Auto Sub owner/revision/schema API."""
from __future__ import annotations

import json
import re
import io
import hashlib
from pathlib import Path

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


def test_platform_migrations_have_a_single_head():
    """Đồ thị migration không được phân nhánh.

    Hai head nghĩa là hai người cùng đặt `down_revision` vào một revision; lúc
    đó `alembic upgrade head` báo lỗi và bản cài dừng giữa chừng — đúng chỗ khó
    xử lý nhất, trên máy chủ đang chạy.

    Trước đây test này so head với một mã revision viết cứng, nên **mọi
    migration hợp lệ mới đều làm nó đỏ** và người thêm migration phải sửa test
    dù không có gì sai. Kiểm số lượng head mới đúng bất biến cần giữ.
    """
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    heads = scripts.get_heads()
    assert len(heads) == 1, f"migration bị phân nhánh, có {len(heads)} head: {heads}"


def test_import_and_zero_credit_transcribe_dedupe_quota(studio_api):
    a, token, *_ = studio_api
    made = a.post("/autosubvideo/api/projects", headers={"X-CSRF-Token": token},
                  json={"name": "ASR"}).json()
    imported = a.post(f"/autosubvideo/api/projects/{made['id']}/import",
        headers={"X-CSRF-Token": token}, data={"revision": 1, "language": "vi"},
        files={"transcript": ("sample.srt",
            b"1\n00:00:00,000 --> 00:00:02,000\nXin chao\n", "text/plain")})
    assert imported.status_code == 200 and imported.json()["payload"]["tracks"][0]["cues"]

    attached = a.post(f"/autosubvideo/api/projects/{made['id']}/source", headers={
        "X-CSRF-Token": token}, data={"revision": 2, "csrf_token": token,
        "filename": "sample.mp4", "duration_s": 4, "width": 1280, "height": 720},
        files={"video": ("sample.mp4", b"\x00\x00\x00\x18ftypisom" + b"x" * 52,
                         "video/mp4")})
    assert attached.status_code == 200
    saved = attached.json()
    assert "/drafts/" in saved["payload"]["source"]["key"]
    import platform_core.db as dbmod
    from platform_core.models import UploadSession
    db = next(dbmod.get_session())
    session = db.query(UploadSession).filter_by(project_id=made["id"]).one()
    assert session.status == "attached" and session.user_id in session.final_key
    db.close()
    queued = a.post(f"/autosubvideo/api/projects/{made['id']}/transcribe", headers={
        "X-CSRF-Token": token, "If-Match": f'"{saved["revision"]}"'},
        json={"language": "vi"})
    assert queued.status_code == 202 and queued.json()["credit"] == 0
    again = a.post(f"/autosubvideo/api/projects/{made['id']}/transcribe", headers={
        "X-CSRF-Token": token, "If-Match": f'"{saved["revision"]}"'},
        json={"language": "vi"})
    assert again.status_code == 202 and again.json()["job_id"] == queued.json()["job_id"]
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


def test_project_source_ticket_validates_owner_size_and_expiry(studio_api, monkeypatch):
    a,token,b,token_b=studio_api
    monkeypatch.setenv("LTT_R2_BROWSER_UPLOAD_ENABLED", "1")
    from platform_core.storage import get_storage
    monkeypatch.setattr(get_storage(), "try_put_url", lambda *args, **kwargs:
        type("Target", (), {"url":"https://upload.test/source", "method":"PUT",
                            "headers":{}, "key":args[0]})())
    made=a.post("/autosubvideo/api/projects",headers={"X-CSRF-Token":token},
        json={"name":"draft-source"}).json()
    ticket=a.post("/autosubvideo/api/uploads",headers={"X-CSRF-Token":token},json={
        "filename":"source.mp4","content_type":"video/mp4","expected_size":64})
    assert ticket.status_code==200 and ticket.json()["mode"]=="direct"
    upload_id=ticket.json()["upload_id"]
    import platform_core.db as dbmod
    from platform_core.models import UploadSession
    db=next(dbmod.get_session());session=db.get(UploadSession,upload_id)
    get_storage().put(session.staging_key,io.BytesIO(
        b"\x00\x00\x00\x18ftypisom"+b"x"*52),"video/mp4");db.close()

    other=b.post("/autosubvideo/api/projects",headers={"X-CSRF-Token":token_b},
        json={"name":"other-project"}).json()
    stolen=b.post(f"/autosubvideo/api/projects/{other['id']}/source",headers={
        "X-CSRF-Token":token_b},data={"revision":1,"upload_id":upload_id,
        "filename":"source.mp4"})
    assert stolen.status_code==422 and "không thuộc user" in stolen.json()["detail"]
    attached=a.post(f"/autosubvideo/api/projects/{made['id']}/source",headers={
        "X-CSRF-Token":token},data={"revision":1,"upload_id":upload_id,
        "filename":"source.mp4","duration_s":4,"width":1280,"height":720})
    assert attached.status_code==200

    db=next(dbmod.get_session());session=db.get(UploadSession,upload_id)
    get_storage().delete(session.final_key);db.close()
    reloaded=a.get(f"/autosubvideo/api/projects/{made['id']}")
    assert reloaded.status_code==200 and reloaded.json()["source_expired"] is True
    assert reloaded.json()["payload"]["source"]["key"]==""

    oversized=a.post("/autosubvideo/api/uploads",headers={"X-CSRF-Token":token},json={
        "filename":"large.mp4","content_type":"video/mp4",
        "expected_size":2*1024*1024*1024+1})
    assert oversized.status_code==422


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


def test_update_reuses_a_configured_healthy_whisperx_sidecar_before_installing():
    root = Path(__file__).resolve().parents[1]
    update = (root / "deploy/windows/update.ps1").read_text("ascii")
    configured = update.index("^LTT_WHISPERX_PYTHON=(.+)$")
    health = update.index("import torch,whisperx,sys")
    installer = update.index("install-whisperx-sidecar.ps1")
    assert configured < health < installer
    assert "Existing WhisperX CUDA sidecar kept" in update


def test_whisperx_timeout_stops_process_tree_without_stderr_pipe(tmp_path, monkeypatch):
    from apps.autosubvideo import transcription
    source=tmp_path/"audio.wav";source.write_bytes(b"wav")
    monkeypatch.setenv("LTT_WHISPERX_PYTHON", __import__("sys").executable)
    monkeypatch.setenv("LTT_WHISPERX_TIMEOUT_SECONDS", "60")
    class Process:
        pid=123;returncode=None
        def poll(self):return None
        def wait(self,timeout=None):raise __import__("subprocess").TimeoutExpired("x",timeout)
    process=Process();calls={}
    def popen(*_args,**kwargs):calls.update(kwargs);return process
    monkeypatch.setattr(transcription.subprocess,"Popen",popen)
    ticks=iter((0,1000));monkeypatch.setattr(transcription.time,"monotonic",lambda:next(ticks))
    monkeypatch.setattr(transcription,"_stop_process_tree",lambda value:calls.update(stopped=value))
    with pytest.raises(transcription.TranscriptionError,match="quá thời gian"):
        transcription._transcribe_whisperx(str(source),language="en",model_name="tiny")
    assert calls["stderr"] is not transcription.subprocess.PIPE
    assert calls["stopped"] is process


def test_auxiliary_cost_is_zero_but_render_never_defaults_free():
    from apps.autosubvideo.manifest import MANIFEST
    assert MANIFEST.credit_cost({"operation": "transcribe"}) == 0
    assert MANIFEST.credit_cost({"operation": "translate"}) == 0
    assert MANIFEST.credit_cost({"operation": "unknown", "duration_s": 60}) == 5
    assert MANIFEST.credit_cost({"duration_s": 60}) == 5


def test_studio_render_quote_snapshot_hold_cancel_refund_and_retry(studio_api):
    a, token, b, _token_b = studio_api
    import platform_core.db as dbmod
    from platform_core import credit
    from platform_core.models import Job, User
    from platform_core.storage import get_storage
    db = next(dbmod.get_session())
    user = db.query(User).filter_by(email="studio-a@example.com").one()
    credit.nap(db, user.id, 100, "render-test")
    key = f"autosubvideo/{user.id}/uploads/render.mp4"
    get_storage().put(key, io.BytesIO(b"fake-video"), "video/mp4")
    user_id = user.id; db.commit(); db.close()
    payload = _payload(); payload["source"]["key"] = key
    payload["source"]["duration_s"] = 61
    payload["output"].update({"quality": "high", "resolution": "1080p",
        "track_ids": ["source"], "export_srt": True, "export_ass": True,
        "export_vtt": True, "export_json": True, "bundle_zip": True})
    made = a.post("/autosubvideo/api/projects", headers={"X-CSRF-Token": token},
                  json={"name": "Render", "payload": payload}).json()
    endpoint = f"/autosubvideo/api/projects/{made['id']}"
    quote = a.post(endpoint + "/quote", headers={"X-CSRF-Token": token,
        "If-Match": '"1"'}, json={"output": made["payload"]["output"]})
    assert quote.status_code == 200
    assert quote.json()["quote"] == {"credit": 8, "vnd": 800, "minutes": 1.02,
        "quality": "high", "resolution": "1080p", "format": "mp4",
        "track_ids": ["source"], "project_revision": 1,
        "preflight": {"score": 100, "error_count": 0, "warning_count": 0,
                      "issue_codes": []}}
    submitted = a.post(endpoint + "/render", headers={"X-CSRF-Token": token,
        "If-Match": '"1"'}, json={"output": made["payload"]["output"]})
    assert submitted.status_code == 202
    job_id = submitted.json()["job_id"]
    assert b.get(f"/autosubvideo/api/jobs/{job_id}").status_code == 404
    history = a.get(f"/autosubvideo/api/jobs?project_id={made['id']}&limit=8")
    assert history.status_code == 200
    assert [item["id"] for item in history.json()["items"]] == [job_id]
    assert history.json()["items"][0]["project_id"] == made["id"]
    assert history.json()["items"][0]["created_at"]
    assert a.get("/autosubvideo/api/jobs?project_id=not-this-project").json()["items"] == []
    assert b.get(f"/autosubvideo/api/jobs?project_id={made['id']}").json()["items"] == []
    db = next(dbmod.get_session()); job = db.get(Job, job_id)
    assert job.params["operation"] == "render_project"
    assert job.params["project_snapshot"]["tracks"][0]["cues"][0]["text"] == "Xin chào"
    assert credit.so_da_giu(db, job_id) == 8 and credit.so_du(db, user_id) == 92
    db.close()
    changed = made["payload"]; changed["tracks"][0]["cues"][0]["text"] = "Đã sửa"
    assert a.put(endpoint, headers={"X-CSRF-Token": token, "If-Match": '"1"'},
                 json={"name": "Render", "payload": changed}).status_code == 200
    db = next(dbmod.get_session()); assert db.get(Job, job_id).params[
        "project_snapshot"]["tracks"][0]["cues"][0]["text"] == "Xin chào"; db.close()
    cancelled = a.post(f"/autosubvideo/api/jobs/{job_id}/cancel",
        headers={"X-CSRF-Token": token}, json={})
    assert cancelled.json() == {"ok": True, "status": "cancelled"}
    db = next(dbmod.get_session()); assert credit.so_du(db, user_id) == 100; db.close()
    retried = a.post(f"/autosubvideo/api/jobs/{job_id}/retry",
        headers={"X-CSRF-Token": token}, json={})
    assert retried.status_code == 202 and retried.json()["job_id"] != job_id
    db = next(dbmod.get_session()); assert credit.so_du(db, user_id) == 92; db.close()


def test_project_render_worker_uses_snapshot_multitrack_resolution_and_bundle(tmp_path, monkeypatch):
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    storage_mod.get_storage().put("autosubvideo/u/uploads/a.mp4", io.BytesIO(b"video"))
    payload = _payload(); payload["source"]["key"] = "autosubvideo/u/uploads/a.mp4"
    payload["tracks"].append({"id":"translated","kind":"translation","language":"en",
        "name":"English","visible":True,"z_index":1,"style_id":"default","cues":[
        {"id":"cue-2","start":0,"end":4,"text":"Hello","speaker":"","words":[]}]})
    payload["output"].update({"resolution":"1080p","format":"mp4","quality":"standard",
        "track_ids":["source","translated"],"export_srt":True,"export_vtt":True,
        "export_json":True,"export_ass":True,"bundle_zip":True})
    from apps.autosubvideo.schemas import StudioProjectV1
    payload = StudioProjectV1.model_validate(payload).model_dump(mode="json")
    canonical=json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode()
    monkeypatch.setattr("platform_core.media.probe",lambda _p:{"duration":4,"width":1280,
        "height":720,"bitrate_kbps":900})
    calls={}
    def fake_burn(**kwargs):
        calls.update(kwargs); open(kwargs["output_path"],"wb").write(b"rendered"); return kwargs["output_path"]
    monkeypatch.setattr("apps.autosubvideo.burn.burn",fake_burn)
    monkeypatch.setattr("apps.autosubvideo.jobs._dam_bao_giu_cho",lambda *_a:None)
    class Ctx:
        job_id="render-job"
        def progress(self,*_args): pass
    from apps.autosubvideo.jobs import handle
    result=handle({"operation":"render_project","owner_id":"u","video_key":payload["source"]["key"],
        "project_revision":3,"project_snapshot":payload,
        "snapshot_sha256":hashlib.sha256(canonical).hexdigest()},Ctx())
    assert calls["target_height"]==1080 and result["track_ids"]==["source","translated"]
    assert set(result["srt_keys"])=={"source","translated"} and result["bundle_key"].endswith(".zip")
    assert set(result["vtt_keys"])=={"source","translated"}
    assert set(result["json_keys"])=={"source","translated"}
    ass=storage_mod.get_storage().open(result["ass_key"]).read().decode("utf-8-sig")
    assert "Dialogue: 0," in ass and "Dialogue: 1," in ass and "{\\an8}" in ass
    storage_mod._storage=None


def test_studio_artifacts_are_owner_scoped_range_capable_and_injection_safe(
        studio_api, tmp_path, monkeypatch):
    a, token, b, _ = studio_api
    import platform_core.db as dbmod
    from platform_core.models import User
    from platform_core.storage import get_storage
    db=next(dbmod.get_session());owner=db.query(User).filter_by(
        email="studio-a@example.com").one().id;db.close()
    video_key=f"autosubvideo/{owner}/job/output.mp4"
    zip_key=f"autosubvideo/{owner}/job/subtitle-bundle.zip"
    storage=get_storage()
    storage.put(video_key,io.BytesIO(b"0123456789"),"video/mp4")
    storage.put(zip_key,io.BytesIO(b"PK-safe"),"application/zip")
    original_url_for=storage.url_for
    # Stub phải khớp chữ ký thật `url_for(key, ttl_s=...)`. Bản cũ chỉ nhận
    # `_key` và vẫn xanh vì route gọi không truyền ttl_s — một stub sai hình
    # nhưng không ai phát hiện.
    monkeypatch.setattr(storage,"url_for",
                        lambda _key,ttl_s=900:"https://r2.invalid/signed")
    monkeypatch.delenv("LTT_R2_BROWSER_UPLOAD_ENABLED",raising=False)
    assert a.get(f"/autosubvideo/v/{video_key}",headers={"Range":"bytes=2-5"}).status_code==206
    assert a.get(f"/autosubvideo/v/{video_key}",headers={"Range":"bytes=2-5"}).content==b"2345"
    monkeypatch.setenv("LTT_R2_BROWSER_UPLOAD_ENABLED","1")
    assert a.get(f"/autosubvideo/v/{video_key}",follow_redirects=False).status_code==302
    monkeypatch.delenv("LTT_R2_BROWSER_UPLOAD_ENABLED")
    monkeypatch.setattr(storage,"url_for",original_url_for)
    assert b.get(f"/autosubvideo/v/{video_key}").status_code==404
    downloaded=a.get(f"/autosubvideo/f/{zip_key}")
    assert downloaded.status_code==200 and downloaded.headers["content-type"].startswith("application/zip")
    assert a.get("/autosubvideo/f/../../secrets/app.env").status_code in {404,405}

    from apps.autosubvideo.ass_builder import build_ass
    from apps.autosubvideo.schemas import SubtitleStyleConfig
    from apps.autosubvideo.segmenter import SubtitleEvent
    path=tmp_path/"injection.ass"
    build_ass([SubtitleEvent(0,1,r"{\p1}m 0 0 l 9 9",r"{\p1}m 0 0 l 9 9")],
              SubtitleStyleConfig(),str(path))
    ass=path.read_text("utf-8-sig")
    assert r"{\p1}" not in ass and r"（\p1）" in ass


def test_render_quote_rejects_unknown_track_and_long_asr_source(studio_api):
    a,token,*_=studio_api
    import platform_core.db as dbmod
    from platform_core.models import User
    from platform_core.storage import get_storage
    db=next(dbmod.get_session());owner=db.query(User).filter_by(
        email="studio-a@example.com").one().id;db.close()
    payload=_payload();payload["source"]["key"]=f"autosubvideo/{owner}/uploads/long.mp4"
    payload["source"]["duration_s"]=7201
    get_storage().put(payload["source"]["key"],io.BytesIO(b"video"),"video/mp4")
    made=a.post("/autosubvideo/api/projects",headers={"X-CSRF-Token":token},
        json={"name":"limits","payload":payload}).json()
    quote=a.post(f"/autosubvideo/api/projects/{made['id']}/quote",headers={
        "X-CSRF-Token":token,"If-Match":'"1"'},json={"output":{"track_ids":["missing"]}})
    assert quote.status_code==422
    transcribe=a.post(f"/autosubvideo/api/projects/{made['id']}/transcribe",headers={
        "X-CSRF-Token":token,"If-Match":'"1"'},json={})
    assert transcribe.status_code==422


def test_render_preflight_blocks_fatal_timing_and_reports_warnings(studio_api):
    a,token,*_=studio_api
    import platform_core.db as dbmod
    from platform_core.models import User
    from platform_core.storage import get_storage
    db=next(dbmod.get_session());owner=db.query(User).filter_by(
        email="studio-a@example.com").one().id;db.close()
    payload=_payload();payload["source"]["key"]=f"autosubvideo/{owner}/uploads/qa.mp4"
    get_storage().put(payload["source"]["key"],io.BytesIO(b"video"),"video/mp4")
    payload["tracks"][0]["cues"]=[
        {"id":"cue-1","start":0,"end":.2,"text":"Nội dung đọc quá nhanh",
         "speaker":"","words":[]},
        {"id":"cue-2","start":.1,"end":1,"text":"Bị chồng thời gian",
         "speaker":"","words":[]},
    ]
    made=a.post("/autosubvideo/api/projects",headers={"X-CSRF-Token":token},
        json={"name":"preflight","payload":payload}).json()
    endpoint=f"/autosubvideo/api/projects/{made['id']}/quote"
    blocked=a.post(endpoint,headers={"X-CSRF-Token":token,"If-Match":'"1"'},
        json={"output":made["payload"]["output"]})
    assert blocked.status_code==422 and "phải sửa" in blocked.json()["detail"]
    assert blocked.headers["content-type"].startswith("application/json")

    payload=made["payload"];payload["tracks"][0]["cues"]=payload["tracks"][0]["cues"][:1]
    saved=a.put(f"/autosubvideo/api/projects/{made['id']}",headers={
        "X-CSRF-Token":token,"If-Match":'"1"'},json={"name":"preflight","payload":payload})
    quoted=a.post(endpoint,headers={"X-CSRF-Token":token,"If-Match":'"2"'},
        json={"output":saved.json()["payload"]["output"]})
    report=quoted.json()["quote"]["preflight"]
    assert quoted.status_code==200 and report["error_count"]==0
    assert report["warning_count"]>=2 and {"short","speed"}.issubset(report["issue_codes"])


def test_autosub_studio_bundle_is_hashed_fresh_and_in_release():
    import json
    from pathlib import Path
    from tools.build_release import collect_files, verify_frontend_bundle
    root = Path(__file__).resolve().parents[1]
    verify_frontend_bundle(str(root))
    manifest = json.loads((root / "server/static/autosub-studio/.vite/manifest.json")
                          .read_text("utf-8"))
    assets = [manifest["src/main.tsx"]["file"],
              *manifest["src/main.tsx"].get("css", [])]
    assert all(asset.startswith("assets/") and ".map" not in asset for asset in assets)
    files = {rel for _full, rel in collect_files(str(root))}
    assert "frontend/autosub-studio/package-lock.json" in files
    assert "server/static/autosub-studio/build-meta.json" in files


def test_studio_style_contract_and_ass_animation(tmp_path):
    from apps.autosubvideo.ass_builder import build_ass
    from apps.autosubvideo.schemas import StudioProjectV1, SubtitleStyleConfig
    from apps.autosubvideo.segmenter import SubtitleEvent
    project = StudioProjectV1.model_validate({"style": {
        "preset": "custom", "font_color": "#12AB34", "animation": "pop",
        "animation_ms": 240, "highlight_mode": "word"}})
    assert project.style.animation == "pop"
    path = tmp_path / "animated.ass"
    event = SubtitleEvent(start=0, end=2, text="Xin chao", display_text="Xin chao")
    build_ass([event], SubtitleStyleConfig(animation="pop", animation_ms=240),
              str(path), highlight_mode="word")
    text = path.read_text(encoding="utf-8-sig")
    assert r"\fscx70\fscy70\t(0,240,\fscx100\fscy100)" in text
    with pytest.raises(Exception):
        StudioProjectV1.model_validate({"style": {"font_color": "red;url(x)"}})


def test_studio_style_api_returns_typed_presets(studio_api):
    client, _token, *_ = studio_api
    response = client.get("/autosubvideo/api/styles")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 9
    assert all(item["config"]["font_color"].startswith("#") for item in items)
    brand = next(item for item in items if item["id"] == "ltt_brand")
    assert brand["highlight_color"] == "#EF3731"
    assert brand["config"]["max_chars_per_line"] == 34
    from apps.autosubvideo.schemas import StudioProjectV1
    with pytest.raises(Exception, match="speaker"):
        StudioProjectV1.model_validate({"speakers": {"S1": "x" * 81}})


def test_auxiliary_assignment_and_translation_are_bounded():
    from apps.autosubvideo.ai_workflows import (AuxiliaryAIError, assign_speakers,
                                                 translate_cues)
    cues = [{"id": "a", "start": 0, "end": 2, "text": "Xin", "words": []},
            {"id": "b", "start": 2, "end": 5, "text": "chào", "words": []}]
    updated, names = assign_speakers(cues, [
        {"start": 0, "end": 1.8, "speaker": "SPEAKER_00"},
        {"start": 2.1, "end": 5, "speaker": "SPEAKER_01"}])
    assert [item["speaker"] for item in updated] == ["SPEAKER_00", "SPEAKER_01"]
    assert names == {"SPEAKER_00": "Người nói 1", "SPEAKER_01": "Người nói 2"}
    translated = translate_cues(None, cues, "English", call=lambda batch: [
        {"id": item["id"], "text": "EN-" + item["text"]} for item in batch])
    assert translated[0]["text"] == "EN-Xin" and translated[0]["words"] == []
    with pytest.raises(AuxiliaryAIError):
        translate_cues(None, cues, "English", call=lambda _batch: [{"id": "wrong", "text": "x"}])


def test_auxiliary_routes_quota_owner_cancel_and_soft_disable(studio_api, monkeypatch):
    a, token_a, b, _token_b = studio_api
    import platform_core.db as dbmod
    from platform_core.models import User
    from platform_core.storage import get_storage
    db = next(dbmod.get_session())
    user = db.query(User).filter_by(email="studio-a@example.com").one(); owner = user.id
    db.close()
    payload = _payload(); payload["source"]["key"] = f"autosubvideo/{owner}/uploads/ai.mp4"
    get_storage().put(payload["source"]["key"], io.BytesIO(b"video"), "video/mp4")
    made = a.post("/autosubvideo/api/projects", headers={"X-CSRF-Token": token_a},
                  json={"name": "AI workflows", "payload": payload}).json()
    monkeypatch.setattr("apps.autosubvideo.ai_workflows.diarization_available", lambda: False)
    assert a.post(f"/autosubvideo/api/projects/{made['id']}/diarize", headers={
        "X-CSRF-Token": token_a, "If-Match": '"1"'}, json={}).status_code == 503
    monkeypatch.setattr("apps.autosubvideo.ai_workflows.diarization_available", lambda: True)
    diarize = a.post(f"/autosubvideo/api/projects/{made['id']}/diarize", headers={
        "X-CSRF-Token": token_a, "If-Match": '"1"'}, json={})
    assert diarize.status_code == 202 and diarize.json()["credit"] == 0
    job_id = diarize.json()["job_id"]
    assert b.get(f"/autosubvideo/api/jobs/{job_id}").status_code == 404
    cancelled = a.post(f"/autosubvideo/api/jobs/{job_id}/cancel",
                       headers={"X-CSRF-Token": token_a}, json={})
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    monkeypatch.setattr("apps.autosubvideo.ai_workflows.dich_kha_dung", lambda _db: True)
    translated = a.post(f"/autosubvideo/api/projects/{made['id']}/translate", headers={
        "X-CSRF-Token": token_a, "If-Match": '"1"'},
        json={"track_id": "source", "target_language": "en"})
    assert translated.status_code == 202 and translated.json()["credit"] == 0


def test_diarize_handler_applies_speakers_to_matching_revision(studio_api, monkeypatch):
    a, token, *_ = studio_api
    import platform_core.db as dbmod
    from platform_core.models import AppProject, User
    from platform_core.storage import get_storage
    db = next(dbmod.get_session()); user = db.query(User).filter_by(
        email="studio-a@example.com").one(); owner = user.id; db.close()
    payload = _payload(); payload["source"]["key"] = f"autosubvideo/{owner}/uploads/d.mp4"
    get_storage().put(payload["source"]["key"], io.BytesIO(b"video"), "video/mp4")
    made = a.post("/autosubvideo/api/projects", headers={"X-CSRF-Token": token},
                  json={"name": "Diarize", "payload": payload}).json()
    monkeypatch.setattr("apps.autosubvideo.ai_workflows.diarize_file", lambda *_a, **_k: [
        {"start": 0, "end": 4, "speaker": "SPEAKER_00"}])
    class Ctx:
        job_id = "job-diarize"
        def progress(self, *_args): pass
        def is_cancelled(self): return False
    from apps.autosubvideo.jobs import handle
    result = handle({"operation": "diarize", "owner_id": owner,
        "project_id": made["id"], "project_revision": 1,
        "video_key": payload["source"]["key"]}, Ctx())
    assert result["assigned_cues"] == 1 and result["speaker_count"] == 1
    db = next(dbmod.get_session()); row = db.get(AppProject, made["id"])
    assert row.payload["tracks"][0]["cues"][0]["speaker"] == "SPEAKER_00"
    db.close()
