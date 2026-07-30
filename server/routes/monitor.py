"""Monitor and TT Audit pages (web port of gui/monitor_tab.py, audit_tab.py)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.services import monitor_service
from server.services import ui_constants as UI
from server.services.audit_service import runner
from server.templating import templates

router = APIRouter(tags=["monitor"])


def _config(request: Request) -> dict:
    cs = getattr(request.app.state, "core_settings", None)
    return dict(cs.config) if cs else {}


@router.get("/monitor", response_class=HTMLResponse)
def monitor_page(request: Request, user: str = Depends(require_login)):
    data = monitor_service.collect(_config(request))
    return templates.TemplateResponse(request, "monitor.html", {
        "user": user, "nav": "monitor", "data": data,
        "colors": UI.COLORS, "csrf_token": issue_csrf_token(request),
    })


@router.post("/monitor/reset-metrics")
def monitor_reset(
    request: Request,
    csrf_token: str = Form(...),
    user: str = Depends(require_login),
):
    if verify_csrf_token(request, csrf_token):
        monitor_service.reset_metrics()
    return RedirectResponse("/monitor", status_code=303)


@router.get("/api/monitor/logs")
def monitor_logs(request: Request, user: str = Depends(require_login)):
    """Log tail for the page's auto-refresh — avoids re-collecting the whole
    dashboard (which makes live Meta/TikTok API calls) every few seconds."""
    return {"logs": monitor_service.collect_logs()}


@router.get("/audit", response_class=HTMLResponse)
def audit_page(request: Request, user: str = Depends(require_login)):
    config = _config(request)
    run = runner()
    # First visit, or a stale cache: kick off a background run. The page
    # renders immediately with whatever is cached (possibly nothing) and the
    # operator can refresh.
    if run.is_stale():
        run.refresh_async(config)
    return templates.TemplateResponse(request, "audit.html", {
        "user": user, "nav": "audit", "report": run.report(),
        "colors": UI.COLORS, "csrf_token": issue_csrf_token(request),
    })


@router.post("/audit/refresh")
def audit_refresh(
    request: Request,
    csrf_token: str = Form(...),
    user: str = Depends(require_login),
):
    if verify_csrf_token(request, csrf_token):
        runner().refresh_async(_config(request))
    return RedirectResponse("/audit", status_code=303)


@router.get("/api/audit/status")
def audit_status(request: Request, user: str = Depends(require_login)):
    r = runner()
    rep = r.report()
    return {"running": rep.running, "summary": rep.summary,
            "counts": rep.counts, "age": rep.age_text,
            "items": len(rep.items), "error": rep.error}
