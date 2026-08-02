"""Candidate generator V2 — multi-pass intent-driven clip proposal engine.

Architecture: 4 sequential passes, each intent-focused.
After all passes: coverage scan + semantic dedup + scoring.

Pass 1: HOOK candidates     — strong openings that grab attention
Pass 2: STORY candidates    — narrative arcs with structure
Pass 3: EMOTIONAL candidates — intensity spikes and viral moments
Pass 4: DENSE INFO candidates — high information density segments

Post-passes:
- Coverage gap scanner: finds important uncovered regions
- Semantic deduplication: removes content-redundant proposals
- Scoring: segment_scorer scores each unique proposal

Design principles:
- Each pass is independent and can run on any content type
- Pass order = priority (hook > story > emotion > info)
- Coverage scanner ensures no important region is missed
- Semantic dedup prevents clips with same content from different passes
- All passes gracefully degrade when data is missing
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from cutclipshort.editorial.genre_profiles import GenreProfile
from cutclipshort.editorial.segment_scorer import ScoredSegment, score_segment
from cutclipshort.editorial.thresholds import T
from cutclipshort.types import (
    AnalysisResult,
    EditConstraints,
    TimeRange,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RawProposal:
    """A proposed clip boundary before scoring."""
    time_range: TimeRange
    source: str              # Pass that generated this (e.g. "hook_question", "story_arc")
    reason: str              # Human-readable explanation of why this was proposed
    intent_hint: str = ""    # Suggested intent: hook/story/payoff/shock/insight/loop
    priority: int = 5        # Lower = higher priority in dedup (1=highest)
    cluster_id: int = -1     # Set by CandidateDiversityManager (-1 = unassigned)


# ══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════

def generate_candidates(
    analysis: AnalysisResult,
    constraints: EditConstraints,
    profile: GenreProfile,
    semantic_ctx: "SemanticContext | None" = None,
    max_passes: int = 6,
    extra_hook_keywords: list[str] | None = None,
) -> list[ScoredSegment]:
    """Multi-pass candidate generation by intent with diversity enforcement.

    Pass 1: HOOK candidates (always runs)
    Pass 2: STORY candidates (runs if max_passes >= 2)
    Pass 3: SHOCK candidates — emotional spikes, controversy (max_passes >= 3)
    Pass 4: INSIGHT candidates — dense info segments (max_passes >= 4)
    Pass 5: PAYOFF candidates — resolution/conclusion segments (max_passes >= 5)
    Pass 6: LOOP candidates — short satisfying moments (max_passes >= 6)
    Post:   Coverage gap scan + CandidateDiversityManager + scoring

    Args:
        max_passes: How many passes to run (tier-controlled).
                    1 = hooks only (fast), 6 = all intents (HQ).
    """
    # Use genre profile duration preferences, clamped by hard constraints
    min_dur = max(constraints.min_clip_duration_sec, profile.ideal_min_sec * 0.8)
    max_dur = min(constraints.max_clip_duration_sec, profile.ideal_max_sec * 1.2)
    # Safety: ensure min < max
    if min_dur >= max_dur:
        logger.warning(
            "Genre '%s' duration range (%.0f-%.0fs) conflicts with constraints (%.0f-%.0fs), using constraints",
            profile.name, profile.ideal_min_sec, profile.ideal_max_sec,
            constraints.min_clip_duration_sec, constraints.max_clip_duration_sec,
        )
        min_dur = constraints.min_clip_duration_sec
        max_dur = constraints.max_clip_duration_sec
    source_duration = analysis.source.duration_sec

    all_proposals: list[RawProposal] = []

    # ── Pre-check: transcript quality ─────────────────────────────
    transcript_quality = _assess_transcript_quality(analysis.transcript)
    _low_transcript = transcript_quality < 0.3
    if _low_transcript:
        logger.warning(
            "Low transcript quality (%.0f%%) — hallucination or wrong language detected. "
            "Limiting to motion/scene-based passes, skipping text-dependent passes.",
            transcript_quality * 100,
        )
        max_passes = min(max_passes, 1)  # Only hook pass (uses scene/motion too)

    # ── PASS 1: HOOK candidates (always) ─────────────────────────
    hook_proposals = _pass_hooks(analysis, min_dur, max_dur, profile,
                                  extra_hook_keywords=extra_hook_keywords or [])
    all_proposals.extend(hook_proposals)
    logger.info("Pass 1 (HOOK): %d proposals", len(hook_proposals))

    # ── PASS 2: STORY candidates ─────────────────────────────────
    if max_passes >= 2:
        story_proposals = _pass_stories(analysis, min_dur, max_dur, profile, semantic_ctx)
        all_proposals.extend(story_proposals)
        logger.info("Pass 2 (STORY): %d proposals", len(story_proposals))

    # ── PASS 3: SHOCK candidates (was: emotional) ────────────────
    if max_passes >= 3:
        shock_proposals = _pass_emotional(analysis, min_dur, max_dur, profile, semantic_ctx)
        # Remap intent_hint from "emotional" to "shock"
        shock_proposals = [
            RawProposal(p.time_range, p.source.replace("emotional", "shock"),
                        p.reason, "shock", p.priority)
            for p in shock_proposals
        ]
        all_proposals.extend(shock_proposals)
        logger.info("Pass 3 (SHOCK): %d proposals", len(shock_proposals))

    # ── PASS 4: INSIGHT candidates (was: dense_info) ─────────────
    if max_passes >= 4:
        insight_proposals = _pass_dense_info(analysis, min_dur, max_dur, profile)
        # Remap intent_hint
        insight_proposals = [
            RawProposal(p.time_range, p.source.replace("dense", "insight"),
                        p.reason, "insight", p.priority)
            for p in insight_proposals
        ]
        all_proposals.extend(insight_proposals)
        logger.info("Pass 4 (INSIGHT): %d proposals", len(insight_proposals))

    # ── PASS 5: PAYOFF candidates (NEW) ──────────────────────────
    if max_passes >= 5:
        payoff_proposals = _pass_payoff(analysis, min_dur, max_dur, profile, semantic_ctx)
        all_proposals.extend(payoff_proposals)
        logger.info("Pass 5 (PAYOFF): %d proposals", len(payoff_proposals))

    # ── PASS 6: LOOP candidates (NEW) ────────────────────────────
    if max_passes >= 6:
        loop_proposals = _pass_loop(analysis, min_dur, max_dur, profile, semantic_ctx)
        all_proposals.extend(loop_proposals)
        logger.info("Pass 6 (LOOP): %d proposals", len(loop_proposals))

    # ── POST: Coverage gap scan ──────────────────────────────────
    if max_passes >= 3:
        gap_proposals = _scan_coverage_gaps(
            analysis, all_proposals, min_dur, max_dur, source_duration, profile,
        )
        all_proposals.extend(gap_proposals)
        logger.info("Coverage gaps: %d proposals", len(gap_proposals))

    # ── PASS 7: MOTION-BASED candidates (when transcript is poor) ──
    target = constraints.target_clip_count
    if transcript_quality < 0.3:
        motion_proposals = _pass_motion_peaks(analysis, min_dur, max_dur, profile)
        all_proposals.extend(motion_proposals)
        logger.info("Pass 7 (MOTION fallback): %d proposals (low transcript quality)", len(motion_proposals))

    logger.info("Total raw proposals: %d", len(all_proposals))

    # ── POST: CandidateDiversityManager ──────────────────────────
    # Adjust overlap threshold based on target: more clips needed → more lenient
    target = constraints.target_clip_count
    # For ≤5 clips: 70% overlap max. For 10+: allow 50% overlap.
    adaptive_overlap = max(0.45, 0.70 - (target - 5) * 0.025) if target > 5 else 0.70
    diversity_mgr = CandidateDiversityManager(
        max_overlap_ratio=adaptive_overlap,
        min_output=target * 2,  # Ensure enough for tournament
    )
    unique_proposals = diversity_mgr.enforce(all_proposals, analysis.transcript)
    logger.info("After diversity enforcement: %d proposals (%d clusters)",
                len(unique_proposals), diversity_mgr.cluster_count)

    # ── SCORING ──────────────────────────────────────────────────
    scored: list[ScoredSegment] = []
    for prop in unique_proposals:
        seg = score_segment(
            time_range=prop.time_range,
            transcript=analysis.transcript,
            audio_segments=analysis.audio_segments,
            visual_segments=analysis.visual_segments,
            scenes=analysis.scenes,
            profile=profile,
            semantic_ctx=semantic_ctx,
        )
        # Inject generation metadata from proposal
        from dataclasses import replace as dc_replace
        seg = dc_replace(
            seg,
            generation_reason=f"[{prop.source}] {prop.reason}",
            cluster_id=prop.cluster_id,
        )

        # [Phase2] Filter gap proposals with minimum score threshold
        # Gap-filled segments that score too low bring down output quality
        _GAP_MIN_SCORE = 0.25
        if prop.source.startswith("coverage_gap") and seg.composite_score < _GAP_MIN_SCORE:
            logger.debug(
                "Dropped low-quality gap proposal (%.2f < %.2f): %s",
                seg.composite_score, _GAP_MIN_SCORE, prop.reason,
            )
            continue

        scored.append(seg)

    return scored


# ══════════════════════════════════════════════════════════════════════════
# PASS 1: HOOK CANDIDATES
# ══════════════════════════════════════════════════════════════════════════

def _pass_hooks(
    analysis: AnalysisResult,
    min_dur: float,
    max_dur: float,
    profile: GenreProfile,
    extra_hook_keywords: list[str] | None = None,
) -> list[RawProposal]:
    """Find segments with strong openings — questions, bold claims, stats.

    Sub-strategies:
    A. Keyword/pattern hook detection (existing logic)
    B. Question-anchored clips
    C. Statistic/number-anchored clips
    D. Energy-spike openings (loud confident start)
    """
    proposals: list[RawProposal] = []
    segments = analysis.transcript
    if not segments:
        return proposals

    used_starts: set[int] = set()

    for i, seg in enumerate(segments):
        if i in used_starts:
            continue

        text_lower = seg.text.lower().strip()
        hook_type, hook_reason = _detect_hook_type(
            text_lower, seg, profile, extra_hook_keywords=extra_hook_keywords or []
        )

        if hook_type == "none":
            continue

        # Extend forward to payoff or natural boundary
        end_idx, found_payoff = _extend_to_payoff(
            segments, i, min_dur, max_dur, profile,
        )

        end_time = segments[end_idx].end
        duration = end_time - seg.start

        if duration >= min_dur:
            used_starts.add(i)
            proposals.append(RawProposal(
                time_range=TimeRange(start=seg.start, end=end_time),
                source=f"hook_{hook_type}",
                reason=f"Hook({hook_type}): {hook_reason}"
                       f"{' → payoff' if found_payoff else ''}",
                intent_hint="hook",
                priority=1,
            ))

    # Energy-spike opening: first 3s has energy > 150% of video mean
    energy_hooks = _find_energy_openings(analysis, min_dur, max_dur)
    proposals.extend(energy_hooks)

    return proposals


def _detect_hook_type(
    text_lower: str, seg: Any, profile: GenreProfile,
    extra_hook_keywords: list[str] | None = None,
) -> tuple[str, str]:
    """Classify what kind of hook this sentence is.

    Returns: (hook_type, reason)
    hook_type: "question", "statistic", "keyword", "bold", "curiosity", "none"
    """
    # Question
    if "?" in seg.text:
        return "question", f'"{text_lower[:40]}..."'

    # Statistic / number
    numbers = re.findall(r'\b\d+[\.\d]*\s*(%|percent|million|billion|thousand|x)\b', text_lower)
    if numbers:
        return "statistic", f"number hook: {numbers[0]}"
    if re.search(r'\b\d+\s+(ways?|tips?|steps?|reasons?|things?|mistakes?)\b', text_lower):
        return "statistic", "list hook"

    # Keyword (EN)
    for kw in profile.hook_keywords:
        kw_pattern = r'(?:^|\b)' + re.escape(kw) + r'(?:\b|$)'
        if re.search(kw_pattern, text_lower):
            return "keyword", f"keyword '{kw}'"

    # Keyword (VI — substring match, Vietnamese has no word boundaries)
    for kw in profile.hook_keywords_vi:
        if kw in text_lower:
            return "keyword", f"keyword_vi '{kw}'"

    # User-defined keywords (from tab profile — substring match, works for both VI/EN)
    for kw in (extra_hook_keywords or []):
        if kw and kw.lower() in text_lower:
            return "keyword", f"user_keyword '{kw}'"

    # Pattern (EN)
    for pattern in profile.hook_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return "keyword", "pattern match"

    # Pattern (VI)
    for pattern in profile.hook_patterns_vi:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return "keyword", "pattern_vi match"

    # Curiosity gap
    curiosity = ("the crazy thing", "you won't believe", "nobody tells",
                 "the secret", "what if", "imagine", "here's what")
    for c in curiosity:
        if c in text_lower:
            return "curiosity", f"curiosity: '{c}'"

    # Bold statement (superlatives, contrarians)
    bold_patterns = [
        (r'\b(best|worst|biggest|most|only|never|always|every)\b', "superlative"),
        (r'\b(wrong|myth|lie|truth|actually|stop|don\'t)\b', "contrarian"),
    ]
    for pat, label in bold_patterns:
        if re.search(pat, text_lower):
            return "bold", label

    return "none", ""


def _extend_to_payoff(
    segments: list, start_idx: int, min_dur: float, max_dur: float,
    profile: GenreProfile,
) -> tuple[int, bool]:
    """Extend from hook forward until payoff or natural boundary."""
    start_time = segments[start_idx].start
    end_idx = start_idx
    found_payoff = False

    for j in range(start_idx + 1, len(segments)):
        if segments[j].end - start_time > max_dur:
            break
        end_idx = j

        # Check payoff keywords (EN + VI)
        j_text = segments[j].text.lower()
        for pk in profile.payoff_keywords:
            pk_pattern = r'(?:^|\b)' + re.escape(pk) + r'(?:\b|$)'
            if re.search(pk_pattern, j_text):
                found_payoff = True
        if not found_payoff:
            for pk in profile.payoff_keywords_vi:
                if pk in j_text:
                    found_payoff = True
                    break
                break
        if found_payoff:
            break

        # Natural pause boundary
        if j + 1 < len(segments):
            gap = segments[j + 1].start - segments[j].end
            if gap > profile.silence_gap_threshold_sec * 1.5:
                break

    return end_idx, found_payoff


def _find_energy_openings(
    analysis: AnalysisResult,
    min_dur: float,
    max_dur: float,
) -> list[RawProposal]:
    """Find points where audio energy spikes (confident delivery start)."""
    proposals: list[RawProposal] = []
    audio = analysis.audio_segments
    if len(audio) < 5:
        return proposals

    energies = [s.energy_avg for s in audio if s.has_speech]
    if not energies:
        return proposals
    mean_e = sum(energies) / len(energies)
    threshold = mean_e * 1.5

    for seg in audio:
        if seg.energy_avg >= threshold and seg.has_speech:
            start = seg.time_range.start
            snapped = _snap_to_sentences(
                TimeRange(start, start + (min_dur + max_dur) / 2),
                analysis.transcript, min_dur, max_dur,
            )
            if snapped:
                proposals.append(RawProposal(
                    time_range=snapped,
                    source="hook_energy",
                    reason=f"Energy spike opening at {start:.1f}s "
                           f"(energy={seg.energy_avg:.3f}, mean={mean_e:.3f})",
                    intent_hint="hook",
                    priority=2,
                ))

    return proposals


# ══════════════════════════════════════════════════════════════════════════
# PASS 2: STORY CANDIDATES
# ══════════════════════════════════════════════════════════════════════════

def _pass_stories(
    analysis: AnalysisResult,
    min_dur: float,
    max_dur: float,
    profile: GenreProfile,
    semantic_ctx,
) -> list[RawProposal]:
    """Find segments with narrative structure — setup → development → payoff.

    Sub-strategies:
    A. Narrative arcs from semantic layer (V2)
    B. Topic-aligned complete segments
    C. Pause-bounded coherent groups (original topic strategy)
    """
    proposals: list[RawProposal] = []

    # A. Narrative arcs from semantic layer
    if semantic_ctx and not getattr(semantic_ctx, 'is_empty', True):
        for arc in getattr(semantic_ctx, 'narrative_arcs', []):
            # Full arc as story clip
            if min_dur <= arc.time_range.duration <= max_dur:
                proposals.append(RawProposal(
                    time_range=arc.time_range,
                    source="story_full_arc",
                    reason=f"Narrative arc: {len(arc.stages)} stages, "
                           f"completeness={arc.completeness:.0%}",
                    intent_hint="story",
                    priority=2,
                ))

            # Climax-centered story clip
            if "climax" in arc.stages:
                cr = arc.stages["climax"]
                pad = min(10.0, cr.start)
                clip_start = max(0.0, cr.start - pad)
                clip_end = min(cr.end + 5.0, arc.time_range.end)
                dur = clip_end - clip_start
                if min_dur <= dur <= max_dur:
                    proposals.append(RawProposal(
                        time_range=TimeRange(clip_start, clip_end),
                        source="story_climax",
                        reason=f"Story climax at {cr.start:.1f}s",
                        intent_hint="story",
                        priority=2,
                    ))

    # B. Topic-aligned segments
    if semantic_ctx:
        for topic in getattr(semantic_ctx, 'topic_segments', []):
            if min_dur <= topic.time_range.duration <= max_dur:
                proposals.append(RawProposal(
                    time_range=topic.time_range,
                    source="story_topic",
                    reason=f"Topic: '{topic.topic_label}' "
                           f"(coherence={topic.coherence_score:.2f})",
                    intent_hint="story",
                    priority=3,
                ))

    # C. Pause-bounded groups (original topic segmentation)
    if analysis.transcript:
        pause_proposals = _propose_pause_groups(
            analysis.transcript, min_dur, max_dur, profile,
        )
        proposals.extend(pause_proposals)

    return proposals


def _propose_pause_groups(
    segments: list, min_dur: float, max_dur: float,
    profile: GenreProfile,
) -> list[RawProposal]:
    """Group transcript by pause boundaries (original v1 topic strategy)."""
    boundaries = _find_pause_boundaries(segments, profile.silence_gap_threshold_sec)
    groups = _group_by_boundaries(segments, boundaries)

    proposals: list[RawProposal] = []
    for group in groups:
        if not group:
            continue
        start = group[0].start
        end = group[-1].end
        duration = end - start

        if duration < min_dur:
            continue
        if duration <= max_dur:
            proposals.append(RawProposal(
                time_range=TimeRange(start=start, end=end),
                source="story_pause_group",
                reason=f"Pause group: {len(group)} sentences, {duration:.1f}s",
                intent_hint="story",
                priority=4,
            ))
        else:
            subs = _split_long_group(group, min_dur, max_dur)
            proposals.extend(subs)

    return proposals


# ══════════════════════════════════════════════════════════════════════════
# PASS 3: EMOTIONAL SPIKE CANDIDATES
# ══════════════════════════════════════════════════════════════════════════

def _pass_emotional(
    analysis: AnalysisResult,
    min_dur: float,
    max_dur: float,
    profile: GenreProfile,
    semantic_ctx,
) -> list[RawProposal]:
    """Find emotional intensity peaks — viral moments, reactions, conflicts.

    Sub-strategies:
    A. Semantic emotional spikes (V2)
    B. Audio energy clusters (high-energy speech windows)
    C. Scene-based visual highlights (high motion + person)
    """
    proposals: list[RawProposal] = []
    target_dur = (min_dur + max_dur) / 2

    # A. Semantic emotional spikes
    if semantic_ctx and getattr(semantic_ctx, 'has_emotions', False):
        for spike in getattr(semantic_ctx, 'emotional_spikes', []):
            if spike.intensity < T.emotional_spike_min_intensity:
                continue

            # Position peak at 40% of clip
            hook_portion = target_dur * 0.4
            clip_start = max(0.0, spike.peak_time - hook_portion)
            clip_end = spike.peak_time + target_dur * 0.6

            if clip_end - clip_start < min_dur:
                clip_end = clip_start + min_dur
            elif clip_end - clip_start > max_dur:
                clip_end = clip_start + max_dur

            # Snap to sentences
            if analysis.transcript:
                clip_start, clip_end = _snap_range_to_sentences(
                    clip_start, clip_end, analysis.transcript, min_dur, max_dur,
                )

            dur = clip_end - clip_start
            if min_dur <= dur <= max_dur:
                proposals.append(RawProposal(
                    time_range=TimeRange(clip_start, clip_end),
                    source="emotional_spike",
                    reason=f"Emotional peak: {spike.emotion_type} "
                           f"intensity={spike.intensity:.2f} at {spike.peak_time:.1f}s",
                    intent_hint="emotional",
                    priority=2,
                ))

    # B. Audio energy clusters
    energy_proposals = _find_energy_clusters(analysis, min_dur, max_dur)
    proposals.extend(energy_proposals)

    # C. Scene-based visual highlights
    if analysis.scenes and not analysis.transcript:
        scene_proposals = _find_visual_highlights(analysis, min_dur, max_dur)
        proposals.extend(scene_proposals)

    return proposals


def _find_energy_clusters(
    analysis: AnalysisResult,
    min_dur: float,
    max_dur: float,
) -> list[RawProposal]:
    """Find clusters of high-energy audio segments."""
    audio = analysis.audio_segments
    speech_segs = [s for s in audio if s.has_speech]
    if len(speech_segs) < 3:
        return []

    mean_e = sum(s.energy_avg for s in speech_segs) / len(speech_segs)
    threshold = mean_e * 1.3

    proposals: list[RawProposal] = []
    cluster_start = None
    cluster_end = None

    for seg in speech_segs:
        if seg.energy_avg >= threshold:
            if cluster_start is None:
                cluster_start = seg.time_range.start
            cluster_end = seg.time_range.end
        else:
            if cluster_start is not None:
                dur = cluster_end - cluster_start
                if dur >= min_dur * 0.5:
                    snapped = _snap_to_sentences(
                        TimeRange(cluster_start, cluster_end),
                        analysis.transcript, min_dur, max_dur,
                    )
                    if snapped:
                        proposals.append(RawProposal(
                            time_range=snapped,
                            source="emotional_energy_cluster",
                            reason=f"High energy cluster {cluster_start:.1f}-{cluster_end:.1f}s",
                            intent_hint="emotional",
                            priority=3,
                        ))
                cluster_start = None
                cluster_end = None

    # Trailing cluster
    if cluster_start is not None and cluster_end is not None:
        dur = cluster_end - cluster_start
        if dur >= min_dur * 0.5:
            snapped = _snap_to_sentences(
                TimeRange(cluster_start, cluster_end),
                analysis.transcript, min_dur, max_dur,
            )
            if snapped:
                proposals.append(RawProposal(
                    time_range=snapped,
                    source="emotional_energy_cluster",
                    reason=f"High energy cluster {cluster_start:.1f}-{cluster_end:.1f}s",
                    intent_hint="emotional",
                    priority=3,
                ))

    return proposals


def _find_visual_highlights(
    analysis: AnalysisResult,
    min_dur: float,
    max_dur: float,
) -> list[RawProposal]:
    """Scene-based visual highlights when no transcript available."""
    scenes = analysis.scenes
    proposals: list[RawProposal] = []
    i = 0
    while i < len(scenes):
        start = scenes[i].time_range.start
        end = scenes[i].time_range.end
        j = i + 1
        while j < len(scenes) and scenes[j].time_range.end - start <= max_dur:
            end = scenes[j].time_range.end
            j += 1
        end = min(end, start + max_dur)
        if end - start >= min_dur:
            proposals.append(RawProposal(
                time_range=TimeRange(start, end),
                source="emotional_visual",
                reason=f"Visual highlight: {j-i} scenes, {end-start:.1f}s",
                intent_hint="emotional",
                priority=5,
            ))
        i = max(i + 1, i + (j - i + 1) // 2)

    return proposals


# ══════════════════════════════════════════════════════════════════════════
# PASS 4: DENSE INFO CANDIDATES
# ══════════════════════════════════════════════════════════════════════════

def _pass_dense_info(
    analysis: AnalysisResult,
    min_dur: float,
    max_dur: float,
    profile: GenreProfile,
) -> list[RawProposal]:
    """Find segments with high information density — many unique concepts.

    Sub-strategies:
    A. Sliding window concept density scoring
    B. Scene+transcript hybrid (visual context + narration)
    """
    proposals: list[RawProposal] = []

    # A. Concept density sliding window
    if analysis.transcript:
        density_proposals = _find_dense_windows(
            analysis.transcript, min_dur, max_dur,
        )
        proposals.extend(density_proposals)

    # B. Scene+transcript hybrid
    if analysis.scenes and analysis.transcript:
        hybrid = _propose_hybrid_scene_transcript(
            analysis, min_dur, max_dur, profile,
        )
        proposals.extend(hybrid)

    return proposals


def _find_dense_windows(
    transcript: list[TranscriptSegment],
    min_dur: float,
    max_dur: float,
) -> list[RawProposal]:
    """Find transcript windows with highest information density.

    Density = unique_concepts / word_count (normalized).
    Slides a window across transcript, scores each position.
    Returns top-N densest non-overlapping windows.
    """
    from cutclipshort.editorial.semantic_scorer import _extract_concepts

    if len(transcript) < 3:
        return []

    target_dur = (min_dur + max_dur) / 2
    proposals: list[RawProposal] = []
    scored_windows: list[tuple[float, TimeRange, float]] = []  # (density, range, concepts)

    # Sliding window
    for i in range(len(transcript)):
        start = transcript[i].start
        text_parts: list[str] = []
        j = i

        while j < len(transcript) and transcript[j].end - start <= max_dur:
            text_parts.append(transcript[j].text)
            j += 1

        end = transcript[min(j, len(transcript)) - 1].end
        duration = max(0.1, end - start)
        if duration < min_dur:
            continue

        full_text = " ".join(text_parts)
        words = full_text.split()
        word_count = len(words)
        if word_count < 10:
            continue

        concepts = _extract_concepts(full_text)
        concept_count = len(concepts)

        # Density: unique concepts per word (higher = more informative)
        density = concept_count / word_count

        # Words per second (ideal: 2-3 wps)
        wps = word_count / duration
        wps_bonus = 1.0 if 2.0 <= wps <= 3.5 else 0.7

        final_score = density * wps_bonus
        scored_windows.append((final_score, TimeRange(start, end), concept_count))

    # Sort by density, take top non-overlapping
    scored_windows.sort(key=lambda x: x[0], reverse=True)

    kept: list[TimeRange] = []
    for score, tr, concepts in scored_windows:
        if len(kept) >= 8:
            break
        # Check overlap with already kept
        overlaps = any(
            tr.overlap_duration(k) / min(tr.duration, k.duration) > T.temporal_overlap_max
            for k in kept
        )
        if overlaps:
            continue

        kept.append(tr)
        proposals.append(RawProposal(
            time_range=tr,
            source="dense_info",
            reason=f"Dense info: {concepts} concepts, "
                   f"density={score:.3f}, {tr.duration:.1f}s",
            intent_hint="dense_info",
            priority=3,
        ))

    return proposals


# ══════════════════════════════════════════════════════════════════════════
# POST: COVERAGE GAP SCANNER
# ══════════════════════════════════════════════════════════════════════════

def _scan_coverage_gaps(
    analysis: AnalysisResult,
    existing_proposals: list[RawProposal],
    min_dur: float,
    max_dur: float,
    source_duration: float,
    profile: GenreProfile,
) -> list[RawProposal]:
    """Ensure full video coverage — generate proposals for uncovered regions.

    Two-pass approach:
    1. Fine-grained zone scan (zone_size = max_dur) — detects ALL gaps
    2. For each gap with content, generate a proposal

    Target: every zone with speech/visual content has ≥1 proposal.
    """
    if source_duration < min_dur * 2:
        return []

    # Fine-grained zones: each zone = max_dur (ensures full coverage)
    zone_size = max(min_dur * 2, min(max_dur, source_duration * 0.15))
    zone_count = max(3, int(source_duration / zone_size) + 1)
    zone_size = source_duration / zone_count

    proposals: list[RawProposal] = []
    covered_zones = 0
    total_content_zones = 0

    for zone_idx in range(zone_count):
        zone_start = zone_idx * zone_size
        zone_end = min((zone_idx + 1) * zone_size, source_duration)
        zone_range = TimeRange(zone_start, zone_end)

        # Check content in zone
        has_speech = any(
            s.time_range.overlaps(zone_range) and s.has_speech
            for s in analysis.audio_segments
        )
        has_scenes = any(
            s.time_range.overlaps(zone_range)
            for s in analysis.scenes
        )
        if not has_speech and not has_scenes:
            continue  # Empty zone — no content to cover

        total_content_zones += 1

        # Check existing coverage
        coverage = sum(
            p.time_range.overlap_duration(zone_range)
            for p in existing_proposals
        )
        coverage_ratio = coverage / max(1.0, zone_range.duration)

        if coverage_ratio >= T.coverage_gap_min_ratio:
            covered_zones += 1
            continue  # Zone adequately covered

        # Generate gap-filling proposal
        gap_proposal = _fill_gap(
            analysis, zone_range, zone_idx, zone_count,
            min_dur, max_dur, coverage_ratio,
        )
        if gap_proposal:
            proposals.append(gap_proposal)
            covered_zones += 1

    coverage_pct = covered_zones / max(1, total_content_zones) * 100
    logger.info(
        "Coverage scan: %d/%d content zones covered (%.0f%%), %d gap proposals",
        covered_zones, total_content_zones, coverage_pct, len(proposals),
    )
    return proposals


def _fill_gap(
    analysis: AnalysisResult,
    zone_range: TimeRange,
    zone_idx: int,
    zone_count: int,
    min_dur: float,
    max_dur: float,
    coverage_ratio: float,
) -> RawProposal | None:
    """Generate a single gap-filling proposal for an uncovered zone."""
    # Try transcript-based first
    if analysis.transcript:
        in_zone = [
            s for s in analysis.transcript
            if s.time_range.overlaps(zone_range)
        ]
        if in_zone:
            gap_start = in_zone[0].start
            gap_end = gap_start + min(max_dur, zone_range.duration)
            for s in in_zone:
                if s.end <= gap_end and s.end - gap_start >= min_dur:
                    gap_end = s.end

            if gap_end - gap_start >= min_dur:
                return RawProposal(
                    time_range=TimeRange(gap_start, gap_end),
                    source="coverage_gap",
                    reason=(
                        f"Coverage gap zone {zone_idx+1}/{zone_count} "
                        f"({zone_range.start:.0f}-{zone_range.end:.0f}s, "
                        f"was {coverage_ratio:.0%} covered)"
                    ),
                    intent_hint="",
                    priority=6,
                )

    # Fallback: scene-based
    zone_scenes = [
        s for s in analysis.scenes
        if s.time_range.overlaps(zone_range)
    ]
    if zone_scenes:
        gap_start = zone_scenes[0].time_range.start
        gap_end = min(zone_scenes[-1].time_range.end, gap_start + max_dur)
        if gap_end - gap_start >= min_dur:
            return RawProposal(
                time_range=TimeRange(gap_start, gap_end),
                source="coverage_gap_visual",
                reason=f"Visual gap zone {zone_idx+1}/{zone_count}",
                intent_hint="",
                priority=6,
            )

    return None


# ══════════════════════════════════════════════════════════════════════════
# POST: SEMANTIC DEDUPLICATION
# ══════════════════════════════════════════════════════════════════════════

def _semantic_deduplicate(
    proposals: list[RawProposal],
    transcript: list[TranscriptSegment],
) -> list[RawProposal]:
    """Remove content-redundant proposals using semantic overlap.

    Two proposals are duplicates if:
    1. Time overlap > 40% (temporal dedup), OR
    2. Shared transcript text > 60% (semantic dedup)

    Higher-priority proposals survive over lower-priority ones.
    """
    from cutclipshort.editorial.semantic_scorer import _extract_concepts

    if not proposals:
        return []

    # Sort by priority (lower = higher priority), then score potential
    sorted_props = sorted(
        proposals,
        key=lambda p: (p.priority, p.time_range.start),
    )

    # Pre-compute concept sets for each proposal
    prop_concepts: dict[int, set[str]] = {}
    for idx, prop in enumerate(sorted_props):
        # Get transcript text within this proposal's time range
        text_parts = [
            s.text for s in transcript
            if s.time_range.overlaps(prop.time_range)
        ] if transcript else []
        full_text = " ".join(text_parts)
        prop_concepts[idx] = _extract_concepts(full_text) if full_text else set()

    kept: list[RawProposal] = []
    kept_indices: list[int] = []

    for idx, prop in enumerate(sorted_props):
        is_dup = False

        for kept_idx in kept_indices:
            existing = sorted_props[kept_idx]

            # Check 1: Temporal overlap > 40%
            overlap = prop.time_range.overlap_duration(existing.time_range)
            shorter = min(prop.time_range.duration, existing.time_range.duration)
            if shorter > 0 and overlap / shorter > T.temporal_overlap_max:
                is_dup = True
                break

            # Check 2: Semantic overlap > threshold
            concepts_a = prop_concepts[idx]
            concepts_b = prop_concepts[kept_idx]
            if concepts_a and concepts_b:
                shared = len(concepts_a & concepts_b)
                smaller = min(len(concepts_a), len(concepts_b))
                if smaller > 0 and shared / smaller > T.semantic_overlap_max:
                    is_dup = True
                    break

        if not is_dup:
            kept.append(prop)
            kept_indices.append(idx)

    return kept


# ══════════════════════════════════════════════════════════════════════════
# HELPER: Hybrid Scene+Transcript (from v1, used by Pass 4)
# ══════════════════════════════════════════════════════════════════════════

def _propose_hybrid_scene_transcript(
    analysis: AnalysisResult,
    min_dur: float,
    max_dur: float,
    profile: GenreProfile,
) -> list[RawProposal]:
    """Scene boundaries + transcript density = smart info segments."""
    scenes = analysis.scenes
    transcript = analysis.transcript
    if not scenes:
        return []

    proposals: list[RawProposal] = []
    target_dur = (min_dur + max_dur) / 2

    for start_idx in range(len(scenes)):
        start_time = scenes[start_idx].time_range.start
        best_end_time = scenes[start_idx].time_range.end

        for end_idx in range(start_idx + 1, len(scenes)):
            end_time = scenes[end_idx].time_range.end
            if end_time - start_time > max_dur:
                break
            if end_time - start_time >= min_dur:
                if abs(end_time - start_time - target_dur) < abs(best_end_time - start_time - target_dur):
                    best_end_time = end_time

        duration = best_end_time - start_time
        if duration < min_dur:
            continue

        clip_range = TimeRange(start=start_time, end=best_end_time)
        speech_segs = [s for s in transcript if s.time_range.overlaps(clip_range)]
        speech_ratio = sum(
            s.time_range.overlap_duration(clip_range) for s in speech_segs
        ) / max(1.0, duration)

        if speech_ratio > T.speech_ratio_min_for_gap_fill and duration <= max_dur:
            proposals.append(RawProposal(
                time_range=clip_range,
                source="dense_hybrid",
                reason=f"Scene+speech: {speech_ratio:.0%} speech, {duration:.1f}s",
                intent_hint="dense_info",
                priority=4,
            ))

    return proposals


# ══════════════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ══════════════════════════════════════════════════════════════════════════

def _find_pause_boundaries(
    segments: list, gap_threshold: float,
) -> list[float]:
    """Find timestamps where significant pauses occur between sentences."""
    boundaries: list[float] = []
    for i in range(1, len(segments)):
        gap = segments[i].start - segments[i - 1].end
        if gap >= gap_threshold:
            boundaries.append(segments[i].start)
    return boundaries


def _group_by_boundaries(
    segments: list, boundaries: list[float],
) -> list[list]:
    """Split segments into groups at boundary timestamps."""
    if not boundaries:
        return [list(segments)]

    groups: list[list] = []
    current: list = []
    b_idx = 0
    for seg in segments:
        if b_idx < len(boundaries) and seg.start >= boundaries[b_idx]:
            if current:
                groups.append(current)
            current = [seg]
            b_idx += 1
        else:
            current.append(seg)
    if current:
        groups.append(current)
    return groups


def _split_long_group(
    group: list, min_dur: float, max_dur: float,
) -> list[RawProposal]:
    """Split oversized group at sentence edges."""
    proposals: list[RawProposal] = []
    target = (min_dur + max_dur) / 2
    i = 0
    while i < len(group):
        start_time = group[i].start
        j = i
        while j < len(group) and group[j].end - start_time <= target:
            j += 1
        if j == i:
            j = i + 1
        end_time = group[min(j, len(group)) - 1].end
        if end_time - start_time >= min_dur:
            proposals.append(RawProposal(
                time_range=TimeRange(start=start_time, end=end_time),
                source="story_pause_sub",
                reason=f"Sub-segment: {j-i} sentences, {end_time-start_time:.1f}s",
                intent_hint="story",
                priority=4,
            ))
        i += max(1, (j - i) * 2 // 3)
    return proposals


def _snap_to_sentences(
    rough_range: TimeRange,
    transcript: list,
    min_dur: float,
    max_dur: float,
) -> TimeRange | None:
    """Snap a rough time range to nearest sentence boundaries."""
    if not transcript:
        return rough_range if rough_range.duration >= min_dur else None

    best_start_seg = None
    best_start_dist = float("inf")
    for seg in transcript:
        if seg.start <= rough_range.start + 1.0:
            dist = abs(rough_range.start - seg.start)
            if dist < best_start_dist:
                best_start_dist = dist
                best_start_seg = seg

    best_end_seg = None
    best_end_dist = float("inf")
    for seg in transcript:
        if seg.end >= rough_range.end - 1.0:
            dist = abs(seg.end - rough_range.end)
            if dist < best_end_dist:
                best_end_dist = dist
                best_end_seg = seg

    if not best_start_seg and transcript:
        best_start_seg = transcript[0]
    if not best_end_seg and transcript:
        best_end_seg = transcript[-1]
    if not best_start_seg or not best_end_seg:
        return None

    start = best_start_seg.start
    end = best_end_seg.end
    if start >= end:
        return None
    if end - start < min_dur:
        for seg in transcript:
            if seg.start > end:
                end = seg.end
                if end - start >= min_dur:
                    break
    if end - start > max_dur:
        end = start + max_dur
        for seg in reversed(transcript):
            if seg.end <= end:
                end = seg.end
                break

    duration = end - start
    if duration < min_dur:
        return None
    return TimeRange(start=start, end=min(end, start + max_dur))


def _snap_range_to_sentences(
    start: float, end: float, transcript: list,
    min_dur: float, max_dur: float,
) -> tuple[float, float]:
    """Snap start/end to nearest sentence boundaries."""
    best_start = start
    best_start_dist = float('inf')
    for seg in transcript:
        dist = abs(seg.start - start)
        if dist < best_start_dist and seg.start <= start + 2.0:
            best_start = seg.start
            best_start_dist = dist

    best_end = end
    best_end_dist = float('inf')
    for seg in transcript:
        dist = abs(seg.end - end)
        if dist < best_end_dist and seg.end >= end - 2.0:
            best_end = seg.end
            best_end_dist = dist

    duration = best_end - best_start
    if duration < min_dur:
        best_end = best_start + min_dur
    elif duration > max_dur:
        best_end = best_start + max_dur

    return best_start, best_end


# ══════════════════════════════════════════════════════════════════════════
# PASS 5: PAYOFF CANDIDATES (resolution, conclusion, satisfying ending)
# ══════════════════════════════════════════════════════════════════════════

def _pass_payoff(
    analysis: AnalysisResult, min_dur: float, max_dur: float,
    profile: GenreProfile, semantic_ctx: "SemanticContext | None",
) -> list[RawProposal]:
    """Find segments with strong payoff — conclusions, resolutions, reveals."""
    proposals: list[RawProposal] = []
    transcript = analysis.transcript
    if not transcript:
        return proposals

    try:
        from cutclipshort.editorial.vocabulary.en import RESOLUTION_WORDS
    except ImportError:
        RESOLUTION_WORDS = frozenset()
    try:
        from cutclipshort.editorial.vocabulary.vi import RESOLUTION_WORDS as VI_RES
        all_res = RESOLUTION_WORDS | VI_RES
    except (ImportError, AttributeError):
        all_res = RESOLUTION_WORDS

    # Strategy A: Semantic narrative resolutions
    if semantic_ctx and hasattr(semantic_ctx, 'narrative_arcs'):
        for arc in semantic_ctx.narrative_arcs:
            stages = arc.stages or {}
            if "resolution" in stages:
                res_range = stages["resolution"]
                s, e = _snap_range_to_sentences(
                    res_range.start, res_range.end, transcript, min_dur, max_dur,
                )
                if min_dur <= e - s <= max_dur:
                    proposals.append(RawProposal(
                        time_range=TimeRange(s, e),
                        source="payoff_resolution",
                        reason=f"Narrative resolution from arc #{arc.arc_id}",
                        intent_hint="payoff", priority=2,
                    ))

    # Strategy B: Resolution vocabulary in final third of video
    source_dur = analysis.source.duration_sec
    final_third_start = source_dur * 0.6
    final_segs = [s for s in transcript if s.start >= final_third_start]
    for i, seg in enumerate(final_segs):
        text_lower = seg.text.lower() if seg.text else ""
        hits = sum(1 for w in all_res if w in text_lower)
        if hits >= 2:
            start = seg.start
            end = min(seg.start + max_dur, source_dur)
            s, e = _snap_range_to_sentences(start, end, transcript, min_dur, max_dur)
            if min_dur <= e - s <= max_dur:
                proposals.append(RawProposal(
                    time_range=TimeRange(s, e),
                    source="payoff_vocabulary",
                    reason=f"Resolution vocabulary ({hits} markers) in final third",
                    intent_hint="payoff", priority=3,
                ))

    logger.debug("Pass 5 (PAYOFF): %d proposals", len(proposals))
    return proposals


# ══════════════════════════════════════════════════════════════════════════
# PASS 6: LOOP CANDIDATES (short, satisfying, replay-worthy)
# ══════════════════════════════════════════════════════════════════════════

def _pass_loop(
    analysis: AnalysisResult, min_dur: float, max_dur: float,
    profile: GenreProfile, semantic_ctx: "SemanticContext | None",
) -> list[RawProposal]:
    """Find short, visually compelling, replay-worthy moments."""
    proposals: list[RawProposal] = []
    scenes = analysis.scenes
    if not scenes:
        return proposals

    # LOOP clips are SHORT (5-20s) and ACTION-driven
    loop_max = min(max_dur, 20.0)
    loop_min = max(min_dur, 5.0)

    # Strategy A: High-motion scene clusters (short bursts)
    for i in range(len(scenes)):
        sc = scenes[i]
        tr = sc.time_range
        motion = getattr(sc, 'motion_avg', 0.5)
        dur = tr.duration
        if motion > 0.6 and loop_min <= dur <= loop_max:
            proposals.append(RawProposal(
                time_range=tr,
                source="loop_motion",
                reason=f"High-motion scene (motion={motion:.2f}, {dur:.1f}s)",
                intent_hint="loop", priority=3,
            ))

    # Strategy B: Scene-pairs forming short visual sequences
    for i in range(len(scenes) - 1):
        sc1, sc2 = scenes[i], scenes[i + 1]
        dur = sc2.time_range.end - sc1.time_range.start
        if loop_min <= dur <= loop_max:
            m1 = getattr(sc1, 'motion_avg', 0.5)
            m2 = getattr(sc2, 'motion_avg', 0.5)
            avg_motion = (m1 + m2) / 2
            if avg_motion > 0.5:
                proposals.append(RawProposal(
                    time_range=TimeRange(sc1.time_range.start, sc2.time_range.end),
                    source="loop_scene_pair",
                    reason=f"Visual sequence ({dur:.1f}s, motion={avg_motion:.2f})",
                    intent_hint="loop", priority=4,
                ))

    # Strategy C: Emotional spike + short = perfect loop
    if semantic_ctx and hasattr(semantic_ctx, 'emotional_spikes'):
        for spike in semantic_ctx.emotional_spikes:
            dur = spike.time_range.duration
            if loop_min <= dur <= loop_max and spike.intensity > 0.5:
                proposals.append(RawProposal(
                    time_range=spike.time_range,
                    source="loop_spike",
                    reason=f"Emotional spike loop ({spike.emotion_type}, intensity={spike.intensity:.2f})",
                    intent_hint="loop", priority=3,
                ))

    logger.debug("Pass 6 (LOOP): %d proposals", len(proposals))
    return proposals


# ══════════════════════════════════════════════════════════════════════════
# CANDIDATE DIVERSITY MANAGER
# ══════════════════════════════════════════════════════════════════════════

class CandidateDiversityManager:
    """Clusters similar proposals, keeps best per cluster, enforces overlap limit.

    Steps:
    1. Build overlap graph (temporal + semantic)
    2. Cluster connected proposals (Union-Find)
    3. Keep highest-priority proposal per cluster
    4. Enforce max overlap constraint (no 2 candidates overlap >70%)
    5. Assign cluster_id to each surviving proposal

    This replaces the old _semantic_deduplicate function.
    """

    def __init__(self, max_overlap_ratio: float = 0.70, min_output: int = 10) -> None:
        self._max_overlap = max_overlap_ratio
        self._min_output = min_output  # Minimum proposals to keep
        self._cluster_count = 0

    @property
    def cluster_count(self) -> int:
        """Number of clusters after enforcement."""
        return self._cluster_count

    def enforce(
        self, proposals: list[RawProposal], transcript: list,
    ) -> list[RawProposal]:
        """Run full diversity pipeline: cluster → select → overlap check.

        Uses spatial bucketing for O(n·k) instead of O(n²) when n>200.
        """
        if not proposals:
            return []

        from cutclipshort.editorial.thresholds import T

        n = len(proposals)
        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        # Extract concept sets for semantic comparison
        concept_sets: list[set[str]] = []
        try:
            from cutclipshort.editorial.semantic_scorer import _extract_concepts
            for p in proposals:
                text = _get_proposal_text(p, transcript)
                concept_sets.append(set(_extract_concepts(text)))
        except ImportError:
            concept_sets = [set() for _ in proposals]

        temporal_thresh = getattr(T, 'temporal_overlap_max', 0.40)
        semantic_thresh = getattr(T, 'semantic_overlap_max', 0.60)

        if n <= 200:
            # Direct O(n²) — fast enough for typical use
            for i in range(n):
                for j in range(i + 1, n):
                    t_ov = _temporal_overlap_ratio(proposals[i], proposals[j])
                    s_ov = _concept_overlap_ratio(concept_sets[i], concept_sets[j])
                    if t_ov > temporal_thresh and s_ov > semantic_thresh:
                        union(i, j)
        else:
            # Spatial bucketing: only compare proposals in nearby time buckets
            # Bucket size = max proposal duration → guarantees all overlaps detected
            max_dur = max((p.time_range.duration for p in proposals), default=60)
            bucket_size = max(max_dur, 30.0)
            buckets: dict[int, list[int]] = {}
            for i, p in enumerate(proposals):
                b_start = int(p.time_range.start / bucket_size)
                b_end = int(p.time_range.end / bucket_size)
                for b in range(b_start, b_end + 1):
                    buckets.setdefault(b, []).append(i)

            compared: set[tuple[int, int]] = set()
            for members in buckets.values():
                for a_idx, i in enumerate(members):
                    for j in members[a_idx + 1:]:
                        pair = (min(i, j), max(i, j))
                        if pair in compared:
                            continue
                        compared.add(pair)
                        t_ov = _temporal_overlap_ratio(proposals[i], proposals[j])
                        s_ov = _concept_overlap_ratio(concept_sets[i], concept_sets[j])
                        if t_ov > temporal_thresh and s_ov > semantic_thresh:
                            union(i, j)

            logger.debug("Spatial clustering: %d comparisons (vs %d naive)",
                        len(compared), n * (n - 1) // 2)

        # Step 2: Group by cluster
        clusters: dict[int, list[int]] = {}
        for i in range(n):
            root = find(i)
            clusters.setdefault(root, []).append(i)

        self._cluster_count = len(clusters)

        # Step 3: Pick top N per cluster (not just 1!)
        # Large clusters may contain diverse time ranges that Union-Find
        # merged via transitive overlap chains. Keep enough for target.
        max_per_cluster = max(5, len(proposals) // max(1, len(clusters)))
        selected: list[RawProposal] = []
        for cluster_id_val, (_, members) in enumerate(sorted(clusters.items())):
            members_sorted = sorted(members, key=lambda i: proposals[i].priority)
            for rank, idx in enumerate(members_sorted[:max_per_cluster]):
                p = proposals[idx]
                tagged = RawProposal(
                    time_range=p.time_range,
                    source=p.source,
                    reason=p.reason,
                    intent_hint=p.intent_hint,
                    priority=p.priority,
                    cluster_id=cluster_id_val,
                )
                selected.append(tagged)

        # Step 4: Final overlap enforcement (no 2 > max_overlap)
        # Two-phase: strict first, then relax if not enough
        sorted_by_priority = sorted(selected, key=lambda p: p.priority)

        final: list[RawProposal] = []
        for candidate in sorted_by_priority:
            if not any(
                _temporal_overlap_ratio(candidate, kept) > self._max_overlap
                for kept in final
            ):
                final.append(candidate)

        # If we don't have enough, progressively relax overlap threshold
        if len(final) < self._min_output and len(selected) > len(final):
            remaining = [p for p in sorted_by_priority if p not in final]
            # Phase 2: allow up to 85% overlap to reach min_output
            relaxed_thresh = min(0.85, self._max_overlap + 0.15)
            for candidate in remaining:
                if len(final) >= self._min_output:
                    break
                if not any(
                    _temporal_overlap_ratio(candidate, kept) > relaxed_thresh
                    for kept in final
                ):
                    final.append(candidate)

        # Fallback: keep at least min_output or 3
        min_keep = max(3, self._min_output)
        if len(final) < min_keep and selected:
            # Last resort: take top by priority regardless of overlap
            for candidate in sorted_by_priority:
                if candidate not in final:
                    final.append(candidate)
                if len(final) >= min_keep:
                    break

        logger.info(
            "DiversityManager: %d proposals → %d clusters → %d final (max_overlap=%.0f%%)",
            n, self._cluster_count, len(final), self._max_overlap * 100,
        )
        return final


def _temporal_overlap_ratio(a: RawProposal, b: RawProposal) -> float:
    """Calculate temporal overlap ratio between two proposals."""
    overlap_start = max(a.time_range.start, b.time_range.start)
    overlap_end = min(a.time_range.end, b.time_range.end)
    overlap = max(0.0, overlap_end - overlap_start)
    shorter = min(a.time_range.duration, b.time_range.duration)
    return overlap / shorter if shorter > 0 else 0.0


def _concept_overlap_ratio(set_a: set[str], set_b: set[str]) -> float:
    """Calculate semantic overlap ratio between two concept sets."""
    if not set_a or not set_b:
        return 0.0
    shared = len(set_a & set_b)
    smaller = min(len(set_a), len(set_b))
    return shared / smaller if smaller > 0 else 0.0


def _get_proposal_text(proposal: RawProposal, transcript: list) -> str:
    """Extract speech text covered by a proposal's time range."""
    parts = []
    for seg in transcript:
        if seg.start >= proposal.time_range.start and seg.end <= proposal.time_range.end:
            parts.append(seg.text)
    return " ".join(parts)


def _assess_transcript_quality(transcript: list) -> float:
    """Score transcript quality 0.0–1.0.

    Detects:
    - Cross-segment hallucination (same text repeated across many segments)
    - Very short/empty transcripts
    - Repetitive word patterns

    Returns:
        0.0 = garbage (all hallucination), 1.0 = high quality
    """
    if not transcript:
        return 0.0

    texts = [getattr(seg, 'text', '') for seg in transcript]
    if not any(texts):
        return 0.0

    # Check cross-segment duplication
    # Normalize texts and count unique
    normalized = [t.strip().lower()[:50] for t in texts if t.strip()]
    if not normalized:
        return 0.0

    unique_ratio = len(set(normalized)) / len(normalized)

    # Check word-level repetition across all text
    all_words = " ".join(texts).lower().split()
    if len(all_words) > 10:
        from collections import Counter
        word_counts = Counter(all_words)
        top_word_freq = word_counts.most_common(1)[0][1] / len(all_words)
        # If single word is >30% of all words, it's likely hallucination
        if top_word_freq > 0.30:
            unique_ratio *= 0.3

    return min(1.0, unique_ratio)


def _pass_motion_peaks(
    analysis, min_dur: float, max_dur: float, profile,
) -> list[RawProposal]:
    """Generate candidates from motion energy peaks.

    Used as fallback when transcript quality is low (action/visual content).
    Finds high-motion segments and creates proposals around them.
    """
    from cutclipshort.types import TimeRange

    if not analysis.audio_segments:
        return []

    # Use scene boundaries as natural cut points
    scenes = analysis.scenes
    if not scenes:
        return []

    proposals = []
    # Group consecutive scenes into clips of target duration
    i = 0
    while i < len(scenes):
        start = scenes[i].time_range.start
        end = scenes[i].time_range.end

        # Extend to meet min_dur by adding consecutive scenes
        j = i + 1
        while j < len(scenes) and (end - start) < min_dur:
            end = scenes[j].time_range.end
            j += 1

        duration = end - start
        if min_dur <= duration <= max_dur:
            proposals.append(RawProposal(
                time_range=TimeRange(start=start, end=end),
                source="motion_peaks",
                reason="High visual activity scene group",
                intent_hint="hook",
                priority=len(proposals),
            ))

        # Move to next non-overlapping position
        i = j if j > i else i + 1

    logger.debug("Motion peaks: %d proposals from %d scenes", len(proposals), len(scenes))
    return proposals
