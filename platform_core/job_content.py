"""Hết hạn *nội dung* của một job, giữ nguyên *bằng chứng*.

Một hàng `jobs` chứa hai thứ khác hẳn nhau, và trước đây chúng chung một số phận
(giữ vĩnh viễn):

* **bằng chứng** — ai, khi nào, công cụ gì, tính bao nhiêu credit. Phải sống lâu
  hơn mọi tranh chấp hoá đơn, nên không có hạn;
* **nội dung** — prompt khách viết, payload kết quả, và **file sinh ra**. Không
  có lý do gì để giữ mãi, và giữ mãi là một khoản nợ về riêng tư lẫn chi phí.

Chính bảng phân loại trong `public_api/governance.py` đã nói phải tách hai thứ
này. Hàng `jobs` thì không tách — nên file kết quả của một API bán ảnh nằm lại
vĩnh viễn, không có store nào khai, không có sweep nào dọn, và khách không có
câu trả lời cho "tôi tải được artifact này trong bao lâu".

## Vì sao neo vào id của job

Ứng dụng tự dựng khoá lưu trữ theo quy ước ``{app}/{owner}/{job_id}/...``. Nền
tảng **không** đọc khoá theo quy ước đó rồi suy ra, mà chỉ nhận những giá trị
chuỗi trong ``params``/``result`` **có chứa id của chính job này**. Nếu phép
nhận dạng sai, cái sai nhất có thể xảy ra là bỏ sót một file — chứ không bao giờ
là xoá file của job khác. Với một thao tác không hoàn tác được, đó là hướng sai
duy nhất chấp nhận được.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from platform_core.models import Job

log = logging.getLogger(__name__)

#: Nội dung sống bao lâu sau khi job kết thúc. Đây là **lời hứa với khách** về
#: cửa sổ tải artifact, nên nó phải xuất hiện trong tài liệu công khai chứ không
#: chỉ ở đây.
RETENTION_DAYS = 30

#: Mỗi lượt quét dọn tối đa bao nhiêu job. Quét là việc nền chạy cạnh job thật;
#: một lượt xoá hàng chục nghìn file sẽ giữ phiên CSDL quá lâu.
BATCH = 200


def _now() -> datetime:
    return datetime.now(timezone.utc)


def content_keys(job: Job) -> list[str]:
    """Khoá lưu trữ mà job này sở hữu.

    Chỉ nhận chuỗi **có chứa id của job**. Xem docstring module: phép nhận dạng
    này được thiết kế để sai theo hướng bỏ sót, không phải theo hướng xoá nhầm.
    """
    khoa: list[str] = []
    job_id = str(job.id or "")
    if not job_id:
        return khoa

    def _quet(value) -> None:
        if isinstance(value, str):
            if f"/{job_id}/" in value and not value.startswith(("http://",
                                                                "https://")):
                khoa.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                _quet(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                _quet(item)

    _quet(job.result if isinstance(job.result, dict) else {})
    _quet(job.params if isinstance(job.params, dict) else {})
    # Giữ thứ tự nhưng bỏ trùng: cùng một khoá xuất hiện ở cả params lẫn result
    # là chuyện bình thường, và xoá hai lần sẽ đếm sai số file đã dọn.
    return list(dict.fromkeys(khoa))


def expire_content(db: DbSession, storage, job: Job, *,
                   now: datetime | None = None) -> int:
    """Xoá file và nội dung của một job, giữ lại hàng. Trả số file đã xoá.

    Hàng vẫn truy được, vẫn đối chiếu được hoá đơn; chỉ nội dung là hết hạn, và
    `content_expired_at` nói rõ điều đó — một trường rỗng không có lời giải
    thích sẽ bị đọc là mất dữ liệu.
    """
    da_xoa = 0
    for key in content_keys(job):
        try:
            storage.delete(key)
            da_xoa += 1
        except FileNotFoundError:
            # File đã biến mất là kết quả mong muốn, không phải lỗi.
            da_xoa += 1
        except Exception:                   # noqa: BLE001
            # Một file không xoá được không được chặn những file còn lại — và
            # job vẫn phải được đánh dấu, nếu không lượt sau sẽ thử lại mãi.
            log.exception("khong xoa duoc file %s cua job %s", key, job.id[:8])

    job.params = {}
    job.result = {}
    job.content_expired_at = now or _now()
    db.flush()
    return da_xoa


def purge_expired(db: DbSession, storage=None, *, days: int = RETENTION_DAYS,
                  limit: int = BATCH, now: datetime | None = None) -> dict:
    """Hết hạn nội dung của những job đã xong đủ lâu.

    Chỉ đụng job đã kết thúc: một job đang chờ hoặc đang chạy còn cần chính
    `params` của nó để chạy được.
    """
    from platform_core.models import JOB_CANCELLED, JOB_DONE, JOB_ERROR

    if storage is None:
        from platform_core.storage import get_storage
        storage = get_storage()

    current = now or _now()
    cutoff = current - timedelta(days=max(1, int(days)))
    rows = db.execute(
        select(Job)
        .where(Job.status.in_((JOB_DONE, JOB_ERROR, JOB_CANCELLED)),
               Job.content_expired_at.is_(None),
               Job.finished_at.is_not(None),
               Job.finished_at < cutoff)
        .order_by(Job.finished_at)
        .limit(max(1, int(limit)))
    ).scalars().all()

    bao_cao = {"jobs": 0, "files": 0}
    for job in rows:
        bao_cao["files"] += expire_content(db, storage, job, now=current)
        bao_cao["jobs"] += 1
    return bao_cao


__all__ = ["BATCH", "RETENTION_DAYS", "content_keys", "expire_content",
           "purge_expired"]
