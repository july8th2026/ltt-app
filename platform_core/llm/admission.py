"""Admission lease chung cho mọi đường gọi tài nguyên LLM.

Lease chỉ trả lời "ai được chạy bây giờ"; durable queue vẫn chỉ là ``jobs``.
Caller giữ quyền commit/rollback để có thể gắn acquire vào transaction nghiệp
vụ của chính nó.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import logging
import threading
from typing import Iterator

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from platform_core.db import get_session
from platform_core.models import ExecutionLease


ORPHAN_TIMEOUT = timedelta(minutes=20)
HEARTBEAT_SECONDS = 60.0
log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def reclaim_expired(
    db: Session,
    *,
    resource: str = "",
    timeout: timedelta = ORPHAN_TIMEOUT,
) -> int:
    """Xoá lease mồ côi trong transaction hiện tại và trả số dòng đã xoá."""
    cutoff = _now() - timeout
    query = db.query(ExecutionLease)
    if resource:
        query = query.filter(ExecutionLease.resource == resource)
    leases = query.all()
    expired = [lease for lease in leases if _aware(lease.heartbeat_at) < cutoff]
    for lease in expired:
        db.delete(lease)
    if expired:
        db.flush()
    return len(expired)


def acquire(
    db: Session,
    *,
    resource: str,
    slots: int,
    user_id: str,
    mode: str,
    holder_id: str,
    job_id: str = "",
    timeout: timedelta = ORPHAN_TIMEOUT,
) -> ExecutionLease | None:
    """Giành một slot; ``None`` nghĩa là toàn bộ slot còn sống đang bận."""
    resource = resource.strip()
    if not resource or slots <= 0:
        return None

    reclaim_expired(db, resource=resource, timeout=timeout)
    taken = {
        row[0]
        for row in db.query(ExecutionLease.slot).filter(
            ExecutionLease.resource == resource).all()
    }
    for slot in range(slots):
        if slot in taken:
            continue
        lease = ExecutionLease(
            resource=resource,
            slot=slot,
            user_id=user_id,
            mode=mode,
            holder_id=holder_id,
            job_id=job_id,
        )
        try:
            with db.begin_nested():
                db.add(lease)
                db.flush()
            return lease
        except IntegrityError:
            # Một tiến trình khác thắng đúng slot giữa SELECT và INSERT.
            continue
    return None


def heartbeat(db: Session, lease_id: str) -> bool:
    lease = db.get(ExecutionLease, lease_id)
    if lease is None:
        return False
    lease.heartbeat_at = _now()
    db.flush()
    return True


def release(db: Session, lease_id: str) -> bool:
    """Nhả lease idempotent; caller quyết định thời điểm commit."""
    lease = db.get(ExecutionLease, lease_id)
    if lease is None:
        return False
    db.delete(lease)
    db.flush()
    return True


def _with_fresh_session(action, lease_id: str) -> bool:  # noqa: ANN001
    sessions = get_session()
    db = next(sessions)
    try:
        changed = action(db, lease_id)
        db.commit()
        return changed
    except Exception:
        db.rollback()
        raise
    finally:
        sessions.close()


def heartbeat_by_id(lease_id: str) -> bool:
    return _with_fresh_session(heartbeat, lease_id)


def release_by_id(lease_id: str) -> bool:
    return _with_fresh_session(release, lease_id)


@contextmanager
def keep_alive(lease_id: str) -> Iterator[None]:
    """Đập nhịp một lease đã commit và nhả idempotent khi khối kết thúc."""
    stop = threading.Event()

    def _pulse() -> None:
        while not stop.wait(HEARTBEAT_SECONDS):
            try:
                heartbeat_by_id(lease_id)
            except Exception:  # noqa: BLE001 - TTL remains the fallback
                log.exception("khong dap nhip duoc execution lease %s", lease_id)

    pulse = threading.Thread(
        target=_pulse, name=f"execution-hb-{lease_id[:8]}", daemon=True)
    pulse.start()
    try:
        yield
    finally:
        stop.set()
        pulse.join(timeout=5)
        try:
            release_by_id(lease_id)
        except Exception:  # noqa: BLE001 - orphan timeout is the final guard
            log.exception("khong nha duoc execution lease %s", lease_id)


@contextmanager
def hold_persisted(
    *,
    resource: str,
    slots: int,
    user_id: str,
    mode: str,
    holder_id: str,
    job_id: str = "",
) -> Iterator[ExecutionLease | None]:
    """Giữ lease đã commit trong suốt khối và luôn nhả khi rời khối."""
    sessions = get_session()
    db = next(sessions)
    lease: ExecutionLease | None = None
    try:
        lease = acquire(
            db, resource=resource, slots=slots, user_id=user_id, mode=mode,
            holder_id=holder_id, job_id=job_id)
        db.commit()
        if lease is None:
            yield None
        else:
            with keep_alive(lease.id):
                yield lease
    finally:
        sessions.close()
