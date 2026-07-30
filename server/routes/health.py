"""Health/readiness/version endpoints (P3). No authentication required —
these are meant to be probed by the reverse proxy / service manager."""
from __future__ import annotations

from fastapi import APIRouter, Request, Response

try:
    from version import APP_VERSION_SHORT as _APP_VERSION
except ImportError:
    _APP_VERSION = "unknown"

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict:
    """Process is up and able to answer HTTP requests. Never checks
    dependencies — that's /ready's job. A monitor that gets anything other
    than 200 here should restart the process, not wait."""
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request, response: Response) -> dict:
    """Process is up AND its config loaded successfully at startup."""
    core_settings = getattr(request.app.state, "core_settings", None)
    if core_settings is None:
        response.status_code = 503
        return {"status": "not_ready", "reason": "config not loaded"}
    return {"status": "ready", "environment": core_settings.environment.value}


@router.get("/version")
def version() -> dict:
    return {"version": _APP_VERSION}
