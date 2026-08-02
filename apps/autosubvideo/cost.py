"""
cost.py — giá credit cho AUTO SUB VIDEO.

Module gốc BOT GEMINI KHÔNG có logic tính tiền (chỉ giới hạn hàng đợi). Đây là
mô hình giá MỚI của nền tảng, theo **thời lượng video × mức chất lượng**, vì chi
phí ~ thời gian encode ~ độ dài × preset.

Tỉ giá Q31: 1 credit = 100đ. Đơn giá do người dùng chốt 2026-08-01:
    ~5 credit / phút @ standard  (draft ×0.6, standard ×1.0, high ×1.5).

Nối sổ credit H3:
- `uoc_luong_credit(duration_s, quality)` = giá TRƯỚC khi chạy → `credit_cost`
  trong manifest để nền tảng GIỮ CHỖ. Handler trả lại đúng số này để quyết toán
  (giá không phụ thuộc token ngoài, ước tính = thật khi duration đã biết).
"""
from __future__ import annotations

import math

CREDIT_PER_MINUTE = 5          # @standard, người dùng chốt 2026-08-01
_QUALITY_MULT = {"draft": 0.6, "standard": 1.0, "high": 1.5}
MIN_CREDIT = 1                 # tối thiểu 1 credit/job (chống job 0 đồng)


def he_so_chat_luong(quality: str) -> float:
    return _QUALITY_MULT.get(quality, 1.0)


def uoc_luong_credit(duration_s: float, quality: str = "standard") -> int:
    """Credit giữ chỗ = phút video × hệ_số_chất_lượng × đơn_giá (làm tròn lên)."""
    minutes = max(0.0, float(duration_s or 0)) / 60.0
    raw = minutes * he_so_chat_luong(quality) * CREDIT_PER_MINUTE
    return max(MIN_CREDIT, math.ceil(raw))


def uoc_luong(duration_s: float, quality: str = "standard") -> dict:
    credit = uoc_luong_credit(duration_s, quality)
    return {"credit": credit, "vnd": credit * 100,
            "minutes": round(max(0.0, float(duration_s or 0)) / 60.0, 2),
            "quality": quality}
