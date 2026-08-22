"""
jobs.py — sổ trạng thái job trong tiến trình, và idempotency.

Trạng thái dùng ĐÚNG bộ tên của bộ build pack (bước 08), không đặt tên mới:

    queued · preparing · generating · saving · completed · failed · cancelled

⭐ IDEMPOTENCY LÀ BẮT BUỘC, KHÔNG PHẢI TỐI ƯU. Một ảnh ở cấu hình chất lượng mất
   2,5–6 phút GPU (D-010). Worker của nền tảng chết giữa chừng rồi job chạy lại mà
   ta vẽ lần hai là đốt thêm 6 phút GPU và có thể tính tiền hai lần.

⭐ Khoá idempotency là `job_id` của NỀN TẢNG, không phải một id do cổng tự sinh —
   chỉ nền tảng mới biết hai lần gọi có phải cùng một job hay không.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

QUEUED = "queued"
PREPARING = "preparing"
GENERATING = "generating"
SAVING = "saving"
COMPLETED = "completed"
FAILED = "failed"
CANCELLED = "cancelled"

#: Trạng thái đã chốt — không đổi được nữa, và trả thẳng từ bộ nhớ khi gọi lại.
KET_THUC = frozenset({COMPLETED, FAILED, CANCELLED})


@dataclass
class Job:
    job_id: str
    prompt_id: str
    status: str = QUEUED
    #: Khoá ảnh trên R2 sau khi đã đẩy xong. Thứ tự giữ nguyên như lúc yêu cầu.
    image_keys: list[str] = field(default_factory=list)
    error_code: str = ""
    error_message: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    #: Số bước đã chạy / tổng, nếu biết. Chỉ có cho job của chính ta.
    progress: Optional[tuple[int, int]] = None

    def as_dict(self) -> dict:
        ra = {
            "job_id": self.job_id,
            "status": self.status,
            "image_keys": list(self.image_keys),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.error_code:
            ra["error"] = {"code": self.error_code, "message": self.error_message}
        if self.progress:
            ra["progress"] = {"value": self.progress[0], "max": self.progress[1]}
        return ra


class JobStore:
    """Sổ job trong bộ nhớ, an toàn với nhiều luồng.

    ⚠️ CỐ Ý KHÔNG BỀN QUA KHỞI ĐỘNG LẠI. Nguồn chân lý về job là CSDL của máy A
    (Q102: không dựng hàng đợi thứ hai). Sau khi cổng khởi động lại, kết quả cũ
    vẫn lấy lại được vì `prompt_id` sinh ổn định từ `job_id` và ComfyUI còn giữ
    `/history` — xem `comfy.prompt_id_for`.
    """

    def __init__(self, now: Callable[[], float]):
        self._now = now
        self._lock = threading.RLock()
        self._jobs: dict[str, Job] = {}

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def create_or_get(self, job_id: str, prompt_id: str) -> tuple[Job, bool]:
        """Trả `(job, la_moi)`. Gọi lại cùng `job_id` **không** tạo job thứ hai."""
        with self._lock:
            co = self._jobs.get(job_id)
            if co is not None:
                return co, False
            t = self._now()
            job = Job(job_id=job_id, prompt_id=prompt_id, created_at=t, updated_at=t)
            self._jobs[job_id] = job
            return job, True

    def set_status(self, job_id: str, status: str, **kw) -> Optional[Job]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if job.status in KET_THUC and status not in KET_THUC:
                # Không cho một luồng chậm chân ghi đè kết quả đã chốt.
                return job
            job.status = status
            for k, v in kw.items():
                setattr(job, k, v)
            job.updated_at = self._now()
            return job

    def fail(self, job_id: str, code: str, message: str) -> Optional[Job]:
        return self.set_status(job_id, FAILED, error_code=code,
                               error_message=str(message)[:500])

    def active_prompt_ids(self) -> set[str]:
        """`prompt_id` của những job cổng này đang giữ — dùng để tách việc của ta
        khỏi việc lạ trong hàng đợi ComfyUI (`busy.observe`)."""
        with self._lock:
            return {j.prompt_id for j in self._jobs.values() if j.status not in KET_THUC}

    def don_dep(self, giu_giay: float = 86400.0) -> int:
        """Bỏ job đã chốt và đã cũ. Trả số job đã bỏ."""
        moc = self._now() - giu_giay
        with self._lock:
            bo = [k for k, j in self._jobs.items()
                  if j.status in KET_THUC and j.updated_at < moc]
            for k in bo:
                del self._jobs[k]
            return len(bo)
