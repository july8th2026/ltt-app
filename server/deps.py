"""
deps.py — FastAPI dependency dùng chung cho tầng web.

Vì sao tách ra: nhiều route cần một phiên CSDL, và cần nó được mở/đóng/commit
theo đúng một khuôn. Gom về đây để không mỗi route tự xoay một kiểu.
"""
from __future__ import annotations

import contextlib
from typing import Iterator, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette.requests import Request


def get_db() -> Iterator[Session]:
    """Phiên CSDL cho một request. Commit khi request xong êm, rollback khi lỗi.

    Dùng cho route **bắt buộc phải có CSDL** (đăng ký, quản lý tài khoản). Nếu
    CSDL chưa cấu hình, `get_session()` ném lỗi ngay — đúng, vì các route này
    vô nghĩa khi không có CSDL.

    Commit-khi-xong: một route đọc thuần cũng commit, nhưng vô hại (không có
    thay đổi để ghi). Đổi lại, route ghi không phải nhớ tự commit — quên commit
    là lỗi âm thầm khó thấy nhất.
    """
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        with contextlib.suppress(StopIteration):
            next(gen)      # để get_session chạy nốt phần đóng phiên


def user_hien_tai(request) -> Optional["object"]:
    """User CSDL từ phiên đăng nhập, hoặc None.

    None khi: chưa đăng nhập, đăng nhập bằng đường admin-env (không có user_id
    trong bảng users), hoặc CSDL chưa cấu hình. Dùng cho các route cần một user
    thật (submit job, xem job, credit) — admin-env là đường lui vận hành, không
    chạy job.
    """
    try:
        sid = request.session.get("sid")
        if not sid:
            return None
        from platform_core.db import get_session
        from platform_core.users import lay_user_tu_phien
        gen = get_session()
        db = next(gen)
        try:
            return lay_user_tu_phien(db, sid)
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
    except Exception:
        return None


def is_operator(request: Request) -> bool:
    """Admin-env or active database admin; never grants operator access to users."""
    try:
        session = request.session
        settings = getattr(request.app.state, "server_settings", None)
        admin_name = getattr(settings, "admin_username", "admin") if settings else "admin"
        if session.get("user") == admin_name:
            return True
        user = user_hien_tai(request)
        return bool(user and user.role == "admin")
    except Exception:
        return False


def require_operator(request: Request) -> str:
    """Require login and then enforce the user/operator boundary."""
    from server.auth.session import require_login

    identity = require_login(request)
    if not is_operator(request):
        raise HTTPException(status_code=403, detail="Trang này chỉ dành cho quản trị viên.")
    return identity


@contextlib.contextmanager
def mo_db_optional() -> Iterator[Optional[Session]]:
    """Mở phiên CSDL nếu có thể, ngược lại trả None — không ném lỗi.

    Dùng cho những chỗ CSDL là **tuỳ chọn** trong giai đoạn chạy song song:
    route đăng nhập thử tra người dùng trong CSDL, nhưng vẫn phải phục vụ được
    đường đăng nhập admin-từ-biến-môi-trường khi CSDL chưa cấu hình (đúng trạng
    thái của hàng trăm test không dựng PostgreSQL).

    Tự commit khi xong êm, giống `get_db`.
    """
    try:
        from platform_core.db import get_session
        gen = get_session()
        db = next(gen)
    except Exception:
        yield None
        return

    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        with contextlib.suppress(StopIteration):
            next(gen)
