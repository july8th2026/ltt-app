"""Caption/subtitle renderer — ASS generation with word-level chunking.

Features:
- Word-level subtitle chunks (2-4 seconds each, NOT full segments)
- Line-breaking at natural word boundaries (Vietnamese + English)
- Keyword highlighting via ASS inline override tags
- Safe area margins (avoids UI-occluded zones on mobile)
- Language-aware timing compensation
- Genre-aware emphasis via keyword categories

ASS format reference:
- Colors: &HAABBGGRR (alpha, blue, green, red)
- Inline tags: {\\c&HBBGGRR&} = primary color, {\\b1} = bold
- Alignment: numpad layout (2=bottom-center, 5=mid-center, 8=top-center)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from cutclipshort.types import CaptionStyle, TranscriptSegment

logger = logging.getLogger(__name__)

# ── Safe area ratios (percentage-based, works for ALL resolutions) ────
# Top 15% and bottom 12% are often occluded by platform UI
_SAFE_TOP_RATIO = 0.15
_SAFE_BOTTOM_RATIO = 0.12
_SAFE_SIDE_RATIO = 0.055

# ── Reference design: 1080x1920 (9:16 portrait) ─────────────────────
_REF_WIDTH = 1080
_REF_HEIGHT = 1920

# ── Subtitle chunk parameters ────────────────────────────────────────
_CHUNK_MAX_DURATION_SEC = 3.5   # Max duration for one subtitle chunk
_CHUNK_MIN_DURATION_SEC = 0.8   # Min duration (avoid flash subtitles)
_CHUNK_TARGET_WORDS = 6         # Target words per chunk (readable pace)
_CHUNK_MAX_WORDS = 10           # Absolute max words per chunk
_CHUNK_MIN_WORDS = 2            # Min words (avoid single-word subs)


@dataclass
class _SubtitleChunk:
    """A single subtitle display unit (2-4 seconds of text)."""
    start: float
    end: float
    text: str


def _compute_responsive_params(
    style: CaptionStyle,
    target_width: int,
    target_height: int,
) -> dict:
    """Compute responsive subtitle parameters for ANY aspect ratio.

    Font size scales by the SHORT SIDE of the frame relative to a 1080px
    reference.  All standard outputs (9:16, 1:1, 16:9) share the same
    1080px short side, so the user-specified font size is preserved 1:1.
    Only non-standard resolutions (720p, 4K, …) trigger actual scaling.

    Chars-per-line scales by WIDTH (determines how many characters fit
    before wrapping).

    Returns dict with: font_size, max_chars_per_line, margin_side, margin_top,
                       margin_bottom, outline_width, play_res_x, play_res_y
    """
    w = max(target_width, 320)
    h = max(target_height, 320)

    # ── Font size: scale by SHORT SIDE (visual consistency) ─────────
    short_side = min(w, h)
    font_scale = short_side / _REF_WIDTH          # _REF_WIDTH = 1080
    font_size = max(24, round(style.font_size * font_scale))

    # ── Chars per line: scale by WIDTH (layout fit) ─────────────────
    char_scale = w / _REF_WIDTH
    max_chars = max(12, round(style.max_chars_per_line * char_scale))

    # ── Margins: percentage-based (unchanged) ───────────────────────
    margin_side = max(20, round(w * _SAFE_SIDE_RATIO))
    margin_top = round(h * _SAFE_TOP_RATIO)
    margin_bottom = round(h * _SAFE_BOTTOM_RATIO)

    # ── Outline scales with font ────────────────────────────────────
    outline_width = max(1, round(style.outline_width * font_scale))

    return {
        "font_size": font_size,
        "max_chars_per_line": max_chars,
        "margin_side": margin_side,
        "margin_top": margin_top,
        "margin_bottom": margin_bottom,
        "outline_width": outline_width,
        "play_res_x": w,
        "play_res_y": h,
    }


# Keyword patterns by category (Vietnamese + English)
KEYWORD_PATTERNS: dict[str, list[str]] = {
    "numbers": [
        r"\b\d+\s*(%|percent|ways|things|tips|reasons|steps|mistakes)\b",
        r"\b(first|second|third|number\s*(one|two|three))\b",
        r"\b#?\d+\b",
        # Vietnamese
        r"\b(thứ\s*(nhất|hai|ba)|số\s*\d+)\b",
    ],
    "questions": [
        r"\b(how|why|what|when|where|who|which)\b",
        r"\?",
        # Vietnamese
        r"\b(tại sao|như thế nào|là gì|ở đâu|khi nào|ai|bao giờ|bao nhiêu|sao lại)\b",
    ],
    "superlatives": [
        r"\b(best|worst|biggest|most|least|never|always|only|every)\b",
        r"\b(amazing|incredible|insane|crazy|shocking|secret|truth)\b",
        # Vietnamese
        r"\b(nhất|tuyệt vời|kinh khủng|điên|sốc|bí mật|sự thật|luôn luôn|không bao giờ)\b",
    ],
}


# ══════════════════════════════════════════════════════════════════════════
# WORD-LEVEL CHUNKING — THE CORE FIX
# ══════════════════════════════════════════════════════════════════════════

def _segment_to_chunks(
    seg: TranscriptSegment,
    max_chars: int,
    language: str = "",
) -> list[_SubtitleChunk]:
    """Split a TranscriptSegment into display-friendly subtitle chunks.

    Strategy:
    1. If segment has word-level timestamps → use them for precise chunks
    2. If no word timestamps → estimate timing by splitting text evenly

    Each chunk: 2-4 seconds, 4-8 words, fits within max_chars per line.
    """
    words = getattr(seg, "words", None) or []

    if words and len(words) >= 2:
        return _chunk_from_words(words, max_chars, language)
    else:
        return _chunk_from_text(seg.start, seg.end, seg.text, max_chars)


def _chunk_from_words(
    words: list,
    max_chars: int,
    language: str = "",
) -> list[_SubtitleChunk]:
    """Create subtitle chunks from word-level timestamps.

    Groups consecutive words into chunks of _CHUNK_TARGET_WORDS,
    respecting natural break points (punctuation, conjunctions).
    """
    if not words:
        return []

    chunks: list[_SubtitleChunk] = []
    current_words: list = []
    current_text_len = 0
    chunk_start: float = 0.0

    for i, w in enumerate(words):
        word_text = w.word.strip() if hasattr(w, "word") else str(getattr(w, "word", ""))
        if not word_text:
            continue

        if not current_words:
            chunk_start = w.start

        current_words.append(w)
        current_text_len += len(word_text) + 1  # +1 for space

        # Decide whether to flush this chunk
        should_flush = False
        word_count = len(current_words)
        chunk_duration = w.end - chunk_start

        # Hard limits — always flush
        if word_count >= _CHUNK_MAX_WORDS:
            should_flush = True
        elif chunk_duration >= _CHUNK_MAX_DURATION_SEC:
            should_flush = True
        elif current_text_len > max_chars * 2:  # Exceeds 2 lines
            should_flush = True

        # Soft limits — flush at natural break points
        elif word_count >= _CHUNK_TARGET_WORDS:
            should_flush = True
        elif word_count >= _CHUNK_MIN_WORDS and chunk_duration >= 1.5:
            # Check for natural break after this word
            if _is_natural_break(word_text, words, i, language):
                should_flush = True

        if should_flush:
            chunk_text = " ".join(
                (cw.word.strip() if hasattr(cw, "word") else str(getattr(cw, "word", "")))
                for cw in current_words
            ).strip()
            if chunk_text:
                chunk_end = current_words[-1].end
                # Extend chunk end to next word's start to eliminate gaps
                if i + 1 < len(words):
                    next_start = words[i + 1].start
                    # Bridge the gap if it's small (< 0.3s)
                    if 0 < next_start - chunk_end < 0.3:
                        chunk_end = next_start
                # Ensure minimum duration
                if chunk_end - chunk_start < _CHUNK_MIN_DURATION_SEC:
                    chunk_end = chunk_start + _CHUNK_MIN_DURATION_SEC
                chunks.append(_SubtitleChunk(
                    start=chunk_start,
                    end=chunk_end,
                    text=chunk_text,
                ))
            current_words = []
            current_text_len = 0

    # Flush remaining words
    if current_words:
        chunk_text = " ".join(
            (cw.word.strip() if hasattr(cw, "word") else str(getattr(cw, "word", "")))
            for cw in current_words
        ).strip()
        if chunk_text:
            chunk_end = current_words[-1].end
            if chunk_end - chunk_start < _CHUNK_MIN_DURATION_SEC:
                chunk_end = chunk_start + _CHUNK_MIN_DURATION_SEC
            # If only 1 word left and previous chunk exists, merge with previous
            if len(current_words) == 1 and chunks:
                prev = chunks[-1]
                chunks[-1] = _SubtitleChunk(
                    start=prev.start,
                    end=chunk_end,
                    text=f"{prev.text} {chunk_text}",
                )
            else:
                chunks.append(_SubtitleChunk(
                    start=chunk_start,
                    end=chunk_end,
                    text=chunk_text,
                ))

    return chunks


def _is_natural_break(
    word_text: str,
    words: list,
    idx: int,
    language: str = "",
) -> bool:
    """Check if this word is a natural break point for subtitles."""
    # After punctuation
    if word_text and word_text[-1] in ",.;:!?…":
        return True

    # Before conjunctions (next word)
    if idx + 1 < len(words):
        next_text = words[idx + 1].word.strip().lower() if hasattr(words[idx + 1], "word") else ""

        # English conjunctions
        en_conjunctions = {"and", "but", "or", "so", "because", "that",
                           "which", "when", "while", "if", "then", "yet"}
        # Vietnamese conjunctions
        vi_conjunctions = {"và", "nhưng", "hoặc", "vì", "nên", "mà",
                           "thì", "nếu", "khi", "để", "hay", "rồi",
                           "còn", "tuy", "dù", "cho"}

        if next_text in en_conjunctions or next_text in vi_conjunctions:
            return True

    return False


def _chunk_from_text(
    start: float,
    end: float,
    text: str,
    max_chars: int,
) -> list[_SubtitleChunk]:
    """Fallback: split text into timed chunks without word timestamps.

    Estimates timing by distributing duration evenly across words.
    """
    text = text.strip()
    if not text:
        return []

    duration = end - start
    words = text.split()

    if not words:
        return []

    # Short segment — single chunk
    if duration <= _CHUNK_MAX_DURATION_SEC or len(words) <= _CHUNK_TARGET_WORDS:
        return [_SubtitleChunk(start=start, end=end, text=text)]

    # Split into groups of _CHUNK_TARGET_WORDS
    chunks: list[_SubtitleChunk] = []
    total_words = len(words)
    time_per_word = duration / total_words

    i = 0
    while i < total_words:
        chunk_word_count = min(_CHUNK_TARGET_WORDS, total_words - i)
        # Try to avoid orphan word at the end
        remaining = total_words - i - chunk_word_count
        if 0 < remaining < _CHUNK_MIN_WORDS:
            chunk_word_count += remaining  # Absorb orphan

        chunk_words = words[i:i + chunk_word_count]
        chunk_start = start + i * time_per_word
        chunk_end = start + (i + chunk_word_count) * time_per_word
        chunk_end = min(chunk_end, end)

        chunks.append(_SubtitleChunk(
            start=chunk_start,
            end=chunk_end,
            text=" ".join(chunk_words),
        ))
        i += chunk_word_count

    return chunks


def generate_ass_file(
    segments: list[TranscriptSegment],
    style: CaptionStyle,
    output_path: Path,
    clip_start_offset: float = 0.0,
    *,
    target_width: int = 1080,
    target_height: int = 1920,
    keyword_categories: tuple[str, ...] = (),
    highlight_color: str | None = None,
    timing_offset_ms: float = 0.0,
    language: str = "",
    speed_factor: float = 1.0,
) -> Path:
    """Generate an ASS subtitle file with word-level chunked subtitles.

    CORE CHANGE: Instead of 1 Dialogue per segment (5-30s static text),
    segments are split into 2-4 second chunks using word timestamps.

    Args:
        segments: Transcript segments with timestamps.
        style: Caption visual styling (base values, will be scaled).
        output_path: Where to write the .ass file.
        clip_start_offset: Subtract from all timestamps (clip-relative).
        target_width: Output frame width in pixels.
        target_height: Output frame height in pixels.
        keyword_categories: Which keyword groups to highlight.
        highlight_color: Override color for keyword highlights (hex).
        timing_offset_ms: Global timing compensation in ms.
        language: Language hint for break points and timing.
        speed_factor: Playback speed (1.5 = 50% faster). Subtitle timestamps
            are divided by this value to stay in sync with sped-up video.

    Returns:
        Path to the generated .ass file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Compute responsive parameters for this aspect ratio
    rp = _compute_responsive_params(style, target_width, target_height)

    # Compute safe area margins based on position
    margin_v = _safe_margin_vertical_responsive(style.position, rp)

    header = _build_ass_header_responsive(style, rp, margin_v)

    # Compute timing offset (language-aware)
    offset_sec = timing_offset_ms / 1000.0
    if offset_sec == 0.0 and language.lower() in ("vi", "vie", "vietnamese"):
        offset_sec = 0.15
        logger.debug("Auto-applied +150ms timing offset for Vietnamese")

    # Speed factor: when video is sped up (e.g. 1.5x), the video timeline
    # is compressed by setpts filter BEFORE the ASS filter runs.
    # So a 10s clip at 1.5x plays in ~6.67s. ASS timestamps must match
    # the compressed timeline: divide by speed_factor.
    spd = max(0.25, speed_factor) if speed_factor != 1.0 else 1.0

    # Phase 1: Collect all timed chunks from all segments
    all_timed: list[tuple[float, float, str]] = []  # (start, end, text)
    total_chunks = 0

    for seg in segments:
        chunks = _segment_to_chunks(seg, rp["max_chars_per_line"], language)
        total_chunks += len(chunks)

        for chunk in chunks:
            start = max(0.0, chunk.start - clip_start_offset - offset_sec)
            end = max(0.0, chunk.end - clip_start_offset - offset_sec)

            # Apply speed compensation
            if spd != 1.0:
                start = start / spd
                end = end / spd

            if end <= start:
                continue

            # Smart line-breaking with responsive char limit
            text = _break_lines(chunk.text, rp["max_chars_per_line"], language)

            # Keyword highlighting
            if keyword_categories:
                hl_color = highlight_color or style.active_word_color
                text = _highlight_keywords(text, keyword_categories, hl_color)

            # ASS line break
            text = text.replace("\n", "\\N")

            all_timed.append((start, end, text))

    # Phase 2: Sort by start time and clamp overlaps between segments
    all_timed.sort(key=lambda x: x[0])
    for i in range(len(all_timed) - 1):
        cur_start, cur_end, cur_text = all_timed[i]
        next_start = all_timed[i + 1][0]
        # If current end overlaps next start, clamp current end
        if cur_end > next_start:
            clamped_end = next_start - 0.02  # 20ms gap to prevent flicker
            if clamped_end > cur_start + 0.3:  # Keep at least 0.3s display
                all_timed[i] = (cur_start, clamped_end, cur_text)
            else:
                # Overlap too severe — keep original but shift next start
                all_timed[i] = (cur_start, cur_end, cur_text)

    # Phase 3: Build ASS dialogue events
    events: list[str] = []
    for start, end, text in all_timed:
        if end <= start:
            continue
        events.append(
            f"Dialogue: 0,{_sec_to_ass_time(start)},{_sec_to_ass_time(end)},Default,,0,0,0,,{text}"
        )

    content = header + "\n".join(events) + "\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    aspect = target_width / target_height
    ar_label = "portrait" if aspect < 0.8 else "landscape" if aspect > 1.2 else "square"
    logger.info(
        "ASS subtitle: %d events from %d segments (%d chunks), "
        "style=%s, %dx%d (%s), font=%dpx, chars/line=%d, lang=%s -> %s",
        len(events), len(segments), total_chunks,
        style.preset_name, target_width, target_height, ar_label,
        rp["font_size"], rp["max_chars_per_line"], language or "unknown",
        output_path.name,
    )
    return output_path


def burn_captions(
    video_path: Path,
    ass_path: Path,
    output_path: Path,
) -> Path:
    """Burn ASS subtitles into video using FFmpeg."""
    from cutclipshort.adapters.ffmpeg import FFmpegAdapter

    ffmpeg = FFmpegAdapter()
    # FFmpeg filter requires forward slashes and escaped colons on Windows
    safe_path = ass_path.as_posix().replace(":", r"\:")
    ass_filter = f"ass='{safe_path}'"

    ffmpeg.encode(
        input_path=video_path,
        output_path=output_path,
        video_filters=ass_filter,
        codec="libx264",
        crf="18",
        preset="medium",
        extra_args=["-c:a", "copy"],
    )

    logger.info("Captions burned into %s", output_path.name)
    return output_path


# ══════════════════════════════════════════════════════════════════════════
# LINE BREAKING
# ══════════════════════════════════════════════════════════════════════════

def _break_lines(text: str, max_chars: int, language: str = "") -> str:
    """Break text into lines at natural word boundaries.

    Rules:
    1. Never exceed max_chars per line
    2. Prefer breaking after punctuation (comma, period, semicolon)
    3. Prefer breaking at conjunctions (Vietnamese + English)
    4. Otherwise break at the nearest word boundary to midpoint
    5. Maximum 2 lines for readability
    """
    text = text.strip()
    if len(text) <= max_chars:
        return text

    words = text.split()
    if len(words) <= 2:
        return text

    # Combined conjunction set (Vietnamese + English)
    _CONJUNCTIONS = {
        # English
        "and", "but", "or", "so", "because", "that", "which", "when", "while", "if",
        # Vietnamese
        "và", "nhưng", "hoặc", "vì", "nên", "mà", "thì", "nếu", "khi", "để",
        "hay", "rồi", "còn", "tuy", "dù", "cho", "với",
    }

    mid = len(text) // 2
    best_pos = -1
    best_score = 999

    pos = 0
    for i, word in enumerate(words[:-1]):
        pos += len(word)
        if i < len(words) - 1:
            candidate_pos = pos + i  # Account for spaces

            score = abs(candidate_pos - mid)

            # Bonus for breaking after punctuation
            if word[-1] in ",.;:!?…":
                score -= 15

            # Bonus for breaking before conjunctions
            next_word = words[i + 1].lower()
            if next_word in _CONJUNCTIONS:
                score -= 10

            if score < best_score:
                best_score = score
                best_pos = candidate_pos

    if best_pos > 0 and best_pos < len(text) - 1:
        line1 = text[:best_pos + 1].rstrip()
        line2 = text[best_pos + 1:].lstrip()

        if len(line1) <= max_chars and len(line2) <= max_chars:
            return f"{line1}\n{line2}"

    # Fallback: break at max_chars word boundary
    line1_words = []
    line1_len = 0
    for w in words:
        if line1_len + len(w) + (1 if line1_words else 0) > max_chars:
            break
        line1_words.append(w)
        line1_len += len(w) + (1 if len(line1_words) > 1 else 0)

    if line1_words and len(line1_words) < len(words):
        line1 = " ".join(line1_words)
        remaining_words = words[len(line1_words):]
        # Truncate line2 to max_chars (avoid overflow)
        line2_words = []
        line2_len = 0
        for w in remaining_words:
            if line2_len + len(w) + (1 if line2_words else 0) > max_chars:
                break
            line2_words.append(w)
            line2_len += len(w) + (1 if len(line2_words) > 1 else 0)
        line2 = " ".join(line2_words) if line2_words else " ".join(remaining_words[:3])
        return f"{line1}\n{line2}"

    return text


# ══════════════════════════════════════════════════════════════════════════
# KEYWORD HIGHLIGHTING
# ══════════════════════════════════════════════════════════════════════════

def _highlight_keywords(
    text: str,
    categories: tuple[str, ...],
    highlight_color: str,
) -> str:
    """Apply ASS inline color tags to matching keywords.

    Wraps matched words in {\\c&HBBGGRR&}{\\b1}word{\\c}{\\b0} tags.
    """
    ass_color = _hex_to_ass_color_inline(highlight_color)

    # Collect all patterns for selected categories
    patterns: list[str] = []
    for cat in categories:
        patterns.extend(KEYWORD_PATTERNS.get(cat, []))

    if not patterns:
        return text

    combined = "|".join(f"({p})" for p in patterns)

    def _replacer(match: re.Match) -> str:
        word = match.group(0)
        return f"{{\\c{ass_color}}}{{\\b1}}{word}{{\\c}}{{\\b0}}"

    return re.sub(combined, _replacer, text, flags=re.IGNORECASE)


def _hex_to_ass_color_inline(hex_color: str) -> str:
    """Convert hex #RRGGBB to ASS inline color &HBBGGRR& format."""
    h = hex_color.lstrip("#")
    if len(h) < 6:
        return "&HFFFFFF&"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"&H{b:02X}{g:02X}{r:02X}&"


# ══════════════════════════════════════════════════════════════════════════
# SAFE AREA
# ══════════════════════════════════════════════════════════════════════════

def _safe_margin_vertical_responsive(position: str, rp: dict) -> int:
    """Compute vertical margin using responsive params."""
    if position == "top":
        return rp["margin_top"]
    elif position == "center":
        return 0  # Center doesn't need margin (numpad alignment 5)
    else:  # bottom
        return rp["margin_bottom"]


# ══════════════════════════════════════════════════════════════════════════
# ASS FILE CONSTRUCTION
# ══════════════════════════════════════════════════════════════════════════

def _build_ass_header_responsive(style: CaptionStyle, rp: dict, margin_v: int = 60) -> str:
    """Build ASS header with RESPONSIVE style — adapts to any aspect ratio."""
    alignment_map = {"top": 8, "center": 5, "bottom": 2}
    alignment = alignment_map.get(style.position, 2)

    primary_color = _hex_to_ass_color(style.font_color)
    outline_color = _hex_to_ass_color(style.outline_color)
    shadow_color = (
        _hex_to_ass_color(style.shadow_color) if style.shadow_enabled
        else "&H00000000"
    )

    # Background box: BorderStyle 3 = opaque box, 1 = outline + shadow
    border_style = 3 if style.bg_box_enabled else 1
    back_colour = _hex_to_ass_color(style.bg_box_color) if style.bg_box_enabled else shadow_color

    # Bold flag: -1 = use font default bold
    bold = -1

    # Use responsive values from _compute_responsive_params
    play_res_x = rp["play_res_x"]
    play_res_y = rp["play_res_y"]
    font_size = rp["font_size"]
    margin_side = rp["margin_side"]
    outline_w = rp["outline_width"]

    return f"""[Script Info]
Title: LTT CUT SHORT Captions
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.font_family},{font_size},{primary_color},&H000000FF,{outline_color},{back_colour},{bold},0,0,0,100,100,0,0,{border_style},{outline_w},{1 if style.shadow_enabled else 0},{alignment},{margin_side},{margin_side},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _sec_to_ass_time(seconds: float) -> str:
    """Convert seconds to ASS time format H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _hex_to_ass_color(hex_color: str) -> str:
    """Convert hex (#RRGGBB or #RRGGBBAA) to ASS &HAABBGGRR format."""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        a = 0
    elif len(h) == 8:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        a = int(h[6:8], 16)
    else:
        return "&H00FFFFFF"
    return f"&H{a:02X}{b:02X}{g:02X}{r:02X}"
