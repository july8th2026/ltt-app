"""
Worker control routes (P6) — start/stop the publishing worker from the
browser.

Every state-changing route is POST + CSRF-protected. Starting a run hands
off to WorkerApplication, which keeps running after the browser closes
(ADR-004).
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.services.worker_control import (
    NoWorkersConfiguredError,
    WorkerBusyError,
    get_controller,
)
from server.templating import templates

router = APIRouter(tags=["workers"])


def _load_config(request: Request) -> dict:
    core_settings = getattr(request.app.state, "core_settings", None)
    return dict(core_settings.config) if core_settings else {}


def _stored_workers(platform: str) -> list:
    from core.worker_store import load_workers
    try:
        return load_workers(platform=platform or None)
    except Exception:
        return []


def _render(request: Request, user: str, *, error: str = "", notice: str = "",
            status_code: int = 200):
    controller = get_controller()
    snapshot = controller.snapshot()
    platform = snapshot.platform or "facebook"
    return templates.TemplateResponse(
        request, "workers.html",
        {
            "user": user,
            "nav": "workers",
            "snapshot": snapshot,
            "configured": _stored_workers(platform),
            "csrf_token": issue_csrf_token(request),
            "error": error,
            "notice": notice,
        },
        status_code=status_code,
    )


@router.get("/workers", response_class=HTMLResponse)
def workers_page(request: Request, user: str = Depends(require_login)):
    return _render(request, user)


@router.post("/workers/start", response_class=HTMLResponse)
def start_worker(
    request: Request,
    csrf_token: str = Form(...),
    platform: str = Form("facebook"),
    user: str = Depends(require_login),
):
    if not verify_csrf_token(request, csrf_token):
        return _render(request, user, error="Phiên đã hết hạn, tải lại trang.",
                       status_code=400)

    platform = platform if platform in ("facebook", "tiktok") else "facebook"
    try:
        get_controller().start(
            workers=_stored_workers(platform),
            config=_load_config(request),
            platform=platform,
        )
    except (WorkerBusyError, NoWorkersConfiguredError) as exc:
        return _render(request, user, error=str(exc), status_code=409)
    except Exception as exc:
        # Ownership conflict with the desktop runner lands here — the
        # message names which host/pid holds the lock.
        return _render(request, user, error=str(exc), status_code=409)

    return RedirectResponse("/workers", status_code=303)


@router.post("/workers/stop", response_class=HTMLResponse)
def stop_worker(
    request: Request,
    csrf_token: str = Form(...),
    user: str = Depends(require_login),
):
    if not verify_csrf_token(request, csrf_token):
        return _render(request, user, error="Phiên đã hết hạn, tải lại trang.",
                       status_code=400)
    get_controller().stop()
    return RedirectResponse("/workers", status_code=303)


@router.get("/api/workers/status")
def workers_status_api(request: Request, user: str = Depends(require_login)):
    """JSON snapshot for the page's auto-refresh — avoids a full re-render
    (and a fresh doctor run) every few seconds."""
    s = get_controller().snapshot()
    return {
        "running": s.running,
        "platform": s.platform,
        "workers": s.workers,
        "log": s.log[-40:],
        "last_error": s.last_error,
    }
