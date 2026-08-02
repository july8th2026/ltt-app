"""FFmpeg filter graph builder.

Builds complex video/audio filter chains for encoding.
Ported from NerfWarAI's ffmpeg_edit_cutonly.py _build_vf/_build_af patterns.

[C2] Caption subtitle filter support:
  - build_subtitle_filter(): tao subtitles filter tu SRT path
  - generate_srt(): tao file SRT tu transcript segments
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


def build_video_filters(
    color_config: dict[str, Any],
    speed_factor: float = 1.0,
    crop: dict[str, int] | None = None,
    target_width: int = 1080,
    target_height: int = 1920,
) -> str:
    """Build an FFmpeg video filter chain string.

    Applies in order: crop → scale → color grade → speed → sharpen.
    Returns a -vf compatible filter string.
    """
    filters: list[str] = []

    # 1. Crop (for reframing)
    if crop:
        filters.append(
            f"crop={crop['w']}:{crop['h']}:{crop['x']}:{crop['y']}"
        )

    # 2. Scale to target resolution
    filters.append(f"scale={target_width}:{target_height}:flags=lanczos")

    # 3. Color grading
    if color_config.get("film_enabled", False):
        curves = color_config.get("film_curves", "")
        if curves:
            filters.append(f"curves={curves}")

        hue_deg = color_config.get("film_hue_deg", 0)
        sat = color_config.get("film_sat", 1.0)
        if hue_deg != 0 or sat != 1.0:
            filters.append(f"hue=h={hue_deg}:s={sat}")

    # 4. EQ (contrast, saturation, brightness)
    eq_parts = []
    contrast = color_config.get("eq_contrast", 1.0)
    saturation = color_config.get("eq_saturation", 1.0)
    brightness = color_config.get("eq_brightness", 0.0)
    if contrast != 1.0:
        eq_parts.append(f"contrast={contrast}")
    if saturation != 1.0:
        eq_parts.append(f"saturation={saturation}")
    if brightness != 0.0:
        eq_parts.append(f"brightness={brightness}")
    if eq_parts:
        filters.append(f"eq={':'.join(eq_parts)}")

    # 5. Sharpen
    unsharp = color_config.get("unsharp_luma", 0.0)
    if unsharp > 0:
        filters.append(f"unsharp=5:5:{unsharp}:5:5:0")

    # 6. Speed (setpts for video)
    if speed_factor != 1.0:
        pts_factor = 1.0 / speed_factor
        filters.append(f"setpts={pts_factor:.4f}*PTS")

    return ",".join(filters) if filters else ""


def build_audio_filters(
    speed_factor: float = 1.0,
    loudnorm_enabled: bool = True,
    loudnorm_lufs: float = -14.0,
    loudnorm_true_peak_db: float = -1.5,
) -> str:
    """Build an FFmpeg audio filter chain string.

    Applies: atempo (speed) → loudnorm.
    """
    filters: list[str] = []

    # Speed (atempo can only handle 0.5-2.0 per filter)
    if speed_factor != 1.0:
        remaining = speed_factor
        while remaining > 2.0:
            filters.append("atempo=2.0")
            remaining /= 2.0
        while remaining < 0.5:
            filters.append("atempo=0.5")
            remaining /= 0.5
        if abs(remaining - 1.0) > 0.001:
            filters.append(f"atempo={remaining:.4f}")

    # Loudnorm
    if loudnorm_enabled:
        filters.append(
            f"loudnorm=I={loudnorm_lufs}:TP={loudnorm_true_peak_db}:LRA=11"
        )

    return ",".join(filters) if filters else ""


# ══════════════════════════════════════════════════════════════════════════
# [C2] Caption / Subtitle support
# ══════════════════════════════════════════════════════════════════════════

def _format_srt_time(seconds: float) -> str:
    """Format seconds to SRT timestamp: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


_MAX_SUB_DURATION = 5.0   # Max seconds per subtitle entry
_MAX_SUB_CHARS = 70       # Max characters per subtitle entry (2 lines x 35)
_READING_WPS = 2.5        # Words per second (150 wpm)
_MIN_DISPLAY = 1.5        # Minimum display time per sub


def _split_long_segment(
    text: str,
    t_start: float,
    t_end: float,
    max_dur: float = _MAX_SUB_DURATION,
    max_chars: int = _MAX_SUB_CHARS,
) -> list[tuple[float, float, str]]:
    """
    Split 1 transcript segment dai thanh nhieu subtitle entries ngan hon.

    Strategy:
    1. Split text theo sentence boundaries (. ! ? ;), roi comma
    2. Tinh display_time cho moi sentence dua tren reading speed
       (words / 2.5 wps, min 1.5s, max 5s)
    3. Phan bo cac sentence deu trong khoang [t_start, t_end]
       Moi sub chi hien thi dung display_time, KHONG dan het slot duration
       => Sub hien, mat, hien, mat — tu nhien nhu karaoke

    Returns: list of (start, end, text) tuples
    """
    import re

    duration = t_end - t_start
    text = text.strip()

    if not text:
        return [(t_start, t_end, text)]
    if duration <= max_dur and len(text) <= max_chars:
        return [(t_start, t_end, text)]

    # Step 1: Split by sentence boundaries
    sentences = re.split(r'(?<=[.!?;])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # Step 2: Split long sentences by comma
    expanded = []
    for s in sentences:
        if len(s) > max_chars:
            parts = re.split(r',\s*', s)
            expanded.extend(p.strip() for p in parts if p.strip())
        else:
            expanded.append(s)
    sentences = expanded if expanded else sentences

    # Step 3: Merge very short adjacent fragments to avoid 1-word subs
    merged = []
    buf = ""
    for s in sentences:
        candidate = f"{buf} {s}".strip() if buf else s
        if len(candidate.split()) <= 8 and len(candidate) <= max_chars:
            buf = candidate
        else:
            if buf:
                merged.append(buf)
            buf = s
    if buf:
        merged.append(buf)
    sentences = merged if merged else sentences

    if not sentences:
        return [(t_start, t_end, text)]

    # Step 4: Compute display time per sentence + position evenly
    n = len(sentences)
    slot_duration = duration / n  # Thoi gian moi slot

    result = []
    for i, sent in enumerate(sentences):
        word_count = len(sent.split())
        # Display = reading time, capped
        display = max(_MIN_DISPLAY, min(max_dur, word_count / _READING_WPS + 0.5))
        display = min(display, slot_duration)  # Khong vuot qua slot

        sub_start = t_start + i * slot_duration
        sub_end = min(sub_start + display, t_end)

        if sub_end - sub_start >= 0.3:
            result.append((sub_start, sub_end, sent))

    return result if result else [(t_start, t_end, text)]


def generate_srt(
    segments: list,
    clip_start: float,
    clip_end: float,
    output_path: Path,
    max_chars_per_line: int = 35,
) -> Path:
    """
    [C2] Tao file SRT tu transcript segments.

    Segments la list cua TranscriptSegment (co .start, .end, .text).
    Thoi gian duoc offset ve 0 (tuong doi voi clip_start).
    Chi giu segments nam trong [clip_start, clip_end].
    [Phase4] Segments dai (>5s) duoc split thanh nhieu entries ngan.

    Args:
        segments: TranscriptSegment list (tu analysis)
        clip_start: Thoi gian bat dau clip trong video goc (seconds)
        clip_end: Thoi gian ket thuc clip trong video goc (seconds)
        output_path: Duong dan file SRT output
        max_chars_per_line: So ky tu toi da moi dong

    Returns:
        Path to SRT file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    srt_entries: list[str] = []
    idx = 0

    for seg in segments:
        seg_start = getattr(seg, "start", 0.0)
        seg_end = getattr(seg, "end", 0.0)
        seg_text = getattr(seg, "text", "").strip()

        if not seg_text:
            continue

        # Chi lay segments overlap voi clip range
        if seg_end <= clip_start or seg_start >= clip_end:
            continue

        # Clamp vao clip range
        t_start = max(seg_start, clip_start) - clip_start
        t_end = min(seg_end, clip_end) - clip_start

        if t_end - t_start < 0.1:
            continue

        # [Phase4] Split segments dai thanh nhieu sub entries ngan
        sub_entries = _split_long_segment(
            seg_text, t_start, t_end,
            max_dur=_MAX_SUB_DURATION,
            max_chars=max_chars_per_line * 2,  # 2 lines
        )

        for sub_start, sub_end, sub_text in sub_entries:
            # Word wrap for display
            text = sub_text
            if len(text) > max_chars_per_line:
                words = text.split()
                lines = []
                current_line = ""
                for word in words:
                    if current_line and len(current_line) + 1 + len(word) > max_chars_per_line:
                        lines.append(current_line)
                        current_line = word
                    else:
                        current_line = f"{current_line} {word}".strip()
                if current_line:
                    lines.append(current_line)
                text = "\n".join(lines)

            idx += 1
            srt_entries.append(
                f"{idx}\n"
                f"{_format_srt_time(sub_start)} --> {_format_srt_time(sub_end)}\n"
                f"{text}\n"
            )

    output_path.write_text("\n".join(srt_entries), encoding="utf-8")
    logger.info("Generated SRT: %d entries -> %s", idx, output_path.name)
    return output_path


def build_subtitle_filter(
    srt_path: Path,
    font_family: str = "Inter",
    font_size: int = 48,
    font_color: str = "#FFFFFF",
    outline_color: str = "#000000",
    outline_width: int = 2,
    position: str = "bottom",
    shadow_enabled: bool = True,
    target_width: int = 1080,
    target_height: int = 1920,
) -> str:
    """
    [C2] Build FFmpeg subtitles filter tu SRT file va style config.

    [Phase4] Font size duoc scale theo actual resolution.
    FFmpeg subtitles filter mac dinh dung PlayResY=384 de scale font.
    De font dung kich thuoc mong muon, ta set original_size (PlayResY)
    sao cho font_size tuong ung voi kich thuoc thuc te tren video.

    Returns: filter string cho -vf, vi du:
      "subtitles='path.srt':force_style='FontName=Inter,FontSize=18,...'"
    """
    # Escape path cho FFmpeg filter (Windows backslash -> forward slash, escape colon)
    srt_str = str(srt_path).replace("\\", "/").replace(":", "\\:")

    # Build ASS style — FFmpeg subtitles filter dung ASS format
    # Color format ASS: &HBBGGRR& (BGR, not RGB)
    def _hex_to_ass_color(hex_color: str) -> str:
        """Convert #RRGGBB to &HBBGGRR& ASS format."""
        hex_color = (hex_color or "#FFFFFF").lstrip("#")
        if len(hex_color) == 8:
            a, r, g, b = hex_color[:2], hex_color[2:4], hex_color[4:6], hex_color[6:8]
            return f"&H{a}{b}{g}{r}&"
        elif len(hex_color) == 6:
            r, g, b = hex_color[:2], hex_color[2:4], hex_color[4:6]
            return f"&H00{b}{g}{r}&"
        return "&H00FFFFFF&"

    primary_color = _hex_to_ass_color(font_color)
    outline_clr = _hex_to_ass_color(outline_color)
    shadow_val = "1" if shadow_enabled else "0"

    # [Phase4] Scale font size cho actual resolution
    # FFmpeg subtitles filter dung PlayResY mac dinh = video height de scale
    # font_size=48 tren PlayResY=1920 se hien thi khoang 48px — qua nho
    # font_size=48 tren PlayResY=384 se hien thi khoang 240px — qua to
    # Target: font ~24px tren 1080w portrait (~2.2% of width)
    # Formula: actual_px = font_size * (video_height / PlayResY)
    # Voi PlayResY = target_height: font_size pixel = font_size tren video
    # => Dung original_size de dat PlayResY = target_height
    # Font size mong muon tren video portrait 1080x1920: ~22-26px
    scaled_font_size = max(16, min(28, int(font_size * target_width / 1920)))
    # 48 * 1080 / 1920 = 27 — hop ly cho 1080w portrait
    scaled_outline = max(1, int(outline_width * target_width / 1920) + 1)

    # MarginV: vi tri doc — scale theo resolution
    margin_v = max(20, int(60 * target_height / 1920))
    alignment = 2  # Bottom center
    if position == "top":
        alignment = 8  # Top center
        margin_v = max(15, int(45 * target_height / 1920))
    elif position == "center":
        alignment = 5  # Middle center
        margin_v = 0

    # MarginL/MarginR de text khong sat mep
    margin_side = max(10, int(40 * target_width / 1080))

    style_parts = [
        f"FontName={font_family}",
        f"FontSize={scaled_font_size}",
        f"PrimaryColour={primary_color}",
        f"OutlineColour={outline_clr}",
        f"Outline={scaled_outline}",
        f"Shadow={shadow_val}",
        f"Alignment={alignment}",
        f"MarginV={margin_v}",
        f"MarginL={margin_side}",
        f"MarginR={margin_side}",
        "Bold=1",
    ]
    force_style = ",".join(style_parts)

    # original_size = target_height: FFmpeg se dung PlayResY = target_height
    # => font_size pixel = exactly scaled_font_size pixel tren video output
    return f"subtitles='{srt_str}':force_style='{force_style}':original_size={target_width}x{target_height}"
