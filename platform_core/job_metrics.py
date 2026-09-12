"""Snapshot observability cho hàng đợi job, không phụ thuộc tên app."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from platform_core import job_events
from platform_core.models import (JOB_CANCELLED, JOB_DONE, JOB_ERROR, JOB_QUEUED,
                                  JOB_RUNNING, CreditEntry, ExecutionLease,
                                  GpuResidency, Job, JobEvent, LlmWaiter)

EXTERNAL_STARVATION_S = 300.0

#: Ô cho lượt chờ **không khai** id model nội bộ (`llm_waiters.model` rỗng).
#:
#: ⛔ VÌ SAO MỘT Ô RIÊNG, KHÔNG GỘP VÀO MODEL MẶC ĐỊNH. Gộp là **bịa**: một cửa
#:    chưa khai model có thể đang phục vụ model nào cũng được, và một con số bịa
#:    ở đây đi thẳng vào câu "model nào đang nghẽn". Ô riêng làm sự thiếu ấy
#:    **nhìn thấy được** trên dashboard, tức nó tự đòi được sửa.
KHONG_KHAI = "khong_khai"


def _seconds(start, end) -> float | None:
    if start is None or end is None:
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return max(0.0, (end - start).total_seconds())


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percentile)))
    return round(ordered[index], 3)


def _dau_ngay(current: datetime) -> datetime:
    """Nửa đêm UTC của ngày chứa `current`.

    ⚠️ UTC, KHÔNG giờ máy. Cột `created_at`/`admitted_at` lưu UTC, và "hôm nay"
       theo hai múi giờ khác nhau là hai câu trả lời khác nhau cho cùng một câu
       hỏi. Máy ở UTC+7 nên "hôm nay" ở đây lệch 7 giờ so với lịch trên tường —
       ghi ra ở khoá `moc_hom_nay` để người đọc biết mình đang đọc cửa sổ nào,
       chứ không phải đoán.
    """
    return current.astimezone(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0)


def llm_theo_model(db: DbSession, *, now: datetime, cutoff: datetime) -> dict:
    """Phòng chờ LLM **theo model × lớp** — độ sâu, tuổi lâu nhất, giây chờ cư trú.

    🔑 KHOÁ LÀ `llm_waiters.model`, KHÔNG PHẢI `resource`. Hôm nay hai tài nguyên
       ứng đúng hai model, nên khoá theo `resource` *cho cùng con số* — và đó là
       lý do phải nói ra tại sao không làm thế: `platform_core` không được biết
       tên app (`test_147`), nên dịch `resource` → model buộc nền tảng nhập một
       bảng ánh xạ từ `apps/`. Bảng ánh xạ ấy chính là hình dạng đã nói sai năm
       lần trong kho này. App khai một lần lúc vào hàng thì không ai phải dịch.

    ⛔ HAI MODEL KHÔNG BAO GIỜ ĐƯỢC CỘNG VÀO MỘT Ô. Chúng nằm trên **hai card**
       (3090 và 5060 Ti); một hàng dài trước 5060 Ti không nói gì về 3090, và
       gộp lại là biến hai hàng đợi thành một cách âm thầm — đúng lý do
       `ngan_sach.TAI_NGUYEN_38/35` phải là hai tên khác nhau.

    ⭐ `sau_*` chỉ đếm người chờ **còn sống** (nhịp tim trong `HAN_NHIP_CHO_S`,
       đọc từ `phong_cho`, không gõ lại): một dòng `cho` mất nhịp là một tiến
       trình đã chết mà vòng dọn chưa chốt, và để nó trong độ sâu là để một xác
       chết giữ hàng — đúng phép lọc `phong_cho.chup_nguoi_cho` đang dùng để
       **quyết định**. Số dòng mất nhịp ra ô `mat_nhip_theo_model` riêng, vì nó
       là một triệu chứng khác (tiến trình web chết), không phải tải.
    """
    from platform_core.llm.phong_cho import HAN_NHIP_CHO_S

    cho = list(db.execute(select(LlmWaiter).where(
        LlmWaiter.trang_thai == "cho")).scalars().all())
    sau: dict[str, dict[str, int]] = {}
    tuoi: dict[str, float] = {}
    mat_nhip: dict[str, int] = {}
    for w in cho:
        model = (w.model or "").strip() or KHONG_KHAI
        song = (_seconds(w.heartbeat_at, now) or 0.0) <= HAN_NHIP_CHO_S
        if not song:
            mat_nhip[model] = mat_nhip.get(model, 0) + 1
            continue
        lop = (w.lop or "").strip() or "khong_khai_lop"
        theo_lop = sau.setdefault(model, {})
        theo_lop[lop] = theo_lop.get(lop, 0) + 1
        tuoi[model] = max(tuoi.get(model, 0.0),
                          _seconds(w.created_at, now) or 0.0)

    # Giây chờ vì **cư trú GPU** trong cửa sổ báo cáo (cột `cho_residency_s`, rev
    # `d91f6c37ab24`). Đây là cái giá thật của việc đổi cư trú 3090, và nó phải
    # đứng RỜI khỏi tổng thời gian chờ: chờ vì cửa sổ ảnh và chờ vì hết slot dẫn
    # tới hai việc sửa khác nhau (xem docstring cột ở `models.LlmWaiter`).
    cu_tru: dict[str, dict[str, float]] = {}
    for w in db.execute(select(LlmWaiter).where(
            LlmWaiter.created_at >= cutoff,
            LlmWaiter.cho_residency_s > 0)).scalars().all():
        model = (w.model or "").strip() or KHONG_KHAI
        giay = float(w.cho_residency_s or 0.0)
        o = cu_tru.setdefault(model, {"so_luot": 0.0, "tong_s": 0.0, "lau_nhat_s": 0.0})
        o["so_luot"] += 1
        o["tong_s"] += giay
        o["lau_nhat_s"] = max(o["lau_nhat_s"], giay)

    return {
        "nhip_song_s": float(HAN_NHIP_CHO_S),
        "sau_theo_model_lop": {m: dict(sorted(v.items()))
                               for m, v in sorted(sau.items())},
        "sau_theo_model": {m: sum(v.values()) for m, v in sorted(sau.items())},
        "tuoi_lau_nhat_s_theo_model": {m: round(v, 3)
                                       for m, v in sorted(tuoi.items())},
        "mat_nhip_theo_model": dict(sorted(mat_nhip.items())),
        "cho_residency_theo_model": {
            m: {"so_luot": int(v["so_luot"]),
                "tong_s": round(v["tong_s"], 3),
                "lau_nhat_s": round(v["lau_nhat_s"], 3)}
            for m, v in sorted(cu_tru.items())},
    }


def tai_nguyen_theo_lo_cua(db: DbSession, nhom: str) -> list[str]:
    """Tài nguyên vai trò `theo_lo` của một nhóm cư trú, đọc từ **bản khai app**.

    ⭐ CHỈ DÙNG API CÔNG KHAI `admission.nhom_cu_tru(resource)`, và tra theo các
       tên tài nguyên **thật sự có trong bảng `jobs`**. Nền tảng vì thế không
       phải biết tên app nào, tài nguyên nào (`test_147`), và không phải nhập
       một bảng ánh xạ thứ hai: bản khai của app vẫn là nguồn duy nhất.

    ⛔ Một bản khai tự mâu thuẫn (`nhom_cu_tru` NÉM) chỉ làm hỏng tài nguyên ấy,
       không làm hỏng cả khối quan sát: quan sát là thứ người ta đọc **khi** hệ
       đang hỏng, nên nó phải sống sót qua một bản khai hỏng.
    """
    from platform_core.llm import admission, residency

    ra: list[str] = []
    for ten in db.execute(select(Job.admission_resource).where(
            Job.admission_resource.is_not(None),
            Job.admission_resource != "").distinct()).scalars().all():
        try:
            g, vai = admission.nhom_cu_tru(str(ten))
        except ValueError:
            continue
        if g == nhom and vai == residency.THEO_LO:
            ra.append(str(ten))
    return sorted(ra)


def residency_3090(db: DbSession, *, now: datetime,
                   tai_nguyen_theo_lo: tuple[str, ...] | list[str] | None = None) -> dict:
    """Cư trú GPU: trạng thái, thời gian trong trạng thái, nạp lại hôm nay.

    Khoá theo **tên nhóm** (`gpu_residency.nhom`) chứ không gắn cứng `rtx3090`:
    bảng tự khai nhóm nào tồn tại, nên thêm một nhóm GPU thứ hai không cần sửa
    hàm này. Hôm nay đúng một dòng.

    🔴 MỌI CON SỐ Ở ĐÂY LÀ **DẪN XUẤT**, KHÔNG PHẢI BỘ ĐẾM GHI TAY. Lý do nằm ở
       docstring `models.GpuResidency`: một bộ đếm ghi tay lệch đúng lúc một tiến
       trình chết giữa cửa sổ, và đó là lúc người ta cần đọc nó nhất.

    ⚠️ `nap_lai_hom_nay.so_lan` LÀ MỘT **CẬN DƯỚI**, và nó phải tự khai như vậy.
       Kho này không có bảng lịch sử chuyển trạng thái — `gpu_residency` giữ
       *trạng thái hiện tại*, một dòng mỗi nhóm — nên số lần nạp lại không đọc
       trực tiếp được. Phép dẫn xuất dùng hai tham số **đã khai** ở
       `residency.ThamSoResidency` (không gõ lại con số nào):

         · một cửa sổ ảnh dài tối đa `cua_so_anh_s` ⇒ hai job ảnh cách nhau hơn
           thế **không thể** cùng một cửa sổ;
         · một cửa sổ nhận tối đa `cua_so_anh_toi_da` job ⇒ một dải dài hơn thế
           **buộc** phải là nhiều cửa sổ.

       Và mỗi cửa sổ ảnh tốn đúng một lần nhả + một lần nạp lại LTT-3.8. Phép này
       **đếm thiếu** khi hai cửa sổ liền nhau nằm trong cùng `cua_so_anh_s` (gộp
       thành một), và **không bao giờ đếm thừa**. Một cận dưới tự khai là cận
       dưới thì dùng được; một con số im lặng sai thì không.

    ⛔ KHÔNG CÓ TÀI NGUYÊN `theo_lo` NÀO ⇒ `None`, KHÔNG PHẢI 0. Chưa app ảnh
       nào khai vai trò `theo_lo` (Task 5.5 làm việc đó) thì câu trả lời đúng là
       *"không đo được"*; một số 0 ở đây sẽ nói "hôm nay 3090 không đổi cư trú
       lần nào" — một câu sai về phía trấn an.

    `tai_nguyen_theo_lo=None` (mặc định) ⇒ tự tra từ bản khai app. Truyền một
    danh sách tường minh là để phép kiểm tiêm dữ liệu mà không phải dựng registry.
    """
    from platform_core.llm import residency

    ts = residency.ThamSoResidency()
    tu_khai = tai_nguyen_theo_lo is None
    moc = _dau_ngay(now)
    ra: dict[str, object] = {"moc_hom_nay": moc.isoformat()}
    nhom: dict[str, dict] = {}
    tat_ca: set[str] = set()
    for row in db.execute(select(GpuResidency)).scalars().all():
        res = (tai_nguyen_theo_lo_cua(db, row.nhom) if tu_khai
               else list(tai_nguyen_theo_lo or ()))
        tat_ca.update(res)
        cua_so = row.cua_so_bat_dau
        anh_trong_cua_so = None
        if res and cua_so is not None:
            anh_trong_cua_so = int(db.execute(select(
                func.count(Job.id)).where(
                    Job.admission_resource.in_(res),
                    Job.admitted_at.is_not(None),
                    Job.admitted_at >= cua_so)).scalar() or 0)
        nhom[row.nhom] = {
            "trang_thai": row.trang_thai,
            "giay_trong_trang_thai": round(_seconds(row.tu_luc, now) or 0.0, 3),
            "cua_so_anh_mo": cua_so is not None,
            "giay_trong_cua_so": (None if cua_so is None
                                  else round(_seconds(cua_so, now) or 0.0, 3)),
            "lan_nap_loi": int(row.lan_nap_loi or 0),
            "anh_da_nhan_trong_cua_so": anh_trong_cua_so,
            "nap_lai_hom_nay": _nap_lai_hom_nay(db, res=res, moc=moc, now=now, ts=ts),
        }
    ra["tai_nguyen_theo_lo"] = sorted(tat_ca)
    ra["nhom"] = dict(sorted(nhom.items()))
    return ra


def _nap_lai_hom_nay(db: DbSession, *, res: list, moc: datetime,
                     now: datetime, ts) -> dict:
    """Số cửa sổ ảnh (= số lần nạp lại LTT-3.8) hôm nay, cận dưới. Xem docstring trên."""
    import math

    if not res:
        return {"so_lan": None, "giay_uoc": None,
                "cach_do": "khong_khai_tai_nguyen_theo_lo"}
    moc_ngay = [t for t in db.execute(select(Job.admitted_at).where(
        Job.admission_resource.in_(res), Job.admitted_at.is_not(None),
        Job.admitted_at >= moc).order_by(Job.admitted_at)).scalars().all()
        if t is not None]
    so_lan, dai, truoc = 0, 0, None
    for t in moc_ngay:
        if truoc is not None and (_seconds(truoc, t) or 0.0) > ts.cua_so_anh_s:
            so_lan += math.ceil(dai / max(1, int(ts.cua_so_anh_toi_da)))
            dai = 0
        dai += 1
        truoc = t
    if dai:
        so_lan += math.ceil(dai / max(1, int(ts.cua_so_anh_toi_da)))
    return {"so_lan": int(so_lan),
            # `t_nap_llm_s` là số ĐO (§G4/§G5) và nó sống ở `ThamSoResidency`.
            # Đây là **ước** tổng thời gian nạp, nên tên khoá nói ra điều đó.
            "giay_uoc": round(so_lan * float(ts.t_nap_llm_s), 3),
            "cach_do": "can_duoi_tu_jobs"}


def snapshot(db: DbSession, *, now: datetime | None = None,
             days: int = 7, stale_minutes: int = 10,
             lease_stale_minutes: int = 20,
             app_slug: str = "",
             tai_nguyen_theo_lo: tuple[str, ...] | list[str] | None = None) -> dict:
    current = now or datetime.now(timezone.utc)
    cutoff = current - timedelta(days=max(1, days))
    jobs_stmt = select(Job).where(Job.created_at >= cutoff)
    if app_slug:
        jobs_stmt = jobs_stmt.where(Job.app_slug == app_slug[:64])
    rows = list(db.execute(jobs_stmt).scalars().all())
    finished = [job for job in rows if job.status in {JOB_DONE, JOB_ERROR}]
    success = sum(job.status == JOB_DONE for job in finished)
    queue_wait = [value for job in rows
                  if (value := _seconds(job.created_at, job.started_at)) is not None]
    admission_delay = [value for job in rows
                       if (value := _seconds(job.created_at, job.admitted_at))
                       is not None]
    runtime = [value for job in finished
               if (value := _seconds(job.started_at, job.finished_at)) is not None]
    from platform_core.job_scheduler import normalize_priority

    lifecycle_by_priority = {
        priority: {
            "started": sum(normalize_priority(job.priority_class) == priority and
                           job.started_at is not None for job in rows),
            "completed": sum(normalize_priority(job.priority_class) == priority and
                             job.status == JOB_DONE for job in rows),
            "failed": sum(normalize_priority(job.priority_class) == priority and
                          job.status == JOB_ERROR for job in rows),
            "cancelled": sum(normalize_priority(job.priority_class) == priority and
                             job.status == JOB_CANCELLED for job in rows),
        }
        for priority in ("internal", "external")
    }
    events_stmt = select(
        JobEvent.event_code, func.count(JobEvent.id),
    ).where(JobEvent.created_at >= cutoff)
    if app_slug:
        events_stmt = events_stmt.where(JobEvent.app_slug == app_slug[:64])
    event_counts: dict[str, int] = dict(db.execute(
        events_stmt.group_by(JobEvent.event_code)).all())
    stale_cutoff = current - timedelta(minutes=max(1, stale_minutes))
    stale = 0
    for job in rows:
        if job.status != JOB_RUNNING:
            continue
        heartbeat = job.heartbeat_at or job.started_at or job.created_at
        if heartbeat.tzinfo is None:
            heartbeat = heartbeat.replace(tzinfo=timezone.utc)
        stale += heartbeat < stale_cutoff
    total = len(finished)
    done_ids = [job.id for job in finished if job.status == JOB_DONE]
    credit_spent = 0
    if done_ids:
        net_rows = db.execute(select(
            CreditEntry.job_id, func.sum(CreditEntry.delta),
        ).where(CreditEntry.job_id.in_(done_ids)).group_by(
            CreditEntry.job_id)).all()
        credit_spent = sum(max(0, -int(delta or 0)) for _job_id, delta in net_rows)
    successful = len(done_ids)

    # Queue hiện tại không bị giới hạn bởi cửa sổ báo cáo: một job chờ tám ngày
    # vẫn phải hiện trên dashboard hôm nay, nếu không chính job kẹt lâu nhất lại
    # biến mất khỏi số liệu.
    queued_stmt = select(Job).where(Job.status == JOB_QUEUED)
    if app_slug:
        queued_stmt = queued_stmt.where(Job.app_slug == app_slug[:64])
    queued_rows = list(db.execute(queued_stmt).scalars().all())
    queue_depth_by_resource: dict[str, int] = {}
    oldest_by_resource: dict[str, float] = {}
    queue_depth_by_resource_priority: dict[str, dict[str, int]] = {}
    oldest_by_resource_priority: dict[str, dict[str, float]] = {}
    waits_by_resource_priority: dict[str, dict[str, list[float]]] = {}
    for job in queued_rows:
        resource = job.admission_resource or "unclassified"
        priority = normalize_priority(job.priority_class)
        queue_depth_by_resource[resource] = queue_depth_by_resource.get(resource, 0) + 1
        age = _seconds(job.created_at, current) or 0.0
        oldest_by_resource[resource] = max(oldest_by_resource.get(resource, 0.0), age)
        by_priority = queue_depth_by_resource_priority.setdefault(resource, {})
        by_priority[priority] = by_priority.get(priority, 0) + 1
        oldest_priority = oldest_by_resource_priority.setdefault(resource, {})
        oldest_priority[priority] = max(oldest_priority.get(priority, 0.0), age)
        waits_by_resource_priority.setdefault(resource, {}).setdefault(
            priority, []).append(age)

    lease_stmt = select(ExecutionLease)
    if app_slug:
        lease_stmt = lease_stmt.join(
            Job, ExecutionLease.job_id == Job.id).where(
                Job.app_slug == app_slug[:64])
    lease_rows = list(db.execute(lease_stmt).scalars().all())
    active_leases_by_resource: dict[str, int] = {}
    lease_stale_cutoff = current - timedelta(
        minutes=max(1, int(lease_stale_minutes)))
    expired_lease_candidates = 0
    for lease in lease_rows:
        heartbeat = lease.heartbeat_at
        if heartbeat.tzinfo is None:
            heartbeat = heartbeat.replace(tzinfo=timezone.utc)
        if heartbeat < lease_stale_cutoff:
            expired_lease_candidates += 1
            continue
        active_leases_by_resource[lease.resource] = (
            active_leases_by_resource.get(lease.resource, 0) + 1)

    return {
        "app_slug": app_slug[:64],
        "window_days": max(1, days),
        "jobs_total": len(rows),
        "finished_total": total,
        "success_rate": round(success / total, 4) if total else 1.0,
        "queue_wait_p50_s": _percentile(queue_wait, 0.50),
        "queue_wait_p95_s": _percentile(queue_wait, 0.95),
        "admission_delay_p50_s": _percentile(admission_delay, 0.50),
        "admission_delay_p95_s": _percentile(admission_delay, 0.95),
        "runtime_p50_s": _percentile(runtime, 0.50),
        "runtime_p95_s": _percentile(runtime, 0.95),
        "lifecycle_by_priority": lifecycle_by_priority,
        "retry_total": int(event_counts.get("retry_scheduled", 0)),
        "refund_total": int(event_counts.get("credit_refunded", 0)),
        "resource_wait_total": int(event_counts.get("resource_wait", 0)),
        "provider_dispatched_total": int(event_counts.get("provider_dispatched", 0)),
        "provider_rejected_total": int(event_counts.get("provider_rejected", 0)),
        "ambiguous_provider_total": int(event_counts.get("ambiguous_provider", 0)),
        "scheduler_priority_override_total": int(
            event_counts.get("scheduler_priority_override", 0)),
        "scheduler_fair_rotation_total": int(
            event_counts.get("scheduler_fair_rotation", 0)),
        "queue_depth": len(queued_rows),
        "queue_depth_by_resource": dict(sorted(queue_depth_by_resource.items())),
        "queue_depth_by_resource_priority": {
            resource: dict(sorted(values.items()))
            for resource, values in sorted(queue_depth_by_resource_priority.items())},
        "oldest_queued_age_s": round(max(oldest_by_resource.values(), default=0.0), 3),
        "oldest_queued_age_s_by_resource": {
            key: round(value, 3) for key, value in sorted(oldest_by_resource.items())},
        "oldest_queued_age_s_by_resource_priority": {
            resource: {priority: round(value, 3)
                       for priority, value in sorted(values.items())}
            for resource, values in sorted(oldest_by_resource_priority.items())},
        "queue_wait_s_by_resource_priority": {
            resource: {
                priority: {"p50": _percentile(values, 0.50),
                           "p95": _percentile(values, 0.95)}
                for priority, values in sorted(classes.items())
            }
            for resource, classes in sorted(waits_by_resource_priority.items())},
        "active_execution_leases": sum(active_leases_by_resource.values()),
        "active_execution_leases_by_resource": dict(
            sorted(active_leases_by_resource.items())),
        "execution_lease_rows": len(lease_rows),
        "expired_execution_lease_candidates": int(expired_lease_candidates),
        "stale_jobs": int(stale),
        # ── Hai khối của dual-model 6.3 ───────────────────────────────────────
        #
        # ⛔ KHÔNG lọc theo `app_slug`. `llm_waiters`/`gpu_residency` là sổ của
        #    **nền tảng** cho một card dùng chung; cắt chúng theo app sẽ cho mỗi
        #    app một phần của cùng một hàng đợi và không ai thấy được cái hàng
        #    thật. Snapshot theo app vẫn mang khối này, và nó cố ý giống hệt
        #    khối toàn cục — cùng một sự thật, không phải một sự thật bị cắt.
        "llm_theo_model": llm_theo_model(db, now=current, cutoff=cutoff),
        "residency_3090": residency_3090(
            db, now=current, tai_nguyen_theo_lo=tai_nguyen_theo_lo),
        "event_write_failures": job_events.event_write_failures(),
        "credit_spent_total": int(credit_spent),
        "credit_per_successful_job": (
            round(credit_spent / successful, 3) if successful else 0.0),
    }


def slo_budget(requires: tuple | list | set = ()) -> dict:
    """Budget generic theo loại executor, không biết tên app cụ thể."""
    needs = set(requires or ())
    if "browser" in needs:
        queue_max = 300.0
        profile = "browser"
    elif needs.intersection({"gpu", "ffmpeg"}):
        queue_max = 120.0
        profile = "compute"
    else:
        queue_max = 30.0
        profile = "api"
    return {
        "profile": profile,
        "minimum_finished": 20,
        "success_rate_min": 0.90,
        "queue_wait_p95_s_max": queue_max,
        "stale_jobs_max": 0,
        "event_write_failures_max": 0,
    }


def evaluate_slo(metrics: dict, budget: dict) -> dict:
    """Đánh giá SLO; ít hơn 20 mẫu là insufficient, không giả PASS."""
    checks = {
        "success_rate": float(metrics.get("success_rate", 0)) >=
                        float(budget["success_rate_min"]),
        "queue_wait_p95": float(metrics.get("queue_wait_p95_s", 0)) <=
                          float(budget["queue_wait_p95_s_max"]),
        "stale_jobs": int(metrics.get("stale_jobs", 0)) <=
                      int(budget["stale_jobs_max"]),
        "event_write_failures": int(metrics.get("event_write_failures", 0)) <=
                                int(budget["event_write_failures_max"]),
    }
    hard_failure = not checks["stale_jobs"] or not checks["event_write_failures"]
    enough = int(metrics.get("finished_total", 0)) >= int(budget["minimum_finished"])
    if hard_failure:
        state = "fail"
    elif not enough:
        state = "insufficient_data"
    else:
        state = "pass" if all(checks.values()) else "fail"
    return {"state": state, "checks": checks, "budget": budget,
            "sample_finished": int(metrics.get("finished_total", 0))}


def alerts(metrics: dict) -> list[dict]:
    """Cảnh báo nền tối thiểu; ngưỡng SLO production được khóa ở Phase 4."""
    found: list[dict[str, object]] = []
    if metrics.get("finished_total", 0) >= 5 and metrics.get("success_rate", 1) < 0.90:
        found.append({"code": "job_success_low", "level": "warning"})
    if metrics.get("stale_jobs", 0) > 0:
        found.append({"code": "job_stale", "level": "error"})
    if metrics.get("event_write_failures", 0) > 0:
        found.append({"code": "job_event_write_failed", "level": "error"})
    for resource, classes in metrics.get(
            "oldest_queued_age_s_by_resource_priority", {}).items():
        age = float(classes.get("external", 0.0) or 0.0)
        if age >= EXTERNAL_STARVATION_S:
            found.append({"code": "external_queue_starvation",
                          "level": "warning", "resource": resource,
                          "oldest_wait_seconds": age})
    return found
