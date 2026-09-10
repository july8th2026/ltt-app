"""Dọn nội dung `lttvideo` quá hạn (`C2`: 3 ngày). Chạy theo lịch trên máy A.

    py tools/don_lttvideo.py           # xem se dung toi bao nhieu job
    py tools/don_lttvideo.py --don     # don that

⛔ Mặc định là **xem thôi**. Hết hạn nội dung **không hoàn tác được**, nên nó
   không nên là hành vi mặc định của một script chạy theo lịch.

🔴 **Vì sao là một công cụ riêng chứ không nằm trong phép quét của nền tảng.**
   `platform_core/job_runner.py:_don_du_lieu_het_han()` giữ một tuple **cứng**
   các quy tắc lưu giữ, và `test_211_data_governance` chốt tuple ấy với
   `public_api/governance.py:STORES`. Nghĩa là **app không tự khai được hạn giữ
   của mình** — muốn thêm thì phải sửa `platform_core/` cộng bảng governance.

   Theo `CLAUDE.md`: *"Nếu thấy buộc phải sửa nền tảng thì dừng lại và nói rõ vì
   sao — đó là dấu hiệu hợp đồng app còn thiếu"*. Đây đúng là chỗ thiếu ấy, và
   nó được ghi ra thay vì lách đi im lặng.

   ⇒ Đường đúng về lâu dài: `AppManifest` khai `retention_days`, nền tảng gom
     các bản khai ấy vào phép quét chung. Đó là một thay đổi hợp đồng, làm riêng.

Đặt lịch trên Windows (mỗi ngày 03:00):

    schtasks /Create /TN "LTTV don video" /SC DAILY /ST 03:00 ^
      /TR "python D:\\LTTSTUDIOSAPP\\tools\\don_lttvideo.py --don"
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))


def main() -> int:
    from apps.lttvideo import features
    from platform_core.db import get_session

    that = "--don" in sys.argv
    gen = get_session()
    db = next(gen)
    try:
        if not that:
            # Chi DEM, khong dung toi. Dung chinh phep loc cua `don_het_han` de
            # con so o day va viec no lam khong the lech nhau.
            from datetime import datetime, timedelta, timezone

            from sqlalchemy import select

            from platform_core.models import (JOB_CANCELLED, JOB_DONE,
                                              JOB_ERROR, Job)

            moc = (datetime.now(timezone.utc)
                   - timedelta(days=features.GIU_NGAY))
            n = len(db.execute(
                select(Job).where(
                    Job.app_slug == "lttvideo",
                    Job.status.in_((JOB_DONE, JOB_ERROR, JOB_CANCELLED)),
                    Job.content_expired_at.is_(None),
                    Job.finished_at.is_not(None),
                    Job.finished_at < moc)
            ).scalars().all())
            print(f"[xem] {n} job qua han {features.GIU_NGAY} ngay. "
                  "Them `--don` de don that.")
            return 0
        ra = features.don_het_han(db)
        db.commit()
        print(f"[don] het han {ra['jobs']} job, {ra['files']} tep")
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
