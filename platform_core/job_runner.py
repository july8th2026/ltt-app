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
import os
import threading
import time
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import select

from platform_core import jobs as jobq
from platform_core import job_events
from platform_core.db import get_session
# Nhập ở đầu tệp (⛔ không lười) vì `LEASE_RECLAIM_INTERVAL_S` dưới đây ĐỌC
# `HEARTBEAT_SECONDS` của nó thay vì gõ lại 60. `admission` chỉ phụ thuộc
# `db`/`models`, nên ⛔ không có vòng nhập.
from platform_core.llm import admission as _admission
from platform_core.i18n import N_
from platform_core.i18n import _ as _t
from platform_core.models import (JOB_CANCELLED, JOB_ERROR, JOB_RUNNING,
                                   Job)

log = logging.getLogger(__name__)

# Hàng đợi trống thì ngủ bao lâu trước khi hỏi lại. Đủ ngắn để job mới chạy
# gần như tức thì, đủ dài để không quay CPU khi rảnh.
#
# ⭐ Từ 25/09/2026 đây là **lưới an toàn**, không còn là độ trễ thường trực: một
#    job mới được xếp sẽ gọi worker dậy ngay qua `jobs.KENH_JOB_MOI`
#    (`_vong_nghe_job_moi`). ⛔ Đừng hạ con số này để "cho nhanh" — trên đội
#    hình thật của máy A là 8 tiến trình worker, hạ 2,0 → 0,5 nhân **bốn** số
#    lượt `reclaim_orphans` + `claim` chạy 24/7 lên cùng một PostgreSQL, để đổi
#    lấy đúng thứ mà đường đánh thức đã cho không.
POLL_INTERVAL_S = 2.0

#: Vòng `LISTEN` chờ bao lâu mỗi lượt trước khi hỏi lại `stop()`. ⛔ KHÔNG phải
#: độ trễ đánh thức (tin nhắn tới thì `notifies` trả về ngay) — chỉ là độ mịn
#: của việc dừng êm khi dịch vụ tắt.
NGHE_TIMEOUT_S = 5.0

# Nhịp báo "lease GPU còn sống". Phải NGẮN hơn nhiều so với
# `gpu_lease.ORPHAN_TIMEOUT` (10 phút), nếu không một job nặng sẽ bị coi là chết
# và mất card vào tay worker khác giữa chừng.
GPU_HEARTBEAT_S = 60.0

# Mọi GPU đều bận thì hoãn job bao lâu trước khi thử lại. Đủ dài để không quay
# vòng đốt CPU, đủ ngắn để người dùng không thấy job đứng im.
GPU_RETRY_DELAY_S = 20

#: Trần số lần hoãn vì tài nguyên trước khi job hỏng **hẳn và đọc được**.
#:
#: ⭐ Vì sao phải có trần (Task 23, 26/09/2026): hoãn ⛔ KHÔNG tăng `attempts` —
#:    cố ý, vì kẹt card ⛔ không phải lỗi của job. Nhưng hệ quả là một job bị bỏ
#:    đói có `attempts = 0`, `status = queued`, `next_run_at` nhích 20 giây một
#:    lần và CPU ≈ 0: nó ⛔ **không bao giờ hỏng hẳn**, nên nó ⛔ không bao giờ
#:    lộ ra. Một vòng lặp vô hạn IM LẶNG tệ hơn một lần hỏng thẳng — nó biểu hiện
#:    thành *"treo"*, và đã tốn một buổi chẩn đoán.
#:
#: Con số: 200 × `GPU_RETRY_DELAY_S` (20 s) ≈ **67 phút** bị bỏ đói liên tục.
#: Quá mức đó thì *"tài nguyên đang bận"* ⛔ không còn là lời giải thích hợp lý,
#: và một thất bại đọc được **kèm hoàn tiền** tốt hơn một job đứng im vô hạn.
#: ⚠️ Đếm theo số sự kiện `resource_wait` của job, tức đếm cả đời job.
TRAN_HOAN_TAI_NGUYEN = 200

#: Mã sự kiện của một lần tụt xuống CPU vì tiến trình ⛔ không dùng được CUDA.
#: Hằng số chứ ⛔ không phải chuỗi gõ lại ở hai nơi — `tests/test_151` đọc chính
#: hằng này, nên phép kiểm ⛔ không thể trôi khỏi mã.
EVENT_GPU_KHONG_DUNG_DUOC = "gpu_khong_dung_duoc"

EVENT_PURGE_INTERVAL_S = 6 * 60 * 60

#: Bao lâu quét `ExecutionLease` mồ côi một lần. **Bằng** `HEARTBEAT_SECONDS`
#: (60 s) — ⛔ không phải trùng ngẫu nhiên, nên hằng ấy được **đọc thẳng** chứ
#: không gõ lại: một watchdog chạy theo nhịp của **chính thứ nó canh**, và một
#: nhịp thiếu là bằng chứng duy nhất nó đi tìm.
#:
#: 🔴 VÌ SAO NÓ PHẢI CÓ TICKER RIÊNG (25/09/2026) — lỗi PHÂN LOẠI, ⛔ không phải
#:    lỗi chỉnh số. Trước đó `admission.reclaim_expired` nằm trong
#:    `_don_du_lieu_het_han()`, tức chạy theo `EVENT_PURGE_INTERVAL_S` = **6 giờ**:
#:
#:        6 h / ORPHAN_TIMEOUT_JOB (300 s)   =  72x
#:        6 h / ORPHAN_TIMEOUT_SYNC (120 s)  = 180x
#:
#:    Ca quan sát 25/09: lưới đỡ ⛔ không kích hoạt trong 17 phút — mà 17 phút chỉ
#:    là **4,7 %** chu kỳ, nên đó là ca **thường**, ⛔ không phải xui. Chờ xấu nhất
#:    ≈ 5 h 55′, trung bình ≈ 3 h; và 8 worker cùng bị một deploy restart thì pha
#:    trùng nhau, ⛔ không có lợi ích lệch pha.
#:
#: ⛔ ĐỪNG "sửa" bằng cách hạ `EVENT_PURGE_INTERVAL_S`: `6 giờ` ⛔ không sai cho
#:    việc dọn log request / thông báo / mẫu metrics — nó sai vì một **watchdog
#:    tính sống-chết** ⛔ không thuộc nhóm **lưu trữ dữ liệu**. Hạ nhóm ấy xuống
#:    60 s là bắt việc dọn log chạy **360 lần** nhiều hơn cần.
#:
#: ⚠️ VAI CỦA NÓ: **lưới đỡ**, ⛔ không phải cơ chế chính. Người dọn chính là
#:    đường nóng — `admission.acquire`/`_giu_slot_trong` gọi `reclaim_expired`
#:    trước khi giành slot, và từ 25/09 đường nóng **tới được** (bộ lọc suất của
#:    `jobs.claim` đọc cùng `admission.han_mo_coi`, nên lease chết ⛔ không còn
#:    giấu được job của chính tài nguyên nó). Cái này chỉ bắt phần đường nóng
#:    ⛔ không tới: tài nguyên ⛔ không có job nào xếp hàng sau nó. ⛔ Đừng nới nó
#:    lên vì "đường nóng đã dọn rồi" — cũng ⛔ đừng tưởng nó là cơ chế chính rồi
#:    hạ xuống nữa.
LEASE_RECLAIM_INTERVAL_S = _admission.HEARTBEAT_SECONDS
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
        # Trạng thái trần số dòng của `progress_counter` — sống theo ĐÚNG một
        # lượt chạy handler (một `JobContext` = một job/attempt), nên khỏi
        # phải khoá theo `(run_id, stage, attempt)` ở tầng gọi.
        self._progress_counter_last_ts = 0.0
        self._progress_counter_last_n = -1

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

    def progress_counter(self, da_xong: int, tong: int, *, don_vi: str = "",
                         nhip_giay: float = 30.0, nhip_don_vi: int = 5,
                         event_code: str = "progress_counter") -> bool:
        """Nhịp tiến độ TRONG một giai đoạn — mang BỘ ĐẾM, không chỉ dấu thời gian.

        Khác `progress()`: `percent` là bậc thang tuỳ ý cho khách; `da_xong/tong`
        là con số thật của công việc, và `job_events.append_progress_counter`
        NÉM nếu thiếu — một nhịp tim lease chứng minh TIẾN TRÌNH còn sống,
        ⛔ không chứng minh VIỆC đang tiến (`advance` 37.010 lượt/52 phút là ví
        dụ: còn sống và quay tại chỗ).

        Trần số dòng: chỉ ghi khi CẢ HAI `nhip_giay` giây VÀ `nhip_don_vi` đơn vị
        đã trôi qua kể từ lần ghi trước (`is_first`/`is_last` luôn ghi) — lấy
        hợp của hai ngưỡng nghĩa là lấy đường THƯA hơn, không phải dày hơn.
        Trả `False` khi bị nén (không ghi), không phải lỗi.
        """
        da_xong = int(da_xong)
        tong = int(tong)
        now = time.monotonic()
        la_dau = self._progress_counter_last_n < 0
        la_cuoi = tong > 0 and da_xong >= tong
        du_giay = (now - self._progress_counter_last_ts) >= nhip_giay
        du_don_vi = (da_xong - max(self._progress_counter_last_n, 0)) >= nhip_don_vi
        if not (la_dau or la_cuoi or (du_giay and du_don_vi)):
            return False
        for db in _one_session():
            job = db.get(Job, self.job_id)
            if job is not None:
                if job.status == JOB_CANCELLED:
                    raise JobCancelled()
                job_events.append_progress_counter(
                    db, job, da_xong=da_xong, tong=tong, don_vi=don_vi,
                    event_code=event_code)
                from datetime import datetime, timezone
                job.heartbeat_at = datetime.now(timezone.utc)
                db.commit()
                self._progress_counter_last_ts = now
                self._progress_counter_last_n = da_xong
                return True
        return False

    def provider_dispatched(self, provider: str = "") -> None:
        """Ghi bền ngay trước outbound HTTP để crash không retry side effect mù."""
        for db in _one_session():
            job = db.get(Job, self.job_id)
            if job is not None:
                jobq.mark_provider_dispatched(db, job, provider)
                db.commit()

    def provider_rejected(self, provider: str = "") -> None:
        """Gỡ ambiguity khi provider đã trả phản hồi xác định trước fallback."""
        for db in _one_session():
            job = db.get(Job, self.job_id)
            if job is not None:
                jobq.mark_provider_rejected(db, job, provider)
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
    user_id = ""
    for db in _one_session():
        job = jobq.claim(db, worker_id=worker_id,
                         capabilities=capabilities)
        if job is None:
            db.commit()
            return False
        job_id, job_type, params = job.id, job.job_type, dict(job.params)
        user_id = job.user_id
        chup_tai_nguyen = job.admission_resource or ""
        chup_suat = int(job.admission_slots or 0)
        db.commit()

    # Vòng lặp trên hoặc `return False`, hoặc gán đủ ba biến — nhưng `_one_session()`
    # là generator nên mypy không thấy được điều đó và coi cả ba còn `| None` suốt
    # phần còn lại của hàm (hơn 20 lỗi `arg-type`, và chúng che mất lỗi thật).
    # Đây là một lối thoát CÓ THẬT, không phải chiều lòng bộ kiểm: nếu generator
    # phiên không sinh vòng nào (DB chết lúc mở phiên) thì ba biến thật sự vẫn là
    # `None`, và chạy tiếp sẽ là `TypeError` ở một dòng ngẫu nhiên phía dưới.
    if job_id is None or job_type is None or params is None:
        log.warning("worker %s: phien DB khong sinh vong nao, bo luot nhat", worker_id)
        return False

    log.info("worker %s nhat job %s (%s)", worker_id, job_id[:8], job_type)

    # 1a. Sức chứa admission của job này — THEO MODEL nó xin (multijob 2.2).
    #
    # 🔴 BẢN KHAI CỦA TOOL ĐI TRƯỚC, VÀ NÓ TRẢ LỜI THEO MODEL. Hai cột
    #    `job.admission_resource/slots` được ghi lúc NỘP, tức trước khi ai biết
    #    `params["model"]` dẫn tới pool nào; với `text.chat` phục vụ hai model
    #    trên hai pool KV khác nhau, một con số chốt lúc nộp là con số của model
    #    *khác*.
    #
    # ⭐ NHƯNG BẢN CHỤP LÚC NỘP KHÔNG BỊ VỨT — có app cố ý dùng nó, và vứt đi là
    #    gỡ một chốt an toàn thật. `auto_scan_video` khai sức chứa theo **giai
    #    đoạn pipeline** chứ không theo tool (`apps/auto_scan_video/manifest.py`
    #    viết thẳng: *"Tai nguyen admission duoc chup luc nop job… vi no la
    #    thuoc tinh cua mot lan chay chu khong phai cua ca app"*), nên ToolSpec
    #    của nó không khai gì. Lấy bản khai của tool làm câu trả lời DUY NHẤT sẽ
    #    cho giai đoạn `tach_nguon_cuc_bo` (demucs, `suat=1`) chạy **không
    #    lease** — tức nhiều `demucs` cùng lúc, đúng sự cố đã làm máy chết.
    #
    # ⇒ Luật: tool khai gì thì tool thắng (và thắng THEO MODEL); tool không khai
    #   gì (`None`) thì bản chụp lúc nộp là câu trả lời. Mọi app hiện có rơi vào
    #   đúng một trong hai nhánh ấy với **cùng con số như trước 2.2**.
    try:
        suc = _suc_chua_job(job_type, params)
    except KeyError as e:
        # Fail-closed, và fail MỘT LẦN: `params["model"]` không có trong bản khai
        # của tool là sai vĩnh viễn, nên trả về hàng đợi chỉ tạo một vòng lặp
        # tiêu slot. Hỏng hẳn + hoàn tiền là kết cục đúng.
        _hong_khai_bao_model(job_id, job_type, str(e))
        return True
    admission_resource = suc.resource if suc is not None else chup_tai_nguyen
    admission_slots = int(suc.slots) if suc is not None else chup_suat

    # 1b. Giành slot của tài nguyên từ xa TRƯỚC GPU cục bộ. Nếu máy B đang bận,
    # không được giữ card trên worker chỉ để ngồi chờ một tài nguyên khác.
    from platform_core.llm import admission, dieu_phoi, tham_so_da_luot
    from contextlib import nullcontext
    try:
        luat = (_luat_cho_job(job_type, params, suc)
                if admission_resource and admission_slots > 0 else {})
    except tham_so_da_luot.DatChoVuotPool as e:
        # Phương án C bất biến 1: đặt chỗ vượt cả pool KV thì KHÔNG BAO GIỜ được
        # nhận — hỏng hẳn + hoàn tiền; không hoãn lại mãi, không kẹp im lặng.
        _hong_khai_bao_model(job_id, job_type, str(e),
                             thong_diep="Job vuot ngan sach ngu canh cua model.")
        return True
    execution = (
        admission.hold_persisted(
            resource=admission_resource, slots=admission_slots,
            user_id=user_id, mode="job", holder_id=job_id, job_id=job_id,
            **luat)
        if admission_resource and admission_slots > 0
        else nullcontext(True)
    )
    with execution as execution_lease:
        if execution_lease is None:
            _tra_ve_hang_doi(job_id, job_type, resource=admission_resource)
            return True

        # 1c. Giành GPU nếu loại job này khai cần (H23), rồi mới chạy handler.
        need_mb = _vram_can(job_type)
        with _giu_gpu(worker_id, job_id, job_type, need_mb) as (lease, het_gpu):
            if het_gpu:
                _tra_ve_hang_doi(job_id, job_type, resource="gpu")
                return True

            _mark_job_admitted(job_id)
            # 2. Chạy handler NGOÀI transaction claim.
            ctx = JobContext(job_id, gpu_uuid=(lease.gpu_uuid if lease else ""))
            from platform_core.job_ingress import trusted_scope

            # O-05: số đặt chỗ của lease đi lên máy B (`X-LTT-Token-Dat`) cùng
            # mọi lời gọi `dieu_phoi` của handler — cùng số hai sổ đếm.
            with trusted_scope("worker", "internal"), dieu_phoi.mang_dat_cho(
                    int(getattr(execution_lease, "token_dat_truoc", 0) or 0)):
                return _chay_handler(worker_id, job_id, job_type, params, ctx)


def _tool_cua_job(job_type: str):
    """`ToolSpec` khai `job_type` này. `None` khi không tìm được / registry hỏng.

    Một vòng lặp, hai bên đọc (`_suc_chua_job` và `_luat_cho_job`) — trước 2.2
    mỗi bên tự quét `discover()` một lần, tức hai chỗ sẽ trôi khỏi nhau.
    """
    try:
        from platform_core.registry import discover
        for item in discover():
            if item.error:
                continue
            for t in item.manifest.tools:
                if t.job_type == job_type:
                    return t
    except Exception:  # noqa: BLE001 - registry hỏng: không đoán được bản khai
        log.exception("khong doc duoc tool cua %s", job_type)
    return None


def _suc_chua_job(job_type: str, params: dict):
    """`AdmissionModel` của job này theo `params["model"]` (multijob 2.2).

    `None` = tool không khai admission nào ⇒ job không giành lease, đúng hành vi
    cũ. Ném `KeyError` khi tool ĐÃ phân biệt theo model mà model job xin không
    có trong bản khai — fail-closed, xem `registry.suc_chua_admission`.
    """
    tool = _tool_cua_job(job_type)
    if tool is None:
        return None
    return tool.admission_cho(str((params or {}).get("model") or ""))


def _hong_khai_bao_model(job_id: str, job_type: str, ly_do: str, *,
                         thong_diep: str = "Job xin mot model tool khong khai.") -> None:
    """Job xin một model tool không khai ⇒ hỏng hẳn (`retry=False`) + hoàn tiền.

    ⛔ KHÔNG `_tra_ve_hang_doi`: đây không phải "tài nguyên đang bận" mà là bản
       khai và yêu cầu không khớp — hoãn lại chỉ để gặp đúng nó ở lượt sau, mãi
       mãi. Và KHÔNG chạy handler: chạy mà không giành lease là đúng cái lỗ
       `admission` sinh ra để bịt.
    """
    log.error("job %s (%s) xin model khong co trong ban khai: %s",
              job_id[:8], job_type, ly_do)
    for db in _one_session():
        job = db.get(Job, job_id)
        if job is not None and job.status not in (JOB_CANCELLED,):
            jobq.fail(db, job, thong_diep, retry=False)
            db.commit()
            _hoan_tien_neu_can(db, job)


def _luat_cho_job(job_type: str, params: dict, suc=None) -> dict:
    """Tham số đa lượt cho job NỀN (multijob D-03): lớp `nen` + phần đặt chỗ KV.

    `suc` = `AdmissionModel` đã giải theo model ở `_chay_mot_job` — ngân sách KV
    đi theo MODEL, không phải theo tool (multijob 2.2). Không khai pool ⇒ `{}`
    ⇒ đúng hành vi cũ.
    ⛔ Ước hỏng ⇒ đặt chỗ CẢ POOL (job chỉ chạy khi không ai khác chạy) — hướng AN
       TOÀN. Lùi về "đếm slot" thì lease vô hình với sổ ngân sách, và một job 150K
       lọt vào cạnh ba phiên dài là tràn pool ⇒ llama.cpp giết MỌI slot.
    """
    from platform_core.llm import luat_nhan, tham_so_da_luot

    tool = _tool_cua_job(job_type)
    if tool is None:
        return {}
    pool = int(suc.token_pool) if suc is not None else 0
    if pool <= 0:
        # 🔴 JOB ẢNH KHÔNG CÓ POOL KV, NHƯNG NÓ VẪN PHẢI MANG LỚP `nen`.
        #    Nó xin suất trên `anh_3090` (residency, `token_pool = 0`), nên nhánh
        #    này trả `{}` và lượt ấy đi tiếp với lớp mặc định `tuong_tac` — tức một
        #    job **nền** cạnh tranh như một lượt **khách đang ngồi đợi**, và luật
        #    "nền ≤ N−1 & nhường tương tác" thôi bảo vệ đúng thứ nó sinh ra để bảo vệ.
        #    (Task 5.3 đo được và chuyển sang — nghĩa vụ 2 của 5.5.)
        #
        # ⚠️ Điều kiện là `residency_group`, không phải tên app: `platform_core`
        #    không được biết app nào tồn tại (`test_147`). App **khai**, nền tảng đọc.
        return dict(lop=luat_nhan.NEN) if getattr(suc, "residency_group", "") else {}
    try:
        from platform_core.public_api.executor import for_tool
        ex = for_tool(tool)
        tin = list((params or {}).get("messages") or [])
        cong_cu = (params or {}).get("tools")
        vao = int(ex.estimate_input(tin, cong_cu) if cong_cu else ex.estimate_input(tin))
        ra = int((params or {}).get("max_tokens") or ex.mac_dinh_cho("job"))
        # O-24 (17/09): kẹp theo cửa sổ của ĐÚNG model (bí danh), không theo cửa
        # sổ hẹp nhất; và đếm ảnh vào đặt chỗ như mọi cửa khác.
        alias = str((params or {}).get("model") or "") or None
        ra = min(ra, int(ex.context_output_cap(vao, alias)))
        from platform_core.runtime_noi_bo.luong import dem_anh
        so_anh = dem_anh(params or {})
    except Exception:  # noqa: BLE001 - đặt chỗ cả pool là đường an toàn
        log.exception("khong uoc duoc token cua job %s — dat cho CA POOL", job_type)
        return dict(lop=luat_nhan.NEN, token_pool=pool, token_dat_truoc=pool)
    # Ngoài `try`: `DatChoVuotPool` (và bản khai thiếu đệm ước) là LỖI THẬT, không
    # phải "ước hỏng" — đặt chỗ cả pool ở đây là kẹp im lặng (phương án C).
    return tham_so_da_luot.luat_cho(suc, lop=luat_nhan.NEN, token_vao_uoc=vao,
                                    xin_ra=ra, so_anh=so_anh)


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

    # ⭐ ĐỪNG XIN MỘT TÀI NGUYÊN MÌNH KHÔNG DÙNG ĐƯỢC (Task 23, đo 26/09/2026).
    #
    #    `nvidia-smi` thấy card ⛔ không có nghĩa tiến trình này dùng được card.
    #    Với `torch 2.11.0+cpu` thì `cuda.is_available() = False` mà `acquire`
    #    VẪN cấp lease, nên: `ctx.has_gpu = True` ⇒ handler bật `--buoc-gpu` ⇒
    #    `demucs_runner` trả `thieu_card` ⇒ giai đoạn hỏng trong ~0 giây ⇒ hoãn
    #    ⇒ **hoãn ⛔ không tính là một lần thử** ⇒ quay vòng VÔ HẠN, CPU ≈ 0.
    #
    # ⛔ `het_gpu=False`, ⛔ không phải True: hoãn ở đây là hoãn mãi mãi — thiếu
    #    CUDA ⛔ không tự lành ở lượt sau. Chạy CPU (chậm) và NÓI RA.
    dung_duoc, vi_sao = gl.gpu_mod.cuda_dung_duoc()
    if not dung_duoc:
        log.warning("job %s (%s) khai can %s MB VRAM nhung tien trinh nay KHONG "
                    "dung duoc CUDA (%s) — chay CPU, KHONG giu lease. Giu lease "
                    "roi hong trong 0 giay la mot vong lap vo han im lang.",
                    job_id[:8], job_type, need_mb, vi_sao)
        _khai_tut_ve_cpu(job_id, job_type, need_mb, vi_sao)
        yield None, False
        return

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
        nha_duoc = False
        try:
            nha_duoc = gl.release(db, lease)
        except Exception:                   # noqa: BLE001
            # Session này đã hỏng sau khi `commit` ném; `rollback` để `close`
            # bên dưới không ném thêm một lỗi che mất lỗi thật.
            try: db.rollback()
            except Exception: log.debug("rollback sau release loi cung loi")  # noqa: BLE001
            log.exception(
                "Khong tra duoc lease GPU cua job %s — dong lease se duoc "
                "`reclaim_orphans` thu hoi NGAY khi trang thai cuoi cua job "
                "hien ra trong CSDL (luat 'job da ket thuc'), KHONG cho het %s",
                job_id[:8], gl.ORPHAN_TIMEOUT)
        try: next(gen)
        except StopIteration: pass
        if not nha_duoc:
            _canh_lease_con_sot(job_id)


def _canh_lease_con_sot(job_id: str) -> int:
    """Đo BẤT BIẾN Ở BIÊN: rời `_giu_gpu` rồi thì job này ⛔ không được còn lease.

    ⭐ Một phép kiểm **cơ học** thắng một lời dặn dò. Trước Task 23 bất biến này
       chỉ nằm trong docstring của `gpu_lease.hold` (*"Quên trả lease thì GPU
       khoá tới khi hết hạn mồ côi"*) — nên khi nó vỡ, ⛔ không con số nào đổi và
       ⛔ không dòng log nào xuất hiện. Nó đã vỡ suốt một lượt nghiệm thu.

    ⚠️ Đo bằng một session SẠCH: chính session vừa ném ⛔ không phải người làm
       chứng đáng tin. Và ⛔ không bao giờ ném ra ngoài — đây là phép ĐO, làm chết
       một job vì phép đo là đổi một lỗi chậm thành một lỗi nhanh hơn.
    """
    from platform_core import gpu_lease as gl
    try:
        for db in _one_session():
            con = gl.lease_cua_job(db, job_id)
            if con:
                log.error("BAT BIEN VO: job %s da roi `_giu_gpu` ma con %d lease "
                          "(%s) — card dang bi giu cho mot job khong con chay",
                          job_id[:8], len(con),
                          ", ".join(x.gpu_uuid[:20] for x in con))
            return len(con)
    except Exception:                       # noqa: BLE001
        log.exception("khong do duoc bat bien lease cho job %s", job_id[:8])
    return 0


def _khai_tut_ve_cpu(job_id: str, job_type: str, need_mb: int, vi_sao: str) -> None:
    """Ghi lại một lần tụt xuống CPU, ở mức cảnh báo. ⛔ Không im lặng.

    ⭐ Docstring `demucs_runner.chon_thiet_bi` nói một lần tụt xuống im lặng *"tắc
       cả hàng đợi chứ không chỉ làm chậm một job"*, và cảnh báo đó **đúng**. Thứ
       Task 23 bỏ là **vòng lặp vô hạn**, ⛔ không phải sự phân biệt: giai đoạn
       vẫn chạy, nhưng mọi con số giây của nó là số CPU và người đọc phải biết.

    `visibility="internal"`: đây là câu kỹ thuật cho người vận hành (bản torch,
    driver), ⛔ không phải câu cho khách.
    """
    try:
        for db in _one_session():
            job = db.get(Job, job_id)
            if job is None:
                return
            job_events.append(
                db, job, EVENT_GPU_KHONG_DUNG_DUOC,
                details={"vi_sao": vi_sao, "vram_mb_da_khai": int(need_mb),
                         "job_type": job_type, "thiet_bi": "cpu"},
                level="warning", visibility="internal")
            db.commit()
    except Exception:                       # noqa: BLE001
        log.exception("khong ghi duoc su kien tut ve CPU cho job %s", job_id[:8])


def _tra_ve_hang_doi(job_id: str, job_type: str, *, resource: str = "gpu") -> None:
    """Đưa job về `queued` để chạy lượt sau, KHÔNG tính là một lần thử hỏng."""
    from platform_core.models import JOB_QUEUED
    from datetime import datetime, timedelta, timezone
    for db in _one_session():
        job = db.get(Job, job_id)
        if job is not None and job.status not in (JOB_CANCELLED,):
            so_hoan = _dem_hoan_tai_nguyen(db, job_id)
            if so_hoan >= TRAN_HOAN_TAI_NGUYEN:
                # ⛔ Không hoãn lần thứ `TRAN+1`: xem `TRAN_HOAN_TAI_NGUYEN`.
                log.error("job %s (%s) da hoan %d lan vi tai nguyen %r — qua "
                          "tran %d, cho hong han de co nguoi doc duoc",
                          job_id[:8], job_type, so_hoan, resource,
                          TRAN_HOAN_TAI_NGUYEN)
                jobq.fail(db, job,
                          f"Hoan {so_hoan} lan vi tai nguyen {resource!r} van "
                          f"khong chay duoc (tran {TRAN_HOAN_TAI_NGUYEN}). Job "
                          f"bi bo doi, khong phai loi xu ly.", retry=False)
                db.commit()
                _hoan_tien_neu_can(db, job)
                return
            job.status = JOB_QUEUED
            # App khai được thì dùng của app: 20 giây hợp với job render dài
            # hàng phút, và đốt 75% thông lượng của một job 5 giây (xem
            # `AppManifest.cho_tai_nguyen_s`).
            delay = _cho_tai_nguyen(job_type)
            job.worker_id = ""
            job.next_run_at = datetime.now(timezone.utc) + timedelta(
                seconds=delay)
            job_events.append(
                db, job, "resource_wait", public_message=N_("Đang chờ tài nguyên xử lý."),
                details={"delay_seconds": delay,
                         "status": JOB_QUEUED, "resource": resource}, level="warning",
            )
            db.commit()
    log.info("job %s (%s) hoãn %ss: tài nguyên %s đang bận",
             job_id[:8], job_type, _cho_tai_nguyen(job_type), resource)


def _dem_hoan_tai_nguyen(db, job_id: str) -> int:
    """Job này đã bị hoãn vì tài nguyên bao nhiêu lần. 0 nếu ⛔ không đọc được.

    ⚠️ Đếm sự kiện `resource_wait`, và sự kiện đó có **HAI người ghi**:
    `_tra_ve_hang_doi` ở đây (worker hoãn trước khi chạy) và
    `jobs.defer_resource` (handler ném lỗi tài nguyên giữa chừng). Đếm ở tầng sự
    kiện bắt được cả hai; đếm bằng một cột riêng chỉ bắt được một.

    ⛔ Lỗi đọc ⇒ trả 0 (fail-open): một `SELECT` hỏng ⛔ không được biến thành
       một job chết. Trần là lưới bắt vòng lặp vô hạn, ⛔ không phải một cửa.
    """
    from sqlalchemy import func

    from platform_core.models import JobEvent
    try:
        return int(db.execute(
            select(func.count()).select_from(JobEvent).where(
                JobEvent.job_id == job_id,
                JobEvent.event_code == "resource_wait")).scalar() or 0)
    except Exception:                       # noqa: BLE001
        log.exception("khong dem duoc so lan hoan cua job %s", job_id[:8])
        return 0


def _cho_tai_nguyen(job_type: str) -> int:
    """Giãn cách thử lại khi tài nguyên bận, theo khai báo của app.

    Không đọc được registry ⇒ dùng mặc định nền tảng. Một app hỏng manifest
    không được phép làm hỏng cả vòng worker.
    """
    try:
        from platform_core.registry import discover
        for item in discover():
            if item.error:
                continue
            if job_type in item.manifest.job_types:
                return item.manifest.cho_tai_nguyen_for(
                    job_type, default=GPU_RETRY_DELAY_S)
    except Exception:                       # noqa: BLE001
        log.exception("khong doc duoc gian cach cho tai nguyen cua %s", job_type)
    return GPU_RETRY_DELAY_S


def _mark_job_admitted(job_id: str) -> None:
    """Commit mốc admission trước handler để crash vẫn để lại queue delay thật."""
    for db in _one_session():
        job = db.get(Job, job_id)
        if job is not None:
            jobq.mark_admitted(db, job)
            db.commit()


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
    # ⭐ `run_id` (25/09): mot lan chay ASV nop hang chuc nghin job `advance`;
    #    tuong quan theo `job_id` cho tung manh roi, khong cho mot cau chuyen.
    #    Doc tu `params` — mot khoa quy uoc, khong rieng cua app nao — nen nen
    #    tang khong can biet truoc app nao dung no (rong voi app khong khai).
    run_id = str(params.get("run_id") or "") if isinstance(params, dict) else ""
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
                             worker_id=worker_id, correlation_id=correlation_id,
                             run_id=run_id),             _canh_gio(job_id, app_slug, job_type):
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
                jobq.mo_ta_loi(exc), limit=5000)
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
                    kind, retry_after = _provider_failure_kind(
                        exc, provider_state=job.provider_state)
                    if kind == "resource_wait":
                        jobq.defer_resource(
                            db, job, retry_after=retry_after,
                            resource=job.admission_resource)
                    elif kind == "loi_nguoi_goi":
                        # KHÔNG đụng `provider_state`: không provider nào từ
                        # chối cả — chính yêu cầu đã sai từ đầu.
                        jobq.fail(db, job, safe_error, retry=False)
                    elif kind == "rejected":
                        job.provider_state = jobq.PROVIDER_REJECTED
                        jobq.fail(db, job, safe_error, retry=False)
                    elif kind == "ambiguous":
                        jobq.mark_ambiguous(db, job, safe_error)
                    else:
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


def _provider_failure_kind(exc: Exception, *, provider_state: str) -> tuple[str, int]:
    """Phân loại có cấu trúc; lỗi không rõ sau dispatch luôn fail-safe."""
    from platform_core.llm.cong_vlm import (
        AmbiguousProviderError, BanError, ProviderOomError, VuotNganSachError)
    from platform_core.llm.dieu_phoi import KhongCoProviderNao

    # ⛔ ĐẶT TRƯỚC mọi phép phân loại provider. Lỗi của người gọi không phụ
    #    thuộc provider nào cả, và để nó rơi xuống nhánh mặc định `"retry"` là
    #    thử lại ba lần một việc không bao giờ thành công (xem `LoiNguoiGoi`).
    if isinstance(exc, jobq.LoiNguoiGoi):
        return "loi_nguoi_goi", 0
    # "Bận" có HAI cửa nói: `jobq.DangBan` là tín hiệu nền tảng mà app nào
    # cũng ném được (H43 Phase 04/05); `BanError` là lớp riêng của cổng VLM,
    # giữ nguyên để không đụng đường text đang bán. Cùng một nhánh, cùng một
    # số: về hàng đợi, không tiêu lượt thử, không chạm tiền.
    if isinstance(exc, (jobq.DangBan, BanError)):
        return "resource_wait", _cho_lai_s(exc)
    if isinstance(exc, KhongCoProviderNao) and exc.busy_only:
        return "resource_wait", 20
    if isinstance(exc, (VuotNganSachError, ProviderOomError)):
        return "rejected", 0
    if (isinstance(exc, AmbiguousProviderError)
            or provider_state == jobq.PROVIDER_DISPATCHED):
        return "ambiguous", 0
    return "retry", 0


def _cho_lai_s(exc: Exception) -> int:
    """Giây chờ trước khi hỏi lại một tài nguyên bận. Sàn 1; không khai ⇒ 20.

    `retry_after_s` rỗng nghĩa là cổng **không biết** còn bao lâu — và không
    biết thì không đoán lạc quan: 20 giây là giãn cách mặc định của nền tảng,
    đủ thưa để không thành máy bơm hỏi, đủ dày để một suất vừa nhả được nhặt.
    """
    try:
        cho = float(getattr(exc, "retry_after_s", None) or 0)
    except (TypeError, ValueError):
        cho = 0.0
    return max(1, int(cho or 20))


def _orphan_terminal(db, job) -> None:
    """Orphan đã terminal phải trả hold/webhook đúng một lần."""
    if job.status == JOB_ERROR:
        _hoan_credit(db, job)
        _enqueue_webhooks(db, job)


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

#: Nhịp quét giữ chỗ treo. Thưa hơn hẳn quét cảnh báo, và có lý do: một khoản
#: giữ chỗ chỉ được coi là treo sau `credit.TREO_SAU` (6 giờ), nên quét 15 phút
#: một lần chỉ là hỏi đi hỏi lại cùng một câu hỏi mà câu trả lời không thể đổi.
HOLD_SCAN_INTERVAL_S = 60 * 60

#: Nhịp đếm card. Thưa, vì một card rơi khỏi bus thì nó rơi luôn cho tới khi có
#: người cắm lại — hỏi mỗi phút không làm câu trả lời tới sớm hơn, chỉ làm
#: `nvidia-smi` bị gọi 60 lần thừa mỗi giờ trên một máy đang chạy job nặng.
GPU_COUNT_INTERVAL_S = 30 * 60

#: Số card máy này PHẢI có. Không đặt = tắt phép kiểm.
#:
#: ⛔ Không tự suy con số này. Hai cách "thông minh" đều sai:
#:    · đọc số card lúc khởi động ⇒ máy khởi động lại khi card đã rụng sẽ chốt
#:      mức thấp đó thành "bình thường", và cảnh báo im vĩnh viễn;
#:    · nhớ mức cao nhất từng thấy ⇒ một lần cắm thử card thứ ba làm máy báo
#:      thiếu mãi mãi.
#:    Con số này là một **tuyên bố về phần cứng**, nên nó phải do người khai.
GPU_MONG_DOI_ENV = "LTT_GPU_MONG_DOI"


def _quet_giu_cho_treo() -> int:
    """Tìm tiền của khách đang bị giữ mà không ai còn kết sổ được, rồi BÁO.

    🔴 Vì sao bước này tồn tại: đo trên production 2026-08-26 thấy **hai** khoản
       giữ chỗ ngày 24/08 không bao giờ được quyết toán hay hoàn. Cả hai nằm
       ngoài vòng đời job, nên `reclaim_orphans` không bao giờ nhìn thấy chúng.
       Trong hai lần đó **chỉ một** được người ghi lại — tỉ lệ phát hiện thủ
       công 1/2.

    ⛔ ~~CHỈ BÁO, KHÔNG TỰ HOÀN.~~ **Sửa 2026-08-29 (H41.3).** Câu cũ đúng cho
       tới khi chủ sản phẩm quyết; họ đã quyết là **có tự hoàn**. Bước này vẫn
       chỉ **báo**, nhưng nay có `_tu_hoan_giu_cho_treo()` chạy ngay sau nó.

    ⭐ Hai bước tách rời, và đó là chủ ý: chuông kêu ở **6 giờ**, tự hoàn ở
       **24 giờ**. Người trực thấy trước và còn 18 tiếng để bác bỏ một báo động
       giả. Gộp hai ngưỡng làm một nghĩa là máy hoàn trước khi ai kịp nhìn — mà
       sổ này **chỉ ghi thêm**, nên trả nhầm không xoá được, chỉ bù được.

    ⭐ Nằm trong `_mot_luot_bao_tri` chứ không phải trong vòng job: cả khối đó
       chạy dưới lease `bao_tri`, nên việc này chạy **đúng một lần trên toàn
       cụm** dù có bao nhiêu tiến trình worker. Đặt nhầm chỗ thì mỗi tiến trình
       gửi một thư về cùng một khoản tiền.
    """
    from platform_core import credit
    from platform_core.models import User
    from platform_core.public_api import notifications

    tong = 0
    for db in _one_session():
        treo = credit.giu_cho_treo(db)
        if not treo:
            return 0

        tien = sum(t.credit for t in treo)
        # Log trước, gửi thư sau: nếu hộp thư hỏng thì con số vẫn còn dấu vết.
        log.warning("GIU CHO TREO: %d khoan, %d credit cua khach dang bi giu "
                    "ma khong ai ket so duoc", len(treo), tien)

        nguoi_truc = db.execute(select(User).where(
            User.role == "admin", User.is_active.is_(True))).scalars().all()
        for t in treo:
            for ai in nguoi_truc:
                row = notifications.raise_alert(
                    db, user_id=ai.id, kind=notifications.HOLD_STRANDED,
                    # Khoá khử trùng lặp là chính khoản tiền đó: một khoản treo
                    # mãi không được báo mãi, và một khoản MỚI không bị im lặng
                    # chỉ vì khoản cũ vừa được báo.
                    subject=f"hold:{t.job_id or 'khong-khoa'}",
                    title=_t("Credit của khách đang bị giữ mà không ai kết sổ được"),
                    body=_t(
                        "Khoản giữ chỗ {credit} credit của tài khoản {user} "
                        "(khoá {khoa}, tạo lúc {luc}) không có quyết toán và "
                        "không có hoàn. Lý do: {ly_do}. Sổ credit CHỈ GHI THÊM "
                        "nên khoản này không tự lành — muốn trả lại cho khách "
                        "thì phải ghi một bút toán bù."
                    ).format(credit=t.credit, user=t.user_id[:8],
                             khoa=t.job_id or _t("(rỗng)"),
                             luc=t.tao_luc, ly_do=t.ly_do))
                if row is not None:
                    notifications.send_email_for(db, row)
                    tong += 1
        db.commit()
    return tong


def _tu_hoan_giu_cho_treo() -> int:
    """Hoàn những khoản treo quá `TU_HOAN_SAU`. Trả về số khoản đã hoàn.

    Tách khỏi `_quet_giu_cho_treo` chứ không gộp: hai bước có **hai ngưỡng khác
    nhau** (6 giờ để báo, 24 giờ để hoàn), và gộp chúng sẽ làm ngưỡng dài biến
    mất trong lần ai đó dọn mã.

    ⭐ Cũng nằm trong `_mot_luot_bao_tri` nên chạy dưới lease `bao_tri` — đúng
       một lần trên toàn cụm. `credit.hoan()` vốn idempotent theo job, nên kể cả
       lease hỏng thì tiền vẫn không trả hai lần; nhưng log sẽ nhân N, và một
       dòng log tiền nhân đôi là thứ làm người trực mất buổi tối để đối chiếu.
    """
    from platform_core import credit

    tong = 0
    for db in _one_session():
        da_hoan = credit.tu_hoan_treo(db)
        db.commit()
        tong = len(da_hoan)
    return tong


def _quet_canh_bao() -> None:
    """Raise the alerts that are true right now, and age out the old ones.

    Deduplication lives in `notifications.raise_alert`, so re-detecting the same
    condition on every pass is harmless by design — which is what lets this be a
    plain periodic scan instead of an event pipeline.
    """
    from platform_core.public_api import (alerting, costing, notifications,
                                          ops_alerts)
    from platform_core.public_api.config import load_public_api_config

    config = load_public_api_config()
    for db in _one_session():
        raised = alerting.scan_all(db, config=config)

        # 🔴 THEM 2026-08-26 — CHUONG NAY DA DUC TU LAU MA CHUA AI TREO.
        #
        #    `costing.scan_for_alerts` bao cho nguoi truc khi bien loi nhuan uoc
        #    tinh am. No co day du: docstring, test (`test_207`), ten trong
        #    `__all__`. Va cho toi hom nay **khong gi goi no** ngoai chinh test
        #    cua no — nen canh bao "dang ban lo" chua bao gio no tren production.
        #
        # ⛔ Do khong phai truong hop ca biet. Cung ngay, tim duoc mot ca thu hai
        #    y het (`usage.reconcile` dem giu cho mo coi, cung chi chay tu test +
        #    mot lenh CLI thu cong). Hai lan cung mot hinh dang: ham canh bao
        #    viet xong, khong cam vao dau, va trong y het mot ham dang chay.
        #
        # ⭐ Vi vay `test_307` chot bang `inspect.getsource` rang cac ham quet
        #    duoc GOI, khong chi ton tai.
        raised += len(costing.scan_for_alerts(db))

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
        _tham_relay_nexus()
        _tham_cong_vlm()
        # Sau `_tham_cong_vlm`, không thay nó: cổng có thể SỐNG mà model vẫn đang
        # bò trên CPU. Hai câu hỏi khác nhau, hai cảnh báo khác nhau.
        _tham_gpu_may_b(db)
        # Cùng một thân `/health`, cùng một họ lỗi: cổng trả lời ĐÚNG về chính
        # nó nhưng câu hỏi đã sai. Xem docstring `_tham_mo_coi_may_b`.
        _tham_mo_coi_may_b(db)
        # Cổng ẢNH là một dịch vụ KHÁC, trên cùng máy B. Nó chết thì cổng VLM vẫn
        # xanh, và ngược lại — nên nó cần phép thăm riêng (H37/L2).
        _tham_cong_render()
        _tham_gpu_anh(db)


def _tham_relay_nexus() -> bool:
    """Relay Nexus còn nghe không? Đếm khi im lặng để cảnh báo tự bắn.

    Vì sao cần: nền tảng có thể xanh hoàn toàn trong khi **không ai kết nối được
    tới máy nào** — relay là một tiến trình khác, trên một máy khác. Trước cái
    này, cách duy nhất biết relay chết là khách gọi điện.

    Chỉ mở một socket TCP rồi đóng: đủ để biết cổng còn nghe, không cần bí mật,
    không gửi gì. Đếm `nexus:relay_im_lang` cho ngưỡng ở `ops_alerts.NGUONG`.
    """
    import socket

    from platform_core import nexus

    if not nexus.enabled():
        return True
    dia_chi = os.environ.get("LTT_NEXUS_RELAY_HOST", "").strip()
    if not dia_chi:
        return True                      # chưa khai → không đoán, không báo
    cong = 21116
    if ":" in dia_chi:
        dia_chi, _, cong_raw = dia_chi.rpartition(":")
        try:
            cong = int(cong_raw)
        except ValueError:
            cong = 21116
    try:
        with socket.create_connection((dia_chi, cong), timeout=5):
            return True
    except OSError as exc:
        log.warning("relay nexus im lang tai %s:%s (%s)", dia_chi, cong,
                    type(exc).__name__)
        try:
            from platform_core.public_api import metrics

            metrics.increment("nexus:relay_im_lang")
        except Exception:                                       # noqa: BLE001
            log.warning("khong dem duoc nexus:relay_im_lang", exc_info=True)
        return False


def _tham_cong_vlm() -> bool:
    """Cổng VLM trên máy B còn trả lời không? Đếm khi im lặng để cảnh báo tự bắn.

    Cùng bài toán với `_tham_relay_nexus`, cùng lời giải: nền tảng có thể **xanh
    hoàn toàn** trong khi model ngôn ngữ nhà không phục vụ được ai — nó là một
    tiến trình khác, trên một máy khác. Trước cái này, cách duy nhất biết máy B
    chết là có người thử gọi rồi thấy hỏng.

    ⭐ Thăm `/live`, **không** `/health`: `/live` cố ý không cần bearer và cố ý
       không nói gì ngoài `{ok, version}`. Một phép thăm dò sống/chết không nên
       phải mang theo bí mật, và không nên đọc được trạng thái vận hành.

    ⛔ BẬN KHÔNG PHẢI IM LẶNG. Máy B trả 429 khi đang bận với việc ảnh hoặc video —
       đó là trạng thái **bình thường** của một máy chia GPU, và nó **không** được
       đếm vào đây. Chỉ đếm khi cổng không trả lời được. Lẫn hai thứ này thì người
       trực bị đánh thức mỗi tối dự án video chạy, và sẽ ngừng đọc cảnh báo.
    """
    goc = (os.environ.get("LTT_LLM_BASE_URL") or "").strip().rstrip("/")
    if not goc:
        return True                      # chưa khai → không đoán, không báo

    try:
        import httpx

        r = httpx.get(f"{goc}/live", timeout=5.0)
        if 200 <= r.status_code < 300:
            return True
        if r.status_code == 429:
            # ⛔ 429 nghĩa là CÓ AI ĐÓ TRẢ LỜI — tiến trình sống, chỉ đang bận.
            #    Đếm nó vào đây thì người trực bị đánh thức mỗi tối dự án video
            #    chạy, và sẽ ngừng đọc cảnh báo. Đó là cách làm hỏng một kênh
            #    cảnh báo cho tốt. (QT-2: bận ≠ hỏng.)
            #
            #    `/live` hôm nay không đi qua trọng tài nên không trả 429; chốt ở
            #    đây là để một bản sau đổi hành vi cũng không phá kênh cảnh báo.
            log.info("cong VLM tra 429 (ban) — con song, khong dem")
            return True
        # 404 VẪN ĐẾM: tiến trình trả lời nhưng không có `/live` nghĩa là bản
        # deploy trên máy B đã cũ — đó là một sự cố thật, chỉ khác kiểu.
        ly_do = f"HTTP {r.status_code}"
    except Exception as exc:                                    # noqa: BLE001
        ly_do = type(exc).__name__

    log.warning("cong VLM im lang tai %s (%s)", goc, ly_do)
    try:
        from platform_core.public_api import metrics

        metrics.increment("ltt_llm:cong_im_lang")
    except Exception:                                           # noqa: BLE001
        log.warning("khong dem duoc ltt_llm:cong_im_lang", exc_info=True)
    return False


def _tham_cong_render() -> bool:
    """Cổng ẢNH trên máy B còn trả lời không? (H37/L2)

    ⭐ VÌ SAO KHÔNG DÙNG CHUNG `_tham_cong_vlm`. Máy B chạy **hai dịch vụ khác
       nhau**: cổng VLM (:8299) và cổng render (:8199). Chúng khởi động riêng,
       chết riêng, và deploy riêng. Một cái xanh không nói gì về cái kia. Gộp làm
       một phép thăm là tự tạo ra một điểm mù đúng bằng nửa số dịch vụ.

    ⭐ Thăm `/live`, **không** `/health`: cùng lý do như cổng VLM — phép thăm dò
       sống/chết không nên phải mang theo bí mật.

    ⛔ BẬN KHÔNG PHẢI HỎNG, và ở đây nó còn dễ nhầm hơn bên VLM: cổng render trả
       429 mỗi khi dự án video chiếm card, và đó là **trạng thái bình thường
       hằng đêm** của máy B (D-005). Đếm nó vào đây thì người trực bị đánh thức
       mỗi tối, và sẽ ngừng đọc cảnh báo.
    """
    goc = (os.environ.get("LTT_RENDER_BASE_URL") or "").strip().rstrip("/")
    if not goc:
        return True                      # chưa khai → không đoán, không báo

    try:
        import httpx

        r = httpx.get(f"{goc}/live", timeout=5.0)
        if 200 <= r.status_code < 300:
            return True
        if r.status_code == 429:
            log.info("cong render tra 429 (ban) — con song, khong dem")
            return True
        # 404 VẪN ĐẾM: có người trả lời mà không có `/live` nghĩa là bản trên máy
        # B đã cũ hơn bản này — một sự cố thật, chỉ khác kiểu.
        ly_do = f"HTTP {r.status_code}"
    except Exception as exc:                                    # noqa: BLE001
        ly_do = type(exc).__name__

    log.warning("cong render im lang tai %s (%s)", goc, ly_do)
    try:
        from platform_core.public_api import metrics

        metrics.increment("ltt_image:cong_im_lang")
    except Exception:                                           # noqa: BLE001
        log.warning("khong dem duoc ltt_image:cong_im_lang", exc_info=True)
    return False


def _tham_gpu_anh(db) -> bool:
    """Model ẢNH có THẬT SỰ nằm trên card không? (H37/L3)

    Cùng bài toán, cùng lời giải, cùng cái máy như `_tham_gpu_may_b` — CUDA hỏng
    thì hỏng cho **mọi** hộ dùng chung card, không riêng LLM.

    ⚠️ Nhưng triệu chứng bên ảnh khó thấy hơn hẳn: một lượt vẽ vốn đã mất 96 giây,
       nên "chậm gấp hàng chục lần" trông giống hệt "máy đang bận" — đúng thứ ta
       đã dạy mọi người coi là bình thường.

    ⛔ KHÔNG đánh dấu lỗi cho khoá ở đây: đây là phép **quan sát**, không phải một
       lượt gọi thật, và `danh_dau_loi` sẽ tắt khoá model nhà sau 5 lần (D-005).
    """
    goc = (os.environ.get("LTT_RENDER_BASE_URL") or "").strip().rstrip("/")
    if not goc:
        return True

    try:
        from platform_core import api_keys, api_pool
        from platform_core.models import APIKEY_CAT_IMAGE

        key = api_pool.chon_key(db, category=APIKEY_CAT_IMAGE,
                                thu_tu_provider=["ltt_image"])
        token = api_keys.lay_credential(db, key)
    except Exception as exc:                                    # noqa: BLE001
        log.debug("bo qua tham GPU anh: khong lay duoc khoa (%s)",
                  type(exc).__name__)
        return True

    try:
        import httpx

        r = httpx.get(f"{goc}/health", timeout=8.0,
                      headers={"Authorization": f"Bearer {token}"})
        if r.status_code != 200:
            return True                  # `_tham_cong_render` đã lo phần chết/sống
        gpu = (r.json() or {}).get("gpu") or {}
    except Exception as exc:                                    # noqa: BLE001
        log.info("khong doc duoc /health cong render de kiem GPU: %s",
                 type(exc).__name__)
        return True

    if not gpu.get("dang_lo"):
        return True

    # `dang_lo` chỉ bật khi CHẮC CHẮN: đang vẽ đủ lâu mà VRAM vẫn thấp.
    log.error("model anh may B dang chay tren CPU, khong phai GPU: %s",
              gpu.get("ly_do") or f"VRAM {gpu.get('vram_dung_mb')} MB")
    try:
        from platform_core.public_api import metrics

        metrics.increment("ltt_image:tren_cpu")
    except Exception:                                           # noqa: BLE001
        log.warning("khong dem duoc ltt_image:tren_cpu", exc_info=True)
    return False


def _health_may_b(db) -> Optional[dict]:
    """Thân `/health` của cổng máy B, hoặc `None` nếu KHÔNG ĐỌC ĐƯỢC.

    ⭐ `None` nghĩa là **chưa biết**, không phải "bình thường". Mọi người gọi đều
       phải coi `None` là *im lặng*, đừng suy ra điều gì từ nó — đó là lý do hàm
       này trả `None` chứ không trả `{}`: một dict rỗng sẽ lặng lẽ đi qua mọi
       phép `.get()` phía sau và trông y hệt một máy B khoẻ mạnh.

    Tách ra vì **hai** phép thăm cùng cần thân này (`_tham_gpu_may_b` và
    `_tham_mo_coi_may_b`); gọi hai lượt HTTP cho cùng một endpoint trong cùng một
    vòng bảo trì là lãng phí, và tệ hơn là hai lượt đó có thể thấy **hai khoảnh
    khắc khác nhau** rồi kết luận mâu thuẫn nhau.
    """
    goc = (os.environ.get("LTT_LLM_BASE_URL") or "").strip().rstrip("/")
    if not goc:
        return None

    try:
        from platform_core import api_keys, api_pool
        from platform_core.models import APIKEY_CAT_CHAT

        key = api_pool.chon_key(db, category=APIKEY_CAT_CHAT,
                                thu_tu_provider=["ltt_llm"])
        token = api_keys.lay_credential(db, key)
    except Exception as exc:                                    # noqa: BLE001
        # Chưa cấu hình khoá `ltt_llm` → không đoán, không báo động. Nhưng ghi
        # lại: "im lặng" phải khác "biến mất", nếu không thì ngày khoá bị xoá
        # nhầm sẽ trông y hệt ngày mọi thứ bình thường.
        log.debug("bo qua tham may B: khong lay duoc khoa (%s)",
                  type(exc).__name__)
        return None

    try:
        import httpx

        r = httpx.get(f"{goc}/health", timeout=8.0,
                      headers={"Authorization": f"Bearer {token}"})
        if r.status_code != 200:
            return None                  # `_tham_cong_vlm` đã lo phần chết/sống
        return r.json() or {}
    except Exception as exc:                                    # noqa: BLE001
        # `_tham_cong_vlm` ngay trên đã lo phần chết/sống và đã đếm nếu cần, nên
        # ở đây KHÔNG đếm lần hai — nhưng vẫn ghi, để một `/health` hỏng theo
        # kiểu khác (JSON vỡ, timeout) không trôi qua không dấu vết.
        log.info("khong doc duoc /health may B: %s", type(exc).__name__)
        return None


def _tham_gpu_may_b(db) -> bool:
    """Model trên máy B có THẬT SỰ nằm trên card không, hay đang bò trên CPU?

    🔴 VÌ SAO CẦN MỘT PHÉP THĂM RIÊNG. Ngày 23/08 máy B tắt không sạch, CUDA hỏng
       cả máy, `llama.cpp` **lặng lẽ rơi về CPU** — và `_tham_cong_vlm` ở trên
       **vẫn xanh suốt**, vì `/live` trả `{"ok": true}` đúng như nó phải trả. Cổng
       sống thật; chỉ là thứ đằng sau nó chậm gấp hàng chục lần.

       Triệu chứng là **chậm**, không phải **lỗi**. Đó là loại hỏng mà mọi chốt
       sống/chết đều bỏ lọt, và nó đã chạy **hơn một giờ** trước khi tình cờ bị
       phát hiện trong lúc đo một việc khác.

    ⭐ PHẢI ĐỌC `/health`, NÊN PHẢI CÓ KHOÁ — và khoá lấy từ `api_pool`, chỗ duy
       nhất được phép giữ nó. Không có khoá thì **im lặng bỏ qua**: một cài đặt
       dev không có máy B, và đoán mò rồi báo động là cách làm hỏng kênh cảnh báo.

    ⛔ KHÔNG đánh dấu lỗi cho khoá ở đây. Đây là phép **quan sát**, không phải một
       lượt gọi thật; `danh_dau_loi` sẽ tắt khoá model nhà sau 5 lần (D-005).
    """
    than = _health_may_b(db)
    if than is None:
        return True
    gpu = than.get("gpu") or {}

    if not gpu.get("dang_lo"):
        return True

    # `dang_lo` chỉ bật khi CHẮC CHẮN: có model đang nạp mà VRAM lại thấp. Không
    # đo được thì nó là `None`, và `None` không phải `True`.
    log.error("model may B dang chay tren CPU, khong phai GPU: %s",
              gpu.get("ly_do") or f"VRAM {gpu.get('vram_dung_mb')} MB")
    try:
        from platform_core.public_api import metrics

        metrics.increment("ltt_llm:tren_cpu")
    except Exception:                                           # noqa: BLE001
        log.warning("khong dem duoc ltt_llm:tren_cpu", exc_info=True)
    return False


def _tham_mo_coi_may_b(db) -> bool:
    """Cổng máy B có đang là một tiến trình MỒ CÔI không?

    🔴 Đo 01/09: dừng vỏ bọc `nssm.exe` của `LTTLlmGateway` thì tiến trình con
       **sống sót**, vẫn giữ cổng 8299, vẫn trả `/health` = **200** — suốt 99
       giây, trong khi `Get-Service` nói `Stopped` và **không ai dựng nó dậy
       nữa**. Mọi chốt sống/chết đều xanh.

    ⭐ CÙNG HỌ VỚI `_tham_gpu_may_b` NGAY TRÊN, và đó là lý do nó nằm ở đây chứ
       không có một vòng lặp riêng. Cả hai đều là: **cổng trả lời đúng về chính
       nó, nhưng câu hỏi đã sai**. Bên kia hỏi *"anh có khoẻ không"* trong khi
       cần hỏi *"anh có đang chạy trên GPU không"*; bên này cần hỏi *"anh có NÊN
       đang chạy không"*.

    ⛔ KHÔNG dựng vòng nền thứ hai. `_mot_luot_bao_tri` chạy dưới lease nên mỗi
       việc trong đó chạy **đúng một lần trên toàn cụm**; một vòng tự dựng sẽ
       chạy ở **mọi** tiến trình worker và báo động trùng N lần (bài học H36).

    ⚠️ Cổng cũ **không có** trường `duoi_dich_vu` — thiếu nó là *chưa biết*, và
       chưa biết thì **im**. Nếu coi thiếu là "bình thường" thì một lần deploy
       hụt sẽ tắt vĩnh viễn phép thăm này mà không ai hay.
    """
    than = _health_may_b(db)
    if than is None:
        return True
    dd = than.get("duoi_dich_vu")
    if not isinstance(dd, dict) or dd.get("mo_coi") is not True:
        return True

    log.error("cong may B la tien trinh MO COI: vo boc dich vu (pid %s, sinh %s) "
              "da chet nhung tien trinh van chay va van giu cong. Khong ai dung "
              "no day neu no chet.", dd.get("vo_boc_pid"), dd.get("vo_boc_sinh"))
    try:
        from platform_core.public_api import metrics

        metrics.increment("ltt_llm:mo_coi")
    except Exception:                                           # noqa: BLE001
        log.warning("khong dem duoc ltt_llm:mo_coi", exc_info=True)
    return False


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

    # Thuê bao theo máy/tháng (Q98). Cũng gác sau cờ + sau lease (đang trong
    # `_quet_canh_bao`), vì trừ tiền mà chạy ở mọi tiến trình worker là trừ N lần.
    # Miễn phí (giá 0) thì hàm này không làm gì.
    from platform_core.nexus import billing

    ket = billing.thu_phi_thang(db)
    db.commit()
    if ket.get("tru") or ket.get("thieu_credit"):
        log.info("nexus thue bao: tru %d may, %d may thieu credit",
                 ket["tru"], ket["thieu_credit"])
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
    from platform_core import oauth_google
    from platform_core.llm import phong_cho
    from platform_core.workflow import su_kien as workflow_su_kien

    rules = (
        ("nhat ky request API", request_log.purge_expired),
        ("thong bao", notifications.purge_expired),
        ("su kien bao mat", security_log.purge_expired),
        ("quan sat chi phi", costing.purge_expired),
        ("ban ghi webhook da gui", outbox.purge_expired),
        ("ban ghi idempotency", idempotency.purge_expired),
        ("mau metrics", metrics.purge_expired),
        # ⛔ `admission.reclaim_expired` KHÔNG còn ở đây — nó là một watchdog tính
        #    sống-chết, ⛔ không phải một luật LƯU TRỮ, nên nó có ticker riêng
        #    (`LEASE_RECLAIM_INTERVAL_S`, `_quet_lease_mo_coi`). Xếp nó vào danh
        #    sách này là đã bắt nó chạy theo nhịp 6 giờ của việc dọn log — 72×
        #    hạn mà nó phải đỡ. Xem chú thích của hằng ấy.
        # Phòng chờ + sổ lượt LLM (multijob): chốt dòng chờ mồ côi, xoá sau 30 ngày.
        ("phong cho LLM", phong_cho.don_het_han),
        # Nội dung của job: file sinh ra + prompt + payload kết quả. Hàng `jobs`
        # ở lại (bằng chứng), nội dung thì hết hạn — trước đây cả hai chung một
        # số phận là giữ vĩnh viễn, nên kho file phình không trần.
        ("noi dung job het han", _don_noi_dung_job),
        # workflow_event cua run DA KET SO qua 90 ngay (spec Sec5.11).
        ("su kien workflow", workflow_su_kien.purge_expired),
        # Luot OAuth do dang (spec Sec9.3): song 10 phut. Hang qua han mang
        # mot PKCE verifier da ma hoa khong ai con can — giu lai la giu mot bi
        # mat qua han su dung cua chinh no.
        ("luot OAuth do dang", oauth_google.don_state_het_han),
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


def _quet_lease_mo_coi() -> int:
    """LƯỚI ĐỠ cho `ExecutionLease` của tiến trình đã chết. Trả số lease thu hồi.

    ⚠️ Người dọn CHÍNH là đường nóng (`admission.acquire`/`_giu_slot_trong` gọi
       `reclaim_expired` trước khi giành slot). Hàm này chỉ bắt phần đường nóng
       ⛔ không tới — tài nguyên mà lúc ấy ⛔ không có ai xin suất.

    ⛔ Lỗi ở đây ⛔ không được giết worker: đây là bảo trì, và một worker chết vì
       lượt dọn thất bại thì ⛔ không dọn được lần sau nữa.
    """
    thu = 0
    try:
        for db in _one_session():
            thu = _admission.reclaim_expired(db)
            db.commit()
        if thu:
            log.info("luoi do: thu hoi %d execution lease mo coi", thu)
    except Exception:  # noqa: BLE001 - bao tri khong duoc giet worker
        log.exception("khong quet duoc execution lease mo coi")
    return thu


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

#: Biên dao động quanh `LEASE_RETRY_S`, theo TỈ LỆ (0,25 = ±25 %).
#:
#: 🔴 **N-46 — vì sao một hằng số trần là một cơn bão.** 8 tiến trình worker của
#:    máy A (`api:6, gpu+ffmpeg:1, voice:1`) khởi động **cùng một lúc** từ một
#:    dịch vụ Windows. Cả 8 gọi `leases.acquire(MAINTENANCE)`; đúng một tiến
#:    trình thắng, 7 tiến trình thua, rồi cả 7 ngủ **đúng 20,000 s** và thức
#:    **cùng một giây**. Mỗi lượt thua không hề miễn phí: `reclaim_expired` +
#:    một `INSERT` vào `singleton_leases` va `UNIQUE(name)` ⇒ `IntegrityError`
#:    ⇒ `rollback`. Nên PostgreSQL nhận **7 `INSERT` hỏng trong cùng một giây,
#:    cứ 20 giây một lần, suốt đời tiến trình** — và vì hằng số không có nhiễu,
#:    các đồng hồ **không bao giờ tự lệch ra**: chúng đồng pha vĩnh viễn.
#:
#: ⭐ Thuốc là nhiễu, không phải một con số lớn hơn: nới `LEASE_RETRY_S` chỉ làm
#:    cơn bão thưa hơn mà vẫn đồng pha, và làm việc nhận lease sau khi chủ chết
#:    chậm đi. ±25 % rải 7 lượt kia trên một cửa sổ 10 giây ngay từ vòng đầu.
LEASE_RETRY_JITTER = 0.25


def _cho_lease_bao_tri() -> float:
    """Số giây chờ trước lượt giành lease bảo trì kế tiếp — CÓ nhiễu (N-46).

    Hàm riêng vì đây là chỗ duy nhất trong tệp có nhiều tiến trình *đồng pha từ
    lúc khởi động*, và một phép kiểm phải nói được "hai lượt gọi không bằng
    nhau" mà không cần dựng 8 tiến trình.
    """
    import random

    bien = LEASE_RETRY_S * LEASE_RETRY_JITTER
    return max(0.1, LEASE_RETRY_S + random.uniform(-bien, bien))


def _bao_tri_cac_app(moc: dict) -> None:
    """Gọi `manifest.bao_tri` của từng app khi tới hạn.

    Mỗi app có mốc riêng trong `moc`, nên app khai một giờ và app khai một ngày
    không kéo nhau.

    Bắt lỗi **theo từng app**: một app ném không được phép chặn app còn lại, và
    càng không được chặn phần bảo trì của nền tảng chạy sau nó. Đây là một trong
    số ít chỗ `except Exception` là đúng — người gọi là vòng lặp gốc, không có ai
    ở trên để xử lý, và im lặng bỏ qua thì hỏng sẽ không bao giờ lộ ra.
    """
    from platform_core import registry

    try:
        viec = registry.viec_bao_tri()
    except Exception:                            # noqa: BLE001
        log.exception("khong doc duoc danh sach viec bao tri cua app")
        return

    for slug, ham, moi_giay in viec:
        khoa = f"app:{slug}"
        if time.monotonic() < moc.get(khoa, 0.0):
            continue
        # Đặt mốc TRƯỚC khi chạy: hàm ném thì lượt sau vẫn phải chờ đủ giãn cách,
        # không quay lại ngay và ném lại mỗi vòng poll.
        moc[khoa] = time.monotonic() + moi_giay
        try:
            ham()
        except Exception:                        # noqa: BLE001
            log.exception("viec bao tri cua app %s that bai", slug)


def _so_gpu_mong_doi() -> int:
    """Số card khai ở `LTT_GPU_MONG_DOI`. 0 = không khai = tắt phép kiểm."""
    raw = (os.environ.get(GPU_MONG_DOI_ENV) or "").strip()
    if not raw:
        return 0
    try:
        return max(0, int(raw))
    except ValueError:
        # Khai sai còn tệ hơn không khai: người vận hành tưởng mình đã bật.
        log.warning("%s=%r khong phai so — bo qua phep kiem so GPU",
                    GPU_MONG_DOI_ENV, raw)
        return 0


def _quet_so_gpu() -> int:
    """Đếm card và báo động khi thiếu. Trả số card thấy được.

    🔴 VÌ SAO VIỆC NÀY CẦN TỒN TẠI. Liên kết driver của card thứ hai trên máy
       này mong manh (`oem3.inf` không liệt kê nó). Khi nó rụng thì **không có
       gì hỏng**: job vẫn chạy, chỉ là tất cả dồn vào một card. Năng lực giảm
       một nửa và mọi tín hiệu vẫn xanh — không ngoại lệ, không job đỏ, không
       cảnh báo. Cách duy nhất để biết là đi đếm card, đúng thứ không ai làm
       vào một ngày bình thường.

    ⭐ Nằm trong `_mot_luot_bao_tri` nên nó chạy dưới lease `bao_tri`, tức
       **đúng một lần trên toàn cụm**. Đặt trong vòng job thì mỗi tiến trình
       worker báo một lần về cùng một card.

    ⛔ CHỈ BÁO, KHÔNG TỰ SỬA. Cắm lại card hay nạp lại driver là việc chạm phần
       cứng của một máy đang phục vụ khách.
    """
    from platform_core import gpu as gpu_mod
    from platform_core.models import User
    from platform_core.public_api import notifications

    mong_doi = _so_gpu_mong_doi()
    if mong_doi <= 0:
        return -1                                # không khai ⇒ không kiểm

    thay = len(gpu_mod.list_gpus())
    if thay >= mong_doi:
        return thay

    # Log trước, gửi sau: hộp thư hỏng thì con số vẫn còn dấu vết.
    log.warning("THIEU GPU: thay %d card, khai %d o %s. Nang luc dang giam ma "
                "khong co gi bao loi.", thay, mong_doi, GPU_MONG_DOI_ENV)

    for db in _one_session():
        nguoi_truc = db.execute(select(User).where(
            User.role == "admin", User.is_active.is_(True))).scalars().all()
        for ai in nguoi_truc:
            notifications.raise_alert(
                db, user_id=ai.id, kind=notifications.GPU_MISSING,
                # Khoá khử trùng lặp mang chính CON SỐ: 1/2 và 0/2 là hai sự
                # việc khác nhau, và card thứ hai rụng không được im lặng chỉ
                # vì card thứ nhất vừa được báo hôm qua.
                subject=f"gpu:{thay}/{mong_doi}",
                title=_t("Máy chủ đang thiếu GPU"),
                body=_t(
                    "Đếm được {thay} card, cấu hình khai {mong_doi} "
                    "({bien}). Không có job nào hỏng vì việc này — chúng chỉ "
                    "dồn hết vào số card còn lại, nên thông lượng giảm mà mọi "
                    "tín hiệu khác vẫn xanh. Kiểm `nvidia-smi -L` trên máy; "
                    "nếu card không hiện thì đó là liên kết driver, không phải "
                    "phần mềm nền tảng."
                ).format(thay=thay, mong_doi=mong_doi, bien=GPU_MONG_DOI_ENV))
        db.commit()
    return thay


def _mot_luot_bao_tri(moc: dict) -> None:
    """Chạy những việc nền đã đến hạn. `moc` giữ mốc thời gian giữa các lượt."""
    # 🔴 TRỌNG TÀI CƯ TRÚ 3090 ĐI ĐẦU, VÀ NÓ KHÔNG CÓ ĐỒNG HỒ RIÊNG.
    #
    #    Đây là **mặt tiếp xúc duy nhất** của trọng tài với thế giới đang chạy
    #    (D01 B). Thiếu dòng này thì: không ai tạo dòng `gpu_residency`, luật 0
    #    `CHO_RESIDENCY` fail-closed ⇒ **mọi lượt `ltt-3.8` chờ hết ngân sách rồi
    #    429**, và job ảnh cũng không bao giờ được mở cửa. Cả hai cánh cùng đóng,
    #    và triệu chứng là *"3.8 bận mãi"* — một câu trỏ sai hướng hoàn toàn (R27).
    #
    # ⭐ Không đặt sau `moc[...]` nào: chu kỳ bảo trì đã là **2 giây**, và nhịp đó
    #    chính là nhịp trọng tài cần. Thêm một đồng hồ thứ hai là thêm một con số
    #    phải giữ đồng bộ với `t_nap_llm_s`/`cua_so_anh_s` mà không ai bắt khớp.
    #
    # ⛔ `buoc_dinh_ky` **không bao giờ ném** (nó tự khai thế và có phép kiểm ghim).
    #    Đó là điều kiện để nó được đứng ở đây: một ngoại lệ tại chỗ này sẽ cắt
    #    **phần còn lại** của lượt bảo trì (dọn dữ liệu, webhook, báo động).
    from platform_core.llm import residency as _residency

    _residency.buoc_dinh_ky()

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

    # ⭐ Ticker RIÊNG, ⛔ không nằm trong `_don_du_lieu_het_han` ở trên: đây là một
    #    watchdog (nhịp của thứ nó canh), ⛔ không phải một luật lưu trữ (nhịp của
    #    việc dọn log). Xem `LEASE_RECLAIM_INTERVAL_S`.
    if time.monotonic() >= moc["lease_reclaim"]:
        _quet_lease_mo_coi()
        moc["lease_reclaim"] = time.monotonic() + LEASE_RECLAIM_INTERVAL_S

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

    # Việc nền của từng app (hợp đồng: `AppManifest.bao_tri`). Nằm ở đây chứ
    # không để app tự dựng vòng lặp: cả khối `_mot_luot_bao_tri` chạy dưới lease
    # `bao_tri`, nên việc của app tự động chạy **đúng một lần trên toàn cụm** dù
    # có bao nhiêu tiến trình worker. App tự chạy vòng thu tiền sẽ trừ khách N
    # lần mỗi chu kỳ — xem chú thích ở `registry.AppManifest.bao_tri`.
    _bao_tri_cac_app(moc)

    if time.monotonic() >= moc["alert"]:
        _quet_canh_bao()
        moc["alert"] = time.monotonic() + ALERT_SCAN_INTERVAL_S

    # 🔴 Tiền của khách bị giữ mà không ai kết sổ được. Đặt SAU `_quet_canh_bao`
    #    và nhịp riêng, vì nó hỏi một câu khác hẳn: các cảnh báo trên nói về
    #    thứ đang xảy ra, cái này nói về thứ đã hỏng và đang nằm im.
    if time.monotonic() >= moc.get("hold_scan", 0.0):
        try:
            _quet_giu_cho_treo()
        except Exception:                        # noqa: BLE001
            # Một hộp thư hỏng hay một truy vấn chậm không được làm dừng việc
            # dọn dữ liệu và giao webhook ở trên.
            log.exception("quet giu cho treo that bai")
        # H41.3 — tự hoàn, NGƯỠNG DÀI HƠN (24h so với 6h ở trên). `try` riêng:
        # một lỗi ở đường tiền không được nuốt mất phần báo động vừa chạy xong,
        # và ngược lại.
        try:
            _tu_hoan_giu_cho_treo()
        except Exception:                        # noqa: BLE001
            log.exception("tu hoan giu cho treo that bai")
        moc["hold_scan"] = time.monotonic() + HOLD_SCAN_INTERVAL_S

    # ⭐ Đếm card. Không phải một phép kiểm sức khoẻ — máy vẫn khoẻ khi thiếu
    #    card, đó mới là vấn đề. Xem docstring của `_quet_so_gpu`.
    if time.monotonic() >= moc.get("gpu_count", 0.0):
        try:
            _quet_so_gpu()
        except Exception:                        # noqa: BLE001
            # `nvidia-smi` treo hay CSDL chậm không được làm dừng việc dọn dữ
            # liệu và giao webhook ở trên.
            log.exception("quet so gpu that bai")
        moc["gpu_count"] = time.monotonic() + GPU_COUNT_INTERVAL_S


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

    moc = {"event_purge": 0.0, "lease_reclaim": 0.0, "upload_sweep": 0.0,
           "webhook": 0.0, "metrics": 0.0, "alert": 0.0}
    lease = None
    while stop is None or not stop():
        try:
            if lease is None:
                for db in _one_session():
                    lease = leases.acquire(db, name=leases.MAINTENANCE)
                if lease is None:
                    time.sleep(_cho_lease_bao_tri())
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


def _cho_viec(bao_thuc: threading.Event, giay: float) -> None:
    """Ngủ tối đa `giay`, nhưng thức NGAY khi có job mới được xếp vào.

    Thay cho `time.sleep(POLL_INTERVAL_S)` ở lượt rảnh. Hai tính chất cần giữ:

    * **Không mất lượt.** Cờ được `set()` từ luồng nghe và chỉ `clear()` **sau**
      khi đã thức. Một tin nhắn tới trong lúc ta đang `claim` vẫn còn nguyên khi
      ta quay lại đây, nên lượt đó không chờ thêm một nhịp nào.
    * **Xấu nhất bằng hành vi cũ.** Không tin nhắn nào tới thì hàm này chính là
      `time.sleep(giay)`.
    """
    if bao_thuc.wait(giay):
        bao_thuc.clear()


def _vong_nghe_job_moi(bao_thuc: threading.Event, stop, url: str) -> None:
    """`LISTEN` kênh `jobs.KENH_JOB_MOI`; mỗi tin nhắn gọi vòng worker dậy.

    🔴 **Đây là ĐÁNH THỨC, không phải hàng đợi.** Luồng này không đọc nội dung
       tin nhắn, không chọn job, không ghi gì. Nó chỉ `set()` một cờ. Mọi phán
       quyết "job nào chạy ở đâu" vẫn nằm nguyên ở `jobs.claim` với
       `FOR UPDATE SKIP LOCKED`. Mất kết nối, mất tin nhắn, hay không có luồng
       này (SQLite) đều chỉ đưa worker về nhịp `POLL_INTERVAL_S` — tức đúng hành
       vi trước 25/09/2026, không có job nào bị bỏ.

    ⭐ **Kết nối RIÊNG, không lấy từ pool của `db.get_engine()`.** Một kết nối
       `LISTEN` bị giữ **suốt đời tiến trình**; lấy nó ra khỏi pool dùng chung là
       vĩnh viễn bớt một kết nối của việc thật. `NullPool` + `AUTOCOMMIT` vì
       `LISTEN` phải nằm ngoài transaction mới nhận được tin nhắn.

    Mất kết nối thì mở lại: PostgreSQL khởi động lại, hay tường lửa cắt một kết
    nối nằm không, không được làm worker mất đường đánh thức vĩnh viễn.
    """
    import sqlalchemy as sa
    from sqlalchemy.pool import NullPool

    from platform_core.db import _connect_args

    while stop is None or not stop():
        eng = None
        try:
            eng = sa.create_engine(url, future=True, poolclass=NullPool,
                                   isolation_level="AUTOCOMMIT",
                                   connect_args=_connect_args(url))
            with eng.connect() as conn:
                conn.exec_driver_sql(f"LISTEN {jobq.KENH_JOB_MOI}")
                raw = conn.connection.driver_connection
                if raw is None:                    # pragma: no cover
                    raise RuntimeError(
                        "khong lay duoc ket noi driver de LISTEN")
                # Một job có thể đã được xếp GIỮA lượt `claim` vừa rồi và câu
                # `LISTEN` này — khe cửa đó chỉ có ở lần mở đầu và sau mỗi lần
                # nối lại. Đánh thức một lượt để nó không bị bỏ qua.
                bao_thuc.set()
                log.info("nghe %s de danh thuc worker", jobq.KENH_JOB_MOI)
                while stop is None or not stop():
                    for _tin in raw.notifies(timeout=NGHE_TIMEOUT_S,
                                             stop_after=1):
                        bao_thuc.set()
        except Exception:                          # noqa: BLE001
            # ⛔ Không `exception()`: một PostgreSQL đang khởi động lại sẽ ghi
            #    một stack trace mỗi 5 giây vào log của 8 tiến trình.
            log.warning("mat duong danh thuc (%s) — quay ve nhip poll, se noi lai",
                        jobq.KENH_JOB_MOI)
            time.sleep(NGHE_TIMEOUT_S)
        finally:
            if eng is not None:
                try:
                    eng.dispose()
                except Exception:                  # noqa: BLE001
                    # ⛔ Không nuốt lặng: một `dispose` hỏng nghĩa là kết nối
                    #    `LISTEN` có thể còn treo ở PostgreSQL, và 8 tiến trình
                    #    rò mỗi lần nối lại thì tới lượt `max_connections`.
                    log.warning("khong dong duoc engine nghe job moi",
                                exc_info=True)


def _bat_dau_nghe(bao_thuc: threading.Event, stop,
                  worker_id: str) -> Optional[threading.Thread]:
    """Mở luồng nghe nếu CSDL là PostgreSQL. `None` nghĩa là chỉ còn nhịp poll.

    ⛔ Không ném: một worker phải chạy được trên SQLite (bộ test) và trên một
       máy chưa cấu hình CSDL xong, và trong cả hai trường hợp hành vi đúng là
       *y như trước khi có đường đánh thức*.
    """
    try:
        from platform_core.db import database_url
        url = database_url()
    except Exception as exc:                       # noqa: BLE001
        # CSDL chưa cấu hình là trạng thái MONG ĐỢI ở máy phát triển, nên đây là
        # `debug` chứ không `warning` — nhưng ⛔ không im: `run_forever` sẽ chạy
        # tiếp bằng nhịp poll, và người đọc log phải biết vì sao.
        log.debug("khong mo duoc duong danh thuc: %s", type(exc).__name__)
        return None
    if not url.startswith(("postgresql", "postgres")):
        return None
    try:
        luong = threading.Thread(
            target=_vong_nghe_job_moi, args=(bao_thuc, stop, url),
            name=f"nghe-job-{worker_id}", daemon=True)
        luong.start()
        return luong
    except Exception:                              # noqa: BLE001
        log.warning("khong mo duoc luong nghe job moi — chi con nhip poll")
        return None


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

    # 🔴 MOI `PATH` MOT LAN, ngay day, TRUOC moi job (N-59).
    #
    #    `ffmpeg` tren may nay cai theo NGUOI DUNG (WinGet) nen chi nam tren
    #    USER Path. Worker chay duoi `LocalSystem` => nhan MACHINE Path => moi
    #    tien trinh con goi `ffmpeg` TRAN deu nem `WinError 2`, va hong IM LANG
    #    o moi noi nguoi goi bat `Exception`.
    #
    #    ⭐ MOT lan o day du cho ca 63 cho (24 tep, `video_assembly` chiem 31):
    #    tien trinh con THUA KE `PATH`. ⛔ Dung di sua 63 cho — do la 63 lan lam
    #    viec ma mot lan da xong, va van bo sot cho thu 64.
    #    Banh coc `tools/check_ffmpeg_tran.py` chan cho thu 64.
    from platform_core import media as _media
    _media.bao_dam_ffmpeg_tren_path()

    luong = None
    if maintenance:
        luong = threading.Thread(target=_vong_bao_tri, args=(stop,),
                                 name=f"bao-tri-{worker_id}", daemon=True)
        luong.start()

    # ⭐ Cờ đánh thức là của RIÊNG lượt `run_forever` này, không phải biến module.
    #    Trên production mỗi làn là một tiến trình riêng nên hai cách giống nhau,
    #    nhưng bộ test (và `job_worker` đường một tiến trình) gọi `run_forever`
    #    trong LUỒNG: một cờ dùng chung thì `clear()` của luồng này ăn mất lượt
    #    thức của luồng kia, và hậu quả là "đôi khi chậm 2 giây" — thứ không ai
    #    truy ra được.
    bao_thuc = threading.Event()
    nghe = _bat_dau_nghe(bao_thuc, stop, worker_id)

    next_metrics_flush = time.monotonic() + METRICS_FLUSH_INTERVAL_S
    while stop is None or not stop():
        try:
            if time.monotonic() >= next_metrics_flush:
                _xa_metrics()
                next_metrics_flush = time.monotonic() + METRICS_FLUSH_INTERVAL_S
            for db in _one_session():
                n = jobq.reclaim_orphans(db, on_terminal=_orphan_terminal)
                db.commit()
                if n:
                    log.warning("nhat lai %d job mo coi", n)
            co_viec = _chay_mot_job(worker_id, capabilities=capabilities)
            if not co_viec:
                _cho_viec(bao_thuc, POLL_INTERVAL_S)
        except Exception:
            # Một lượt hỏng không được giết cả worker — ngủ rồi thử lại.
            # ⛔ Ở đây ngủ THẬT, không `_cho_viec`: một job mới không sửa được
            #    cái vừa ném ra, và thức sớm chỉ để ném lại là một vòng nóng.
            log.exception("loi trong vong worker, tiep tuc")
            time.sleep(POLL_INTERVAL_S)

    if nghe is not None:
        nghe.join(timeout=NGHE_TIMEOUT_S + 1.0)
    if luong is not None:
        luong.join(timeout=30)
    try:
        _xa_metrics()          # số của lượt cuối không được biến mất theo tiến trình
    except Exception:          # noqa: BLE001
        log.exception("khong xa duoc metrics luc dung")
    log.info("worker %s dung", worker_id)
