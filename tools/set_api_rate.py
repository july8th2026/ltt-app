r"""Nới trần nhịp (rate limit) của Public API qua **chính sách mặc định** trong CSDL.

    python -m tools.set_api_rate --create 6000 --read 12000 --write 12000 --jobs 50

⭐ VÌ SAO QUA CSDL CHỨ KHÔNG QUA BIẾN MÔI TRƯỜNG. `platform_core.public_api.policy
   .resolve()` đọc **chính sách mặc định** (`ApiPolicy.is_default`) ở **mỗi
   request**, nên đổi nó có tác dụng **NGAY**, không cần khởi động lại dịch vụ và
   không phải nướng lại biến môi trường vào NSSM (đường `LTT_PUBLIC_API_CREATE_RPM`
   chỉ ăn khi cài lại). Đây là cần gạt vận hành, không phải một lần deploy.

⛔ VÌ SAO TRẦN CAO Ở ĐÂY LÀ ĐÚNG, KHÔNG PHẢI LƠ LÀ. Trần `create_rpm=20` mặc định
   là để chặn LẠM DỤNG một Public API mở cho người lạ. Nhưng model nhà là **một
   khe** (single-slot) trên máy B: nó tự điều nhịp — bận thì trả 503, không phải
   nhận vô hạn. Và tiền tính theo **token thật sinh ra**, không theo số request.
   Nên với client agentic (Codex/Claude Code) của chính chủ, trần 20/phút chỉ
   biến một lượt làm-việc-thật thành bão retry → 429. Trần cao ở đây chỉ còn là
   **chốt chặn một vòng lặp chạy loạn**, không phải thước đo tải — tải do khe của
   B quyết.

⚠️ CHẠY TRÊN MÁY CHỦ, cần `LTT_DATABASE_URL` (nằm trong secrets\app.env):
       cd D:\LTTSTUDIOSAPP
       $env:LTT_DATABASE_URL = ...   # nạp từ app.env
       C:\LTTPlatform\venv\Scripts\python.exe -m tools.set_api_rate --create 6000

   Đảo lại về mặc định 20/120: `--create 20 --read 120 --write 120 --jobs 5`,
   hoặc xoá hẳn dòng chính sách trong trang admin (khi đó rơi về hằng số config).
"""
from __future__ import annotations

import argparse

from platform_core.db import get_session
from platform_core.public_api import policy


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--create", type=int, default=6000,
                    help="rpm_create — số lượt TẠO (mỗi stream/job) mỗi phút")
    ap.add_argument("--read", type=int, default=12000, help="rpm_read")
    ap.add_argument("--write", type=int, default=12000, help="rpm_write")
    ap.add_argument("--jobs", type=int, default=50,
                    help="max_active_jobs — trần đồng thời")
    ap.add_argument("--name", default="agentic-mac-dinh",
                    help="tên chính sách (khi tạo mới)")
    a = ap.parse_args(argv)

    gen = get_session()
    db = next(gen)
    try:
        hien = policy.default_policy(db)
        if hien is None:
            row = policy.create_policy(
                db, name=a.name, is_default=True,
                description="Tran nhip cao cho client agentic (set_api_rate.py)",
                rpm_create=a.create, rpm_read=a.read, rpm_write=a.write,
                max_active_jobs=a.jobs)
            act = "TAO MOI"
        else:
            row = policy.update_policy(
                db, hien, rpm_create=a.create, rpm_read=a.read,
                rpm_write=a.write, max_active_jobs=a.jobs)
            act = "CAP NHAT"
        db.commit()
        print(f"[OK] {act} chinh sach mac dinh '{row.name}':")
        print(f"      rpm_create     = {row.rpm_create}")
        print(f"      rpm_read       = {row.rpm_read}")
        print(f"      rpm_write      = {row.rpm_write}")
        print(f"      max_active_jobs= {row.max_active_jobs}")
        print("      -> co tac dung NGAY (resolve doc moi request), khong can restart.")
        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"[LOI] khong dat duoc chinh sach: {type(exc).__name__}: {exc}")
        return 1
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
