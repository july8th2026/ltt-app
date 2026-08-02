"""
Transcript normalizer — clean and prepare raw transcript for subtitle rendering.

Pipeline (applied in order):
  1. Filter out non-speech segments (silence, B-ROLL markers)
  2. Normalize text (whitespace, punctuation, brackets)
  3. Fix overlapping timestamps
  4. Merge segments that are too short (< min_duration)
  5. Split segments that are too long (> max_duration)
  6. Re-index sequentially
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class NormConfig:
    """Normalizer configuration."""
    min_duration: float = 0.8       # Merge segments shorter than this (seconds)
    max_duration: float = 8.0       # Split segments longer than this (seconds)
    gap_threshold: float = 0.05     # Overlap tolerance (seconds)
    strip_brackets: bool = True     # Remove [B-ROLL], [MUSIC], etc.
    collapse_whitespace: bool = True


@dataclass
class Segment:
    """Internal segment representation."""
    start: float
    end: float
    text: str
    scene_id: str = ""
    index: int = 0

    @property
    def duration(self) -> float:
        return self.end - self.start

    def to_dict(self) -> dict:
        return {
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "text": self.text,
            "scene_id": self.scene_id,
            "index": self.index,
        }


# ── Public API ───────────────────────────────────────────────────────────────

def normalize(
    raw_segments: list[dict],
    config: Optional[NormConfig] = None,
) -> list[dict]:
    """
    Full normalization pipeline.
    Input: raw transcript JSON array.
    Output: cleaned, re-indexed list of segment dicts.
    """
    cfg = config or NormConfig()

    segments = _parse_raw(raw_segments)
    segments = _filter_non_speech(segments, strip_brackets=cfg.strip_brackets)
    segments = _normalize_text(segments, collapse_ws=cfg.collapse_whitespace)
    segments = _fix_overlaps(segments, gap_threshold=cfg.gap_threshold)
    segments = _merge_short(segments, min_dur=cfg.min_duration)
    segments = _split_long(segments, max_dur=cfg.max_duration)
    segments = _reindex(segments)

    return [s.to_dict() for s in segments]


# ── Step 1: Parse raw input ──────────────────────────────────────────────────

def _parse_raw(raw: list[dict]) -> list[Segment]:
    """Convert raw dicts to Segment objects, sorted by start time.
    Filters out silence/B-ROLL segments by type field.
    """
    result: list[Segment] = []
    for item in raw:
        start = float(item.get("start", 0))
        end = float(item.get("end", 0))
        text = str(item.get("text", ""))
        seg_type = str(item.get("type", "speech")).lower().strip()

        if end <= start:
            continue

        # Skip silence segments (B-ROLL, transitions, pauses)
        if seg_type == "silence":
            continue

        result.append(Segment(
            start=start,
            end=end,
            text=text,
            scene_id=item.get("scene_id", ""),
            index=item.get("index", 0),
        ))

    result.sort(key=lambda s: s.start)
    return result


# ── Step 2: Filter non-speech ────────────────────────────────────────────────

_BRACKET_RE = re.compile(r"\[.*?\]")


def _filter_non_speech(
    segments: list[Segment],
    strip_brackets: bool = True,
) -> list[Segment]:
    """Remove silence segments and bracket annotations."""
    result: list[Segment] = []
    for seg in segments:
        text = seg.text.strip()

        # Skip if entire text is a bracket annotation like [B-ROLL: TRANSITION]
        if _BRACKET_RE.fullmatch(text):
            continue

        # Optionally strip inline bracket tags
        if strip_brackets:
            text = _BRACKET_RE.sub("", text).strip()

        if not text:
            continue

        seg.text = text
        result.append(seg)

    return result


# ── Step 3: Normalize text ───────────────────────────────────────────────────

_MULTI_SPACE_RE = re.compile(r"[ \t]+")
# Fix dash artifacts within words from ASR (e.g. "T -Rex" → "T-Rex", "T - Rex" → "T-Rex")
# Only match when both sides are single characters (not full words like "Xin chào - Tạm biệt")
# Pattern: single non-space char + optional space + dash + optional space + single uppercase/char
_DASH_ARTIFACT_RE = re.compile(r"(?<=\b\w)\s+-\s*(?=\w)")  # "T -Rex" or "T - Rex"


def _normalize_text(
    segments: list[Segment],
    collapse_ws: bool = True,
) -> list[Segment]:
    """Clean up whitespace, fix common OCR/ASR artifacts."""
    for seg in segments:
        text = seg.text

        # Collapse multiple spaces/tabs
        if collapse_ws:
            text = _MULTI_SPACE_RE.sub(" ", text)

        # Fix " -Rex" / " - Rex" dash artifacts from speech-to-text
        text = _DASH_ARTIFACT_RE.sub("-", text)

        # Strip leading/trailing whitespace
        text = text.strip()

        # Ensure text doesn't start with lowercase after sentence-ending previous seg
        seg.text = text

    return segments


# ── Step 4: Fix overlapping timestamps ───────────────────────────────────────

def _fix_overlaps(
    segments: list[Segment],
    gap_threshold: float = 0.05,
) -> list[Segment]:
    """
    Fix overlapping timestamps between consecutive segments.
    If segment[i].end > segment[i+1].start, set end = next.start.
    """
    for i in range(len(segments) - 1):
        curr = segments[i]
        nxt = segments[i + 1]

        if curr.end > nxt.start + gap_threshold:
            # Overlap detected — clamp current end to next start
            curr.end = nxt.start

        # Ensure minimum duration after clamping, but don't overlap next segment
        if curr.end <= curr.start:
            curr.end = min(curr.start + 0.1, nxt.start)
            # If still invalid (start == nxt.start), set minimal gap
            if curr.end <= curr.start:
                curr.end = curr.start + 0.01

    return segments


# ── Step 5: Merge short segments ─────────────────────────────────────────────

def _merge_short(
    segments: list[Segment],
    min_dur: float = 0.8,
) -> list[Segment]:
    """
    Merge segments shorter than min_dur into the next segment.
    Preserves timing continuity.
    """
    if not segments:
        return segments

    result: list[Segment] = []
    pending: Optional[Segment] = None

    for seg in segments:
        if pending is None:
            pending = seg
            continue

        if pending.duration < min_dur:
            # Merge pending into current segment
            pending = Segment(
                start=pending.start,
                end=seg.end,
                text=f"{pending.text} {seg.text}".strip(),
                scene_id=pending.scene_id,
            )
        else:
            result.append(pending)
            pending = seg

    if pending is not None:
        # If last pending is short, merge with previous
        if pending.duration < min_dur and result:
            last = result[-1]
            result[-1] = Segment(
                start=last.start,
                end=pending.end,
                text=f"{last.text} {pending.text}".strip(),
                scene_id=last.scene_id,
            )
        else:
            result.append(pending)

    return result


# ── Step 6: Split long segments ──────────────────────────────────────────────

def _split_long(
    segments: list[Segment],
    max_dur: float = 8.0,
) -> list[Segment]:
    """
    Split segments longer than max_dur at natural break points.
    Uses punctuation and conjunctions as split candidates.
    Falls back to midpoint split if no natural break found.
    """
    result: list[Segment] = []

    for seg in segments:
        if seg.duration <= max_dur:
            result.append(seg)
            continue

        parts = _split_at_natural_break(seg, max_dur)
        result.extend(parts)

    return result


# Split priority: sentence boundary > comma/semicolon > midpoint
_SENTENCE_BREAK_RE = re.compile(r"(?<=[.!?])\s+")
_CLAUSE_BREAK_RE = re.compile(r"(?<=[,;:])\s+")


def _split_at_natural_break(seg: Segment, max_dur: float) -> list[Segment]:
    """Recursively split a segment at natural text boundaries."""
    if seg.duration <= max_dur:
        return [seg]

    text = seg.text
    total_dur = seg.duration

    # Try sentence break first, then clause break
    for pattern in (_SENTENCE_BREAK_RE, _CLAUSE_BREAK_RE):
        split_pos = _find_best_split(text, pattern)
        if split_pos is not None:
            left_text = text[:split_pos].strip()
            right_text = text[split_pos:].strip()

            if left_text and right_text:
                ratio = len(left_text) / len(text)
                mid_time = seg.start + total_dur * ratio

                left = Segment(start=seg.start, end=round(mid_time, 3),
                               text=left_text, scene_id=seg.scene_id)
                right = Segment(start=round(mid_time, 3), end=seg.end,
                                text=right_text, scene_id=seg.scene_id)

                # Recurse in case halves are still too long
                return _split_at_natural_break(left, max_dur) + \
                       _split_at_natural_break(right, max_dur)

    # Fallback: split at word boundary nearest to midpoint
    mid_char = len(text) // 2
    space_pos = text.rfind(" ", 0, mid_char + 10)
    if space_pos <= 0:
        space_pos = text.find(" ", mid_char)
    if space_pos <= 0:
        # No space at all — can't split further
        return [seg]

    left_text = text[:space_pos].strip()
    right_text = text[space_pos:].strip()
    ratio = len(left_text) / len(text)
    mid_time = seg.start + total_dur * ratio

    left = Segment(start=seg.start, end=round(mid_time, 3),
                   text=left_text, scene_id=seg.scene_id)
    right = Segment(start=round(mid_time, 3), end=seg.end,
                    text=right_text, scene_id=seg.scene_id)

    return _split_at_natural_break(left, max_dur) + \
           _split_at_natural_break(right, max_dur)


def _find_best_split(text: str, pattern: re.Pattern) -> Optional[int]:
    """Find the split position closest to the midpoint of text."""
    mid = len(text) // 2
    best_pos: Optional[int] = None
    best_dist = len(text)

    for match in pattern.finditer(text):
        pos = match.start()
        # Don't split too close to edges (< 20% from either side)
        if pos < len(text) * 0.2 or pos > len(text) * 0.8:
            continue
        dist = abs(pos - mid)
        if dist < best_dist:
            best_dist = dist
            best_pos = match.end()  # split AFTER the punctuation + space

    return best_pos


# ── Step 7: Re-index ─────────────────────────────────────────────────────────

def _reindex(segments: list[Segment]) -> list[Segment]:
    """Assign sequential 1-based index to all segments."""
    for i, seg in enumerate(segments, start=1):
        seg.index = i
    return segments
