"""
webhooks.py — nhận callback cổng thanh toán (H9). CÔNG KHAI (không đăng nhập),
nhưng **bắt buộc chữ ký** — đây là ranh giới tiền vào hệ thống.

Miễn CSRF: đây là API máy-gọi-máy, không phải form trình duyệt. An toàn đến từ
chữ ký HMAC của cổng, không phải token CSRF.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["webhooks"])
_log = logging.getLogger("ltt.webhook")


@router.post("/webhooks/payment/payos")
async def payos_webhook(request: Request):
    from platform_core import payments
    from platform_core.payments import ChuKyKhongHopLe, GatewayChuaCauHinh

    gw = payments.get("payos")
    raw = await request.body()
    try:
        ket_qua = gw.xac_thuc_webhook(dict(request.headers), raw)
    except GatewayChuaCauHinh:
        _log.warning("PayOS webhook nhung cong chua cau hinh")
        return JSONResponse({"success": False, "message": "gateway not configured"},
                            status_code=503)
    except ChuKyKhongHopLe:
        _log.warning("PayOS webhook chu ky sai -> tu choi")
        return JSONResponse({"success": False, "message": "invalid signature"},
                            status_code=400)

    # Chữ ký hợp lệ. Cộng credit nếu đã trả (idempotent). Đơn không tồn tại =
    # có thể là ping xác minh endpoint của PayOS -> vẫn ack 200.
    if ket_qua.get("paid"):
        from platform_core.db import get_session
        from platform_core import billing
        gen = get_session(); db = next(gen)
        try:
            order = billing.ghi_nhan_tra(
                db, int(ket_qua["order_code"]),
                gateway_ref=str(ket_qua.get("ref") or ""), by="payos-webhook")
            db.commit()
            if order is not None:
                _log.info("PayOS webhook: don %s da cong credit", ket_qua["order_code"])
        finally:
            try: next(gen)
            except StopIteration: pass
    return JSONResponse({"success": True})
