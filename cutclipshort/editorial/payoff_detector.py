"""Payoff detector — scores the closing strength of a candidate segment.

A clip that ends abruptly mid-sentence or mid-thought feels broken.
A clip with a clear payoff (conclusion, punchline, resolution) feels
complete and satisfying. This module detects:

1. **Closure keywords**: "so that's why", "the bottom line", "and that's how"
2. **Sentence completion**: Ends on a period/exclamation, not mid-word
3. **Energy drop**: Natural speech energy decrease signals a thought ending
4. **Pause after payoff**: Brief silence after the last sentence = natural end
5. **Punchline detection** (comedy): Setup → pause → laughter pattern

Scoring range: 0.0 (no payoff / cut mid-thought) to 1.0 (perfect closure).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from cutclipshort.editorial.genre_profiles import GenreProfile
from cutclipshort.editorial.thresholds import T as _T
from cutclipshort.types import (
    AudioSegment,
    TimeRange,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)

PAYOFF_WINDOW_SEC = 5.0  # Last N seconds define the payoff zone


@dataclass(frozen=True)
class PayoffAnalysis:
    """Detailed payoff/closure analysis."""
    score: float               # 0.0-1.0 composite
    payoff_text: str           # Closing words
    payoff_type: str           # "keyword_closure", "natural_pause", "sentence_end", "incomplete"
    keyword_score: float       # 0.0-1.0
    sentence_complete: float   # 0.0 or 1.0
    energy_drop_score: float   # 0.0-1.0
    trailing_pause: float      # 0.0-1.0
    reasoning: str


def score_payoff(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
    profile: GenreProfile,
) -> PayoffAnalysis:
    """Score the closure quality of a segment's ending."""
    payoff_start = max(time_range.start, time_range.end - PAYOFF_WINDOW_SEC)
    payoff_range = TimeRange(start=payoff_start, end=time_range.end)

    # Extract closing text
    payoff_text, payoff_segments = _extract_payoff_text(payoff_range, transcript)
    payoff_lower = payoff_text.lower().strip()

    # 1. Keyword closure
    keyword_score = _score_closure_keywords(payoff_lower, profile)

    # 2. Sentence completeness (ends on punctuation?)
    sentence_complete = _score_sentence_completion(payoff_text, payoff_segments, time_range)

    # 3. Energy drop toward end (natural deceleration)
    energy_drop = _score_energy_drop(payoff_range, audio_segments)

    # 4. Trailing pause (silence after last word = natural stop)
    trailing_pause = _score_trailing_pause(payoff_segments, time_range, audio_segments)

    # Composite
    raw = (
        keyword_score * 0.30
        + sentence_complete * 0.35
        + energy_drop * 0.15
        + trailing_pause * 0.20
    )

    # Apply closure penalty from genre profile if incomplete
    if sentence_complete < _T.payoff_sentence_complete_threshold and profile.needs_closure:
        raw = max(0.0, raw - profile.closure_penalty * 0.5)

    score = max(0.0, min(1.0, raw))

    # Classify
    if keyword_score > _T.payoff_keyword_threshold + 0.20:
        payoff_type = "keyword_closure"
    elif trailing_pause > _T.payoff_sentence_complete_threshold and sentence_complete > _T.payoff_sentence_complete_threshold:
        payoff_type = "natural_pause"
    elif sentence_complete > _T.payoff_sentence_complete_threshold:
        payoff_type = "sentence_end"
    else:
        payoff_type = "incomplete"

    # Reasoning
    reasons = []
    if keyword_score > _T.payoff_keyword_threshold:
        reasons.append(f"closure keyword found ({keyword_score:.2f})")
    if sentence_complete > _T.payoff_sentence_complete_threshold:
        reasons.append("ends on complete sentence")
    else:
        reasons.append("INCOMPLETE: cut mid-sentence")
    if energy_drop > _T.payoff_energy_drop_threshold:
        reasons.append("natural energy decrease")
    if trailing_pause > _T.payoff_trailing_pause_threshold:
        reasons.append("natural trailing pause")

    return PayoffAnalysis(
        score=round(score, 3),
        payoff_text=payoff_text[-150:],
        payoff_type=payoff_type,
        keyword_score=round(keyword_score, 3),
        sentence_complete=round(sentence_complete, 3),
        energy_drop_score=round(energy_drop, 3),
        trailing_pause=round(trailing_pause, 3),
        reasoning="; ".join(reasons) if reasons else "weak ending",
    )


# ── Internal ─────────────────────────────────────────────────────────────

def _extract_payoff_text(
    payoff_range: TimeRange,
    transcript: list[TranscriptSegment],
) -> tuple[str, list[TranscriptSegment]]:
    """Get transcript text in the payoff window."""
    matching = [
        seg for seg in transcript
        if seg.time_range.overlaps(payoff_range)
    ]
    if not matching:
        return "", []

    # Take last few segments
    text_parts = [seg.text.strip() for seg in matching[-4:]]
    return " ".join(text_parts), matching


def _score_closure_keywords(text: str, profile: GenreProfile) -> float:
    """Score based on genre payoff keywords (EN + VI) with word-boundary matching."""
    import re
    if not text:
        return 0.0

    # Genre-specific keywords (English)
    for kw in profile.payoff_keywords:
        pattern = r'(?:^|\b)' + re.escape(kw) + r'(?:\b|$)'
        if re.search(pattern, text, re.IGNORECASE):
            return 0.8

    # Genre-specific keywords (Vietnamese — substring match, no word boundaries)
    for kw in profile.payoff_keywords_vi:
        if kw in text:
            return 0.8

    # Multi-language resolution words from vocabulary files
    try:
        from cutclipshort.editorial.vocabulary.en import RESOLUTION_WORDS as EN_RES
        for kw in EN_RES:
            if kw in text.lower():
                return 0.7
    except ImportError:
        pass
    try:
        from cutclipshort.editorial.vocabulary.vi import RESOLUTION_WORDS as VI_RES
        for kw in VI_RES:
            if kw in text.lower():
                return 0.7
    except ImportError:
        pass

    return 0.0


def _score_sentence_completion(
    text: str,
    segments: list[TranscriptSegment],
    full_range: TimeRange,
) -> float:
    """Check if the clip ends on a complete sentence (EN + VI aware).

    Vietnamese transcripts from Whisper often lack punctuation.
    We use multiple signals: punctuation, semantic end-words,
    trailing pause, and mid-sentence markers.
    """
    if not text:
        return 0.3  # No transcript = uncertain

    stripped = text.rstrip()
    if not stripped:
        return 0.3

    # 1. Ends with sentence-terminal punctuation? (works for both EN + VI)
    if stripped[-1] in ".!?":
        return 1.0

    # 2. Vietnamese semantic sentence-end words (no punctuation needed)
    lower = stripped.lower()

    # Strong closures (multi-word phrases — very reliable)
    vi_strong_end = (
        "xong rồi", "vậy đó", "thế đó", "như vậy", "thế thôi",
        "chỉ vậy", "có thế", "là xong", "hết rồi", "được rồi",
        "vậy thôi", "thế nhé", "xong nhé", "biết chưa",
    )
    for end_word in vi_strong_end:
        if lower.endswith(end_word):
            return 0.90  # Very strong VI semantic completion

    # Moderate closures (3+ char single words — reliable when standalone)
    vi_moderate_end = (
        "rồi", "xong", "được", "thôi", "luôn", "liền",
        "vậy", "nhé", "nha", "lắm", "ghê",
    )
    for end_word in vi_moderate_end:
        if lower.endswith(end_word):
            return 0.80  # Good VI closure

    # Weak closures (2 char — only if preceded by space to avoid mid-word match)
    vi_weak_end = ("đó", "đấy", "hết", "ngay")
    for end_word in vi_weak_end:
        # Must be a standalone word: check space before it
        suffix = " " + end_word
        if lower.endswith(suffix):
            return 0.70  # Acceptable but less certain

    # 3. Check trailing silence gap (works for any language)
    if segments:
        last_seg = segments[-1]
        gap = full_range.end - last_seg.end
        if gap > 2.0:
            # Large gap after last speech = intentional pause = complete
            return 0.7
        elif 0.3 <= gap <= 2.0:
            # Moderate gap = likely natural ending
            return 0.6
        elif gap < 0.3:
            # Speech runs right up to the cut = likely mid-sentence
            return 0.2

    # 4. Ends with mid-sentence markers = definitely incomplete (EN + VI)
    mid_sentence_markers = (
        # English
        ",", " and", " but", " or", " the", " a", " to", " of", " in", " for", " with",
        # Vietnamese conjunctions/prepositions (always mid-sentence)
        " và", " nhưng", " hoặc", " vì", " nên", " mà",
        " khi", " nếu", " của", " với", " cho", " về",
        " để", " bởi", " từ", " theo", " qua",
    )
    for marker in mid_sentence_markers:
        if stripped.endswith(marker):
            return 0.1

    # 5. Vietnamese: no punctuation but no mid-sentence marker = likely OK
    #    (Whisper VI output rarely has punctuation, so absence ≠ incomplete)
    return 0.55  # Raised from 0.4: benefit of doubt for VI content


def _score_energy_drop(
    payoff_range: TimeRange,
    audio_segments: list[AudioSegment],
) -> float:
    """Detect natural energy decrease toward the end (= natural stopping point)."""
    relevant = [
        seg for seg in audio_segments
        if seg.time_range.overlaps(payoff_range)
    ]
    if len(relevant) < 2:
        return 0.5  # Not enough data

    # Compare energy of first half vs second half of payoff window
    mid = payoff_range.start + payoff_range.duration / 2
    first_half = [s for s in relevant if s.time_range.midpoint < mid]
    second_half = [s for s in relevant if s.time_range.midpoint >= mid]

    if not first_half or not second_half:
        return 0.5

    avg_first = sum(s.energy_avg for s in first_half) / len(first_half)
    avg_second = sum(s.energy_avg for s in second_half) / len(second_half)

    # Energy drop = good (natural deceleration)
    if avg_second < avg_first * 0.7:
        return 0.8
    elif avg_second < avg_first * 0.9:
        return 0.6
    else:
        return 0.3  # Energy stays flat or rises = not a natural ending


def _score_trailing_pause(
    segments: list[TranscriptSegment],
    full_range: TimeRange,
    audio_segments: list[AudioSegment],
) -> float:
    """Score the gap between last speech and clip end."""
    if not segments:
        return 0.0

    last_speech_end = max(seg.end for seg in segments)
    gap = full_range.end - last_speech_end

    # Ideal: 0.3-1.5s pause after last word
    if 0.3 <= gap <= 1.5:
        return 0.9
    elif gap < 0.3:
        return 0.3  # Cut too tight to speech end
    elif gap <= 3.0:
        return 0.6  # Acceptable
    else:
        return 0.2  # Too much dead air at end
