"""Platform constraints and duration rules.

Defines hard limits for each target platform.
"""

from __future__ import annotations

from cutclipshort.types import AspectRatio, EditConstraints

# ── Platform Presets ─────────────────────────────────────────────────────

PLATFORM_CONSTRAINTS: dict[str, EditConstraints] = {
    "tiktok": EditConstraints(
        min_clip_duration_sec=15.0,
        max_clip_duration_sec=60.0,
        target_clip_count=5,
        platform="tiktok",
        aspect_ratio=AspectRatio.PORTRAIT_9_16,
        target_width=1080,
        target_height=1920,
    ),
    "youtube_shorts": EditConstraints(
        min_clip_duration_sec=15.0,
        max_clip_duration_sec=60.0,
        target_clip_count=5,
        platform="youtube_shorts",
        aspect_ratio=AspectRatio.PORTRAIT_9_16,
        target_width=1080,
        target_height=1920,
    ),
    "instagram_reels": EditConstraints(
        min_clip_duration_sec=15.0,
        max_clip_duration_sec=90.0,
        target_clip_count=5,
        platform="instagram_reels",
        aspect_ratio=AspectRatio.PORTRAIT_9_16,
        target_width=1080,
        target_height=1920,
    ),
    "landscape": EditConstraints(
        min_clip_duration_sec=30.0,
        max_clip_duration_sec=180.0,
        target_clip_count=3,
        platform="landscape",
        aspect_ratio=AspectRatio.LANDSCAPE_16_9,
        target_width=1920,
        target_height=1080,
    ),
    "square": EditConstraints(
        min_clip_duration_sec=15.0,
        max_clip_duration_sec=60.0,
        target_clip_count=5,
        platform="square",
        aspect_ratio=AspectRatio.SQUARE_1_1,
        target_width=1080,
        target_height=1080,
    ),
}


def get_constraints(platform: str) -> EditConstraints:
    """Get constraints for a platform. Falls back to tiktok if unknown."""
    return PLATFORM_CONSTRAINTS.get(platform, PLATFORM_CONSTRAINTS["tiktok"])


def validate_clip_duration(
    duration_sec: float,
    constraints: EditConstraints,
) -> bool:
    """Check if a clip duration fits within constraints."""
    return constraints.min_clip_duration_sec <= duration_sec <= constraints.max_clip_duration_sec
