"""Style packs — genre-aware editorial + render style bundles.

A StylePack is the single object that controls HOW a clip looks and feels.
It maps a genre to concrete decisions across every render dimension:

- Subtitle style (which CaptionStyle to use)
- Color grading (which color_preset)
- Crop aggressiveness (zoom level, person tracking tightness)
- Pacing (speed factor, cut timing preferences)
- Opening behavior (hook emphasis, intro seconds)
- Emphasis strategy (what to highlight visually/aurally)
- Audio treatment (loudnorm target, demucs, SFX)
- Scoring weights override (optional — genre_profiles is the default)

Adding a new style pack = add one entry to STYLE_PACKS. No other file changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CropConfig:
    """How aggressively to crop/zoom for this style."""
    zoom_base: float = 1.0          # 1.0 = no zoom, 1.5 = 50% zoom
    zoom_on_hook: float = 1.0       # Extra zoom during hook window
    person_target_fraction: float = 0.70   # Person fills this % of frame height
    smooth_alpha: float = 0.07      # Lower = smoother camera movement
    max_pan_speed: float = 900.0    # Max px/sec camera pan
    prefer_person_track: bool = True


@dataclass(frozen=True)
class PacingConfig:
    """Pacing preferences for this style."""
    speed_factor: float = 1.0
    cut_on_silence: bool = True       # Prefer cuts at silence gaps
    silence_trim_sec: float = 0.0     # Trim leading/trailing silence by this much
    hook_hold_sec: float = 0.0        # Extra visual emphasis on first N seconds
    max_dead_air_sec: float = 1.5     # Max allowed silence gap mid-clip


@dataclass(frozen=True)
class EmphasisConfig:
    """What to emphasize visually/aurally."""
    keyword_highlight: bool = False   # Highlight keywords in subtitles
    keyword_categories: tuple[str, ...] = ()  # "numbers", "questions", "superlatives"
    hook_zoom_enabled: bool = False   # Zoom in slightly during hook
    punchline_pause: bool = False     # Insert micro-pause before punchline
    energy_boost_db: float = 0.0      # Boost audio energy on high-energy segments


@dataclass(frozen=True)
class StylePack:
    """Complete style bundle for a genre/content type.

    This is the authoritative source for all render style decisions.
    The style_planner reads this to produce ClipSpec parameters.
    """
    name: str
    display_name: str
    description: str

    # Subtitle
    subtitle_style: str = "minimal"          # Key into subtitle_styles registry
    subtitle_fallback: str = "clean_boxed"   # If primary not available

    # Color
    color_preset: str = "original"

    # Crop/Framing
    crop: CropConfig = field(default_factory=CropConfig)

    # Pacing
    pacing: PacingConfig = field(default_factory=PacingConfig)

    # Emphasis
    emphasis: EmphasisConfig = field(default_factory=EmphasisConfig)

    # Audio
    loudnorm_lufs: float = -14.0
    demucs_enabled: bool = False
    sfx_intro: str | None = None  # Path to intro SFX (whoosh, etc.)

    # Opening behavior
    hook_subtitle_style: str | None = None   # Override subtitle for hook window
    hook_window_sec: float = 3.0             # First N sec = hook zone

    # Metadata
    recommended_platforms: tuple[str, ...] = ("tiktok", "youtube_shorts")


# ══════════════════════════════════════════════════════════════════════════
# STYLE PACK REGISTRY
# ══════════════════════════════════════════════════════════════════════════

STYLE_PACKS: dict[str, StylePack] = {

    "talking_head": StylePack(
        name="talking_head",
        display_name="Talking Head",
        description="Single speaker face-to-camera. Clean captions, tight person framing.",
        subtitle_style="bold_highlight",
        subtitle_fallback="minimal",
        color_preset="original",
        crop=CropConfig(
            zoom_base=1.3,
            zoom_on_hook=1.4,
            person_target_fraction=0.70,
            prefer_person_track=True,
        ),
        pacing=PacingConfig(
            speed_factor=1.0,
            silence_trim_sec=0.3,
            hook_hold_sec=0.0,
            max_dead_air_sec=1.5,
        ),
        emphasis=EmphasisConfig(
            keyword_highlight=True,
            keyword_categories=("numbers", "superlatives"),
            hook_zoom_enabled=True,
        ),
        hook_subtitle_style="viral_pop",
        hook_window_sec=3.0,
    ),

    "podcast": StylePack(
        name="podcast",
        display_name="Podcast",
        description="Multi-speaker conversation. Captions essential, moderate crop.",
        subtitle_style="clean_boxed",
        subtitle_fallback="minimal",
        color_preset="original",
        crop=CropConfig(
            zoom_base=1.1,
            zoom_on_hook=1.2,
            person_target_fraction=0.60,
            prefer_person_track=True,
        ),
        pacing=PacingConfig(
            speed_factor=1.0,
            silence_trim_sec=0.2,
            hook_hold_sec=0.0,
            max_dead_air_sec=2.0,
        ),
        emphasis=EmphasisConfig(
            keyword_highlight=True,
            keyword_categories=("questions",),
        ),
        demucs_enabled=False,  # Enable per-clip if music detected
        hook_subtitle_style="bold_highlight",
    ),

    "interview": StylePack(
        name="interview",
        display_name="Interview",
        description="Q&A format. Clear captions, speaker-aware crop priority.",
        subtitle_style="clean_boxed",
        subtitle_fallback="minimal",
        color_preset="clear_fresh",
        crop=CropConfig(
            zoom_base=1.2,
            zoom_on_hook=1.3,
            person_target_fraction=0.65,
            prefer_person_track=True,
        ),
        pacing=PacingConfig(
            speed_factor=1.0,
            silence_trim_sec=0.1,
            max_dead_air_sec=2.0,
        ),
        emphasis=EmphasisConfig(
            keyword_highlight=True,
            keyword_categories=("questions",),
        ),
        hook_subtitle_style="bold_highlight",
    ),

    "review": StylePack(
        name="review",
        display_name="Review",
        description="Product/topic review. Key terms highlighted, moderate zoom.",
        subtitle_style="educator",
        subtitle_fallback="clean_boxed",
        color_preset="clear_fresh",
        crop=CropConfig(
            zoom_base=1.2,
            zoom_on_hook=1.35,
            person_target_fraction=0.65,
            prefer_person_track=True,
        ),
        pacing=PacingConfig(
            speed_factor=1.0,
            silence_trim_sec=0.2,
            max_dead_air_sec=1.5,
        ),
        emphasis=EmphasisConfig(
            keyword_highlight=True,
            keyword_categories=("numbers", "superlatives"),
            hook_zoom_enabled=True,
        ),
        hook_subtitle_style="viral_pop",
    ),

    "storytelling": StylePack(
        name="storytelling",
        display_name="Storytelling",
        description="Narrative arc. Cinematic captions, dramatic pacing.",
        subtitle_style="story_emphasis",
        subtitle_fallback="cinematic",
        color_preset="cinematic",
        crop=CropConfig(
            zoom_base=1.15,
            zoom_on_hook=1.3,
            person_target_fraction=0.60,
            smooth_alpha=0.04,  # Slower, more cinematic camera
            prefer_person_track=True,
        ),
        pacing=PacingConfig(
            speed_factor=1.0,
            silence_trim_sec=0.0,  # Keep dramatic pauses
            hook_hold_sec=1.0,
            max_dead_air_sec=2.5,
        ),
        emphasis=EmphasisConfig(
            keyword_highlight=True,
            keyword_categories=("superlatives",),
            hook_zoom_enabled=True,
        ),
        hook_subtitle_style="bold_highlight",
        hook_window_sec=4.0,
    ),

    "comedy": StylePack(
        name="comedy",
        display_name="Comedy",
        description="Setup-punchline. Bold captions, tight timing, punchline emphasis.",
        subtitle_style="comedy_bold",
        subtitle_fallback="bold_highlight",
        color_preset="clear_fresh",
        crop=CropConfig(
            zoom_base=1.3,
            zoom_on_hook=1.4,
            person_target_fraction=0.70,
            prefer_person_track=True,
        ),
        pacing=PacingConfig(
            speed_factor=1.0,
            silence_trim_sec=0.0,  # Comedic pauses are important
            max_dead_air_sec=2.0,
        ),
        emphasis=EmphasisConfig(
            keyword_highlight=True,
            keyword_categories=("superlatives",),
            punchline_pause=True,
        ),
        hook_subtitle_style="viral_pop",
        hook_window_sec=2.5,
    ),

    "education": StylePack(
        name="education",
        display_name="Education",
        description="Tutorial/lesson. Technical captions, key terms highlighted.",
        subtitle_style="educator",
        subtitle_fallback="teleprompter",
        color_preset="clear_fresh",
        crop=CropConfig(
            zoom_base=1.1,
            zoom_on_hook=1.2,
            person_target_fraction=0.60,
            prefer_person_track=True,
        ),
        pacing=PacingConfig(
            speed_factor=1.0,
            silence_trim_sec=0.1,
            max_dead_air_sec=1.5,
        ),
        emphasis=EmphasisConfig(
            keyword_highlight=True,
            keyword_categories=("numbers", "questions"),
        ),
        hook_subtitle_style="bold_highlight",
        hook_window_sec=3.0,
    ),

    "news_commentary": StylePack(
        name="news_commentary",
        display_name="News Commentary",
        description="Hot takes, reactions. Punchy captions, aggressive crop.",
        subtitle_style="viral_pop",
        subtitle_fallback="bold_highlight",
        color_preset="original",
        crop=CropConfig(
            zoom_base=1.35,
            zoom_on_hook=1.5,
            person_target_fraction=0.75,
            prefer_person_track=True,
        ),
        pacing=PacingConfig(
            speed_factor=1.02,  # Slight speedup for energy
            silence_trim_sec=0.3,
            max_dead_air_sec=1.0,
        ),
        emphasis=EmphasisConfig(
            keyword_highlight=True,
            keyword_categories=("numbers", "superlatives", "questions"),
            hook_zoom_enabled=True,
        ),
        hook_subtitle_style="viral_pop",
        hook_window_sec=2.5,
    ),

    # ── Entertainment genres (v3) ──────────────────────────────────────

    "nature": StylePack(
        name="nature",
        display_name="Thiên nhiên",
        description="Visual-first. Cinematic color, minimal captions, slow pacing.",
        subtitle_style="minimal",
        subtitle_fallback="clean_boxed",
        color_preset="cinematic",
        crop=CropConfig(
            zoom_base=1.0,  # No zoom — show the full scene
            zoom_on_hook=1.0,
            person_target_fraction=0.5,
            prefer_person_track=False,  # Track scene, not person
        ),
        pacing=PacingConfig(
            speed_factor=1.0,
            cut_on_silence=False,  # Don't cut at silence — ambient is content
            silence_trim_sec=0.0,
            max_dead_air_sec=3.0,  # Long ambient pauses OK
        ),
        emphasis=EmphasisConfig(
            keyword_highlight=False,  # Nature doesn't need text emphasis
            hook_zoom_enabled=False,
        ),
    ),

    "history": StylePack(
        name="history",
        display_name="Lịch sử",
        description="Documentary style. Rich captions, factual emphasis.",
        subtitle_style="clean_boxed",
        subtitle_fallback="minimal",
        color_preset="original",
        crop=CropConfig(
            zoom_base=1.1,
            zoom_on_hook=1.2,
            person_target_fraction=0.6,
            prefer_person_track=True,
        ),
        pacing=PacingConfig(
            speed_factor=1.0,
            silence_trim_sec=0.2,
            max_dead_air_sec=1.5,
        ),
        emphasis=EmphasisConfig(
            keyword_highlight=True,
            keyword_categories=("numbers", "superlatives"),
            hook_zoom_enabled=True,
        ),
    ),

    "action": StylePack(
        name="action",
        display_name="Hành động",
        description="High energy. Fast cuts, no zoom, minimal/no captions.",
        subtitle_style="minimal",
        subtitle_fallback="clean_boxed",
        color_preset="original",
        crop=CropConfig(
            zoom_base=1.0,
            zoom_on_hook=1.0,
            person_target_fraction=0.5,
            prefer_person_track=False,  # Track action, not face
        ),
        pacing=PacingConfig(
            speed_factor=1.0,
            cut_on_silence=False,
            silence_trim_sec=0.0,
            max_dead_air_sec=2.0,
        ),
        emphasis=EmphasisConfig(
            keyword_highlight=False,
            hook_zoom_enabled=False,
        ),
    ),

    "kids_music": StylePack(
        name="kids_music",
        display_name="Nhạc thiếu nhi",
        description="Colorful, fun. Lyrics as captions, bright colors.",
        subtitle_style="bold_highlight",
        subtitle_fallback="minimal",
        color_preset="clear_fresh",
        crop=CropConfig(
            zoom_base=1.0,
            zoom_on_hook=1.0,
            person_target_fraction=0.6,
            prefer_person_track=False,
        ),
        pacing=PacingConfig(
            speed_factor=1.0,
            cut_on_silence=False,  # Music is continuous
            silence_trim_sec=0.0,
            max_dead_air_sec=1.0,
        ),
        emphasis=EmphasisConfig(
            keyword_highlight=True,
            keyword_categories=("superlatives",),
            hook_zoom_enabled=False,
        ),
    ),

    "animation": StylePack(
        name="animation",
        display_name="Hoạt hình",
        description="Story-driven. Cinematic, character-focused captions.",
        subtitle_style="clean_boxed",
        subtitle_fallback="minimal",
        color_preset="original",
        crop=CropConfig(
            zoom_base=1.0,
            zoom_on_hook=1.1,
            person_target_fraction=0.5,
            prefer_person_track=False,
        ),
        pacing=PacingConfig(
            speed_factor=1.0,
            silence_trim_sec=0.1,
            max_dead_air_sec=1.5,
        ),
        emphasis=EmphasisConfig(
            keyword_highlight=False,
            hook_zoom_enabled=True,
        ),
        hook_window_sec=2.0,
    ),
}


# ══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════

def get_style_pack(genre: str) -> StylePack:
    """Get style pack by genre name. Falls back to talking_head."""
    return STYLE_PACKS.get(genre, STYLE_PACKS["talking_head"])


def list_style_packs() -> list[dict[str, str]]:
    """List all style packs with metadata for GUI display."""
    return [
        {
            "name": pack.name,
            "display_name": pack.display_name,
            "description": pack.description,
            "subtitle": pack.subtitle_style,
            "color": pack.color_preset,
        }
        for pack in STYLE_PACKS.values()
    ]


def list_pack_names() -> list[str]:
    """Return ordered list of pack names."""
    return list(STYLE_PACKS.keys())
