"""P10 HTTP API: CSRF, ownership, ETag, palette and import/export."""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from platform_core.agent.workflows import plan_to_canvas


def _plan():
    return {"version": 1, "goal": "Viết kịch bản kiểm thử", "budget_max_credit": 50,
            "steps": [{"id": "s1", "tool": "text.script", "after": [],
                       "fanout": 1, "max_retry": 0, "on_fail": "retry_same",
                       "verify": None, "params": {"topic": "Một chủ đề hữu ích"}}]}


def _csrf(html: str) -> str:
    match = re.search(r'data-csrf-token="([^"]+)"', html)
    assert match
    return match.group(1)


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'api.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    for email in ("canvas-a@example.com", "canvas-b@example.com"):
        tao_nguoi_dung(db, email=email, password="Strong-pass-123", is_verified=True)
    db.commit(); db.close(); dbmod.reset_engine()
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test", "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "workflow-api-test-session", "LTT_ADMIN_USERNAME": "",
        "LTT_ADMIN_PASSWORD_HASH": ""})

    def login(email):
        client = TestClient(app, base_url="https://testserver", follow_redirects=True)
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        assert client.post("/login", data={"username": email, "password": "Strong-pass-123",
            "csrf_token": token, "next": "/agent/canvas"}).status_code == 200
        canvas = client.get("/agent/canvas")
        return client, _csrf(canvas.text)

    a, token_a = login("canvas-a@example.com")
    b, token_b = login("canvas-b@example.com")
    yield a, token_a, b, token_b
    a.close(); b.close(); dbmod.reset_engine()


def _create(client, token, *, name="Workflow A"):
    return client.post("/agent/api/workflows", headers={"X-CSRF-Token": token},
                       json={"name": name, "canvas": plan_to_canvas(_plan())})


def test_crud_etag_stale_conflict_and_csrf(api):
    a, token, *_ = api
    assert a.post("/agent/api/workflows", json={}).status_code == 400
    created = _create(a, token)
    assert created.status_code == 201 and created.headers["etag"] == '"1"'
    workflow = created.json(); wid = workflow["id"]
    assert a.get("/agent/api/workflows").json()["items"][0]["id"] == wid
    assert a.get(f"/agent/api/workflows/{wid}").json()["canvas"] == workflow["canvas"]
    canvas = workflow["canvas"]; canvas["goal"] = "Mục tiêu đã sửa"
    saved = a.put(f"/agent/api/workflows/{wid}", headers={
        "X-CSRF-Token": token, "If-Match": '"1"'}, json={"name": "Mới", "canvas": canvas})
    assert saved.status_code == 200 and saved.json()["revision"] == 2
    stale = a.put(f"/agent/api/workflows/{wid}", headers={
        "X-CSRF-Token": token, "If-Match": '"1"'}, json={"name": "Cũ", "canvas": canvas})
    assert stale.status_code == 409


def test_ownership_clone_archive_import_export(api):
    a, token_a, b, token_b = api
    row = _create(a, token_a).json(); wid = row["id"]
    assert b.get(f"/agent/api/workflows/{wid}").status_code == 404
    assert b.put(f"/agent/api/workflows/{wid}", headers={"X-CSRF-Token": token_b},
                 json={"revision": 1, "name": "chiếm", "canvas": row["canvas"]}).status_code == 404
    assert b.post(f"/agent/api/workflows/{wid}/clone",
                  headers={"X-CSRF-Token": token_b}, json={}).status_code == 404
    clone = a.post(f"/agent/api/workflows/{wid}/clone",
                   headers={"X-CSRF-Token": token_a}, json={})
    assert clone.status_code == 201 and clone.json()["source_workflow_id"] == wid
    exported = a.get(f"/agent/api/workflows/{wid}/export")
    assert exported.status_code == 200 and exported.json()["format"] == "ltt-agent-workflow"
    imported = a.post("/agent/api/workflows/import", headers={"X-CSRF-Token": token_a},
                      json=exported.json())
    assert imported.status_code == 201
    archived = a.post(f"/agent/api/workflows/{wid}/archive",
                      headers={"X-CSRF-Token": token_a}, json={})
    assert archived.json()["status"] == "archived"
    assert a.put(f"/agent/api/workflows/{wid}", headers={"X-CSRF-Token": token_a},
                 json={"revision": archived.json()["revision"], "name": "x",
                       "canvas": row["canvas"]}).status_code == 422
    assert a.delete(f"/agent/api/workflows/{wid}").status_code == 405


def test_validate_server_price_and_palette_are_authoritative(api):
    a, token, *_ = api
    row = _create(a, token).json(); wid = row["id"]
    result = a.post(f"/agent/api/workflows/{wid}/validate", headers={
        "X-CSRF-Token": token, "If-Match": '"1"'}, json={})
    assert result.status_code == 200 and result.json()["validation"]["valid"]
    assert result.json()["estimated"] > 0 and result.json()["status"] == "validated"
    palette = a.get("/agent/api/palette").json()
    assert palette["version"] == 2 and len(palette["tools"]) == 20
    assert palette["routing"]["mode"] == "platform_auto"
    assert any(model["id"] == "seedance-2.0" and len(model["providers"]) == 2
               for model in palette["models"])
    assert all("price" not in tool and "params_schema" in tool for tool in palette["tools"])
    assert {tool["name"]: tool["label"] for tool in palette["tools"] if tool["primary"]} == {
        "text.generate": "Tạo văn bản", "image.generate": "Tạo hình ảnh",
        "video.generate": "Tạo video"}
    quote = a.post("/agent/api/tools/text.script/quote",
        headers={"X-CSRF-Token": token}, json={"params": {"topic": "Chủ đề hợp lệ"},
        "fanout": 2, "max_retry": 1})
    assert quote.status_code == 200
    assert quote.json()["maximum"] == quote.json()["unit"] * 4
    assert quote.json()["authoritative"] is True
    bad = a.post("/agent/api/tools/text.script/quote",
        headers={"X-CSRF-Token": token}, json={"params": {}})
    assert bad.status_code == 200 and bad.json()["valid"] is False
    assert bad.json()["maximum"] is None and bad.json()["authoritative"] is True


def test_canvas_preferences_are_validated_and_owned_per_user(api):
    a, token_a, b, _ = api
    assert a.get("/agent/api/preferences").json() == {
        "theme": "dark", "catalog_mode": "advanced", "revision": 0}
    assert a.put("/agent/api/preferences", json={
        "theme": "dark", "catalog_mode": "advanced"}).status_code == 400
    saved = a.put("/agent/api/preferences", headers={"X-CSRF-Token": token_a}, json={
        "theme": "dark", "catalog_mode": "advanced"})
    assert saved.status_code == 200
    assert saved.json() == {"theme": "dark", "catalog_mode": "advanced", "revision": 1}
    assert a.get("/agent/api/preferences").json()["theme"] == "dark"
    assert b.get("/agent/api/preferences").json()["theme"] == "dark"
    assert a.put("/agent/api/preferences", headers={"X-CSRF-Token": token_a}, json={
        "theme": "blue", "catalog_mode": "simple"}).status_code == 422


def test_import_pathological_and_client_price_are_rejected(api):
    a, token, *_ = api
    body = {"format": "ltt-agent-workflow", "version": 1, "name": "độc",
            "canvas": plan_to_canvas(_plan())}
    body["canvas"]["nodes"][0]["data"]["price"] = 0
    assert a.post("/agent/api/workflows/import", headers={"X-CSRF-Token": token},
                  json=body).status_code == 422
    deep = {"format": "ltt-agent-workflow", "version": 1, "name": "sâu",
            "canvas": {"version": 1, "nodes": [], "edges": [], "viewport": {}}}
    cursor = deep["canvas"]
    for _ in range(22):
        cursor["x"] = {}; cursor = cursor["x"]
    assert a.post("/agent/api/workflows/import", headers={"X-CSRF-Token": token},
                  json=deep).status_code == 422


def test_workflow_snapshot_quote_approve_and_run_again_are_revision_bound(api):
    a, token_a, b, token_b = api
    workflow = _create(a, token_a).json(); wid = workflow["id"]
    validated = a.post(f"/agent/api/workflows/{wid}/validate", headers={
        "X-CSRF-Token": token_a, "If-Match": '"1"'}, json={}).json()
    revision = validated["revision"]
    stale = a.post(f"/agent/api/workflows/{wid}/runs", headers={
        "X-CSRF-Token": token_a, "If-Match": '"1"'}, json={})
    assert stale.status_code == 409
    created = a.post(f"/agent/api/workflows/{wid}/runs", headers={
        "X-CSRF-Token": token_a, "If-Match": f'"{revision}"'}, json={})
    assert created.status_code == 201
    run = created.json()
    assert run["status"] == "awaiting_approval" and len(run["quote_hash"]) == 64
    listing = a.get("/agent/api/runs").json()["items"]
    assert listing[0]["id"] == run["id"] and "plan" not in listing[0]
    assert a.get(f"/agent/api/runs/{run['id']}").json()["plan"] == run["plan"]
    assert b.get("/agent/api/runs").json()["items"] == []
    assert b.get(f"/agent/api/runs/{run['id']}").status_code == 404
    assert b.post(f"/agent/api/runs/{run['id']}/approve", headers={
        "X-CSRF-Token": token_b}, json={"version": run["version"],
        "quote_hash": run["quote_hash"]}).status_code == 404
    assert a.post(f"/agent/api/runs/{run['id']}/approve", headers={
        "X-CSRF-Token": token_a}, json={"version": run["version"],
        "quote_hash": "0" * 64}).status_code == 409

    import platform_core.db as dbmod
    from platform_core import credit
    from platform_core.models import User
    db = next(dbmod.get_session())
    user = db.query(User).filter_by(email="canvas-a@example.com").one()
    credit.cap_tay(db, user.id, 100, by="test"); db.commit(); db.close()
    approved = a.post(f"/agent/api/runs/{run['id']}/approve", headers={
        "X-CSRF-Token": token_a}, json={"version": run["version"],
        "quote_hash": run["quote_hash"]})
    assert approved.status_code == 200 and approved.json()["status"] == "running"
    again = a.post(f"/agent/api/runs/{run['id']}/again", headers={
        "X-CSRF-Token": token_a}, json={})
    assert again.status_code == 201 and again.json()["id"] != run["id"]
    assert again.json()["plan"] == run["plan"]


def test_schedule_uses_durable_queue_and_run_snapshot_restores_workflow(api, monkeypatch):
    a, token_a, b, token_b = api
    workflow = _create(a, token_a).json()
    validated = a.post(f"/agent/api/workflows/{workflow['id']}/validate", headers={
        "X-CSRF-Token": token_a, "If-Match": '"1"'}, json={}).json()
    run = a.post(f"/agent/api/workflows/{workflow['id']}/runs", headers={
        "X-CSRF-Token": token_a, "If-Match": f'"{validated["revision"]}"'}, json={}).json()

    import platform_core.db as dbmod
    from platform_core import credit
    from platform_core.models import Job, User
    db = next(dbmod.get_session())
    user = db.query(User).filter_by(email="canvas-a@example.com").one()
    credit.cap_tay(db, user.id, 100, by="test"); db.commit(); db.close()
    scheduled = datetime.now(timezone.utc) + timedelta(minutes=20)
    approved = a.post(f"/agent/api/runs/{run['id']}/approve", headers={
        "X-CSRF-Token": token_a}, json={"version": run["version"],
        "quote_hash": run["quote_hash"], "scheduled_at": scheduled.isoformat()})
    assert approved.status_code == 200
    assert approved.json()["scheduled_at"] == scheduled.isoformat()

    called = []
    monkeypatch.setattr("apps.agent.routes.jobs.advance",
                        lambda *_args, **_kwargs: called.append(True))
    early = a.post(f"/agent/api/runs/{run['id']}/tick",
                   headers={"X-CSRF-Token": token_a}, json={})
    assert early.status_code == 200 and early.json()["status"] == "running"
    assert called == []

    db = next(dbmod.get_session())
    queued = db.query(Job).filter_by(job_type="agent.advance").one()
    queued_at = queued.next_run_at.replace(tzinfo=queued.next_run_at.tzinfo or timezone.utc)
    assert queued.status == "queued" and queued_at >= scheduled - timedelta(seconds=1)
    db.close()

    assert b.post(f"/agent/api/runs/{run['id']}/restore-workflow",
                  headers={"X-CSRF-Token": token_b}, json={}).status_code == 404
    restored = a.post(f"/agent/api/runs/{run['id']}/restore-workflow",
                      headers={"X-CSRF-Token": token_a}, json={})
    assert restored.status_code == 201
    assert restored.json()["canvas"] == workflow["canvas"]

    from apps.agent import jobs as agent_jobs
    from platform_core.agent import runs as agent_runs
    monkeypatch.setattr(agent_jobs, "advance", lambda session, *, run_id, user_id:
                        agent_runs.get_owned(session, run_id, user_id))
    result = agent_jobs.handle({"run_id": run["id"], "user_id": user.id},
                               SimpleNamespace(job_id=queued.id))
    assert result["status"] == "running"
    db = next(dbmod.get_session())
    assert db.query(Job).filter(Job.dedupe_key ==
        f"agent:advance:{run['id']}:after:{queued.id}").count() == 1
    db.close()


def test_prompt_creates_editable_canvas_without_approval(api, monkeypatch):
    a, token, *_ = api
    monkeypatch.setattr("apps.agent.routes.plan_once", lambda *_args, **_kwargs: _plan())
    response = a.post("/agent/api/workflows/plan", headers={"X-CSRF-Token": token},
                      json={"goal": "Tạo nội dung kiểm thử bằng tiếng Việt",
                            "budget_max_credit": 50})
    assert response.status_code == 201
    assert response.json()["status"] == "draft"
    assert response.json()["canvas"]["nodes"][0]["data"]["tool"] == "text.script"


def test_api_round_trips_canvas_v2_without_losing_non_execution_content(api):
    a, token, *_ = api
    legacy = plan_to_canvas(_plan())
    canvas = {"version": 2, "goal": legacy["goal"],
              "budget_max_credit": legacy["budget_max_credit"],
              "active_page_id": "p1", "pages": [{"id": "p1", "name": "Trang chính",
                  "nodes": legacy["nodes"], "edges": legacy["edges"],
                  "viewport": legacy["viewport"],
                  "frames": [{"id": "f1", "name": "Nhóm 1", "node_ids": ["s1"]}],
                  "notes": [{"id": "n1", "text": "Ghi chú"}], "comments": []}]}
    created = a.post("/agent/api/workflows", headers={"X-CSRF-Token": token},
                     json={"name": "Workflow v2", "canvas": canvas})
    assert created.status_code == 201 and created.json()["canvas"] == canvas
    wid = created.json()["id"]
    validated = a.post(f"/agent/api/workflows/{wid}/validate", headers={
        "X-CSRF-Token": token, "If-Match": '"1"'}, json={})
    assert validated.status_code == 200 and validated.json()["validation"]["valid"]
    exported = a.get(f"/agent/api/workflows/{wid}/export").json()
    assert exported["canvas"] == canvas


def test_production_feature_off_blocks_new_run_but_keeps_workflow(api, monkeypatch):
    a, token, *_ = api
    workflow = _create(a, token).json()
    validated = a.post(f"/agent/api/workflows/{workflow['id']}/validate", headers={
        "X-CSRF-Token": token, "If-Match": '"1"'}, json={}).json()
    monkeypatch.setenv("LTT_AGENT_CANVAS_RUN_ENABLED", "0")
    blocked = a.post(f"/agent/api/workflows/{workflow['id']}/runs", headers={
        "X-CSRF-Token": token, "If-Match": f'"{validated["revision"]}"'}, json={})
    assert blocked.status_code == 503
    assert a.get(f"/agent/api/workflows/{workflow['id']}").status_code == 200


def test_assistant_preview_khong_mutate_va_apply_can_token_da_ky(api, monkeypatch):
    a, token, *_ = api
    workflow = _create(a, token).json(); wid = workflow["id"]
    monkeypatch.setenv("LTT_SESSION_SECRET", "assistant-test-secret")
    import apps.agent.routes as routes
    proposal = _plan(); proposal["goal"] = "Workflow đã cải tiến"
    monkeypatch.setattr(routes, "plan_once", lambda *_args, **_kwargs: proposal)
    preview = a.post(f"/agent/api/workflows/{wid}/assistant/preview", headers={
        "X-CSRF-Token": token, "If-Match": '"1"'},
        json={"mode": "improve", "prompt": "Cải thiện workflow"})
    assert preview.status_code == 200 and "event: analysis" in preview.text
    packet = next(part for part in preview.text.split("\n\n") if part.startswith("event: proposal"))
    payload = json.loads(next(line[6:] for line in packet.splitlines() if line.startswith("data: ")))
    assert a.get(f"/agent/api/workflows/{wid}").json()["revision"] == 1
    applied = a.post(f"/agent/api/workflows/{wid}/assistant/apply",
                     headers={"X-CSRF-Token": token}, json={"token": payload["token"]})
    assert applied.status_code == 200 and applied.json()["revision"] == 2
    assert applied.json()["canvas"]["goal"] == "Workflow đã cải tiến"
    tampered = payload["token"][:-1] + ("a" if payload["token"][-1] != "a" else "b")
    assert a.post(f"/agent/api/workflows/{wid}/assistant/apply",
                  headers={"X-CSRF-Token": token}, json={"token": tampered}).status_code == 409


def test_snapshot_share_view_clone_revoke_va_activity(api):
    a, token_a, b, token_b = api
    workflow = _create(a, token_a).json(); wid = workflow["id"]
    snapshots = a.get(f"/agent/api/workflows/{wid}/snapshots").json()["items"]
    assert snapshots[0]["revision"] == 1
    view = a.post(f"/agent/api/workflows/{wid}/shares", headers={"X-CSRF-Token": token_a},
                  json={"permission": "view", "expires_hours": 1})
    assert view.status_code == 201 and "token" not in view.json()
    view_path = view.json()["path"]
    assert b.get(view_path).json()["workflow"]["id"] == wid
    assert b.post(view_path + "/clone", headers={"X-CSRF-Token": token_b}, json={}).status_code == 403
    clone = a.post(f"/agent/api/workflows/{wid}/shares", headers={"X-CSRF-Token": token_a},
                   json={"permission": "clone", "expires_hours": 1}).json()
    copied = b.post(clone["path"] + "/clone", headers={"X-CSRF-Token": token_b}, json={})
    assert copied.status_code == 201 and copied.json()["source_workflow_id"] == wid
    revoked = a.post(f"/agent/api/workflows/{wid}/shares/{view.json()['id']}/revoke",
                     headers={"X-CSRF-Token": token_a}, json={})
    assert revoked.json()["revoked"] is True and b.get(view_path).status_code == 404
    events = a.get(f"/agent/api/workflows/{wid}/activity").json()["items"]
    assert {item["event"] for item in events} >= {"snapshot", "share_created", "share_revoked"}


def test_production_rollout_admin_then_allowlist(api, monkeypatch):
    a, token_a, b, token_b = api
    import platform_core.db as dbmod
    from platform_core.models import User
    db = next(dbmod.get_session())
    user_a = db.query(User).filter_by(email="canvas-a@example.com").one()
    user_b = db.query(User).filter_by(email="canvas-b@example.com").one()
    user_b.role = "admin"
    allowed_id = user_a.id
    db.commit(); db.close()

    def create_run(client, token):
        workflow = _create(client, token).json()
        validated = client.post(f"/agent/api/workflows/{workflow['id']}/validate", headers={
            "X-CSRF-Token": token, "If-Match": '"1"'}, json={}).json()
        return client.post(f"/agent/api/workflows/{workflow['id']}/runs", headers={
            "X-CSRF-Token": token, "If-Match": f'"{validated["revision"]}"'}, json={})

    monkeypatch.setenv("LTT_AGENT_CANVAS_RUN_ROLLOUT", "admin")
    assert create_run(a, token_a).status_code == 503
    assert create_run(b, token_b).status_code == 201
    monkeypatch.setenv("LTT_AGENT_CANVAS_RUN_ROLLOUT", "allowlist")
    monkeypatch.setenv("LTT_AGENT_CANVAS_RUN_USER_IDS", allowed_id)
    assert create_run(a, token_a).status_code == 201


def test_admin_audit_metrics_and_safe_cancel_hide_user_content(api):
    a, token_a, b, token_b = api
    workflow = _create(a, token_a).json()
    validated = a.post(f"/agent/api/workflows/{workflow['id']}/validate", headers={
        "X-CSRF-Token": token_a, "If-Match": '"1"'}, json={}).json()
    run = a.post(f"/agent/api/workflows/{workflow['id']}/runs", headers={
        "X-CSRF-Token": token_a, "If-Match": f'"{validated["revision"]}"'}, json={}).json()
    assert a.get("/agent/api/admin/runs").status_code == 404
    import platform_core.db as dbmod
    from platform_core.models import User
    db = next(dbmod.get_session())
    db.query(User).filter_by(email="canvas-b@example.com").one().role = "admin"
    db.commit(); db.close()
    listing = b.get("/agent/api/admin/runs")
    assert listing.status_code == 200 and listing.json()["items"][0]["id"] == run["id"]
    assert "goal" not in listing.text and "plan" not in listing.text
    metrics = b.get("/agent/api/admin/metrics").json()
    assert metrics["runs"] == 1 and metrics["estimated"] == run["estimated"]
    assert "run_success_rate" in metrics and "worker_wait_by_capability" in metrics
    assert metrics["live"]["planning_attempts"] >= 0
    assert b.post(f"/agent/api/admin/runs/{run['id']}/cancel", json={}).status_code == 400
    cancelled = b.post(f"/agent/api/admin/runs/{run['id']}/cancel",
                       headers={"X-CSRF-Token": token_b}, json={})
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
