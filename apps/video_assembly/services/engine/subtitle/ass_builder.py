"""
ASS subtitle builder — generates .ass files from subtitle events + style config.

ASS (Advanced SubStation Alpha) format supports:
  - Rich styling (font, color, outline, shadow, position)
  - Line breaks via \\N
  - Per-event override tags {\\pos} {\\c} {\\bord} etc.
  - Karaoke highlighting via {\\kf} tags
  - Safe area margins, line spacing, font fallback

This builder generates spec-compliant ASS output usable with FFmpeg's `ass` filter.

Extracted from BOT GEMINI auto_sub_video/ass_builder.py.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from .schemas import SubtitleStyleConfig
from .segmenter import SubtitleEvent

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
    styles = _build_styles_section(
        style, video_width, video_height,
        highlight_color=highlight_color,
        highlight_mode=highlight_mode,
    )
    dialogue = _build_events_section(
        events, style, highlight_mode, highlight_color,
        keyword_highlights=keyword_highlights or [],
        keyword_highlight_color=keyword_highlight_color,
        video_width=video_width,
        video_height=video_height,
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
    highlight_mode: str = "none",
) -> str:
    """Build [V4+ Styles] section from SubtitleStyleConfig.

    For karaoke mode ("word"): ASS \\kf tags transition text FROM SecondaryColour
    TO PrimaryColour.  So PrimaryColour must be the *highlight* color (the color
    text becomes after the sweep) and SecondaryColour must be the *font* color
    (the color text starts as before the sweep).

    For all other modes: PrimaryColour = font_color, SecondaryColour = highlight_color
    (override tags in dialogue lines handle the coloring).
    """
    if highlight_mode == "word":
        # Karaoke: swap so text starts as font_color, sweeps to highlight_color
        primary = _hex_to_ass_color(highlight_color)
        secondary = _hex_to_ass_color(style.font_color)
    else:
        primary = _hex_to_ass_color(style.font_color)
        secondary = _hex_to_ass_color(highlight_color)
    # Background box: use BorderStyle=3 (opaque box) if bg_box enabled
    if style.bg_box:
        back_color = _hex_to_ass_color(
            style.bg_color,
            alpha=int((1 - style.bg_opacity) * 255),
        )
        border_style = 3
        effective_outline = getattr(style, "bg_padding", style.outline_width)
        # In ASS BorderStyle=3, OutlineColour renders as text outline ON TOP of
        # the box.  Using the user's outline_color (meant for non-box mode) would
        # paint a visible halo over the box background.  Set OutlineColour to
        # match bg_color so the text outline blends with the box.
        outline = _hex_to_ass_color(
            style.bg_color,
            alpha=int((1 - style.bg_opacity) * 255),
        )
        shadow_offset = 0  # no drop-shadow on the box itself
    else:
        back_color = "&H80000000"
        border_style = 1
        effective_outline = style.outline_width
        outline = _hex_to_ass_color(style.outline_color)
        shadow_offset = style.shadow_offset

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

    # ASS Spacing field = inter-CHARACTER spacing (horizontal), NOT line spacing.
    # Vertical line spacing is handled in _build_events_section via spacer lines.
    spacing = 0

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
        f"100,100,{spacing},0,{border_style},{effective_outline},{shadow_offset},"
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
    """Build [Events] section with Dialogue lines.

    When line_spacing > 0 and alignment is bottom (1-3) or top (7-9), each
    \\N-separated line is emitted as its own Dialogue event with a per-event
    MarginV override.  This is the only reliable way to control vertical gap
    between lines in libass/FFmpeg: the ASS Spacing field is inter-character
    only, and alpha override tags cannot suppress the background box for an
    individual line within a multi-line event.

    For karaoke (highlight_mode='word') or middle alignment (4-6), lines are
    kept in a single event because splitting would corrupt karaoke timing or
    require complex centre-point math.
    """
    result_lines = [
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    line_spacing = getattr(style, "line_spacing", 0)
    alignment = style.alignment  # ASS numpad: 1-3=bottom, 4-6=middle, 7-9=top

    # Effective base margin_v (mirrors safe-area logic in _build_styles_section)
    safe_pct = getattr(style, "safe_area_percent", 0)
    base_margin_v = style.margin_v
    if safe_pct > 0:
        safe_v = int(video_height * safe_pct / 100)
        base_margin_v = max(base_margin_v, safe_v)

    # Height of one rendered line (text + box padding above and below).
    # Used to calculate per-line MarginV when splitting events.
    # Non-box mode: approximate with font ascent ratio (most fonts ~1.2×).
    bg_padding = getattr(style, "bg_padding", 0) if style.bg_box else 0
    line_h = style.font_size + 2 * bg_padding

    # Decide whether to split multi-line events into separate Dialogue events.
    # Conditions: explicit spacing requested, bottom/top alignment, not karaoke.
    split_lines = (
        line_spacing > 0
        and alignment in (1, 2, 3, 7, 8, 9)
        and highlight_mode != "word"   # karaoke timing must stay in one event
    )

    for ev in events:
        start_ts = _format_ass_time(ev.start)
        end_ts = _format_ass_time(ev.end)

        raw_parts = ev.display_text.split("\\N")

        if not split_lines or len(raw_parts) <= 1:
            # ── Single-event path (original behaviour) ──────────────────────
            text = _apply_highlight(
                ev, highlight_mode, highlight_color,
                keyword_highlights=keyword_highlights or [],
                keyword_highlight_color=keyword_highlight_color,
            )
            result_lines.append(
                f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{text}"
            )
        else:
            # ── Split path: one Dialogue event per line ──────────────────────
            # Each event uses a per-event MarginV (7th positional field) that
            # overrides the style's MarginV for this specific line.
            n = len(raw_parts)
            for i, part_text in enumerate(raw_parts):
                # Build a minimal event for per-line highlight processing.
                # For non-word modes _apply_highlight only needs display_text.
                line_ev = SubtitleEvent(
                    start=ev.start,
                    end=ev.end,
                    text=part_text,
                    display_text=part_text,
                )
                highlighted = _apply_highlight(
                    line_ev, highlight_mode, highlight_color,
                    keyword_highlights=keyword_highlights or [],
                    keyword_highlight_color=keyword_highlight_color,
                )

                if alignment in (1, 2, 3):
                    # Bottom alignment: i=0 is top line, i=n-1 is bottom line.
                    # Bottom line sits at base_margin_v; each line above it
                    # adds one (line_h + line_spacing) step.
                    pos_from_bottom = n - 1 - i
                    margin_v = base_margin_v + pos_from_bottom * (line_h + line_spacing)
                else:
                    # Top alignment (7, 8, 9): i=0 is top, grows downward.
                    margin_v = base_margin_v + i * (line_h + line_spacing)

                result_lines.append(
                    f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,{margin_v},,{highlighted}"
                )

    return "\n".join(result_lines)


# ── Highlight modes ──────────────────────────────────────────────────────────

def _sanitize_ass_text(text: str) -> str:
    """Remove stray curly braces that ASS would interpret as override tags."""
    # Only strip { } that are NOT valid ASS overrides (our own tags start with \)
    return re.sub(r"\{(?!\\)", "\uff08", text).replace("}", "\uff09")


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

    ass_color = _hex_to_ass_color(color)
    # Get the primary style color tag to reset after keyword
    reset_tag = "{\\r}"

    # Build a regex pattern matching any keyword (case insensitive, word boundary)
    escaped = [re.escape(kw) for kw in keywords if kw.strip()]
    if not escaped:
        return text

    pattern = re.compile(
        r"(?<!\{\\)(\b(?:" + "|".join(escaped) + r")\b)",
        re.IGNORECASE,
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
