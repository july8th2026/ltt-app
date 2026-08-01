"""
payments — cổng thanh toán AGNOSTIC (H9, Q31).

Nghiệp vụ (`billing.py`) chỉ nói chuyện với giao diện `Gateway` ở đây; muốn thêm
VNPAY/MoMo sau chỉ cần viết một adapter và đăng ký vào `GATEWAYS` — KHÔNG đụng
nghiệp vụ, route hay app (giống Provider Registry ở H8).

Bất biến:
- adapter KHÔNG tự cộng credit; nó chỉ tạo thanh toán + xác thực webhook. Cộng
  credit là việc DUY NHẤT của `billing.ghi_nhan_tra` (đi qua sổ credit H3).
- thiếu credential → `GatewayChuaCauHinh` (tắt mềm) để dev/test chạy được.
"""
from __future__ import annotations

from typing import Optional, Protocol


class GatewayError(Exception):
    """Lỗi chung của cổng (tạo thanh toán thất bại, phản hồi lạ)."""


class GatewayChuaCauHinh(GatewayError):
    """Cổng chưa có credential -> tắt mềm (dev/test / chưa nhập khoá production)."""


class ChuKyKhongHopLe(GatewayError):
    """Chữ ký webhook sai -> TỪ CHỐI, không cộng credit."""


class Gateway(Protocol):
    id: str

    def da_cau_hinh(self) -> bool: ...

    def tao_thanh_toan(self, *, order_code: int, amount_vnd: int, description: str,
                       return_url: str, cancel_url: str) -> dict: ...

    def xac_thuc_webhook(self, headers: dict, raw_body: bytes) -> dict: ...


# Registry điền ở dưới (sau khi import adapter, tránh vòng import).
GATEWAYS: dict = {}


def get(gateway_id: str) -> Optional["Gateway"]:
    return GATEWAYS.get((gateway_id or "").strip().lower())


def _dang_ky() -> None:
    from platform_core.payments.payos import PayOSGateway
    g = PayOSGateway()
    GATEWAYS[g.id] = g


_dang_ky()
