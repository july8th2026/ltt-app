"""Ba đường cho agent: ghép máy, nhịp tim, đổi vé phiên.

Mọi đường đều fail-closed sau cờ `LTT_NEXUS`, và mọi đường trả **JSON**.

## Giới hạn nhịp nằm ở đây, không ở domain

`platform_core.nexus.devices` nói rõ nó **không** tự giới hạn nhịp, và rằng đó là
việc của route. Đây là chỗ trả nợ câu đó. Hai trần khác nhau cho hai loại nguy
hiểm khác nhau:

* **ghép máy** — mã 8 ký tự từ bảng 32 ký tự (40 bit) sống 5 phút. Entropy đã
  lớn, nhưng không có trần thì một kẻ tấn công vẫn được thử tuỳ ý, và toán học
  chỉ cần vài triệu lần thử là chuyện của một buổi chiều. Trần theo **IP**;
* **nhịp tim** — không nguy hiểm về bảo mật, nhưng một agent hỏng vòng lặp có thể
  gõ cửa hàng nghìn lần một phút. Trần theo **thiết bị**.

Dùng lại `platform_core.public_api.limits` chứ không viết bộ đếm thứ hai: nó đã
có sẵn cửa sổ trượt và đã được đo tải ở H35.

## Vì sao mọi lời từ chối đều nói cùng một câu

Giống mã ghép và vé phiên: phân biệt "sai chữ ký" với "thiết bị đã thu hồi" cho
kẻ dò biết mình đang tới gần. Chỉ có **một** thông điệp cho mọi lý do xác thực
thất bại, và mã HTTP là `401` cho mọi trường hợp.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from platform_core import nexus
from platform_core.nexus import agent_auth, devices, sessions

log = logging.getLogger(__name__)

router = APIRouter(prefix="/nexus-agent", tags=["nexus-agent"])

_NO_STORE = {"Cache-Control": "no-store"}

#: Trần cho việc đổi mã ghép, theo IP. Cố ý thấp: người thật ghép một máy vài
#: lần một ngày, còn kẻ dò cần hàng nghìn lần mới có cơ hội.
GHEP_MOI_PHUT = 10

#: Trần nhịp tim theo thiết bị. Nhịp thật là mỗi 60 giây; 20 cho phép thử lại
#: khi mạng chập chờn mà vẫn chặn một vòng lặp hỏng.
NHIP_TIM_MOI_PHUT = 20


def _loi(status: int, ma: str, thong_diep: str) -> JSONResponse:
    """Lỗi dạng JSON. Không bao giờ HTML — bên gọi là máy."""
    return JSONResponse({"error": {"code": ma, "message": thong_diep}},
                        status_code=status, headers=_NO_STORE)


def _tat() -> JSONResponse:
    """Cờ tắt → 404, cùng lý do như bề mặt khách: 403 xác nhận có tồn tại."""
    return _loi(404, "not_found", "Not found.")


def _ip(request: Request) -> str:
    """IP thật sau Cloudflare Tunnel.

    Dùng lại đường đã có của nền tảng thay vì đọc `request.client` — sau Tunnel
    thì `request.client` là địa chỉ của tunnel, nên giới hạn theo nó sẽ gộp mọi
    người dùng trên thế giới vào một xô.
    """
    from server.auth.session import client_ip

    try:
        return client_ip(request) or ""
    except Exception:                                          # noqa: BLE001
        log.exception("khong doc duoc IP that")
        return ""


def _qua_tran(khoa: str, moi_phut: int) -> bool:
    from platform_core.public_api import limits

    duoc_phep, _thu_lai = limits.allow(khoa, moi_phut, window_s=60)
    return not duoc_phep


def _mo_db():
    from platform_core.db import get_session

    return get_session()


@router.post("/enroll")
async def enroll(request: Request):
    """Đổi mã ghép lấy một thiết bị được tin.

    Đường này **không** ký được: agent chưa có danh tính nào để ký bằng. Nó là
    đúng một cửa vào, và vì vậy nó là đường duy nhất có trần theo IP.
    """
    if not nexus.enabled():
        return _tat()

    ip = _ip(request)
    if _qua_tran(f"nexus-enroll:{ip}", GHEP_MOI_PHUT):
        return _loi(429, "rate_limited", "Too many attempts. Try again later.")

    try:
        body = await request.json()
    except (ValueError, UnicodeDecodeError):
        # Hep chu khong bat `Exception`: body hong la loi cua NGUOI GOI va tra
        # 400 la dung. Con mot loi khac o day (vd CSDL, mang) thi phai noi ra
        # chu khong duoc doi lot thanh "body sai dinh dang".
        return _loi(400, "invalid_request", "Body must be JSON.")
    if not isinstance(body, dict):
        return _loi(400, "invalid_request", "Body must be a JSON object.")

    gen = _mo_db()
    db = next(gen)
    try:
        device = devices.doi_ma(
            db,
            code=str(body.get("code") or ""),
            public_key=str(body.get("public_key") or ""),
            display_name=str(body.get("display_name") or "")[:120],
            hardware_fingerprint=str(body.get("hardware_fingerprint") or "")[:128],
            platform=str(body.get("platform") or "")[:32],
            agent_version=str(body.get("agent_version") or "")[:32],
            ip=ip)
        db.commit()
        return JSONResponse({"device_id": device.id,
                             "display_name": device.display_name},
                            headers=_NO_STORE)
    except devices.NexusError as exc:
        db.rollback()
        # Mot thong diep cho moi ly do. Xem docstring module.
        return _loi(400, "enroll_failed", str(exc))
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


async def _xac_thuc(request: Request, device_id: str, timestamp: str,
                    signature: str, db):
    """Thiết bị đã ký request này, hoặc None.

    Trả `None` chứ không ném, để nơi gọi quyết định mã HTTP — và để **một** câu
    từ chối dùng cho mọi lý do.
    """
    if not device_id or not timestamp or not signature:
        return None
    row = db.get(devices.NexusDevice, device_id)
    if row is None or row.revoked_at is not None:
        return None
    try:
        agent_auth.verify(public_key=row.public_key, signature=signature,
                          method=request.method, path=request.url.path,
                          timestamp=timestamp, body=await request.body())
    except agent_auth.AgentAuthError:
        return None
    return row


@router.post("/heartbeat")
async def heartbeat(
    request: Request,
    device_id: str = Header(default="", alias=agent_auth.HEADER_DEVICE),
    timestamp: str = Header(default="", alias=agent_auth.HEADER_TIMESTAMP),
    signature: str = Header(default="", alias=agent_auth.HEADER_SIGNATURE),
):
    """Tôi còn sống. Trả về việc thiết bị có còn được tin không.

    Trả `revoked` tường minh thay vì chỉ `401`: agent cần biết **dừng hẳn** thay
    vì thử lại mãi. Điều đó không lộ gì cho kẻ tấn công — nó phải ký được bằng
    khoá riêng của chính thiết bị mới nhận được câu trả lời này.
    """
    if not nexus.enabled():
        return _tat()

    gen = _mo_db()
    db = next(gen)
    try:
        device = await _xac_thuc(request, device_id, timestamp, signature, db)
        if device is None:
            return _loi(401, "unauthorized", "Invalid or missing signature.")
        if _qua_tran(f"nexus-hb:{device.id}", NHIP_TIM_MOI_PHUT):
            return _loi(429, "rate_limited", "Too many heartbeats.")

        con_dung = devices.nhip_tim(db, device)
        cho_phien = [{"session_id": s.id, "quyen": s.quyen}
                     for s in sessions.dang_mo(db, device_id=device.id)]
        db.commit()
        return JSONResponse({"ok": con_dung, "revoked": not con_dung,
                             "sessions": cho_phien}, headers=_NO_STORE)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/session/redeem")
async def redeem(
    request: Request,
    device_id: str = Header(default="", alias=agent_auth.HEADER_DEVICE),
    timestamp: str = Header(default="", alias=agent_auth.HEADER_TIMESTAMP),
    signature: str = Header(default="", alias=agent_auth.HEADER_SIGNATURE),
):
    """Đổi vé phiên. Chỉ **thiết bị đích** đổi được vé của chính nó.

    Hai phép kiểm độc lập, và cả hai đều cần: chữ ký chứng minh *ai đang gọi*,
    còn `session.device_id` chứng minh *vé này dành cho ai*. Thiếu phép thứ hai
    thì một thiết bị hợp lệ đổi được vé của thiết bị khác.
    """
    if not nexus.enabled():
        return _tat()

    body_raw = await request.body()
    gen = _mo_db()
    db = next(gen)
    try:
        device = await _xac_thuc(request, device_id, timestamp, signature, db)
        if device is None:
            return _loi(401, "unauthorized", "Invalid or missing signature.")

        try:
            import json
            body = json.loads(body_raw or b"{}")
        except (ValueError, UnicodeDecodeError):
            return _loi(400, "invalid_request", "Body must be JSON.")

        try:
            phien = sessions.doi_ve(db, ticket=str((body or {}).get("ticket") or ""))
        except devices.NexusError as exc:
            db.rollback()
            return _loi(400, "redeem_failed", str(exc))

        if phien.device_id != device.id:
            # Ve cua thiet bi khac. Doi ve da tieu no o tren, nen phai huy.
            db.rollback()
            return _loi(400, "redeem_failed", "That session ticket cannot be used.")

        db.commit()
        return JSONResponse({"session_id": phien.id, "quyen": phien.quyen},
                            headers=_NO_STORE)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
