"""
Subtitle style configuration — dataclass version (no pydantic dependency).
Extracted from BOT GEMINI auto_sub_video/schemas.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SubtitleStyleConfig:
    """Subtitle styling options for burn-in render."""
    # Font
    font_family: str = "Arial"
    font_size: int = 48
    font_color: str = "#FFFFFF"
    bold: bool = True
    italic: bool = False
    font_fallback: str = "Arial,Helvetica,sans-serif"

    # Outline & shadow
    outline_color: str = "#000000"
    outline_width: int = 2
    shadow_color: str = "#000000"
    shadow_offset: int = 1

    # Position & spacing
    alignment: int = 2
    margin_v: int = 30
    margin_h: int = 20
    line_spacing: int = 0

    # Background box
    bg_box: bool = False
    bg_color: str = "#000000"
    bg_opacity: float = 0.5
    bg_padding: int = 10

    # Safe area
    safe_area_percent: int = 0

    # Text layout
    max_chars_per_line: int = 42
    max_lines: int = 2

    # Highlight (karaoke) settings
    highlight_mode: str = "none"
    highlight_color: str = "#FFD700"
    keyword_highlights: List[str] = field(default_factory=list)
    keyword_highlight_color: str = "#FF4444"

    def copy_with(self, **updates) -> "SubtitleStyleConfig":
        """Create a copy with updated fields (replaces pydantic model_copy)."""
        import dataclasses
        d = dataclasses.asdict(self)
        d.update(updates)
        return SubtitleStyleConfig(**d)


@dataclass
class StylePreset:
    """Style preset metadata for API/GUI listing."""
    id: str = ""
    label: str = ""
    description: str = ""
    config: Optional[SubtitleStyleConfig] = None
    highlight_mode: str = "none"
    highlight_color: str = "#FFD700"
