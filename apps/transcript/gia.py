"""Giá của App `transcript` — theo PHÚT AUDIO, đo từ chính tệp đã tải lên.

Chủ dự án chốt 22/09/2026: "để như khuyến nghị, điều chỉnh sau". Khuyến nghị:
**2 credit / phút audio bắt đầu tính (200đ/phút), tối thiểu 1, làm tròn lên.**

Căn cứ (cùng nền tảng, cùng tỉ giá 1 credit = 100đ — Q31):
- `autosubvideo` khắc phụ đề 5 credit/phút (`apps/autosubvideo/cost.py`);
- `ltt_voice` sinh giọng ~12 credit/phút (`apps/ltt_voice/gia.py`);
- phiên âm large-v3 tốn ~9–18 giây GPU / phút audio (RTF 0.15–0.3 đo 22/09),
  nhẹ hơn cả hai.

⛔ Q84: khách không bao giờ trả hơn phần đã giữ ở báo giá. Worker đo lại thời
   lượng thật và quyết toán `min(giá thật, đã giữ)` — không giữ thêm sau báo giá.
"""
from __future__ import annotations

import math

CREDIT_PER_MINUTE = 2
MIN_CREDIT = 1


def uoc_luong_credit(duration_s: float | int | None) -> int:
    phut = max(0.0, float(duration_s or 0.0)) / 60.0
    return max(MIN_CREDIT, math.ceil(phut * CREDIT_PER_MINUTE))
