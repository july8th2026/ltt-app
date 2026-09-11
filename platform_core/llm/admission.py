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
        from platform_core.public_api import metrics
        metrics.increment(metrics.ADMISSION_EXPIRED, len(expired))
        db.flush()
    return len(expired)


def _khoa_resource(db: Session, resource: str) -> None:
    """Tuần tự hoá luật nhận của MỘT tài nguyên trong transaction hiện tại.

    Luật ngân sách cộng token của mọi lease sống rồi mới INSERT — hai tiến trình
    cùng cộng rồi cùng INSERT là vượt pool dù `UNIQUE(resource, slot)` vẫn giữ
    đúng số slot. Khoá advisory của transaction tự nhả ở commit/rollback, cùng
    khuôn `public_api/limits.py:_lock_job_admission`. SQLite bỏ qua (test logic
    đơn luồng); race kiểm bằng PostgreSQL thật.
    """
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return
    from sqlalchemy import text

    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
               {"k": f"llm-admission:{resource}"})


def _lop_cua(lease: ExecutionLease) -> str:
    """Lease cũ (trước multijob) không có lớp: job là nền, còn lại là tương tác."""
    from platform_core.llm import luat_nhan

    if lease.lop:
        return lease.lop
    return luat_nhan.NEN if lease.mode == "job" else luat_nhan.TUONG_TAC


def xet_va_giu(
    db: Session,
    *,
    resource: str,
    slots: int,
    user_id: str,
    mode: str,
    holder_id: str,
    job_id: str = "",
    timeout: timedelta = ORPHAN_TIMEOUT,
    lop: str = "",
    token_dat_truoc: int = 0,
    token_prefill_moi: int = 0,
    la_whale: bool = False,
    token_pool: int = 0,
    waiter_id: str = "",
    tuoi_cho_s: float = 0.0,
    cho_whale_toi_da_s: float = 30.0,
    now: datetime | None = None,
) -> tuple[ExecutionLease | None, str]:
    """Xét theo `luat_nhan` rồi giành một slot. Trả `(lease | None, mã lý do)`.

    ⭐ Khi `token_pool <= 0` và không khai `lop`: ĐÚNG hành vi cũ "đếm slot" —
       mọi tool không phải model nhà (ảnh, tiếng…) không đổi gì.
    ⛔ Caller giữ quyền commit/rollback, như `acquire` luôn làm.
    """
    from platform_core.llm import luat_nhan, phong_cho

    resource = resource.strip()
    if not resource or slots <= 0:
        return None, luat_nhan.CHO_SLOT
    if token_pool <= 0 and not lop:
        lease = _giu_slot_trong(db, resource=resource, slots=slots, user_id=user_id,
                                mode=mode, holder_id=holder_id, job_id=job_id,
                                timeout=timeout)
        return lease, ("" if lease is not None else luat_nhan.CHO_SLOT)

    _khoa_resource(db, resource)
    reclaim_expired(db, resource=resource, timeout=timeout)
    song = db.query(ExecutionLease).filter(ExecutionLease.resource == resource).all()
    giu = [luat_nhan.Luot(id=l.id, user_id=l.user_id, lop=_lop_cua(l),
                          token_dat_truoc=int(l.token_dat_truoc or 0),
                          la_whale=bool(l.la_whale)) for l in song]
    cho = phong_cho.chup_nguoi_cho(db, resource=resource, now=now)
    yc = luat_nhan.Luot(id=waiter_id or holder_id, user_id=user_id,
                        lop=lop or luat_nhan.TUONG_TAC,
                        token_dat_truoc=int(token_dat_truoc), la_whale=bool(la_whale),
                        tuoi_s=float(tuoi_cho_s))
    px = luat_nhan.xet(yc, giu, cho, luat_nhan.ThamSo(
        so_slot=slots, pool=int(token_pool), cho_whale_toi_da_s=cho_whale_toi_da_s))
    if not px.nhan:
        from platform_core.public_api import metrics
        metrics.increment(metrics.ADMISSION_REJECTED)
        return None, px.ly_do
    lease = _chen_lease(db, resource=resource, slots=slots,
                        taken={l.slot for l in song}, user_id=user_id, mode=mode,
                        holder_id=holder_id, job_id=job_id, lop=yc.lop,
                        token_dat_truoc=int(token_dat_truoc),
                        token_prefill_moi=int(token_prefill_moi),
                        la_whale=bool(la_whale))
    return lease, ("" if lease is not None else luat_nhan.CHO_SLOT)


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
    **luat,
) -> ExecutionLease | None:
    """Giành một slot; ``None`` nghĩa là không nhận được (xem `xet_va_giu` để biết vì sao).

    `**luat` là các tham số đa lượt của `xet_va_giu` (`lop`, `token_dat_truoc`,
    `token_pool`…). Không truyền gì ⇒ đúng hành vi cũ.
    """
    lease, _ly_do = xet_va_giu(db, resource=resource, slots=slots, user_id=user_id,
                               mode=mode, holder_id=holder_id, job_id=job_id,
                               timeout=timeout, **luat)
    return lease


def _giu_slot_trong(
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
    """Hành vi CŨ: giành slot trống đầu tiên; ``None`` nghĩa là mọi slot còn sống đang bận."""
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
            from platform_core.public_api import metrics
            metrics.increment(metrics.ADMISSION_ACQUIRED)
            return lease
        except IntegrityError:
            # Một tiến trình khác thắng đúng slot giữa SELECT và INSERT.
            continue
    from platform_core.public_api import metrics
    metrics.increment(metrics.ADMISSION_REJECTED)
    return None


def _chen_lease(db: Session, *, resource: str, slots: int, taken: set,
                user_id: str, mode: str, holder_id: str, job_id: str,
                lop: str, token_dat_truoc: int, token_prefill_moi: int,
                la_whale: bool) -> ExecutionLease | None:
    """INSERT lease vào slot trống đầu tiên — cùng khuôn savepoint của đường cũ."""
    from platform_core.public_api import metrics

    for slot in range(slots):
        if slot in taken:
            continue
        lease = ExecutionLease(
            resource=resource, slot=slot, user_id=user_id, mode=mode,
            holder_id=holder_id, job_id=job_id, lop=lop,
            token_dat_truoc=token_dat_truoc, token_prefill_moi=token_prefill_moi,
            la_whale=la_whale)
        try:
            with db.begin_nested():
                db.add(lease)
                db.flush()
            metrics.increment(metrics.ADMISSION_ACQUIRED)
            return lease
        except IntegrityError:
            # Một tiến trình khác thắng đúng slot giữa SELECT và INSERT (SQLite
            # không có advisory lock; PostgreSQL thì không tới được đây).
            continue
    metrics.increment(metrics.ADMISSION_REJECTED)
    return None


def xoa_co_whale(lease_id: str) -> bool:
    """Prefill của lượt này đã xong (byte đầu tiên về) ⇒ nó thôi là whale.

    ⭐ Luật "≤1 whale" (D-05) nói về PREFILL — thứ làm đói người khác. Phần decode
       sau đó rẻ (M-1: người mới chạy lại ~46 tok/s cạnh nó). Giữ cờ suốt lượt là
       bắt whale kế tiếp chờ thêm vài phút vô cớ. Phiên mới, commit riêng; hỏng
       thì chỉ ghi log — tệ nhất là whale kế chờ lâu hơn, không sai tiền.
    """
    if not lease_id:
        return False

    def _xoa(db: Session, lid: str) -> bool:
        lease = db.get(ExecutionLease, lid)
        if lease is None or not lease.la_whale:
            return False
        lease.la_whale = False
        db.flush()
        return True

    try:
        return _with_fresh_session(_xoa, lease_id)
    except Exception:  # noqa: BLE001 - chỉ ảnh hưởng thứ tự, không ảnh hưởng tiền
        log.exception("khong tat duoc co whale cua lease %s", lease_id)
        return False


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
    from platform_core.public_api import metrics
    metrics.increment(metrics.ADMISSION_RELEASED)
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
    **luat,
) -> Iterator[ExecutionLease | None]:
    """Giữ lease đã commit trong suốt khối và luôn nhả khi rời khối.

    `**luat` chuyển thẳng cho `xet_va_giu` (lớp, token đặt chỗ, pool…) — job nền
    đi qua đây với `lop="nen"` (multijob Task 9).
    """
    sessions = get_session()
    db = next(sessions)
    lease: ExecutionLease | None = None
    try:
        lease = acquire(
            db, resource=resource, slots=slots, user_id=user_id, mode=mode,
            holder_id=holder_id, job_id=job_id, **luat)
        db.commit()
        if lease is None:
            yield None
        else:
            with keep_alive(lease.id):
                yield lease
    finally:
        sessions.close()
