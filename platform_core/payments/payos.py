"""
payos.py — adapter PayOS (H9, Q31). VietQR + webhook ký HMAC-SHA256.

Credential đọc từ env (`secrets\app.env` trên máy chủ):
- `LTT_PAYOS_CLIENT_ID`, `LTT_PAYOS_API_KEY`, `LTT_PAYOS_CHECKSUM_KEY`
- `LTT_PAYOS_BASE_URL` (tuỳ, mặc định api-merchant.payos.vn)

Thiếu bất kỳ khoá nào → `da_cau_hinh()` False và mọi thao tác ném
`GatewayChuaCauHinh` → nền tảng tắt mềm phần thanh toán (dev/test chạy được).

Chữ ký PayOS: ghép các trường theo THỨ TỰ KHOÁ tăng dần thành
`k1=v1&k2=v2&...` rồi HMAC-SHA256 hex bằng `checksumKey`. Dùng cho CẢ tạo thanh
toán (amount, cancelUrl, description, orderCode, returnUrl) LẪN verify webhook
(ký lại toàn bộ object `data`).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os

from platform_core.payments import (ChuKyKhongHopLe, GatewayChuaCauHinh,
                                     GatewayError)

DEFAULT_BASE_URL = "https://api-merchant.payos.vn"


def _sap_xep_ky(checksum_key: str, data: dict) -> str:
    """Ghép data theo khoá tăng dần -> HMAC-SHA256 hex. None -> chuỗi rỗng."""
    parts = []
    for k in sorted(data.keys()):
        v = data[k]
        parts.append(f"{k}={'' if v is None else v}")
    canon = "&".join(parts)
    return hmac.new(checksum_key.encode("utf-8"), canon.encode("utf-8"),
                    hashlib.sha256).hexdigest()


class PayOSGateway:
    id = "payos"

    def __init__(self) -> None:
        self.client_id = (os.environ.get("LTT_PAYOS_CLIENT_ID") or "").strip()
        self.api_key = (os.environ.get("LTT_PAYOS_API_KEY") or "").strip()
        self.checksum_key = (os.environ.get("LTT_PAYOS_CHECKSUM_KEY") or "").strip()
        self.base_url = (os.environ.get("LTT_PAYOS_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    def da_cau_hinh(self) -> bool:
        return bool(self.client_id and self.api_key and self.checksum_key)

    def _bat_buoc_cau_hinh(self) -> None:
        if not self.da_cau_hinh():
            raise GatewayChuaCauHinh(
                "PayOS chua co credential (LTT_PAYOS_CLIENT_ID/API_KEY/CHECKSUM_KEY)")

    def chu_ky_tao(self, *, amount_vnd: int, cancel_url: str, description: str,
                   order_code: int, return_url: str) -> str:
        """Chữ ký cho yêu cầu tạo thanh toán (5 trường bắt buộc, theo thứ tự khoá)."""
        return _sap_xep_ky(self.checksum_key, {
            "amount": amount_vnd, "cancelUrl": cancel_url, "description": description,
            "orderCode": order_code, "returnUrl": return_url,
        })

    def tao_thanh_toan(self, *, order_code: int, amount_vnd: int, description: str,
                       return_url: str, cancel_url: str, timeout: int = 15) -> dict:
        self._bat_buoc_cau_hinh()
        sig = self.chu_ky_tao(amount_vnd=amount_vnd, cancel_url=cancel_url,
                              description=description, order_code=order_code,
                              return_url=return_url)
        payload = {
            "orderCode": order_code, "amount": amount_vnd, "description": description,
            "returnUrl": return_url, "cancelUrl": cancel_url, "signature": sig,
        }
        import httpx
        url = f"{self.base_url}/v2/payment-requests"
        headers = {"x-client-id": self.client_id, "x-api-key": self.api_key,
                   "Content-Type": "application/json"}
        try:
            r = httpx.post(url, headers=headers, json=payload, timeout=timeout)
        except Exception as e:  # noqa: BLE001
            raise GatewayError(f"PayOS mang loi: {type(e).__name__}") from None
        if r.status_code != 200:
            raise GatewayError(f"PayOS HTTP {r.status_code}")
        body = r.json()
        if body.get("code") not in ("00", 0, None) and str(body.get("code")) != "00":
            raise GatewayError(f"PayOS tu choi: {body.get('desc') or body.get('code')}")
        data = body.get("data") or {}
        return {
            "checkout_url": data.get("checkoutUrl", ""),
            "qr_code": data.get("qrCode", ""),
            "ref": str(data.get("paymentLinkId") or data.get("bin") or ""),
        }

    def xac_thuc_webhook(self, headers: dict, raw_body: bytes) -> dict:
        self._bat_buoc_cau_hinh()
        try:
            body = json.loads(raw_body.decode("utf-8") if isinstance(raw_body, (bytes, bytearray))
                              else raw_body)
        except Exception:  # noqa: BLE001
            raise ChuKyKhongHopLe("webhook body khong phai JSON") from None
        data = body.get("data")
        signature = body.get("signature") or ""
        if not isinstance(data, dict) or not signature:
            raise ChuKyKhongHopLe("thieu data hoac signature")
        mong_doi = _sap_xep_ky(self.checksum_key, data)
        if not hmac.compare_digest(mong_doi, signature):
            raise ChuKyKhongHopLe("chu ky webhook sai")
        try:
            order_code = int(data.get("orderCode"))
        except (TypeError, ValueError):
            raise ChuKyKhongHopLe("orderCode khong hop le") from None
        # PayOS: code "00" ở data (hoặc body) = thành công.
        paid = str(data.get("code", body.get("code", ""))) == "00"
        return {"order_code": order_code, "paid": paid,
                "ref": str(data.get("reference") or data.get("paymentLinkId") or "")}
