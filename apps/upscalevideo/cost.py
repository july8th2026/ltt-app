"""
cost.py — giá credit cho UPSCALE VIDEO.

Module gốc BOT GEMINI không tính tiền. Mô hình MỚI: theo **phút video × độ phân
giải đích × preset** (chi phí ~ thời gian GPU ~ số frame × diện tích × độ nặng model).

Đơn giá người dùng chốt 2026-08-01: ~30 credit/phút @1080p Fast.
  hệ_số_res: 1080=1.0 · 1440=1.8 · 2160(4K)=4.0
  hệ_số_preset: fast=1.0 · quality=2.5
Tỉ giá Q31: 1 credit = 100đ. Preview (~8s đầu) tính theo thời lượng thực (nhỏ).
"""
from __future__ import annotations

import math

CREDIT_PER_MINUTE = 30         # @1080p Fast, chốt 2026-08-01
MIN_CREDIT = 1

_RES_MULT = {1080: 1.0, 1440: 1.8, 2160: 4.0}
_PRESET_MULT = {"fast": 1.0, "quality": 2.5}
_PREVIEW_SECONDS = 8.0


def he_so_res(target_height: int) -> float:
    return _RES_MULT.get(int(target_height), 1.0)


def he_so_preset(preset: str) -> float:
    return _PRESET_MULT.get(preset, 1.0)


def uoc_luong_credit(duration_s: float, target_height: int = 1080,
                     preset: str = "fast", preview: bool = False) -> int:
    dur = min(float(duration_s or 0), _PREVIEW_SECONDS) if preview else float(duration_s or 0)
    minutes = max(0.0, dur) / 60.0
    raw = minutes * he_so_res(target_height) * he_so_preset(preset) * CREDIT_PER_MINUTE
    return max(MIN_CREDIT, math.ceil(raw))


def uoc_luong(duration_s: float, target_height: int = 1080, preset: str = "fast",
              preview: bool = False) -> dict:
    credit = uoc_luong_credit(duration_s, target_height, preset, preview)
    dur = min(float(duration_s or 0), _PREVIEW_SECONDS) if preview else float(duration_s or 0)
    return {"credit": credit, "vnd": credit * 100,
            "minutes": round(max(0.0, dur) / 60.0, 2),
            "target_height": target_height, "preset": preset, "preview": preview}
