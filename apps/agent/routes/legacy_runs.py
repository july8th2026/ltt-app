"""Luong plan/run doi dau, truoc canvas. Giu cho link cu."""
from __future__ import annotations

from __future__ import annotations
from datetime import datetime, timezone
from time import perf_counter
from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from apps.agent import jobs
from apps.agent.manifest import MANIFEST
from platform_core import credit
from platform_core.agent import budget, executor, metrics, runs
from platform_core.agent.planner import PlannerError, plan_once
from platform_core.agent.validator import validate_plan
from platform_core.models import AGENT_AWAITING_APPROVAL, AGENT_RUNNING
from platform_core.frontend_bundle import bundle_assets
from server.auth.csrf import verify_csrf_token
from server.auth.session import require_login
from server.deps import get_db
from server.templating import templates

from apps.agent.routes._shared import (
    _cancel_advance_jobs, _canvas_presentation_mode, _enqueue_advance,
    _owned, _page_context, _run_context, _run_json, _scheduled_datetime,
    _user, router)


@router.get("", response_class=HTMLResponse)
def page(request: Request, _identity: str = Depends(require_login)):
    return templates.TemplateResponse(request, "agent.html", _page_context(request))


@router.get("/canvas", response_class=HTMLResponse)
def canvas_page(request: Request, _identity: str = Depends(require_login)):
    canvas_js, canvas_css = bundle_assets("agent-canvas")
    if not canvas_js:
        raise HTTPException(status_code=503, detail="Canvas bundle chưa được build.")
    context = _page_context(request)
    context.update({"canvas_js": canvas_js, "canvas_css": canvas_css,
                    "canvas_presentation": _canvas_presentation_mode()})
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
