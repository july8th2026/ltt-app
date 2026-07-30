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

    return templates.TemplateResponse(request, "home.html", {
        "user": user,
        "nav": "home",
        "apps": [a for a in loaded if not a.error],
        "broken": [a for a in loaded if a.error],
        "blockers": [s for s in report.sections if s["status"] == doctor.BLOCK],
    })
