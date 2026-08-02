"""Export profile registry.

Platform-specific encoding and dimension settings.
"""

from __future__ import annotations

from cutclipshort.types import AspectRatio, ExportProfile, RenderSettings

# ── Export Profiles ──────────────────────────────────────────────────────

EXPORT_PROFILES: dict[str, ExportProfile] = {
    "tiktok": ExportProfile(
        name="tiktok",
        display_name="TikTok",
        aspect_ratio=AspectRatio.PORTRAIT_9_16,
        width=1080,
        height=1920,
        max_duration_sec=60.0,
        max_file_size_mb=95.0,
        render_settings=RenderSettings(
            crf="20",
            audio_bitrate="192k",
            size_control_enabled=True,
            max_file_size_mb=95.0,
            encoding_mode="crf_capped",
            target_resolution="1080p",
        ),
    ),
    "youtube_shorts": ExportProfile(
        name="youtube_shorts",
        display_name="YouTube Shorts",
        aspect_ratio=AspectRatio.PORTRAIT_9_16,
        width=1080,
        height=1920,
        max_duration_sec=60.0,
        max_file_size_mb=95.0,
        render_settings=RenderSettings(
            crf="19",
            audio_bitrate="192k",
            size_control_enabled=True,
            max_file_size_mb=95.0,
            encoding_mode="crf_capped",
            target_resolution="1080p",
        ),
    ),
    "instagram_reels": ExportProfile(
        name="instagram_reels",
        display_name="Instagram Reels",
        aspect_ratio=AspectRatio.PORTRAIT_9_16,
        width=1080,
        height=1920,
        max_duration_sec=90.0,
        max_file_size_mb=95.0,
        render_settings=RenderSettings(
            crf="20",
            audio_bitrate="192k",
            size_control_enabled=True,
            max_file_size_mb=95.0,
            encoding_mode="crf_capped",
            target_resolution="auto",
        ),
    ),
    "landscape_1080p": ExportProfile(
        name="landscape_1080p",
        display_name="Landscape 1080p",
        aspect_ratio=AspectRatio.LANDSCAPE_16_9,
        width=1920,
        height=1080,
        max_duration_sec=300.0,
        max_file_size_mb=95.0,
        render_settings=RenderSettings(
            crf="20",
            audio_bitrate="192k",
            size_control_enabled=True,
            max_file_size_mb=95.0,
            encoding_mode="crf_capped",
            target_resolution="auto",
        ),
    ),
    "square_1080": ExportProfile(
        name="square_1080",
        display_name="Square 1080x1080",
        aspect_ratio=AspectRatio.SQUARE_1_1,
        width=1080,
        height=1080,
        max_duration_sec=60.0,
        max_file_size_mb=95.0,
        render_settings=RenderSettings(
            crf="20",
            audio_bitrate="192k",
            size_control_enabled=True,
            max_file_size_mb=95.0,
            encoding_mode="crf_capped",
            target_resolution="1080p",
        ),
    ),
}


def get_export_profile(name: str) -> ExportProfile:
    """Get export profile by name. Falls back to tiktok."""
    return EXPORT_PROFILES.get(name, EXPORT_PROFILES["tiktok"])


def list_export_profiles() -> list[dict[str, str]]:
    """List all profiles with name and display_name."""
    return [
        {"name": p.name, "display_name": p.display_name}
        for p in EXPORT_PROFILES.values()
    ]
