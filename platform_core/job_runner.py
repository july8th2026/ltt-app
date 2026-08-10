"""
job_runner.py — vòng chạy của worker (H2, Q26).

Đây là phần chạy trong dịch vụ **LTTWorker** — tiến trình RIÊNG với web (Q6),
nên một job nặng (FFmpeg/GPU về sau) không làm chậm web, và cập nhật web không
giết job đang chạy.

Vòng đời một lượt:
    reclaim_orphans → claim → chạy handler (đập nhịp + báo tiến độ) → complete/fail

Mỗi bước là **một transaction ngắn riêng**: claim commit ngay để job chuyển
`running` (worker khác không nhặt lại); tiến độ commit riêng để web thấy job
nhích; complete/fail commit riêng. Không giữ một transaction mở suốt thời gian
chạy handler — một handler chạy 3 phút mà giữ khoá dòng 3 phút sẽ chặn mọi thứ.
"""
from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from typing import Optional

from platform_core import jobs as jobq
from platform_core import job_events
from platform_core.db import get_session
from platform_core.i18n import N_
from platform_core.models import JOB_CANCELLED, JOB_ERROR, Job

log = logging.getLogger(__name__)

# Hàng đợi trống thì ngủ bao lâu trước khi hỏi lại. Đủ ngắn để job mới chạy
# gần như tức thì, đủ dài để không quay CPU khi rảnh.
POLL_INTERVAL_S = 2.0

# Nhịp báo "lease GPU còn sống". Phải NGẮN hơn nhiều so với
# `gpu_lease.ORPHAN_TIMEOUT` (10 phút), nếu không một job nặng sẽ bị coi là chết
# và mất card vào tay worker khác giữa chừng.
GPU_HEARTBEAT_S = 60.0

# Mọi GPU đều bận thì hoãn job bao lâu trước khi thử lại. Đủ dài để không quay
# vòng đốt CPU, đủ ngắn để người dùng không thấy job đứng im.
GPU_RETRY_DELAY_S = 20
EVENT_PURGE_INTERVAL_S = 6 * 60 * 60


class JobContext:
    """Tiện ích worker cấp cho handler: báo tiến độ (kèm đập nhịp).

    Mỗi lần `progress()` mở một transaction ngắn để ghi — nhờ vậy web thấy job
    nhích ngay, và heartbeat được cập nhật nên job đang chạy không bị coi là
    mồ côi.
    """

    def __init__(self, job_id: str, gpu_uuid: str = ""):
        self.job_id = job_id
        # GPU đã được nền tảng GIÀNH cho job này (H23). Rỗng = chạy CPU, hoặc
        # máy không có GPU, hoặc job không khai `gpu_vram_mb`.
        #
        # Handler KHÔNG được tự chọn card. Tự chọn nghĩa là hai handler chạy
        # song song cùng đọc "GPU 0 trống" rồi cùng nạp model lên đó và OOM —
        # đó là lý do việc giành chỗ nằm ở nền tảng, không ở app.
        self.gpu_uuid = gpu_uuid
        self.worker_id = ""
        self.attempt = 0
        self.app_slug = ""
        self.job_type = ""

    @property
    def has_gpu(self) -> bool:
        return bool(self.gpu_uuid)

    def gpu_env(self, base: dict | None = None) -> dict:
        """Môi trường đã ghim tiến trình con vào ĐÚNG card được cấp.

        Dùng cho mọi thứ chạy ngoài tiến trình worker (whisperx, ffmpeg, engine
        vendor): `subprocess.run(cmd, env=ctx.gpu_env())`. Không có GPU thì trả
        môi trường nguyên vẹn, nên gọi vô điều kiện cũng an toàn.
        """
        import os
        if not self.gpu_uuid:
            return dict(os.environ if base is None else base)
        from platform_core import gpu as gpu_mod
        return gpu_mod.env_for(self.gpu_uuid, base)

    def progress(self, percent: int, message: str = "") -> None:
        for db in _one_session():
            job = db.get(Job, self.job_id)
            if job is not None:
                if job.status == JOB_CANCELLED:
                    raise JobCancelled()
                jobq.set_progress(db, job, percent, message)
                db.commit()

    def event(self, event_code: str, message: str = "", *, details: dict | None = None,
              level: str = "info", visibility: str = job_events.INTERNAL,
              event_key: str | None = None) -> bool:
        """Ghi một mốc nghiệp vụ/kỹ thuật cho job mà không lộ payload.

        App dùng API này cho các mốc đặc thù (ví dụ ``provider_submitted`` hay
        ``artifact_saved``). Lỗi ghi telemetry không được làm hỏng job đang
        chạy; bộ đếm ``event_write_failures`` và process log vẫn lưu dấu vết.
        """
        try:
            for db in _one_session():
                job = db.get(Job, self.job_id)
                if job is None:
                    return False
                job_events.append(
                    db, job, event_code, public_message=message,
                    details=details or {}, level=level, visibility=visibility,
                    event_key=event_key,
                )
                db.commit()
                return True
        except Exception:  # noqa: BLE001 - observability must be best effort
            log.exception("khong ghi duoc job event %s", event_code)
            return False
        return False

    def stage(self, name: str, message: str = "", *, details: dict | None = None,
              event_key: str | None = None) -> bool:
        """Tên gọi ngắn cho app ghi mốc ``stage`` nội bộ."""
        return self.event(
            "stage", message or name, details={"stage": str(name)[:80], **(details or {})},
            visibility=job_events.INTERNAL, event_key=event_key,
        )

    def is_cancelled(self) -> bool:
        """Read the durable job state; safe for subprocess polling callbacks."""
        for db in _one_session():
            job = db.get(Job, self.job_id)
            return job is not None and job.status == JOB_CANCELLED
        return False


class JobCancelled(Exception):
    """Cooperative cancellation requested by the job owner."""


def _one_session():
    """Một session dùng một lần (generator để đóng chắc chắn)."""
    gen = get_session()
    db = next(gen)
    try:
        yield db
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _chay_mot_job(worker_id: str) -> bool:
    """Nhặt và chạy đúng một job. Trả True nếu có job để chạy, False nếu trống.

    claim() ở một transaction, chạy handler ở ngoài transaction đó, rồi
    complete/fail ở transaction khác — xem docstring module vì sao.
    """
    # 1. Nhặt (transaction ngắn, commit ngay để job thành 'running').
    job_id: Optional[str] = None
    job_type = params = None
    for db in _one_session():
        job = jobq.claim(db, worker_id=worker_id)
        if job is None:
            db.commit()
            return False
        job_id, job_type, params = job.id, job.job_type, dict(job.params)
        db.commit()

    log.info("worker %s nhat job %s (%s)", worker_id, job_id[:8], job_type)

    # 1b. Giành GPU nếu loại job này khai cần (H23). Giành TRƯỚC khi chạy
    # handler, và bằng khoá nguyên tử — không phải "đọc nvidia-smi rồi chọn".
    need_mb = _vram_can(job_type)
    with _giu_gpu(worker_id, job_id, job_type, need_mb) as (lease, het_gpu):
        if het_gpu:
            # Mọi card đều bận. Trả job về hàng đợi thay vì chạy chung một card
            # rồi OOM giữa chừng — người dùng chờ thêm một lượt vẫn hơn là mất
            # cả job. Không tính là một lần thử thất bại.
            _tra_ve_hang_doi(job_id, job_type)
            return True

        # 2. Chạy handler NGOÀI transaction claim (không giữ khoá suốt lúc chạy).
        ctx = JobContext(job_id, gpu_uuid=(lease.gpu_uuid if lease else ""))
        return _chay_handler(worker_id, job_id, job_type, params, ctx)


def _vram_can(job_type: str) -> int:
    """VRAM tối thiểu app khai cho loại job này. 0 = không cần GPU riêng."""
    try:
        from platform_core.registry import discover
        for item in discover():
            if item.error:
                continue
            if job_type in item.manifest.job_types:
                return item.manifest.vram_for(job_type)
    except Exception:                       # noqa: BLE001
        log.exception("Không đọc được nhu cầu VRAM của %s — coi như không cần GPU",
                      job_type)
    return 0


@contextmanager
def _giu_gpu(worker_id: str, job_id: str, job_type: str, need_mb: int):
    """Giữ một GPU suốt thời gian chạy job. Yields (lease, het_gpu).

    Đập nhịp bằng **luồng riêng** chứ không dựa vào `ctx.progress()`: một job
    nạp model 8 phút không gọi progress lần nào sẽ bị coi là mồ côi, lease bị
    thu hồi, worker khác chiếm card — rồi cả hai OOM. Đúng cái ta đang tránh.
    """
    if need_mb <= 0:
        yield None, False
        return

    from platform_core import gpu_lease as gl
    gen = get_session(); db = next(gen)
    lease = None
    try:
        lease = gl.acquire(db, worker_id=worker_id, job_id=job_id, need_mb=need_mb)
    except Exception:                       # noqa: BLE001
        log.exception("Không giành được GPU cho %s — chạy tiếp không GPU", job_type)
    if lease is None:
        try:
            het_gpu = bool(gl.gpu_mod.list_gpus())   # có GPU nhưng đều bận?
        except Exception:                   # noqa: BLE001
            log.exception("Không đếm được GPU — coi như máy không có GPU")
            het_gpu = False
        try: next(gen)
        except StopIteration: pass
        yield None, het_gpu
        return

    log.info("job %s chạy trên GPU %s (index %s), xin %s MB",
             job_id[:8], lease.gpu_uuid[:20], lease.gpu_index, need_mb)
    dung = threading.Event()

    def _nhip():
        while not dung.wait(GPU_HEARTBEAT_S):
            try:
                gl.heartbeat(db, lease)
            except Exception:               # noqa: BLE001
                log.exception("Đập nhịp lease GPU lỗi")

    t = threading.Thread(target=_nhip, name=f"gpu-hb-{job_id[:8]}", daemon=True)
    t.start()
    try:
        yield lease, False
    finally:
        dung.set()
        t.join(timeout=5)
        try:
            gl.release(db, lease)
        except Exception:                   # noqa: BLE001
            log.exception("Không trả được lease GPU — sẽ hết hạn theo mồ côi")
        try: next(gen)
        except StopIteration: pass


def _tra_ve_hang_doi(job_id: str, job_type: str) -> None:
    """Đưa job về `queued` để chạy lượt sau, KHÔNG tính là một lần thử hỏng."""
    from platform_core.models import JOB_QUEUED
    from datetime import datetime, timedelta, timezone
    for db in _one_session():
        job = db.get(Job, job_id)
        if job is not None and job.status not in (JOB_CANCELLED,):
            job.status = JOB_QUEUED
            job.worker_id = ""
            job.next_run_at = datetime.now(timezone.utc) + timedelta(
                seconds=GPU_RETRY_DELAY_S)
            job_events.append(
                db, job, "resource_wait", public_message=N_("Đang chờ tài nguyên xử lý."),
                details={"delay_seconds": GPU_RETRY_DELAY_S,
                         "status": JOB_QUEUED}, level="warning",
            )
            db.commit()
    log.info("job %s (%s) hoãn %ss: mọi GPU đang bận",
             job_id[:8], job_type, GPU_RETRY_DELAY_S)


def _chay_handler(worker_id: str, job_id: str, job_type: str, params: dict,
                  ctx: "JobContext") -> bool:
    started = time.perf_counter()
    app_slug = ""
    attempt = 0
    correlation_id = ""
    for db in _one_session():
        job = db.get(Job, job_id)
        if job is not None:
            app_slug = job.app_slug
            attempt = int(job.attempts or 0) + 1
            correlation_id = job.correlation_id or ""
    ctx.worker_id = worker_id
    ctx.attempt = attempt
    ctx.app_slug = app_slug
    ctx.job_type = job_type
    from platform_core.observability import job_logging_context
    with job_logging_context(job_id=job_id, app_slug=app_slug, job_type=job_type,
                             worker_id=worker_id, correlation_id=correlation_id):
        _runtime_event(
            job_id, "execution_started", details={"worker_id": worker_id,
            "attempt": attempt}, event_key=f"execution-started:{attempt}")
        try:
            handler = jobq.resolve_handler(job_type)
            result = handler(params, ctx)
            if not isinstance(result, dict):
                result = {"result": result}
        except JobCancelled:
            _runtime_event(job_id, "execution_cancelled", level="warning",
                           details={"attempt": attempt,
                                    "duration_ms": _duration_ms(started)},
                           event_key=f"execution-cancelled:{attempt}")
            for db in _one_session():
                job = db.get(Job, job_id)
                if job is not None:
                    _hoan_credit(db, job); db.commit()
            return True
        except Exception as exc:
            # 3a. Thất bại → fail(). Chỉ hoàn credit khi job hết lượt;
            # retry còn lại giữ nguyên hold để lượt sau dùng.
            safe_error = job_events.sanitize_text(
                f"{type(exc).__name__}: {exc}", limit=5000)
            _runtime_event(job_id, "execution_failed", level="error", details={
                "attempt": attempt, "error_type": type(exc).__name__,
                "error": safe_error, "duration_ms": _duration_ms(started),
                "error_fingerprint": job_events.error_fingerprint(safe_error),
            }, event_key=f"execution-failed:{attempt}")
            for db in _one_session():
                job = db.get(Job, job_id)
                if job is not None:
                    # A subprocess can notice cancellation by callback and unwind
                    # with its own exception type. Never fail() a cancelled job.
                    if job.status == JOB_CANCELLED:
                        _hoan_credit(db, job)
                        db.commit()
                        log.info("job %s da huy cooperative", job_id[:8])
                        return True
                    jobq.fail(db, job, safe_error)
                    if job.status == JOB_ERROR:
                        _hoan_credit(db, job)
                    db.commit()
            log.warning("job %s that bai: %s", job_id[:8], safe_error)
            return True

        # 3b. Thành công → complete() + quyết toán credit (cùng transaction).
        _runtime_event(job_id, "execution_completed", details={
            "attempt": attempt, "duration_ms": _duration_ms(started),
            "result_keys": _result_keys(result),
            "reported_credit_cost": _safe_credit_cost(result),
        }, event_key=f"execution-completed:{attempt}")
        for db in _one_session():
            job = db.get(Job, job_id)
            if job is not None:
                if job.status == JOB_CANCELLED:
                    _hoan_credit(db, job); db.commit(); return True
                jobq.complete(db, job, result)
                _quyet_toan_credit(db, job, result)
                db.commit()
        log.info("job %s xong", job_id[:8])
        return True


def _duration_ms(started: float) -> int:
    return max(0, int(round((time.perf_counter() - started) * 1000)))


def _result_keys(result: dict) -> list[str]:
    """Chỉ ghi tên key, không ghi nội dung kết quả/artifact."""
    return sorted(str(key)[:80] for key in result.keys())[:50]


def _safe_credit_cost(result: dict) -> int | None:
    value = result.get("credit_cost")
    if isinstance(value, bool):
        return None
    try:
        return max(0, int(value)) if value is not None else None
    except (TypeError, ValueError):
        return None


def _runtime_event(job_id: str, event_code: str, *, details: dict | None = None,
                   level: str = "info", event_key: str | None = None) -> bool:
    """Best-effort internal event writer used around every app handler."""
    try:
        for db in _one_session():
            job = db.get(Job, job_id)
            if job is None:
                return False
            job_events.append(db, job, event_code, visibility=job_events.INTERNAL,
                              level=level, details=details or {}, event_key=event_key)
            db.commit()
            return True
    except Exception:  # noqa: BLE001
        log.exception("khong ghi duoc runtime event %s", event_code)
        return False
    return False


def _quyet_toan_credit(db, job: Job, result: dict) -> None:
    """Quyết toán credit khi job xong. Chỉ chạm sổ nếu job có giữ chỗ.

    Giá thật lấy từ `result["credit_cost"]` nếu handler báo (như Seedance tính
    theo token thật); nếu không, dùng đúng phần đã giữ (giá ước tính = giá thật,
    như demo). Job không đi qua credit (không có hold) thì bỏ qua.
    """
    from platform_core import credit
    if not job.user_id or credit.so_da_giu(db, job.id) == 0:
        return
    actual = result.get("credit_cost")
    if actual is None:
        actual = credit.so_da_giu(db, job.id)
    credit.quyet_toan(db, job.user_id, job.id, int(actual))


def _hoan_credit(db, job: Job) -> None:
    """Hoàn credit khi job thất bại hẳn. Idempotent, bỏ qua nếu không có hold."""
    from platform_core import credit
    if not job.user_id or credit.so_da_giu(db, job.id) == 0:
        return
    credit.hoan(db, job.user_id, job.id)


def run_forever(worker_id: str, *, stop=None) -> None:
    """Vòng lặp chính của worker. `stop` là callable trả True để dừng êm.

    Trước mỗi lượt rảnh, dọn job mồ côi — nhờ vậy một worker vừa khởi động lại
    sẽ tự nhặt lại job mà worker chết để lại, không cần ai can thiệp.
    """
    log.info("worker %s bat dau", worker_id)
    next_event_purge = 0.0
    while stop is None or not stop():
        try:
            if time.monotonic() >= next_event_purge:
                for db in _one_session():
                    removed = job_events.purge_expired(db)
                    db.commit()
                    if removed[job_events.CUSTOMER] or removed[job_events.INTERNAL]:
                        log.info("don job event het han: customer=%s internal=%s",
                                 removed[job_events.CUSTOMER], removed[job_events.INTERNAL])
                next_event_purge = time.monotonic() + EVENT_PURGE_INTERVAL_S
            for db in _one_session():
                n = jobq.reclaim_orphans(db)
                db.commit()
                if n:
                    log.warning("nhat lai %d job mo coi", n)
            co_viec = _chay_mot_job(worker_id)
            if not co_viec:
                time.sleep(POLL_INTERVAL_S)
        except Exception:
            # Một lượt hỏng không được giết cả worker — ngủ rồi thử lại.
            log.exception("loi trong vong worker, tiep tuc")
            time.sleep(POLL_INTERVAL_S)
    log.info("worker %s dung", worker_id)
