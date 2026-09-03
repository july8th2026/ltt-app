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


@router.get("/api/so-du")
def api_so_du(request: Request, _=Depends(require_login), db=Depends(get_db)):
    """So du credit hien tai.

    ⭐ Vi sao mot duong rieng chu khong nhet vao `su_that()`: so du doi vi
       NHUNG VIEC KHAC nua (app khac, nap tien), khong chi vi hoi thoai nay.
       Gop vao thi giao dien chi thay so moi khi hoi thoai doi — va do la luc
       no da sai roi. Thanh tren cua nen tang la HTML dung, chi doi khi tai
       lai trang; day la duong de ChatLTT noi so that ma khong bat tai lai.
    """
    from platform_core import credit

    return json_ok({"credit": int(credit.so_du(db, uid(request)))})


@router.get("/api/danh-muc")
def api_danh_muc(request: Request, _=Depends(require_login), db=Depends(get_db)):
    """Catalog ChatLTT cho người dùng hiện tại — chỉ thứ chính sách sản phẩm mời."""
    ds = chinh_sach.danh_muc(db, user_id=uid(request))
    return json_ok({"nang_luc": [
        {"ten": n.ten, "phuong_thuc": n.phuong_thuc, "che_do": n.che_do, "nhan": n.nhan,
         "models": n.models, "model_mac_dinh": n.model_mac_dinh,
         "tuy_chon": n.tuy_chon, "gia": n.gia,
         "duong_dan_app": n.duong_dan_app, "san_sang": n.san_sang, "hop_dong": n.hop_dong}
        for n in ds]})
