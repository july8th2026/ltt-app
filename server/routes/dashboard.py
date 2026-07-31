"""Trang chủ — danh sách app, sinh từ apps/*/manifest.py.

Trước đây "/" chỉ hiện tóm tắt blocker. Giờ nó là cửa vào của nền tảng nhiều
app, nhưng vẫn giữ phần blocker ở trên: đây là trang thấy đầu tiên sau khi
đăng nhập, nên là chỗ đúng nhất để nói "bot chưa đăng được vì thiếu X".

Phần blocker dùng lại tools/doctor.py để trang chủ, /status và CLI không bao
giờ nói khác nhau. Bỏ qua kiểm tra Sheet vì trang này tải mỗi lần đăng nhập,
mà kiểm tra Sheet tốn một vòng gọi mạng.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from server.auth.session import require_login
from server.templating import templates

router = APIRouter(tags=["home"])


@router.get("/", response_class=HTMLResponse)
def home(request: Request, user: str = Depends(require_login)):
    from platform_core.registry import discover
    from tools import doctor

    loaded = discover()
    report = doctor.run(check_sheet_flag=False)

    # Lọc app theo quyền của người dùng (H1.4): bỏ app `hidden`. App `locked`
    # vẫn hiện, template gắn nhãn. Bọc an toàn: khi chưa có CSDL hoặc là
    # admin-env (đường lui), hiện đủ như trước — không được để phân quyền làm
    # trang chủ trắng khi DB trục trặc.
    visible = [a for a in loaded if not a.error]
    try:
        u = _user_hien_tai(request)
        if u is not None:
            from platform_core.app_access import loc_app_hien_thi
            from platform_core.db import get_session
            gen = get_session(); db = next(gen)
            try:
                visible = loc_app_hien_thi(db, u, visible)
            finally:
                try: next(gen)
                except StopIteration: pass
    except Exception:
        pass

    return templates.TemplateResponse(request, "home.html", {
        "user": user,
        "nav": "home",
        "apps": visible,
        "broken": [a for a in loaded if a.error],
        "blockers": [s for s in report.sections if s["status"] == doctor.BLOCK],
    })


def _user_hien_tai(request: Request):
    """User CSDL từ phiên, hoặc None (admin-env / ẩn danh / chưa có DB)."""
    try:
        sid = request.session.get("sid")
        if not sid:
            return None
        from platform_core.db import get_session
        from platform_core.users import lay_user_tu_phien
        gen = get_session(); db = next(gen)
        try:
            return lay_user_tu_phien(db, sid)
        finally:
            try: next(gen)
            except StopIteration: pass
    except Exception:
        return None
