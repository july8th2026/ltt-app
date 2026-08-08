"""H19 PROMPT AI OMMI: schema, worker and owner-scoped API contracts."""
from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient


def test_manifest_and_schema_are_public_versioned_and_defensive():
    from apps.prompt_ai_ommi.manifest import MANIFEST
    from apps.prompt_ai_ommi.project_schema import clean_project, empty_project
    assert MANIFEST.public is True
    assert {tool.name for tool in MANIFEST.tools} == {
        "text.prompt_package", "story.storyboard"}
    payload = empty_project("Demo")
    payload["brief"].update({"duration_seconds": "invalid", "scene_count": 999})
    payload["resources"] = [{"size": "invalid", "kind": "unknown"}]
    payload["scenes"] = [{"duration_seconds": "invalid", "selected_version": "bad"}]
    clean = clean_project(payload)
    assert clean["version"] == 1
    assert clean["brief"]["duration_seconds"] == 30
    assert clean["brief"]["scene_count"] == 20
    assert clean["resources"][0]["kind"] == "prop"
    assert clean["scenes"][0]["duration_seconds"] == 5


def test_production_rollout_defaults_off(monkeypatch):
    from apps.prompt_ai_ommi.routes._shared import _run_mode
    monkeypatch.delenv("LTT_PROMPT_AI_OMMI_ROLLOUT", raising=False)
    monkeypatch.setenv("LTT_ENV", "production")
    assert _run_mode() == "off"
    monkeypatch.setenv("LTT_PROMPT_AI_OMMI_ROLLOUT", "allowlist")
    assert _run_mode() == "allowlist"


def test_ui_has_real_lifecycle_batch_and_hidden_state_guards():
    source = (Path(__file__).parents[1] / "apps" / "prompt_ai_ommi" /
              "templates" / "prompt_ai_ommi.html").read_text(encoding="utf-8")
    assert ".ommi [hidden]{display:none!important}" in source
    assert ".ommi:not(.inspecting) .ommi-inspector{display:none}" in source
    assert "async function saveCurrent()" in source
    assert "await saveCurrent()" in source
    assert "/handoff-batch/image" in source
    for control in ("import-project", "clone-btn", "archive-btn", "theme-toggle"):
        assert f"$('#{control}').on" in source


def test_preview_and_worker_normalize_provider_output(monkeypatch):
    from apps.prompt_ai_ommi import jobs
    from apps.prompt_ai_ommi.project_schema import empty_project, prompt_job_params
    from apps.prompt_ai_ommi.services.composer import preview
    project = empty_project("Phim thử")
    project["brief"]["story"] = "Một câu chuyện đủ dài để AI có thể phân tích thành nhiều cảnh."
    project["resources"] = [{"id": "r1", "kind": "image", "name": "Nhân vật",
                             "description": "áo đỏ", "storage_key": "", "size": 0}]
    check = preview(project)
    assert check["valid"] is True and "@IMAGE_1" in check["master_prompt"]
    params = prompt_job_params(project, operation="director", model="gemini-2.5-flash")
    monkeypatch.setattr(jobs.provider, "generate_json", lambda *_args, **_kwargs: ({
        "summary": "Gói cảnh", "anchors": {"style": "cinematic"},
        "scenes": [{"title": "Mở đầu", "prompt": "Wide establishing shot"}],
    }, 123))
    result = jobs.handle(params)
    assert result["tokens_used"] == 123
    assert len(result["prompt_package"]["scenes"]) == project["brief"]["scene_count"]
    assert result["prompt_package"]["scenes"][0]["versions"]


def _build_app(tmp_path, monkeypatch):
    db_path = (tmp_path / "ommi.db").as_posix()
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "ommi-test-session-secret")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    import platform_core.storage as storage_mod
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    from platform_core.credit import cap_tay
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        for email in ("ommi-a@example.com", "ommi-b@example.com"):
            user = tao_nguoi_dung(db, email=email, password="Strong-pass-123",
                                  is_verified=True)
            db.flush(); cap_tay(db, user.id, 200, by="pytest", note="PROMPT AI OMMI")
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    return create_app(env={"LTT_ENV": "development", "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "ommi-test-session-secret", "LTT_ADMIN_USERNAME": "",
        "LTT_ADMIN_PASSWORD_HASH": ""}), dbmod, storage_mod


def _login(app, email):
    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={"username": email, "password": "Strong-pass-123",
        "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
    studio = client.get("/prompt-ai-ommi")
    assert studio.status_code == 200 and "Prompt AI" in studio.text
    csrf = re.search(r'data-csrf-token="([^"]+)"', studio.text).group(1)
    return client, csrf


def test_project_revision_preferences_credit_and_ownership(tmp_path, monkeypatch):
    app, dbmod, storage_mod = _build_app(tmp_path, monkeypatch)
    owner, csrf = _login(app, "ommi-a@example.com")
    try:
        made = owner.post("/prompt-ai-ommi/api/projects", headers={"X-CSRF-Token": csrf},
                          json={"name": "Campaign"})
        assert made.status_code == 201
        project = made.json(); project_id = project["id"]
        payload = project["payload"]
        payload["brief"]["story"] = "Một câu chuyện quảng cáo đủ dài để chạy AI Director an toàn."
        saved = owner.put(f"/prompt-ai-ommi/api/projects/{project_id}",
            headers={"X-CSRF-Token": csrf}, json={"revision": project["revision"],
                                                  "payload": payload})
        assert saved.status_code == 200 and saved.json()["revision"] == project["revision"] + 1
        stale = owner.put(f"/prompt-ai-ommi/api/projects/{project_id}",
            headers={"X-CSRF-Token": csrf}, json={"revision": 0, "payload": payload})
        assert stale.status_code == 409
        preference = owner.put("/prompt-ai-ommi/api/preferences",
            headers={"X-CSRF-Token": csrf}, json={"theme": "dark", "revision": 0})
        assert preference.status_code == 200 and preference.json()["theme"] == "dark"
        assert owner.get("/prompt-ai-ommi/api/preferences").json()["theme"] == "dark"
        quote = owner.post(f"/prompt-ai-ommi/api/projects/{project_id}/quote",
            headers={"X-CSRF-Token": csrf}, json={"operation": "director"})
        assert quote.status_code == 200 and quote.json()["credit"] > 0
        job = owner.post(f"/prompt-ai-ommi/api/projects/{project_id}/generate",
            headers={"X-CSRF-Token": csrf}, json={"operation": "director"})
        assert job.status_code == 201 and job.json()["status"] == "queued"
        package = owner.get(f"/prompt-ai-ommi/api/projects/{project_id}/export/json")
        assert package.status_code == 200 and package.json()["format"] == "ltt-prompt-ai-ommi"
        imported = owner.post("/prompt-ai-ommi/api/import",
            headers={"X-CSRF-Token": csrf}, json=package.json())
        assert imported.status_code == 201
        other, _ = _login(app, "ommi-b@example.com")
        try:
            assert other.get(f"/prompt-ai-ommi/api/projects/{project_id}").status_code == 404
        finally:
            other.close()
    finally:
        owner.close(); dbmod.reset_engine(); storage_mod._storage = None


def test_image_handoff_normalizes_ultrawide_and_quotes_before_submit(tmp_path, monkeypatch):
    app, dbmod, storage_mod = _build_app(tmp_path, monkeypatch)
    client, csrf = _login(app, "ommi-a@example.com")
    try:
        payload = {"name": "Handoff"}
        made = client.post("/prompt-ai-ommi/api/projects",
            headers={"X-CSRF-Token": csrf}, json=payload).json()
        body = made["payload"]; body["brief"]["aspect_ratio"] = "21:9"
        body["scenes"] = [{"id": "scene_one", "title": "Cảnh", "duration_seconds": 7,
                           "prompt": "A cinematic wide landscape with one red vehicle"}]
        saved = client.put(f"/prompt-ai-ommi/api/projects/{made['id']}",
            headers={"X-CSRF-Token": csrf},
            json={"revision": made["revision"], "payload": body}).json()
        quote = client.post(f"/prompt-ai-ommi/api/projects/{made['id']}/handoff/image",
            headers={"X-CSRF-Token": csrf}, json={"scene_id": "scene_one"})
        assert saved["revision"] == made["revision"] + 1
        assert quote.status_code == 200
        assert quote.json()["confirmed"] is False and quote.json()["credit"] > 0
        batch = client.post(f"/prompt-ai-ommi/api/projects/{made['id']}/handoff-batch/image",
            headers={"X-CSRF-Token": csrf}, json={"scene_ids": ["scene_one"]})
        assert batch.status_code == 200
        assert batch.json()["count"] == 1 and batch.json()["confirmed"] is False
    finally:
        client.close(); dbmod.reset_engine(); storage_mod._storage = None
