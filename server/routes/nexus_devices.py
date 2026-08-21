"""Trang "Máy của tôi" — người dùng tự quản lý máy LTT Nexus của mình.

Model B (Q101) bỏ web-broker: web KHÔNG điều khiển máy, nhưng người dùng **phải**
xem và cắt được quyền truy cập máy của chính mình. Mất laptop mà không thu hồi
được thì tài khoản coi như thủng — đây là lỗ hổng vận hành, không phải tiện nghi.

Trang này chỉ làm ba việc: **xem** (máy, online, thuê bao), **đổi tên**, và
**thu hồi**. Không cấp vé, không mở phiên — đúng ranh giới Model B.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from platform_core import nexus
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import user_hien_tai
from server.templating import templates

router = APIRouter(tags=["nexus-devices"])

#: Trang tự ẩn khi Nexus tắt (Q93 fail-closed) — 404 y như route agent.
_TAT = HTMLResponse(status_code=404, content="Not found")


def _lay_danh_sach(db, user_id: str) -> list[dict]:
    """Máy của một tài khoản, kèm trạng thái hiển thị. Trả dict (không phải ORM)
    để template không chạm session đã đóng."""
    from platform_core.nexus import billing, devices

    ra = []
    for d in devices.danh_sach(db, user_id=user_id):
        ra.append({
            "id": d.id,
            "ten": d.display_name or "",   # rỗng → template dịch nhãn thay
            "rustdesk_id": d.rustdesk_id or "",
            "online": devices.dang_online(d),
            "da_tra": billing.da_thanh_toan(d),
            "paid_until": d.paid_until,
            "last_seen_at": d.last_seen_at,
            "platform": getattr(d, "platform", "") or "",
        })
    return ra


@router.get("/may-cua-toi", response_class=HTMLResponse)
def trang_may(request: Request, user: str = Depends(require_login)):
    """Danh sách máy đã gắn vào tài khoản."""
    if not nexus.enabled():
        return _TAT
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.nexus import billing

    u = user_hien_tai(request)
    may, so_du = [], None
    gen = get_session(); db = next(gen)
    try:
        if u is not None:
            may = _lay_danh_sach(db, u.id)
            so_du = credit.so_du(db, u.id)
    finally:
        try: next(gen)
        except StopIteration: pass
    return templates.TemplateResponse(request, "nexus_may.html", {
        "user": user, "nav": "may", "may": may, "so_du": so_du,
        "gia_thang": billing.gia_may_thang(),
        "co_user_csdl": u is not None,
        "csrf_token": issue_csrf_token(request),
    })


def _may_cua_minh(db, request: Request, device_id: str):
    """Máy đó có thuộc người đang đăng nhập không. None = không (đừng nói vì sao
    — không lộ máy người khác có tồn tại hay không)."""
    from platform_core.nexus import devices

    u = user_hien_tai(request)
    if u is None:
        return None
    return devices.cua_chu(db, user_id=u.id, device_id=device_id)


@router.post("/may-cua-toi/{device_id}/doi-ten")
def doi_ten(request: Request, device_id: str, ten: str = Form(""),
            csrf_token: str = Form(""), user: str = Depends(require_login)):
    """Đổi tên hiển thị của máy (chỉ ảnh hưởng cách người dùng nhận ra nó)."""
    if not nexus.enabled():
        return _TAT
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/may-cua-toi?loi=csrf", status_code=303)
    from platform_core.db import get_session

    gen = get_session(); db = next(gen)
    try:
        d = _may_cua_minh(db, request, device_id)
        if d is None:
            return RedirectResponse("/may-cua-toi?loi=khong-thay", status_code=303)
        d.display_name = (ten or "").strip()[:120]
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass
    return RedirectResponse("/may-cua-toi?ok=doi-ten", status_code=303)


@router.post("/may-cua-toi/{device_id}/thu-hoi")
def thu_hoi_may(request: Request, device_id: str, csrf_token: str = Form(""),
                user: str = Depends(require_login)):
    """Thu hồi máy: khoá đăng ký đó lại (máy mất/bán đi thì cắt ngay).

    Thu hồi **không xoá** lịch sử — nhật ký truy cập cũ phải còn để đối chiếu.
    """
    if not nexus.enabled():
        return _TAT
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/may-cua-toi?loi=csrf", status_code=303)
    from platform_core.db import get_session
    from platform_core.nexus import devices

    gen = get_session(); db = next(gen)
    try:
        d = _may_cua_minh(db, request, device_id)
        if d is None:
            return RedirectResponse("/may-cua-toi?loi=khong-thay", status_code=303)
        devices.thu_hoi(db, d, by=str(user))
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass
    return RedirectResponse("/may-cua-toi?ok=thu-hoi", status_code=303)
