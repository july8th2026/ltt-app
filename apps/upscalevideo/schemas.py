"""Kiểu dữ liệu upscalevideo (di trú trung thành từ BOT GEMINI video_upscale)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Preset(str, Enum):
    fast = "fast"        # realesr-general-x4v3 — nhanh, ~1GB VRAM, mặc định
    quality = "quality"  # realesrgan-x4plus   — nét hơn, cần ~10-15GB VRAM


PRESET_MODEL = {
    Preset.fast:    "realesr-general-x4v3",
    Preset.quality: "realesrgan-x4plus",
}
ENGINE_SCALE = 4  # cả 2 model đều x4; hạ về target_height ở khâu encode


class Codec(str, Enum):
    h264 = "h264"
    hevc = "hevc"       # H.265 — file nhỏ hơn ~30%


ENCODER = {Codec.h264: "h264_nvenc", Codec.hevc: "hevc_nvenc"}
ALLOWED_HEIGHTS = (1080, 1440, 2160)


class TuneResult(BaseModel):
    """Kết quả autotune cho 1 lần chạy."""
    model: str
    tile: int
    threads: str                        # "load:proc:save"
    est_alloc_mb: int
    free_mb: int
    budget_mb: int
    fast_path: bool
    warning: str = ""
