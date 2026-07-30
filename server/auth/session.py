"""Session-based auth helpers (P3)."""
from __future__ import annotations

from fastapi import HTTPException
from starlette.requests import Request

_SESSION_USER_KEY = "user"


def current_user(request: Request) -> str | None:
    return request.session.get(_SESSION_USER_KEY)


def log_in(request: Request, username: str) -> None:
    # Drop any pre-auth session keys (e.g. a CSRF token issued to an
    # anonymous visitor) rather than carrying them into an authenticated
    # session — cheap mitigation for session fixation given Starlette's
    # cookie-only session store has no server-side ID to rotate.
    request.session.clear()
    request.session[_SESSION_USER_KEY] = username


def log_out(request: Request) -> None:
    request.session.clear()


def require_login(request: Request) -> str:
    """FastAPI dependency: 303-redirects to /login when not authenticated."""
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user
