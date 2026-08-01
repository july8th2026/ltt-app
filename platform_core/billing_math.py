"""
billing_math.py — toán tiền/credit MỘT chỗ (H9).

Tỉ giá chốt (Q31): **1 credit = 100đ** (100.000đ = 1.000 credit). Gói nạp có
bonus theo %. Trang bán, đơn hàng, admin đều gọi các hàm ở đây nên số luôn khớp —
không rải công thức khắp nơi (bài học: tính tiền hai chỗ là tiền lệch hai chỗ).

Số nguyên toàn bộ (credit là đơn vị nguyên) — làm tròn XUỐNG, không tạo credit lẻ.
"""
from __future__ import annotations

VND_PER_CREDIT = 100    # 1 credit = 100đ


def credits_base_tu_vnd(price_vnd: int) -> int:
    """Số credit gốc cho một số tiền (chưa bonus). Làm tròn xuống."""
    v = int(price_vnd)
    if v < 0:
        raise ValueError("price_vnd am")
    return v // VND_PER_CREDIT


def bonus_credits(credits_base: int, bonus_percent: int) -> int:
    """Credit tặng thêm theo % (làm tròn xuống)."""
    b = int(credits_base)
    p = int(bonus_percent)
    if b < 0 or p < 0:
        raise ValueError("gia tri am")
    return b * p // 100


def tong_credits(credits_base: int, bonus_percent: int) -> int:
    """Tổng credit khách nhận = gốc + bonus."""
    b = int(credits_base)
    return b + bonus_credits(b, bonus_percent)
