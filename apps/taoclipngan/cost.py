"""
cost.py — giá credit cho TẠO CLIP NGẮN.

Engine không có tính tiền. Chi phí thật ~ thời gian GPU = chép lời (theo độ dài
NGUỒN) + encode (theo SỐ CLIP xuất). Đề xuất người dùng chốt 2026-08-02
(Q31: 1 credit = 100đ):

  credit = phút_nguồn × hệ_số_tier × ĐƠN_GIÁ_PHÚT + số_clip × ĐƠN_GIÁ_CLIP
  hệ_số_tier: fast ×1.0 · balanced ×1.6 · high_quality ×2.2
  (balanced ≈ 8 credit/phút; fast ≈ 5; high ≈ 11)

Giữ chỗ theo phút client khai + số clip mục tiêu; worker đo phút THẬT + đếm clip
THẬT rồi nâng giữ chỗ (nếu thiếu) + quyết toán.
"""
from __future__ import annotations

import math

DON_GIA_PHUT = 5            # credit/phút @ tier ×1.0
DON_GIA_CLIP = 5           # credit/clip xuất
MIN_CREDIT = 1
_TIER_MULT = {"fast": 1.0, "balanced": 1.6, "high_quality": 2.2}


def he_so_tier(tier: str) -> float:
    return _TIER_MULT.get(tier, 1.6)


def uoc_luong_credit(duration_s: float, tier: str = "high_quality",
                     n_clips: int = 3) -> int:
    minutes = max(0.0, float(duration_s or 0)) / 60.0
    raw = minutes * he_so_tier(tier) * DON_GIA_PHUT + max(0, int(n_clips)) * DON_GIA_CLIP
    return max(MIN_CREDIT, math.ceil(raw))


def uoc_luong(duration_s: float, tier: str = "high_quality", n_clips: int = 3) -> dict:
    credit = uoc_luong_credit(duration_s, tier, n_clips)
    return {"credit": credit, "vnd": credit * 100,
            "minutes": round(max(0.0, float(duration_s or 0)) / 60.0, 2),
            "tier": tier, "n_clips": n_clips}
