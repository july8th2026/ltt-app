"""Quy tắc nghiệp vụ của `lttvideo` — hiện chỉ có một: **hạn giữ nội dung**.

📌 Ở `features.py` chứ không ở `routes.py`: hợp đồng app (`AGENTS.md` §8) nói
   route chỉ lo HTTP, nghiệp vụ ở `features.py` với app một miền.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)

#: `C2` — chủ dự án chốt 07/09: video giữ **3 ngày**.
#:
#: ⚠️ Nền tảng có hạn riêng, **30 ngày** (`platform_core.job_content
#: .RETENTION_DAYS`), áp cho **mọi** app. Ta ngắn hơn, nên phép quét của ta chạy
#: trước; phép quét của nền tảng sau đó chỉ thấy nội dung đã hết hạn rồi.
#:
#: ⛔ **KHÔNG** hạ hằng số toàn cục xuống 3: nó sẽ xoá sớm nội dung của mọi app
#:    khác — một thao tác không hoàn tác, làm thay người không hỏi.
GIU_NGAY = 3


def don_het_han(db, storage=None, *, gioi_han: int = 200,
                bay_gio: datetime | None = None) -> dict:
    """Hết hạn nội dung của job `lttvideo` đã kết thúc quá `GIU_NGAY`.

    ⭐ Dùng `platform_core.job_content.expire_content` chứ **không** tự xoá khoá
       R2. Hàm ấy chỉ đụng những chuỗi trong `params`/`result` **có chứa id của
       chính job đó**, nên cái sai tệ nhất có thể xảy ra là **bỏ sót** một tệp —
       không bao giờ là xoá tệp của job khác. Với một thao tác không hoàn tác,
       đó là hướng sai duy nhất chấp nhận được, và tự viết lại phép ấy là vứt bỏ
       chính đảm bảo đó.

    Trả `{"jobs": n, "files": m}`.
    """
    from sqlalchemy import select

    from platform_core.job_content import expire_content
    from platform_core.models import (JOB_CANCELLED, JOB_DONE, JOB_ERROR, Job)

    if storage is None:
        from platform_core.storage import get_storage

        storage = get_storage()

    gio = bay_gio or datetime.now(timezone.utc)
    moc = gio - timedelta(days=max(1, int(GIU_NGAY)))

    rows = db.execute(
        select(Job)
        .where(Job.app_slug == "lttvideo",
               Job.status.in_((JOB_DONE, JOB_ERROR, JOB_CANCELLED)),
               Job.content_expired_at.is_(None),
               Job.finished_at.is_not(None),
               Job.finished_at < moc)
        .order_by(Job.finished_at)
        .limit(max(1, int(gioi_han)))
    ).scalars().all()

    ra = {"jobs": 0, "files": 0}
    for job in rows:
        ra["files"] += expire_content(db, storage, job, now=gio)
        ra["jobs"] += 1
    if ra["jobs"]:
        log.info("lttvideo: het han noi dung cua %d job, %d tep",
                 ra["jobs"], ra["files"])
    return ra
