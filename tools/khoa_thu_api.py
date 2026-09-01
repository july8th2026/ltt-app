r"""
khoa_thu_api.py — phát một KHOÁ API cho tài khoản THỬ, để nghiệm thu `/api/v1`
bằng đúng đường mà một khách lập trình đi.

    powershell -ExecutionPolicy Bypass -File .\setup\khoa_thu_api.ps1

## Vì sao cần

Điều kiện qua V8 là *"gọi thật qua Cloudflare bằng khoá thật"*. Không có cách
nào kiểm điều đó mà không có một khoá — và khoá thì `platform_core.public_api
.keys` chỉ trả về **một lần**, không lấy lại được.

⭐ Đây không phải một đường vòng: `issue()` là đúng hàm mà cổng nhà phát triển
   gọi khi khách bấm "tạo khoá". Nó thừa hưởng mọi ràng buộc của cửa đó — trần
   số khoá mỗi tài khoản, pepper hiện hành, scope.

⛔ CHỈ CHO ĐUÔI `.local`. Một khoá API là một chứng danh sống, và nó **tiêu tiền
   thật** của chủ sở hữu. Phát khoá cho một tài khoản khách — kể cả để "thử
   giúp họ" — là mượn danh tính và ví của họ. Chặn ở đây bằng cùng quy ước đuôi
   email mà `ve_dang_nhap_thu.py` dùng.

⚠️ In khoá ra màn hình. Đừng chạy nó trong một phiên có người khác nhìn, và
   đừng chép khoá vào bất cứ tệp nào được commit.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DUOI_THU = ".local"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", default="thu.giongnoi@lttstudios.local")
    ap.add_argument("--ten", default="nghiem thu speech.ltt")
    ap.add_argument("--che-do", default="live", choices=("live", "test"),
                    help="`test` = che do thu: khong cham GPU, khong cham so tien.")
    a = ap.parse_args(argv)

    if not a.email.endswith(DUOI_THU):
        print(f"TU CHOI: chi phat khoa cho tai khoan thu (duoi '{DUOI_THU}').",
              file=sys.stderr)
        return 2

    from platform_core import users
    from platform_core.db import get_session
    from platform_core.public_api import keys as devkeys

    gen = get_session()
    db = next(gen)
    try:
        u = users.tim_theo_email(db, a.email)
        if u is None:
            print(f"KHONG THAY {a.email}", file=sys.stderr)
            return 2
        try:
            # ⭐ Đủ để đi HẾT một vòng nghiệm thu: đọc danh mục, nộp việc, theo
            #   dõi, tải kết quả. Lần đầu tôi chỉ xin `jobs:*` và `/api/v1/tools`
            #   trả `403 missing_scope` — một lỗi tốt, vì nó nói **thiếu scope
            #   nào** thay vi chỉ "không được phép".
            #
            # ⚠️ LẦN THỨ HAI danh sách này thiếu một scope: 01/09, đo đường huỷ
            #   job thì `POST /jobs/{id}/cancel` trả `403 missing_scope`, và
            #   **405 ở các động từ khác** làm nó thoạt trông như "không có
            #   đường huỷ". Thêm `jobs:cancel`.
            #
            # ⭐ Chính vì lỗi 403 gọi tên scope thiếu mà việc này mất 30 giây
            #   thay vì một buổi. Đó là lập luận cho kiểu lỗi ấy, không phải
            #   một lời khen suông.
            _, token = devkeys.issue(
                db, user_id=str(u.id), name=a.ten, mode=a.che_do,
                scopes=("tools:read", "jobs:create", "jobs:read",
                        "jobs:cancel", "artifacts:read", "credits:read"))
        except devkeys.DeveloperKeyError as e:
            # Trần số khoá là một ràng buộc THẬT của sản phẩm, không phải một
            # phiền toái của kịch bản này. Nói ra rồi dừng, đừng đi vòng.
            print(f"TU CHOI: {e}", file=sys.stderr)
            return 2
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
