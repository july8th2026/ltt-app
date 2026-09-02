"""_p_trang.py — vỏ trang ChatLTT + catalog theo chính sách sản phẩm."""
from __future__ import annotations

from fastapi import Depends, Request
from fastapi.responses import HTMLResponse

from apps.chatltt.routes._chung import issue_csrf_token, json_ok, router, uid
from apps.chatltt.services import chinh_sach
from platform_core.frontend_bundle import bundle_assets
from server.auth.session import require_login
from server.deps import get_db
from server.templating import templates


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def trang(request: Request, _=Depends(require_login)):
    js, css = bundle_assets("chatltt")
    return templates.TemplateResponse(request, "chatltt.html", {
        "request": request, "chatltt_js": js, "chatltt_css": css,
        "csrf_token": issue_csrf_token(request),
    })


@router.get("/api/danh-muc")
def api_danh_muc(request: Request, _=Depends(require_login), db=Depends(get_db)):
    """Catalog ChatLTT cho người dùng hiện tại — chỉ thứ chính sách sản phẩm mời."""
    ds = chinh_sach.danh_muc(db, user_id=uid(request))
    return json_ok({"nang_luc": [
        {"ten": n.ten, "phuong_thuc": n.phuong_thuc, "che_do": n.che_do, "nhan": n.nhan,
         "models": n.models, "tuy_chon": n.tuy_chon, "gia": n.gia,
         "duong_dan_app": n.duong_dan_app, "san_sang": n.san_sang, "hop_dong": n.hop_dong}
        for n in ds]})
