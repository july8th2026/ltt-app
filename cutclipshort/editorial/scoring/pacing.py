"""Pacing scorer — duration fit, WPM, speech ratio, silence ratio."""

from __future__ import annotations

from cutclipshort.editorial.genre_profiles import GenreProfile
from cutclipshort.types import AudioSegment, TimeRange, TranscriptSegment


def score_pacing(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
    profile: GenreProfile,
) -> tuple[float, list[int], str, int, float]:
    """Score pacing: speech rate, silence ratio, duration fit.

    Returns: (pacing_score, transcript_ids, speech_text, word_count, speech_ratio)
    """
    duration = time_range.duration

    matching_segs = [
        seg for seg in transcript if seg.time_range.overlaps(time_range)
    ]
    seg_ids = [seg.id for seg in matching_segs]
    text = " ".join(seg.text.strip() for seg in matching_segs)
    word_count = len(text.split()) if text else 0

    speech_sec = sum(
        seg.time_range.overlap_duration(time_range) for seg in matching_segs
    )
    speech_ratio = speech_sec / duration if duration > 0 else 0.0

    wpm = (word_count / (speech_sec / 60.0)) if speech_sec > 10 else 0.0

    scores = []

    # Duration fit
    dur_dist = abs(duration - profile.sweet_spot_sec) / profile.sweet_spot_sec
    scores.append(max(0.0, 1.0 - dur_dist))

    # WPM fit — skip for genres that don't require speech
    if not profile.require_speech:
        scores.append(0.8)  # Neutral: WPM irrelevant for non-speech genres
    elif wpm > 0:
        if profile.ideal_wpm_min <= wpm <= profile.ideal_wpm_max:
            scores.append(1.0)
        else:
            wpm_mid = (profile.ideal_wpm_min + profile.ideal_wpm_max) / 2
            wpm_dist = abs(wpm - wpm_mid) / wpm_mid
            scores.append(max(0.0, 1.0 - wpm_dist))
    else:
        scores.append(0.1)  # No speech in a speech-required genre

    # Speech ratio — skip penalty for genres that don't require speech
    if not profile.require_speech:
        scores.append(0.8)  # Neutral: speech not required, don't penalize absence
    elif speech_ratio >= profile.min_speech_ratio:
        scores.append(1.0)
    else:
        scores.append(speech_ratio / profile.min_speech_ratio)

    # Silence ratio
    silence_segs = [
        seg for seg in audio_segments
        if seg.time_range.overlaps(time_range) and seg.has_silence
    ]
    silence_sec = sum(
        seg.time_range.overlap_duration(time_range) for seg in silence_segs
    )
    silence_ratio = silence_sec / duration if duration > 0 else 0.0
    if silence_ratio <= profile.max_silence_ratio:
        scores.append(1.0)
    else:
        excess = silence_ratio - profile.max_silence_ratio
        scores.append(max(0.0, 1.0 - excess * 3))

    pacing_score = sum(scores) / len(scores) if scores else 0.5
    return pacing_score, seg_ids, text, word_count, speech_ratio
