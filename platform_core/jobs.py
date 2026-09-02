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

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session as DbSession, aliased

from platform_core.models import (JOB_CANCELLED, JOB_DONE, JOB_ERROR, JOB_QUEUED, JOB_RUNNING,
                                  Job)
from platform_core import job_events
from platform_core.i18n import N_

# Job running quá lâu không đập nhịp bị coi là mồ côi (worker chết).
ORPHAN_TIMEOUT = timedelta(minutes=5)

# Giãn cách retry: lần thử thứ n chờ base * 2^(n-1) giây, chặn trên.
_RETRY_BASE_S = 10
_RETRY_MAX_S = 600

# Job/account đã chờ tới mốc này được đưa lên trước account mới để không đói.
FAIR_AGING = timedelta(minutes=5)
PROVIDER_DISPATCHED = "dispatched"
PROVIDER_REJECTED = "rejected"
PROVIDER_AMBIGUOUS = "ambiguous"
PROVIDER_COMPLETED = "completed"


class JobError(Exception):
    pass


class LoiNguoiGoi(Exception):
    """Lỗi nằm ở **yêu cầu của người gọi**, không ở hệ thống. ⛔ KHÔNG thử lại.

    ## Khoảng trống hợp đồng mà lớp này lấp

    Trước 31/08/2026, khả năng thử-lại của một job được quyết định **hoàn toàn**
    bởi `job_runner._provider_failure_kind` — một danh sách gõ tay các kiểu ngoại
    lệ của provider LLM. Mọi ngoại lệ khác rơi vào nhánh mặc định `"retry"`.

    Hệ quả: một handler ném "không tìm thấy giọng này trong tài khoản của bạn"
    được **thử lại ba lần**. Ba suất GPU, ba lượt xếp hàng, ba lần chờ — cho một
    việc không bao giờ thành công, vì nguyên nhân là dữ liệu người dùng gửi lên
    chứ không phải một trục trặc thoáng qua.

    ⭐ Đo thật ngày 31/08/2026: job `a49ce0d3` (một tài khoản mượn `voice_id` của
       tài khoản khác) chạy `attempts = 3` rồi mới `error`. Tiền được hoàn đúng,
       nhưng khách phải chờ 31 giây để nghe một câu trả lời mà cửa vào đã biết
       ngay từ đầu.

    ⛔ Đừng dùng nó cho lỗi hạ tầng. "Máy bận", "mạng chập chờn", "cổng chưa nạp
       xong model" đều PHẢI được thử lại — đánh dấu chúng là lỗi người gọi biến
       một trục trặc thoáng qua thành một thất bại vĩnh viễn trong mắt khách.

    Cách dùng trong app::

        from platform_core.jobs import LoiNguoiGoi

        class LoiGiongNoi(LoiNguoiGoi):
            \"\"\"Thông điệp đưa thẳng cho khách — phải nói được cách sửa.\"\"\"
    """


class DangBan(Exception):
    """Tài nguyên thi hành đang **bận**. ⛔ KHÔNG PHẢI HỎNG, KHÔNG PHẢI LỖI KHÁCH.

    Đối xứng với `LoiNguoiGoi` ở trên: `LoiNguoiGoi` là "đừng thử lại nữa", còn
    lớp này là "thử lại, nhưng **đừng tính** lần này". Worker đưa job về hàng đợi
    bằng `defer_resource` — không tiêu lượt thử, không chạm sổ tiền, và job
    quay lại sau `retry_after_s` giây (rỗng ⇒ giãn cách mặc định của nền tảng).

    ## Khoảng trống hợp đồng mà lớp này lấp (H43 Phase 04/05, 03/09/2026)

    `job_runner._provider_failure_kind` chỉ nhận ra "bận" qua lớp `BanError`
    của cổng VLM. Một app bán model khác (cổng render ảnh, cổng giọng) cũng
    gặp 429 cùng nghĩa, nhưng **không có cách nào nói điều đó** với worker mà
    không import mô-đun của cổng VLM — thứ chẳng liên quan gì tới nó. Hệ quả
    đo được ở Phase 02: "máy bận" của hai app đó rơi vào nhánh `retry`, tiêu
    một trong ba lượt thử, và sau ba lượt bận thì job **hỏng hẳn** kèm hoàn
    tiền — cho một việc chưa từng chạy.

    ⭐ Đây là tín hiệu **nền tảng** để app nào cũng ném được mà không cần biết
       app hay cổng nào khác tồn tại. Cổng nào có lớp "bận" riêng thì dịch sang
       lớp này ở cửa job của app (giữ nguyên thông điệp), hoặc cho lớp đó kế
       thừa lớp này.

    ⛔ Đừng dùng cho lỗi hạ tầng thật (mạng đứt, cổng trả 5xx). "Bận" là trạng
       thái có hạn; "hỏng" thì phải **đếm** lượt thử để còn báo cho khách. Xếp
       lại vô hạn một cổng đã chết là job nằm `queued` mãi mà không ai được báo.

    Cách dùng trong app::

        from platform_core.jobs import DangBan

        except cong.BanError as e:
            raise DangBan(str(e), retry_after_s=e.eta_s) from e
    """

    def __init__(self, ly_do: str = "", retry_after_s: Optional[float] = None):
        super().__init__(ly_do or "tai nguyen dang ban")
        self.ly_do = ly_do
        self.retry_after_s = retry_after_s


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
           parent_id: str = "", plan_id: str = "", step_id: str = "",
           correlation_id: str = "", retry_of_id: str = "",
           admission_resource: str = "", admission_slots: int = 0) -> Job:
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
        retry_of_id=retry_of_id,
        admission_resource=str(admission_resource or "")[:96],
        admission_slots=max(0, int(admission_slots or 0)),
    )
    if correlation_id:
        job.correlation_id = correlation_id[:36]
    db.add(job)
    db.flush()
    job_events.append(
        db, job, "submitted", public_message=N_("Đã tiếp nhận yêu cầu."),
        details={"status": JOB_QUEUED}, event_key="submitted",
    )
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
    peer = aliased(Job)
    last_account_claim = (
        select(func.max(peer.last_claimed_at))
        .where(peer.user_id == Job.user_id,
               peer.admission_resource == Job.admission_resource)
        .correlate(Job)
        .scalar_subquery()
    )
    aged_first = case((Job.created_at <= now - FAIR_AGING, 0), else_=1)
    never_served_first = case((last_account_claim.is_(None), 0), else_=1)
    row = db.execute(
        stmt
        # Aging trước, rồi fair-share theo account, cuối cùng FIFO ổn định trong
        # account. Không có giá tiền trong phép xếp thứ tự này.
        .order_by(aged_first, never_served_first, last_account_claim,
                  Job.created_at, Job.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).scalars().first()
    if row is None:
        return None

    row.status = JOB_RUNNING
    row.worker_id = worker_id
    row.started_at = row.started_at or now
    row.heartbeat_at = now
    row.last_claimed_at = now
    attempt = int(row.attempts or 0) + 1
    job_events.append(
        db, row, "claimed", visibility=job_events.INTERNAL,
        details={"worker_id": worker_id, "attempt": attempt},
        event_key=f"claimed:{attempt}",
    )
    job_events.append(
        db, row, "started", public_message=N_("Bắt đầu xử lý."),
        details={"attempt": attempt, "max_attempts": row.max_attempts,
                 "status": JOB_RUNNING}, event_key=f"started:{attempt}",
    )
    db.flush()
    return row


def heartbeat(db: DbSession, job: Job) -> None:
    """Đập nhịp — báo cho hệ thống biết worker còn sống với job này."""
    job.heartbeat_at = _bay_gio()
    db.flush()


def mark_admitted(db: DbSession, job: Job, *, at: datetime | None = None) -> None:
    """Ghi mốc đầu tiên job có đủ tài nguyên để chạy, bền qua restart."""
    if job.status != JOB_RUNNING or job.admitted_at is not None:
        return
    admitted = at or _bay_gio()
    job.admitted_at = admitted
    delay_ms = max(0, int((_aware(admitted) - _aware(job.created_at)).total_seconds()
                          * 1000))
    attempt = int(job.attempts or 0) + 1
    job_events.append(
        db, job, "admitted", visibility=job_events.INTERNAL,
        details={"attempt": attempt, "resource": job.admission_resource,
                 "admission_delay_ms": delay_ms},
        event_key="admitted")
    from platform_core.public_api import metrics
    metrics.observe(metrics.LATENCY_ADMISSION, delay_ms)
    db.flush()


def mark_provider_dispatched(db: DbSession, job: Job, provider: str = "") -> None:
    """Ghi bền ngay trước outbound HTTP; crash sau mốc này không retry mù."""
    if job.status != JOB_RUNNING:
        return
    job.provider_state = PROVIDER_DISPATCHED
    job.provider_dispatched_at = _bay_gio()
    attempt = int(job.attempts or 0) + 1
    job_events.append(
        db, job, "provider_dispatched", visibility=job_events.INTERNAL,
        details={"attempt": attempt, "provider": str(provider)[:64]},
        event_key=f"provider-dispatched:{attempt}")
    db.flush()


def mark_provider_rejected(db: DbSession, job: Job, provider: str = "") -> None:
    """Đã nhận phản hồi xác định; lần dispatch này không còn ambiguous."""
    if job.status != JOB_RUNNING:
        return
    job.provider_state = PROVIDER_REJECTED
    attempt = int(job.attempts or 0) + 1
    job_events.append(
        db, job, "provider_rejected", visibility=job_events.INTERNAL,
        details={"attempt": attempt, "provider": str(provider)[:64]},
        event_key=f"provider-rejected:{attempt}:{str(provider)[:32]}")
    db.flush()


def defer_resource(db: DbSession, job: Job, *, retry_after: float = 20,
                   resource: str = "") -> None:
    """Từ chối xác định trước provider: về queue, không tiêu attempt."""
    delay = max(1, min(_RETRY_MAX_S, int(retry_after or 20)))
    job.status = JOB_QUEUED
    job.worker_id = ""
    job.provider_state = PROVIDER_REJECTED
    job.next_run_at = _bay_gio() + timedelta(seconds=delay)
    job_events.append(
        db, job, "resource_wait", public_message=N_("Đang chờ tài nguyên xử lý."),
        details={"delay_seconds": delay, "status": JOB_QUEUED,
                 "resource": str(resource)}, level="warning")
    db.flush()


def mark_ambiguous(db: DbSession, job: Job, error: str) -> None:
    """Provider có thể đã nhận: terminal có lý do, tuyệt đối không auto-retry."""
    job.attempts += 1
    job.status = JOB_ERROR
    job.provider_state = PROVIDER_AMBIGUOUS
    job.worker_id = ""
    job.finished_at = _bay_gio()
    job.error = job_events.sanitize_text(error, limit=5000)
    job_events.append(
        db, job, "ambiguous_provider",
        public_message=N_(
            "Không thể xác định kết quả từ nhà cung cấp; hệ thống đã dừng tự thử lại."),
        details={"attempt": job.attempts, "status": JOB_ERROR},
        level="error", event_key="ambiguous-provider")
    db.flush()


def set_progress(db: DbSession, job: Job, percent: int, message: str = "") -> None:
    job.progress = max(0, min(100, int(percent)))
    if message:
        job.progress_msg = message[:255]
    job.heartbeat_at = _bay_gio()
    job_events.append(
        db, job, "progress", public_message=message or N_("Đang xử lý."),
        details={"percent": job.progress, "status": job.status},
        event_key=f"progress:{job.progress}:{(message or '')[:40]}",
    )
    db.flush()


def complete(db: DbSession, job: Job, result: dict) -> None:
    job.status = JOB_DONE
    job.result = result
    job.progress = 100
    job.finished_at = _bay_gio()
    if job.provider_state == PROVIDER_DISPATCHED:
        job.provider_state = PROVIDER_COMPLETED
    job_events.append(
        db, job, "completed", public_message=N_("Đã hoàn tất."),
        details={"status": JOB_DONE}, event_key="completed",
    )
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
    job_events.append(
        db, job, "cancelled", public_message=N_("Đã hủy theo yêu cầu."),
        details={"status": JOB_CANCELLED}, level="warning", event_key="cancelled",
    )
    db.flush()
    return True


def fail(db: DbSession, job: Job, error: str, *, retry: bool = True) -> None:
    """Ghi nhận thất bại. Còn lượt thì hẹn chạy lại; hết lượt thì `error`.

    Giãn cách tăng dần để một lỗi tạm thời (mạng chập chờn) được thử lại thưa
    dần thay vì dồn dập.

    `retry=False` cho những thất bại mà thử lại chắc chắn hỏng y hệt — job vượt
    trần thời gian là ví dụ: nó treo vì chính công việc đó, nên chạy lại chỉ
    tiêu thêm một slot rồi treo tiếp, ba lần.
    """
    job.attempts += 1
    safe_error = job_events.sanitize_text(error, limit=5000)
    job.error = safe_error
    if retry and job.attempts < job.max_attempts:
        cho = min(_RETRY_MAX_S, _RETRY_BASE_S * (2 ** (job.attempts - 1)))
        job.status = JOB_QUEUED
        job.next_run_at = _bay_gio() + timedelta(seconds=cho)
        job.worker_id = ""
        job_events.append(
            db, job, "retry_scheduled",
            public_message=N_("Gặp gián đoạn tạm thời, hệ thống sẽ tự thử lại."),
            details={"attempt": job.attempts, "max_attempts": job.max_attempts,
                     "delay_seconds": cho, "status": JOB_QUEUED},
            level="warning", event_key=f"retry:{job.attempts}",
        )
    else:
        job.status = JOB_ERROR
        job.finished_at = _bay_gio()
        job_events.append(
            db, job, "failed",
            public_message=N_("Không thể hoàn tất yêu cầu. Bạn có thể thử lại."),
            details={"attempt": job.attempts, "max_attempts": job.max_attempts,
                     "status": JOB_ERROR}, level="error", event_key="failed",
        )
    job_events.append(
        db, job, "attempt_error", visibility=job_events.INTERNAL, level="error",
        details={"attempt": job.attempts, "error": safe_error},
        event_key=f"attempt-error:{job.attempts}",
    )
    db.flush()


def reclaim_orphans(db: DbSession, *, timeout: timedelta = ORPHAN_TIMEOUT,
                    on_terminal=None) -> int:
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
        job_events.append(
            db, job, "orphan_reclaimed", visibility=job_events.INTERNAL,
            level="warning", details={"worker_id": job.worker_id},
            event_key=f"orphan:{int(job.attempts or 0) + 1}",
        )
        if job.provider_state == PROVIDER_DISPATCHED:
            mark_ambiguous(
                db, job,
                N_("Worker mất kết nối sau khi đã gửi yêu cầu tới nhà cung cấp."))
        else:
            fail(db, job, "Worker mất kết nối giữa chừng (job mồ côi, nhặt lại).")
        if job.status == JOB_ERROR and on_terminal is not None:
            on_terminal(db, job)
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
