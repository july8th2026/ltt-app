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
import re
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from sqlalchemy import exists, func, literal, or_, select
from sqlalchemy.orm import Session as DbSession

from platform_core.models import (ExecutionLease, JOB_CANCELLED, JOB_DONE, JOB_ERROR,
                                  JOB_QUEUED, JOB_RUNNING, Job)
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


#: Câu chung cho khách khi job hỏng vì lý do KHÔNG phải của họ — cùng câu với sự kiện `failed` (`fail()`).
LOI_CHUNG_KHACH = N_("Không thể hoàn tất yêu cầu. Bạn có thể thử lại.")
#: Dấu ngăn "chi tiết cho vận hành" với "câu cho khách" trong `Job.error` của một lỗi KHÔNG phải `LoiNguoiGoi`.
DAU_CAU_KHACH = "|| khach: "
_LOI_KHACH = re.compile(r"LoiNguoiGoi(?:\(\w+\))?: (.*)\Z", re.S)


def mo_ta_loi(exc: BaseException) -> str:
    """Chuỗi `Job.error` của một ngoại lệ — MỘT nguồn cho `job_runner`.

    `TenLop: thông điệp` cho vận hành. `LoiNguoiGoi` (câu app viết CHO KHÁCH) mang dấu riêng
    `LoiNguoiGoi(<lớp con>): …` — tên lớp con vẫn còn cho vận hành, còn `loi_cho_khach` nhận ra được
    mà không cần import module app (lúc hiển thị, `isinstance` không còn: ngoại lệ đã thành chuỗi).
    """
    if isinstance(exc, LoiNguoiGoi):
        nhan = "LoiNguoiGoi" if type(exc) is LoiNguoiGoi else f"LoiNguoiGoi({type(exc).__name__})"
        return f"{nhan}: {exc}"
    cau = getattr(exc, "cau_khach", None)
    if isinstance(cau, str) and cau.strip():
        # Lỗi TẠM THỜI (phải thử lại ⇒ không thể là `LoiNguoiGoi`) vẫn nói được câu đã soạn cho khách khi
        # hết lượt thử. Chi tiết kỹ thuật giữ nguyên cho vận hành, câu khách nằm ở cuối sau dấu.
        return f"{type(exc).__name__}: {exc} {DAU_CAU_KHACH}{cau}"
    return f"{type(exc).__name__}: {exc}"


def loi_cho_khach(job) -> str:
    """Câu lỗi được phép hiện cho KHÁCH (đã dịch), `""` nếu job không lỗi.

    Chỉ câu của `LoiNguoiGoi` đi qua nguyên văn; mọi lỗi khác (hạ tầng, provider, bug, hết giờ, định dạng
    cũ trước dấu `LoiNguoiGoi`) ⇒ `LOI_CHUNG_KHACH` — không bao giờ văn bản thô, như `/api/v1` (Q76).
    """
    from platform_core.i18n import _

    if job is None or getattr(job, "status", None) != JOB_ERROR:
        return ""
    loi = getattr(job, "error", None) or ""
    m = _LOI_KHACH.match(loi)
    if m and m.group(1).strip():
        return _(m.group(1))
    if DAU_CAU_KHACH in loi:
        cau = loi.split(DAU_CAU_KHACH, 1)[1].strip()
        if cau:
            return _(cau)
    return _(LOI_CHUNG_KHACH)


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
           admission_resource: str = "", admission_slots: int = 0,
           origin: str | None = None,
           priority_class: str | None = None) -> Job:
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

    from platform_core import job_ingress, job_scheduler

    context_origin, context_priority = job_ingress.current()

    job = Job(
        user_id=user_id, app_slug=app_slug, job_type=job_type,
        params=params or {}, dedupe_key=dedupe_key,
        max_attempts=max_attempts, status=JOB_QUEUED,
        parent_id=parent_id, plan_id=plan_id, step_id=step_id,
        retry_of_id=retry_of_id,
        admission_resource=str(admission_resource or "")[:96],
        admission_slots=max(0, int(admission_slots or 0)),
        origin=job_scheduler.normalize_origin(
            context_origin if origin is None else origin),
        priority_class=job_scheduler.normalize_priority(
            context_priority if priority_class is None else priority_class),
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

def _con_cho_tai_nguyen(now: datetime):
    """Điều kiện SQL: job này còn chỗ ở tài nguyên dùng chung của nó.

    🔴 VÌ SAO NÓ TỒN TẠI — đo từ log worker production 28 ngày (11/08→07/09/2026):

        9.833 / 10.663 = 92,2 %  lượt nhặt `ltt_llm.chat` kết thúc bằng
                                 "hoãn Ns: tài nguyên llm_remote đang bận"
        11.929 lượt nhặt  →  868 job xong  =  13,7 lượt nhặt cho MỖI job hoàn tất

    Trước đây `claim()` nhặt job **trước**, rồi worker mới giành `ExecutionLease`
    **sau**; hụt thì `defer_resource` xếp lại. Với `llm_remote` chỉ có MỘT suất,
    mọi job chat loại trừ nhau — nên 92 % kia là trạng thái **bình thường**, không
    phải sự cố. Mỗi lượt nhặt-rồi-nhả vẫn tốn một vòng truy vấn, một lượt ghi
    `job_events`, và một khoảng chờ mà khách nhìn thấy.

    ⭐ Cách sửa là **hỏi trước, nhặt sau**. Đếm lease còn sống của tài nguyên rồi
    loại job của những tài nguyên đã đầy ra khỏi câu truy vấn — bộ nhặt không bao
    giờ nhìn thấy chúng.

    ⛔ Đừng "sửa" bằng cách nới `ORPHAN_TIMEOUT` hay giảm giãn cách thử lại: cả
       hai làm vòng quay **dày hơn**, không làm nó ngắn đi.

    ⚠️ Đây là **bộ lọc cơ hội, không phải khoá**. Hai worker vẫn có thể cùng thấy
       một suất trống rồi cùng nhặt hai job khác nhau của cùng tài nguyên. Lớp
       giành thật vẫn là `ExecutionLease` với `UNIQUE(resource, slot)`, và
       `job_runner` vẫn `defer_resource` khi hụt. Bộ lọc này chỉ làm chuyện đó
       thành **hiếm** thay vì **thường trực**.
    """
    from platform_core.llm.admission import ORPHAN_TIMEOUT

    # Lease quá hạn đập nhịp là lease của worker đã chết — `admission.acquire`
    # thu hồi chúng, nên ở đây cũng không được tính là đang chiếm suất.
    con_song = now - ORPHAN_TIMEOUT
    dang_giu = (
        select(func.count(ExecutionLease.id))
        .where(ExecutionLease.resource == Job.admission_resource,
               ExecutionLease.heartbeat_at >= con_song)
        .correlate(Job)
        .scalar_subquery()
    )
    return or_(
        Job.admission_resource == "",      # job không dùng tài nguyên chia sẻ
        Job.admission_slots <= 0,          # app chưa khai sức chứa ⇒ giữ hành vi cũ
        dang_giu < Job.admission_slots,
    )


def _app_hop_nang_luc(capabilities: Optional[set[str]]) -> Optional[list[str]]:
    """Slug các app mà worker với năng lực này phục vụ được.

    ``None`` nghĩa là worker đa năng — không lọc gì cả. Danh sách **rỗng** là
    một câu trả lời khác hẳn: worker này không phục vụ được app nào.
    """
    if capabilities is None:
        return None
    from platform_core.registry import discover
    return [item.slug for item in discover() if not item.error and
            set(item.manifest.requires).issubset(capabilities)]


def co_job_dang_cho_tai_nguyen(
        db: DbSession, capabilities: Optional[set[str]] = None) -> bool:
    """Có job đến hạn nhưng đang bị chặn **chỉ vì** tài nguyên hết suất không?

    🔴 VÌ SAO CẦN HÀM NÀY. Từ khi `claim()` lọc theo suất, `None` mang hai
    nghĩa (xem docstring của nó). Mọi bên gọi ngoài vòng worker đều viết

        job = jobs.claim(db, worker_id=...)
        if job is None:
            break            # ← DỪNG ở một trạng thái chỉ là tạm

    ⛔ Bản vá hiển nhiên — "thấy `None` thì ngủ rồi thử lại" — **sai**, vì nó
       phạt cả những lượt hàng đợi rỗng thật bằng đúng số giây ấy. Cái cần sửa
       không phải phản ứng, mà là **câu hỏi**: bên gọi phải hỏi được theo Ý
       NGHĨA thay vì đoán từ HÌNH DẠNG của giá trị trả về.

    Trả ``True`` khi tồn tại ít nhất một job `queued` đã đến hạn, thuộc app
    worker này phục vụ được, có khai tài nguyên chia sẻ, và tài nguyên đó hiện
    **không còn suất**. Trả ``False`` cho mọi trạng thái khác — kể cả hàng đợi
    rỗng, và kể cả khi có job nhưng nó nhặt được ngay.

    ⚠️ Đây là một **ảnh chụp**, không phải lời hứa: suất có thể được nhả ngay
       sau khi hàm trả về. Nó trả lời *"lúc này có đáng chờ không"*, không trả
       lời *"chờ bao lâu"*. Chỉ đọc — không khoá dòng nào.
    """
    now = _bay_gio()
    stmt = select(func.count(Job.id)).where(
        Job.status == JOB_QUEUED,
        Job.next_run_at <= now,
        Job.admission_resource != "",
        Job.admission_slots > 0,
        ~_con_cho_tai_nguyen(now),
    )
    eligible = _app_hop_nang_luc(capabilities)
    if eligible is not None:
        if not eligible:
            return False
        stmt = stmt.where(Job.app_slug.in_(eligible))
    return bool(db.execute(stmt).scalar_one())


def claim(db: DbSession, *, worker_id: str,
          capabilities: Optional[set[str]] = None) -> Optional[Job]:
    """Nhặt một job đến hạn chạy, hoặc ``None`` nếu lượt này không nhặt được gì.

    ⚠️ ``None`` KHÔNG còn nghĩa là "hàng đợi trống". Nó có **hai** nguyên nhân:

        1. không có job nào đến hạn cho worker này — hết việc thật;
        2. có job đến hạn, nhưng tài nguyên dùng chung của nó đã hết suất
           (`_con_cho_tai_nguyen`) — việc vẫn còn đó, chỉ là chưa tới lượt.

    Hai nguyên nhân đó cần hai phản ứng khác nhau, và **giá trị trả về không
    phân biệt được chúng**. Vòng worker thật ngủ rồi thử lại nên nó đúng ở cả
    hai; bên gọi nào cần biết mình đang ở trạng thái nào thì hỏi
    `co_job_dang_cho_tai_nguyen()` — đừng suy từ `None`.

    `FOR UPDATE SKIP LOCKED`: nếu một worker khác đã khoá dòng này, ta bỏ qua
    nó thay vì chờ — nên nhiều worker chạy song song không giẫm chân nhau và
    không job nào bị nhặt hai lần.

    Khi truyền ``capabilities``, chỉ app có toàn bộ ``manifest.requires`` nằm
    trong tập năng lực worker mới được claim. ``None`` giữ tương thích worker
    đa năng hiện hữu.
    """
    now = _bay_gio()
    stmt = select(Job).where(Job.status == JOB_QUEUED, Job.next_run_at <= now)
    eligible = _app_hop_nang_luc(capabilities)
    if eligible is not None:
        if not eligible:
            return None
        stmt = stmt.where(Job.app_slug.in_(eligible))
    stmt = stmt.where(_con_cho_tai_nguyen(now))
    from platform_core import job_scheduler

    row = db.execute(
        stmt
        .order_by(*job_scheduler.order_expressions(Job, now=now))
        .limit(1)
        .with_for_update(skip_locked=True)
    ).scalars().first()
    if row is None:
        return None

    # One bounded observability query records when the scheduler materially
    # changed FIFO. It does not participate in arbitration; the locked row and
    # ExecutionLease remain the only authorities.
    from platform_core.job_scheduler import normalize_priority

    selected_priority = normalize_priority(row.priority_class)
    observable = [
        Job.status == JOB_QUEUED,
        Job.next_run_at <= now,
        Job.admission_resource == row.admission_resource,
        Job.id != row.id,
    ]
    if eligible is not None:
        observable.append(Job.app_slug.in_(eligible))
    priority_override, fair_rotation = db.execute(select(
        exists(select(Job.id).where(
            *observable,
            Job.priority_class != "internal",
        )) if selected_priority == "internal" else literal(False),
        exists(select(Job.id).where(
            *observable,
            Job.priority_class == row.priority_class,
            Job.user_id != row.user_id,
            Job.created_at < row.created_at,
        )),
    )).one()

    row.status = JOB_RUNNING
    row.worker_id = worker_id
    row.started_at = row.started_at or now
    row.heartbeat_at = now
    row.last_claimed_at = now
    attempt = int(row.attempts or 0) + 1
    job_events.append(
        db, row, "claimed", visibility=job_events.INTERNAL,
        details={"worker_id": worker_id, "attempt": attempt,
                 "origin": row.origin, "priority_class": selected_priority},
        event_key=f"claimed:{attempt}",
    )
    if priority_override:
        job_events.append(
            db, row, "scheduler_priority_override",
            visibility=job_events.INTERNAL,
            details={"resource": row.admission_resource,
                     "priority_class": selected_priority},
            event_key=f"scheduler-priority:{attempt}",
        )
    if fair_rotation:
        job_events.append(
            db, row, "scheduler_fair_rotation",
            visibility=job_events.INTERNAL,
            details={"resource": row.admission_resource,
                     "priority_class": selected_priority},
            event_key=f"scheduler-fair:{attempt}",
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
            public_message=LOI_CHUNG_KHACH,
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
