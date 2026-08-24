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

from fastapi import (APIRouter, Depends, Form, HTTPException, Request,
                     WebSocket, WebSocketDisconnect)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

import apps.vps as vps_app
from apps.vps import os_images
from apps.vps.cost import PLANS, lay_plan
from apps.vps.manifest import MANIFEST
from apps.vps.services import (billing, capacity, console, dieu_khien,
                               provisioning)
from apps.vps.services.proxmox import (ChuaCauHinh, ProxmoxError,
                                       client_tu_moi_truong)
from apps.vps.tables import VpsEvent, VpsInstance, VpsIp
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
            "con_ngay": billing.con_bao_nhieu_ngay(m),
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


# ── vòng đời một máy ─────────────────────────────────────────────────────────

def _may_cua_khach(db, request: Request, instance_id: str) -> VpsInstance:
    """Lấy máy VÀ kiểm nó thuộc về người đang đăng nhập.

    404 chứ không 403 khi máy của người khác: 403 xác nhận id đó có thật, và
    một danh sách id có thật là thứ đầu tiên người ta dò.
    """
    may = db.get(VpsInstance, str(instance_id or ""))
    if may is None or str(may.user_id) != _chu(request):
        raise HTTPException(status_code=404)
    return may


def _thao_tac(request: Request, csrf_token: str, instance_id: str, db, ham):
    """Khuôn chung của bật/tắt/khởi động lại: CSRF → chủ sở hữu → gọi → về trang.

    Ba thao tác này chạy THẲNG, không qua hàng đợi — xem docstring của
    `services/dieu_khien.py`.
    """
    if not verify_csrf_token(request, csrf_token):
        return _ve_trang(_t("Phiên đã hết hạn — tải lại trang rồi thử lại."))
    may = _may_cua_khach(db, request, instance_id)
    try:
        client = client_tu_moi_truong()
    except ChuaCauHinh:
        return _ve_trang(_t("Hệ thống đang bận, thử lại sau."))
    try:
        ham(db, may, client, boi=_chu(request))
    except dieu_khien.KhongDuocPhepError as exc:
        return _ve_trang(str(exc))
    except ProxmoxError as exc:
        log.warning("VPS: thao tac tren may %s that bai: %s", may.id, exc)
        return _ve_trang(_t("Máy chủ không nhận lệnh lúc này. Thử lại sau ít phút."))
    return RedirectResponse(f"{MANIFEST.route_prefix}/{may.id}", status_code=303)


@router.post("/{instance_id}/bat")
def bat_may(instance_id: str, request: Request, csrf_token: str = Form(...),
            _g: None = Depends(_cong_co), _u: str = Depends(require_login),
            db=Depends(get_db)):
    return _thao_tac(request, csrf_token, instance_id, db, dieu_khien.bat)


@router.post("/{instance_id}/tat")
def tat_may(instance_id: str, request: Request, csrf_token: str = Form(...),
            _g: None = Depends(_cong_co), _u: str = Depends(require_login),
            db=Depends(get_db)):
    return _thao_tac(request, csrf_token, instance_id, db, dieu_khien.tat)


@router.post("/{instance_id}/khoi-dong-lai")
def khoi_dong_lai_may(instance_id: str, request: Request,
                      csrf_token: str = Form(...),
                      _g: None = Depends(_cong_co),
                      _u: str = Depends(require_login), db=Depends(get_db)):
    return _thao_tac(request, csrf_token, instance_id, db, dieu_khien.khoi_dong_lai)


@router.post("/{instance_id}/cai-lai")
def cai_lai_may(instance_id: str, request: Request, csrf_token: str = Form(...),
                xac_nhan: str = Form(""), os_id: str = Form(""),
                _g: None = Depends(_cong_co), _u: str = Depends(require_login),
                db=Depends(get_db)):
    """Cài lại từ đầu. **Mất sạch dữ liệu**, nên đòi gõ đúng tên máy để xác nhận.

    Khuôn của GitHub, và lý do giống hệt: nút này không hoàn tác được, nên nó
    phải khó bấm nhầm hơn một cú click.
    """
    if not verify_csrf_token(request, csrf_token):
        return _ve_trang(_t("Phiên đã hết hạn — tải lại trang rồi thử lại."))
    may = _may_cua_khach(db, request, instance_id)
    if str(xac_nhan).strip() != (may.ten or may.id[:8]):
        return _ve_trang(_t("Gõ đúng tên máy để xác nhận cài lại."))
    if may.trang_thai in ("dang_tao", "da_xoa"):
        return _ve_trang(_t("Máy đang bận hoặc đã bị xoá."))

    if os_id and not os_images.hop_le(may.plan_id, os_id, may.dia_them_gb)[0]:
        return _ve_trang(os_images.hop_le(may.plan_id, os_id, may.dia_them_gb)[1])

    may.trang_thai = "dang_tao"
    provisioning.ghi_su_kien(db, may.id, "xin_cai_lai", boi=_chu(request),
                             os_id=os_id or may.os_id)
    from platform_core import jobs as job_queue
    job_queue.submit(db, user_id=_chu(request), app_slug=MANIFEST.slug,
                     job_type="vps.rebuild",
                     params={"instance_id": may.id, "os_id": os_id or ""})
    db.commit()
    return RedirectResponse(f"{MANIFEST.route_prefix}/{may.id}", status_code=303)


@router.post("/{instance_id}/xoa")
def xoa_may(instance_id: str, request: Request, csrf_token: str = Form(...),
            xac_nhan: str = Form(""),
            _g: None = Depends(_cong_co), _u: str = Depends(require_login),
            db=Depends(get_db)):
    """Xoá vĩnh viễn. Không hoàn tác được — cũng đòi gõ đúng tên máy."""
    if not verify_csrf_token(request, csrf_token):
        return _ve_trang(_t("Phiên đã hết hạn — tải lại trang rồi thử lại."))
    may = _may_cua_khach(db, request, instance_id)
    if str(xac_nhan).strip() != (may.ten or may.id[:8]):
        return _ve_trang(_t("Gõ đúng tên máy để xác nhận xoá."))
    if may.trang_thai == "da_xoa":
        return RedirectResponse(MANIFEST.route_prefix, status_code=303)

    provisioning.ghi_su_kien(db, may.id, "xin_xoa", boi=_chu(request))
    from platform_core import jobs as job_queue
    job_queue.submit(db, user_id=_chu(request), app_slug=MANIFEST.slug,
                     job_type="vps.destroy",
                     params={"instance_id": may.id, "boi": _chu(request)})
    db.commit()
    return RedirectResponse(MANIFEST.route_prefix, status_code=303)


@router.get("/{instance_id}", response_class=HTMLResponse)
def trang_chi_tiet(instance_id: str, request: Request,
                   _g: None = Depends(_cong_co),
                   _u: str = Depends(require_login), db=Depends(get_db)):
    may = _may_cua_khach(db, request, instance_id)
    ip = db.execute(
        select(VpsIp).where(VpsIp.instance_id == may.id)).scalars().first()
    su_kien = db.execute(
        select(VpsEvent).where(VpsEvent.instance_id == may.id)
        .order_by(VpsEvent.created_at.desc()).limit(20)).scalars().all()
    return templates.TemplateResponse(request, "vps_chi_tiet.html", {
        "nav": MANIFEST.slug, "app": MANIFEST,
        "may": may,
        "plan": lay_plan(may.plan_id),
        "os": os_images.lay_os(may.os_id),
        "dia_chi": ip.dia_chi if ip is not None else "",
        "con_han": billing.con_han(may),
        "con_ngay": billing.con_bao_nhieu_ngay(may),
        "su_kien": su_kien,
        "os_ban_duoc": os_images.os_ban_duoc(),
        "csrf_token": issue_csrf_token(request),
        "loi": request.query_params.get("loi", ""),
    })


# ── console trong trình duyệt ────────────────────────────────────────────────

@router.get("/{instance_id}/console", response_class=HTMLResponse)
def trang_console(instance_id: str, request: Request,
                  _g: None = Depends(_cong_co),
                  _u: str = Depends(require_login), db=Depends(get_db)):
    """Trang chứa noVNC. Vé cấp ở đây, tiêu ở bước mở WebSocket.

    Vé đi qua **query string của WebSocket**, không qua cookie: WebSocket không
    có CSRF, và một cookie tự động gửi kèm nghĩa là bất kỳ trang nào cũng mở
    được console của khách bằng một dòng JavaScript.
    """
    may = _may_cua_khach(db, request, instance_id)
    try:
        dieu_khien.kiem_dieu_khien_duoc(may)
    except dieu_khien.KhongDuocPhepError as exc:
        return _ve_trang(str(exc))

    # Mở phiên VNC NGAY Ở ĐÂY, không ở bước WebSocket: vé của Proxmox vừa là
    # query `vncticket` của URL (server dùng) vừa là **mật khẩu VNC** trong bước
    # bắt tay RFB (trình duyệt dùng). Gọi hai lần là hai phiên khác nhau, và vé
    # của phiên B không mở được cổng của phiên A.
    try:
        ve_pve = client_tu_moi_truong().ve_console(int(may.vmid))
    except (ProxmoxError, ChuaCauHinh) as exc:
        log.warning("VPS console: khong mo duoc phien VNC cho %s: %s", may.id, exc)
        return _ve_trang(_t("Không mở được console lúc này. Thử lại sau ít phút."))

    return templates.TemplateResponse(request, "vps_console.html", {
        "nav": MANIFEST.slug, "app": MANIFEST,
        "may": may,
        "ve": console.cap_ve(db, may, _chu(request),
                             cong=ve_pve.get("port") or 0,
                             pve_ve=ve_pve.get("ticket") or ""),
        # Trình duyệt cần vé này làm mật khẩu VNC. Nó chỉ mở được ĐÚNG cổng của
        # phiên này, trên một máy chủ mà khách không biết địa chỉ — chính giao
        # diện Proxmox cũng làm y như vậy với người dùng của nó.
        "vnc_mat_khau": ve_pve.get("ticket") or "",
        "han_ve_giay": console.HAN_VE_GIAY,
    })


@router.websocket("/{instance_id}/console/ws")
async def cau_console(websocket: WebSocket, instance_id: str, ve: str = ""):
    """Bắc cầu byte giữa trình duyệt khách và console của Proxmox.

    Khách **không bao giờ** biết địa chỉ Proxmox và không bao giờ cầm vé của
    Proxmox — nếu chạm được cổng 8006 thì họ chạm được giao diện quản trị của cả
    cụm, nơi có mọi máy của mọi khách và nút xoá của từng cái.

    Không dùng `Depends` ở đây: WebSocket của FastAPI không chạy chuỗi phụ thuộc
    giống HTTP, và trộn hai đường xác thực là cách chắc chắn để một trong hai bị
    bỏ quên. Tất cả kiểm tra nằm tường minh trong thân hàm.
    """
    import asyncio
    import ssl as ssl_mod

    if not vps_app.enabled():
        await websocket.close(code=1008)
        return

    from platform_core.db import get_session

    # `user_hien_tai` nhận bất cứ thứ gì có `.session`, và Starlette gắn session
    # cho CẢ WebSocket — nên không cần đường xác thực thứ hai. Hai đường xác
    # thực là cách chắc chắn để một trong hai bị bỏ quên.
    u = user_hien_tai(websocket)
    user_id = str(getattr(u, "id", "") or "")
    if not user_id:
        await websocket.close(code=1008)
        return

    gen = get_session()
    db = next(gen)
    try:
        may, cong, pve_ve = console.tieu_ve(db, ve, instance_id, user_id)
        client = client_tu_moi_truong()
        # Dùng lại ĐÚNG phiên VNC đã mở ở trang console. Gọi `ve_console` lần
        # nữa ở đây là mở một cổng mới, và vé của cổng B không mở được cổng A.
        dia_chi = console.dia_chi_websocket_proxmox(
            client.config, int(may.vmid), {"port": cong, "ticket": pve_ve})
    except (console.VeKhongHopLeError, ProxmoxError, ChuaCauHinh) as exc:
        log.warning("VPS console: tu choi mo cau: %s", exc)
        await websocket.close(code=1008)
        return
    finally:
        gen.close()

    import websockets

    ctx = ssl_mod.create_default_context()
    if not client.config.verify:
        # Cụm dùng chứng chỉ tự ký. Đây là kết nối TỪ SERVER MÌNH tới Proxmox
        # trong LAN, không phải kết nối của khách — cùng mức tin cậy với mọi lời
        # gọi API khác trong `proxmox.py`.
        ctx.check_hostname = False
        ctx.verify_mode = ssl_mod.CERT_NONE

    await websocket.accept(subprotocol="binary")
    try:
        async with websockets.connect(
                dia_chi, ssl=ctx, subprotocols=["binary"],
                additional_headers=client._headers(), open_timeout=20) as pve:
            # KHÔNG gửi dòng `user:ticket` nào ở đây. Đó là giao thức của
            # `termproxy` (xterm.js); `vncproxy` thì vé là **mật khẩu VNC** và
            # nó đi qua bước bắt tay RFB do trình duyệt thực hiện. Chèn một dòng
            # chữ vào giữa luồng nhị phân VNC làm Proxmox đóng kết nối ngay và
            # KHÔNG NÓI GÌ — triệu chứng chỉ là "console trắng". Mất một buổi
            # 24/08 để tìm ra, và chỉ tìm ra khi mở trình duyệt thật.

            async def khach_toi_pve():
                while True:
                    goi = await websocket.receive()
                    if goi.get("type") == "websocket.disconnect":
                        return
                    await pve.send(goi.get("bytes") or goi.get("text") or b"")

            async def pve_toi_khach():
                async for goi in pve:
                    if isinstance(goi, bytes):
                        await websocket.send_bytes(goi)
                    else:
                        await websocket.send_text(goi)

            xong, con_lai = await asyncio.wait(
                {asyncio.create_task(khach_toi_pve()),
                 asyncio.create_task(pve_toi_khach())},
                return_when=asyncio.FIRST_COMPLETED)
            for t in con_lai:
                t.cancel()
    except WebSocketDisconnect:
        pass
    except Exception as exc:            # noqa: BLE001 - biên của một cầu nối
        log.warning("VPS console: cau dut giua chung: %s: %s",
                    type(exc).__name__, exc)
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            pass                        # khách đã đóng trước


def _ve_trang(loi: str) -> RedirectResponse:
    """Về trang chính kèm một câu giải thích. Không dựng lại cả trang ở nhánh lỗi
    — nhánh lỗi dựng trang là chỗ hai đường code lệch nhau theo thời gian."""
    from urllib.parse import quote
    return RedirectResponse(f"{MANIFEST.route_prefix}?loi={quote(str(loi))}",
                            status_code=303)
