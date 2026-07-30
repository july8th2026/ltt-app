"""CSRF protection for session-cookie-authenticated form POSTs (P3).

Synchronizer-token pattern: a random token is stored server-side in the
signed session and must be echoed back as a hidden form field on the next
state-changing POST. Session cookies alone are not CSRF-safe (the browser
attaches them automatically to cross-site requests), so every POST route
must call `verify_csrf_token` before acting on the request.
"""
from __future__ import annotations

import hmac
import secrets

from starlette.requests import Request

_SESSION_KEY = "csrf_token"


def issue_csrf_token(request: Request) -> str:
    """Return the current session's CSRF token, generating one if absent."""
    token = request.session.get(_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[_SESSION_KEY] = token
    return token


def verify_csrf_token(request: Request, submitted_token: str) -> bool:
    expected = request.session.get(_SESSION_KEY)
    if not expected or not submitted_token:
        return False
    return hmac.compare_digest(expected, submitted_token)
