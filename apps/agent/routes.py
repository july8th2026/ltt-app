"""Authenticated planning, approval, progress and audit UX for LTT Agent."""
from __future__ import annotations

import json
import hashlib
import mimetypes
import os
from time import perf_counter
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from apps.agent import jobs
from apps.agent.manifest import MANIFEST
from platform_core import credit
from platform_core.agent import budget, executor, metrics, runs, workflows
from platform_core.agent.tools import discover_tools, resolve_params_schema
from platform_core.registry import discover
from platform_core.models import AgentWorkflow, WORKFLOW_ARCHIVED
from platform_core.agent.planner import PlannerError, plan_once
from platform_core.agent.validator import validate_plan
from platform_core.models import AGENT_AWAITING_APPROVAL, AGENT_RUNNING, AgentRun, Job
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import get_db, user_hien_tai
from server.templating import templates

router = APIRouter(tags=["agent"])
_CANVAS_MANIFEST = (Path(__file__).resolve().parents[2] / "server" / "static" /
                    "agent-canvas" / ".vite" / "manifest.json")


def _run_rollout_mode() -> str:
    """Return off/admin/allowlist/public with a safe production default."""
    configured = os.environ.get("LTT_AGENT_CANVAS_RUN_ROLLOUT")
    if configured is not None:
        mode = configured.strip().lower()
        return mode if mode in {"off", "admin", "allowlist", "public"} else "off"
    legacy = os.environ.get("LTT_AGENT_CANVAS_RUN_ENABLED")
    if legacy is not None:
        return "public" if legacy.strip().lower() in {"1", "true", "yes", "on"} else "off"
    return "off" if os.environ.get("LTT_ENV", "").strip().lower() in {
        "production", "prod"} else "public"


def _new_runs_enabled(user) -> bool:
    mode = _run_rollout_mode()
    if mode == "public":
        return True
    if mode == "admin" and getattr(user, "role", "") == "admin":
        return True
    if mode == "allowlist":
        allowed = {value.strip() for value in os.environ.get(
            "LTT_AGENT_CANVAS_RUN_USER_IDS", "").split(",") if value.strip()}
        return getattr(user, "role", "") == "admin" or str(getattr(user, "id", "")) in allowed
    return False


def _require_new_runs_enabled(user) -> None:
    if not _new_runs_enabled(user):
        raise HTTPException(status_code=503, detail="Tạo run Canvas đang tạm khóa.")


def _user(request: Request):
    user = user_hien_tai(request)
    if user is None:
        raise HTTPException(status_code=403, detail="Cần tài khoản người dùng.")
    return user


def _owned(db: Session, request: Request, run_id: str) -> tuple[object, AgentRun]:
    user = _user(request)
    try:
        return user, runs.get_owned(db, run_id, user.id)
    except runs.AgentRunError:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt Agent.") from None


def _page_context(request: Request, *, error: str = "") -> dict:
    return {"nav": MANIFEST.slug, "app": MANIFEST,
            "csrf_token": issue_csrf_token(request), "error": error}


def _run_context(request: Request, run: AgentRun, *, error: str = "") -> dict:
    context = _page_context(request, error=error)
    context.update({"run": run, "steps": list((run.plan or {}).get("steps") or []),
                    "checkpoints": run.checkpoint or {},
                    "decisions": list(run.decision_log or [])})
    return context


def _verify_json_csrf(request: Request, body: dict) -> None:
    token = request.headers.get("X-CSRF-Token", "") or str(body.get("csrf_token", ""))
    if not verify_csrf_token(request, token):
        raise HTTPException(status_code=400, detail="Phiên đã hết hạn.")


def _workflow_json(row: AgentWorkflow, *, include_canvas: bool = True) -> dict:
    payload = {"id": row.id, "name": row.name, "status": row.status,
               "revision": row.revision, "plan_version": row.plan_version,
               "budget_max": row.budget_max, "estimated": row.estimated,
               "source_workflow_id": row.source_workflow_id,
               "created_at": row.created_at.isoformat(),
               "updated_at": row.updated_at.isoformat()}
    if include_canvas:
        payload["canvas"] = workflows.as_canvas(row)
    return payload


def _workflow_response(row: AgentWorkflow, *, status_code: int = 200):
    return JSONResponse(_workflow_json(row), status_code=status_code,
                        headers={"ETag": f'"{row.revision}"'})


def _quote_hash(run: AgentRun) -> str:
    payload = {"run_id": run.id, "version": run.version, "plan": run.plan,
               "estimated": run.estimated, "budget_max": run.budget_max}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _run_json(run: AgentRun) -> dict:
    quote_hash = next((item.get("quote_hash", "") for item in reversed(
        list(run.decision_log or [])) if item.get("event") == "workflow_source"), "")
    artifacts = []
    for step_id, state in (run.checkpoint or {}).items():
        outputs = state.get("outputs") if isinstance(state, dict) else None
        values = []
        def collect(value, name="output"):
            if isinstance(value, dict):
                for key, item in value.items(): collect(item, str(key))
            elif isinstance(value, list):
                for item in value: collect(item, name)
            elif isinstance(value, str) and (name.endswith("_key") or name.endswith("_keys")):
                values.append((name, value))
        collect(outputs)
        artifacts.extend({"step_id": step_id, "name": name,
                          "url": f"/agent/api/runs/{run.id}/artifacts/{step_id}/{index}"}
                         for index, (name, _key) in enumerate(values))
    return {"id": run.id, "version": run.version, "status": run.status,
            "goal": run.goal, "plan": run.plan, "checkpoint": run.checkpoint,
            "budget_max": run.budget_max, "estimated": run.estimated,
            "actual": run.actual, "quote_hash": quote_hash,
            "decisions": run.decision_log, "artifacts": artifacts}


def _artifact_key(run: AgentRun, step_id: str, index: int) -> str:
    state = (run.checkpoint or {}).get(step_id) or {}
    found = []
    def collect(value, name="output"):
        if isinstance(value, dict):
            for key, item in value.items(): collect(item, str(key))
        elif isinstance(value, list):
            for item in value: collect(item, name)
        elif isinstance(value, str) and (name.endswith("_key") or name.endswith("_keys")):
            found.append(value)
    collect(state.get("outputs"))
    if index < 0 or index >= len(found):
        raise HTTPException(status_code=404, detail="Không tìm thấy artifact.")
    return found[index]


def _palette_tool(name, spec, owner, loaded) -> dict:
    schema = resolve_params_schema(name, apps=loaded)
    variants = {}
    for field, rule in schema.items():
        if rule.get("type") == "model_ref":
            variants[field] = {str(value): resolve_params_schema(
                name, {field: value}, apps=loaded) for value in rule.get("values", [])}
    return {"name": spec.name, "description": spec.description,
            "app_slug": owner.slug, "app_name": owner.manifest.display_name,
            "requires": list(owner.manifest.requires), "params_schema": schema,
            "schema_variants": variants, "returns": spec.returns,
            "verifiable": list(spec.verifiable)}


@router.get("", response_class=HTMLResponse)
def page(request: Request, _identity: str = Depends(require_login)):
    return templates.TemplateResponse(request, "agent.html", _page_context(request))


@router.get("/canvas", response_class=HTMLResponse)
def canvas_page(request: Request, _identity: str = Depends(require_login)):
    try:
        manifest = json.loads(_CANVAS_MANIFEST.read_text(encoding="utf-8"))
        entry = manifest["src/main.tsx"]
        canvas_js = [f"/static/agent-canvas/{entry['file']}"]
        canvas_css = [f"/static/agent-canvas/{item}" for item in entry.get("css", [])]
    except (OSError, KeyError, ValueError):
        raise HTTPException(status_code=503, detail="Canvas bundle chưa được build.") from None
    context = _page_context(request)
    context.update({"canvas_js": canvas_js, "canvas_css": canvas_css})
    return templates.TemplateResponse(request, "agent_canvas.html", context)


@router.post("/plan", response_class=HTMLResponse)
def create_plan(request: Request, goal: str = Form(""), budget_max: int = Form(0),
                csrf_token: str = Form(""), _identity: str = Depends(require_login),
                db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "agent.html", _page_context(request, error="Phiên đã hết hạn — tải lại trang."),
            status_code=400)
    goal = " ".join(goal.split())
    if len(goal) < 10 or len(goal) > 8000 or budget_max < 5:
        return templates.TemplateResponse(
            request, "agent.html", _page_context(
                request, error="Mục tiêu cần 10–8.000 ký tự và ngân sách tối thiểu 5 credit."),
            status_code=200)
    user = _user(request)
    planning_started = perf_counter(); planning_success = False
    try:
        plan = plan_once(db, goal=goal, budget_max_credit=budget_max)
        plan["budget_max_credit"] = budget_max
        validation = validate_plan(plan, db=db, user=user)
        if not validation.valid:
            message = "; ".join(issue.message for issue in validation.issues[:5])
            return templates.TemplateResponse(
                request, "agent.html", _page_context(request, error=message), status_code=200)
        run = runs.create_run_capped(db, user_id=user.id, goal=goal, plan=plan,
                                     budget_max=budget_max)
        budget.set_quote(db, run, plan=plan, validation=validation)
        db.flush()
        planning_success = True
    except (PlannerError, budget.BudgetError, runs.AgentRunError):
        db.rollback()
        return templates.TemplateResponse(
            request, "agent.html", _page_context(
                request, error="Chưa thể lập kế hoạch hợp lệ. Hãy điều chỉnh mục tiêu hoặc ngân sách."),
            status_code=200)
    finally:
        metrics.record_planning(success=planning_success,
                                latency_ms=(perf_counter() - planning_started) * 1000)
    return RedirectResponse(f"{MANIFEST.route_prefix}/runs/{run.id}", status_code=303)


@router.get("/runs/{run_id}", response_class=HTMLResponse)
def run_page(request: Request, run_id: str, _identity: str = Depends(require_login),
             error: str = "", db: Session = Depends(get_db)):
    _user_row, run = _owned(db, request, run_id)
    messages = {"credit": "Không đủ credit để giữ mức tối đa này.",
                "approval": "Plan đã thay đổi hoặc không còn chờ phê duyệt."}
    return templates.TemplateResponse(
        request, "agent_run.html", _run_context(request, run, error=messages.get(error, "")))


@router.get("/runs/{run_id}/api")
def run_api(request: Request, run_id: str, _identity: str = Depends(require_login),
            db: Session = Depends(get_db)):
    _user_row, run = _owned(db, request, run_id)
    return JSONResponse(_run_json(run))


@router.post("/runs/{run_id}/approve")
def approve_run(request: Request, run_id: str, version: int = Form(...),
                csrf_token: str = Form(""), _identity: str = Depends(require_login),
                db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(status_code=400, detail="Phiên đã hết hạn.")
    user, run = _owned(db, request, run_id)
    approval_success = False
    try:
        budget.approve(db, run_id=run.id, user_id=user.id, approved_by=user.id,
                       expected_version=version)
        approval_success = True
    except credit.ThieuCreditError:
        return RedirectResponse(
            f"{MANIFEST.route_prefix}/runs/{run.id}?error=credit", status_code=303)
    except budget.BudgetError:
        return RedirectResponse(
            f"{MANIFEST.route_prefix}/runs/{run.id}?error=approval", status_code=303)
    finally:
        metrics.record_approval(success=approval_success)
    return RedirectResponse(f"{MANIFEST.route_prefix}/runs/{run.id}", status_code=303)


@router.post("/runs/{run_id}/tick", response_class=HTMLResponse)
def tick_run(request: Request, run_id: str, csrf_token: str = Form(""),
             _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(status_code=400, detail="Phiên đã hết hạn.")
    user, run = _owned(db, request, run_id)
    if run.status == AGENT_RUNNING:
        run = jobs.advance(db, run_id=run.id, user_id=user.id)
    return templates.TemplateResponse(
        request, "_agent_progress.html", _run_context(request, run))


@router.post("/runs/{run_id}/cancel")
def cancel_run(request: Request, run_id: str, csrf_token: str = Form(""),
               _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(status_code=400, detail="Phiên đã hết hạn.")
    user, run = _owned(db, request, run_id)
    if run.status in (AGENT_AWAITING_APPROVAL, AGENT_RUNNING):
        actual = executor.actual_cost(run, runs.children(db, run)) if run.status == AGENT_RUNNING else 0
        budget.cancel(db, run_id=run.id, user_id=user.id, actual=actual)
    return RedirectResponse(f"{MANIFEST.route_prefix}/runs/{run.id}", status_code=303)


@router.get("/api/palette")
def workflow_palette(request: Request, _identity: str = Depends(require_login),
                     db: Session = Depends(get_db)):
    user = _user(request)
    from platform_core import app_access
    loaded = discover()
    allowed = {item.slug for item in loaded
               if app_access.muc_quyen(db, user, item.slug) == app_access.ENABLED}
    tools = discover_tools(apps=loaded, allowed_slugs=allowed)
    owners = {tool.name: item for item in loaded for tool in item.manifest.tools}
    return JSONResponse({"version": 1, "tools": [
        _palette_tool(name, spec, owners[name], loaded)
        for name, spec in sorted(tools.items())]})


@router.post("/api/workflows/plan")
async def workflow_plan(request: Request, _identity: str = Depends(require_login),
                        db: Session = Depends(get_db)):
    """Turn a Vietnamese goal into an editable draft; never approves or spends."""
    body = await request.json(); _verify_json_csrf(request, body)
    user = _user(request)
    goal = " ".join(str(body.get("goal", "")).split())
    try:
        budget_max = int(body.get("budget_max_credit", 0))
    except (TypeError, ValueError):
        budget_max = 0
    if len(goal) < 10 or len(goal) > 8000 or budget_max < 5:
        raise HTTPException(status_code=422, detail="Mục tiêu/ngân sách không hợp lệ.")
    planning_started = perf_counter(); planning_success = False
    try:
        plan = plan_once(db, goal=goal, budget_max_credit=budget_max)
        plan.update({"goal": goal, "budget_max_credit": budget_max})
        result = validate_plan(plan, db=db, user=user)
        if not result.valid:
            raise workflows.WorkflowError("; ".join(item.message for item in result.issues[:5]))
        row = workflows.create(db, user_id=user.id,
                               name=str(body.get("name") or goal[:80]),
                               canvas=workflows.plan_to_canvas(plan))
        planning_success = True
    except (PlannerError, workflows.WorkflowError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    finally:
        metrics.record_planning(success=planning_success,
                                latency_ms=(perf_counter() - planning_started) * 1000)
    return _workflow_response(row, status_code=201)


def _prepare_run(db: Session, *, user, plan: dict, source: dict) -> AgentRun:
    _require_new_runs_enabled(user)
    validation = validate_plan(plan, db=db, user=user)
    if not validation.valid:
        raise workflows.WorkflowError("Workflow không còn hợp lệ.")
    run = runs.create_run_capped(db, user_id=user.id, goal=str(plan.get("goal", "")),
                                 plan=plan, budget_max=int(plan.get("budget_max_credit", 0)))
    budget.set_quote(db, run, plan=plan, validation=validation)
    event = {"event": "workflow_source", **source, "quote_hash": _quote_hash(run)}
    runs.append_decision(db, run, event)
    return run


@router.post("/api/workflows/{workflow_id}/runs")
async def workflow_create_run(request: Request, workflow_id: str,
                              _identity: str = Depends(require_login),
                              db: Session = Depends(get_db)):
    """Snapshot an exact validated Canvas revision into an immutable AgentRun."""
    body = await request.json(); _verify_json_csrf(request, body)
    user = _user(request)
    try:
        row = workflows.get_owned(db, workflow_id, user.id)
        expected = int(request.headers.get("If-Match", "").strip('"') or body["revision"])
        if row.revision != expected:
            raise workflows.WorkflowConflict("Workflow đã được sửa; cần báo giá lại.")
        plan = workflows.canvas_to_plan(workflows.as_canvas(row))
        run = _prepare_run(db, user=user, plan=plan,
                           source={"workflow_id": row.id, "workflow_revision": row.revision,
                                   "correlation_id": getattr(request.state, "correlation_id", "")})
    except workflows.WorkflowConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail="Không tìm thấy workflow.") from None
    except (KeyError, TypeError, ValueError, workflows.WorkflowError,
            budget.BudgetError, runs.AgentRunError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return JSONResponse(_run_json(run), status_code=201)


@router.post("/api/runs/{run_id}/approve")
async def workflow_approve_run(request: Request, run_id: str,
                               _identity: str = Depends(require_login),
                               db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user, run = _owned(db, request, run_id)
    if str(body.get("quote_hash", "")) != _run_json(run)["quote_hash"]:
        metrics.record_approval(success=False)
        raise HTTPException(status_code=409, detail="Báo giá đã thay đổi.")
    approval_success = False
    try:
        run = budget.approve(db, run_id=run.id, user_id=user.id, approved_by=user.id,
                             expected_version=int(body.get("version", 0)))
        approval_success = True
    except credit.ThieuCreditError:
        raise HTTPException(status_code=402, detail="Không đủ credit.") from None
    except (ValueError, budget.BudgetError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    finally:
        metrics.record_approval(success=approval_success)
    return JSONResponse(_run_json(run))


@router.post("/api/runs/{run_id}/again")
async def workflow_run_again(request: Request, run_id: str,
                             _identity: str = Depends(require_login),
                             db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user, source = _owned(db, request, run_id)
    try:
        run = _prepare_run(db, user=user, plan=dict(source.plan),
                           source={"source_run_id": source.id,
                                   "source_run_version": source.version,
                                   "correlation_id": getattr(request.state, "correlation_id", "")})
    except (workflows.WorkflowError, budget.BudgetError, runs.AgentRunError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return JSONResponse(_run_json(run), status_code=201)


@router.post("/api/runs/{run_id}/tick")
async def workflow_tick_run(request: Request, run_id: str,
                            _identity: str = Depends(require_login),
                            db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user, run = _owned(db, request, run_id)
    if run.status == AGENT_RUNNING:
        run = jobs.advance(db, run_id=run.id, user_id=user.id)
    return JSONResponse(_run_json(run))


@router.post("/api/runs/{run_id}/cancel")
async def workflow_cancel_run(request: Request, run_id: str,
                              _identity: str = Depends(require_login),
                              db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user, run = _owned(db, request, run_id)
    if run.status in (AGENT_AWAITING_APPROVAL, AGENT_RUNNING):
        actual = executor.actual_cost(run, runs.children(db, run)) if run.status == AGENT_RUNNING else 0
        run = budget.cancel(db, run_id=run.id, user_id=user.id, actual=actual)
    return JSONResponse(_run_json(run))


@router.get("/api/runs/{run_id}/artifacts/{step_id}/{index}")
def workflow_artifact(request: Request, run_id: str, step_id: str, index: int,
                      _identity: str = Depends(require_login),
                      db: Session = Depends(get_db)):
    """Owned, short-lived artifact delivery; R2 redirects, local streams."""
    _user_row, run = _owned(db, request, run_id)
    key = _artifact_key(run, step_id, index)
    from platform_core.storage import StorageError, get_storage
    storage = get_storage()
    try:
        direct = storage.url_for(key)
        if direct:
            return RedirectResponse(direct, status_code=307)
        stream = storage.open(key)
    except (OSError, StorageError):
        raise HTTPException(status_code=404, detail="Artifact không còn tồn tại.") from None
    media_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
    return StreamingResponse(stream, media_type=media_type,
                             headers={"Cache-Control": "private, no-store"})


@router.get("/api/workflows")
def workflow_list(request: Request, _identity: str = Depends(require_login),
                  db: Session = Depends(get_db)):
    user = _user(request)
    rows = db.query(AgentWorkflow).filter_by(user_id=user.id).order_by(
        AgentWorkflow.updated_at.desc()).all()
    return JSONResponse({"items": [_workflow_json(row, include_canvas=False) for row in rows]})


@router.post("/api/workflows")
async def workflow_create(request: Request, _identity: str = Depends(require_login),
                          db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user = _user(request)
    try:
        row = workflows.create(db, user_id=user.id, name=str(body.get("name", "")),
                               canvas=body.get("canvas"))
    except workflows.WorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _workflow_response(row, status_code=201)


@router.get("/api/workflows/{workflow_id}")
def workflow_get(request: Request, workflow_id: str,
                 _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    user = _user(request)
    try:
        row = workflows.get_owned(db, workflow_id, user.id)
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail="Không tìm thấy workflow.") from None
    return _workflow_response(row)


@router.put("/api/workflows/{workflow_id}")
async def workflow_save(request: Request, workflow_id: str,
                        _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user = _user(request)
    try:
        revision = int(request.headers.get("If-Match", "").strip('"') or body["revision"])
        row = workflows.save(db, workflow_id=workflow_id, user_id=user.id,
                             revision=revision, name=str(body.get("name", "")),
                             canvas=body.get("canvas"))
    except workflows.WorkflowConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail="Không tìm thấy workflow.") from None
    except (KeyError, TypeError, ValueError, workflows.WorkflowError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _workflow_response(row)


@router.post("/api/workflows/{workflow_id}/validate")
async def workflow_validate(request: Request, workflow_id: str,
                            _identity: str = Depends(require_login),
                            db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user = _user(request)
    try:
        row = workflows.get_owned(db, workflow_id, user.id)
        expected = int(request.headers.get("If-Match", "").strip('"') or body["revision"])
        if row.revision != expected:
            raise workflows.WorkflowConflict("Workflow đã được sửa ở phiên khác.")
        result = workflows.validate(db, row, user=user)
    except workflows.WorkflowConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail="Không tìm thấy workflow.") from None
    response = _workflow_json(row)
    response["validation"] = {"valid": result.valid,
                              "estimated_max_credit": result.estimated_max_credit,
                              "issues": [issue.__dict__ for issue in result.issues],
                              "step_costs": list(result.step_costs)}
    return JSONResponse(response, headers={"ETag": f'"{row.revision}"'})


@router.post("/api/workflows/{workflow_id}/clone")
async def workflow_clone(request: Request, workflow_id: str,
                         _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user = _user(request)
    try:
        source = workflows.get_owned(db, workflow_id, user.id)
        row = workflows.create(db, user_id=user.id,
                               name=str(body.get("name") or f"{source.name} — bản sao"),
                               canvas=workflows.as_canvas(source), source_workflow_id=source.id)
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail="Không tìm thấy workflow.") from None
    return _workflow_response(row, status_code=201)


@router.post("/api/workflows/{workflow_id}/archive")
async def workflow_archive(request: Request, workflow_id: str,
                           _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user = _user(request)
    try:
        row = workflows.get_owned(db, workflow_id, user.id)
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail="Không tìm thấy workflow.") from None
    if row.status != WORKFLOW_ARCHIVED:
        row.status = WORKFLOW_ARCHIVED; row.revision += 1
    return _workflow_response(row)


@router.get("/api/workflows/{workflow_id}/export")
def workflow_export(request: Request, workflow_id: str,
                    _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    user = _user(request)
    try:
        row = workflows.get_owned(db, workflow_id, user.id)
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail="Không tìm thấy workflow.") from None
    return JSONResponse({"format": "ltt-agent-workflow", "version": 1,
                         "name": row.name, "canvas": workflows.as_canvas(row)},
                        headers={"Content-Disposition":
                                 f'attachment; filename="workflow-{row.id}.json"'})


@router.post("/api/workflows/import")
async def workflow_import(request: Request, _identity: str = Depends(require_login),
                          db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    if body.get("format") != "ltt-agent-workflow" or body.get("version") != 1:
        raise HTTPException(status_code=422, detail="Định dạng workflow không hỗ trợ.")
    user = _user(request)
    try:
        row = workflows.create(db, user_id=user.id, name=str(body.get("name", "")),
                               canvas=body.get("canvas"))
    except workflows.WorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _workflow_response(row, status_code=201)


def _require_admin_user(request: Request):
    user = _user(request)
    if getattr(user, "role", "") != "admin":
        raise HTTPException(status_code=404, detail="Không tìm thấy.")
    return user


@router.get("/api/admin/runs")
def agent_admin_runs(request: Request, _identity: str = Depends(require_login),
                     db: Session = Depends(get_db)):
    """Read-only operational audit without exposing goals, params or user PII."""
    _require_admin_user(request)
    rows = db.query(AgentRun).order_by(AgentRun.created_at.desc()).limit(100).all()
    return JSONResponse({"items": [{
        "id": row.id, "user_ref": hashlib.sha256(row.user_id.encode()).hexdigest()[:12],
        "status": row.status, "version": row.version, "estimated": row.estimated,
        "actual": row.actual, "step_count": len((row.plan or {}).get("steps") or []),
        "events": [str(item.get("event", "")) for item in (row.decision_log or [])],
    } for row in rows]})


@router.get("/api/admin/metrics")
def agent_admin_metrics(request: Request, _identity: str = Depends(require_login),
                        db: Session = Depends(get_db)):
    _require_admin_user(request)
    rows = db.query(AgentRun).all()
    statuses: dict[str, int] = {}
    retries = verifies = refunds = 0
    for row in rows:
        statuses[row.status] = statuses.get(row.status, 0) + 1
        retries += sum(1 for item in (row.decision_log or [])
                       if item.get("event") == "verify" and item.get("attempt", 0))
        verifies += sum(1 for item in (row.decision_log or []) if item.get("event") == "verify")
        refunds += sum(int(item.get("refunded", 0)) for item in (row.decision_log or [])
                       if item.get("event") == "settle")
    estimated = sum(row.estimated for row in rows)
    actual = sum(row.actual for row in rows)
    terminal = sum(count for status, count in statuses.items()
                   if status in {"done", "error", "cancelled"})
    run_success_rate = statuses.get("done", 0) / terminal if terminal else 0
    requirements = {item.slug: tuple(item.manifest.requires) for item in discover()}
    waits: dict[str, list[float]] = {}
    for job in db.query(Job).filter(Job.parent_id != "").all():
        if job.started_at is None:
            continue
        seconds = max(0.0, job.started_at.timestamp() - job.created_at.timestamp())
        for capability in requirements.get(job.app_slug, ("api",)):
            waits.setdefault(capability, []).append(seconds)
    worker_wait = {name: {"count": len(values), "avg_s": sum(values) / len(values),
                          "max_s": max(values)} for name, values in waits.items()}
    return JSONResponse({"runs": len(rows), "statuses": statuses, "retries": retries,
                         "verifications": verifies, "estimated": estimated,
                         "actual": actual, "actual_estimated_ratio": actual / estimated if estimated else 0,
                         "refunded": refunds, "run_success_rate": run_success_rate,
                         "worker_wait_by_capability": worker_wait,
                         "live": metrics.snapshot()})


@router.post("/api/admin/runs/{run_id}/cancel")
async def agent_admin_cancel(request: Request, run_id: str,
                             _identity: str = Depends(require_login),
                             db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    _require_admin_user(request)
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy run.")
    if run.status in (AGENT_AWAITING_APPROVAL, AGENT_RUNNING):
        actual = executor.actual_cost(run, runs.children(db, run)) if run.status == AGENT_RUNNING else 0
        run = budget.cancel(db, run_id=run.id, user_id=run.user_id, actual=actual)
    return JSONResponse({"id": run.id, "status": run.status,
                         "estimated": run.estimated, "actual": run.actual})
