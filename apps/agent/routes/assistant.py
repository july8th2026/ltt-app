"""Tro ly AI: dung ke hoach, xem truoc va ap dung de xuat."""
from __future__ import annotations

from __future__ import annotations
import json
from time import perf_counter
from fastapi import Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from itsdangerous import BadSignature, SignatureExpired
from sqlalchemy.orm import Session
from platform_core.agent import metrics, workflows
from platform_core.models import AgentWorkflow
from platform_core.agent.planner import PlannerError, plan_once
from platform_core.agent.validator import validate_plan
from server.auth.session import require_login
from server.deps import get_db

from apps.agent.routes._shared import (
    _ASSISTANT_SALT, _assistant_serializer, _user, _verify_json_csrf,
    _workflow_response, router)


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
