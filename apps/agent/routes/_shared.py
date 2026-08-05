"""
_shared.py - router va helper dung chung cho moi module route cua app agent.

Truoc 2026-08-06 ca 48 handler nam trong MOT file 1.308 dong. Tach theo mien
(AGENTS.md muc 8) de debug theo hang muc: loi chia se link thi mo `sharing.py`,
khong phai cuon qua tro ly AI va man hinh quan tri.

Logic nghiep vu cua app nay nam o `platform_core/agent/` (budget, executor,
planner, runs, validator, workflows) chu khong o `services/` trong app: agent
la mot phan cua nen tang, khong phai app khach.

Router khai o day chu khong o `__init__` de moi module import duoc no ma khong
tao vong import.
"""
from __future__ import annotations

import json
import hashlib
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy.orm import Session

from apps.agent.manifest import MANIFEST
from platform_core import jobs as job_queue
from platform_core.agent import budget, runs, workflows
from platform_core.agent.tools import resolve_params_schema
from platform_core.models import APP_PROJECT_ACTIVE, AgentWorkflow, AgentWorkflowShare, AppProject
from platform_core.agent.validator import validate_plan
from platform_core.models import AgentRun, Job
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.deps import user_hien_tai

router = APIRouter(tags=["agent"])
_ASSET_LIMIT = 90 * 1024 * 1024
_ASSET_MIME_PREFIXES = ("image/", "video/", "audio/")
_ASSISTANT_SALT = "ltt-agent-assistant-proposal-v1"
_PREFERENCES_SLUG = "agent.preferences"
_DEFAULT_PREFERENCES = {"theme": "dark", "catalog_mode": "simple",
                        "presentation_version": "creative-v1"}


def _canvas_presentation_mode() -> str:
    """Creative is the default; legacy keeps the H20 renderer as rollback."""
    configured = os.environ.get("LTT_AGENT_CANVAS_PRESENTATION", "creative")
    return "legacy" if configured.strip().lower() == "legacy" else "creative"


def _assistant_serializer() -> URLSafeTimedSerializer:
    secret = (os.environ.get("LTT_SESSION_SECRET") or "").strip()
    if not secret:
        raise RuntimeError("Assistant proposal signer chưa được cấu hình.")
    return URLSafeTimedSerializer(secret)


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
        "audio.generate": ("Tạo âm thanh", "content", True),
        "asset.image": ("Ảnh đầu vào", "input", False),
        "asset.images": ("Bộ ảnh", "input", False),
        "asset.video": ("Video đầu vào", "input", False),
        "asset.audio": ("Âm thanh đầu vào", "input", False),
        "image.upscale": ("Nâng cấp ảnh", "transform", False),
        "video.upscale": ("Nâng cấp video", "transform", False),
        "video.extract_frames": ("Tách khung hình", "transform", False),
        "media.merge_image": ("Ghép ảnh", "transform", False),
        "media.merge_video": ("Ghép video", "transform", False),
        "video.social_import": ("Social Video", "input", False),
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
        # H20 stored "advanced" as its default. An unversioned row is not an
        # explicit customer opt-in, so H21 migrates its presentation to simple
        # without changing the workflow document or ToolSpec runtime.
        if (saved.get("presentation_version") == "creative-v1" and
                saved.get("catalog_mode") in {"simple", "advanced"}):
            payload["catalog_mode"] = saved["catalog_mode"]
    return {**payload, "revision": row.revision if row else 0}

def _prepare_run(db: Session, *, user, plan: dict, source: dict) -> AgentRun:
    _require_new_runs_enabled(user)
    validation = validate_plan(plan, db=db, user=user)
    if not validation.valid:
        raise workflows.WorkflowError("Workflow không còn hợp lệ.")
    run = runs.create_run_capped(db, user_id=user.id, goal=str(plan.get("goal", "")),
                                 plan=plan, budget_max=int(plan.get("budget_max_credit", 0)))
    # Canvas đã được người dùng dựng và validate; không có lần gọi AI planner nào
    # ở luồng này nên chỉ báo/giữ chi phí thực thi. Luồng form goal→AI plan ở trên
    # vẫn dùng planning_cost mặc định.
    budget.set_quote(db, run, plan=plan, validation=validation, planning_cost=0)
    event = {"event": "workflow_source", **source, "quote_hash": _quote_hash(run)}
    runs.append_decision(db, run, event)
    return run

def _active_share(db: Session, token: str) -> AgentWorkflowShare:
    digest = hashlib.sha256(token.encode()).hexdigest()
    row = db.query(AgentWorkflowShare).filter_by(token_hash=digest).first()
    now = datetime.now(timezone.utc)
    expires = row.expires_at if row and row.expires_at.tzinfo else (
        row.expires_at.replace(tzinfo=timezone.utc) if row else now)
    if row is None or row.revoked_at is not None or expires <= now:
        raise HTTPException(status_code=404, detail="Share không tồn tại hoặc đã hết hạn.")
    return row

def _require_admin_user(request: Request):
    user = _user(request)
    if getattr(user, "role", "") != "admin":
        raise HTTPException(status_code=404, detail="Không tìm thấy.")
    return user
