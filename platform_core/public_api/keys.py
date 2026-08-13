"""Lifecycle of developer API keys: issue, verify, list, revoke, rotate.

Threat model this file is written against
-----------------------------------------

*Stolen database dump.* Only ``HMAC-SHA256(pepper, secret)`` is stored and the
pepper lives in the process environment, not in the database. Without it an
attacker cannot even test guesses offline, and with 256 bits of CSPRNG secret
there is nothing to guess anyway.

*Denial of service through the auth path.* Verification is one HMAC — tens of
microseconds. A password-grade KDF here would let any anonymous caller burn a
CPU core per request; that is a worse bug than the one it would prevent, and the
input is random rather than human-chosen so the KDF buys nothing.

*Key enumeration.* An unknown ``key_id`` and a wrong secret take the same path:
the digest is always computed, the comparison is always ``compare_digest``, and
both answer with the same ``None``. Callers upstream must not tell the two apart
in the response either.

*Write amplification.* ``last_used_at`` is bucketed, so a client polling a job
every two seconds does not turn every read into a row update.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from platform_core.public_api.scopes import normalize_scopes
from platform_core.public_api.tables import (DeveloperApiKey, KEY_PREFIX,
                                             DEVKEY_ACTIVE)

# 32 bytes = 256 bits, urlsafe-base64 without padding -> 43 characters.
SECRET_BYTES = 32
KEY_ID_BYTES = 16          # 128 bits: collisions are not a practical concern
SECRET_LENGTH = 43
KEY_ID_LENGTH = 32
MAX_ISSUE_ATTEMPTS = 3

# How stale ``last_used_at`` is allowed to be. Five minutes is enough for
# "is this key still in use?" and turns a per-request write into a rare one.
LAST_USED_BUCKET = timedelta(minutes=5)

MAX_KEYS_PER_USER = 25
MAX_EXPIRY = timedelta(days=365)

PEPPER_ENV = "LTT_API_KEY_PEPPER"
PEPPER_VERSION_ENV = "LTT_API_KEY_PEPPER_VERSION"
# Retired peppers stay readable so a rotation does not invalidate live keys:
# LTT_API_KEY_PEPPER_V1, LTT_API_KEY_PEPPER_V2, ...
RETIRED_PEPPER_PREFIX = "LTT_API_KEY_PEPPER_V"
MIN_PEPPER_LENGTH = 32

_HEX = frozenset("0123456789abcdef")
_SECRET_ALPHABET = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


class DeveloperKeyError(Exception):
    """Refusing to issue/verify because of configuration or bad input."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


# ── Pepper handling ───────────────────────────────────────────────────────────

def current_pepper(env: dict | None = None) -> tuple[int, str]:
    """``(version, secret)`` used for new keys. Raises when unconfigured.

    Deliberately no default value: a built-in fallback pepper is the same as no
    pepper at all, and it would ship silently to every installation.
    """
    values = os.environ if env is None else env
    pepper = str(values.get(PEPPER_ENV, "")).strip()
    if len(pepper) < MIN_PEPPER_LENGTH:
        raise DeveloperKeyError(
            f"{PEPPER_ENV} is missing or too short "
            f"(need at least {MIN_PEPPER_LENGTH} characters).")
    try:
        version = int(str(values.get(PEPPER_VERSION_ENV, "1")).strip() or "1")
    except ValueError as exc:
        raise DeveloperKeyError(f"{PEPPER_VERSION_ENV} must be an integer.") from exc
    if version < 1:
        raise DeveloperKeyError(f"{PEPPER_VERSION_ENV} must be >= 1.")
    return version, pepper


def pepper_for_version(version: int, env: dict | None = None) -> str:
    """Pepper that produced an existing digest, current or retired."""
    values = os.environ if env is None else env
    active_version, active = current_pepper(values)
    if int(version) == active_version:
        return active
    retired = str(values.get(f"{RETIRED_PEPPER_PREFIX}{int(version)}", "")).strip()
    if len(retired) < MIN_PEPPER_LENGTH:
        raise DeveloperKeyError(
            f"No pepper available for version {version}; keys issued with it "
            "cannot be verified until it is restored or the keys are rotated.")
    return retired


def digest_secret(secret: str, pepper: str) -> str:
    return hmac.new(pepper.encode("utf-8"), secret.encode("utf-8"),
                    hashlib.sha256).hexdigest()


# ── Token format ──────────────────────────────────────────────────────────────

def _new_key_id() -> str:
    return secrets.token_hex(KEY_ID_BYTES)


def _new_secret() -> str:
    return secrets.token_urlsafe(SECRET_BYTES)[:SECRET_LENGTH]


def format_token(key_id: str, secret: str) -> str:
    return f"{KEY_PREFIX}_{key_id}_{secret}"


def parse_token(token: str) -> tuple[str, str] | None:
    """``ltt_sk_<key_id>_<secret>`` → ``(key_id, secret)``; ``None`` if malformed.

    Structural checks only, and no logging: a malformed token is still a
    credential someone typed, so it must not end up in a log line or an error
    message.
    """
    if not token or not isinstance(token, str):
        return None
    # `maxsplit=3` matters: the secret is urlsafe base64, so it legitimately
    # contains "_" and a plain split() would shred a perfectly valid token.
    parts = token.split("_", 3)
    if len(parts) != 4:                       # "ltt", "sk", key_id, secret
        return None
    if f"{parts[0]}_{parts[1]}" != KEY_PREFIX:
        return None
    key_id, secret = parts[2], parts[3]
    if len(key_id) != KEY_ID_LENGTH or len(secret) != SECRET_LENGTH:
        return None
    if not all(char in _HEX for char in key_id):
        return None
    if not all(char in _SECRET_ALPHABET for char in secret):
        return None
    return key_id, secret


# ── Issue ─────────────────────────────────────────────────────────────────────

def issue(db, *, user_id: str, name: str = "", scopes=(), allowed_tools=(),
          expires_at: datetime | None = None, env: dict | None = None,
          now: datetime | None = None) -> tuple[DeveloperApiKey, str]:
    """Create a key. Returns the row and the plaintext token **once**.

    The caller must show the plaintext to its owner and then forget it: nothing
    in this module can recover it afterwards, by design.
    """
    current = now or _now()
    version, pepper = current_pepper(env)
    owner = str(user_id or "").strip()
    if not owner:
        raise DeveloperKeyError("A developer key must belong to a user.")

    live = db.execute(select(DeveloperApiKey).where(
        DeveloperApiKey.user_id == owner,
        DeveloperApiKey.revoked_at.is_(None))).scalars().all()
    if len([key for key in live if key.is_usable(now=current)]) >= MAX_KEYS_PER_USER:
        raise DeveloperKeyError(
            f"This account already has {MAX_KEYS_PER_USER} active API keys.")

    expiry = _aware(expires_at)
    if expiry is not None:
        if expiry <= current:
            raise DeveloperKeyError("expires_at must be in the future.")
        if expiry > current + MAX_EXPIRY:
            raise DeveloperKeyError("expires_at must be within one year.")

    clean_scopes = normalize_scopes(scopes)
    clean_tools = _normalize_tools(allowed_tools)

    # A 128-bit key_id will not collide in practice; retrying anyway means a
    # freak collision (or a truncated generator in a future edit) fails one
    # request instead of raising an opaque IntegrityError at commit time.
    last_error: Exception | None = None
    for _attempt in range(MAX_ISSUE_ATTEMPTS):
        key_id, secret = _new_key_id(), _new_secret()
        key = DeveloperApiKey(
            id=str(uuid.uuid4()), user_id=owner, name=str(name or "")[:120],
            key_id=key_id, verifier_digest=digest_secret(secret, pepper),
            pepper_version=version, scopes=clean_scopes,
            allowed_tools=clean_tools, enabled=True, created_at=current,
            expires_at=expiry,
        )
        db.add(key)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            last_error = exc
            continue
        return key, format_token(key_id, secret)
    raise DeveloperKeyError("Could not allocate a unique key id.") from last_error


def _normalize_tools(tools) -> list:
    seen, out = set(), []
    for tool in tools or ():
        name = str(tool).strip()
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


# ── Verify ────────────────────────────────────────────────────────────────────

def verify(db, token: str, *, env: dict | None = None,
           now: datetime | None = None) -> DeveloperApiKey | None:
    """Resolve a bearer token to a usable key, or ``None``.

    Every failure mode returns the same ``None`` and walks the same code path.
    A caller that answered "unknown key" differently from "wrong secret" would
    turn this into an oracle for enumerating valid key ids.
    """
    current = now or _now()
    parsed = parse_token(token)
    if parsed is None:
        _equalize_work(env)
        return None
    key_id, secret = parsed

    key = db.execute(select(DeveloperApiKey).where(
        DeveloperApiKey.key_id == key_id)).scalar_one_or_none()
    if key is None:
        _equalize_work(env)
        return None

    try:
        pepper = pepper_for_version(int(key.pepper_version or 1), env)
    except DeveloperKeyError:
        # A key whose pepper is gone cannot be verified. Failing closed is the
        # only safe answer; the operator sees it as "key stopped working", which
        # is exactly what a missing pepper means.
        return None

    candidate = digest_secret(secret, pepper)
    if not hmac.compare_digest(candidate, str(key.verifier_digest or "")):
        return None
    if not key.is_usable(now=current):
        return None
    return key


def _equalize_work(env: dict | None) -> None:
    """Do the same HMAC for a malformed/unknown token as for a real one."""
    try:
        _version, pepper = current_pepper(env)
    except DeveloperKeyError:
        pepper = "unconfigured-pepper-placeholder-value-only"
    digest_secret(secrets.token_urlsafe(SECRET_BYTES)[:SECRET_LENGTH], pepper)


def touch_last_used(db, key: DeveloperApiKey, *, now: datetime | None = None) -> bool:
    """Refresh ``last_used_at`` at most once per bucket. True when it wrote."""
    current = now or _now()
    previous = _aware(key.last_used_at)
    if previous is not None and current - previous < LAST_USED_BUCKET:
        return False
    key.last_used_at = current
    db.flush()
    return True


# ── Management ────────────────────────────────────────────────────────────────

def list_for_user(db, user_id: str) -> list:
    """Metadata for one owner. Never returns anything secret."""
    return list(db.execute(select(DeveloperApiKey).where(
        DeveloperApiKey.user_id == str(user_id or ""),
    ).order_by(DeveloperApiKey.created_at.desc())).scalars().all())


def get_owned(db, *, user_id: str, key_id: str) -> DeveloperApiKey | None:
    """Owner-scoped lookup. The owner filter is in the query, not in an ``if``.

    Fetch-then-check is how object-level authorization gets forgotten; making
    ownership part of the WHERE clause means a miss is indistinguishable from a
    key that does not exist, which is also the right answer to return.
    """
    return db.execute(select(DeveloperApiKey).where(
        DeveloperApiKey.user_id == str(user_id or ""),
        DeveloperApiKey.key_id == str(key_id or ""),
    )).scalar_one_or_none()


def revoke(db, key: DeveloperApiKey, *, now: datetime | None = None) -> bool:
    """Irreversible. Returns False when the key was already revoked."""
    if key.revoked_at is not None:
        return False
    key.revoked_at = now or _now()
    key.enabled = False
    db.flush()
    return True


def set_enabled(db, key: DeveloperApiKey, enabled: bool) -> None:
    """Temporary pause, unlike :func:`revoke` which cannot be undone."""
    if key.revoked_at is not None:
        raise DeveloperKeyError("A revoked key cannot be re-enabled.")
    key.enabled = bool(enabled)
    db.flush()


def rotate(db, key: DeveloperApiKey, *, env: dict | None = None,
           now: datetime | None = None) -> str:
    """Give an existing key new secret material; the old token stops working.

    In-place rather than issue-and-revoke so scopes, name and history stay on
    one row. For a zero-downtime swap, issue a second key, migrate the client,
    then revoke the first — that is a deployment choice, not a default.
    """
    if key.revoked_at is not None:
        raise DeveloperKeyError("A revoked key cannot be rotated.")
    current = now or _now()
    version, pepper = current_pepper(env)
    for _attempt in range(MAX_ISSUE_ATTEMPTS):
        key_id, secret = _new_key_id(), _new_secret()
        key.key_id = key_id
        key.verifier_digest = digest_secret(secret, pepper)
        key.pepper_version = version
        key.rotated_at = current
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            continue
        return format_token(key_id, secret)
    raise DeveloperKeyError("Could not allocate a unique key id.")


def status_of(key: DeveloperApiKey, *, now: datetime | None = None) -> str:
    return key.status(now=now)


__all__ = ["DEVKEY_ACTIVE", "DeveloperKeyError", "current_pepper", "digest_secret",
           "format_token", "get_owned", "issue", "list_for_user", "parse_token",
           "pepper_for_version", "revoke", "rotate", "set_enabled", "status_of",
           "touch_last_used", "verify"]
