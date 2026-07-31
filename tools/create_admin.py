"""
create_admin.py — tạo hoặc nâng một tài khoản admin TRONG CSDL (H3-admin).

Đây là cách tạo admin KHÔNG phụ thuộc biến môi trường (đường admin-env cũ). Khi
đã có ít nhất một admin trong CSDL, có thể gỡ đường admin-env (xem H1.2/H3-admin).

Chạy trên máy chủ bằng venv:

    C:\\LTTPlatform\\venv\\Scripts\\python.exe tools\\create_admin.py admin@lttstudios.com

Mật khẩu: nhập qua getpass (không hiện trên màn hình), hoặc đặt biến môi trường
`LTT_NEW_ADMIN_PASSWORD` cho môi trường không tương tác. Mật khẩu chỉ lưu dạng
băm (PBKDF2), không bao giờ in ra hay ghi xuống đĩa.

Idempotent: email đã tồn tại → nâng thành admin + đặt lại mật khẩu (thu hồi mọi
phiên cũ của tài khoản đó). Chưa tồn tại → tạo mới, role=admin, đã xác thực.
"""
from __future__ import annotations

import getpass
import os
import sys

# Cho phép chạy trực tiếp từ thư mục gốc dự án.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    email = (sys.argv[1] if len(sys.argv) > 1
             else os.environ.get("LTT_ADMIN_EMAIL", "")).strip()
    if not email or "@" not in email:
        print("Cách dùng: python tools/create_admin.py <email>", file=sys.stderr)
        return 2

    pw = os.environ.get("LTT_NEW_ADMIN_PASSWORD", "")
    if not pw:
        pw = getpass.getpass("Mat khau admin moi: ")
        if pw != getpass.getpass("Nhap lai: "):
            print("Mat khau khong khop.", file=sys.stderr)
            return 1
    if len(pw) < 12:
        print("Mat khau toi thieu 12 ky tu.", file=sys.stderr)
        return 1

    from platform_core.db import get_session
    from platform_core.users import (chuan_hoa_email, doi_mat_khau,
                                     tao_nguoi_dung, tim_theo_email)

    email = chuan_hoa_email(email)
    gen = get_session()
    db = next(gen)
    try:
        existing = tim_theo_email(db, email)
        if existing is not None:
            existing.role = "admin"
            existing.is_active = True
            existing.is_verified = True
            doi_mat_khau(db, existing, pw)   # đặt lại mật khẩu + thu hồi phiên cũ
            action = "Da nang thanh admin + dat lai mat khau"
        else:
            u = tao_nguoi_dung(db, email=email, password=pw, role="admin",
                               is_verified=True)
            u.is_active = True
            action = "Da tao admin moi"
        db.commit()
        print(f"{action}: {email} (role=admin)")
        print("Dang nhap tai /login bang EMAIL nay (o 'Ten dang nhap').")
        return 0
    except Exception as e:
        db.rollback()
        print(f"Loi: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    sys.exit(main())
