"""
ASS subtitle builder — generates .ass files from subtitle events + style config.

ASS (Advanced SubStation Alpha) format supports:
  - Rich styling (font, color, outline, shadow, position)
  - Line breaks via \\N
  - Per-event override tags {\\pos} {\\c} {\\bord} etc.
  - Karaoke highlighting via {\\kf} tags
  - Safe area margins, line spacing, font fallback

This builder generates spec-compliant ASS output usable with FFmpeg's `ass` filter.
"""
from __future__ import annotations

from pathlib import Path

import logging

from apps.autosubvideo.schemas import SubtitleStyleConfig
from apps.autosubvideo.segmenter import SubtitleEvent

logger = logging.getLogger(__name__)


# ── Public API ───────────────────────────────────────────────────────────────

def build_ass(
    events: list[SubtitleEvent],
    style: SubtitleStyleConfig,
    output_path: str,
    *,
    title: str = "Auto Sub Video",
    video_width: int = 1920,
    video_height: int = 1080,
    highlight_mode: str = "none",
    highlight_color: str = "#FFD700",
    keyword_highlights: list[str] | None = None,
    keyword_highlight_color: str = "#FF4444",
) -> str:
    """
    Build a complete ASS subtitle file.
    Returns the output file path.
    """
    header = _build_header(title, video_width, video_height)
    styles = _build_styles_section(style, video_width, video_height, highlight_color=highlight_color)
    dialogue = _build_events_section(
        events, style, highlight_mode, highlight_color,
        video_width=video_width, video_height=video_height,
        keyword_highlights=keyword_highlights or [],
        keyword_highlight_color=keyword_highlight_color,
    )

    content = f"{header}\n{styles}\n{dialogue}\n"

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8-sig")  # BOM for player compatibility

    logger.debug(
        "[ass_builder] wrote %s: %d events, style=%s/%s, %dx%d",
        path.name, len(events), style.font_family, style.font_size,
        video_width, video_height,
    )

    return str(path)


def build_srt(
    events: list[SubtitleEvent],
    output_path: str,
) -> str:
    """
    Build an SRT subtitle file (plain text, no styling).
    Returns the output file path.
    """
    lines: list[str] = []

    for i, ev in enumerate(events, start=1):
        start_ts = _format_srt_time(ev.start)
        end_ts = _format_srt_time(ev.end)
        # SRT uses literal newlines, not \N
        text = ev.display_text.replace("\\N", "\n")
        lines.append(f"{i}")
        lines.append(f"{start_ts} --> {end_ts}")
        lines.append(text)
        lines.append("")  # blank line separator

    content = "\n".join(lines)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    logger.debug("[ass_builder] wrote SRT: %s (%d events)", path.name, len(events))

    return str(path)


# ── ASS Header ───────────────────────────────────────────────────────────────

def _build_header(title: str, width: int, height: int) -> str:
    return (
        "[Script Info]\n"
        f"Title: {title}\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {width}\n"
        f"PlayResY: {height}\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        "YCbCr Matrix: TV.709\n"
    )


# ── ASS Styles ───────────────────────────────────────────────────────────────

def _build_styles_section(
    style: SubtitleStyleConfig,
    video_width: int = 1920,
    video_height: int = 1080,
    highlight_color: str = "#FFD700",
) -> str:
    """Build [V4+ Styles] section from SubtitleStyleConfig."""
    primary = _hex_to_ass_color(style.font_color)
    secondary = _hex_to_ass_color(highlight_color)  # Used by \kf karaoke tags
    outline = _hex_to_ass_color(style.outline_color)
    shadow = _hex_to_ass_color(
        getattr(style, "shadow_color", style.outline_color),
        alpha=80,
    )

    # Background box: use BorderStyle=3 (opaque box) if bg_box enabled
    if style.bg_box:
        back_color = _hex_to_ass_color(
            style.bg_color,
            alpha=int((1 - style.bg_opacity) * 255),
        )
        border_style = 3
        # For bg_box, outline_width acts as box padding
        effective_outline = getattr(style, "bg_padding", style.outline_width)
    else:
        back_color = "&H80000000"
        border_style = 1
        effective_outline = style.outline_width

    bold_flag = -1 if style.bold else 0
    italic_flag = -1 if style.italic else 0

    # Compute safe-area-adjusted margins
    safe_pct = getattr(style, "safe_area_percent", 0)
    margin_h = style.margin_h
    margin_v = style.margin_v
    if safe_pct > 0:
        safe_h = int(video_width * safe_pct / 100)
        safe_v = int(video_height * safe_pct / 100)
        margin_h = max(margin_h, safe_h)
        margin_v = max(margin_v, safe_v)

    # Line spacing → ASS Spacing field (inter-character) + custom
    spacing = getattr(style, "line_spacing", 0)

    # Font — use primary font, ASS handles system fallback natively
    font = style.font_family

    # Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour,
    #         OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut,
    #         ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow,
    #         Alignment, MarginL, MarginR, MarginV, Encoding
    default_line = (
        f"Style: Default,{font},{style.font_size},"
        f"{primary},{secondary},{outline},{back_color},"
        f"{bold_flag},{italic_flag},0,0,"
        f"100,100,{spacing},0,{border_style},{effective_outline},{style.shadow_offset},"
        f"{style.alignment},{margin_h},{margin_h},{margin_v},1"
    )

    return (
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"{default_line}\n"
    )


# ── ASS Events ──────────────────────────────────────────────────────────────

def _build_events_section(
    events: list[SubtitleEvent],
    style: SubtitleStyleConfig,
    highlight_mode: str,
    highlight_color: str,
    keyword_highlights: list[str] | None = None,
    keyword_highlight_color: str = "#FF4444",
    video_width: int = 1920,
    video_height: int = 1080,
) -> str:
    """Build [Events] section with Dialogue lines."""
    lines = [
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for ev in events:
        start_ts = _format_ass_time(ev.start)
        end_ts = _format_ass_time(ev.end)
        text = _apply_highlight(
            ev, highlight_mode, highlight_color,
            keyword_highlights=keyword_highlights or [],
            keyword_highlight_color=keyword_highlight_color,
        )
        text = _apply_animation(text, style, video_width, video_height)

        line = f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}"
        lines.append(line)

    return "\n".join(lines)


def _apply_animation(text: str, style: SubtitleStyleConfig,
                     video_width: int, video_height: int) -> str:
    """ASS/libass-compatible entry animation shared with Studio preview."""
    mode = getattr(style, "animation", "none")
    duration = max(0, min(int(getattr(style, "animation_ms", 180)), 1000))
    if mode == "fade" and duration:
        return f"{{\\fad({duration},0)}}{text}"
    if mode == "pop" and duration:
        return (f"{{\\fscx70\\fscy70\\t(0,{duration},"
                f"\\fscx100\\fscy100)}}{text}")
    if mode == "slide_up" and duration:
        x = video_width // 2
        target_y = max(0, video_height - style.margin_v)
        return f"{{\\move({x},{target_y + 80},{x},{target_y},0,{duration})}}{text}"
    return text


# ── Highlight modes ──────────────────────────────────────────────────────────

def _sanitize_ass_text(text: str) -> str:
    """Remove stray curly braces that ASS would interpret as override tags."""
    # Only strip { } that are NOT valid ASS overrides (our own tags start with \)
    import re
    # Remove {content} blocks that don't start with a backslash (user text, not ASS tags)
    return re.sub(r"\{(?!\\)", "（", text).replace("}", "）")


def _apply_highlight(
    ev: SubtitleEvent,
    mode: str,
    color: str,
    keyword_highlights: list[str] | None = None,
    keyword_highlight_color: str = "#FF4444",
) -> str:
    """Apply highlight effect to subtitle text."""
    text = _sanitize_ass_text(ev.display_text)

    if mode == "none":
        return text

    if mode == "word":
        return _highlight_word_by_word(ev, color)

    if mode == "underline":
        return _highlight_underline(text, color)

    if mode == "bg_flash":
        return _highlight_bg_flash(text, color)

    if mode == "all_text":
        return _highlight_all_text(text, color)

    if mode == "keyword":
        return _highlight_keywords(text, keyword_highlights or [], keyword_highlight_color)

    return text


def _highlight_word_by_word(ev: SubtitleEvent, color: str) -> str:
    """
    Karaoke-style: use ASS \\kf tags to highlight each word sequentially.
    Duration per word = total event duration / word count.
    """
    raw = _sanitize_ass_text(ev.display_text).replace("\\N", " \\N ")
    words = raw.split()

    if len(words) <= 1:
        return ev.display_text

    dur_cs = int((ev.end - ev.start) * 100)
    speech_words = [w for w in words if w != "\\N"]
    per_word = max(dur_cs // len(speech_words), 1) if speech_words else dur_cs

    parts: list[str] = []
    for word in words:
        if word == "\\N":
            parts.append("\\N")
        else:
            parts.append(f"{{\\kf{per_word}}}{word}")

    return " ".join(parts).replace(" \\N ", "\\N")


def _highlight_underline(text: str, color: str) -> str:
    """Add underline + accent color override to the entire event."""
    ass_color = _hex_to_ass_color(color)
    return f"{{\\u1\\c{ass_color}}}{text}"


def _highlight_bg_flash(text: str, color: str) -> str:
    """Fade-in effect with accent color: text appears with a quick alpha fade."""
    ass_color = _hex_to_ass_color(color)
    return f"{{\\fad(150,50)\\c{ass_color}}}{text}"


def _highlight_all_text(text: str, color: str) -> str:
    """All text rendered in accent color — uniform highlight for entire subtitle."""
    ass_color = _hex_to_ass_color(color)
    return f"{{\\c{ass_color}}}{text}"


def _highlight_keywords(text: str, keywords: list[str], color: str) -> str:
    """
    Highlight specific keywords within subtitle text.
    Each matching word gets override tags to change color.
    Case-insensitive matching.
    """
    if not keywords:
        return text

    import re as _re
    ass_color = _hex_to_ass_color(color)
    # Get the primary style color tag to reset after keyword
    reset_tag = "{\\r}"

    # Build a regex pattern matching any keyword (case insensitive, word boundary)
    escaped = [_re.escape(kw) for kw in keywords if kw.strip()]
    if not escaped:
        return text

    pattern = _re.compile(
        r"(?<!\{\\)(\b(?:" + "|".join(escaped) + r")\b)",
        _re.IGNORECASE,
    )

    def _replace(m):
        return f"{{\\c{ass_color}}}{m.group(1)}{reset_tag}"

    return pattern.sub(_replace, text)


# ── Color conversion ────────────────────────────────────────────────────────

def _hex_to_ass_color(hex_color: str, alpha: int = 0) -> str:
    """
    Convert #RRGGBB to ASS color format &HAABBGGRR.
    ASS uses BGR order with alpha (00=opaque, FF=transparent).
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    else:
        r, g, b = 255, 255, 255

    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


# ── Time formatting ─────────────────────────────────────────────────────────

def _format_ass_time(seconds: float) -> str:
    """Convert seconds to ASS timestamp: H:MM:SS.cc"""
    seconds = max(0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp: HH:MM:SS,mmm"""
    seconds = max(0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
