"""
Segmenter — re-segment normalized transcript for subtitle display.

Modes:
  - sentence:   Full sentences, up to max_chars_per_line × max_lines.
                 Best for YouTube landscape, cinematic.
  - phrase:     Short phrases, 1-2 lines. Good for Reels / clean look.
  - short_form: 1 line, punchy, fast. Designed for TikTok / Shorts.

Each mode respects SegmentConfig constraints and produces display-ready
subtitle events with line breaks pre-computed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


SegmentMode = Literal["sentence", "phrase", "short_form", "punchline", "word_emphasis"]


@dataclass
class SegmentConfig:
    """Controls how text is chunked and displayed."""
    mode: SegmentMode = "sentence"
    max_chars_per_line: int = 42
    max_lines: int = 2
    min_duration: float = 0.6       # Don't show subtitle shorter than this
    max_duration: float = 7.0       # Force split if longer
    words_per_minute: int = 200     # Reading speed for pacing validation


@dataclass
class SubtitleEvent:
    """Single subtitle display event — ready for ASS/SRT output."""
    start: float
    end: float
    text: str           # Plain text (no line breaks)
    display_text: str   # Text with \N line breaks for ASS
    line_count: int = 1
    scene_id: str = ""
    index: int = 0

    def to_dict(self) -> dict:
        return {
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "text": self.text,
            "display_text": self.display_text,
            "line_count": self.line_count,
            "scene_id": self.scene_id,
            "index": self.index,
        }


# ── Public API ───────────────────────────────────────────────────────────────

def segment(
    normalized: list[dict],
    config: SegmentConfig | None = None,
) -> list[SubtitleEvent]:
    """
    Re-segment normalized transcript into subtitle events.
    Input: output from transcript_normalizer.normalize()
    Output: list of SubtitleEvent ready for ASS/SRT rendering.
    """
    cfg = config or SegmentConfig()

    if cfg.mode == "sentence":
        events = _segment_sentence(normalized, cfg)
    elif cfg.mode == "phrase":
        events = _segment_phrase(normalized, cfg)
    elif cfg.mode == "short_form":
        events = _segment_short_form(normalized, cfg)
    elif cfg.mode == "punchline":
        events = _segment_punchline(normalized, cfg)
    elif cfg.mode == "word_emphasis":
        events = _segment_word_emphasis(normalized, cfg)
    else:
        events = _segment_sentence(normalized, cfg)

    events = _enforce_duration(events, cfg)
    events = _apply_line_breaks(events, cfg)
    events = _reindex(events)

    return events


# ── Mode: Sentence ───────────────────────────────────────────────────────────

def _segment_sentence(
    segments: list[dict],
    cfg: SegmentConfig,
) -> list[SubtitleEvent]:
    """
    Group segments into full sentences.
    A sentence boundary is detected by ending punctuation (.!?).
    Multiple short segments merge into one event until sentence ends
    or max_chars is reached.
    """
    max_chars = cfg.max_chars_per_line * cfg.max_lines
    events: list[SubtitleEvent] = []
    buffer_text = ""
    buffer_start: float | None = None
    buffer_end: float = 0
    buffer_scene = ""

    for seg in segments:
        text = seg["text"]
        start = seg["start"]
        end = seg["end"]

        if buffer_start is None:
            buffer_start = start
            buffer_scene = seg.get("scene_id", "")

        candidate = f"{buffer_text} {text}".strip() if buffer_text else text
        buffer_end = end

        if len(candidate) > max_chars:
            # Flush current buffer first
            if buffer_text:
                events.append(SubtitleEvent(
                    start=buffer_start, end=start,
                    text=buffer_text, display_text=buffer_text,
                    scene_id=buffer_scene,
                ))
            buffer_text = text
            buffer_start = start
            buffer_scene = seg.get("scene_id", "")
        else:
            buffer_text = candidate

        # Check if sentence ends
        if _ends_sentence(text):
            events.append(SubtitleEvent(
                start=buffer_start, end=buffer_end,
                text=buffer_text, display_text=buffer_text,
                scene_id=buffer_scene,
            ))
            buffer_text = ""
            buffer_start = None

    # Flush remaining
    if buffer_text and buffer_start is not None:
        events.append(SubtitleEvent(
            start=buffer_start, end=buffer_end,
            text=buffer_text, display_text=buffer_text,
            scene_id=buffer_scene,
        ))

    return events


# ── Mode: Phrase ─────────────────────────────────────────────────────────────

def _segment_phrase(
    segments: list[dict],
    cfg: SegmentConfig,
) -> list[SubtitleEvent]:
    """
    Keep each segment roughly as-is but merge very short ones
    and split at comma/clause boundaries if too long.
    Target: 1-2 short lines per event.
    """
    max_chars = cfg.max_chars_per_line * cfg.max_lines
    events: list[SubtitleEvent] = []

    for seg in segments:
        text = seg["text"]
        start = seg["start"]
        end = seg["end"]

        if len(text) <= max_chars:
            events.append(SubtitleEvent(
                start=start, end=end,
                text=text, display_text=text,
                scene_id=seg.get("scene_id", ""),
            ))
        else:
            # Split at clause boundary
            parts = _split_at_clauses(text, cfg.max_chars_per_line)
            dur = end - start
            total_chars = len(text)

            offset = start
            for part in parts:
                ratio = len(part) / total_chars
                part_dur = dur * ratio
                events.append(SubtitleEvent(
                    start=round(offset, 3),
                    end=round(offset + part_dur, 3),
                    text=part, display_text=part,
                    scene_id=seg.get("scene_id", ""),
                ))
                offset += part_dur

    return events


# ── Mode: Short-form ─────────────────────────────────────────────────────────

def _segment_short_form(
    segments: list[dict],
    cfg: SegmentConfig,
) -> list[SubtitleEvent]:
    """
    TikTok/Shorts style — 1 line, punchy, max ~25 chars.
    Split aggressively at every natural pause.
    """
    short_max = min(cfg.max_chars_per_line, 30)
    events: list[SubtitleEvent] = []

    for seg in segments:
        text = seg["text"]
        start = seg["start"]
        end = seg["end"]
        dur = end - start

        words = text.split()
        if not words:
            continue

        # Build chunks of ~short_max chars
        chunks: list[str] = []
        current_chunk: list[str] = []
        current_len = 0

        for word in words:
            new_len = current_len + len(word) + (1 if current_chunk else 0)
            if new_len > short_max and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_len = len(word)
            else:
                current_chunk.append(word)
                current_len = new_len

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        # Distribute time proportionally
        total_chars = sum(len(c) for c in chunks)
        offset = start
        for chunk in chunks:
            ratio = len(chunk) / total_chars if total_chars else 1
            chunk_dur = max(dur * ratio, 0.3)
            events.append(SubtitleEvent(
                start=round(offset, 3),
                end=round(offset + chunk_dur, 3),
                text=chunk, display_text=chunk,
                scene_id=seg.get("scene_id", ""),
            ))
            offset += chunk_dur

    return events


# ── Mode: Punchline ──────────────────────────────────────────────────────

def _segment_punchline(
    segments: list[dict],
    cfg: SegmentConfig,
) -> list[SubtitleEvent]:
    """
    Punchline style — 1-3 words per event, punchy impact.
    Each chunk appears as a dramatic reveal, great for hooks & emphasis.
    Splits at 2-4 words per event for maximum visual punch.
    """
    target_words = 3  # words per punchline event
    events: list[SubtitleEvent] = []

    for seg in segments:
        text = seg["text"]
        start = seg["start"]
        end = seg["end"]
        dur = end - start

        words = text.split()
        if not words:
            continue

        # Build chunks of ~target_words
        chunks: list[str] = []
        for i in range(0, len(words), target_words):
            chunk = " ".join(words[i:i + target_words])
            chunks.append(chunk)

        # Distribute time proportionally by character count
        total_chars = sum(len(c) for c in chunks)
        offset = start
        for chunk in chunks:
            ratio = len(chunk) / total_chars if total_chars else 1
            chunk_dur = max(dur * ratio, 0.25)
            events.append(SubtitleEvent(
                start=round(offset, 3),
                end=round(offset + chunk_dur, 3),
                text=chunk, display_text=chunk,
                scene_id=seg.get("scene_id", ""),
            ))
            offset += chunk_dur

    return events


# ── Mode: Word Emphasis ──────────────────────────────────────────────────

def _segment_word_emphasis(
    segments: list[dict],
    cfg: SegmentConfig,
) -> list[SubtitleEvent]:
    """
    Word-by-word emphasis — each word gets its own subtitle event.
    Creates a typing/reveal effect. Best for music lyrics, dramatic reads.
    """
    events: list[SubtitleEvent] = []

    for seg in segments:
        text = seg["text"]
        start = seg["start"]
        end = seg["end"]
        dur = end - start

        words = text.split()
        if not words:
            continue

        # Equal duration per word
        per_word = dur / len(words)
        # Minimum display time per word
        min_per = max(per_word, 0.15)

        offset = start
        for word in words:
            word_dur = min_per
            events.append(SubtitleEvent(
                start=round(offset, 3),
                end=round(min(offset + word_dur, end), 3),
                text=word, display_text=word,
                scene_id=seg.get("scene_id", ""),
            ))
            offset += word_dur

    return events


# ── Post-processing ──────────────────────────────────────────────────────────

def _enforce_duration(
    events: list[SubtitleEvent],
    cfg: SegmentConfig,
) -> list[SubtitleEvent]:
    """Clamp event durations to min/max bounds."""
    result: list[SubtitleEvent] = []

    for i, ev in enumerate(events):
        dur = ev.end - ev.start

        # Skip events that are too short to read
        if dur < cfg.min_duration * 0.5:
            # Merge into previous if possible
            if result:
                prev = result[-1]
                prev.end = ev.end
                prev.text = f"{prev.text} {ev.text}".strip()
                prev.display_text = prev.text
                continue

        # Extend very short events
        if dur < cfg.min_duration:
            ev.end = round(ev.start + cfg.min_duration, 3)
            # Don't overlap with next event
            if i + 1 < len(events) and ev.end > events[i + 1].start:
                ev.end = events[i + 1].start

        result.append(ev)

    return result


def _apply_line_breaks(
    events: list[SubtitleEvent],
    cfg: SegmentConfig,
) -> list[SubtitleEvent]:
    """Insert line breaks (\\N) for multi-line display in ASS."""
    for ev in events:
        lines = wrap_lines(ev.text, cfg.max_chars_per_line, cfg.max_lines)
        ev.display_text = "\\N".join(lines)
        ev.line_count = len(lines)
    return events


def _wrap_text(text: str, max_chars: int, max_lines: int) -> list[str]:
    """
    Word-wrap text into lines of max_chars.
    Uses balanced wrapping — distributes words evenly across lines
    to avoid a long first line and a very short second line.
    """
    if len(text) <= max_chars:
        return [text]

    words = text.split()
    if not words:
        return [text]

    # For 2-line wrapping, try balanced split first
    if max_lines == 2:
        balanced = _balanced_two_line_wrap(words, max_chars)
        if balanced:
            return balanced

    # Fallback: greedy wrap
    lines: list[str] = []
    current_line: list[str] = []
    current_len = 0

    for i, word in enumerate(words):
        new_len = current_len + len(word) + (1 if current_line else 0)

        if new_len > max_chars and current_line:
            lines.append(" ".join(current_line))
            if len(lines) >= max_lines - 1:
                # Last line gets all remaining words
                lines.append(" ".join(words[i:]))
                return lines[:max_lines]
            current_line = [word]
            current_len = len(word)
        else:
            current_line.append(word)
            current_len = new_len

    if current_line:
        lines.append(" ".join(current_line))

    return lines[:max_lines]


# ── CJK-aware wrapping ──────────────────────────────────────────────────────
#
# `_wrap_text` splits on spaces only. Chinese/Japanese text has no spaces, so a
# whole Han sentence came out as ONE line of any length (measured 22/09 with a
# 30-character Douyin line: 1 line, no break). `wrap_lines` keeps `_wrap_text`
# byte-for-byte for space-separated text and adds a width-aware path when the
# text contains East Asian Wide/Fullwidth characters.

#: Characters that must not START a line (basic kinsoku). Splitting before
#: them leaves a comma or closing bracket alone at the head of line 2.
_NO_LINE_START = set("，。！？、；：）」』】》〉,.!?;:)]}…”’")


def is_wide(ch: str) -> bool:
    """True for East Asian Wide/Fullwidth characters (Han, kana, fullwidth)."""
    import unicodedata
    return unicodedata.east_asian_width(ch) in ("W", "F")


def has_wide(text: str) -> bool:
    return any(is_wide(c) for c in text or "")


def display_width(text: str) -> int:
    """Columns: a wide character counts 2, anything else 1."""
    return sum(2 if is_wide(c) else 1 for c in text or "")


def split_units(text: str) -> list[tuple[str, bool]]:
    """Wrap units: every wide char is its own unit; other runs split on spaces.

    Returns `(unit, space_before)` pairs so a line can be re-joined exactly
    (no space is invented between two Han characters, none is lost between two
    Latin words).
    """
    units: list[tuple[str, bool]] = []
    buf, buf_space, pending_space = "", False, False
    for ch in text or "":
        if ch.isspace():
            if buf:
                units.append((buf, buf_space))
                buf = ""
            pending_space = bool(units)
            continue
        if is_wide(ch):
            if buf:
                units.append((buf, buf_space))
                buf = ""
                pending_space = False
            units.append((ch, pending_space))
            pending_space = False
            continue
        if not buf:
            buf_space, pending_space = pending_space, False
        buf += ch
    if buf:
        units.append((buf, buf_space))
    return units


def _join_units(units: list[tuple[str, bool]]) -> str:
    if not units:
        return ""
    return units[0][0] + "".join((" " if sp else "") + u for u, sp in units[1:])


def wrap_lines(text: str, max_chars: int = 42, max_lines: int = 2) -> list[str]:
    """Public line wrapper, CJK-aware. `max_chars` is in Latin columns.

    Space-separated text goes through `_wrap_text` unchanged. Text with wide
    characters is measured with `display_width` (a Han character = 2 columns)
    and may break between any two units except before `_NO_LINE_START`.
    Like `_wrap_text`, the last allowed line takes whatever remains.
    """
    if not has_wide(text):
        return _wrap_text(text, max_chars, max_lines)
    units = split_units(text)
    if not units:
        return [text]
    whole = _join_units(units)
    if display_width(whole) <= max_chars or len(units) == 1:
        return [whole]
    ok = [i for i in range(1, len(units)) if units[i][0][0] not in _NO_LINE_START]

    if max_lines == 2:
        best: tuple[int, str, str] | None = None
        for i in ok:
            a, b = _join_units(units[:i]), _join_units(units[i:])
            wa, wb = display_width(a), display_width(b)
            if wa <= max_chars and wb <= max_chars and (best is None or abs(wa - wb) < best[0]):
                best = (abs(wa - wb), a, b)
        if best:
            return [best[1], best[2]]

    lines: list[str] = []
    start = 0
    for i in range(1, len(units)):
        if i in ok and display_width(_join_units(units[start:i + 1])) > max_chars:
            lines.append(_join_units(units[start:i]))
            start = i
            if len(lines) >= max_lines - 1:
                break
    lines.append(_join_units(units[start:]))
    return lines[:max_lines]


def _balanced_two_line_wrap(words: list[str], max_chars: int) -> list[str] | None:
    """
    Find the split point that minimizes the difference between
    line lengths, while keeping both lines under max_chars.
    Returns None if no valid split found.
    """
    total = " ".join(words)
    if len(total) <= max_chars:
        return [total]

    best_split = -1
    best_diff = len(total)

    # Try each possible split point
    for i in range(1, len(words)):
        line1 = " ".join(words[:i])
        line2 = " ".join(words[i:])

        # Both lines must fit
        if len(line1) > max_chars or len(line2) > max_chars:
            continue

        diff = abs(len(line1) - len(line2))
        if diff < best_diff:
            best_diff = diff
            best_split = i

    if best_split < 0:
        return None

    return [" ".join(words[:best_split]), " ".join(words[best_split:])]


def _reindex(events: list[SubtitleEvent]) -> list[SubtitleEvent]:
    for i, ev in enumerate(events, start=1):
        ev.index = i
    return events


# ── Helpers ──────────────────────────────────────────────────────────────────

# Detect sentence end: . ! ? and Vietnamese-style ellipsis …
_SENTENCE_END_RE = re.compile(r"[.!?…]['\"]?\s*$")


def _ends_sentence(text: str) -> bool:
    """Check if text ends with sentence-ending punctuation."""
    return bool(_SENTENCE_END_RE.search(text.strip()))


_CLAUSE_SPLIT_RE = re.compile(
    r"(,\s+|;\s+|:\s+|\s+and\s+|\s+but\s+|\s+while\s+"
    r"|\s+và\s+|\s+nhưng\s+|\s+khi\s+|\s+hoặc\s+|\s+hay\s+"
    r"|\s+nên\s+|\s+vì\s+|\s+do\s+|\s+mà\s+|\s+rồi\s+|\s+thì\s+)",
    re.IGNORECASE,
)


def _split_at_clauses(text: str, max_per_line: int) -> list[str]:
    """Split text at clause boundaries, keeping each part under max_per_line."""
    parts = _CLAUSE_SPLIT_RE.split(text)

    # Re-join split delimiters with their preceding part
    merged: list[str] = []
    for part in parts:
        if not part.strip():
            continue
        if merged and len(merged[-1]) + len(part) <= max_per_line:
            merged[-1] += part
        else:
            merged.append(part.strip())

    return merged if merged else [text]
