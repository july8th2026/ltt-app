"""
templating.py — the single Jinja2 environment for the whole app.

Every route module imported its own `Jinja2Templates(directory=...)`, which
meant a global (like the nav's "which pages are built yet" map) had to be
threaded through every single route context or the template would raise
UndefinedError. One shared instance with globals fixes that at the source.
"""
from __future__ import annotations

import pathlib

from fastapi.templating import Jinja2Templates

# Đường dẫn TUYỆT ĐỐI, suy ra từ vị trí chính file này.
#
# Trước đây là "server/templates" — tương đối theo thư mục làm việc. Nó chạy
# đúng chỉ vì NSSM đặt AppDirectory về gốc dự án. Ai chạy uvicorn từ thư mục
# khác là MỌI trang trả 500 vì không tìm thấy template, mà thông báo lỗi lại
# không nói gì về thư mục làm việc. Khi chuyển sang máy mới đây là bẫy dễ vấp
# nhất, nên chốt cứng theo vị trí file.
_TEMPLATE_DIR = pathlib.Path(__file__).resolve().parent / "templates"

templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

# Which desktop tabs have a real web page yet. The sidebar reads this to
# show an honest "đang xây" badge instead of pretending a link is finished.
# Flip a value to True in the same commit that lands the real page.
BUILT_PAGES = {
    "sheet_fb":      True,
    "sheet_tiktok":  True,
    "manual_fb":     True,
    "manual_tiktok": True,
    "facebook":      True,
    "tiktok":        True,
    "monitor":       True,
    "audit":         True,
    "settings":      True,
    "status":        True,
}

try:
    from version import APP_VERSION_SHORT as _VER
except Exception:
    _VER = ""

templates.env.globals["built"] = BUILT_PAGES


def _nav_apps(request=None):
    """Danh sách app cho sidebar. Quét mỗi lần render là đủ nhanh (chỉ đọc
    module đã cache trong sys.modules), và nhờ vậy thêm app không cần restart
    lúc phát triển.

    Nhận `request` để lọc app `hidden` theo người dùng (H1.4) — sidebar phải
    khớp với trang chủ, nếu không app bị ẩn vẫn hiện ở thanh bên. Bọc an toàn:
    lỗi lọc (chưa có CSDL, admin-env) thì hiện đủ, không làm sập trang."""
    try:
        from platform_core.registry import discover
        loaded = [a for a in discover() if a.manifest.enabled and not a.error]
    except Exception:
        # Sidebar lỗi không được làm sập trang. Trả rỗng còn hơn 500.
        return []

    if request is None:
        return loaded
    try:
        sid = request.session.get("sid")
        if not sid:
            return loaded      # admin-env / ẩn danh → không lọc ở đây
        from platform_core.app_access import loc_app_hien_thi
        from platform_core.db import get_session
        from platform_core.users import lay_user_tu_phien
        gen = get_session(); db = next(gen)
        try:
            user = lay_user_tu_phien(db, sid)
            return loc_app_hien_thi(db, user, loaded) if user else loaded
        finally:
            try: next(gen)
            except StopIteration: pass
    except Exception:
        return loaded


templates.env.globals["nav_apps"] = _nav_apps
templates.env.globals["app_version"] = _VER
