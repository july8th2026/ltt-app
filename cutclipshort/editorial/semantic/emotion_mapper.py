"""Emotion mapper — detects emotional intensity spikes across timeline.

Multi-signal fusion: text emotion + audio energy + speech pace + punctuation.
Produces EmotionalSpike objects for peaks above threshold.
"""

from __future__ import annotations

import logging

from cutclipshort.editorial.semantic_scorer import (
    _EMOTION_HIGH,
    _EMOTION_MEDIUM,
    _EMOTION_MILD,
    _tokenize,
)
from cutclipshort.types import (
    AudioSegment,
    EmotionalSpike,
    TimeRange,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)

_MIN_INTENSITY = 0.40
_MERGE_WINDOW_SEC = 5.0

# Emotion classification vocabulary
_EXCITEMENT_WORDS = frozenset({
    "amazing", "incredible", "unbelievable", "wow", "awesome",
    "fantastic", "brilliant", "spectacular", "mindblowing",
})
_HUMOR_WORDS = frozenset({
    "funny", "hilarious", "joke", "laugh", "haha", "lol",
    "comedy", "punchline", "ridiculous", "absurd",
})
_ANGER_WORDS = frozenset({
    "wrong", "terrible", "hate", "disgusting", "outrageous",
    "furious", "unacceptable", "worst", "stupid",
})
_SURPRISE_WORDS = frozenset({
    "wait", "what", "really", "seriously", "plot twist",
    "unexpected", "suddenly", "turns out", "shocked",
})
_TENSION_WORDS = frozenset({
    "but", "however", "problem", "danger", "risk", "scary",
    "worried", "afraid", "crisis", "threat", "careful",
})


def detect_spikes(
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
    min_intensity: float = _MIN_INTENSITY,
    merge_window: float = _MERGE_WINDOW_SEC,
) -> list[EmotionalSpike]:
    """Find emotional intensity peaks across the timeline."""
    if not transcript:
        return []

    # 1. Compute per-sentence intensity
    raw: list[tuple[TranscriptSegment, float, str]] = []
    for seg in transcript:
        intensity, emotion_type, source = _score_sentence(seg, audio_segments, transcript)
        raw.append((seg, intensity, emotion_type))

    # 2. Smooth with 3-point moving average
    smoothed = _smooth(raw)

    # 3. Find peaks above threshold
    peaks = [
        (seg, intensity, etype)
        for seg, intensity, etype in smoothed
        if intensity >= min_intensity
    ]

    # 4. Merge adjacent peaks
    spikes = _merge_adjacent(peaks, merge_window)

    return spikes


def _score_sentence(
    seg: TranscriptSegment,
    audio_segments: list[AudioSegment],
    all_transcript: list[TranscriptSegment],
) -> tuple[float, str, str]:
    """Score emotional intensity of a single sentence.

    Returns: (intensity, emotion_type, source)
    """
    words = _tokenize(seg.text.lower())
    if not words:
        return 0.0, "neutral", "none"

    # 1. Text emotional density
    high = sum(1 for w in words if w in _EMOTION_HIGH)
    med = sum(1 for w in words if w in _EMOTION_MEDIUM)
    mild = sum(1 for w in words if w in _EMOTION_MILD)
    weighted = high * 3 + med * 2 + mild
    # Emotion density scale: 5% emotional words = max score
    _EMOTION_DENSITY_SCALE = 0.05
    text_score = min(1.0, weighted / max(1, len(words)) / _EMOTION_DENSITY_SCALE)

    # 2. Audio energy deviation
    seg_range = TimeRange(seg.start, seg.end)
    matching = [a for a in audio_segments if a.time_range.overlaps(seg_range)]
    all_energies = sorted(a.energy_avg for a in audio_segments if a.energy_avg > 0)
    # Use median (robust to outliers) instead of mean
    median_energy = all_energies[len(all_energies) // 2] if all_energies else 0.1

    energy_score = 0.0
    if matching:
        seg_energy = max(a.energy_avg for a in matching)
        if median_energy > 0:
            energy_score = min(1.0, max(0.0, (seg_energy - median_energy) / median_energy))

    # 3. Pace acceleration (words per second vs neighbors)
    duration = max(0.1, seg.end - seg.start)
    wps = len(words) / duration
    pace_score = min(1.0, max(0.0, (wps - 2.5) / 2.5))  # Above 2.5 wps = fast

    # 4. Punctuation intensity
    excl = seg.text.count("!")
    caps_words = sum(1 for w in seg.text.split() if w.isupper() and len(w) > 1)
    punct_score = min(1.0, excl * 0.3 + caps_words * 0.2)

    # Combined
    combined = (
        text_score * 0.35
        + energy_score * 0.30
        + pace_score * 0.15
        + punct_score * 0.20
    )

    # Determine dominant source
    source_scores = {
        "text": text_score, "energy": energy_score,
        "pace": pace_score, "punctuation": punct_score,
    }
    source = max(source_scores, key=source_scores.get)
    if text_score > 0.3 and energy_score > 0.3:
        source = "combined"

    # Classify emotion type
    emotion_type = _classify_emotion(words)

    return combined, emotion_type, source


def _classify_emotion(words: list[str]) -> str:
    """Classify dominant emotion type from word set."""
    word_set = set(words)

    scores = {
        "excitement": len(word_set & _EXCITEMENT_WORDS),
        "humor": len(word_set & _HUMOR_WORDS),
        "anger": len(word_set & _ANGER_WORDS),
        "surprise": len(word_set & _SURPRISE_WORDS),
        "tension": len(word_set & _TENSION_WORDS),
    }

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        # Fallback: check high emotion words
        if word_set & _EMOTION_HIGH:
            return "excitement"
        return "neutral"

    return best


def _smooth(
    data: list[tuple[TranscriptSegment, float, str]],
) -> list[tuple[TranscriptSegment, float, str]]:
    """3-point moving average smoothing."""
    if len(data) < 3:
        return data

    result = list(data)
    for i in range(1, len(data) - 1):
        avg = (data[i - 1][1] + data[i][1] + data[i + 1][1]) / 3
        result[i] = (data[i][0], avg, data[i][2])

    return result


def _merge_adjacent(
    peaks: list[tuple[TranscriptSegment, float, str]],
    window: float,
) -> list[EmotionalSpike]:
    """Merge adjacent peaks within window into single spikes."""
    if not peaks:
        return []

    spikes: list[EmotionalSpike] = []
    current_group: list[tuple[TranscriptSegment, float, str]] = [peaks[0]]

    for i in range(1, len(peaks)):
        seg, intensity, etype = peaks[i]
        prev_seg = current_group[-1][0]

        if seg.start - prev_seg.end <= window:
            current_group.append(peaks[i])
        else:
            spikes.append(_group_to_spike(current_group, len(spikes)))
            current_group = [peaks[i]]

    if current_group:
        spikes.append(_group_to_spike(current_group, len(spikes)))

    return spikes


def _group_to_spike(
    group: list[tuple[TranscriptSegment, float, str]],
    spike_id: int,
) -> EmotionalSpike:
    """Convert a group of peak sentences into a single EmotionalSpike."""
    best = max(group, key=lambda x: x[1])
    peak_seg, peak_intensity, _ = best

    # Dominant emotion type
    type_counts: dict[str, int] = {}
    for _, _, etype in group:
        type_counts[etype] = type_counts.get(etype, 0) + 1
    dominant = max(type_counts, key=type_counts.get)

    # Determine source
    sources = {src for _, _, src in group}
    source = "combined" if len(sources) > 1 else sources.pop()

    return EmotionalSpike(
        spike_id=spike_id,
        time_range=TimeRange(group[0][0].start, group[-1][0].end),
        peak_time=peak_seg.start + (peak_seg.end - peak_seg.start) / 2,
        intensity=round(peak_intensity, 3),
        emotion_type=dominant,
        source=source,
        transcript_segment_ids=[seg.id for seg, _, _ in group],
    )
