"""Bearer authentication for ``/api/v1``.

One request, one verification: parse ``Authorization: Bearer``, verify the
developer key, build a :class:`Principal` from what the *credential* says — never
from anything the request body or path claims.

What is deliberately not here:

* **no CSRF.** A CSRF token defends a browser session that the browser attaches
  automatically. A bearer token is attached only by a client that already has
  it, and this surface refuses cookies outright, so the attack CSRF prevents
  cannot happen. The developer portal (Prompt 15) is a session UI and keeps its
  CSRF protection;
* **no "who are you" in the failure.** Every rejection is the same 401 with the
  same body. Distinguishing "unknown key" from "wrong secret" from "revoked"
  would let anyone map which key ids exist;
* **no raw token anywhere.** Audit lines carry the public ``key_id`` when the
  token was at least well-formed, plus a reason code. The secret half never
  reaches a log, an exception message or a response.
"""
from __future__ import annotations

import logging

from fastapi import Depends
from sqlalchemy.orm import Session
from starlette.requests import Request

from platform_core.public_api import errors
from platform_core.public_api import keys as devkeys
from platform_core.public_api import limits
from platform_core.public_api import metrics
from platform_core.public_api import policy
from platform_core.public_api.principal import Principal, ensure_scope
from server.api import deps
from server.api.context import client_ip, request_id
from server.deps import get_db

log = logging.getLogger("ltt.public_api.auth")

# Reason codes are for operators reading logs, never for the caller: the
# response says only "invalid or missing credential".
REASON_NO_HEADER = "no_bearer_header"
REASON_MALFORMED = "malformed_token"
REASON_UNKNOWN_OR_WRONG = "unknown_or_wrong_secret"
REASON_UNUSABLE = "revoked_expired_or_disabled"
REASON_MISCONFIGURED = "pepper_not_configured"
REASON_IP_NOT_ALLOWED = "ip_not_in_key_allowlist"


def _config(request):
    return getattr(request.app.state, "public_api_config", None)


def _audit_failure(request, reason: str, key_id: str = "") -> None:
    """One redacted line per rejected request.

    ``key_id`` is the public half of the token and is safe to record; it is what
    a support conversation refers to. The secret half is never passed in.
    """
    proxies = getattr(_config(request), "trusted_proxies", ())
    metrics.increment(metrics.AUTH_FAILURE)
    log.warning(
        "public api auth rejected reason=%s key_id=%s ip=%s path=%s request_id=%s",
        reason, key_id or "-", client_ip(request, proxies), request.url.path,
        request_id(request),
    )


def resolve_from_database(request, db) -> Principal | None:
    """The production resolver installed into ``server.api.deps``.

    Returns ``None`` for every failure; the caller turns that into one 401.
    """
    config = _config(request)
    token = deps.bearer_token(request)
    if not token:
        _audit_failure(request, REASON_NO_HEADER)
        _throttle(request, config, "")
        return None

    parsed = devkeys.parse_token(token)
    if parsed is None:
        # Still runs a digest inside verify(); do not shortcut it here either.
        devkeys.verify(db, token)
        _audit_failure(request, REASON_MALFORMED)
        _throttle(request, config, "")
        return None
    public_key_id = parsed[0]

    try:
        key = devkeys.verify(db, token)
    except devkeys.DeveloperKeyError:
        # Missing/short pepper: the platform is misconfigured, not the caller.
        # Fail closed and make the cause visible to an operator.
        _audit_failure(request, REASON_MISCONFIGURED, public_key_id)
        return None
    if key is None:
        _audit_failure(request, REASON_UNKNOWN_OR_WRONG, public_key_id)
        _throttle(request, config, public_key_id)
        return None
    if not key.is_usable():
        _audit_failure(request, REASON_UNUSABLE, public_key_id)
        _throttle(request, config, public_key_id)
        return None

    # The key verified; it is simply not allowed to be presented from here.
    # Same 401 as every other failure — telling a caller "right key, wrong
    # address" confirms the key is real to whoever stole it.
    proxies = getattr(config, "trusted_proxies", ()) if config else ()
    if not devkeys.ip_allowed(key, client_ip(request, proxies)):
        _audit_failure(request, REASON_IP_NOT_ALLOWED, public_key_id)
        _throttle(request, config, public_key_id)
        return None

    principal = Principal(
        key_id=key.key_id,
        user_id=key.user_id,
        scopes=frozenset(key.scopes or ()),
        allowed_tools=frozenset(key.allowed_tools or ()),
        project_id=str(key.project_id or ""),
        mode=str(getattr(key, "mode", "live") or "live"),
        request_id=request_id(request),
    )
    # Published before the limiter runs, not after: a 429 belongs to a caller
    # who has already proved who they are, and it is the failure they are most
    # likely to come looking for. Attaching it afterwards left exactly that one
    # unattributable in the access log and in the request log (EXT-09).
    request.state.api_principal = principal

    # A kill switch is checked here rather than in the middleware because three
    # of its six scopes name a subject — a user, a project, a credential — and
    # the subject is only known once the credential has verified. Doing it at
    # the same boundary keeps one place where "not now" is decided (EXT-14).
    _refuse_if_switched_off(db, request, principal)

    # Rate limit before doing anything else with the request: a key in a loop
    # should cost one window lookup, not a full handler. The ceiling comes from
    # the resolved policy, and the account bucket is what stops a caller buying
    # more rate by creating more keys.
    if config is not None:
        resolved = policy.resolve(db, config=config, principal=principal)
        request.state.api_limits = resolved
        limits.enforce_request_rate(
            key_id=key.key_id, config=config, limits=resolved,
            user_id=principal.user_id,
            is_write=request.method.upper() not in ("GET", "HEAD", "OPTIONS"))

    # Bucketed, so a client polling a job does not turn every read into a write.
    devkeys.touch_last_used(db, key)

    metrics.increment(metrics.AUTH_SUCCESS)
    return principal


def _throttle(request, config, key_id: str) -> None:
    """Count this failure. Raises 429 once the source is clearly probing."""
    if config is None:
        return
    limits.note_auth_failure(
        client_ip=client_ip(request, getattr(config, "trusted_proxies", ())),
        key_id=key_id, config=config)


def _refuse_if_switched_off(db, request, principal) -> None:
    """Turn an engaged switch into the refusal a caller can act on.

    No new error codes: `maintenance` and a disabled tool are 503s because the
    caller should come back, and a suspended subject is a 403 because coming
    back will not help. Inventing codes for these would grow the public error
    vocabulary for states it already describes.

    The reason the operator typed **is** returned. It is written by an operator
    for a customer, and withholding it just moves the same conversation into a
    support ticket.
    """
    from platform_core.public_api.tables import (KILL_GLOBAL_WRITES,
                                                 KILL_MAINTENANCE, KILL_TOOL)

    is_write = request.method.upper() not in ("GET", "HEAD", "OPTIONS")
    refusal = policy.check(db, principal=principal, is_write=is_write)
    if refusal is None:
        return

    metrics.increment(metrics.KILL_SWITCH_REFUSED)
    if refusal.scope == KILL_MAINTENANCE:
        raise errors.service_unavailable(
            f"The API is in maintenance: {refusal.reason}",
            retry_after=refusal.retry_after)
    if refusal.scope == KILL_GLOBAL_WRITES:
        raise errors.read_only(
            f"Write operations are paused: {refusal.reason}")
    if refusal.scope == KILL_TOOL:
        raise errors.service_unavailable(
            f"This tool is temporarily unavailable: {refusal.reason}",
            retry_after=refusal.retry_after)
    raise errors.forbidden(
        f"API access for this account is suspended: {refusal.reason}")


def install_database_resolver() -> None:
    deps.set_principal_resolver(resolve_from_database)


def require_principal(request: Request,
                      db: Session = Depends(get_db)) -> Principal:
    """FastAPI dependency: the verified caller, or 401."""
    return deps.resolve_principal(request, db)


def require_scope(scope: str):
    """Dependency factory: verified caller **and** the named scope, or 403.

    Scope is checked here, at the boundary, so it is refused before a route can
    reach a quote, a credit hold or a job insert. A check further in is a check
    that some future route will forget.
    """

    def _dependency(principal: Principal = Depends(require_principal)) -> Principal:
        ensure_scope(principal, scope)
        return principal

    return _dependency


def optional_principal(request: Request,
                       db: Session = Depends(get_db)) -> Principal | None:
    """For routes that answer anonymously but personalise when authenticated."""
    if not deps.bearer_token(request):
        return None
    try:
        return deps.resolve_principal(request, db)
    except errors.ApiError:
        return None


__all__ = ["install_database_resolver", "optional_principal", "require_principal",
           "require_scope", "resolve_from_database"]
