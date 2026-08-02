"""Subtitle style registry — defines all available caption visual presets.

Each style is a complete CaptionStyle instance with font, color, position,
animation, line-breaking, keyword highlight, and safe-area parameters.

Adding a new subtitle style = add one entry here. No other file changes needed.

Style categories:
- CLEAN:     Minimal distraction, readability first
- IMPACT:    Bold, attention-grabbing, social-media optimized
- NARRATIVE: Story-friendly, cinematic feel
- TECHNICAL: Dense info, education/review content
"""

from __future__ import annotations

from cutclipshort.types import CaptionStyle

# ══════════════════════════════════════════════════════════════════════════
# SUBTITLE STYLE DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════

SUBTITLE_STYLES: dict[str, CaptionStyle] = {

    # ── CLEAN category ────────────────────────────────────────────────

    "minimal": CaptionStyle(
        preset_name="minimal",
        font_family="Inter",
        font_size=44,
        font_color="#FFFFFF",
        active_word_color="#FFFFFF",
        outline_color="#000000",
        outline_width=2,
        shadow_enabled=True,
        shadow_color="#00000060",
        bg_box_enabled=False,
        position="bottom",
        animation="none",
        max_chars_per_line=38,
    ),

    "clean_boxed": CaptionStyle(
        preset_name="clean_boxed",
        font_family="Inter",
        font_size=42,
        font_color="#FFFFFF",
        active_word_color="#FFFFFF",
        outline_color="#00000000",
        outline_width=0,
        shadow_enabled=False,
        bg_box_enabled=True,
        bg_box_color="#000000B3",
        position="bottom",
        animation="none",
        max_chars_per_line=40,
    ),

    # ── IMPACT category ───────────────────────────────────────────────

    "bold_highlight": CaptionStyle(
        preset_name="bold_highlight",
        font_family="Montserrat",
        font_size=54,
        font_color="#FFFFFF",
        active_word_color="#FFDD00",
        outline_color="#000000",
        outline_width=3,
        shadow_enabled=True,
        shadow_color="#00000099",
        bg_box_enabled=False,
        position="center",
        animation="none",
        max_chars_per_line=28,
    ),

    "viral_pop": CaptionStyle(
        preset_name="viral_pop",
        font_family="Montserrat",
        font_size=58,
        font_color="#FFFFFF",
        active_word_color="#FF3B3B",
        outline_color="#000000",
        outline_width=4,
        shadow_enabled=True,
        shadow_color="#000000CC",
        bg_box_enabled=False,
        position="center",
        animation="none",
        max_chars_per_line=24,
    ),

    "neon_accent": CaptionStyle(
        preset_name="neon_accent",
        font_family="Montserrat",
        font_size=52,
        font_color="#FFFFFF",
        active_word_color="#00FF88",
        outline_color="#000000",
        outline_width=3,
        shadow_enabled=True,
        shadow_color="#00FF8833",
        bg_box_enabled=False,
        position="center",
        animation="none",
        max_chars_per_line=30,
    ),

    # ── NARRATIVE category ────────────────────────────────────────────

    "cinematic": CaptionStyle(
        preset_name="cinematic",
        font_family="Georgia",
        font_size=40,
        font_color="#F0E6D3",
        active_word_color="#F0E6D3",
        outline_color="#000000",
        outline_width=1,
        shadow_enabled=True,
        shadow_color="#00000080",
        bg_box_enabled=False,
        position="bottom",
        animation="none",
        max_chars_per_line=42,
    ),

    "story_emphasis": CaptionStyle(
        preset_name="story_emphasis",
        font_family="Georgia",
        font_size=46,
        font_color="#FFFFFF",
        active_word_color="#FFB347",
        outline_color="#1A1A1A",
        outline_width=2,
        shadow_enabled=True,
        shadow_color="#00000099",
        bg_box_enabled=False,
        position="bottom",
        animation="none",
        max_chars_per_line=35,
    ),

    # ── TECHNICAL category ────────────────────────────────────────────

    "educator": CaptionStyle(
        preset_name="educator",
        font_family="Inter",
        font_size=42,
        font_color="#FFFFFF",
        active_word_color="#4FC3F7",
        outline_color="#000000",
        outline_width=2,
        shadow_enabled=True,
        shadow_color="#00000080",
        bg_box_enabled=True,
        bg_box_color="#1A1A1AB3",
        position="bottom",
        animation="none",
        max_chars_per_line=40,
    ),

    "teleprompter": CaptionStyle(
        preset_name="teleprompter",
        font_family="Inter",
        font_size=38,
        font_color="#E0E0E0",
        active_word_color="#FFFFFF",
        outline_color="#000000",
        outline_width=1,
        shadow_enabled=False,
        bg_box_enabled=True,
        bg_box_color="#000000CC",
        position="bottom",
        animation="none",
        max_chars_per_line=45,
    ),

    # ── FUN category ──────────────────────────────────────────────────

    "karaoke": CaptionStyle(
        preset_name="karaoke",
        font_family="Impact",
        font_size=52,
        font_color="#FFFFFF",
        active_word_color="#FF4444",
        outline_color="#000000",
        outline_width=2,
        shadow_enabled=False,
        bg_box_enabled=True,
        bg_box_color="#00000099",
        position="bottom",
        animation="none",
        max_chars_per_line=30,
    ),

    "comedy_bold": CaptionStyle(
        preset_name="comedy_bold",
        font_family="Impact",
        font_size=56,
        font_color="#FFFFFF",
        active_word_color="#FFE135",
        outline_color="#000000",
        outline_width=4,
        shadow_enabled=True,
        shadow_color="#000000CC",
        bg_box_enabled=False,
        position="center",
        animation="none",
        max_chars_per_line=22,
    ),
}


# ── Public API ───────────────────────────────────────────────────────────

def get_subtitle_style(name: str) -> CaptionStyle:
    """Get subtitle style by name. Falls back to minimal."""
    return SUBTITLE_STYLES.get(name, SUBTITLE_STYLES["minimal"])


def list_subtitle_styles() -> list[dict[str, str]]:
    """List all available subtitle styles with metadata."""
    categories = {
        "minimal": "Clean", "clean_boxed": "Clean",
        "bold_highlight": "Impact", "viral_pop": "Impact", "neon_accent": "Impact",
        "cinematic": "Narrative", "story_emphasis": "Narrative",
        "educator": "Technical", "teleprompter": "Technical",
        "karaoke": "Fun", "comedy_bold": "Fun",
    }
    return [
        {
            "name": name,
            "display_name": name.replace("_", " ").title(),
            "category": categories.get(name, "Other"),
            "font": style.font_family,
            "position": style.position,
            "animation": style.animation,
        }
        for name, style in SUBTITLE_STYLES.items()
    ]


def list_style_names() -> list[str]:
    """Return ordered list of style names."""
    return list(SUBTITLE_STYLES.keys())
