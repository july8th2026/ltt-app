"""Style planner v2 — uses StylePacks to drive all render decisions.

After candidates are ranked, the style planner consults the genre's
StylePack to decide every visual/audio parameter for the clip.

Hierarchy (low → high priority):
1. StylePack defaults (from genre)
2. GenreProfile defaults (caption_enabled, color)
3. User overrides (from GUI edit page)

The planner produces a flat dict consumed by edit_plan_builder.
"""

from __future__ import annotations

import logging

from cutclipshort.editorial.genre_profiles import GenreProfile
from cutclipshort.presets.color_presets import get_color_preset
from cutclipshort.presets.style_packs import StylePack, get_style_pack
from cutclipshort.presets.subtitle_styles import get_subtitle_style
from cutclipshort.types import (
    AudioConfig,
    CandidateClip,
    CaptionStyle,
    FramingParams,
)

logger = logging.getLogger(__name__)


def plan_style(
    candidate: CandidateClip,
    profile: GenreProfile,
    user_overrides: dict | None = None,
) -> dict:
    """Decide the complete editorial style for a candidate clip.

    Returns dict with keys matching what edit_plan_builder expects:
        color_preset_name, color_config, caption_enabled, caption_style,
        audio_config, speed_factor, crop_config, emphasis_config,
        keyword_categories, hook_subtitle_style
    """
    overrides = user_overrides or {}
    pack = get_style_pack(profile.name)

    # ── Color ────────────────────────────────────────────────────────
    color_name = overrides.get("color_preset", pack.color_preset)
    color_config = get_color_preset(color_name)

    # ── Subtitle style ───────────────────────────────────────────────
    caption_enabled = overrides.get(
        "caption_enabled",
        profile.default_caption_enabled and candidate.has_speech,
    )

    caption_style = None
    if caption_enabled:
        style_name = overrides.get("caption_preset", pack.subtitle_style)
        caption_style = get_subtitle_style(style_name)

    # Hook subtitle (different style for first N seconds)
    hook_caption_style = None
    if caption_enabled and pack.hook_subtitle_style:
        hook_style_name = overrides.get(
            "hook_caption_preset", pack.hook_subtitle_style,
        )
        hook_caption_style = get_subtitle_style(hook_style_name)

    # ── Audio ────────────────────────────────────────────────────────
    audio_config = _build_audio_config(candidate, pack, overrides)

    # ── Speed / Pacing ───────────────────────────────────────────────
    speed = overrides.get("speed_factor", pack.pacing.speed_factor)

    # ── Crop config (passed through for framing resolution) ──────────
    crop = pack.crop

    # ── Emphasis / keyword highlight ─────────────────────────────────
    keyword_cats = pack.emphasis.keyword_categories if pack.emphasis.keyword_highlight else ()

    return {
        "color_preset_name": color_name,
        "color_config": color_config,
        "caption_enabled": caption_enabled,
        "caption_style": caption_style,
        "hook_caption_style": hook_caption_style,
        "hook_window_sec": pack.hook_window_sec,
        "audio_config": audio_config,
        "speed_factor": speed,
        "crop_config": crop,
        "emphasis_config": pack.emphasis,
        "keyword_categories": keyword_cats,
        "style_pack_name": pack.name,
        "silence_trim_sec": pack.pacing.silence_trim_sec,
        "max_dead_air_sec": pack.pacing.max_dead_air_sec,
    }


def resolve_framing_from_pack(
    pack_crop,
    source_width: float,
    source_height: float,
    person_cx: float | None = None,
    person_cy: float | None = None,
) -> FramingParams:
    """Build FramingParams from StylePack's CropConfig.

    Uses person center if available, otherwise center crop.
    """
    cx = person_cx if person_cx is not None else source_width / 2.0
    cy = person_cy if person_cy is not None else source_height / 2.0

    return FramingParams(
        cx_start=cx,
        cy_start=cy,
        cx_end=cx,
        cy_end=cy,
        zoom_start=pack_crop.zoom_base,
        zoom_end=pack_crop.zoom_base,
        smooth_alpha=pack_crop.smooth_alpha,
        max_pan_px_per_sec=pack_crop.max_pan_speed,
        person_target_fraction=pack_crop.person_target_fraction,
    )


def _build_audio_config(
    candidate: CandidateClip,
    pack: StylePack,
    overrides: dict,
) -> AudioConfig:
    """Build audio config from pack defaults + overrides."""
    demucs = overrides.get("demucs_enabled", pack.demucs_enabled)

    # Auto-enable demucs for podcast if music detected
    if pack.name == "podcast" and "has_music" in (candidate.tags or []):
        demucs = True

    return AudioConfig(
        demucs_enabled=demucs,
        demucs_model="htdemucs",
        loudnorm_enabled=True,
        loudnorm_lufs=overrides.get("loudnorm_lufs", pack.loudnorm_lufs),
        loudnorm_true_peak_db=overrides.get("loudnorm_true_peak_db", -1.5),
    )
