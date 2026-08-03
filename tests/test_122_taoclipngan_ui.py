"""H15.S12.1 Clip Studio source/transcript/compare UI contract."""
import io
import json
import re
from pathlib import Path

from fastapi.testclient import TestClient


def test_clip_template_has_library_transcript_compare_and_accessibility():
    template = (Path(__file__).parents[1] / "apps" / "taoclipngan" /
                "templates" / "taoclipngan.html").read_text("utf-8")
    assert 'class="clip-studio"' in template
    assert "Thư viện nguồn gần đây" in template and "clip-source" in template
    assert "Transcript & biên tập package" in template and "data-transcript" in template
    assert 'id="clip-compare"' in template and "clip-pick" in template
    assert 'role="progressbar"' in template and 'role="status"' in template
    assert "innerHTML" not in template and "onclick=" not in template
    assert template.count('style="') == 1
    assert 'style="width:{{ job.progress }}%"' in template


def test_clip_css_is_scoped_and_responsive():
    css = (Path(__file__).parents[1] / "server" / "static" / "ltt.css").read_text("utf-8")
    assert ".clip-studio" in css and ".clip-compare-grid" in css
    assert "@media(max-width:560px){.clip-heading" in css


def test_clip_worker_exposes_timed_transcript_for_real_outputs():
    source = (Path(__file__).parents[1] / "apps" / "taoclipngan" /
              "jobs.py").read_text("utf-8")
    assert '"source_start"' in source and '"source_end"' in source
    assert '"transcript": captions' in source and "caption_segments" in source


def test_clip_source_library_is_storage_backed_and_owner_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'clip.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    import platform_core.storage as storage_mod
    from platform_core.models import Job, User
    from platform_core.users import tao_nguoi_dung

    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    for email in ("clip-a@example.com", "clip-b@example.com"):
        tao_nguoi_dung(db, email=email, password="Strong-pass-123", is_verified=True)
    users = {row.email: row for row in db.query(User).all()}
    for email, name in (("clip-a@example.com", "owner-video.mp4"),
                        ("clip-b@example.com", "other-video.mp4")):
        user = users[email]; key = f"taoclipngan/{user.id}/uploads/{name}"
        storage_mod.get_storage().put(key, io.BytesIO(b"video"), "video/mp4")
        db.add(Job(user_id=user.id, app_slug="taoclipngan",
                   job_type="taoclipngan.render", status="done",
                   params={"video_key": key, "source_filename": name,
                           "duration_s": 12}, result={"clips": []}))
    db.commit(); db.close(); dbmod.reset_engine()
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test", "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "clip-library-test-session", "LTT_ADMIN_USERNAME": "",
        "LTT_ADMIN_PASSWORD_HASH": ""})
    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={"username": "clip-a@example.com",
        "password": "Strong-pass-123", "csrf_token": token,
        "next": "/taoclipngan"}).status_code == 200
    studio = client.get("/taoclipngan")
    assert "owner-video.mp4" in studio.text
    assert "other-video.mp4" not in studio.text
    client.close(); dbmod.reset_engine(); storage_mod._storage = None
