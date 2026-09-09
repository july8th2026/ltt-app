"""
Transcript normalizer — clean and prepare raw transcript for subtitle rendering.

Pipeline (applied in order):
  1. Filter out non-speech segments (silence, B-ROLL markers)
  2. Normalize text (whitespace, punctuation, brackets)
  3. Fix overlapping timestamps
  4. Merge segments that are too short (< min_duration)
  5. Split segments that are too long (> max_duration)
  6. Re-index sequentially

Extracted from BOT GEMINI auto_sub_video/transcript_normalizer.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class NormConfig:
    """Normalizer configuration."""
    min_duration: float = 0.8
    max_duration: float = 8.0
    gap_threshold: float = 0.05
    strip_brackets: bool = True
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
    result: list[Segment] = []
    for item in raw:
        start = float(item.get("start", 0))
        end = float(item.get("end", 0))
        text = str(item.get("text", ""))
        seg_type = str(item.get("type", "speech")).lower().strip()

        if end <= start:
            continue
        if seg_type == "silence":
            continue

        result.append(Segment(
            start=start, end=end, text=text,
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
    result: list[Segment] = []
    for seg in segments:
        text = seg.text.strip()
        if _BRACKET_RE.fullmatch(text):
            continue
        if strip_brackets:
            text = _BRACKET_RE.sub("", text).strip()
        if not text:
            continue
        seg.text = text
        result.append(seg)
    return result


# ── Step 3: Normalize text ───────────────────────────────────────────────────

_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_DASH_ARTIFACT_RE = re.compile(r"(?<=\b\w)\s+-\s*(?=\w)")


def _normalize_text(
    segments: list[Segment],
    collapse_ws: bool = True,
) -> list[Segment]:
    for seg in segments:
        text = seg.text
        if collapse_ws:
            text = _MULTI_SPACE_RE.sub(" ", text)
        text = _DASH_ARTIFACT_RE.sub("-", text)
        text = text.strip()
        seg.text = text
    return segments


# ── Step 4: Fix overlapping timestamps ───────────────────────────────────────

def _fix_overlaps(
    segments: list[Segment],
    gap_threshold: float = 0.05,
) -> list[Segment]:
    for i in range(len(segments) - 1):
        curr = segments[i]
        nxt = segments[i + 1]
        if curr.end > nxt.start + gap_threshold:
            curr.end = nxt.start
        if curr.end <= curr.start:
            curr.end = min(curr.start + 0.1, nxt.start)
            if curr.end <= curr.start:
                curr.end = curr.start + 0.01
    return segments


# ── Step 5: Merge short segments ─────────────────────────────────────────────

def _merge_short(
    segments: list[Segment],
    min_dur: float = 0.8,
) -> list[Segment]:
    if not segments:
        return segments

    result: list[Segment] = []
    pending: Optional[Segment] = None

    for seg in segments:
        if pending is None:
            pending = seg
            continue
        if pending.duration < min_dur:
            pending = Segment(
                start=pending.start, end=seg.end,
                text=f"{pending.text} {seg.text}".strip(),
                scene_id=pending.scene_id,
            )
        else:
            result.append(pending)
            pending = seg

    if pending is not None:
        if pending.duration < min_dur and result:
            last = result[-1]
            result[-1] = Segment(
                start=last.start, end=pending.end,
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
    result: list[Segment] = []
    for seg in segments:
        if seg.duration <= max_dur:
            result.append(seg)
            continue
        parts = _split_at_natural_break(seg, max_dur)
        result.extend(parts)
    return result


_SENTENCE_BREAK_RE = re.compile(r"(?<=[.!?])\s+")
_CLAUSE_BREAK_RE = re.compile(r"(?<=[,;:])\s+")


def _split_at_natural_break(seg: Segment, max_dur: float) -> list[Segment]:
    if seg.duration <= max_dur:
        return [seg]

    text = seg.text
    total_dur = seg.duration

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
                return _split_at_natural_break(left, max_dur) + \
                       _split_at_natural_break(right, max_dur)

    mid_char = len(text) // 2
    space_pos = text.rfind(" ", 0, mid_char + 10)
    if space_pos <= 0:
        space_pos = text.find(" ", mid_char)
    if space_pos <= 0:
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
    mid = len(text) // 2
    best_pos: Optional[int] = None
    best_dist = len(text)

    for match in pattern.finditer(text):
        pos = match.start()
        if pos < len(text) * 0.2 or pos > len(text) * 0.8:
            continue
        dist = abs(pos - mid)
        if dist < best_dist:
            best_dist = dist
            best_pos = match.end()

    return best_pos


# ── Step 7: Re-index ─────────────────────────────────────────────────────────

def _reindex(segments: list[Segment]) -> list[Segment]:
    for i, seg in enumerate(segments, start=1):
        seg.index = i
    return segments
