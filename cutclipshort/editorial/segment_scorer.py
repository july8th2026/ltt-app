"""Segment scorer — multi-signal composite scoring for candidate clips.

Combines hook analysis, payoff analysis, and content quality signals
into a single CandidateScore. Each signal is weighted according to
the genre profile.

Signals scored:
1. Hook strength (from hook_detector)
2. Pacing (speech rate, silence ratio, duration fit)
3. Completeness (from payoff_detector)
4. Visual quality (person presence, motion appropriateness)
5. Audio quality (energy consistency, no clipping markers)
6. Content density (word count, information density)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from cutclipshort.editorial.genre_profiles import GenreProfile
from cutclipshort.editorial.coherence import CoherenceResult, score_coherence
from cutclipshort.editorial.hook_detector import HookAnalysis, score_hook
from cutclipshort.editorial.payoff_detector import PayoffAnalysis, score_payoff
from cutclipshort.editorial.thresholds import T as _T
from cutclipshort.types import (
    AudioSegment,
    CandidateScore,
    SceneInfo,
    TimeRange,
    TranscriptSegment,
    VisualSegment,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScoredSegment:
    """A time range with detailed scoring breakdown."""
    time_range: TimeRange
    composite_score: float         # 0.0-1.0 final weighted score
    score: CandidateScore          # Standard CandidateScore for types contract

    # Detailed breakdowns
    hook: HookAnalysis
    payoff: PayoffAnalysis
    pacing_score: float
    visual_score: float
    audio_score: float
    content_density_score: float

    # Transcript coverage
    transcript_segment_ids: list[int]
    speech_text: str               # Full text of clip
    word_count: int
    speech_ratio: float            # Fraction of clip with speech

    # Reasoning
    reasoning: str

    # Genre cue details (v2)
    genre_cue_score: float = 0.0
    genre_cue_reasoning: str = ""

    # Hook-Payoff coherence (v2)
    coherence: CoherenceResult | None = None

    # V2: Intent classification and semantic context
    clip_intent: str = "unknown"
    intent_confidence: float = 0.0
    intent_reasoning: str = ""
    intent_features: dict[str, float] = field(default_factory=dict)
    semantic_context_score: float = 0.0
    topic_label: str = ""
    emotional_intensity: float = 0.0
    narrative_completeness: float = 0.0

    # V3: Generation tracking
    generation_reason: str = ""    # Why this candidate was proposed
    cluster_id: int = -1           # Diversity cluster assignment


def score_segment(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
    visual_segments: list[VisualSegment],
    scenes: list[SceneInfo],
    profile: GenreProfile,
    semantic_ctx: "SemanticContext | None" = None,
) -> ScoredSegment:
    """Score a candidate time range across all editorial dimensions.

    This is the central scoring function. It does NOT decide whether
    something is a candidate — it scores an already-proposed segment.
    """
    # 1. Hook analysis
    hook = score_hook(time_range, transcript, audio_segments, profile)

    # 2. Payoff analysis
    payoff = score_payoff(time_range, transcript, audio_segments, profile)

    # 3. Pacing score
    pacing_score, transcript_ids, speech_text, word_count, speech_ratio = (
        _score_pacing(time_range, transcript, audio_segments, profile)
    )

    # 4. Visual quality
    visual_score = _score_visual(time_range, visual_segments, scenes, profile)

    # 5. Audio quality
    audio_score = _score_audio(time_range, audio_segments, profile)

    # 6. Content density
    content_density = _score_content_density(
        time_range, word_count, speech_ratio, profile,
    )

    # 7. Genre-specific content cues (additive bonus)
    genre_cue_score, genre_cue_reasoning = _score_genre_cues(
        time_range, transcript, audio_segments, profile,
    )

    # 8. Hook-Payoff coherence (v2)
    coherence = score_coherence(hook, payoff, time_range, transcript)

    # 9. Semantic analysis (v4: NLP-enhanced scoring)
    from cutclipshort.editorial.semantic_scorer import (
        analyze_text as semantic_analyze,
        score_hook_semantic,
        score_coherence_semantic,
    )
    semantic = semantic_analyze(speech_text)
    semantic_hook_score = score_hook_semantic(hook.hook_text)

    # Semantic coherence: vocabulary overlap between hook and payoff
    payoff_start = time_range.start + time_range.duration * 0.6
    payoff_segs = [
        s for s in transcript
        if s.time_range.overlaps(TimeRange(start=payoff_start, end=time_range.end))
    ]
    payoff_text = " ".join(s.text.strip() for s in payoff_segs)
    semantic_coherence = score_coherence_semantic(
        hook.hook_text, speech_text, payoff_text,
    )

    # 10. [V2] Semantic context enrichment
    semantic_context_score = 0.0
    topic_label_v2 = ""
    emotional_intensity_v2 = 0.0
    narrative_comp_v2 = 0.0
    clip_intent = "unknown"
    intent_confidence = 0.0
    intent_reasoning = ""

    if semantic_ctx is not None and not getattr(semantic_ctx, 'is_empty', True):
        semantic_context_score, topic_label_v2, emotional_intensity_v2, narrative_comp_v2 = (
            _score_semantic_context(time_range, semantic_ctx)
        )

    # Weighted composite from genre profile
    w = profile.weights
    base_composite = (
        hook.score * w.hook_strength
        + pacing_score * w.pacing
        + payoff.score * w.completeness
        + visual_score * w.visual_quality
        + audio_score * w.audio_quality
        + content_density * w.content_density
    )

    # Coherence modulates composite (v4: combines structural + semantic)
    # Structural coherence: regex-based hook→payoff resolution (reliable)
    # Semantic coherence: vocabulary overlap (softer signal)
    _STRUCTURAL_COHERENCE_WEIGHT = 0.6
    _SEMANTIC_COHERENCE_WEIGHT = 0.4
    _COHERENCE_CENTER = 0.4       # Score below this = penalty, above = bonus
    _COHERENCE_SENSITIVITY = 0.25  # How much coherence affects composite
    structural_coherence = coherence.score
    blended_coherence = (
        structural_coherence * _STRUCTURAL_COHERENCE_WEIGHT
        + semantic_coherence * _SEMANTIC_COHERENCE_WEIGHT
    )
    coherence_modifier = (blended_coherence - _COHERENCE_CENTER) * _COHERENCE_SENSITIVITY

    # Genre cue bonus: up to +20%
    genre_bonus = genre_cue_score * 0.20

    # Semantic bonus: up to +10% for high-quality text
    semantic_bonus = 0.0
    if semantic.semantic_score > _T.semantic_score_bonus_threshold:
        semantic_bonus = (semantic.semantic_score - _T.semantic_score_bonus_threshold) * 0.25  # Max +0.10

    # Semantic hook bonus: boost hooks with strong semantic signals
    hook_semantic_bonus = 0.0
    if semantic_hook_score > _T.semantic_hook_bonus_threshold:
        hook_semantic_bonus = (semantic_hook_score - _T.semantic_hook_bonus_threshold) * 0.10  # Max +0.05

    # Filler penalty: high filler ratio = unprofessional
    filler_penalty = 0.0
    if semantic.filler_ratio > _T.filler_heavy_threshold:
        filler_penalty = -0.05
    elif semantic.filler_ratio > _T.filler_moderate_threshold:
        filler_penalty = -0.02

    # Hook weakness penalty: punish truly weak hooks harder
    hook_penalty = 0.0
    if hook.score < _T.hook_weak_penalty:
        hook_penalty = -0.08
    elif hook.score < _T.hook_moderate_penalty:
        hook_penalty = -0.04

    # [V2] Semantic context bonus: up to +15%
    # Formula: (score - threshold) * scale → max bonus = (1.0 - 0.3) * 0.214 = 0.15
    _SEMANTIC_CTX_THRESHOLD = 0.3
    _SEMANTIC_CTX_SCALE = 0.214  # Produces max +0.15 bonus at score=1.0
    semantic_ctx_bonus = 0.0
    if semantic_context_score > _SEMANTIC_CTX_THRESHOLD:
        semantic_ctx_bonus = (semantic_context_score - _SEMANTIC_CTX_THRESHOLD) * _SEMANTIC_CTX_SCALE

    composite = max(0.0, min(1.0,
        base_composite + genre_bonus + coherence_modifier
        + semantic_bonus + hook_semantic_bonus
        + hook_penalty + filler_penalty
        + semantic_ctx_bonus
    ))

    # 11. [V2] Intent classification (after composite, uses all signals)
    intent_features: dict[str, float] = {}
    if semantic_ctx is not None and not getattr(semantic_ctx, 'is_empty', True):
        try:
            from cutclipshort.editorial.semantic.intent_classifier import classify_intent
            clip_intent, intent_confidence, intent_reasoning, intent_features = classify_intent(
                hook_score=hook.score,
                payoff_score=payoff.score,
                coherence_resolution_found=(
                    coherence.resolution_found if coherence else False
                ),
                emotional_intensity=emotional_intensity_v2,
                narrative_completeness=narrative_comp_v2,
                speech_text=speech_text,
                genre_cue_score=genre_cue_score,
                pacing_score=pacing_score,
                content_density=content_density,
                audio_energy=audio_score,
                motion_intensity=visual_score,
            )
        except Exception as e:
            logger.warning("Intent classification failed: %s", e)
    else:
        # Run intent even without semantic context (using available signals)
        try:
            from cutclipshort.editorial.semantic.intent_classifier import classify_intent
            clip_intent, intent_confidence, intent_reasoning, intent_features = classify_intent(
                hook_score=hook.score,
                payoff_score=payoff.score,
                coherence_resolution_found=(
                    coherence.resolution_found if coherence else False
                ),
                emotional_intensity=0.0,
                narrative_completeness=0.0,
                speech_text=speech_text,
                genre_cue_score=genre_cue_score,
                pacing_score=pacing_score,
                content_density=content_density,
                audio_energy=audio_score,
                motion_intensity=visual_score,
            )
        except Exception as e:
            logger.warning("Intent classification (no semantic): %s", e)

    # 12. Retention-based scoring (intent-weighted)
    retention_score = 0.0
    retention_breakdown: dict[str, float] = {}
    try:
        from cutclipshort.editorial.scoring.retention import (
            opening_arrest, curiosity_gap, narrative_arc_score,
            payoff_satisfaction, redundancy_penalty, loop_potential,
            cut_naturalness, compute_retention_composite,
        )

        # Extract signals for retention metrics
        first_words = speech_text[:50].lower() if speech_text else ""
        _filler_starts = any(first_words.startswith(f) for f in ("um ", "uh ", "so ", "like "))

        r1, _ = opening_arrest(
            hook.score, audio_score, "?" in first_words,
            bool(re.search(r'\d', first_words)), _filler_starts,
        )
        r2, _ = curiosity_gap(
            hook.score, payoff.score, speech_text.count("?") if speech_text else 0,
            hook.score > 0.6 and payoff.score < 0.3, speech_text,
        )
        r3, _ = narrative_arc_score(
            narrative_comp_v2, coherence.score if coherence else 0.0,
            has_setup=hook.score > 0.3,
            has_development=pacing_score > 0.4,
            has_resolution=coherence.resolution_found if coherence else False,
        )
        r4, _ = payoff_satisfaction(
            payoff.score, coherence.resolution_found if coherence else False,
            audio_score, coherence.resolution_found if coherence else False,
        )
        _unique_words = len(set(speech_text.lower().split())) if speech_text else 0
        _total_words = max(1, word_count)
        r5, _ = redundancy_penalty(
            speech_text, time_range.duration, _unique_words / _total_words,
        )
        r6, _ = loop_potential(
            time_range.duration, visual_score, emotional_intensity_v2,
            word_count, payoff.score > 0.5,
        )
        # Approximate cut naturalness from speech boundaries
        _at_sentence_start = any(
            abs(s.start - time_range.start) < 0.5 for s in transcript
        ) if transcript else True
        _at_sentence_end = any(
            abs(s.end - time_range.end) < 0.5 for s in transcript
        ) if transcript else True
        r7, _ = cut_naturalness(
            starts_mid_word=not _at_sentence_start and speech_ratio > 0.5,
            ends_mid_word=not _at_sentence_end and speech_ratio > 0.5,
            starts_mid_sentence=not _at_sentence_start,
            ends_mid_sentence=not _at_sentence_end,
            boundary_snapped=_at_sentence_start and _at_sentence_end,
        )

        retention_score, retention_breakdown = compute_retention_composite(
            (r1, r2, r3, r4, r5, r6, r7), clip_intent,
        )
    except Exception as e:
        logger.debug("Retention scoring skipped: %s", e)

    # Blend retention into composite (30% retention + 70% editorial)
    _RETENTION_BLEND = 0.30
    final_composite = composite * (1.0 - _RETENTION_BLEND) + retention_score * _RETENTION_BLEND
    final_composite = max(0.0, min(1.0, final_composite))

    # Build standard CandidateScore
    candidate_score = CandidateScore(
        overall=round(final_composite, 3),
        hook_strength=round(hook.score, 3),
        pacing=round(pacing_score, 3),
        completeness=round(payoff.score, 3),
        visual_quality=round(visual_score, 3),
        audio_quality=round(audio_score, 3),
        topic_coherence=round(content_density, 3),
        semantic_richness=round(retention_score, 3),
    )

    # Assemble reasoning
    parts = [
        f"hook={hook.score:.2f}({hook.hook_type})",
        f"payoff={payoff.score:.2f}({payoff.payoff_type})",
        f"coherence={blended_coherence:.2f}",
        f"pacing={pacing_score:.2f}",
        f"visual={visual_score:.2f}",
        f"audio={audio_score:.2f}",
        f"density={content_density:.2f}",
        f"retention={retention_score:.3f}({clip_intent})",
    ]
    if genre_cue_score > _T.genre_cue_bonus_threshold:
        parts.append(f"genre_cue=+{genre_bonus:.2f}({genre_cue_reasoning})")
    if filler_penalty != 0:
        parts.append(f"filler_pen={filler_penalty:+.3f}")
    parts.append(f"composite={final_composite:.3f}")
    reasoning = " | ".join(parts)

    return ScoredSegment(
        time_range=time_range,
        composite_score=round(final_composite, 3),
        score=candidate_score,
        hook=hook,
        payoff=payoff,
        pacing_score=round(pacing_score, 3),
        visual_score=round(visual_score, 3),
        audio_score=round(audio_score, 3),
        content_density_score=round(content_density, 3),
        genre_cue_score=round(genre_cue_score, 3),
        transcript_segment_ids=transcript_ids,
        speech_text=speech_text,
        word_count=word_count,
        speech_ratio=round(speech_ratio, 3),
        genre_cue_reasoning=genre_cue_reasoning,
        reasoning=reasoning,
        coherence=coherence,
        # V2
        clip_intent=clip_intent,
        intent_confidence=round(intent_confidence, 3),
        intent_reasoning=intent_reasoning,
        intent_features=intent_features,
        semantic_context_score=round(semantic_context_score, 3),
        topic_label=topic_label_v2,
        emotional_intensity=round(emotional_intensity_v2, 3),
        narrative_completeness=round(narrative_comp_v2, 3),
    )


# ── Scoring modules (extracted to editorial/scoring/ for testability) ────

from cutclipshort.editorial.scoring.pacing import score_pacing as _score_pacing
from cutclipshort.editorial.scoring.visual import score_visual as _score_visual
from cutclipshort.editorial.scoring.audio import score_audio as _score_audio
from cutclipshort.editorial.scoring.density import score_content_density as _score_content_density


# ── Genre Cues (v2 additive bonus) ──────────────────────────────────────

def _score_genre_cues(
    time_range: TimeRange,
    transcript: list[TranscriptSegment],
    audio_segments: list[AudioSegment],
    profile: GenreProfile,
) -> tuple[float, str]:
    """Run the genre-specific cue detector for this profile's genre.

    Returns (score, reasoning) tuple. Score is 0.0-1.0.
    Only runs the detector matching the current genre — not all 5.
    """
    from cutclipshort.editorial.genre_cues import (
        detect_comedy_cues,
        detect_education_cues,
        detect_story_cues,
        detect_news_cues,
        detect_review_cues,
        detect_talking_head_cues,
        detect_podcast_cues,
        detect_interview_cues,
        detect_nature_cues,
        detect_history_cues,
        detect_action_cues,
        detect_kids_music_cues,
        detect_animation_cues,
    )

    detectors = {
        "talking_head": detect_talking_head_cues,
        "podcast": detect_podcast_cues,
        "interview": detect_interview_cues,
        "comedy": detect_comedy_cues,
        "education": detect_education_cues,
        "storytelling": detect_story_cues,
        "news_commentary": detect_news_cues,
        "review": detect_review_cues,
        "nature": detect_nature_cues,
        "history": detect_history_cues,
        "action": detect_action_cues,
        "kids_music": detect_kids_music_cues,
        "animation": detect_animation_cues,
    }

    detector = detectors.get(profile.name)
    if detector is None:
        logger.debug("No genre cue detector for '%s', skipping genre bonus", profile.name)
        return 0.0, ""

    try:
        result = detector(time_range, transcript, audio_segments)
        return result.score, result.reasoning
    except Exception as e:
        logger.warning("Genre cue detector failed for %s: %s", profile.name, e)
        return 0.0, ""


# ── [V2] Semantic Context Scoring ─────────────────────────────────────────

def _score_semantic_context(
    time_range: TimeRange,
    semantic_ctx,
) -> tuple[float, str, float, float]:
    """Score semantic context signals for a time range.

    Returns: (context_score, topic_label, emotional_intensity, narrative_completeness)
    All are bonuses. Range: 0.0-1.0.
    """
    scores: list[float] = []
    topic_label = ""
    emotional_intensity = 0.0
    narrative_comp = 0.0

    # Topic alignment: segment covers a coherent single topic
    for topic in getattr(semantic_ctx, 'topic_segments', []):
        overlap = time_range.overlap_duration(topic.time_range)
        coverage = overlap / max(1.0, time_range.duration)
        if coverage > 0.5:
            scores.append(topic.coherence_score * coverage)
            topic_label = topic.topic_label
            break

    # Narrative arc overlap
    for arc in getattr(semantic_ctx, 'narrative_arcs', []):
        if time_range.overlaps(arc.time_range):
            overlap_frac = time_range.overlap_duration(arc.time_range) / max(1.0, arc.time_range.duration)
            if overlap_frac > 0.3:
                narrative_comp = arc.completeness * overlap_frac
                scores.append(narrative_comp)

    # Emotional spike overlap
    for spike in getattr(semantic_ctx, 'emotional_spikes', []):
        if time_range.contains(spike.peak_time):
            emotional_intensity = max(emotional_intensity, spike.intensity)
            scores.append(spike.intensity * 0.8)

    # Concept cluster coverage
    for cluster in getattr(semantic_ctx, 'concept_clusters', []):
        if cluster.time_ranges:
            cluster_range = TimeRange(
                start=min(r.start for r in cluster.time_ranges),
                end=max(r.end for r in cluster.time_ranges),
            )
            if time_range.overlaps(cluster_range):
                scores.append(cluster.cohesion_score * 0.5)

    context_score = min(1.0, sum(scores) / max(1, len(scores))) if scores else 0.0
    return context_score, topic_label, emotional_intensity, narrative_comp
