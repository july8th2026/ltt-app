"""Timeline và nhật ký debug dùng chung cho mọi job của nền tảng.

Hợp đồng này cố ý không biết tên app. App/worker chỉ phát event có mã ổn định;
UI khách hàng chỉ đọc event ``customer``. Event ``internal`` dành cho operator
và vẫn được lọc PII/bí mật trước khi ghi để log không trở thành kho secret thứ
hai.
"""
from __future__ import annotations

import re
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session as DbSession

from platform_core.models import Job, JobEvent

CUSTOMER = "customer"
INTERNAL = "internal"
_VISIBILITIES = {CUSTOMER, INTERNAL}
_LEVELS = {"debug", "info", "warning", "error"}
_DENY_KEYS = {
    "authorization", "cookie", "set_cookie", "password", "password_hash",
    "token", "secret", "api_key", "credential", "email", "goal", "prompt",
    "params", "plan", "checkpoint", "request", "body", "provider_payload",
}
_CUSTOMER_KEYS = {
    "percent", "attempt", "max_attempts", "delay_seconds", "artifact_count",
    "related_job_id", "status",
}
_EMAIL = re.compile(r"(?i)\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_SECRET_TEXT = re.compile(
    r"(?i)(bearer\s+\S+|(?:api[_ -]?key|token|password|secret|credential)"
    r"\s*[:=]\s*\S+)"
)
_event_write_failures = 0
CUSTOMER_RETENTION_DAYS = 365
INTERNAL_RETENTION_DAYS = 30


def sanitize_text(value: Any, limit: int = 2000) -> str:
    """Lọc chuỗi không tin cậy trước khi ghi CSDL hoặc operational log."""
    text = str(value or "")
    text = _EMAIL.sub("[Filtered email]", text)
    text = _SECRET_TEXT.sub("[Filtered]", text)
    return text[:limit]


def error_fingerprint(value: Any) -> str:
    """Ổn định hóa lỗi đã lọc để gom nhóm bug mà không lưu traceback/payload."""
    return hashlib.sha256(sanitize_text(value, limit=5000).encode("utf-8")).hexdigest()[:16]


# Alias nội bộ giữ bề mặt cũ trong module; caller mới dùng tên công khai rõ nghĩa.
_safe_text = sanitize_text


def redact_details(value: Any) -> Any:
    """Lọc đệ quy metadata kỹ thuật trước khi nó chạm CSDL."""
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            cleaned[str(key)[:80]] = (
                "[Filtered]" if normalized in _DENY_KEYS else redact_details(item)
            )
        return cleaned
    if isinstance(value, (list, tuple)):
        return [redact_details(item) for item in value[:50]]
    if isinstance(value, str):
        return _safe_text(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _safe_text(value)


def _customer_details(details: dict | None) -> dict:
    source = details or {}
    return {key: redact_details(value) for key, value in source.items()
            if key in _CUSTOMER_KEYS}


def append(
    db: DbSession, job: Job, event_code: str, *, public_message: str = "",
    details: dict | None = None, level: str = "info", visibility: str = CUSTOMER,
    event_key: str | None = None,
) -> JobEvent:
    """Thêm một event và cấp sequence tăng dần. Không commit.

    ``event_key`` là khoá idempotency theo job. Khi cùng event được phát lại do
    retry HTTP/worker, hàm trả event cũ và không tạo dòng thứ hai.
    """
    if visibility not in _VISIBILITIES:
        raise ValueError("invalid job event visibility")
    if level not in _LEVELS:
        raise ValueError("invalid job event level")
    code = str(event_code or "").strip().lower()
    if not code or len(code) > 48:
        raise ValueError("invalid job event code")
    key = (str(event_key).strip()[:128] if event_key else None)
    if key:
        old = db.execute(select(JobEvent).where(
            JobEvent.job_id == job.id, JobEvent.event_key == key,
        )).scalars().first()
        if old is not None:
            return old

    # Cấp số bằng UPDATE nguyên tử trên chính dòng job. Hai worker/request chạy
    # đồng thời sẽ tuần tự hoá ở CSDL, không cùng đọc rồi cùng ghi một sequence.
    next_sequence = db.execute(
        update(Job).where(Job.id == job.id)
        .values(event_sequence=Job.event_sequence + 1)
        .returning(Job.event_sequence)
    ).scalar_one()
    job.event_sequence = int(next_sequence)
    event = JobEvent(
        job_id=job.id,
        user_id=job.user_id,
        app_slug=job.app_slug,
        sequence=int(next_sequence),
        event_code=code,
        level=level,
        visibility=visibility,
        public_message=_safe_text(public_message, 255),
        details=(_customer_details(details) if visibility == CUSTOMER
                 else redact_details(details or {})),
        correlation_id=str(job.correlation_id or "")[:36],
        event_key=key,
    )
    db.add(event)
    try:
        db.flush()
    except Exception:
        global _event_write_failures
        _event_write_failures += 1
        raise
    return event


def event_write_failures() -> int:
    return _event_write_failures


def append_progress_counter(
    db: DbSession, job: Job, event_code: str = "progress_counter", *,
    da_xong: int, tong: int, don_vi: str, visibility: str = INTERNAL,
) -> JobEvent:
    """Nhịp tiến độ TRONG một giai đoạn — mang bộ đếm, không chỉ dấu thời gian.

    🔑 BẤT BIẾN Ở BIÊN (khuôn `ke_cat.kiem()`): đây là nơi DUY NHẤT ghi loại
       event này, nên `if` ở đây canh được MỌI người gọi — một `if` ở chỗ gọi
       chỉ canh một chỗ gọi.

    ⛔ NÉM nếu thiếu `da_xong`/`tong`: một nhịp tim lease chứng minh TIẾN TRÌNH
       còn sống, ⛔ không chứng minh VIỆC đang tiến — heartbeat 60s của
       `advance` 37.010 lượt/52 phút là "còn sống và quay tại chỗ", một dấu
       thời gian không tự phân biệt được nó với "đang làm việc".

    ⛔ NÉM nếu `da_xong` lùi so với lần ghi trước CỦA CÙNG JOB (một job = một
       `(run_id, stage, attempt)`, xem `jobs.py:526`): bộ đếm việc không được
       giật lùi trong một lượt chạy.
    """
    if da_xong is None or tong is None:
        raise ValueError("nhip tien do thieu bo dem da_xong/tong")
    da_xong = int(da_xong)
    tong = int(tong)
    if da_xong < 0 or tong < 0:
        raise ValueError(f"nhip tien do am: da_xong={da_xong} tong={tong}")
    truoc = db.execute(
        select(JobEvent.details)
        .where(JobEvent.job_id == job.id, JobEvent.event_code == event_code)
        .order_by(JobEvent.sequence.desc()).limit(1)
    ).scalars().first()
    if truoc is not None:
        cu = int((truoc or {}).get("da_xong") or 0)
        if da_xong < cu:
            raise ValueError(
                f"nhip tien do lui: da_xong={da_xong} < lan truoc={cu} "
                f"(job {job.id})")
    return append(
        db, job, event_code, visibility=visibility,
        details={"da_xong": da_xong, "tong": tong, "don_vi": str(don_vi or "")[:40]},
    )


def timeline(db: DbSession, job_id: str, *, include_internal: bool = False,
             limit: int = 200) -> list[JobEvent]:
    stmt = select(JobEvent).where(JobEvent.job_id == job_id)
    if not include_internal:
        stmt = stmt.where(JobEvent.visibility == CUSTOMER)
    return list(db.execute(
        stmt.order_by(JobEvent.sequence).limit(max(1, min(int(limit), 500)))
    ).scalars().all())


def retention_report(db: DbSession, *, now: datetime | None = None,
                     customer_days: int = CUSTOMER_RETENTION_DAYS,
                     internal_days: int = INTERNAL_RETENTION_DAYS) -> dict:
    """Dry-run không chứa dữ liệu người dùng trước khi dọn retention.

    Job active quá tuổi không bao giờ bị xóa: nó là tín hiệu recovery cần xử
    lý. Ledger credit nằm ở bảng append-only riêng và không thuộc purge này.
    """
    current = now or datetime.now(timezone.utc)
    customer_days = max(1, int(customer_days))
    internal_days = max(1, int(internal_days))
    customer_cutoff = current - timedelta(days=customer_days)
    internal_cutoff = current - timedelta(days=internal_days)
    terminal = ("done", "error", "cancelled")
    active = ("queued", "running")

    def count(stmt) -> int:
        return int(db.execute(stmt).scalar_one() or 0)

    return {
        "policy": {
            "customer_days": customer_days,
            "internal_days": internal_days,
            "artifacts": "separate_policy",
            "credit_ledger": "never_purged_by_job_retention",
        },
        "customer_events_due": count(select(func.count(JobEvent.id)).where(
            JobEvent.visibility == CUSTOMER,
            JobEvent.created_at < customer_cutoff)),
        "internal_events_due": count(select(func.count(JobEvent.id)).where(
            JobEvent.visibility == INTERNAL,
            JobEvent.created_at < internal_cutoff)),
        "terminal_jobs_due": count(select(func.count(Job.id)).where(
            Job.status.in_(terminal), Job.created_at < customer_cutoff)),
        "active_jobs_older_than_policy": count(select(func.count(Job.id)).where(
            Job.status.in_(active), Job.created_at < customer_cutoff)),
        "generated_at": current,
    }


def purge_expired(db: DbSession, *, now: datetime | None = None,
                  customer_days: int = CUSTOMER_RETENTION_DAYS,
                  internal_days: int = INTERNAL_RETENTION_DAYS) -> dict[str, int]:
    """Xoá event hết hạn theo lớp dữ liệu; artifact có chính sách riêng."""
    current = now or datetime.now(timezone.utc)
    customer_cutoff = current - timedelta(days=max(1, customer_days))
    internal_cutoff = current - timedelta(days=max(1, internal_days))
    customer = db.execute(delete(JobEvent).where(
        JobEvent.visibility == CUSTOMER, JobEvent.created_at < customer_cutoff,
    )).rowcount or 0
    internal = db.execute(delete(JobEvent).where(
        JobEvent.visibility == INTERNAL, JobEvent.created_at < internal_cutoff,
    )).rowcount or 0
    db.flush()
    return {CUSTOMER: int(customer), INTERNAL: int(internal)}


def purge_expired_jobs(db: DbSession, *, now: datetime | None = None,
                       customer_days: int = CUSTOMER_RETENTION_DAYS,
                       batch_size: int = 1000) -> int:
    """Xóa một batch Job terminal quá hạn; không bao giờ chạm ledger/artifact.

    Hàm cố ý không được worker gọi tự động ở H26.11. Operator phải xem dry-run,
    có backup và gọi explicit trong release runbook. Event được xóa tường minh
    để hành vi giống nhau cả khi SQLite không bật foreign-key cascade.
    """
    current = now or datetime.now(timezone.utc)
    cutoff = current - timedelta(days=max(1, int(customer_days)))
    size = max(1, min(int(batch_size), 5000))
    ids = list(db.execute(select(Job.id).where(
        Job.status.in_(("done", "error", "cancelled")),
        Job.created_at < cutoff,
    ).order_by(Job.created_at).limit(size)).scalars().all())
    if not ids:
        return 0
    db.execute(delete(JobEvent).where(JobEvent.job_id.in_(ids)))
    removed = db.execute(delete(Job).where(Job.id.in_(ids))).rowcount or 0
    db.flush()
    return int(removed)
