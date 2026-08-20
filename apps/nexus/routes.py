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
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from apps.nexus.manifest import MANIFEST
import logging

from platform_core import nexus
from platform_core.i18n import _ as _t
from platform_core.nexus import audit, devices, release, sessions
from platform_core.nexus.devices import NexusError

log = logging.getLogger(__name__)
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


def _ip(request: Request) -> str:
    """IP thật của controller (sau Cloudflare Tunnel), để ghi vào phiên."""
    from server.auth.session import client_ip

    try:
        return client_ip(request) or ""
    except Exception:                                          # noqa: BLE001
        log.exception("khong doc duoc IP controller")
        return ""


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
        loi = None
        if request.query_params.get("loi") == "khong_cap_ve":
            loi = _t("Không mở được phiên điều khiển. Nếu bạn đang bật thu phí, "
                     "hãy kiểm tra số dư credit ở thanh trên cùng.")
        return templates.TemplateResponse(request, "nexus_trang_chinh.html", {
            "user": user.email, "nav": MANIFEST.slug, "app": MANIFEST,
            "csrf_token": issue_csrf_token(request), "loi": loi,
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


@router.get("/tai", response_class=HTMLResponse)
def tai(request: Request, _u: str = Depends(require_login)):
    """Trang tải agent. Công bố SHA-256 và **nói trước** cảnh báo SmartScreen (Q95).

    Vì sao chính LTT phải nói trước cảnh báo: khách sẽ thấy nó dù thế nào (agent
    chưa ký mã). Nếu người giải thích cảnh báo đó là LTT thì nó là một bước cài
    bình thường; nếu người giải thích là **kẻ gọi điện lừa đảo** (T1) thì cùng
    cảnh báo đó thành đòn bẩy. Ai kể trước thì người đó định nghĩa nó.

    `ban` có thể là `None` (chưa phát hành) — template xử lý, không phải lỗi.
    """
    from server.templating import templates

    _bat_buoc_bat()
    _chu(request)
    ban = release.ban_phat_hanh_hien_tai()
    return templates.TemplateResponse(request, "nexus_tai.html", {
        "nav": MANIFEST.slug, "app": MANIFEST, "ban": ban,
    })


@router.post("/dieu-khien/{device_id}")
def bat_dau_dieu_khien(request: Request, device_id: str,
                       csrf_token: str = Form(...),
                       _u: str = Depends(require_login)):
    """Khách bấm 'Điều khiển' → cấp vé cho máy của CHÍNH mình, mở trang phiên.

    `cap_ve` tự cưỡng chế chủ sở hữu (Q93 ràng buộc 5), nhưng ta kiểm `cua_chu`
    trước để máy người khác trả 404 giống hệt máy không tồn tại (ràng buộc 9),
    thay vì để `cap_ve` ném một thông điệp khác.
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
            raise HTTPException(status_code=404)
        try:
            row, _ve = sessions.cap_ve(db, user_id=user.id, device=device,
                                       controller_ip=_ip(request))
        except NexusError:
            # Thuê bao hết credit (Q98) hoặc thiết bị vừa bị thu hồi: không cấp vé.
            # Quay về danh sách với gợi ý nạp; số dư + nút nạp đã ở thanh trên cùng.
            db.rollback()
            return RedirectResponse(f"{MANIFEST.route_prefix}?loi=khong_cap_ve",
                                    status_code=303)
        db.commit()
        return RedirectResponse(f"{MANIFEST.route_prefix}/phien/{row.id}",
                                status_code=303)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _phien_cua_chu(db, request: Request, session_id: str):
    """Phiên nếu là của người đang đăng nhập, hoặc 404. Không bao giờ 403 —
    một session_id của người khác không được xác nhận là có tồn tại."""
    user = _chu(request)
    phien = sessions.lay_phien(db, session_id=session_id)
    if phien is None or phien.user_id != user.id:
        raise HTTPException(status_code=404)
    return phien


@router.get("/phien/{session_id}", response_class=HTMLResponse)
def trang_phien(request: Request, session_id: str,
                _u: str = Depends(require_login)):
    """Trang một phiên điều khiển: chờ máy đích sẵn sàng, rồi hiện cách kết nối."""
    from server.templating import templates

    _bat_buoc_bat()
    gen = _mo_db()
    db = next(gen)
    try:
        phien = _phien_cua_chu(db, request, session_id)
        dev = devices.cua_chu(db, user_id=phien.user_id, device_id=phien.device_id)
        return templates.TemplateResponse(request, "nexus_dieu_khien.html", {
            "nav": MANIFEST.slug, "app": MANIFEST,
            "session_id": phien.id,
            "ten_may": dev.display_name if dev else "",
            "csrf_token": issue_csrf_token(request),
        })
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.get("/phien/{session_id}/ket-noi")
def ket_noi(request: Request, session_id: str,
            _u: str = Depends(require_login)):
    """JSON cho trang phiên hỏi liên tục: máy đích đã báo engine chưa.

    Chỉ trả mật khẩu khi phiên còn mở VÀ agent đã báo. Trước đó trả
    `san_sang=false` để trang tiếp tục chờ. Mật khẩu chỉ nằm trong phản hồi này,
    trang không cất nó — dùng xong hiển thị là thôi.
    """
    _bat_buoc_bat()
    gen = _mo_db()
    db = next(gen)
    try:
        phien = _phien_cua_chu(db, request, session_id)
        try:
            kn = sessions.lay_ket_noi(db, phien, user_id=phien.user_id)
        except NexusError:
            # `lay_ket_noi` ném NexusError cho MỌI trạng thái "chưa sẵn sàng"
            # (chưa báo, đã đóng, hết hạn) — đó là trạng thái, không phải lỗi, nên
            # trang cứ hỏi tiếp. Bắt HẸP: một lỗi khác (vd giải mã hỏng) phải nổi
            # lên chứ không đội lốt "chưa sẵn sàng".
            dong = phien.ended_at is not None or phien.revoked_at is not None
            return JSONResponse({"san_sang": False, "da_dong": dong},
                                headers={"Cache-Control": "no-store"})
        return JSONResponse({
            "san_sang": True,
            "server": "45.76.185.75",
            "engine_id": kn["engine_id"],
            "mat_khau": kn["secret"],
            "quyen": kn["quyen"],
        }, headers={"Cache-Control": "no-store"})
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/phien/{session_id}/ket-thuc")
def ket_thuc_phien(request: Request, session_id: str,
                   csrf_token: str = Form(...),
                   _u: str = Depends(require_login)):
    """Khách bấm 'Kết thúc' → đóng phiên (xoá mật khẩu ngay, W2)."""
    _bat_buoc_bat()
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse(MANIFEST.route_prefix, status_code=303)
    gen = _mo_db()
    db = next(gen)
    try:
        phien = _phien_cua_chu(db, request, session_id)
        sessions.ket_thuc(db, phien)
        db.commit()
        return RedirectResponse(MANIFEST.route_prefix, status_code=303)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


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
