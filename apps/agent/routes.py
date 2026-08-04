"""Authenticated planning, approval, progress and audit UX for LTT Agent."""
from __future__ import annotations

import json
import hashlib
import mimetypes
import os
import io
import tempfile
import uuid
import zipfile
import secrets
from datetime import datetime, timedelta, timezone
from time import perf_counter
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from apps.agent import jobs
from apps.agent.manifest import MANIFEST
from platform_core import credit, jobs as job_queue
from platform_core.agent import budget, executor, metrics, runs, workflows
from platform_core.agent.tools import (ToolParamsError, discover_tools,
                                       resolve_params_schema, validate_tool_params)
from platform_core.registry import RegistryError, credit_for, discover
from platform_core.models import (APP_PROJECT_ACTIVE, AgentWorkflow,
                                  AgentWorkflowShare, AppProject,
                                  WORKFLOW_ARCHIVED)
from platform_core.agent.planner import PlannerError, plan_once
from platform_core.agent.validator import validate_plan
from platform_core.models import AGENT_AWAITING_APPROVAL, AGENT_RUNNING, AgentRun, Job
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import get_db, user_hien_tai
from server.templating import templates

router = APIRouter(tags=["agent"])
_ASSET_LIMIT = 90 * 1024 * 1024
_ASSET_MIME_PREFIXES = ("image/", "video/", "audio/")
_ASSISTANT_SALT = "ltt-agent-assistant-proposal-v1"
_PREFERENCES_SLUG = "agent.preferences"
_DEFAULT_PREFERENCES = {"theme": "light", "catalog_mode": "simple"}


def _assistant_serializer() -> URLSafeTimedSerializer:
    secret = (os.environ.get("LTT_SESSION_SECRET") or "").strip()
    if not secret:
        raise RuntimeError("Assistant proposal signer chưa được cấu hình.")
    return URLSafeTimedSerializer(secret)
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
    scheduled = next((item.get("scheduled_at") for item in reversed(run.decision_log or [])
                      if item.get("event") == "scheduled"), "")
    return {"id": run.id, "version": run.version, "status": run.status,
            "goal": run.goal, "plan": run.plan, "checkpoint": run.checkpoint,
            "budget_max": run.budget_max, "estimated": run.estimated,
            "actual": run.actual, "quote_hash": quote_hash,
            "decisions": run.decision_log, "artifacts": artifacts,
            "scheduled_at": scheduled}


def _scheduled_datetime(run: AgentRun) -> datetime | None:
    value = next((item.get("scheduled_at") for item in reversed(run.decision_log or [])
                  if item.get("event") == "scheduled"), "")
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def _schedule_at(value) -> datetime:
    if value in (None, ""):
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Thời gian lên lịch không hợp lệ.") from exc
    if parsed.tzinfo is None:
        raise ValueError("Thời gian lên lịch phải kèm múi giờ.")
    parsed = parsed.astimezone(timezone.utc)
    if parsed > datetime.now(timezone.utc) + timedelta(days=30):
        raise ValueError("Chỉ được lên lịch tối đa 30 ngày.")
    return parsed


def _enqueue_advance(db: Session, run: AgentRun, scheduled_at: datetime) -> Job:
    existing = next((item.get("scheduled_at") for item in reversed(run.decision_log or [])
                     if item.get("event") == "scheduled"), "")
    effective = _schedule_at(existing) if existing else scheduled_at
    job = job_queue.submit(
        db, user_id=run.user_id, app_slug="agent", job_type="agent.advance",
        params={"run_id": run.id, "user_id": run.user_id},
        dedupe_key=f"agent:advance:{run.id}:initial", max_attempts=3,
    )
    job.next_run_at = max(effective, datetime.now(timezone.utc))
    if not existing:
        runs.append_decision(db, run, {"event": "scheduled",
                                       "scheduled_at": scheduled_at.isoformat()})
    return job


def _cancel_advance_jobs(db: Session, run: AgentRun) -> None:
    queued = db.query(Job).filter(
        Job.user_id == run.user_id, Job.app_slug == "agent",
        Job.dedupe_key.like(f"agent:advance:{run.id}:%"),
    ).all()
    for job in queued:
        job_queue.cancel(db, job)


def _run_summary(run: AgentRun) -> dict:
    return {"id": run.id, "version": run.version, "status": run.status,
            "estimated": run.estimated, "actual": run.actual,
            "created_at": run.created_at.isoformat() if run.created_at else "",
            "finished_at": run.finished_at.isoformat() if run.finished_at else ""}


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
    presentation = {
        "text.generate": ("Tạo văn bản", "content", True),
        "image.generate": ("Tạo hình ảnh", "content", True),
        "video.generate": ("Tạo video", "content", True),
        "text.script": ("Viết kịch bản", "specialized", False),
        "image.thumbnail": ("Tạo thumbnail", "specialized", False),
        "image.batch_generate": ("Tạo nhiều ảnh", "specialized", False),
        "audio.generate": ("Tạo âm thanh", "content", False),
        "asset.image": ("Ảnh đầu vào", "input", False),
        "asset.video": ("Video đầu vào", "input", False),
        "asset.audio": ("Âm thanh đầu vào", "input", False),
        "image.upscale": ("Nâng cấp ảnh", "transform", False),
        "video.upscale": ("Nâng cấp video", "transform", False),
        "video.extract_frames": ("Tách khung hình", "transform", False),
        "media.merge_image": ("Ghép ảnh", "transform", False),
        "media.merge_video": ("Ghép video", "transform", False),
        "video.social_import": ("Video từ liên kết", "input", False),
    }
    label, category, primary = presentation.get(
        spec.name, (spec.name.replace(".", " ").title(), "advanced", False))
    return {"name": spec.name, "label": label, "category": category,
            "primary": primary, "description": spec.description,
            "app_slug": owner.slug, "app_name": owner.manifest.display_name,
            "requires": list(owner.manifest.requires), "params_schema": schema,
            "schema_variants": variants, "returns": spec.returns,
            "verifiable": list(spec.verifiable)}


def _preferences_row(db: Session, user_id: str) -> AppProject | None:
    return db.query(AppProject).filter_by(
        user_id=user_id, app_slug=_PREFERENCES_SLUG,
        status=APP_PROJECT_ACTIVE).order_by(AppProject.updated_at.desc()).first()


def _preferences_json(row: AppProject | None) -> dict:
    payload = dict(_DEFAULT_PREFERENCES)
    if row:
        saved = row.payload or {}
        if saved.get("theme") in {"light", "dark"}:
            payload["theme"] = saved["theme"]
        if saved.get("catalog_mode") in {"simple", "advanced"}:
            payload["catalog_mode"] = saved["catalog_mode"]
    return {**payload, "revision": row.revision if row else 0}


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
        run = budget.approve(db, run_id=run.id, user_id=user.id, approved_by=user.id,
                             expected_version=version)
        _enqueue_advance(db, run, datetime.now(timezone.utc))
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
    scheduled = _scheduled_datetime(run)
    if run.status == AGENT_RUNNING and (scheduled is None or
                                        scheduled <= datetime.now(timezone.utc)):
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
        run = budget.cancel(db, run_id=run.id, user_id=user.id, actual=actual)
        _cancel_advance_jobs(db, run)
    return RedirectResponse(f"{MANIFEST.route_prefix}/runs/{run.id}", status_code=303)


@router.get("/api/preferences")
def get_preferences(request: Request, _identity: str = Depends(require_login),
                    db: Session = Depends(get_db)):
    user = _user(request)
    return JSONResponse(_preferences_json(_preferences_row(db, user.id)))


@router.put("/api/preferences")
async def save_preferences(request: Request, _identity: str = Depends(require_login),
                           db: Session = Depends(get_db)):
    body = await request.json()
    _verify_json_csrf(request, body)
    theme = str(body.get("theme", ""))
    catalog_mode = str(body.get("catalog_mode", ""))
    if theme not in {"light", "dark"} or catalog_mode not in {"simple", "advanced"}:
        raise HTTPException(status_code=422, detail="Tùy chọn giao diện không hợp lệ.")
    user = _user(request)
    from platform_core import app_projects
    row = _preferences_row(db, user.id)
    payload = {"theme": theme, "catalog_mode": catalog_mode}
    try:
        if row:
            row = app_projects.save(
                db, project_id=row.id, user_id=user.id, app_slug=_PREFERENCES_SLUG,
                revision=row.revision, name="Agent UI preferences",
                schema_version=1, payload=payload)
        else:
            row = app_projects.create(
                db, user_id=user.id, app_slug=_PREFERENCES_SLUG,
                name="Agent UI preferences", schema_version=1, payload=payload)
    except app_projects.ProjectError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.flush()
    return JSONResponse(_preferences_json(row))


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
    from platform_core import providers
    return JSONResponse({"version": 2,
        "routing": {"mode": "platform_auto", "server_choice": "managed",
                    "description": "Nền tảng chọn provider khả dụng; không lộ API key."},
        "models": providers.model_catalog(), "tools": [
        _palette_tool(name, spec, owners[name], loaded)
        for name, spec in sorted(tools.items())]})


@router.post("/api/assets")
async def workflow_asset_upload(request: Request, file: UploadFile = File(...),
                                _identity: str = Depends(require_login)):
    """Upload an owned Canvas asset; output is a server-generated storage key."""
    token = request.headers.get("X-CSRF-Token", "")
    if not verify_csrf_token(request, token):
        raise HTTPException(status_code=400, detail="Phiên đã hết hạn.")
    user = _user(request)
    content_type = str(file.content_type or "").lower()
    if not any(content_type.startswith(prefix) for prefix in _ASSET_MIME_PREFIXES):
        raise HTTPException(status_code=415, detail="Chỉ nhận ảnh, video hoặc audio.")
    data = await file.read(_ASSET_LIMIT + 1)
    if not data or len(data) > _ASSET_LIMIT:
        raise HTTPException(status_code=413, detail="Asset phải từ 1 byte đến 90 MB.")
    suffix = Path(file.filename or "asset").suffix.lower()[:10]
    if content_type.startswith("image/"):
        try:
            from PIL import Image
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
        except Exception:
            raise HTTPException(status_code=422, detail="File ảnh không hợp lệ.") from None
    else:
        from platform_core import media
        temp_path = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
                temp.write(data); temp_path = temp.name
            if media.duration_seconds(temp_path) <= 0:
                raise HTTPException(status_code=422, detail="File media không có thời lượng hợp lệ.")
        finally:
            if temp_path:
                try: os.unlink(temp_path)
                except OSError: pass
    from platform_core.storage import get_storage
    key = f"agent-assets/{user.id}/{uuid.uuid4().hex}{suffix}"
    stored = get_storage().put(key, io.BytesIO(data), content_type=content_type)
    kind = content_type.split("/", 1)[0]
    return {"key": stored.key, "kind": kind, "name": Path(file.filename or "asset").name,
            "size": stored.size, "content_type": content_type,
            "provenance": {"source": "user_upload", "owner": "current_user"}}


@router.post("/api/tools/{tool_name}/quote")
async def workflow_tool_quote(request: Request, tool_name: str,
                              _identity: str = Depends(require_login),
                              db: Session = Depends(get_db)):
    """Authoritative non-mutating node quote for the inline composer."""
    body = await request.json(); _verify_json_csrf(request, body)
    user = _user(request)
    from platform_core import app_access
    loaded = discover()
    allowed = {item.slug for item in loaded
               if app_access.muc_quyen(db, user, item.slug) == app_access.ENABLED}
    tools = discover_tools(apps=loaded, allowed_slugs=allowed)
    spec = tools.get(tool_name)
    if spec is None:
        raise HTTPException(status_code=404, detail="Tool không tồn tại/không có quyền.")
    try:
        params = validate_tool_params(tool_name, body.get("params", {}), apps=loaded)
        fanout = int(body.get("fanout", 1)); retry = int(body.get("max_retry", 0))
        if not 1 <= fanout <= 4 or not 0 <= retry <= 2:
            raise ToolParamsError("fanout/max_retry không hợp lệ")
        unit = credit_for(spec.job_type, params, apps=loaded)
    except (ToolParamsError, RegistryError, ValueError, TypeError) as exc:
        return {"tool": tool_name, "valid": False, "detail": str(exc),
                "maximum": None, "authoritative": True}
    return {"tool": tool_name, "valid": True, "unit": unit, "fanout": fanout,
            "max_retry": retry, "maximum": unit * fanout * (1 + retry),
            "authoritative": True}


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


@router.post("/api/workflows/{workflow_id}/assistant/preview")
async def workflow_assistant_preview(request: Request, workflow_id: str,
                                     _identity: str = Depends(require_login),
                                     db: Session = Depends(get_db)):
    """SSE analysis/proposal stream. It never mutates the workflow."""
    body = await request.json(); _verify_json_csrf(request, body)
    user = _user(request)
    try:
        row = workflows.get_owned(db, workflow_id, user.id)
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail="Không tìm thấy workflow.") from None
    expected = int(request.headers.get("If-Match", "").strip('"') or body.get("revision", 0))
    if row.revision != expected:
        raise HTTPException(status_code=409, detail="Workflow đã thay đổi; hãy phân tích lại.")
    mode = str(body.get("mode") or "analyze")
    prompt = str(body.get("prompt") or "").strip()[:4000]
    if mode not in {"analyze", "improve"} or (mode == "improve" and len(prompt) < 3):
        raise HTTPException(status_code=422, detail="Yêu cầu Assistant không hợp lệ.")
    canvas = workflows.as_canvas(row); current_plan = workflows.canvas_to_plan(canvas)
    current_validation = validate_plan(current_plan, db=db, user=user)
    steps = list(current_plan.get("steps") or [])
    patterns = db.query(AgentWorkflow).filter(
        AgentWorkflow.user_id == user.id, AgentWorkflow.id != row.id).order_by(
        AgentWorkflow.updated_at.desc()).limit(5).all()
    pattern_context = []
    for item in patterns:
        try:
            pattern_plan = workflows.canvas_to_plan(workflows.as_canvas(item))
        except workflows.WorkflowError:
            continue
        pattern_context.append({"name": item.name, "goal": item.goal,
                                "tools": [str(step.get("tool"))
                                          for step in pattern_plan.get("steps", [])]})
    analysis = {"nodes": len(steps), "valid": current_validation.valid,
                "issues": [issue.message for issue in current_validation.issues[:8]],
                "roots": sum(not step.get("after") and not step.get("after_error") for step in steps),
                "patterns_considered": len(pattern_context)}

    async def stream():
        yield "event: analysis\ndata: " + json.dumps(analysis, ensure_ascii=False) + "\n\n"
        if mode == "analyze":
            yield "event: done\ndata: {\"mutated\":false}\n\n"; return
        try:
            context = json.dumps({"current_plan": current_plan,
                                  "private_patterns": pattern_context}, ensure_ascii=False,
                                 separators=(",", ":"))
            goal = ("Improve the CURRENT workflow according to the user request. Preserve useful "
                    "steps and return a complete replacement Plan. Current context: " + context +
                    "\nUser request: " + prompt)
            proposed_plan = plan_once(db, goal=goal,
                                      budget_max_credit=current_plan.get("budget_max_credit", 0))
            validation = validate_plan(proposed_plan, db=db, user=user)
            if not validation.valid:
                detail = "; ".join(issue.message for issue in validation.issues[:5])
                yield "event: error\ndata: " + json.dumps({"detail": detail}, ensure_ascii=False) + "\n\n"; return
            proposed_canvas = workflows.plan_to_canvas(proposed_plan)
            token = _assistant_serializer().dumps({"workflow_id": row.id,
                "user_id": user.id, "revision": row.revision,
                "name": row.name, "canvas": proposed_canvas}, salt=_ASSISTANT_SALT)
            proposal = {"token": token, "canvas": proposed_canvas,
                        "diff": {"before_nodes": len(steps),
                                 "after_nodes": len(proposed_plan.get("steps") or []),
                                 "estimated_max_credit": validation.estimated_max_credit}}
            yield "event: proposal\ndata: " + json.dumps(proposal, ensure_ascii=False) + "\n\n"
            yield "event: done\ndata: {\"mutated\":false}\n\n"
        except Exception as exc:
            yield "event: error\ndata: " + json.dumps({
                "detail": f"Assistant tạm thời không tạo được đề xuất ({type(exc).__name__})."}) + "\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@router.post("/api/workflows/{workflow_id}/assistant/apply")
async def workflow_assistant_apply(request: Request, workflow_id: str,
                                   _identity: str = Depends(require_login),
                                   db: Session = Depends(get_db)):
    """Apply only a short-lived server-signed preview after full validation."""
    body = await request.json(); _verify_json_csrf(request, body)
    user = _user(request)
    try:
        payload = _assistant_serializer().loads(str(body.get("token") or ""),
                                                salt=_ASSISTANT_SALT, max_age=1800)
    except (BadSignature, SignatureExpired):
        raise HTTPException(status_code=409, detail="Đề xuất đã hết hạn hoặc không hợp lệ.") from None
    if payload.get("workflow_id") != workflow_id or payload.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy đề xuất.")
    try:
        row = workflows.get_owned(db, workflow_id, user.id)
        if row.revision != int(payload.get("revision", 0)):
            raise workflows.WorkflowConflict("Workflow đã thay đổi; không thể áp dụng đề xuất cũ.")
        plan = workflows.canvas_to_plan(payload.get("canvas"))
        validation = validate_plan(plan, db=db, user=user)
        if not validation.valid:
            raise workflows.WorkflowError("Đề xuất không còn hợp lệ với catalog/quyền hiện tại.")
        row = workflows.save(db, workflow_id=row.id, user_id=user.id,
                             revision=row.revision, name=str(payload.get("name") or row.name),
                             canvas=payload["canvas"])
    except workflows.WorkflowConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except workflows.WorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _workflow_response(row)


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
        canvas = workflows.as_canvas(row)
        plan = workflows.canvas_to_plan(canvas)
        targets, scope = workflows.scope_targets(canvas, body.get("scope") or {"mode": "full"})
        scoped_plan = workflows.scope_plan(plan, targets)
        run = _prepare_run(db, user=user, plan=scoped_plan,
                           source={"workflow_id": row.id, "workflow_revision": row.revision,
                                   "scope": scope,
                                   "use_cache": bool(body.get("use_cache", True)),
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
        scheduled_at = _schedule_at(body.get("scheduled_at"))
        run = budget.approve(db, run_id=run.id, user_id=user.id, approved_by=user.id,
                             expected_version=int(body.get("version", 0)))
        _enqueue_advance(db, run, scheduled_at)
        approval_success = True
    except credit.ThieuCreditError:
        raise HTTPException(status_code=402, detail="Không đủ credit.") from None
    except (ValueError, budget.BudgetError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    finally:
        metrics.record_approval(success=approval_success)
    return JSONResponse(_run_json(run))


@router.post("/api/runs/{run_id}/restore-workflow")
async def workflow_restore_run(request: Request, run_id: str,
                               _identity: str = Depends(require_login),
                               db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body)
    user, source = _owned(db, request, run_id)
    try:
        canvas = workflows.plan_to_canvas(dict(source.plan))
        row = workflows.create(db, user_id=user.id,
                               name=str(body.get("name") or f"Khôi phục {source.goal[:80]}"),
                               canvas=canvas)
    except workflows.WorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return _workflow_response(row, status_code=201)


@router.get("/api/runs")
def workflow_run_list(request: Request, _identity: str = Depends(require_login),
                      db: Session = Depends(get_db)):
    user = _user(request)
    rows = db.query(AgentRun).filter_by(user_id=user.id).order_by(
        AgentRun.created_at.desc()).limit(20).all()
    return JSONResponse({"items": [_run_summary(row) for row in rows]})


@router.get("/api/runs/{run_id}")
def workflow_run_get(request: Request, run_id: str,
                     _identity: str = Depends(require_login),
                     db: Session = Depends(get_db)):
    _user_row, run = _owned(db, request, run_id)
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
    scheduled = _scheduled_datetime(run)
    if run.status == AGENT_RUNNING and (scheduled is None or
                                        scheduled <= datetime.now(timezone.utc)):
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
        _cancel_advance_jobs(db, run)
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


@router.get("/api/runs/{run_id}/bundle")
def workflow_run_bundle(request: Request, run_id: str,
                        _identity: str = Depends(require_login),
                        db: Session = Depends(get_db)):
    """Owned ZIP containing the immutable scoped plan and available artifacts."""
    _user_row, run = _owned(db, request, run_id)
    from platform_core.storage import StorageError, get_storage
    storage = get_storage(); artifact_rows = list(_run_json(run).get("artifacts") or [])
    keys = []
    for item in artifact_rows:
        try:
            key = _artifact_key(run, str(item["step_id"]),
                                sum(1 for prior in keys if prior[0] == item["step_id"]))
            keys.append((str(item["step_id"]), key))
        except HTTPException:
            continue
    total = sum(storage.size(key) for _step, key in keys if storage.exists(key))
    if total > 200 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Bundle vượt 200 MB; tải từng artifact.")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        source = next((item for item in reversed(run.decision_log or [])
                       if item.get("event") == "workflow_source"), {})
        archive.writestr("manifest.json", json.dumps({
            "format": "ltt-agent-run-bundle", "version": 1, "run_id": run.id,
            "status": run.status, "scope": source.get("scope", {"mode": "full"}),
            "plan": run.plan, "artifacts": artifact_rows,
        }, ensure_ascii=False, indent=2))
        for index, (step_id, key) in enumerate(keys, 1):
            if not storage.exists(key):
                continue
            try:
                with storage.open(key) as stream:
                    archive.writestr(f"artifacts/{step_id}/{index:03d}-{Path(key).name}", stream.read())
            except (OSError, StorageError):
                continue
    output.seek(0)
    return StreamingResponse(output, media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="ltt-run-{run.id[:8]}.zip"',
        "Cache-Control": "private, no-store"})


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


@router.get("/api/workflows/{workflow_id}/snapshots")
def workflow_snapshots(request: Request, workflow_id: str,
                       _identity: str = Depends(require_login),
                       db: Session = Depends(get_db)):
    user = _user(request)
    try:
        items = workflows.snapshots(db, workflow_id, user.id)
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail="Không tìm thấy workflow.") from None
    return {"items": [{"revision": item.revision, "name": item.name,
                        "reason": item.reason, "created_at": item.created_at.isoformat()}
                       for item in items]}


@router.post("/api/workflows/{workflow_id}/snapshots/{revision}/restore")
async def workflow_snapshot_restore(request: Request, workflow_id: str, revision: int,
                                    _identity: str = Depends(require_login),
                                    db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body); user = _user(request)
    try:
        row = workflows.restore_snapshot(db, workflow_id=workflow_id, user_id=user.id,
                                         revision=revision,
                                         expected_revision=int(body.get("revision", 0)))
    except workflows.WorkflowConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail="Không tìm thấy snapshot.") from None
    return _workflow_response(row)


@router.get("/api/workflows/{workflow_id}/shares")
def workflow_shares(request: Request, workflow_id: str,
                    _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    user = _user(request)
    try: workflows.get_owned(db, workflow_id, user.id)
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail="Không tìm thấy workflow.") from None
    rows = db.query(AgentWorkflowShare).filter_by(workflow_id=workflow_id, owner_id=user.id).order_by(
        AgentWorkflowShare.created_at.desc()).all()
    return {"items": [{"id": row.id, "permission": row.permission,
                        "expires_at": row.expires_at.isoformat(),
                        "revoked": row.revoked_at is not None} for row in rows]}


@router.post("/api/workflows/{workflow_id}/shares")
async def workflow_share_create(request: Request, workflow_id: str,
                                _identity: str = Depends(require_login),
                                db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body); user = _user(request)
    try: workflows.get_owned(db, workflow_id, user.id)
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail="Không tìm thấy workflow.") from None
    permission = str(body.get("permission") or "view")
    if permission not in {"view", "clone"}:
        raise HTTPException(status_code=422, detail="Quyền share không hợp lệ.")
    hours = max(1, min(int(body.get("expires_hours", 24)), 168))
    token = secrets.token_urlsafe(32)
    row = AgentWorkflowShare(workflow_id=workflow_id, owner_id=user.id,
                             token_hash=hashlib.sha256(token.encode()).hexdigest(),
                             permission=permission,
                             expires_at=datetime.now(timezone.utc) + timedelta(hours=hours))
    db.add(row); db.flush()
    return JSONResponse({"id": row.id, "permission": permission,
                         "path": f"/agent/shared/{token}", "expires_at": row.expires_at.isoformat()},
                        status_code=201)


def _active_share(db: Session, token: str) -> AgentWorkflowShare:
    digest = hashlib.sha256(token.encode()).hexdigest()
    row = db.query(AgentWorkflowShare).filter_by(token_hash=digest).first()
    now = datetime.now(timezone.utc)
    expires = row.expires_at if row and row.expires_at.tzinfo else (
        row.expires_at.replace(tzinfo=timezone.utc) if row else now)
    if row is None or row.revoked_at is not None or expires <= now:
        raise HTTPException(status_code=404, detail="Share không tồn tại hoặc đã hết hạn.")
    return row


@router.get("/shared/{token}")
def workflow_shared_view(request: Request, token: str,
                         _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    share = _active_share(db, token); row = db.get(AgentWorkflow, share.workflow_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Workflow không còn tồn tại.")
    return {"permission": share.permission, "workflow": _workflow_json(row)}


@router.post("/shared/{token}/clone")
async def workflow_shared_clone(request: Request, token: str,
                                _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body); user = _user(request)
    share = _active_share(db, token)
    if share.permission != "clone":
        raise HTTPException(status_code=403, detail="Share chỉ có quyền xem.")
    source = db.get(AgentWorkflow, share.workflow_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Workflow không còn tồn tại.")
    row = workflows.create(db, user_id=user.id, name=f"{source.name} — shared clone",
                           canvas=workflows.as_canvas(source), source_workflow_id=source.id)
    return _workflow_response(row, status_code=201)


@router.post("/api/workflows/{workflow_id}/shares/{share_id}/revoke")
async def workflow_share_revoke(request: Request, workflow_id: str, share_id: str,
                                _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    body = await request.json(); _verify_json_csrf(request, body); user = _user(request)
    row = db.query(AgentWorkflowShare).filter_by(id=share_id, workflow_id=workflow_id,
                                                owner_id=user.id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy share.")
    row.revoked_at = datetime.now(timezone.utc)
    return {"id": row.id, "revoked": True}


@router.get("/api/workflows/{workflow_id}/activity")
def workflow_activity(request: Request, workflow_id: str,
                      _identity: str = Depends(require_login), db: Session = Depends(get_db)):
    user = _user(request)
    try: snapshots = workflows.snapshots(db, workflow_id, user.id)
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail="Không tìm thấy workflow.") from None
    events = [{"event": "snapshot", "revision": item.revision, "reason": item.reason,
               "at": item.created_at.isoformat()} for item in snapshots]
    shares = db.query(AgentWorkflowShare).filter_by(workflow_id=workflow_id, owner_id=user.id).all()
    events.extend({"event": "share_revoked" if item.revoked_at else "share_created",
                   "permission": item.permission,
                   "at": (item.revoked_at or item.created_at).isoformat()} for item in shares)
    return {"items": sorted(events, key=lambda item: item["at"], reverse=True)[:100]}


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


@router.get("/api/workflows/{workflow_id}/frames/{frame_id}/export")
def workflow_frame_export(request: Request, workflow_id: str, frame_id: str,
                          _identity: str = Depends(require_login),
                          db: Session = Depends(get_db)):
    user = _user(request)
    try:
        row = workflows.get_owned(db, workflow_id, user.id)
        canvas = workflows.as_canvas(row)
        targets, scope = workflows.scope_targets(canvas, {"mode": "frame", "frame_id": frame_id})
        plan = workflows.scope_plan(workflows.canvas_to_plan(canvas), targets)
    except workflows.WorkflowNotFound:
        raise HTTPException(status_code=404, detail="Không tìm thấy workflow.") from None
    except workflows.WorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return JSONResponse({"format": "ltt-agent-workflow", "version": 1,
                         "name": f"{row.name} · {scope['frame_name']}",
                         "canvas": workflows.plan_to_canvas(plan), "scope": scope})


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
