"""
tokens.py — token xác thực email và đặt lại mật khẩu.

Đây là chỗ `itsdangerous` thay cho fastapi-users (Q24): `URLSafeTimedSerializer`
là mẫu chuẩn cho token dùng-một-lần-có-hạn, đã được soi kỹ, và đã có sẵn trong
dự án.

Ba tính chất một token loại này phải có, và cách đạt được:

1. **Không giả mạo được** — token được ký bằng `LTT_SESSION_SECRET`; sửa một
   ký tự là chữ ký sai.
2. **Hết hạn** — `max_age` khi đọc; token cũ bị từ chối.
3. **Đúng mục đích** — mỗi loại một `salt` riêng, nên token xác thực email
   không dùng thay cho token đặt lại mật khẩu được (và ngược lại).

Còn một tính chất phải có nhưng **token tự nó không làm được: dùng-một-lần.**
Một token ký chỉ mang dữ liệu + hạn, không có trạng thái "đã dùng". Tính
một-lần đến từ *hệ quả* của hành động: xác thực email xong thì `is_verified`
đã True, lần bấm thứ hai không đổi gì; đặt lại mật khẩu xong thì mật khẩu đã
khác, và (quan trọng) mọi phiên bị thu hồi. Chỗ nào cần một-lần chặt hơn thế
thì phải lưu jti đã dùng — hiện chưa cần.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

# Salt phân biệt mục đích. Đổi các chuỗi này sẽ vô hiệu mọi token cũ cùng loại.
_SALT_XAC_THUC_EMAIL = "ltt-xac-thuc-email-v1"
_SALT_DAT_LAI_MK = "ltt-dat-lai-mat-khau-v1"

# Hạn mặc định.
TTL_XAC_THUC_EMAIL = 24 * 3600      # 24 giờ — người dùng có thể xác thực sau
TTL_DAT_LAI_MK = 3600              # 1 giờ — cửa sổ hẹp hơn vì nhạy cảm hơn


def _serializer() -> URLSafeTimedSerializer:
    secret = (os.environ.get("LTT_SESSION_SECRET") or "").strip()
    if not secret:
        # Cùng khoá với session; ở development server.settings tự sinh một khoá
        # tạm nếu chưa đặt, nên chỗ này chỉ trống khi gọi ngoài ngữ cảnh app.
        raise RuntimeError(
            "Chua co LTT_SESSION_SECRET — khong ky duoc token. "
            "Bien nay do server.settings quan ly."
        )
    return URLSafeTimedSerializer(secret)


def tao_token_xac_thuc_email(user_id: str) -> str:
    return _serializer().dumps(user_id, salt=_SALT_XAC_THUC_EMAIL)


def doc_token_xac_thuc_email(token: str, *, max_age: int = TTL_XAC_THUC_EMAIL) -> Optional[str]:
    """Trả về user_id nếu token hợp lệ và chưa hết hạn, ngược lại None."""
    return _doc(token, _SALT_XAC_THUC_EMAIL, max_age)


def tao_token_dat_lai_mk(user_id: str) -> str:
    return _serializer().dumps(user_id, salt=_SALT_DAT_LAI_MK)


def doc_token_dat_lai_mk(token: str, *, max_age: int = TTL_DAT_LAI_MK) -> Optional[str]:
    return _doc(token, _SALT_DAT_LAI_MK, max_age)


def _doc(token: str, salt: str, max_age: int) -> Optional[str]:
    if not token:
        return None
    try:
        return _serializer().loads(token, salt=salt, max_age=max_age)
    except (SignatureExpired, BadSignature):
        # Hết hạn và giả mạo đều trả None — nơi gọi không cần phân biệt, và
        # phân biệt ra cũng chỉ giúp kẻ dò biết token nào từng hợp lệ.
        return None
    except Exception:                   # noqa: BLE001
        # Không phải token hỏng mà là HỆ THỐNG hỏng (thiếu khoá ký, cấu hình
        # sai). Trả None lặng lẽ khiến mọi token trông như giả mạo, và người
        # gỡ rối đi tìm nhầm phía người dùng.
        logging.getLogger(__name__).exception(
            "Lỗi hệ thống khi mở token (salt=%s) — mọi token sẽ bị coi là không hợp lệ",
            salt)
        return None
