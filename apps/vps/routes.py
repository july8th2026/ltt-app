"""HTTP của app VPS. CHỈ lo HTTP — mọi quy tắc ở `apps/vps/services/`.

Router KHÔNG tự viết prefix `/vps`; nền tảng gắn từ `MANIFEST.route_prefix`.

## Lớp chặn thứ hai, và thứ tự của nó

`MANIFEST.enabled` đọc cờ `LTT_VPS` lúc nạp, nhưng mọi handler ở đây còn kiểm lại
qua `Depends(_cong_co)`. Hai lớp vì chúng hỏng theo hai kiểu: manifest quyết định
app có **hiện trong catalog** không; route quyết định một URL gõ thẳng có **trả
lời** không.

**Thứ tự trong chữ ký quan trọng.** `Depends` chạy theo thứ tự khai báo, nên cổng
cờ phải đứng **trước** `require_login`. Đặt sau thì một route "đã đóng" vẫn chuyển
hướng về `/login` — tức là vẫn xác nhận nó tồn tại, và vẫn bắt khách đăng nhập vào
một thứ không mở.

404 chứ không 403: 403 xác nhận bề mặt này có thật.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

import apps.vps as vps_app
from apps.vps import os_images
from apps.vps.cost import PLANS, lay_plan
from apps.vps.manifest import MANIFEST
from apps.vps.services import billing, capacity, provisioning
from apps.vps.services.proxmox import (ChuaCauHinh, ProxmoxError,
                                       client_tu_moi_truong)
from apps.vps.tables import VpsInstance, VpsIp
from platform_core.i18n import _ as _t
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import get_db, user_hien_tai
from server.templating import templates

log = logging.getLogger(__name__)

router = APIRouter(tags=["vps"])


def _cong_co() -> None:
    """Cờ tắt → 404. Đặt TRƯỚC `require_login` trong mọi chữ ký."""
    if not vps_app.enabled():
        raise HTTPException(status_code=404)


def _chu(request: Request) -> str:
    u = user_hien_tai(request)
    uid = getattr(u, "id", None)
    if not uid:
        raise HTTPException(status_code=401)
    return str(uid)


def _suc_chua(db) -> tuple[capacity.SucChua | None, str]:
    """Sức chứa hiện tại, và lý do nếu không đọc được.

    Không đọc được Proxmox **không** phải lỗi trang: trang vẫn phải mở để khách
    xem máy của mình. Nhưng nút "Tạo máy" thì phải khoá — bán khi không biết còn
    bao nhiêu chỗ là đúng thứ `capacity.py` sinh ra để phòng.
    """
    try:
        client = client_tu_moi_truong()
        return provisioning.suc_chua_hien_tai(
            db, client.trang_thai_node(), client.kho_luu_tru(),
            client.danh_sach_vm()), ""
    except ChuaCauHinh as exc:
        return None, f"chua cau hinh Proxmox: {exc}"
    except ProxmoxError as exc:
        log.warning("vps: khong doc duoc suc chua: %s", exc)
        return None, "khong ket noi duoc may chu ao"


def _may_cua_toi(db, user_id: str) -> list:
    """Máy của một khách, kèm địa chỉ đã ghép sẵn để template khỏi tính toán."""
    may = list(db.execute(
        select(VpsInstance)
        .where(VpsInstance.user_id == user_id,
               VpsInstance.trang_thai != "da_xoa")
        .order_by(VpsInstance.created_at.desc())
    ).scalars())
    if not may:
        return []

    # Địa chỉ khách gõ vào LÀ IP công khai riêng của máy — từ 2026-08-24 không
    # còn `IP:cổng`. Chưa cấp xong thì để trống, đừng hiện địa chỉ của cổng vào:
    # khách sẽ thử gõ nó và rơi vào máy người khác.
    ip_rieng = {}
    for x in db.execute(
        select(VpsIp).where(VpsIp.instance_id.in_([m.id for m in may]))
    ).scalars():
        ip_rieng.setdefault(x.instance_id, x)

    ket_qua = []
    for m in may:
        x = ip_rieng.get(m.id)
        ket_qua.append({
            "may": m,
            "plan": lay_plan(m.plan_id),
            "os": os_images.lay_os(m.os_id),
            "dia_chi": x.dia_chi if x is not None else "",
            "con_han": billing.con_han(m),
        })
    return ket_qua


@router.get("", response_class=HTMLResponse)
def trang_chinh(request: Request,
                _g: None = Depends(_cong_co),
                _u: str = Depends(require_login),
                db=Depends(get_db)):
    user_id = _chu(request)
    suc_chua, loi_ha_tang = _suc_chua(db)

    goi = []
    for p in PLANS:
        con_cho = (capacity.cho_phep_ban(suc_chua, p.id).cho_phep
                   if suc_chua is not None else False)
        goi.append({
            "plan": p,
            "credit": p.credit_thang,
            "con_cho": con_cho,
            "os": [o for o in os_images.os_ban_duoc()
                   if os_images.hop_le(p.id, o.id)[0]],
        })

    return templates.TemplateResponse(request, "vps.html", {
        "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "goi": goi,
        "may_cua_toi": _may_cua_toi(db, user_id),
        "suc_chua": suc_chua,
        "loi_ha_tang": loi_ha_tang,
        "loi": request.query_params.get("loi", ""),
    })


@router.post("/tao", response_class=HTMLResponse)
def tao_may(request: Request,
            csrf_token: str = Form(...),
            plan_id: str = Form(...),
            os_id: str = Form(...),
            vung: str = Form("port"),
            dia_them_gb: int = Form(0),
            _g: None = Depends(_cong_co),
            _u: str = Depends(require_login),
            db=Depends(get_db)):
    """Tạo một máy: kiểm điều kiện, thu chu kỳ đầu, rồi NỘP JOB.

    Không có gì chạm Proxmox trong request này. Clone + sysprep + boot lần đầu mất
    vài phút tới hơn mười, mà Cloudflare cắt request ở **100 giây** — làm đồng bộ
    thì khách nhận lỗi 524 trong khi một máy vẫn đang được tạo ở phía sau, và
    không ai biết nó tồn tại.
    """
    user_id = _chu(request)
    if not verify_csrf_token(request, csrf_token):
        return _ve_trang(_t("Phiên đã hết hạn — tải lại trang rồi thử lại."))

    plan = lay_plan(plan_id)
    if plan is None:
        return _ve_trang(_t("Gói không hợp lệ."))

    duoc, ly_do = os_images.hop_le(plan_id, os_id, dia_them_gb)
    if not duoc:
        return _ve_trang(ly_do)

    suc_chua, loi_ha_tang = _suc_chua(db)
    if suc_chua is None:
        return _ve_trang(_t("Hệ thống đang bận, chưa nhận máy mới. Thử lại sau."))
    kiem = capacity.cho_phep_ban(suc_chua, plan_id, dia_them_gb)
    if not kiem.cho_phep:
        return _ve_trang(_t("Đã hết chỗ cho cấu hình này. Vui lòng chọn gói nhỏ hơn."))

    try:
        gateway = provisioning.chon_gateway(db, vung)
    except provisioning.KhongCoGatewayError:
        return _ve_trang(_t("Vùng bạn chọn hiện không nhận máy mới."))

    may = VpsInstance(user_id=user_id, plan_id=plan_id, os_id=os_id,
                      dia_them_gb=int(dia_them_gb or 0),
                      gateway_id=gateway.id, trang_thai="dang_tao")
    db.add(may)
    db.flush()

    # Thu chu kỳ đầu TRƯỚC khi nộp job: hết credit thì không được chiếm chỗ.
    try:
        billing.thu_mot_chu_ky(db, may)
    except billing.ThieuCreditError as exc:
        db.rollback()
        return _ve_trang(_t("Không đủ credit: %(ly_do)s") % {"ly_do": exc})

    provisioning.ghi_su_kien(db, may.id, "tao_moi", boi=user_id,
                             plan_id=plan_id, os_id=os_id, vung=vung)

    from platform_core import jobs as job_queue
    job_queue.submit(db, user_id=user_id, app_slug=MANIFEST.slug,
                     job_type="vps.provision",
                     params={"instance_id": may.id})
    db.commit()
    return RedirectResponse(MANIFEST.route_prefix, status_code=303)


def _ve_trang(loi: str) -> RedirectResponse:
    """Về trang chính kèm một câu giải thích. Không dựng lại cả trang ở nhánh lỗi
    — nhánh lỗi dựng trang là chỗ hai đường code lệch nhau theo thời gian."""
    from urllib.parse import quote
    return RedirectResponse(f"{MANIFEST.route_prefix}?loi={quote(str(loi))}",
                            status_code=303)
