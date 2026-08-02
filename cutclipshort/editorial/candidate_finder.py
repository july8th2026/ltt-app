"""Candidate clip finder.

Generic candidate generation from AnalysisResult.
Strategies can override or extend this with genre-specific logic.
"""

from __future__ import annotations

import logging
from typing import Any

from cutclipshort.types import (
    AnalysisResult,
    CandidateClip,
    CandidateScore,
    ContentType,
    EditConstraints,
    TimeRange,
)

logger = logging.getLogger(__name__)


def find_candidates(
    analysis: AnalysisResult,
    constraints: EditConstraints,
    config: dict[str, Any],
) -> list[CandidateClip]:
    """Find clip candidates from analysis data.

    Default algorithm:
    1. Walk through transcript segments, grouping into chunks
       of target duration.
    2. Score each chunk by speech energy, motion, person presence.
    3. Snap boundaries to sentence edges.
    4. Deduplicate overlapping candidates.
    5. Return sorted by score.
    """
    min_dur = constraints.min_clip_duration_sec
    max_dur = constraints.max_clip_duration_sec
    target_count = constraints.max_clip_count

    candidates: list[CandidateClip] = []
    candidate_id = 0

    if not analysis.transcript:
        # Fallback: use scenes directly when no transcript
        candidates = _candidates_from_scenes(analysis, min_dur, max_dur)
    else:
        candidates = _candidates_from_transcript(
            analysis, min_dur, max_dur,
        )

    # Deduplicate overlapping candidates
    candidates = _deduplicate(candidates, overlap_threshold=0.5)

    # Sort by score descending
    candidates.sort(key=lambda c: c.score.overall, reverse=True)

    # Limit count
    candidates = candidates[:target_count]

    # Re-assign sequential IDs
    result = []
    for i, c in enumerate(candidates):
        result.append(CandidateClip(
            candidate_id=f"c{i + 1:03d}",
            time_range=c.time_range,
            score=c.score,
            content_type=c.content_type,
            genre_fit=c.genre_fit,
            motion_avg=c.motion_avg,
            has_speech=c.has_speech,
            speech_text_preview=c.speech_text_preview,
            transcript_segment_ids=c.transcript_segment_ids,
            has_person=c.has_person,
            person_count=c.person_count,
            tags=c.tags,
            hook_text=c.hook_text,
            suggested_hook_type=c.suggested_hook_type,
            strategy_name=c.strategy_name,
            strategy_reasoning=c.strategy_reasoning,
        ))

    logger.info("Found %d candidates from %d initial", len(result), len(candidates))
    return result


def _candidates_from_transcript(
    analysis: AnalysisResult,
    min_dur: float,
    max_dur: float,
) -> list[CandidateClip]:
    """Group transcript segments into candidate clips."""
    candidates = []
    segments = analysis.transcript
    if not segments:
        return []

    # Sliding window over transcript segments
    i = 0
    cid = 0
    while i < len(segments):
        # Start a new candidate at segment i
        start_time = segments[i].start
        end_time = segments[i].end
        text_parts = [segments[i].text]
        seg_ids = [segments[i].id]
        j = i + 1

        # Extend until max_dur or end of segments
        while j < len(segments) and (segments[j].end - start_time) <= max_dur:
            end_time = segments[j].end
            text_parts.append(segments[j].text)
            seg_ids.append(segments[j].id)
            j += 1

        duration = end_time - start_time
        if duration >= min_dur:
            tr = TimeRange(start=start_time, end=end_time)
            motion_avg = _avg_motion_in_range(analysis, tr)
            has_person = _has_person_in_range(analysis, tr)

            score = _score_candidate(
                duration, motion_avg, has_person, len(text_parts),
            )

            full_text = " ".join(text_parts)
            candidates.append(CandidateClip(
                candidate_id=f"tmp_{cid}",
                time_range=tr,
                score=score,
                content_type=ContentType.TALKING_HEAD,
                genre_fit=0.7,
                motion_avg=motion_avg,
                has_speech=True,
                speech_text_preview=full_text[:120],
                transcript_segment_ids=seg_ids,
                has_person=has_person,
                person_count=1 if has_person else 0,
                tags=_auto_tags(motion_avg, has_person, duration),
                hook_text=text_parts[0] if text_parts else "",
                suggested_hook_type="organic",
                strategy_name="generic",
                strategy_reasoning=f"Transcript group: {len(text_parts)} segments, {duration:.1f}s",
            ))
            cid += 1

        # Advance by half the window for overlap
        step = max(1, (j - i) // 2)
        i += step

    return candidates


def _candidates_from_scenes(
    analysis: AnalysisResult,
    min_dur: float,
    max_dur: float,
) -> list[CandidateClip]:
    """Fallback: group consecutive scenes into candidates."""
    candidates = []
    scenes = analysis.scenes
    if not scenes:
        return []

    i = 0
    cid = 0
    while i < len(scenes):
        start_time = scenes[i].time_range.start
        end_time = scenes[i].time_range.end
        j = i + 1

        while j < len(scenes) and (scenes[j].time_range.end - start_time) <= max_dur:
            end_time = scenes[j].time_range.end
            j += 1

        duration = end_time - start_time
        if duration >= min_dur:
            tr = TimeRange(start=start_time, end=end_time)
            motion_avg = _avg_motion_in_range(analysis, tr)

            score = _score_candidate(duration, motion_avg, False, 0)
            candidates.append(CandidateClip(
                candidate_id=f"tmp_{cid}",
                time_range=tr,
                score=score,
                content_type=ContentType.UNKNOWN,
                genre_fit=0.5,
                motion_avg=motion_avg,
                has_speech=False,
                speech_text_preview="",
                has_person=False,
                strategy_name="generic_scene",
                strategy_reasoning=f"Scene group: {j - i} scenes, {duration:.1f}s",
            ))
            cid += 1

        i = max(i + 1, i + (j - i) // 2)

    return candidates


def _score_candidate(
    duration: float,
    motion_avg: float,
    has_person: bool,
    segment_count: int,
) -> CandidateScore:
    """Compute a basic candidate score."""
    # Prefer clips in the 20-45s sweet spot
    dur_score = 1.0 - abs(duration - 30.0) / 30.0
    dur_score = max(0.0, min(1.0, dur_score))

    motion_score = min(1.0, motion_avg / 30.0)
    person_score = 0.8 if has_person else 0.3
    speech_score = min(1.0, segment_count / 5.0) if segment_count > 0 else 0.2

    overall = (
        dur_score * 0.15
        + motion_score * 0.15
        + person_score * 0.20
        + speech_score * 0.25
        + 0.5 * 0.25  # placeholder for hook/completeness
    )

    return CandidateScore(
        overall=round(overall, 3),
        hook_strength=round(speech_score * 0.8, 3),
        pacing=round(dur_score, 3),
        completeness=0.5,  # Will be refined by strategy
        visual_quality=round(person_score, 3),
        audio_quality=0.7,
    )


def _avg_motion_in_range(analysis: AnalysisResult, tr: TimeRange) -> float:
    """Average motion score within a time range."""
    # Use visual_segments if available, fall back to scenes
    relevant = [
        s.motion_avg for s in analysis.scenes
        if s.time_range.overlaps(tr)
    ]
    return sum(relevant) / len(relevant) if relevant else 0.0


def _has_person_in_range(analysis: AnalysisResult, tr: TimeRange) -> bool:
    """Check if any person detected in time range."""
    for vs in analysis.visual_segments:
        if vs.time_range.overlaps(tr) and vs.has_person:
            return True
    return False


def _auto_tags(motion_avg: float, has_person: bool, duration: float) -> list[str]:
    """Generate automatic tags based on metrics."""
    tags = []
    if motion_avg > 25:
        tags.append("high_energy")
    if motion_avg < 5:
        tags.append("calm")
    if has_person:
        tags.append("person_detected")
    if duration < 20:
        tags.append("short")
    if duration > 50:
        tags.append("long")
    return tags


def _deduplicate(
    candidates: list[CandidateClip],
    overlap_threshold: float = 0.5,
) -> list[CandidateClip]:
    """Remove candidates that overlap too much with higher-scored ones."""
    if not candidates:
        return []

    sorted_cands = sorted(candidates, key=lambda c: c.score.overall, reverse=True)
    kept: list[CandidateClip] = []

    for cand in sorted_cands:
        is_duplicate = False
        for existing in kept:
            overlap = cand.time_range.overlap_duration(existing.time_range)
            min_dur = min(cand.time_range.duration, existing.time_range.duration)
            if min_dur > 0 and overlap / min_dur > overlap_threshold:
                is_duplicate = True
                break
        if not is_duplicate:
            kept.append(cand)

    return kept
