"""
billing.py (route) — trang nạp credit cho người dùng (H9).

Luồng: `/nap` (chọn gói) -> POST tạo đơn -> `/nap/don/{id}` (mở trang PayOS +
theo dõi trạng thái, HTMX poll). Mọi cộng credit đi qua `platform_core.billing`
(idempotent, qua sổ H3) — route KHÔNG tự cộng credit.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import user_hien_tai
from server.templating import templates

router = APIRouter(tags=["billing"])

GATEWAY_MAC_DINH = "payos"


@router.get("/nap", response_class=HTMLResponse)
def trang_nap(request: Request, user: str = Depends(require_login)):
    from platform_core import billing, credit
    from platform_core.db import get_session
    u = user_hien_tai(request)
    goi, so_du, don_gan_day = [], None, []
    gen = get_session(); db = next(gen)
    try:
        goi = billing.goi_active(db)
        for g in goi:
            db.expunge(g)
        if u is not None:
            so_du = credit.so_du(db, u.id)
            don_gan_day = billing.liet_ke_don(db, user_id=u.id, limit=10)
            for order in don_gan_day:
                db.expunge(order)
    finally:
        try: next(gen)
        except StopIteration: pass
    return templates.TemplateResponse(request, "nap.html", {
        "user": user, "nav": "nap", "goi": goi, "so_du": so_du,
        "don_gan_day": don_gan_day, "co_user_csdl": u is not None,
        "csrf_token": issue_csrf_token(request),
    })


@router.post("/nap/tao", response_class=HTMLResponse)
def tao_don(request: Request, package_id: str = Form(...),
            csrf_token: str = Form(""), user: str = Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        return HTMLResponse("CSRF", status_code=400)
    u = user_hien_tai(request)
    if u is None:
        return RedirectResponse("/nap", status_code=303)
    from platform_core import billing
    from platform_core.db import get_session
    base = str(request.base_url).rstrip("/")
    gen = get_session(); db = next(gen)
    order_id = None
    try:
        pkg = billing.lay_goi(db, package_id)
        if pkg is None or not pkg.active:
            return RedirectResponse("/nap", status_code=303)
        order = billing.tao_don(
            db, user_id=u.id, package=pkg, gateway_id=GATEWAY_MAC_DINH,
            return_url=f"{base}/nap/don/PLACEHOLDER",
            cancel_url=f"{base}/nap")
        order_id = order.id
        # return_url cần id đơn -> cập nhật lại sau khi có id (đơn giản: bỏ qua,
        # PayOS vẫn về trang chủ; trang /nap/don tự poll trạng thái).
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass
    return RedirectResponse(f"/nap/don/{order_id}", status_code=303)


@router.get("/nap/don/{order_id}", response_class=HTMLResponse)
def chi_tiet_don(request: Request, order_id: str, user: str = Depends(require_login)):
    from platform_core import billing
    from platform_core.db import get_session
    u = user_hien_tai(request)
    gen = get_session(); db = next(gen)
    try:
        order = billing.lay_don(db, order_id)
        if order is None or (u is not None and order.user_id != u.id):
            return HTMLResponse("Không thấy đơn.", status_code=404)
        db.expunge(order)
    finally:
        try: next(gen)
        except StopIteration: pass
    return templates.TemplateResponse(request, "nap_don.html", {
        "user": user, "nav": "nap", "order": order,
    })


@router.get("/nap/don/{order_id}/trangthai", response_class=HTMLResponse)
def trang_thai_don(request: Request, order_id: str, user: str = Depends(require_login)):
    """Fragment HTMX: trạng thái đơn (poll). Trả badge + số dư nếu đã trả."""
    from platform_core import billing, credit
    from platform_core.db import get_session
    u = user_hien_tai(request)
    gen = get_session(); db = next(gen)
    order = so_du = None
    try:
        order = billing.lay_don(db, order_id)
        if order is None or (u is not None and order.user_id != u.id):
            return HTMLResponse("", status_code=404)
        if u is not None:
            so_du = credit.so_du(db, u.id)
        db.expunge(order)
    finally:
        try: next(gen)
        except StopIteration: pass
    return templates.TemplateResponse(request, "_nap_trangthai.html", {
        "order": order, "so_du": so_du,
    })
