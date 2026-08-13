"""DB-backed idempotency for chargeable API operations.

The rule this implements: *same key + same request → same logical operation;
same key + different request → conflict.*

Why it cannot be built on ``jobs.dedupe_key``: that one deduplicates only while
the earlier job is still queued or running. A client that retries after its
first attempt already finished — the normal reaction to a timeout it cannot
distinguish from a failure — would get a second job and a second credit hold.

Why the unique constraint does the work: two requests racing with the same key
both attempt an INSERT; the database lets exactly one through and the loser
reads the winner's row. Checking "does a record exist?" first and inserting
afterwards is the classic check-then-write race, and under concurrency it does
double-charge.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from platform_core.public_api.errors import conflict, invalid_request
from platform_core.public_api.tables import (ApiIdempotencyRecord,
                                             IDEMPOTENCY_COMPLETED,
                                             IDEMPOTENCY_IN_PROGRESS)

MAX_KEY_LENGTH = 255
MIN_KEY_LENGTH = 8


def _now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_hash(payload) -> str:
    """Stable fingerprint of a request body, independent of key order."""
    canon = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str,
                       separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def require_key(raw: str) -> str:
    """Validate the ``Idempotency-Key`` header.

    Required rather than optional on chargeable routes: making it optional means
    the safe path is the one a client has to remember, and the unsafe one is the
    default. A minimum length keeps "1" or "retry" — values that collide across
    unrelated requests — out of the table.
    """
    key = str(raw or "").strip()
    if not key:
        raise invalid_request(
            "This endpoint requires an Idempotency-Key header.")
    if len(key) < MIN_KEY_LENGTH or len(key) > MAX_KEY_LENGTH:
        raise invalid_request(
            f"Idempotency-Key must be between {MIN_KEY_LENGTH} and "
            f"{MAX_KEY_LENGTH} characters.")
    return key


def _lock(db, key_id: str, operation: str, key: str) -> None:
    """Serialise same-key requests on PostgreSQL.

    The unique constraint already makes double-insert impossible; this only
    turns a racing pair into "wait, then replay" instead of "fail, then retry",
    which is the friendlier of the two correct behaviours. SQLite serialises
    writes at the file level, so it needs nothing here.
    """
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
                   {"k": f"public-api-idem:{key_id}:{operation}:{key}"})


def find(db, *, key_id: str, operation: str, key: str):
    return db.execute(select(ApiIdempotencyRecord).where(
        ApiIdempotencyRecord.key_id == key_id,
        ApiIdempotencyRecord.operation == operation,
        ApiIdempotencyRecord.idempotency_key == key,
    )).scalar_one_or_none()


def begin(db, *, key_id: str, user_id: str, operation: str, key: str,
          request_hash: str):
    """Claim the key for this request, or return the record that already owns it.

    Returns ``(record, replay)``. ``replay=True`` means the caller must not do
    the work again and should answer from ``record.response``.

    Raises 409 when the same key arrives with a different payload, and when a
    first attempt is still in flight — a client that fires two different
    requests under one key has a bug, and one that retries mid-flight should
    wait rather than be handed a half-built answer.
    """
    _lock(db, key_id, operation, key)
    existing = find(db, key_id=key_id, operation=operation, key=key)
    if existing is not None:
        return _replay(existing, request_hash)

    record = ApiIdempotencyRecord(
        id=str(uuid.uuid4()), key_id=key_id, user_id=user_id,
        operation=operation, idempotency_key=key, request_hash=request_hash,
        status=IDEMPOTENCY_IN_PROGRESS, created_at=_now(), updated_at=_now(),
    )
    db.add(record)
    try:
        db.flush()
    except IntegrityError:
        # Lost the race (or no advisory lock, as on SQLite). The winner's row is
        # authoritative; roll back only this insert and read it.
        db.rollback()
        existing = find(db, key_id=key_id, operation=operation, key=key)
        if existing is None:      # pragma: no cover - defensive
            raise
        return _replay(existing, request_hash)
    return record, False


def _replay(record, request_hash: str):
    from platform_core.public_api import metrics

    if record.request_hash != request_hash:
        metrics.increment(metrics.IDEMPOTENCY_CONFLICT)
        raise conflict(
            "This Idempotency-Key was already used with a different request "
            "body.", idempotency_key=record.idempotency_key)
    if record.status != IDEMPOTENCY_COMPLETED:
        raise conflict(
            "A request with this Idempotency-Key is still being processed.",
            idempotency_key=record.idempotency_key)
    return record, True


def complete(db, record, *, response: dict, job_id: str = "") -> None:
    """Store the logical answer so a later retry replays it byte for byte."""
    record.status = IDEMPOTENCY_COMPLETED
    record.response = dict(response or {})
    record.job_id = str(job_id or "")
    record.updated_at = _now()
    db.flush()
