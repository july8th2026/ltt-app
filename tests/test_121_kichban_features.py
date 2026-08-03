"""H15.S11.2 source/research/version/shot-list contract."""
from __future__ import annotations

import json
import re

from fastapi.testclient import TestClient


def test_context_directive_never_claims_external_research():
    from apps.kichban.features import context_directive
    text = context_directive("https://example.test/source", "Số liệu do user nhập")
    assert "do not invent citations" in text
    assert "https://example.test/source" in text and "Số liệu do user nhập" in text


def test_shot_list_and_project_payload_are_deterministic():
    from apps.kichban.features import derive_shot_list, project_payload
    script = {"title": "T", "hook": "H", "sections": [
        {"title": "Một", "content": "C1"}, {"title": "Hai", "content": "C2"}],
        "outro": "O"}
    shots = derive_shot_list(script)
    assert [x["scene"] for x in shots] == [1, 2, 3, 4]
    assert shots[0]["section"] == "Hook" and shots[-1]["section"] == "Outro & CTA"
    payload = project_payload(job_id="j1", script=script, sources="S", research="R")
    assert payload["kind"] == "script_project" and payload["source_job_id"] == "j1"
    assert payload["shot_list"] == shots


def test_build_worker_prompt_includes_user_sources(monkeypatch):
    from apps.kichban import jobs
    monkeypatch.setattr(jobs, "_lay_key", lambda: ("key", None))
    seen = {}
    def fake(prompt, _key):
        seen["prompt"] = prompt
        return '{"title":"T","hook":"H","sections":[],"outro":"","description":"","tags":[]}'
    monkeypatch.setattr(jobs, "_goi_gemini_text", fake)
    out = jobs.handle({"topic": "Chủ đề", "sources": "SOURCE-ABC",
                       "research": "RESEARCH-XYZ"})
    assert "SOURCE-ABC" in seen["prompt"] and "RESEARCH-XYZ" in seen["prompt"]
    assert out["shot_list"][0]["section"] == "Hook"


def test_script_version_route_enforces_owner_and_optimistic_revision(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'script.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.models import Job, User
    from platform_core.users import tao_nguoi_dung

    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    for email in ("script-a@example.com", "script-b@example.com"):
        tao_nguoi_dung(db, email=email, password="Strong-pass-123", is_verified=True)
    owner = db.query(User).filter_by(email="script-a@example.com").one()
    job = Job(user_id=owner.id, app_slug="kichban", job_type="kichban.generate",
              status="done", params={"sources": "S", "research": "R"},
              result={"script": {"title": "T", "hook": "H", "sections": [],
                                  "outro": "O", "description": "D", "tags": []},
                      "shot_list": []})
    db.add(job); db.commit(); job_id = job.id; db.close(); dbmod.reset_engine()
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test", "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "script-version-test-session", "LTT_ADMIN_USERNAME": "",
        "LTT_ADMIN_PASSWORD_HASH": ""})

    def login(email):
        client = TestClient(app, base_url="https://testserver", follow_redirects=True)
        page = client.get("/login")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        assert client.post("/login", data={"username": email, "password": "Strong-pass-123",
            "csrf_token": csrf, "next": "/kichban"}).status_code == 200
        studio = client.get("/kichban")
        token = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
        return client, token

    owner_client, token = login("script-a@example.com")
    script_json = json.dumps({"title": "Edited", "hook": "H", "sections": [],
                              "outro": "O", "description": "D", "tags": []})
    made = owner_client.post(f"/kichban/r/{job_id}/save", data={
        "csrf_token": token, "script_json": script_json, "sources": "S2",
        "research": "R2", "revision": 0})
    assert made.status_code == 200 and made.json()["revision"] == 1
    project_id = made.json()["project_id"]
    saved = owner_client.post(f"/kichban/r/{job_id}/save", data={
        "csrf_token": token, "script_json": script_json, "project_id": project_id,
        "revision": 1, "sources": "S3", "research": "R3"})
    assert saved.status_code == 200 and saved.json()["revision"] == 2
    stale = owner_client.post(f"/kichban/r/{job_id}/save", data={
        "csrf_token": token, "script_json": script_json, "project_id": project_id,
        "revision": 1})
    assert stale.status_code == 409
    other, other_token = login("script-b@example.com")
    assert other.post(f"/kichban/r/{job_id}/save", data={
        "csrf_token": other_token, "script_json": script_json,
        "project_id": project_id, "revision": 2}).status_code == 404
    owner_client.close(); other.close(); dbmod.reset_engine()
