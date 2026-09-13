"""Durable intent and read-back journal for VPS external mutations.

Only a fingerprint of non-secret request shape is retained. Provider responses
and exception text can contain credentials, so ambiguous failures are recorded
with a fixed operator-safe message rather than copied verbatim.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from apps.vps.tables import VpsExternalMutation, VpsInstance
from apps.vps.services.backends.contracts import BackendConflict


_SECRET_MARKERS = ("secret", "token", "password", "credential", "api_key", "apikey")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_shape(value: Any) -> Any:
    """Return stable request structure while discarding secret-bearing fields."""
    if isinstance(value, dict):
        return {
            str(key): _safe_shape(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if not any(marker in str(key).lower() for marker in _SECRET_MARKERS)
        }
    if isinstance(value, (list, tuple)):
        return [_safe_shape(item) for item in value]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    # Values are deliberately represented by type/digest, not copied. This
    # prevents an innocently named field from becoming a credential sink.
    return {"type": type(value).__name__, "digest": hashlib.sha256(
        str(value).encode("utf-8")).hexdigest()}


def _fingerprint(request: dict | None) -> str:
    payload = json.dumps(
        _safe_shape(request or {}), sort_keys=True, separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def intent(db, *, operation_id: str, instance: VpsInstance, step: str,
           request: dict | None = None) -> VpsExternalMutation:
    """Create one intent per operation/step, or return its durable predecessor."""
    if not instance.infrastructure_profile_id:
        raise ValueError("external mutation requires a pinned infrastructure profile")
    idem = f"{operation_id}:{step}"
    instance_id = instance.id
    profile_id = instance.infrastructure_profile_id
    fingerprint = _fingerprint(request)

    def validate(existing):
        if (existing.instance_id != instance_id
                or existing.profile_id != profile_id
                or existing.request_fingerprint != fingerprint):
            raise BackendConflict("idempotency key belongs to a different pinned request")
        return existing

    existing = db.execute(select(VpsExternalMutation).where(
        VpsExternalMutation.idempotency_key == idem)).scalar_one_or_none()
    if existing is not None:
        return validate(existing)
    row = VpsExternalMutation(
        operation_id=operation_id,
        instance_id=instance_id,
        profile_id=profile_id,
        step=step,
        idempotency_key=idem,
        state="INTENT",
        request_fingerprint=fingerprint,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        # A concurrent worker may have inserted the same deterministic intent.
        # The unique index is the arbiter; after rollback adopt only an exactly
        # matching predecessor, never silently change its request/profile.
        db.rollback()
        predecessor = db.execute(select(VpsExternalMutation).where(
            VpsExternalMutation.idempotency_key == idem)).scalar_one_or_none()
        if predecessor is None:
            raise BackendConflict("concurrent mutation intent requires review") from None
        return validate(predecessor)
    return row


def requested(db, row: VpsExternalMutation, *, external_ref: str = "") -> None:
    row.state = "REQUESTED"
    row.external_ref = str(external_ref or "")[:190]
    row.attempts = int(row.attempts or 0) + 1
    row.last_error_code = ""
    row.last_error_detail = ""
    db.flush()


def observed(db, row: VpsExternalMutation, *, external_ref: str = "") -> None:
    row.state = "OBSERVED"
    if external_ref:
        row.external_ref = str(external_ref)[:190]
    row.observed_at = _now()
    row.last_error_code = ""
    row.last_error_detail = ""
    db.flush()


def failed(db, row: VpsExternalMutation, code: str) -> None:
    row.state = "FAILED"
    row.last_error_code = str(code or "external_failure")[:64]
    row.last_error_detail = "external mutation failed; inspect canonical provider logs"
    db.flush()


def needs_review(db, row: VpsExternalMutation, _unsafe_detail: str = "") -> None:
    row.state = "NEEDS_REVIEW"
    row.last_error_code = "ambiguous_external_outcome"
    row.last_error_detail = (
        "external outcome is ambiguous; verify canonical provider read-back")
    db.flush()


def compensated(db, row: VpsExternalMutation) -> None:
    row.state = "COMPENSATED"
    row.compensated_at = _now()
    db.flush()
