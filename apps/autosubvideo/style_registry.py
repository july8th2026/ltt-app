"""
Style registry — subtitle style presets for auto_sub_video.

Each preset maps to a full SubtitleStyleConfig with concrete values
for font, color, outline, shadow, position, and highlight behavior.

Highlight modes:
  - none:       Plain text, no word highlighting
  - word:       Current word highlighted in accent color (karaoke-style)
  - underline:  Current phrase underlined
  - bg_flash:   Background box flashes on each new subtitle
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from apps.autosubvideo.schemas import SubtitleStyleConfig, StylePreset


HighlightMode = Literal["none", "word", "underline", "bg_flash"]


@dataclass
class FullStylePreset:
    """Complete style definition — preset metadata + config + highlight."""
    id: str
    label: str
    description: str
    config: SubtitleStyleConfig
    highlight_mode: HighlightMode = "none"
    highlight_color: str = "#FFD700"    # Accent color for highlight


# ── Preset definitions ───────────────────────────────────────────────────────

_PRESETS: dict[str, FullStylePreset] = {}


def _register(preset: FullStylePreset) -> FullStylePreset:
    _PRESETS[preset.id] = preset
    return preset


# LTT Studios brand template — reusable, deterministic and render-parity safe.
_register(FullStylePreset(
    id="ltt_brand",
    label="LTT Brand",
    description="Trắng đậm, nhấn đỏ Carbon Red — đồng nhất nhận diện LTT Studios",
    config=SubtitleStyleConfig(
        font_family="Montserrat", font_size=58, font_color="#FFFFFF",
        font_fallback="Montserrat,Arial,sans-serif", outline_color="#08090A",
        outline_width=3, shadow_color="#08090A", shadow_offset=2, bold=True,
        italic=False, alignment=2, margin_v=54, margin_h=34, line_spacing=2,
        bg_box=True, bg_color="#08090A", bg_opacity=0.72, bg_padding=12,
        safe_area_percent=5, max_chars_per_line=34, max_lines=2,
    ),
    highlight_mode="word",
    highlight_color="#EF3731",
))


# ── 1. TikTok Bold ───────────────────────────────────────────────────────────
_register(FullStylePreset(
    id="tiktok_bold",
    label="TikTok Bold",
    description="Trắng bold viền dày, center, 1 dòng ngắn — chuẩn viral",
    config=SubtitleStyleConfig(
        font_family="Montserrat",
        font_size=64,
        font_color="#FFFFFF",
        font_fallback="Montserrat,Arial,sans-serif",
        outline_color="#000000",
        outline_width=4,
        shadow_offset=0,
        bold=True,
        italic=False,
        alignment=5,
        margin_v=60,
        margin_h=30,
        line_spacing=5,
        bg_box=False,
        safe_area_percent=5,
        max_chars_per_line=25,
    ),
    highlight_mode="word",
    highlight_color="#FFEE00",
))

# ── 2. Reels Clean ──────────────────────────────────────────────────────────
_register(FullStylePreset(
    id="reels_clean",
    label="Reels Clean",
    description="Trắng trên nền đen bán trong suốt, gọn gàng, dễ đọc",
    config=SubtitleStyleConfig(
        font_family="Helvetica Neue",
        font_size=44,
        font_color="#FFFFFF",
        font_fallback="Helvetica Neue,Helvetica,Arial,sans-serif",
        outline_color="#000000",
        outline_width=0,
        shadow_offset=0,
        bold=True,
        italic=False,
        alignment=2,
        margin_v=50,
        margin_h=40,
        line_spacing=2,
        bg_box=True,
        bg_color="#000000",
        bg_opacity=0.6,
        bg_padding=15,
        safe_area_percent=3,
        max_chars_per_line=35,
    ),
    highlight_mode="bg_flash",
    highlight_color="#FFFFFF",
))

# ── 3. Cinematic ────────────────────────────────────────────────────────────
_register(FullStylePreset(
    id="cinematic",
    label="Cinematic",
    description="Vàng nhạt, serif font, letterbox — phong cách phim điện ảnh",
    config=SubtitleStyleConfig(
        font_family="Georgia",
        font_size=42,
        font_color="#F5E6CA",
        font_fallback="Georgia,Times New Roman,serif",
        outline_color="#1A1A1A",
        shadow_color="#0A0A0A",
        outline_width=2,
        shadow_offset=2,
        bold=False,
        italic=True,
        alignment=2,
        margin_v=40,
        margin_h=60,
        line_spacing=4,
        bg_box=False,
        safe_area_percent=5,
        max_chars_per_line=45,
    ),
    highlight_mode="none",
))

# ── 4. Meme Punch ───────────────────────────────────────────────────────────
_register(FullStylePreset(
    id="meme_punch",
    label="Meme Punch",
    description="Impact font, trắng viền đen cực dày — kiểu meme/gaming",
    config=SubtitleStyleConfig(
        font_family="Impact",
        font_size=72,
        font_color="#FFFFFF",
        font_fallback="Impact,Arial Black,sans-serif",
        outline_color="#000000",
        outline_width=5,
        shadow_offset=0,
        bold=True,
        italic=False,
        alignment=5,
        margin_v=20,
        margin_h=20,
        line_spacing=0,
        bg_box=False,
        max_chars_per_line=20,
    ),
    highlight_mode="word",
    highlight_color="#FF4444",
))

# ── 5. Kids Color ───────────────────────────────────────────────────────────
_register(FullStylePreset(
    id="kids_color",
    label="Kids Color",
    description="Vàng tươi, viền xanh dương, vui nhộn — kênh thiếu nhi",
    config=SubtitleStyleConfig(
        font_family="Comic Sans MS",
        font_size=56,
        font_color="#FFD700",
        font_fallback="Comic Sans MS,Comic Neue,cursive",
        outline_color="#1E90FF",
        outline_width=3,
        shadow_offset=2,
        bold=True,
        italic=False,
        alignment=2,
        margin_v=35,
        margin_h=30,
        line_spacing=3,
        bg_box=True,
        bg_color="#000080",
        bg_opacity=0.4,
        bg_padding=12,
        max_chars_per_line=30,
    ),
    highlight_mode="word",
    highlight_color="#FF69B4",
))

# ── 6. Punchline ────────────────────────────────────────────────────────
_register(FullStylePreset(
    id="punchline",
    label="Punchline",
    description="Đỏ cam nổi bật, chữ to, center — tối ưu cho hook & emphasis",
    config=SubtitleStyleConfig(
        font_family="Anton",
        font_size=80,
        font_color="#FF6B35",
        font_fallback="Anton,Impact,Arial Black,sans-serif",
        outline_color="#000000",
        outline_width=4,
        shadow_offset=3,
        shadow_color="#1A0A00",
        bold=True,
        italic=False,
        alignment=5,
        margin_v=0,
        margin_h=40,
        line_spacing=0,
        bg_box=False,
        safe_area_percent=5,
        max_chars_per_line=20,
        max_lines=1,
    ),
    highlight_mode="all_text",
    highlight_color="#FFFFFF",
))

# ── 7. Word Emphasis ──────────────────────────────────────────────────
_register(FullStylePreset(
    id="word_emphasis",
    label="Word Emphasis",
    description="Từng chữ reveal, nền tối, hiệu ứng typing — kịch tính, lyric video",
    config=SubtitleStyleConfig(
        font_family="Oswald",
        font_size=72,
        font_color="#E0E0E0",
        font_fallback="Oswald,Impact,Arial,sans-serif",
        outline_color="#000000",
        outline_width=3,
        shadow_offset=2,
        shadow_color="#000000",
        bold=True,
        italic=False,
        alignment=5,
        margin_v=0,
        margin_h=30,
        line_spacing=0,
        bg_box=True,
        bg_color="#000000",
        bg_opacity=0.7,
        bg_padding=20,
        safe_area_percent=0,
        max_chars_per_line=30,
        max_lines=1,
    ),
    highlight_mode="word",
    highlight_color="#00E5FF",
))

# ── 8. Default ──────────────────────────────────────────────────────────────
_register(FullStylePreset(
    id="default",
    label="Mặc định",
    description="Trắng viền đen, Arial Bold — phổ thông, dễ đọc",
    config=SubtitleStyleConfig(
        font_family="Arial",
        font_size=48,
        font_color="#FFFFFF",
        outline_color="#000000",
        outline_width=2,
        shadow_offset=1,
        bold=True,
        italic=False,
        alignment=2,
        margin_v=30,
        margin_h=20,
        bg_box=False,
        max_chars_per_line=42,
    ),
    highlight_mode="none",
))


# ── Public API ───────────────────────────────────────────────────────────────

def get_preset(style_id: str) -> Optional[FullStylePreset]:
    """Get a full style preset by ID. Returns None if not found."""
    return _PRESETS.get(style_id)


def get_config(style_id: str) -> SubtitleStyleConfig:
    """
    Resolve style_id → SubtitleStyleConfig.
    Falls back to 'default' if style_id not found.
    """
    preset = _PRESETS.get(style_id) or _PRESETS["default"]
    return preset.config


def get_highlight_mode(style_id: str) -> HighlightMode:
    """Get the highlight mode for a style preset."""
    preset = _PRESETS.get(style_id) or _PRESETS["default"]
    return preset.highlight_mode


def get_highlight_color(style_id: str) -> str:
    """Get the highlight accent color for a style preset."""
    preset = _PRESETS.get(style_id) or _PRESETS["default"]
    return preset.highlight_color


def list_presets() -> list[StylePreset]:
    """Return all presets as StylePreset (for API response), including full config."""
    return [
        StylePreset(
            id=p.id,
            label=p.label,
            description=p.description,
            config=p.config,
            highlight_mode=p.highlight_mode,
            highlight_color=p.highlight_color,
        )
        for p in _PRESETS.values()
    ]


def list_ids() -> list[str]:
    """Return all available style IDs."""
    return list(_PRESETS.keys())
