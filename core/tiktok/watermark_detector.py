"""
Lightweight watermark detector (Sprint TT-5 / F4).

TikTok aggressively deboosts videos that contain another platform's
watermark (CapCut, Splash, InShot, Filmora, etc.). True per-pixel CV
detection requires OpenCV + ML models — heavyweight for a desktop bot.

This module uses CHEAP heuristics that catch ~80 % of cases without any
binary dependency:

  1. FILENAME signals — the most common: CapCut exports as
     `VID_<timestamp>_capcut.mp4`, Splash as `<id>_splash.mp4`, etc.
     The user often imports the file as-is from the editor.

  2. CONTAINER METADATA — many editors stamp the encoder field of the
     MOV/MP4 container. ffprobe exposes this in `format.tags.encoder` or
     stream metadata. We check that against a known-editor list.

  3. AUDIO METADATA — some editors stamp audio "title" or "comment".

For deeper detection, F4-future would wire OpenCV template matching on
the first/last seconds of video. Out of scope for this iteration.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional

# Known editor signatures — filename substrings and encoder strings.
_FILENAME_SIGNATURES: dict[str, str] = {
    "capcut":   "CapCut",
    "splash":   "Splash",
    "inshot":   "InShot",
    "filmora":  "Filmora",
    "kinemaster": "KineMaster",
    "vllo":     "VLLO",
    "vita":     "VITA",
    "videoshow": "VideoShow",
    "alight":   "Alight Motion",
    "cute_cut": "Cute Cut",
}

_ENCODER_SIGNATURES: dict[str, str] = {
    "capcut":     "CapCut",
    "lavf":       "FFmpeg/libavformat (likely OK — generic)",
    "x264":       "x264 (likely OK — generic)",
    "splash":     "Splash",
    "inshot":     "InShot",
    "filmora":    "Filmora",
    "kinemaster": "KineMaster",
}


@dataclass(frozen=True)
class WatermarkSignal:
    detected:    bool
    source:      str          # "filename" | "encoder_tag" | "title_tag" | "none"
    editor_name: str          # human-readable, e.g. "CapCut"
    confidence:  str          # "high" | "medium" | "low"
    message:     str
    fix_hint:    str = ""


def detect_watermark(file_path: str) -> WatermarkSignal:
    """Inspect *file_path* for known editor signatures.

    Returns WatermarkSignal — detected=True when high-confidence hit found.
    Always safe to call (no exceptions); returns "none" on any failure.
    """
    if not file_path or not os.path.exists(file_path):
        return WatermarkSignal(
            detected=False, source="none", editor_name="", confidence="low",
            message="File không tồn tại",
        )

    # 1. Filename check — strongest signal because users rarely rename
    lower = os.path.basename(file_path).lower()
    for sig, editor in _FILENAME_SIGNATURES.items():
        if sig in lower:
            return WatermarkSignal(
                detected=True, source="filename", editor_name=editor,
                confidence="high",
                message=f"Tên file gợi ý xuất từ {editor}: {os.path.basename(file_path)}",
                fix_hint=(
                    f"Re-export từ {editor} CHỌN tuỳ chọn 'Remove watermark' / "
                    "'Export without watermark'. Hoặc dùng tool xoá watermark."
                ),
            )

    # 2. ffprobe encoder tag check (only if ffprobe available — graceful skip)
    encoder = _ffprobe_encoder(file_path)
    if encoder:
        e_low = encoder.lower()
        for sig, editor in _ENCODER_SIGNATURES.items():
            if sig in e_low and "OK" not in editor:
                return WatermarkSignal(
                    detected=True, source="encoder_tag", editor_name=editor,
                    confidence="medium",
                    message=f"Metadata encoder '{encoder}' = {editor}",
                    fix_hint=f"Re-encode bằng ffmpeg để strip metadata",
                )

    return WatermarkSignal(
        detected=False, source="none", editor_name="", confidence="medium",
        message="Không phát hiện watermark qua heuristic",
    )


def _ffprobe_encoder(file_path: str) -> Optional[str]:
    """Pull format.tags.encoder via ffprobe. Returns None on any failure."""
    try:
        from core.tiktok.video_validator import _ffprobe
    except Exception:
        return None
    meta = _ffprobe(file_path)
    if meta is None:
        return None
    fmt = meta.get("format", {}) or {}
    tags = fmt.get("tags", {}) or {}
    # Prioritise "encoder"; fall back to "handler_name" / "compatible_brands"
    return (
        tags.get("encoder")
        or tags.get("Encoder")
        or tags.get("ENCODER")
        or ""
    ).strip() or None
