"""Attempts that never became a request, and the ones that did but should not.

Why a table of its own
----------------------

``ApiRequestLog`` (EXT-09) is the **customer's** log, and its ``user_id`` is the
axis that keeps one account from seeing another's traffic. The events here often
belong to nobody: a caller with no credential, a key that does not exist, a key
that was revoked last week. Writing those into a tenant-scoped table would mean
either inventing an owner or storing rows nobody can ever see — so they live
apart, and only an operator reads them.

That separation was not obvious until the gap showed itself: ``guard.py`` skips
the request log entirely when there is no principal, so **every authentication
failure was invisible in the database**. "Is somebody probing us" and "is a
revoked key still being used" — both named in the EXT-16 brief — could not be
answered without reading process log files.

What is recorded, and what is refused
-------------------------------------

Recorded: the kind of failure, the address it came from, the **public half** of
whatever key id was presented, the route, and the correlation id that ties it to
everything else. The public half is what a support conversation already refers
to, which is the same reasoning ``auth.py`` used when it started logging it.

Never recorded: the secret half of a token, an ``Authorization`` header, a
request body, or a provider credential. There is no code path here that accepts
them, so a future caller cannot pass one by accident.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from platform_core.public_api.tables import ApiSecurityEvent

#: The kinds worth a row. Each one is a question an operator actually asks; a
#: kind nobody would search for is noise that makes the real ones harder to see.
#:
#: One limit worth stating: ``REVOKED_KEY`` is almost never what gets recorded,
#: because ``keys.verify()`` answers the same ``None`` for an unknown key, a
#: wrong secret and a revoked one — on purpose, so a caller cannot enumerate
#: valid key ids by watching which failure comes back. The authentication path
#: therefore does not know it saw a revoked key. ``revoked_key_attempts()``
#: below answers that question at read time instead, where answering it costs
#: nothing.
NO_CREDENTIAL = "auth.no_credential"
UNKNOWN_KEY = "auth.unknown_key"
REVOKED_KEY = "auth.revoked_key"
IP_NOT_ALLOWED = "auth.ip_not_allowed"
MISCONFIGURED = "auth.misconfigured"
THROTTLED = "auth.throttled"
KINDS = (NO_CREDENTIAL, UNKNOWN_KEY, REVOKED_KEY, IP_NOT_ALLOWED,
         MISCONFIGURED, THROTTLED)

#: How long these are kept. Long enough to investigate an incident from last
#: month; short enough that a table nobody prunes does not become the biggest
#: thing in the database.
RETENTION_DAYS = 90


def _now() -> datetime:
    return datetime.now(timezone.utc)


def record(db, *, kind: str, ip: str = "", key_id: str = "", route: str = "",
           request_id: str = "", user_id: str = "", detail: str = "",
           now: datetime | None = None) -> ApiSecurityEvent | None:
    """Write one attempt. Unknown kinds are refused rather than stored.

    Returns ``None`` for an unknown kind instead of raising: this is called from
    the authentication path, and a logging mistake must never turn a 401 into a
    500.
    """
    if kind not in KINDS:
        return None
    row = ApiSecurityEvent(
        id=str(uuid.uuid4()), kind=kind, ip=str(ip or "")[:64],
        key_id=str(key_id or "")[:48], route=str(route or "")[:200],
        request_id=str(request_id or "")[:64], user_id=str(user_id or "")[:36],
        detail=str(detail or "")[:200], created_at=now or _now())
    db.add(row)
    return row


def list_recent(db, *, kind: str = "", ip: str = "", key_id: str = "",
                since: datetime | None = None, limit: int = 100,
                offset: int = 0) -> list:
    statement = select(ApiSecurityEvent)
    if kind:
        statement = statement.where(ApiSecurityEvent.kind == str(kind))
    if ip:
        statement = statement.where(ApiSecurityEvent.ip == str(ip))
    if key_id:
        statement = statement.where(ApiSecurityEvent.key_id == str(key_id))
    if since is not None:
        statement = statement.where(ApiSecurityEvent.created_at >= since)
    return list(db.execute(
        statement.order_by(ApiSecurityEvent.created_at.desc())
        .offset(max(0, int(offset))).limit(max(1, min(int(limit), 500)))
    ).scalars())


def summary(db, *, hours: int = 24, now: datetime | None = None) -> dict:
    """Counts per kind, plus the noisiest sources.

    The addresses matter more than the total: one address failing four hundred
    times is a scanner, four hundred addresses failing once each is a broken
    release, and the same total tells the two apart only when it is broken down.
    """
    moment = now or _now()
    since = moment - timedelta(hours=max(1, int(hours)))

    by_kind = dict(db.execute(
        select(ApiSecurityEvent.kind, func.count())
        .where(ApiSecurityEvent.created_at >= since)
        .group_by(ApiSecurityEvent.kind)).all())
    top_ips = db.execute(
        select(ApiSecurityEvent.ip, func.count())
        .where(ApiSecurityEvent.created_at >= since, ApiSecurityEvent.ip != "")
        .group_by(ApiSecurityEvent.ip)
        .order_by(func.count().desc()).limit(10)).all()
    top_keys = db.execute(
        select(ApiSecurityEvent.key_id, func.count())
        .where(ApiSecurityEvent.created_at >= since,
               ApiSecurityEvent.key_id != "")
        .group_by(ApiSecurityEvent.key_id)
        .order_by(func.count().desc()).limit(10)).all()

    return {
        "hours": int(hours),
        "since": since,
        "total": sum(int(count) for count in by_kind.values()),
        # Counted by joining, not by reading a label — see the note on KINDS.
        "revoked_in_use": len(revoked_key_attempts(db, since=since)),
        "by_kind": {str(kind): int(count) for kind, count in by_kind.items()},
        "top_ips": [(str(ip), int(count)) for ip, count in top_ips],
        "top_keys": [(str(key), int(count)) for key, count in top_keys],
    }


def revoked_key_attempts(db, *, since: datetime | None = None,
                         limit: int = 100) -> list:
    """Recorded attempts whose key id belongs to a key that was revoked.

    Matched here rather than labelled at write time, because the code that
    refuses the call is deliberately unable to tell a revoked key from an
    invented one. Doing the join now changes nothing an attacker can observe and
    gives an operator the answer they actually came for: *somebody is still
    using a credential we turned off* — which usually means a deployment nobody
    updated, not an attack.
    """
    from platform_core.public_api.tables import DeveloperApiKey

    statement = select(ApiSecurityEvent).where(ApiSecurityEvent.key_id != "")
    if since is not None:
        statement = statement.where(ApiSecurityEvent.created_at >= since)
    rows = list(db.execute(statement.order_by(
        ApiSecurityEvent.created_at.desc()).limit(
            max(1, min(int(limit), 500)))).scalars())
    if not rows:
        return []

    revoked = {
        str(key_id) for (key_id,) in db.execute(
            select(DeveloperApiKey.key_id).where(
                DeveloperApiKey.revoked_at.is_not(None),
                DeveloperApiKey.key_id.in_({row.key_id for row in rows}))).all()
    }
    return [row for row in rows if row.key_id in revoked]


def purge_expired(db, *, days: int = RETENTION_DAYS,
                  now: datetime | None = None) -> int:
    cutoff = (now or _now()) - timedelta(days=max(1, int(days)))
    rows = db.execute(select(ApiSecurityEvent).where(
        ApiSecurityEvent.created_at < cutoff)).scalars().all()
    for row in rows:
        db.delete(row)
    return len(rows)


__all__ = [
    "IP_NOT_ALLOWED", "KINDS", "MISCONFIGURED", "NO_CREDENTIAL",
    "RETENTION_DAYS", "REVOKED_KEY", "THROTTLED", "UNKNOWN_KEY", "list_recent",
    "purge_expired", "record", "revoked_key_attempts", "summary",
]
