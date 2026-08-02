"""YOLO-guided reframing and motion zoom.

Computes crop/zoom parameters for converting landscape video to portrait.
Ported from NerfWarAI's yolo_reframe.py smoothstep/crop logic.
"""

from __future__ import annotations

import math
from typing import Any

from cutclipshort.types import FramingParams, PersonDetection


def smoothstep(t: float) -> float:
    """Smooth interpolation [0,1] → [0,1] with ease in/out."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def interpolate_framing(
    framing: FramingParams,
    progress: float,
) -> tuple[float, float, float]:
    """Interpolate framing parameters over clip duration.

    Args:
        framing: Start/end framing params.
        progress: 0.0 (clip start) to 1.0 (clip end).

    Returns:
        (cx, cy, zoom) at the given progress point.
    """
    t = smoothstep(progress)
    cx = framing.cx_start + (framing.cx_end - framing.cx_start) * t
    cy = framing.cy_start + (framing.cy_end - framing.cy_start) * t
    zoom = framing.zoom_start + (framing.zoom_end - framing.zoom_start) * t
    return cx, cy, zoom


def compute_crop_rect(
    cx: float,
    cy: float,
    zoom: float,
    source_w: int,
    source_h: int,
    target_w: int,
    target_h: int,
) -> dict[str, int]:
    """Compute FFmpeg-compatible crop rectangle.

    Returns {"x": int, "y": int, "w": int, "h": int}.
    """
    target_ratio = target_w / target_h
    crop_h = int(source_h / zoom)
    crop_w = int(crop_h * target_ratio)

    # Clamp to source bounds
    crop_w = min(crop_w, source_w)
    crop_h = min(crop_h, source_h)

    x = int(cx - crop_w / 2)
    y = int(cy - crop_h / 2)

    # Keep within frame
    x = max(0, min(x, source_w - crop_w))
    y = max(0, min(y, source_h - crop_h))

    return {"x": x, "y": y, "w": crop_w, "h": crop_h}


def _compute_adaptive_smooth_alpha(
    cx0: float, cy0: float, cx1: float, cy1: float,
    clip_duration: float,
    source_w: int,
) -> float:
    """
    [Phase2] Adaptive smoothing alpha dua tren toc do pan.

    - Di chuyen nhanh (>40% frame width/s) -> alpha cao hon (0.15) = camera theo sat
    - Di chuyen cham (<10% frame width/s) -> alpha thap (0.05) = camera muot
    - Mac dinh: 0.07

    Returns:
        smooth_alpha in [0.03, 0.20]
    """
    if clip_duration <= 0 or source_w <= 0:
        return 0.07

    pan_distance = math.sqrt((cx1 - cx0) ** 2 + (cy1 - cy0) ** 2)
    pan_speed_frac = (pan_distance / source_w) / clip_duration  # fraction of width per sec

    if pan_speed_frac > 0.40:
        # Fast movement -> higher alpha for responsiveness
        return 0.15
    elif pan_speed_frac > 0.20:
        return 0.10
    elif pan_speed_frac > 0.05:
        return 0.07  # Default
    else:
        # Slow/static -> smoother, more cinematic
        return 0.04


def compute_framing_from_persons(
    persons_start: list[PersonDetection],
    persons_end: list[PersonDetection],
    source_w: int,
    source_h: int,
    target_fraction: float = 0.70,
    clip_duration: float = 0.0,
) -> FramingParams:
    """Compute framing params from person detections at clip start/end.

    Uses the largest person as the tracking target.
    [Phase2] Adaptive smooth_alpha based on pan speed.
    """
    def _center_and_zoom(
        persons: list[PersonDetection],
    ) -> tuple[float, float, float]:
        if not persons:
            return source_w / 2.0, source_h / 2.0, 1.0

        # Use largest person
        person = max(persons, key=lambda p: p.area)
        cx, cy = person.cx, person.cy

        # Compute zoom to make person fill target_fraction of frame height
        if person.h > 0:
            zoom = (source_h * target_fraction) / person.h
            zoom = max(1.0, min(zoom, 2.5))  # Clamp
        else:
            zoom = 1.0

        return cx, cy, zoom

    cx0, cy0, z0 = _center_and_zoom(persons_start)
    cx1, cy1, z1 = _center_and_zoom(persons_end)

    # [Phase2] Adaptive alpha
    alpha = _compute_adaptive_smooth_alpha(
        cx0, cy0, cx1, cy1, clip_duration, source_w,
    )

    return FramingParams(
        cx_start=cx0, cy_start=cy0,
        cx_end=cx1, cy_end=cy1,
        zoom_start=z0, zoom_end=z1,
        smooth_alpha=alpha,
        max_pan_px_per_sec=900.0,
        person_target_fraction=target_fraction,
    )
