r"""
tai_ket_qua_job.py — tải tệp kết quả của một job về đĩa, để đem đi ĐO.

    ... tools\tai_ket_qua_job.py <job_id> --ra tmp\x.wav

Chạy qua một lớp nạp `app.env` (xem `setup\chay_thu_giong.ps1`).

⭐ Vì sao không tải bằng trình duyệt: đường `/jobs/{id}/artifacts/0` trả tệp cho
   NGƯỜI, và muốn lấy nó bằng script thì phải mang theo cookie phiên. Ở đây ta
   đã đứng trên máy chủ và đã có kho — đọc thẳng từ kho vừa ngắn hơn vừa không
   cần cầm một chứng danh nào.

⛔ Nó KHÔNG kiểm quyền sở hữu, vì nó không phải một cửa của khách. Đây là công
   cụ vận hành chạy trên máy chủ; đừng bọc nó thành route.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("job_id")
    ap.add_argument("--ra", required=True)
    a = ap.parse_args(argv)

    from sqlalchemy import select

    from platform_core.db import get_session
    from platform_core.models import Job
    from platform_core.storage import get_storage

    gen = get_session()
    db = next(gen)
    try:
        j = db.execute(select(Job).where(Job.id == a.job_id)).scalar_one_or_none()
        if j is None:
            print(f"khong thay job {a.job_id}", file=sys.stderr)
            return 2
        kq = j.result or {}
        khoa = kq.get("audio_key")
        if not khoa:
            print(f"job {a.job_id} khong co audio_key (status={j.status})",
                  file=sys.stderr)
            return 2
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    os.makedirs(os.path.dirname(os.path.abspath(a.ra)) or ".", exist_ok=True)
    with get_storage().open(khoa) as f:
        data = f.read()
    with open(a.ra, "wb") as f:
        f.write(data)
    print(f"{khoa} -> {a.ra} ({len(data)} byte)")
    for k in ("duration_s", "credit_cost", "so_doan", "phien_ban_gia"):
        if k in kq:
            print(f"  {k:<14} {kq[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
