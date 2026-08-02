"""
jobs.py — hàng đợi job tự quản trên PostgreSQL (H2, Q26).

Một bảng `jobs` là nguồn chân lý duy nhất. Không có kho thứ hai. Nhờ vậy:
- **atomic job + credit**: web gọi `submit()` trong cùng session/transaction với
  việc trừ credit (H3) — hoặc cả hai cùng thành, hoặc cả hai cùng rollback,
  không bao giờ có job không trừ tiền hay tiền trừ mà không có job;
- **nhiều worker không nhặt trùng**: `claim()` dùng
  `SELECT … FOR UPDATE SKIP LOCKED` — hai worker chạy song song, mỗi job chỉ
  một worker lấy được, Postgres lo phần khoá;
- **job không mồ côi**: worker đập nhịp (`heartbeat`) khi chạy; job `running`
  mà lâu không đập nhịp (worker chết) được `reclaim_orphans()` trả về hàng đợi.

Giao diện (`submit/claim/heartbeat/set_progress/complete/fail/reclaim_orphans`)
cố ý giữ hẹp: nếu sau này cần đổi sang một hàng đợi khác thì chỉ viết lại file
này, app và worker không đổi.

Tất cả hàm **không tự commit** trừ khi ghi rõ — nơi gọi (web request, vòng
worker) quyết định ranh giới transaction.
"""
from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from platform_core.models import (JOB_CANCELLED, JOB_DONE, JOB_ERROR, JOB_QUEUED, JOB_RUNNING,
                                  Job)

# Job running quá lâu không đập nhịp bị coi là mồ côi (worker chết).
ORPHAN_TIMEOUT = timedelta(minutes=5)

# Giãn cách retry: lần thử thứ n chờ base * 2^(n-1) giây, chặn trên.
_RETRY_BASE_S = 10
_RETRY_MAX_S = 600


class JobError(Exception):
    pass


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    # SQLite trả naive; Postgres trả aware. Chuẩn hoá tại điểm so sánh.
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


# ── Nộp job ───────────────────────────────────────────────────────────────────

def submit(db: DbSession, *, user_id: str, app_slug: str, job_type: str,
           params: dict, dedupe_key: str = "", max_attempts: int = 3,
           parent_id: str = "", plan_id: str = "", step_id: str = "") -> Job:
    """Tạo một job ở trạng thái `queued`. KHÔNG commit — caller commit cùng credit.

    Nếu `dedupe_key` khác rỗng và đã có một job **chưa kết thúc** (queued/running)
    cùng key của cùng người dùng, trả lại job cũ thay vì tạo mới. Đây là chốt
    chặn double-submit / F5 / bấm "Tạo lại": người dùng không tạo được hai job
    (và không bị trừ tiền hai lần) cho cùng một yêu cầu đang chạy.
    """
    if dedupe_key:
        cu = db.execute(
            select(Job).where(
                Job.user_id == user_id,
                Job.dedupe_key == dedupe_key,
                Job.status.in_((JOB_QUEUED, JOB_RUNNING)),
            )
        ).scalars().first()
        if cu is not None:
            return cu

    job = Job(
        user_id=user_id, app_slug=app_slug, job_type=job_type,
        params=params or {}, dedupe_key=dedupe_key,
        max_attempts=max_attempts, status=JOB_QUEUED,
        parent_id=parent_id, plan_id=plan_id, step_id=step_id,
    )
    db.add(job)
    db.flush()
    return job


# ── Worker nhặt job ───────────────────────────────────────────────────────────

def claim(db: DbSession, *, worker_id: str,
          capabilities: Optional[set[str]] = None) -> Optional[Job]:
    """Nhặt một job đến hạn chạy. Trả None nếu hàng đợi trống.

    `FOR UPDATE SKIP LOCKED`: nếu một worker khác đã khoá dòng này, ta bỏ qua
    nó thay vì chờ — nên nhiều worker chạy song song không giẫm chân nhau và
    không job nào bị nhặt hai lần.

    Khi truyền ``capabilities``, chỉ app có toàn bộ ``manifest.requires`` nằm
    trong tập năng lực worker mới được claim. ``None`` giữ tương thích worker
    đa năng hiện hữu.
    """
    now = _bay_gio()
    stmt = select(Job).where(Job.status == JOB_QUEUED, Job.next_run_at <= now)
    if capabilities is not None:
        from platform_core.registry import discover
        eligible = [item.slug for item in discover() if not item.error and
                    set(item.manifest.requires).issubset(capabilities)]
        if not eligible:
            return None
        stmt = stmt.where(Job.app_slug.in_(eligible))
    row = db.execute(
        stmt
        .order_by(Job.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).scalars().first()
    if row is None:
        return None

    row.status = JOB_RUNNING
    row.worker_id = worker_id
    row.started_at = row.started_at or now
    row.heartbeat_at = now
    db.flush()
    return row


def heartbeat(db: DbSession, job: Job) -> None:
    """Đập nhịp — báo cho hệ thống biết worker còn sống với job này."""
    job.heartbeat_at = _bay_gio()
    db.flush()


def set_progress(db: DbSession, job: Job, percent: int, message: str = "") -> None:
    job.progress = max(0, min(100, int(percent)))
    if message:
        job.progress_msg = message[:255]
    job.heartbeat_at = _bay_gio()
    db.flush()


def complete(db: DbSession, job: Job, result: dict) -> None:
    job.status = JOB_DONE
    job.result = result
    job.progress = 100
    job.finished_at = _bay_gio()
    db.flush()


def cancel(db: DbSession, job: Job) -> bool:
    """Hủy job queued/running. Caller hoàn credit trong cùng transaction.

    Worker kiểm tra trạng thái trước complete và trong mỗi progress tick, nên job
    đang chạy sẽ dừng hợp tác ở điểm an toàn kế tiếp; không có kill-process mù.
    """
    if job.status not in (JOB_QUEUED, JOB_RUNNING):
        return False
    job.status = JOB_CANCELLED
    job.progress_msg = "đã hủy"
    job.finished_at = _bay_gio()
    db.flush()
    return True


def fail(db: DbSession, job: Job, error: str) -> None:
    """Ghi nhận thất bại. Còn lượt thì hẹn chạy lại; hết lượt thì `error`.

    Giãn cách tăng dần để một lỗi tạm thời (mạng chập chờn) được thử lại thưa
    dần thay vì dồn dập.
    """
    job.attempts += 1
    job.error = (error or "")[:5000]
    if job.attempts < job.max_attempts:
        cho = min(_RETRY_MAX_S, _RETRY_BASE_S * (2 ** (job.attempts - 1)))
        job.status = JOB_QUEUED
        job.next_run_at = _bay_gio() + timedelta(seconds=cho)
        job.worker_id = ""
    else:
        job.status = JOB_ERROR
        job.finished_at = _bay_gio()
    db.flush()


def reclaim_orphans(db: DbSession, *, timeout: timedelta = ORPHAN_TIMEOUT) -> int:
    """Trả về hàng đợi các job `running` mà worker đã chết (lâu không đập nhịp).

    Tính một lần thử đã tiêu (attempts += 1): một job làm treo worker không
    được phép quay lại vô hạn lần và giết mọi worker nối tiếp. Hết lượt thì
    thành `error`. Trả về số job đã xử lý.
    """
    nguong = _bay_gio() - timeout
    # SKIP LOCKED: hai worker cùng reclaim không được nhặt trùng một orphan (nếu
    # không, cả hai fail() nó → attempts += 2, đếm sai lượt). Worker kia đang khoá
    # dòng nào thì bỏ qua. SQLite (test) bỏ qua mệnh đề này, vô hại.
    rows = db.execute(
        select(Job).where(Job.status == JOB_RUNNING).with_for_update(skip_locked=True)
    ).scalars().all()

    n = 0
    for job in rows:
        hb = _aware(job.heartbeat_at) or _aware(job.started_at)
        if hb is not None and hb > nguong:
            continue      # vẫn còn sống
        n += 1
        fail(db, job, "Worker mất kết nối giữa chừng (job mồ côi, nhặt lại).")
    db.flush()
    return n


# ── Tra handler của app ───────────────────────────────────────────────────────

def resolve_handler(job_type: str) -> Callable[..., dict]:
    """job_type → hàm `handle(params, ctx)` của app sở hữu nó.

    Đọc qua registry (`job_type_owners`) rồi import `apps.<slug>.jobs` — không
    hardcode slug, giữ đúng hợp đồng "nền tảng không biết trước app nào".
    """
    from platform_core.registry import job_type_owners
    slug = job_type_owners().get(job_type)
    if not slug:
        raise JobError(f"không app nào nhận job_type {job_type!r}")
    try:
        mod = importlib.import_module(f"apps.{slug}.jobs")
    except ModuleNotFoundError as exc:
        raise JobError(f"app {slug!r} không có jobs.py") from exc
    handler = getattr(mod, "handle", None)
    if handler is None:
        raise JobError(f"apps.{slug}.jobs không có hàm handle()")
    return handler
