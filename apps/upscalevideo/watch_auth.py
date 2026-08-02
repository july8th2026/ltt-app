"""Scoped bearer credentials for the local Upscale Watch Agent.

The raw token is returned once. Only a domain-separated SHA-256 digest is kept
in the existing server-side session table; it cannot be reused as a web cookie.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from platform_core.models import Session, User

MARKER = "upscale-watch-agent"
TOKEN_DAYS = 90


def _digest(raw: str) -> str:
    return hashlib.sha256(("upscale-watch\0" + raw).encode("utf-8")).hexdigest()


def issue(db, user_id: str) -> str:
    revoke(db, user_id)
    raw = secrets.token_urlsafe(40)
    now = datetime.now(timezone.utc)
    db.add(Session(id=_digest(raw), user_id=user_id, created_at=now,
                   expires_at=now + timedelta(days=TOKEN_DAYS),
                   user_agent=MARKER, ip="local-agent"))
    db.flush()
    return raw


def revoke(db, user_id: str) -> int:
    result = db.execute(delete(Session).where(
        Session.user_id == user_id, Session.user_agent == MARKER))
    db.flush()
    return int(result.rowcount or 0)


def authenticate(db, authorization: str) -> User | None:
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None
    raw = authorization[len(prefix):].strip()
    if len(raw) < 32:
        return None
    row = db.get(Session, _digest(raw))
    if row is None or row.user_agent != MARKER:
        return None
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= datetime.now(timezone.utc):
        return None
    return db.execute(select(User).where(
        User.id == row.user_id, User.is_active.is_(True))).scalar_one_or_none()
