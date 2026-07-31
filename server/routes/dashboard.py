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

from server.auth.session import current_identity_optional
from server.templating import templates

router = APIRouter(tags=["home"])


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Trang chủ = CATALOG (H6/Q30).

    CÔNG KHAI: khách chưa đăng nhập vẫn xem được danh sách app (chỉ app
    `enabled and public`), bấm một app thì mới cần đăng nhập. Đã đăng nhập thì
    lọc theo quyền (AppAccess) và hiện blocker/app-lỗi như trước.
    """
    from platform_core.registry import discover

    user = current_identity_optional(request)
    authed = user is not None
    loaded = discover()
    ok_apps = [a for a in loaded if not a.error]

    if not authed:
        # Khách: chỉ hiện app self-serve công khai; KHÔNG lộ blocker/app-lỗi.
        visible = [a for a in ok_apps
                   if a.manifest.enabled and a.manifest.public]
        return templates.TemplateResponse(request, "home.html", {
            "user": None, "authed": False, "nav": "home",
            "apps": visible, "broken": [], "app_setup": {},
        })

    # Đã đăng nhập: lọc theo quyền (H1.4) + tính "cần thiết lập" theo TỪNG app.
    # Bọc an toàn: DB trục trặc / admin-env thì hiện đủ, không để phân quyền làm
    # trang trắng.
    from tools import doctor
    report = doctor.run(check_sheet_flag=False)
    visible = ok_apps
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

    # Blocker doctor gắn vào ĐÚNG thẻ app (H6.6): không còn banner FB/TikTok toàn
    # cục. Khớp theo manifest.blocker_titles do app tự khai — nền tảng KHÔNG
    # hardcode tên app. Blocker không thuộc app nào vẫn xem đầy đủ ở /status.
    block_sections = [s for s in report.sections if s["status"] == doctor.BLOCK]
    app_setup: dict = {}
    for item in visible:
        titles = getattr(item.manifest, "blocker_titles", ()) or ()
        hits = [s for s in block_sections if s["check"] in titles]
        if hits:
            app_setup[item.manifest.slug] = hits

    return templates.TemplateResponse(request, "home.html", {
        "user": user,
        "authed": True,
        "nav": "home",
        "apps": visible,
        "broken": [a for a in loaded if a.error],
        "app_setup": app_setup,
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
