"""H15.S12.2 Clip score/brand/social package contract."""
from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient


def test_brand_platform_rationale_and_srt_helpers():
    from apps.taoclipngan.features import (brand_overrides, clean_brand,
        clean_platforms, platform_copy, score_rationale, srt_text)
    assert clean_brand("bad") == "auto"
    assert brand_overrides("ltt_red")["caption_preset"] == "viral_pop"
    assert clean_platforms(["tiktok", "bad", "tiktok"]) == ["tiktok"]
    assert set(clean_platforms([])) == {"tiktok", "youtube_shorts", "instagram_reels"}
    copy = platform_copy("T" * 200, "D", ["LTT"], ["youtube_shorts"])
    assert len(copy["youtube_shorts"]["title"]) == 100

    class Score:
        overall = .9; hook_strength = .8; pacing = .7; completeness = .6
        visual_quality = .5; audio_quality = .4; topic_coherence = .3
        semantic_richness = .2
    class Candidate:
        score = Score(); explanation = None; why_selected = "Vì hook rõ"
        strategy_reasoning = ""; clip_intent = "insight"; risk_flags = []
    rationale = score_rationale(Candidate())
    assert rationale["overall"] == .9 and rationale["dimensions"]["pacing"] == .7
    assert "00:00:01,250 --> 00:00:03,500" in srt_text([
        {"start": 1.25, "end": 3.5, "text": "Xin chào"}])


def test_clip_feature_controls_are_wired_to_worker_and_routes():
    root = Path(__file__).parents[1]
    template = (root / "apps" / "taoclipngan" / "templates" /
                "taoclipngan.html").read_text("utf-8")
    worker = (root / "apps" / "taoclipngan" / "jobs.py").read_text("utf-8")
    routes = (root / "apps" / "taoclipngan" / "routes.py").read_text("utf-8")
    assert 'name="brand_preset"' in template and 'name="platforms"' in template
    assert "Vì sao AI chọn đoạn này?" in template and "clip-save-package" in template
    assert "user_overrides=brand_overrides(brand_preset)" in worker
    assert "score_rationale(cand)" in worker and "platform_copy(" in worker
    assert '@router.get("/package/{job_id}.zip")' in routes


def test_package_save_revision_zip_and_ownership(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'package.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    import platform_core.storage as storage_mod
    from platform_core.models import Job, User
    from platform_core.users import tao_nguoi_dung

    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    for email in ("package-a@example.com", "package-b@example.com"):
        tao_nguoi_dung(db, email=email, password="Strong-pass-123", is_verified=True)
    owner = db.query(User).filter_by(email="package-a@example.com").one()
    key = f"taoclipngan/{owner.id}/job/clip.mp4"
    storage_mod.get_storage().put(key, io.BytesIO(b"real-video-bytes"), "video/mp4")
    job = Job(user_id=owner.id, app_slug="taoclipngan",
              job_type="taoclipngan.render", status="done",
              params={"brand_preset": "ltt_red", "source_filename": "source.mp4"},
              result={"platforms": ["tiktok"], "clips": [{"video_key": key,
                  "title": "Original", "duration_s": 3, "source_start": 0,
                  "source_end": 3, "transcript": [{"start": 0, "end": 3,
                  "text": "Original transcript"}]}]})
    db.add(job); db.commit(); job_id = job.id; db.close(); dbmod.reset_engine()
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test", "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "clip-package-test-session", "LTT_ADMIN_USERNAME": "",
        "LTT_ADMIN_PASSWORD_HASH": ""})

    def login(email):
        client = TestClient(app, base_url="https://testserver", follow_redirects=True)
        page = client.get("/login")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        assert client.post("/login", data={"username": email,
            "password": "Strong-pass-123", "csrf_token": csrf,
            "next": "/taoclipngan"}).status_code == 200
        studio = client.get("/taoclipngan")
        token = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
        return client, token

    owner_client, token = login("package-a@example.com")
    draft = json.dumps({"platforms": ["tiktok", "youtube_shorts"],
        "clips": [{"index": 0, "title": "Edited", "transcript_text": "Edited caption"}]})
    made = owner_client.post(f"/taoclipngan/package/{job_id}/save", data={
        "csrf_token": token, "package_json": draft, "revision": 0})
    assert made.status_code == 200 and made.json()["revision"] == 1
    project_id = made.json()["project_id"]
    stale = owner_client.post(f"/taoclipngan/package/{job_id}/save", data={
        "csrf_token": token, "package_json": draft, "project_id": project_id,
        "revision": 0})
    assert stale.status_code == 409
    archive_response = owner_client.get(f"/taoclipngan/package/{job_id}.zip")
    assert archive_response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(archive_response.content)) as archive:
        assert {"clips/clip_01.mp4", "captions/clip_01.srt", "package.json",
                "README.txt"}.issubset(archive.namelist())
        assert "Edited caption" in archive.read("captions/clip_01.srt").decode("utf-8")
        manifest = json.loads(archive.read("package.json"))
        assert manifest["brand_preset"] == "ltt_red"
        assert set(manifest["platforms"]) == {"tiktok", "youtube_shorts"}
    other, _ = login("package-b@example.com")
    assert other.get(f"/taoclipngan/package/{job_id}.zip").status_code == 404
    owner_client.close(); other.close(); dbmod.reset_engine(); storage_mod._storage = None
