"""Narrative segmenter — detects story arcs in transcript.

Identifies intro → rising action → climax → resolution patterns
using marker detection and intensity curve analysis.

Reuses vocabulary from semantic_scorer.py for stage detection.
"""

from __future__ import annotations

import logging
import re

from cutclipshort.editorial.semantic_scorer import (
    _SETUP_MARKERS,
    _DEVELOPMENT_MARKERS,
    _RESOLUTION_MARKERS,
    _EMOTION_HIGH,
    _EMOTION_MEDIUM,
    _tokenize,
)
from cutclipshort.types import (
    AudioSegment,
    NarrativeArc,
    TimeRange,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)

_MIN_ARC_SENTENCES = 5
_CLIMAX_WORDS = frozenset({
    "finally", "moment", "boom", "suddenly", "then", "realized",
    "unbelievable", "insane", "shocking", "incredible", "wow",
    "breakthrough", "discovered", "happened", "explosion", "reveal",
}) | _EMOTION_HIGH


def detect_arcs(
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
    min_arc_sentences: int = _MIN_ARC_SENTENCES,
) -> list[NarrativeArc]:
    """Detect story arcs in transcript.

    Returns arcs with completeness >= 0.4 (at least 2 of 4 stages).
    """
    if len(transcript) < min_arc_sentences:
        return []

    # 1. Score each sentence for stage markers
    stage_scores = _score_stages(transcript)

    # 2. Build intensity curve
    intensity = _build_intensity_curve(transcript, audio_segments)

    # 3. Find climax peaks
    peaks = _find_peaks(intensity, min_prominence=0.3)

    if not peaks:
        # Try lower threshold
        peaks = _find_peaks(intensity, min_prominence=0.2)

    # 4. Build arcs around peaks
    arcs: list[NarrativeArc] = []
    used_ranges: list[TimeRange] = []

    for peak_idx, peak_intensity in peaks:
        arc = _try_build_arc(
            transcript, stage_scores, peak_idx, peak_intensity,
            min_arc_sentences,
        )
        if arc is None or arc.completeness < 0.4:
            continue

        # Skip if overlaps with existing arc
        if any(arc.time_range.overlap_duration(r) / arc.time_range.duration > 0.5
               for r in used_ranges):
            continue

        arcs.append(arc)
        used_ranges.append(arc.time_range)

    return arcs


def _score_stages(
    transcript: list[TranscriptSegment],
) -> list[dict[str, float]]:
    """Score each sentence for narrative stage markers."""
    results = []
    for seg in transcript:
        lower = seg.text.lower()
        words = set(_tokenize(lower))

        intro = 0.0
        for m in _SETUP_MARKERS:
            if m in lower[:80]:
                intro = 0.8
                break
        if not intro and any(w in words for w in {"so", "today", "let"}):
            intro = 0.3

        rising = 0.0
        for m in _DEVELOPMENT_MARKERS:
            if m in lower:
                rising = 0.8
                break
        if not rising and any(w in words for w in {"because", "since", "when"}):
            rising = 0.3

        climax = 0.0
        climax_hits = len(words & _CLIMAX_WORDS)
        if climax_hits >= 2:
            climax = 0.9
        elif climax_hits == 1:
            climax = 0.5
        if "!" in seg.text:
            climax = max(climax, 0.4)

        resolution = 0.0
        for m in _RESOLUTION_MARKERS:
            if m in lower:
                resolution = 0.8
                break
        if not resolution and any(w in words for w in {"so", "therefore", "conclusion"}):
            resolution = 0.3

        results.append({
            "intro": intro,
            "rising_action": rising,
            "climax": climax,
            "resolution": resolution,
        })

    return results


def _build_intensity_curve(
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
) -> list[float]:
    """Build per-sentence intensity from text + audio energy."""
    intensities: list[float] = []

    for seg in transcript:
        words = _tokenize(seg.text.lower())
        if not words:
            intensities.append(0.0)
            continue

        # Text emotional density
        emotion_count = sum(1 for w in words if w in _EMOTION_HIGH | _EMOTION_MEDIUM)
        text_intensity = min(1.0, emotion_count / max(1, len(words)) * 10)

        # Punctuation intensity
        punct = seg.text.count("!") * 0.2 + seg.text.count("?") * 0.1
        punct = min(0.5, punct)

        # Audio energy
        audio_energy = 0.0
        seg_range = TimeRange(seg.start, seg.end)
        matching_audio = [
            a for a in audio_segments if a.time_range.overlaps(seg_range)
        ]
        if matching_audio:
            audio_energy = max(a.energy_avg for a in matching_audio)

        combined = text_intensity * 0.45 + audio_energy * 0.35 + punct * 0.20
        intensities.append(combined)

    # Smooth with 3-point moving average
    if len(intensities) >= 3:
        smoothed = list(intensities)
        for i in range(1, len(smoothed) - 1):
            smoothed[i] = (intensities[i - 1] + intensities[i] + intensities[i + 1]) / 3
        return smoothed

    return intensities


def _find_peaks(
    curve: list[float], min_prominence: float,
) -> list[tuple[int, float]]:
    """Find local maxima with minimum prominence."""
    if len(curve) < 3:
        return []

    peaks: list[tuple[int, float]] = []
    for i in range(1, len(curve) - 1):
        if curve[i] > curve[i - 1] and curve[i] > curve[i + 1]:
            # Prominence: height above lowest neighbor
            prominence = curve[i] - min(curve[i - 1], curve[i + 1])
            if prominence >= min_prominence and curve[i] >= 0.3:
                peaks.append((i, curve[i]))

    # Sort by intensity descending
    peaks.sort(key=lambda p: p[1], reverse=True)
    return peaks[:5]  # Max 5 arcs per video


def _try_build_arc(
    transcript: list[TranscriptSegment],
    stage_scores: list[dict[str, float]],
    peak_idx: int,
    peak_intensity: float,
    min_sentences: int,
) -> NarrativeArc | None:
    """Try to construct a narrative arc around a climax peak."""
    n = len(transcript)

    # Find arc boundaries: scan backward for intro, forward for resolution
    arc_start = max(0, peak_idx - min_sentences)
    arc_end = min(n - 1, peak_idx + min(min_sentences, n - peak_idx - 1))

    # Expand backward to find intro
    for i in range(peak_idx - 1, max(0, peak_idx - 15), -1):
        if stage_scores[i]["intro"] > 0.5:
            arc_start = i
            break

    # Expand forward to find resolution
    for i in range(peak_idx + 1, min(n, peak_idx + 15)):
        if stage_scores[i]["resolution"] > 0.5:
            arc_end = i
            break

    if arc_end - arc_start + 1 < min_sentences:
        return None

    # Determine which stages are present
    stages: dict[str, TimeRange] = {}

    # Intro: highest intro score in first third of arc
    third = max(1, (arc_end - arc_start) // 3)
    intro_scores = [(i, stage_scores[i]["intro"]) for i in range(arc_start, arc_start + third)]
    if intro_scores:
        best_intro = max(intro_scores, key=lambda x: x[1])
        if best_intro[1] > 0.2:
            seg = transcript[best_intro[0]]
            stages["intro"] = TimeRange(seg.start, seg.end)

    # Rising action: highest rising score between intro and climax
    mid_start = arc_start + third
    mid_end = peak_idx
    rising_scores = [(i, stage_scores[i]["rising_action"]) for i in range(mid_start, mid_end)]
    if rising_scores:
        best_rising = max(rising_scores, key=lambda x: x[1])
        if best_rising[1] > 0.2:
            seg = transcript[best_rising[0]]
            stages["rising_action"] = TimeRange(seg.start, seg.end)

    # Climax: the peak itself
    climax_seg = transcript[peak_idx]
    stages["climax"] = TimeRange(climax_seg.start, climax_seg.end)

    # Resolution: highest resolution score after climax
    res_scores = [(i, stage_scores[i]["resolution"]) for i in range(peak_idx + 1, arc_end + 1)]
    if res_scores:
        best_res = max(res_scores, key=lambda x: x[1])
        if best_res[1] > 0.2:
            seg = transcript[best_res[0]]
            stages["resolution"] = TimeRange(seg.start, seg.end)

    completeness = len(stages) / 4.0

    return NarrativeArc(
        arc_id=0,  # Caller assigns final IDs
        time_range=TimeRange(
            transcript[arc_start].start,
            transcript[arc_end].end,
        ),
        stages=stages,
        completeness=round(completeness, 2),
        climax_intensity=round(peak_intensity, 3),
        transcript_segment_ids=[
            transcript[i].id for i in range(arc_start, arc_end + 1)
        ],
    )
