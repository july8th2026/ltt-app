"""HTTP của bề mặt khách hàng Nexus. Chỉ lo HTTP — nghiệp vụ ở `platform_core.nexus`.

Router này KHÔNG tự viết prefix `/nexus`; nền tảng gắn từ `MANIFEST.route_prefix`.

## Lớp chặn thứ hai

`MANIFEST.enabled` đã đọc cờ `LTT_NEXUS` lúc nạp, nhưng mọi handler ở đây còn
gọi `_bat_buoc_bat()` lần nữa. Hai lớp vì chúng hỏng theo hai kiểu khác nhau:
manifest quyết định app có **hiện trong catalog** không, còn route quyết định
một URL gõ thẳng có **trả lời** không. Chỉ có lớp đầu thì cờ tắt vẫn để lộ một
bề mặt cho ai biết đường dẫn.

## Ở đây KHÔNG có đường đổi mã ghép

Đổi mã là việc của **agent trên máy khách**, không phải của trình duyệt — nên nó
thuộc bề mặt `server/nexus/` (Q93: HTTP cho endpoint/relay), chưa dựng. Đó cũng
là chỗ phải đặt rate-limit mà `platform_core.nexus.devices` nói rõ nó không tự
làm. Ghi ra đây vì "route nào chịu trách nhiệm giới hạn nhịp" là loại câu hỏi
nếu không có câu trả lời viết sẵn thì sẽ không ai trả lời.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from apps.nexus.manifest import MANIFEST
from platform_core import nexus
from platform_core.i18n import _ as _t
from platform_core.nexus import audit, devices, sessions
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import user_hien_tai

router = APIRouter(tags=["nexus"])


def _bat_buoc_bat() -> None:
    """Cờ tắt → 404, không phải 403.

    404 vì 403 xác nhận rằng bề mặt này có tồn tại — với một sản phẩm điều khiển
    máy từ xa thì ngay cả việc đó cũng không nên nói.
    """
    if not nexus.enabled():
        raise HTTPException(status_code=404)


def _chu(request: Request):
    """Người dùng trong CSDL. Admin break-glass (Q29) không có hàng `users`."""
    user = user_hien_tai(request)
    if user is None:
        raise HTTPException(status_code=404)
    return user


def _mo_db():
    from platform_core.db import get_session

    return get_session()


@router.get("", response_class=HTMLResponse)
def trang_chinh(request: Request, _u: str = Depends(require_login)):
    from server.templating import templates

    _bat_buoc_bat()
    gen = _mo_db()
    db = next(gen)
    try:
        user = _chu(request)
        danh_sach = [
            {"row": row, "online": devices.dang_online(row),
             "phien": sessions.dang_mo(db, device_id=row.id)}
            for row in devices.danh_sach(db, user_id=user.id)
        ]
        return templates.TemplateResponse(request, "nexus_trang_chinh.html", {
            "user": user.email, "nav": MANIFEST.slug, "app": MANIFEST,
            "csrf_token": issue_csrf_token(request),
            "thiet_bi": danh_sach,
            "dong_thoi_gian": audit.dong_thoi_gian(db, user_id=user.id, limit=30),
            "do_admin_lam": audit.do_admin_lam,
            "nhan": _nhan_su_kien(),
            # Câu xác nhận đi từ đây chứ không viết trong template: lồng dấu
            # ngoặc kép vào `onsubmit="… confirm('…')"` làm vỡ thuộc tính HTML
            # giữa câu, và bản đầu của template này đã vỡ đúng như vậy.
            "xac_nhan_thu_hoi": _t(
                'Thu hồi máy này? Mọi phiên đang chạy sẽ bị cắt ngay.'),
        })
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/ma-ghep", response_class=HTMLResponse)
def tao_ma(request: Request, csrf_token: str = Form(...),
           _u: str = Depends(require_login)):
    """Sinh mã ghép và hiện nó **một lần**.

    Trang này cố ý nói bằng ngôn ngữ hậu quả chứ không phải ngôn ngữ kỹ thuật
    (Q93 ràng buộc 8): người đọc phải hiểu rằng đưa mã này đi là đưa cả máy.
    """
    from server.templating import templates

    _bat_buoc_bat()
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse(MANIFEST.route_prefix, status_code=303)

    gen = _mo_db()
    db = next(gen)
    try:
        user = _chu(request)
        row, ma = devices.tao_ma_ghep(db, user_id=user.id)
        db.commit()
        return templates.TemplateResponse(request, "nexus_ma_ghep.html", {
            "user": user.email, "nav": MANIFEST.slug, "app": MANIFEST,
            "ma": devices.format_code(ma),
            "het_han_luc": row.expires_at,
        })
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/thu-hoi/{device_id}")
def thu_hoi(request: Request, device_id: str, csrf_token: str = Form(...),
            _u: str = Depends(require_login)):
    """Thu hồi một thiết bị và **cắt luôn mọi phiên đang chạy trên nó**.

    Thu hồi mà để phiên đang chạy tiếp là thu hồi trên giấy: người đang điều
    khiển vẫn đang điều khiển.
    """
    _bat_buoc_bat()
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse(MANIFEST.route_prefix, status_code=303)

    gen = _mo_db()
    db = next(gen)
    try:
        user = _chu(request)
        device = devices.cua_chu(db, user_id=user.id, device_id=device_id)
        if device is None:
            # Máy của người khác và máy không tồn tại phải giống hệt nhau
            # (Q93 ràng buộc 9).
            raise HTTPException(status_code=404)
        for phien in sessions.dang_mo(db, device_id=device.id):
            sessions.thu_hoi_ve(db, phien, by=devices_boi_chu())
        devices.thu_hoi(db, device, by=devices_boi_chu())
        db.commit()
        return RedirectResponse(MANIFEST.route_prefix, status_code=303)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def devices_boi_chu() -> str:
    """Chính chủ thao tác. Tách thành hàm để không ai gõ nhầm chuỗi ở hai chỗ —
    `audit.do_admin_lam` phân biệt admin với chủ bằng đúng chuỗi này."""
    return audit.BOI_CHU


def _nhan_su_kien() -> dict:
    """Tên sự kiện bằng tiếng khách hàng. Một chỗ duy nhất.

    Hai trang cùng hiện dòng thời gian; nếu mỗi trang tự dịch thì có ngày cùng
    một sự kiện mang hai tên khác nhau, và khách sẽ tưởng đó là hai việc.
    """
    return {
        audit.GHEP: _t('Ghép máy'),
        audit.THU_HOI_THIET_BI: _t('Thu hồi máy'),
        audit.CAP_VE: _t('Cấp vé phiên'),
        audit.BAT_DAU_PHIEN: _t('Bắt đầu điều khiển'),
        audit.KET_THUC_PHIEN: _t('Kết thúc phiên'),
        audit.THU_HOI_PHIEN: _t('Cắt phiên'),
    }


@router.get("/nhat-ky", response_class=HTMLResponse)
def nhat_ky(request: Request, _u: str = Depends(require_login)):
    """Ai đã vào máy tôi. Đây là bề mặt của **khách**, không phải của admin."""
    from server.templating import templates

    _bat_buoc_bat()
    gen = _mo_db()
    db = next(gen)
    try:
        user = _chu(request)
        return templates.TemplateResponse(request, "nexus_nhat_ky.html", {
            "user": user.email, "nav": MANIFEST.slug, "app": MANIFEST,
            "dong_thoi_gian": audit.dong_thoi_gian(db, user_id=user.id, limit=200),
            "do_admin_lam": audit.do_admin_lam,
            "nhan": _nhan_su_kien(),
        })
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
