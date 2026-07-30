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


def _nav_apps():
    """Danh sách app cho sidebar. Quét mỗi lần render là đủ nhanh (chỉ đọc
    module đã cache trong sys.modules), và nhờ vậy thêm app không cần restart
    lúc phát triển."""
    try:
        from platform_core.registry import discover
        return [a for a in discover() if a.manifest.enabled and not a.error]
    except Exception:
        # Sidebar lỗi không được làm sập trang. Trả rỗng còn hơn 500.
        return []


templates.env.globals["nav_apps"] = _nav_apps
templates.env.globals["app_version"] = _VER
