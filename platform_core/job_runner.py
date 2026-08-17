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
from platform_core.models import (JOB_CANCELLED, JOB_ERROR, JOB_RUNNING,
                                   Job)

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
UPLOAD_SWEEP_INTERVAL_S = 60 * 60
# Webhooks are delivered by the worker, never by the request that
# finished the job: a customer's endpoint being slow or down must not
# delay a settlement (Q92 / Public API prompt 09).
WEBHOOK_DELIVERY_INTERVAL_S = 15
# The Public API keeps its counters in memory (see
# `platform_core/public_api/metrics.py`); the worker prints them so an operator
# has something to read without adding a metrics service.
METRICS_LOG_INTERVAL_S = 5 * 60
#: Xả bộ đếm xuống CSDL. Một lượt ghi gộp mỗi tiến trình mỗi phút —
#: đủ mịn để thấy một cơn tăng đột biến, đủ thưa để không tốn gì.
METRICS_FLUSH_INTERVAL_S = 60

#: Trần thời gian chạy mặc định cho một job, theo lớp tài nguyên. App khai lại
#: được qua `manifest.max_runtime_s`. Con số ở đây cố ý **rộng rãi**: nó không
#: phải hạn mức hiệu năng, nó là cái chốt chặn cho job treo hẳn.
RUNTIME_LIMIT_S = {"gpu": 2 * 3600, "ffmpeg": 2 * 3600, "browser": 30 * 60,
                   "api": 30 * 60}
RUNTIME_LIMIT_DEFAULT_S = 30 * 60


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


def _chay_mot_job(worker_id: str, *, capabilities=None) -> bool:
    """Nhặt và chạy đúng một job. Trả True nếu có job để chạy, False nếu trống.

    claim() ở một transaction, chạy handler ở ngoài transaction đó, rồi
    complete/fail ở transaction khác — xem docstring module vì sao.

    `capabilities` giới hạn tiến trình này chỉ nhặt job của app khai
    `manifest.requires` nằm gọn trong tập đó — cho phép chia đội hình worker
    theo loại tài nguyên thay vì theo số card. None nghĩa là đa năng, giữ
    nguyên hành vi cũ.
    """
    # 1. Nhặt (transaction ngắn, commit ngay để job thành 'running').
    job_id: Optional[str] = None
    job_type = params = None
    for db in _one_session():
        job = jobq.claim(db, worker_id=worker_id,
                         capabilities=capabilities)
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


def _tran_thoi_gian(app_slug: str, job_type: str) -> int:
    """Job này được chạy tối đa bao nhiêu giây."""
    from platform_core import registry
    from platform_core.public_api.limits import resource_class

    for item in registry.discover():
        if item.error or item.manifest.slug != app_slug:
            continue
        lop = resource_class(item.manifest)
        return item.manifest.runtime_limit_for(
            job_type, default=RUNTIME_LIMIT_S.get(lop, RUNTIME_LIMIT_DEFAULT_S))
    return RUNTIME_LIMIT_DEFAULT_S


def _het_gio(job_id: str, job_type: str, giay: int) -> None:
    """Job vượt trần: trả lời khách, hoàn tiền, rồi kết thúc tiến trình.

    Vì sao phải kết thúc tiến trình. Handler đang chạy code tuỳ ý — thường là
    thư viện C/CUDA giữ GIL — nên không có cách nào đáng tin để dừng nó từ
    Python. Đánh dấu job hỏng mà để handler chạy tiếp thì khách có câu trả lời
    nhưng **slot vẫn bị chiếm**, tức chỉ giải quyết được nửa vấn đề.

    An toàn vì tiến trình cha thay thế con đã chết (`job_worker.main`), và vì
    trạng thái job đã được ghi xuống CSDL **trước** khi thoát.

    `retry=False`: thử lại một job treo chỉ tiêu thêm một slot rồi treo tiếp.
    """
    import os as _os

    log.error("job %s (%s) vuot tran %ss — ket thuc tien trinh",
              job_id[:8], job_type, giay)
    try:
        for db in _one_session():
            job = db.get(Job, job_id)
            if job is not None and job.status == JOB_RUNNING:
                jobq.fail(db, job,
                          f"Job vuot tran thoi gian chay ({giay}s).",
                          retry=False)
                db.commit()
                _hoan_tien_neu_can(db, job)
    except Exception:                       # noqa: BLE001
        log.exception("khong ghi duoc trang thai het gio cho %s", job_id[:8])
    finally:
        # `_exit` chứ không phải `sys.exit`: handler có thể nuốt SystemExit, và
        # ở đây không còn gì đáng dọn — trạng thái đã bền vững.
        _os._exit(3)


def _hoan_tien_neu_can(db, job) -> None:
    """Trả lại phần credit đang giữ của một job không bao giờ hoàn tất."""
    from platform_core import credit

    try:
        if credit.so_da_giu(db, job.id) > 0:
            credit.hoan(db, job.user_id, job.id)
            db.commit()
    except Exception:                       # noqa: BLE001
        log.exception("khong hoan duoc credit cho job %s", job.id[:8])


@contextmanager
def _canh_gio(job_id: str, app_slug: str, job_type: str):
    """Đồng hồ canh giờ cho một job, tắt chắc chắn khi rời khối.

    Là context manager chứ không phải hai lời gọi start/cancel rải rác: hàm này
    có nhiều đường thoát, và quên tắt ở **một** đường nghĩa là một job chạy xong
    trong năm giây vẫn bị giết tiến trình khi tới hạn — đồng hồ canh giờ biến
    thành đồng hồ hẹn giờ tự sát.
    """
    tran = _tran_thoi_gian(app_slug, job_type)
    dong_ho = None
    if tran > 0:
        dong_ho = threading.Timer(float(tran), _het_gio,
                                  args=(job_id, job_type, tran))
        dong_ho.daemon = True
        dong_ho.start()
    try:
        yield tran
    finally:
        if dong_ho is not None:
            dong_ho.cancel()


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
                             worker_id=worker_id, correlation_id=correlation_id),             _canh_gio(job_id, app_slug, job_type):
        _runtime_event(
            job_id, "execution_started", details={"worker_id": worker_id,
            "attempt": attempt}, event_key=f"execution-started:{attempt}")
        try:
            handler = jobq.resolve_handler(job_type)
            result = _ket_qua_sandbox(job_id, params)
            if result is None:
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
                    _hoan_credit(db, job)
                    _enqueue_webhooks(db, job)
                    db.commit()
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
                        _enqueue_webhooks(db, job)
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
                settlement = _quyet_toan_credit(db, job, result)
                # After settlement, so the observation sits beside the charge it
                # will be compared against; before the webhook is queued only in
                # the sense that both happen in this transaction — a bookkeeping
                # estimate must never be why a customer's callback is late.
                _ghi_chi_phi(db, job)
                _enqueue_webhooks(db, job)
                if settlement is not None:
                    public_result = dict(result)
                    public_result["credit_cost"] = settlement.charged_credit
                    job.result = public_result
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


def _enqueue_webhooks(db, job: Job) -> None:
    """Write the outbox rows in the job's own transaction.

    Same transaction on purpose: an event that is written afterwards can be lost
    by a crash in between, and an event written before the job commits can
    announce something that never happened.
    """
    from platform_core.public_api.outbox import enqueue_for_job

    enqueue_for_job(db, job)


def _quyet_toan_credit(db, job: Job, result: dict):
    """Quyết toán credit khi job xong. Chỉ chạm sổ nếu job có giữ chỗ.

    Giá thật lấy từ `result["credit_cost"]` nếu handler báo (như Seedance tính
    theo token thật); nếu không, dùng đúng phần đã giữ (giá ước tính = giá thật,
    như demo). Job không đi qua credit (không có hold) thì bỏ qua.
    """
    from platform_core import credit
    if not job.user_id or credit.so_da_giu(db, job.id) == 0:
        return None
    actual = result.get("credit_cost")
    if actual is None:
        actual = credit.so_da_giu(db, job.id)
    return credit.quyet_toan(db, job.user_id, job.id, int(actual))


def _hoan_credit(db, job: Job) -> None:
    """Hoàn credit khi job thất bại hẳn. Idempotent, bỏ qua nếu không có hold."""
    from platform_core import credit
    if not job.user_id or credit.so_da_giu(db, job.id) == 0:
        return
    credit.hoan(db, job.user_id, job.id)
    try:
        from platform_core import upload_sessions
        from platform_core.storage import get_storage
        upload_sessions.cleanup_failed_job(db, get_storage(), job)
    except Exception:  # noqa: BLE001 - refund must not be blocked by cleanup
        log.exception("khong cleanup duoc input cua job %s", job.id[:8])


def _giao_webhook() -> None:
    """One pass of the webhook outbox. Never fatal to the worker loop."""
    import random

    from platform_core.public_api.outbox import deliver_due

    for db in _one_session():
        report = deliver_due(db, jitter=random.random())
        db.commit()
        if report["attempted"]:
            log.info("webhook: attempted=%s delivered=%s failed=%s dead=%s",
                     report["attempted"], report["delivered"], report["failed"],
                     report["dead"])


#: Alert conditions are slow-moving — a budget threshold, an expiring key, a
#: webhook that has given up. Scanning every fifteen minutes is soon enough to
#: be useful and rare enough to cost nothing.
ALERT_SCAN_INTERVAL_S = 15 * 60


def _quet_canh_bao() -> None:
    """Raise the alerts that are true right now, and age out the old ones.

    Deduplication lives in `notifications.raise_alert`, so re-detecting the same
    condition on every pass is harmless by design — which is what lets this be a
    plain periodic scan instead of an event pipeline.
    """
    from platform_core.public_api import alerting, notifications, ops_alerts
    from platform_core.public_api.config import load_public_api_config

    config = load_public_api_config()
    for db in _one_session():
        raised = alerting.scan_all(db, config=config)
        gone = notifications.purge_expired(db)
        db.commit()
        if raised:
            log.info("canh bao API: %d thong bao moi", raised)
        if gone:
            log.info("don %d thong bao API het han", gone)

        # Cùng nhịp, khác người nhận: trên là cho khách, đây là cho người trực.
        # Chỉ đọc `api_metric_samples` nên không cần commit; vắng
        # LTT_OPS_ALERT_EMAIL thì trả 0 và không làm gì.
        ops_alerts.gui(db)

        _don_nexus(db)


def _don_nexus(db) -> int:
    """Dọn mã ghép hết giá trị. Trả số dòng đã xoá.

    Gác sau cờ `LTT_NEXUS`: Nexus mặc định TẮT (Q93 fail-closed), và khi tắt thì
    bảng của nó có thể còn chưa được migrate. Truy vấn một bảng chưa tồn tại
    trong vòng bảo trì sẽ ném mỗi lượt và làm log ngập — nên cờ tắt là **không
    chạm gì cả**, không phải "thử rồi bỏ qua lỗi".
    """
    from platform_core import nexus

    if not nexus.enabled():
        return 0
    from platform_core.nexus import devices as nexus_devices

    xoa = nexus_devices.don_ma_het_han(db)
    db.commit()
    if xoa:
        log.info("don %d ma ghep nexus het gia tri", xoa)
    return xoa


def _don_noi_dung_job(db) -> int:
    """Cầu nối cho vòng dọn chung: trả số job đã hết hạn nội dung."""
    from platform_core import job_content

    bao_cao = job_content.purge_expired(db)
    if bao_cao["jobs"]:
        log.info("het han noi dung %d job, xoa %d file",
                 bao_cao["jobs"], bao_cao["files"])
    return bao_cao["jobs"]


def _don_du_lieu_het_han() -> None:
    """Run every declared retention rule once.

    Each store gets its own session and its own commit: one table whose purge
    fails must not stop the others, because the one that fails is usually the
    biggest, and the biggest is the one that most needs the others to succeed.

    The list here is checked against `governance.STORES` by
    `test_211_data_governance`, so adding a table with a retention class and
    forgetting to sweep it fails the suite rather than growing quietly.
    """
    from platform_core.public_api import (costing, idempotency, metrics,
                                          notifications, outbox, request_log,
                                          security_log)

    rules = (
        ("nhat ky request API", request_log.purge_expired),
        ("thong bao", notifications.purge_expired),
        ("su kien bao mat", security_log.purge_expired),
        ("quan sat chi phi", costing.purge_expired),
        ("ban ghi webhook da gui", outbox.purge_expired),
        ("ban ghi idempotency", idempotency.purge_expired),
        ("mau metrics", metrics.purge_expired),
        # Nội dung của job: file sinh ra + prompt + payload kết quả. Hàng `jobs`
        # ở lại (bằng chứng), nội dung thì hết hạn — trước đây cả hai chung một
        # số phận là giữ vĩnh viễn, nên kho file phình không trần.
        ("noi dung job het han", _don_noi_dung_job),
    )
    for label, purge in rules:
        try:
            for db in _one_session():
                gone = purge(db)
                db.commit()
                if gone:
                    log.info("don %d dong %s", gone, label)
        except Exception:  # noqa: BLE001 - housekeeping must not kill the worker
            log.exception("khong don duoc %s", label)


def _ghi_chi_phi(db, job) -> None:
    """Record what this job consumed, if the operator configured any rates.

    Never fatal: cost analytics is a business view, and a platform that failed
    a customer's job because it could not write an estimate would have its
    priorities exactly backwards.
    """
    from platform_core.public_api import costing

    try:
        costing.record_job(db, job)
    except Exception:  # noqa: BLE001
        log.exception("khong ghi duoc quan sat chi phi cho job %s", job.id[:8])


def _ket_qua_sandbox(job_id: str, params: dict):
    """Canned output for a test-mode job, or ``None`` for a live one.

    This is the single link test mode replaces. Everything before it — auth,
    scopes, validation, quoting, idempotency, the job row, the lease — and
    everything after it — settlement, artifacts, events, webhooks — is the same
    code a live call runs. A sandbox that skipped any of those would let an
    integration pass here and fail in production (EXT-12, decision D4).
    """
    from platform_core.public_api import sandbox
    from platform_core.public_api.catalog import build_catalog
    from platform_core.public_api.config import load_public_api_config
    from platform_core.storage import get_storage

    meta = (params or {}).get("_api")
    if not isinstance(meta, dict) or not sandbox.is_test(meta.get("mode")):
        return None

    name = str(meta.get("tool") or "")
    # Built for this one tool rather than read from process configuration: the
    # worker must answer the same shape whatever the API process happens to be
    # publishing right now, and the job already names its tool.
    config = load_public_api_config({"LTT_PUBLIC_API": "1",
                                     "LTT_PUBLIC_API_TOOLS": name})
    tool = next((item for item in build_catalog(config) if item.name == name),
                None)
    if tool is None:
        raise RuntimeError("sandbox job names a tool that is not published")

    log.info("job %s chay che do test: khong goi provider", job_id[:8])
    return sandbox.canned_result(tool, params, get_storage())


def _xa_metrics() -> None:
    """Đưa bộ đếm của tiến trình NÀY xuống CSDL.

    Cố ý **không** nằm trong vòng bảo trì: vòng đó chỉ chạy ở một tiến trình,
    còn bộ đếm thì mỗi tiến trình một bản. Để leader xả hộ nghĩa là mất số của
    mọi tiến trình còn lại — và mất một cách im lặng, vì tổng vẫn ra một con số
    trông hợp lý.
    """
    from platform_core.public_api import metrics

    for db in _one_session():
        n = metrics.flush(db, prefix=metrics.WORKER_PREFIX)
        db.commit()
        if n:
            log.debug("xa %d mau metrics", n)


def _ghi_metrics() -> None:
    """One line of counters. Cheap, and the only observability this needs."""
    from platform_core.public_api import metrics

    snapshot = metrics.snapshot()
    if snapshot["counters"]:
        log.info("public api metrics %s", snapshot)


#: Bao lâu thử giành lại lease bảo trì khi tiến trình khác đang giữ. Ngắn so với
#: TTL của lease, để chủ chết thì có người nhận trong một chu kỳ chứ không phải
#: chờ hết hạn rồi mới bắt đầu hỏi.
LEASE_RETRY_S = 20.0


def _mot_luot_bao_tri(moc: dict) -> None:
    """Chạy những việc nền đã đến hạn. `moc` giữ mốc thời gian giữa các lượt."""
    if time.monotonic() >= moc["event_purge"]:
        for db in _one_session():
            removed = job_events.purge_expired(db)
            db.commit()
            if removed[job_events.CUSTOMER] or removed[job_events.INTERNAL]:
                log.info("don job event het han: customer=%s internal=%s",
                         removed[job_events.CUSTOMER], removed[job_events.INTERNAL])
        # …and every other retention rule on the same visit. Each of these used
        # to be "somebody handles it"; writing the inventory in
        # `public_api/governance.py` showed that four of them nobody did, and
        # one had a purge function that was never called. A retention policy
        # naming a function nobody runs reads as a promise (EXT-19).
        _don_du_lieu_het_han()
        moc["event_purge"] = time.monotonic() + EVENT_PURGE_INTERVAL_S

    if time.monotonic() >= moc["upload_sweep"]:
        from platform_core import upload_sessions
        from platform_core.storage import get_storage
        for db in _one_session():
            report = upload_sessions.sweep(db, get_storage(), dry_run=False)
            db.commit()
            if report["due"] or report["errors"]:
                log.info(
                    "don upload het han: due=%s deleted=%s errors=%s active=%s",
                    report["due"], report["deleted"], report["errors"],
                    report["skipped_active"],
                )
        moc["upload_sweep"] = time.monotonic() + UPLOAD_SWEEP_INTERVAL_S

    if time.monotonic() >= moc["webhook"]:
        _giao_webhook()
        moc["webhook"] = time.monotonic() + WEBHOOK_DELIVERY_INTERVAL_S

    if time.monotonic() >= moc["metrics"]:
        _ghi_metrics()
        moc["metrics"] = time.monotonic() + METRICS_LOG_INTERVAL_S

    if time.monotonic() >= moc["alert"]:
        _quet_canh_bao()
        moc["alert"] = time.monotonic() + ALERT_SCAN_INTERVAL_S


def _vong_bao_tri(stop) -> None:
    """Việc nền, chạy ở ĐÚNG MỘT tiến trình, trong luồng riêng.

    Hai điều được sửa ở đây, và chúng khác nhau:

    **Đúng một tiến trình.** Trước đây mọi tiến trình worker đều chạy vòng này —
    mà số tiến trình mặc định bằng số GPU. Hai tiến trình nghĩa là mọi việc nền
    chạy hai lần, cùng lúc, vì chúng khởi động cùng nhau nên đồng hồ hẹn giờ
    trùng pha. Lease quyết định ai chạy; ai không giành được thì chỉ chạy job.

    **Luồng riêng.** Ngay cả khi chỉ một tiến trình chạy, vòng bảo trì vẫn xen
    *giữa các job* — nên một job năm phút làm webhook của mọi khách khác chờ năm
    phút. Con số "độ trễ webhook 4,71 ms" đo trước đây là của một hàng đợi rỗng.
    Việc nền ở đây là chờ mạng và chờ CSDL nên luồng là đúng hình dạng; việc
    nặng gọi CUDA giữ GIL thì đã nằm ở tiến trình riêng rồi.

    Mất lease thì **dừng ngay**. Tiếp tục làm sau khi mất quyền là đúng cái mà
    lease sinh ra để ngăn.
    """
    from platform_core import leases

    moc = {"event_purge": 0.0, "upload_sweep": 0.0, "webhook": 0.0,
           "metrics": 0.0, "alert": 0.0}
    lease = None
    while stop is None or not stop():
        try:
            if lease is None:
                for db in _one_session():
                    lease = leases.acquire(db, name=leases.MAINTENANCE)
                if lease is None:
                    time.sleep(LEASE_RETRY_S)
                    continue
                log.info("tien trinh nay chay vong bao tri")

            _mot_luot_bao_tri(moc)

            for db in _one_session():
                if not leases.heartbeat(db, lease):
                    log.warning("mat lease bao tri — dung viec nen")
                    lease = None
        except Exception:
            log.exception("loi trong vong bao tri, tiep tuc")
        time.sleep(POLL_INTERVAL_S)

    if lease is not None:
        try:
            for db in _one_session():
                leases.release(db, lease)
        except Exception:                       # noqa: BLE001
            log.exception("khong nha duoc lease bao tri")


def run_forever(worker_id: str, *, stop=None, maintenance: bool = True,
                capabilities=None) -> None:
    """Vòng lặp chính của worker. `stop` là callable trả True để dừng êm.

    Trước mỗi lượt rảnh, dọn job mồ côi — nhờ vậy một worker vừa khởi động lại
    sẽ tự nhặt lại job mà worker chết để lại, không cần ai can thiệp.

    `maintenance=False` cho một tiến trình **chỉ chạy job**. Việc nền vẫn được
    bảo vệ bằng lease dù cờ này bật ở mọi tiến trình — cờ là tiện nghi, lease
    mới là cơ chế.

    `capabilities` giới hạn tiến trình này chỉ nhặt job mà app khai
    `manifest.requires` nằm gọn trong tập đó. None nghĩa là đa năng.
    """
    log.info("worker %s bat dau%s", worker_id,
             f" (nang luc: {sorted(capabilities)})" if capabilities else "")

    luong = None
    if maintenance:
        luong = threading.Thread(target=_vong_bao_tri, args=(stop,),
                                 name=f"bao-tri-{worker_id}", daemon=True)
        luong.start()

    next_metrics_flush = time.monotonic() + METRICS_FLUSH_INTERVAL_S
    while stop is None or not stop():
        try:
            if time.monotonic() >= next_metrics_flush:
                _xa_metrics()
                next_metrics_flush = time.monotonic() + METRICS_FLUSH_INTERVAL_S
            for db in _one_session():
                n = jobq.reclaim_orphans(db)
                db.commit()
                if n:
                    log.warning("nhat lai %d job mo coi", n)
            co_viec = _chay_mot_job(worker_id, capabilities=capabilities)
            if not co_viec:
                time.sleep(POLL_INTERVAL_S)
        except Exception:
            # Một lượt hỏng không được giết cả worker — ngủ rồi thử lại.
            log.exception("loi trong vong worker, tiep tuc")
            time.sleep(POLL_INTERVAL_S)

    if luong is not None:
        luong.join(timeout=30)
    try:
        _xa_metrics()          # số của lượt cuối không được biến mất theo tiến trình
    except Exception:          # noqa: BLE001
        log.exception("khong xa duoc metrics luc dung")
    log.info("worker %s dung", worker_id)
