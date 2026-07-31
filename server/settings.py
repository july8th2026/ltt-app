"""
Server-specific settings (P3) — session secret and admin credentials.

Layered on top of core.settings (environment profile + runtime paths),
not a replacement for it. Never stores or logs a secret value; only reads
them from the environment.
"""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass

from core.settings import Environment, resolve_environment


class MissingServerSecretError(RuntimeError):
    """A required server secret (session key / admin credentials) is unset."""


@dataclass(frozen=True)
class ServerSettings:
    environment:          Environment
    session_secret:       str
    admin_username:       str
    admin_password_hash:  str
    secure_cookies:       bool   # False only allowed in development, for plain-HTTP local testing


def load_server_settings(env: dict | None = None) -> ServerSettings:
    e = os.environ if env is None else env
    environment = resolve_environment(env)

    session_secret = (e.get("LTT_SESSION_SECRET") or "").strip()
    admin_username = (e.get("LTT_ADMIN_USERNAME") or "").strip()
    admin_password_hash = (e.get("LTT_ADMIN_PASSWORD_HASH") or "").strip()

    if environment == Environment.DEVELOPMENT:
        # Convenience only: an ephemeral secret so `uvicorn server.app:app
        # --reload` works out of the box locally. Every process restart
        # invalidates all sessions — acceptable for development, and
        # explicitly refused below for the other two profiles so a real
        # deployment can never silently fall back to this.
        session_secret = session_secret or secrets.token_urlsafe(32)
        admin_username = admin_username or "admin"
        # No default password hash is fabricated — an unset admin hash in
        # development still means "nobody can log in" rather than a known
        # default credential shipping in the codebase.
    else:
        # Q29: admin-env chi la BREAK-GLASS, khong con bat buoc. Admin chinh la
        # user role=admin trong CSDL (H3-admin, tools/create_admin.py). O
        # production LTT_ADMIN_PASSWORD_HASH thuong RONG => admin-env vo hieu;
        # dat lai qua env khi can cuu ho. Chi SESSION_SECRET la bat buoc o day.
        missing = [
            name for name, value in (
                ("LTT_SESSION_SECRET", session_secret),
            ) if not value
        ]
        if missing:
            raise MissingServerSecretError(
                f"Missing required server secret(s) for environment "
                f"'{environment.value}': {', '.join(missing)}. Set them as "
                "environment variables (see docs/_luutru/PROJECT_MEMORY.md for "
                "names/storage location — never commit the values)."
            )

    secure_cookies = environment != Environment.DEVELOPMENT

    return ServerSettings(
        environment=environment,
        session_secret=session_secret,
        admin_username=admin_username,
        admin_password_hash=admin_password_hash,
        secure_cookies=secure_cookies,
    )
