"""Phiên đăng nhập (H1.2).

Có HAI đường đăng nhập chạy **song song** trong giai đoạn này, cố ý:

1. **admin-từ-biến-môi-trường** (đường cũ, đang chạy production): cookie ký của
   Starlette mang `session["user"] = username`. Không chạm CSDL. Đây là đường
   lui — luôn còn một cách vào kể cả khi CSDL hỏng.

2. **người dùng trong CSDL** (đường mới, H1.2): cookie ký mang
   `session["sid"] = <session_id>`, trỏ tới một dòng trong bảng `sessions`.
   Thu hồi được (xoá dòng), nên "đăng xuất khỏi mọi thiết bị" và "đổi mật khẩu
   đá mọi phiên" mới làm được — cookie ký thuần không có id để thu hồi.

`require_login` nhận diện cả hai và luôn trả về một chuỗi định danh (username
hoặc email), nên **không route nào đang dùng nó phải đổi**. Đường CSDL thất bại
im lặng khi CSDL chưa cấu hình, để hàng trăm test không dựng PostgreSQL vẫn
chạy đường admin-env bình thường.

Khi gỡ đường admin-env (cuối H1), xoá nhánh `session["user"]` và cập nhật test.
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from starlette.requests import Request

_SESSION_USER_KEY = "user"   # duong admin-env (cu)
_SESSION_SID_KEY = "sid"     # duong nguoi dung CSDL (moi)


# ── Đường admin-từ-biến-môi-trường (giữ nguyên hành vi cũ) ────────────────────

def current_user(request: Request) -> Optional[str]:
    """Chỉ đường admin-env. Giữ nguyên để test và code cũ không đổi nghĩa."""
    return request.session.get(_SESSION_USER_KEY)


def log_in(request: Request, username: str) -> None:
    # Xoá mọi khoá phiên trước-đăng-nhập (vd token CSRF cấp cho khách ẩn danh)
    # thay vì mang chúng vào phiên đã đăng nhập — giảm nhẹ session fixation.
    request.session.clear()
    request.session[_SESSION_USER_KEY] = username


def log_out(request: Request) -> None:
    """Xoá cookie phiên, và nếu là phiên CSDL thì thu hồi luôn ở máy chủ."""
    sid = request.session.get(_SESSION_SID_KEY)
    if sid:
        _thu_hoi_sid_an_toan(sid)
    request.session.clear()


# ── Đường người dùng CSDL (mới) ───────────────────────────────────────────────

def log_in_db(request: Request, sid: str) -> None:
    """Ghi nhận một phiên CSDL vào cookie. `sid` do `users.tao_phien` cấp."""
    request.session.clear()
    request.session[_SESSION_SID_KEY] = sid


def current_sid(request: Request) -> Optional[str]:
    return request.session.get(_SESSION_SID_KEY)


def _resolve_sid(sid: str) -> Optional[str]:
    """Đổi sid lấy email, mở một phiên CSDL ngắn. None nếu sai/hết hạn/chưa có DB.

    Bọc toàn bộ trong try/except: khi CSDL chưa cấu hình (nhiều test), đường này
    phải **thất bại im lặng** để đường admin-env vẫn phục vụ được.
    """
    try:
        from platform_core.db import get_session
        from platform_core.users import lay_user_tu_phien
        gen = get_session()
        db = next(gen)
        try:
            user = lay_user_tu_phien(db, sid)
            db.commit()      # lay_user_tu_phien co the xoa phien het han
            return user.email if user else None
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
    except Exception:
        return None


def _thu_hoi_sid_an_toan(sid: str) -> None:
    try:
        from platform_core.db import get_session
        from platform_core.users import thu_hoi_phien
        gen = get_session()
        db = next(gen)
        try:
            thu_hoi_phien(db, sid)
            db.commit()
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
    except Exception:
        pass


# ── Dependency dùng chung ─────────────────────────────────────────────────────

def require_login(request: Request) -> str:
    """FastAPI dependency: 303 về /login khi chưa đăng nhập.

    Trả về chuỗi định danh (username của admin-env, hoặc email của user CSDL).
    Chữ ký không đổi so với bản cũ, nên mọi route `Depends(require_login)` giữ
    nguyên.
    """
    u = request.session.get(_SESSION_USER_KEY)
    if u:
        return u

    sid = request.session.get(_SESSION_SID_KEY)
    if sid:
        email = _resolve_sid(sid)
        if email:
            return email

    raise HTTPException(status_code=303, headers={"Location": "/login"})
