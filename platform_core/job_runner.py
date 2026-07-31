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
import time
from typing import Optional

from platform_core import jobs as jobq
from platform_core.db import get_session
from platform_core.models import Job

log = logging.getLogger(__name__)

# Hàng đợi trống thì ngủ bao lâu trước khi hỏi lại. Đủ ngắn để job mới chạy
# gần như tức thì, đủ dài để không quay CPU khi rảnh.
POLL_INTERVAL_S = 2.0


class JobContext:
    """Tiện ích worker cấp cho handler: báo tiến độ (kèm đập nhịp).

    Mỗi lần `progress()` mở một transaction ngắn để ghi — nhờ vậy web thấy job
    nhích ngay, và heartbeat được cập nhật nên job đang chạy không bị coi là
    mồ côi.
    """

    def __init__(self, job_id: str):
        self.job_id = job_id

    def progress(self, percent: int, message: str = "") -> None:
        for db in _one_session():
            job = db.get(Job, self.job_id)
            if job is not None:
                jobq.set_progress(db, job, percent, message)
                db.commit()


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

    # 2. Chạy handler NGOÀI transaction claim (không giữ khoá suốt thời gian chạy).
    ctx = JobContext(job_id)
    try:
        handler = jobq.resolve_handler(job_type)
        result = handler(params, ctx)
        if not isinstance(result, dict):
            result = {"result": result}
    except Exception as exc:
        # 3a. Thất bại → fail() (có thể hẹn chạy lại).
        for db in _one_session():
            job = db.get(Job, job_id)
            if job is not None:
                jobq.fail(db, job, f"{type(exc).__name__}: {exc}")
                db.commit()
        log.warning("job %s that bai: %s", job_id[:8], exc)
        return True

    # 3b. Thành công → complete().
    for db in _one_session():
        job = db.get(Job, job_id)
        if job is not None:
            jobq.complete(db, job, result)
            db.commit()
    log.info("job %s xong", job_id[:8])
    return True


def run_forever(worker_id: str, *, stop=None) -> None:
    """Vòng lặp chính của worker. `stop` là callable trả True để dừng êm.

    Trước mỗi lượt rảnh, dọn job mồ côi — nhờ vậy một worker vừa khởi động lại
    sẽ tự nhặt lại job mà worker chết để lại, không cần ai can thiệp.
    """
    log.info("worker %s bat dau", worker_id)
    while stop is None or not stop():
        try:
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
