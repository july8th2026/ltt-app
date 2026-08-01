"""
cost.py — mô hình giá seedance (di trú trung thành từ BOT GEMINI
`app/modules/seedance_video/cost.py`).

Giá theo TOKEN ≈ (w×h×fps×duration) × hệ số hiệu chỉnh, nhân rate USD/1M-token
theo model + có/không video input, cộng markup, quy ra VND, rồi ĐỔI RA CREDIT
của nền tảng (Q31: 1 credit = 100đ).

Hai điểm nối với sổ credit H3:
- `uoc_luong_credit(...)` = giá TRƯỚC khi chạy → dùng làm `credit_cost` trong
  manifest để nền tảng GIỮ CHỖ (reserve).
- `credit_tu_token(...)` = giá THẬT sau khi provider trả `usage.total_tokens` →
  handler trả về `credit_cost` này để worker QUYẾT TOÁN (hoàn phần giữ dư).
"""
from __future__ import annotations

import math

VND_PER_CREDIT = 100          # Q31
USD_TO_VND = 26000            # manifest BOT GEMINI
MARKUP_PERCENT = 0

_RES_DIM = {"480p": (854, 480), "720p": (1280, 720),
            "1080p": (1920, 1080), "4k": (3840, 2160)}

# Rate USD / 1.000.000 token = (có_video_input, KHÔNG_video_input)
_RATE_PER_M = {
    "seedance-2.0":      (4.3, 7.0),
    "seedance-2.0-fast": (3.3, 5.6),
    "seedance-2.0-mini": (2.1, 3.5),
}
_DEFAULT_RATE = (4.3, 7.0)

DEFAULT_FPS = 24
# Hiệu chỉnh từ 1 job thật (mini 480p/16:9/5s): total_tokens = 50638.
_CAL_TOKENS, _CAL_W, _CAL_H, _CAL_FPS, _CAL_DUR = 50638, 854, 480, 24, 5
_TOKENS_PER_UNIT = _CAL_TOKENS / (_CAL_W * _CAL_H * _CAL_FPS * _CAL_DUR)


def _rate(model: str, has_video_input: bool) -> float:
    pair = _RATE_PER_M.get(model, _DEFAULT_RATE)
    return pair[0] if has_video_input else pair[1]


def uoc_tinh_token(resolution: str, duration: int, fps: int = DEFAULT_FPS) -> int:
    w, h = _RES_DIM.get(resolution, (1280, 720))     # lạ → 720p (ước cao, an toàn)
    dur = max(1, int(duration))
    return int((w * h * fps * dur) * _TOKENS_PER_UNIT)


def _vnd_tu_usd(usd: float) -> int:
    return int(round(usd * USD_TO_VND))


def _credit_tu_vnd(vnd: int) -> int:
    return max(1, math.ceil(vnd / VND_PER_CREDIT))


def usd_tu_token(model: str, tokens: int, has_video_input: bool = False) -> float:
    return round(tokens / 1_000_000 * _rate(model, has_video_input) * (1 + MARKUP_PERCENT / 100.0), 4)


def credit_tu_token(model: str, tokens: int, has_video_input: bool = False) -> int:
    """Credit THẬT sau khi biết token provider dùng (để quyết toán)."""
    return _credit_tu_vnd(_vnd_tu_usd(usd_tu_token(model, tokens, has_video_input)))


def uoc_luong(model: str, resolution: str, duration: int,
              has_video_input: bool = False) -> dict:
    """Ước tính trước khi chạy: token/usd/vnd/credit + công thức (để hiện UI + reserve)."""
    tokens = uoc_tinh_token(resolution, duration)
    usd = usd_tu_token(model, tokens, has_video_input)
    vnd = _vnd_tu_usd(usd)
    credit = _credit_tu_vnd(vnd)
    return {"tokens": tokens, "usd": usd, "vnd": vnd, "credit": credit,
            "formula": f"~{tokens:,} token x ${_rate(model, has_video_input)}/1M = "
                       f"${usd} ~ {vnd:,}d = {credit} credit"}


def uoc_luong_credit(model: str, resolution: str, duration: int,
                     has_video_input: bool = False) -> int:
    return uoc_luong(model, resolution, duration, has_video_input)["credit"]
