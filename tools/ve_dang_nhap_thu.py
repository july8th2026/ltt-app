r"""
ve_dang_nhap_thu.py — phát một VÉ ĐĂNG NHẬP MỘT LẦN cho tài khoản THỬ, để kiểm
giao diện bằng trình duyệt thật.

    powershell -ExecutionPolicy Bypass -File .\setup\ve_dang_nhap_thu.ps1

⭐ VÌ SAO ĐI ĐƯỜNG NÀY, KHÔNG PHẢI ĐI QUA Ô MẬT KHẨU

   `CLAUDE.md` quy tắc 5/5b bắt kiểm giao diện trên URL công khai, và phần lớn
   màn hình đáng kiểm nằm **sau đăng nhập**. Ba đường vào có thể nghĩ tới:

     1. Gõ mật khẩu vào `/login` — ngoài chuyện đó là việc không được làm, nó
        còn **không chạy**: `/login` có Turnstile, tức một phép xác minh chống
        bot, và vượt nó cũng là việc không được làm.
     2. Tự ký một cookie phiên — cookie trình duyệt ở đây là Starlette session
        ĐÃ KÝ. Ký lấy bằng khoá của ứng dụng là chế ra một chứng danh ở ngoài
        luồng xác thực. Không làm.
     3. **Vé SSO một lần** — `platform_core/nexus/sso.py`. Đây là một **tính
        năng có sẵn của sản phẩm**, không phải một đường vòng: ứng dụng Nexus
        vẫn dùng đúng nó để nối phiên app sang phiên web.

   Chọn 3. Nó đi qua đúng cửa mà nền tảng đã mở, và nó thừa hưởng luôn ba ràng
   buộc mà cửa đó tự mang theo: vé sống 90 giây, dùng một lần rồi bị xoá, và
   phiên sinh ra mang nhãn tự khai trong danh sách phiên.

⛔ CHỈ CHO ĐUÔI `.local`. Vé là một chứng danh sống. Phát vé cho một tài khoản
   khách — kể cả để "xem thử giúp họ" — là mượn danh tính của họ. Chặn ở đây
   bằng quy ước đuôi email, cùng thứ mà `tai_khoan_thu.py` dùng.
"""
from __future__ import annotations

import argparse
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace", line_buffering=True)

DUOI_THU = ".local"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", default="thu.giongnoi@lttstudios.local")
    ap.add_argument("--goc", default="https://app.lttstudios.com",
                    help="Goc URL de ghep ve vao.")
    a = ap.parse_args(argv)

    if not a.email.endswith(DUOI_THU):
        print(f"TU CHOI: chi phat ve cho tai khoan thu (duoi '{DUOI_THU}').",
              file=sys.stderr)
        return 2

    from platform_core import users
    from platform_core.db import get_session
    from platform_core.nexus import sso

    gen = get_session()
    db = next(gen)
    try:
        u = users.tim_theo_email(db, a.email)
        if u is None:
            print(f"KHONG THAY {a.email}", file=sys.stderr)
            return 2
        ve = sso.tao_ve(db, u, ip="127.0.0.1")
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    # Vé sống 90 giây — in ra rồi phải mở NGAY.
    print(f"{a.goc.rstrip('/')}/nexus-sso?ma={ve}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
