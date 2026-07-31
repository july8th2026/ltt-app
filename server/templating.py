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

# Hợp đồng app (H5): app được mang template RIÊNG trong `apps/<slug>/templates/`
# để tự dựng UI (extends base.html) MÀ KHÔNG phải bỏ file vào server/templates/.
# Không có phần này thì "thêm app = thêm thư mục" chỉ đúng với phần xử lý, còn
# giao diện vẫn buộc chạm server/ — đúng lỗ hổng H5 phải lấp. server/templates/
# đứng TRƯỚC nên nền tảng luôn thắng khi trùng tên (app không ghi đè được vỏ).
_APPS_DIR = pathlib.Path(__file__).resolve().parent.parent / "apps"
_app_template_dirs = sorted(
    str(p) for p in _APPS_DIR.glob("*/templates") if p.is_dir()
)
if _app_template_dirs:
    from jinja2 import ChoiceLoader, FileSystemLoader
    templates.env.loader = ChoiceLoader(
        [FileSystemLoader(str(_TEMPLATE_DIR))]
        + [FileSystemLoader(d) for d in _app_template_dirs]
    )

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


def _so_du_credit(request=None):
    """Số dư credit của người dùng CSDL đang đăng nhập, hoặc None (H6).

    None khi: chưa đăng nhập bằng phiên CSDL (admin-env / ẩn danh), chưa có CSDL,
    hay bất kỳ lỗi nào — vỏ chỉ hiện badge khi có số thật, không làm sập trang.
    """
    if request is None:
        return None
    try:
        sid = request.session.get("sid")
        if not sid:
            return None
        from platform_core.credit import so_du
        from platform_core.db import get_session
        from platform_core.users import lay_user_tu_phien
        gen = get_session(); db = next(gen)
        try:
            u = lay_user_tu_phien(db, sid)
            return so_du(db, u.id) if u else None
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
    except Exception:
        return None


templates.env.globals["so_du_credit"] = _so_du_credit


def _active_app(request=None):
    """Slug của app mà đường dẫn hiện tại thuộc về, hoặc None (H6.6).

    Vỏ hai tầng: sidebar hiện MỖI APP MỘT DÒNG (launcher); trang con của app chỉ
    bung ra khi đang ở TRONG app đó. Dùng app_cho_path (khớp tiền tố dài nhất
    trên route_prefix + nav) nên không hardcode tên app. Bọc an toàn."""
    if request is None:
        return None
    try:
        from platform_core.app_access import app_cho_path
        from platform_core.registry import discover
        return app_cho_path(request.url.path, discover())
    except Exception:
        return None


def _is_admin(request=None):
    """True nếu phiên hiện tại là admin CSDL (H6.6) → hiện link Quản trị.

    Chỉ True cho user CSDL role=admin. admin-env/ẩn danh/lỗi → False (không lộ
    link quản trị nhầm). Bọc an toàn: lỗi không được làm sập vỏ."""
    if request is None:
        return False
    try:
        sid = request.session.get("sid")
        if not sid:
            return False
        from platform_core.db import get_session
        from platform_core.users import lay_user_tu_phien
        gen = get_session(); db = next(gen)
        try:
            u = lay_user_tu_phien(db, sid)
            return bool(u and u.role == "admin")
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
    except Exception:
        return False


templates.env.globals["active_app"] = _active_app
templates.env.globals["is_admin"] = _is_admin


def _csrf_token(request=None):
    """Token CSRF của phiên cho các form nhỏ dựng thẳng trong base (vd nút Đăng
    xuất). `issue_csrf_token` idempotent nên nhiều form trên cùng trang dùng
    chung một token — không ghi đè nhau."""
    if request is None:
        return ""
    try:
        from server.auth.csrf import issue_csrf_token
        return issue_csrf_token(request)
    except Exception:
        return ""


# Tên KHÁC `csrf_token` vì nhiều route truyền biến context tên `csrf_token` (một
# CHUỖI) — trùng tên sẽ che global và `{{ csrf_token(request) }}` gọi chuỗi → lỗi.
templates.env.globals["phien_csrf"] = _csrf_token
