"""Clip ranker V2 — multi-objective selection with coverage optimization.

V2 architecture: instead of greedy score-first, uses a 4-objective
tournament that balances quality, diversity, coverage, and intent mix.

Objectives:
1. QUALITY    — composite score (higher = better)
2. DIVERSITY  — temporal spread + hook type variety
3. COVERAGE   — full video represented, no dead zones
4. INTENT MIX — hook + story + payoff balanced set

Selection algorithm:
1. Filter: remove below-threshold + duration-invalid candidates
2. Score: compute multi-objective fitness for each candidate
3. Select: iterative tournament — pick best FITNESS, update objectives
4. Rebalance: check intent mix, swap if needed
5. Convert: ScoredSegment → CandidateClip with full metadata
"""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any

from cutclipshort.editorial.genre_profiles import GenreProfile
from cutclipshort.editorial.segment_scorer import ScoredSegment
from cutclipshort.editorial.thresholds import T
from cutclipshort.types import (
    CandidateClip,
    ContentType,
    EditConstraints,
    TimeRange,
)

logger = logging.getLogger(__name__)

# ── Thresholds ───────────────────────────────────────────────────────
MIN_VIABLE_SCORE = 0.20
MAX_OVERLAP_RATIO = 0.25
MIN_GAP_SEC = 5.0

# ── Objective weights ────────────────────────────────────────────────
W_QUALITY = 0.40     # Raw composite score
W_DIVERSITY = 0.20   # Temporal spread + hook variety
W_COVERAGE = 0.25    # Video zone coverage
W_INTENT = 0.15      # Intent balance bonus

# ── Intent mix targets ───────────────────────────────────────────────
_IDEAL_INTENT_MIX = {
    "hook": 0.25,       # ~25% hook clips — strong openers
    "story": 0.20,      # ~20% story clips — narrative arcs
    "payoff": 0.15,     # ~15% payoff clips — satisfying endings
    "shock": 0.15,      # ~15% shock clips — surprises, drama, controversy
    "insight": 0.15,    # ~15% insight clips — learnings, dense info
    "loop": 0.10,       # ~10% loop clips — replay-worthy moments
}


# ══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════

def rank_and_select(
    scored: list[ScoredSegment],
    constraints: EditConstraints,
    profile: GenreProfile,
    source_duration: float,
    learned_preferences: Any = None,
) -> list[CandidateClip]:
    """Multi-objective ranking and selection.

    Tournament-based: iteratively selects the candidate that maximizes
    the combined fitness across all 4 objectives, updating state after
    each pick (coverage map, intent counts, temporal spread).
    """
    if not scored:
        return []

    # ── Step 1: Filter ────────────────────────────────────────────
    viable = _filter_viable(scored, constraints)
    if not viable:
        viable = sorted(scored, key=lambda s: s.composite_score, reverse=True)[:3]
        logger.warning("No viable candidates, taking top %d by score", len(viable))

    # Apply objective boost from genre
    viable = _objective_rerank(viable, profile)

    logger.info("Ranker V2: %d viable from %d scored", len(viable), len(scored))

    # ── Step 2: Tournament selection ──────────────────────────────
    target = constraints.target_clip_count
    max_clips = constraints.max_clip_count

    selected = _tournament_select(
        viable, target, max_clips, source_duration, constraints,
        learned_preferences=learned_preferences,
    )

    logger.info("Tournament selected: %d clips", len(selected))

    # ── Step 3: Intent rebalance ──────────────────────────────────
    selected = _rebalance_intents(selected, viable, target)

    # ── Step 4: Final trim to target ──────────────────────────────
    selected = selected[:target]

    # ── Step 5: Convert to CandidateClip ──────────────────────────
    candidates = _to_candidate_clips(selected, profile)

    # ── Step 6: Log ───────────────────────────────────────────────
    _log_selection(candidates, scored, profile, source_duration)

    return candidates


# ══════════════════════════════════════════════════════════════════════════
# STEP 1: FILTERING
# ══════════════════════════════════════════════════════════════════════════

def _filter_viable(
    scored: list[ScoredSegment], constraints: EditConstraints,
) -> list[ScoredSegment]:
    """Remove below-threshold and duration-invalid candidates."""
    viable = []
    for s in scored:
        if s.composite_score < MIN_VIABLE_SCORE:
            continue
        dur = s.time_range.duration
        if dur < constraints.min_clip_duration_sec * 0.8:  # 20% tolerance
            continue
        if dur > constraints.max_clip_duration_sec * 1.2:
            continue
        viable.append(s)
    return viable


# ══════════════════════════════════════════════════════════════════════════
# STEP 2: TOURNAMENT SELECTION
# ══════════════════════════════════════════════════════════════════════════

def _tournament_select(
    candidates: list[ScoredSegment],
    target: int,
    max_clips: int,
    source_duration: float,
    constraints: EditConstraints,
    learned_preferences: Any = None,
) -> list[ScoredSegment]:
    """Iteratively pick the candidate with highest multi-objective fitness.

    After each pick, update the state (coverage, intent counts, etc.)
    so subsequent picks account for what's already selected.

    When target is high relative to source duration, overlap constraints
    are progressively relaxed to allow more clips.
    """
    # State tracking
    selected: list[ScoredSegment] = []
    selection_reasons: dict[int, dict] = {}  # idx → fitness breakdown
    n_zones = max(3, min(6, int(source_duration / 60)))
    zone_size = source_duration / n_zones
    zone_coverage = [0.0] * n_zones
    intent_counts: dict[str, int] = {}
    hook_type_counts: dict[str, int] = {}
    cluster_ids_seen: set[int] = set()
    topic_labels_seen: set[str] = set()

    # Adaptive overlap: estimate max non-overlapping clips possible
    avg_clip_dur = (constraints.min_clip_duration_sec + constraints.max_clip_duration_sec) / 2
    max_non_overlap = max(1, int(source_duration / (avg_clip_dur + MIN_GAP_SEC)))

    # If target > what fits without overlap, relax constraints
    if target > max_non_overlap:
        overlap_ratio = min(0.50, MAX_OVERLAP_RATIO + (target - max_non_overlap) * 0.05)
        gap_sec = max(1.0, MIN_GAP_SEC - (target - max_non_overlap) * 1.0)
        logger.info(
            "Adaptive overlap: target=%d > max_non_overlap=%d → "
            "overlap_ratio=%.2f (was %.2f), gap=%.1fs (was %.1fs)",
            target, max_non_overlap, overlap_ratio, MAX_OVERLAP_RATIO, gap_sec, MIN_GAP_SEC,
        )
    else:
        overlap_ratio = MAX_OVERLAP_RATIO
        gap_sec = MIN_GAP_SEC

    pool = sorted(candidates, key=lambda s: s.composite_score, reverse=True)

    for round_num in range(min(target, len(pool))):
        best_idx = -1
        best_fitness = -1.0
        best_breakdown: dict[str, float] = {}

        for idx, cand in enumerate(pool):
            if _overlaps_any(cand, selected, overlap_ratio, gap_sec):
                continue

            fitness, breakdown = _compute_fitness(
                cand, selected, zone_coverage, zone_size, n_zones,
                intent_counts, hook_type_counts, source_duration,
                learned_preferences=learned_preferences,
                cluster_ids_seen=cluster_ids_seen,
                topic_labels_seen=topic_labels_seen,
            )

            if fitness > best_fitness:
                best_fitness = fitness
                best_idx = idx
                best_breakdown = breakdown

        if best_idx < 0:
            break

        winner = pool.pop(best_idx)
        selected.append(winner)
        selection_reasons[len(selected) - 1] = best_breakdown

        # Update all state dimensions
        zone_idx = min(n_zones - 1, int(winner.time_range.midpoint / zone_size))
        zone_coverage[zone_idx] += winner.time_range.duration / zone_size

        intent = getattr(winner, 'clip_intent', 'unknown')
        intent_counts[intent] = intent_counts.get(intent, 0) + 1

        ht = winner.hook.hook_type
        hook_type_counts[ht] = hook_type_counts.get(ht, 0) + 1

        cid = getattr(winner, 'cluster_id', -1)
        if cid >= 0:
            cluster_ids_seen.add(cid)

        topic = getattr(winner, 'topic_label', '') or ''
        if topic:
            topic_labels_seen.add(topic)

        logger.debug(
            "Round %d: picked [%.0f-%.0fs] fitness=%.3f intent=%s cluster=%d topic=%s",
            round_num + 1, winner.time_range.start, winner.time_range.end,
            best_fitness, intent, cid, topic[:20],
        )

    # Stash selection reasons for downstream use
    for i, seg in enumerate(selected):
        if hasattr(seg, '__dict__'):
            pass  # frozen dataclass — will inject reason in _to_candidate_clips
    # Store as module-level for _to_candidate_clips to access
    _tournament_reasons.clear()
    _tournament_reasons.update(selection_reasons)

    return selected


# Module-level storage for tournament reasons (thread-safe for single pipeline)
_tournament_reasons: dict[int, dict] = {}


def _build_selection_reason(rank_idx: int) -> str:
    """Build human-readable selection reason from tournament fitness breakdown."""
    bd = _tournament_reasons.get(rank_idx)
    if not bd:
        return f"Rank #{rank_idx + 1}"

    # Find top 2 contributing factors
    factors = [
        ("quality", bd.get("quality", 0)),
        ("diversity", bd.get("diversity", 0)),
        ("coverage", bd.get("coverage", 0)),
        ("intent", bd.get("intent_balance", 0)),
        ("cluster", bd.get("cluster_diversity", 0)),
        ("topic", bd.get("topic_diversity", 0)),
    ]
    top = sorted(factors, key=lambda f: f[1], reverse=True)[:2]
    top_str = " + ".join(f"{name}={val:.2f}" for name, val in top)
    fitness = bd.get("fitness", 0)
    return f"Rank #{rank_idx + 1} (fitness={fitness:.3f}: {top_str})"


def _overlaps_any(
    cand: ScoredSegment,
    selected: list[ScoredSegment],
    max_overlap: float = MAX_OVERLAP_RATIO,
    min_gap: float = MIN_GAP_SEC,
) -> bool:
    """Check if candidate overlaps with any already-selected clip."""
    for s in selected:
        overlap = cand.time_range.overlap_duration(s.time_range)
        shorter = min(cand.time_range.duration, s.time_range.duration)
        if shorter > 0 and overlap / shorter > max_overlap:
            return True
        # Also check minimum gap
        gap = abs(cand.time_range.start - s.time_range.end)
        gap2 = abs(s.time_range.start - cand.time_range.end)
        if min(gap, gap2) < min_gap and overlap > 0:
            return True
    return False


def _compute_fitness(
    cand: ScoredSegment,
    selected: list[ScoredSegment],
    zone_coverage: list[float],
    zone_size: float,
    n_zones: int,
    intent_counts: dict[str, int],
    hook_type_counts: dict[str, int],
    source_duration: float,
    learned_preferences: Any = None,
    cluster_ids_seen: set[int] | None = None,
    topic_labels_seen: set[str] | None = None,
) -> tuple[float, dict[str, float]]:
    """Compute 6-objective fitness for a candidate.

    Returns:
        (fitness_score, breakdown_dict) for explainability.
    """
    total_selected = len(selected) or 1

    # ── Objective 1: Quality (raw score) ──────────────────────────
    quality = cand.composite_score

    # ── Objective 2: Temporal + Hook type diversity ───────────────
    diversity = 1.0
    if selected:
        min_dist = min(
            abs(cand.time_range.midpoint - s.time_range.midpoint)
            for s in selected
        )
        max_possible = source_duration / 2
        diversity = min(1.0, min_dist / max(1.0, max_possible))

    ht = cand.hook.hook_type
    ht_count = hook_type_counts.get(ht, 0)
    if ht_count / total_selected > T.rank_hook_type_dominance_max:
        diversity *= 0.7

    # ── Objective 3: Timeline coverage ────────────────────────────
    zone_idx = min(n_zones - 1, int(cand.time_range.midpoint / zone_size))
    current_zone = zone_coverage[zone_idx]
    if current_zone < T.rank_zone_coverage_low:
        coverage = 1.0
    elif current_zone < T.rank_zone_coverage_med:
        coverage = 0.7
    elif current_zone < 1.0:
        coverage = 0.4
    else:
        coverage = 0.15

    # ── Objective 4: Intent balance ───────────────────────────────
    intent = getattr(cand, 'clip_intent', 'unknown')
    intent_count = intent_counts.get(intent, 0)
    ideal_ratio = _IDEAL_INTENT_MIX.get(intent, 0.1)
    if total_selected <= 1:
        intent_balance = 0.8
    else:
        current_ratio = intent_count / total_selected
        if current_ratio < ideal_ratio:
            intent_balance = 0.9
        elif current_ratio > ideal_ratio * 2:
            intent_balance = 0.3
        else:
            intent_balance = 0.6

    # ── Objective 5: Cluster diversity (NEW) ──────────────────────
    cluster_id = getattr(cand, 'cluster_id', -1)
    if cluster_ids_seen and cluster_id >= 0:
        if cluster_id in cluster_ids_seen:
            cluster_div = 0.2  # Same cluster = heavy penalty
        else:
            cluster_div = 1.0  # New cluster = bonus
    else:
        cluster_div = 0.7  # No cluster info = neutral

    # ── Objective 6: Topic diversity (NEW) ────────────────────────
    topic = getattr(cand, 'topic_label', '') or ''
    if topic and topic_labels_seen:
        if topic in topic_labels_seen:
            topic_div = 0.3  # Same topic = penalty
        else:
            topic_div = 1.0  # New topic = bonus
    else:
        topic_div = 0.7  # No topic = neutral

    # ── Combined fitness (6 objectives) ───────────────────────────
    # Rebalanced weights: quality 35%, coverage 20%, diversity 15%,
    # intent 10%, cluster 10%, topic 10%
    W_Q, W_D, W_C, W_I, W_CL, W_T = 0.35, 0.15, 0.20, 0.10, 0.10, 0.10

    fitness = (
        quality * W_Q
        + diversity * W_D
        + coverage * W_C
        + intent_balance * W_I
        + cluster_div * W_CL
        + topic_div * W_T
    )

    breakdown = {
        "quality": round(quality, 3),
        "diversity": round(diversity, 3),
        "coverage": round(coverage, 3),
        "intent_balance": round(intent_balance, 3),
        "cluster_diversity": round(cluster_div, 3),
        "topic_diversity": round(topic_div, 3),
        "fitness": round(fitness, 4),
    }

    # ── V3: Apply learned preference bias ─────────────────────────
    if learned_preferences is not None:
        try:
            from cutclipshort.editorial.learning.preference_engine import apply_bias_to_fitness
            clip_scores = {
                "hook": cand.hook.score,
                "pacing": cand.pacing_score,
                "payoff": cand.payoff.score,
                "visual": cand.visual_score,
                "audio": cand.audio_score,
                "content": cand.content_density_score,
                "coherence": cand.coherence.score if cand.coherence else 0.5,
                "semantic": getattr(cand, 'semantic_context_score', 0.0),
                "genre": cand.genre_cue_score,
            }
            fitness = apply_bias_to_fitness(
                base_fitness=fitness,
                bias=learned_preferences,
                clip_scores=clip_scores,
                clip_intent=getattr(cand, 'clip_intent', 'unknown'),
                clip_duration=cand.time_range.duration,
            )
        except Exception as exc:
            logger.debug("Bias application failed, using base fitness: %s", exc)

    breakdown["fitness"] = round(fitness, 4)
    return fitness, breakdown


# ══════════════════════════════════════════════════════════════════════════
# STEP 3: INTENT REBALANCE
# ══════════════════════════════════════════════════════════════════════════

def _rebalance_intents(
    selected: list[ScoredSegment],
    pool: list[ScoredSegment],
    target: int,
) -> list[ScoredSegment]:
    """Check if intent mix is healthy; swap if needed.

    Rule: if all clips are same intent AND pool has different intents,
    swap the weakest same-intent for the best different-intent.
    """
    if len(selected) <= 2:
        return selected

    intents = [getattr(s, 'clip_intent', 'unknown') for s in selected]
    unique_intents = set(intents)

    if len(unique_intents) > 1:
        return selected  # Already diverse

    # All same intent — try to swap up to 2 weakest for different-intent alternatives
    dominant = intents[0]
    max_swaps = min(2, len(selected) - 1)  # Keep at least 1 of dominant
    result = list(selected)

    for swap_round in range(max_swaps):
        alternatives = [
            s for s in pool
            if getattr(s, 'clip_intent', 'unknown') != dominant
            and not _overlaps_any(s, result)
        ]
        if not alternatives:
            break

        alternatives.sort(key=lambda s: s.composite_score, reverse=True)
        best_alt = alternatives[0]

        # Find weakest same-intent in current result
        same_intent = [s for s in result if getattr(s, 'clip_intent', 'unknown') == dominant]
        if not same_intent:
            break
        weakest = min(same_intent, key=lambda s: s.composite_score)

        if best_alt.composite_score >= weakest.composite_score * 0.65:
            result = [s for s in result if s is not weakest]
            result.append(best_alt)
            logger.info(
                "Intent rebalance #%d: swapped %s(%.2f) for %s(%.2f)",
                swap_round + 1,
                getattr(weakest, 'clip_intent', '?'), weakest.composite_score,
                getattr(best_alt, 'clip_intent', '?'), best_alt.composite_score,
            )
        else:
            break

    result.sort(key=lambda s: s.composite_score, reverse=True)
    return result


# ══════════════════════════════════════════════════════════════════════════
# STEP 5: CONVERT TO CANDIDATE CLIPS
# ══════════════════════════════════════════════════════════════════════════

def _to_candidate_clips(
    selected: list[ScoredSegment],
    profile: GenreProfile,
) -> list[CandidateClip]:
    """Convert ScoredSegments to CandidateClip objects with explanations."""
    from cutclipshort.evaluation.explainability import explain_candidate

    candidates: list[CandidateClip] = []

    for i, seg in enumerate(selected):
        tags = _generate_tags(seg)
        content_type = ContentType.TALKING_HEAD if seg.speech_ratio > 0.5 else ContentType.UNKNOWN
        genre_fit = _compute_genre_fit(seg, profile)
        coherence = seg.coherence

        # Build V4 explanation (with comparative + intent)
        runner_up_score = selected[i + 1].composite_score if i + 1 < len(selected) else 0
        runner_up_intent = getattr(selected[i + 1], 'clip_intent', '') if i + 1 < len(selected) else ""
        explanation = explain_candidate(
            composite_score=seg.composite_score,
            hook_score=seg.hook.score,
            hook_type=seg.hook.hook_type,
            hook_text=seg.hook.hook_text,
            payoff_score=seg.payoff.score,
            payoff_type=seg.payoff.payoff_type,
            pacing_score=seg.pacing_score,
            visual_score=seg.visual_score,
            audio_score=seg.audio_score,
            content_density=seg.content_density_score,
            coherence_score=coherence.score if coherence else 0.5,
            coherence_resolved=coherence.resolution_found if coherence else False,
            hook_promise=coherence.hook_promise if coherence else "none",
            resolution_type=coherence.resolution_type if coherence else "none",
            genre_cue_score=seg.genre_cue_score,
            semantic_score=getattr(seg, 'semantic_context_score', 0.0),
            speech_ratio=seg.speech_ratio,
            clip_intent=getattr(seg, 'clip_intent', 'unknown'),
            intent_confidence=getattr(seg, 'intent_confidence', 0.0),
            topic_label=getattr(seg, 'topic_label', ''),
            filler_ratio=0.0,
            reasoning=seg.reasoning,
            is_selected=True,
            # V4: Comparative + intent
            rank_position=i + 1,
            total_candidates=len(selected),
            runner_up_score=runner_up_score,
            runner_up_intent=runner_up_intent,
            selection_breakdown=_tournament_reasons.get(i),
            intent_features=dict(getattr(seg, 'intent_features', {})),
            intent_reasoning=getattr(seg, 'intent_reasoning', ''),
            generation_reason=getattr(seg, 'generation_reason', ''),
        )

        candidate = CandidateClip(
            candidate_id=f"c{i + 1:03d}",
            time_range=seg.time_range,
            score=seg.score,
            content_type=content_type,
            genre_fit=round(genre_fit, 3),
            motion_avg=0.0,
            has_speech=seg.speech_ratio > T.rank_speech_presence_threshold,
            speech_text_preview=seg.speech_text[:120] if seg.speech_text else "",
            transcript_segment_ids=seg.transcript_segment_ids,
            has_person=seg.visual_score > T.rank_visual_person_threshold,
            person_count=1 if seg.visual_score > T.rank_visual_person_threshold else 0,
            tags=tags,
            hook_text=seg.hook.hook_text,
            suggested_hook_type=seg.hook.hook_type,
            strategy_name=profile.name,
            strategy_reasoning=seg.reasoning,
            why_selected=explanation.why_selected,
            why_ranked_higher=_build_selection_reason(i),
            why_might_fail="; ".join(w.label for w in explanation.weaknesses[:3]),
            why_not_others=explanation.why_not_others,
            intent_explanation=explanation.intent_explanation,
            risk_flags=explanation.risk_flags,
            objective=_GENRE_OBJECTIVES.get(profile.name, "retention"),
            hook_promise=coherence.hook_promise if coherence else "",
            payoff_resolution=coherence.resolution_type if coherence else "",
            clip_intent=getattr(seg, 'clip_intent', 'unknown'),
            intent_confidence=getattr(seg, 'intent_confidence', 0.0),
            intent_reasoning=getattr(seg, 'intent_reasoning', ''),
            intent_features=dict(getattr(seg, 'intent_features', {})),
            generation_reason=getattr(seg, 'generation_reason', ''),
            cluster_id=getattr(seg, 'cluster_id', -1),
            topic_label=getattr(seg, 'topic_label', ''),
            emotional_peak_intensity=getattr(seg, 'emotional_intensity', 0.0),
            narrative_completeness=getattr(seg, 'narrative_completeness', 0.0),
            explanation=explanation,
        )
        candidates.append(candidate)

    _apply_titles(candidates, profile.name)
    return candidates


# ══════════════════════════════════════════════════════════════════════════
# OBJECTIVE RERANK (genre-specific boost)
# ══════════════════════════════════════════════════════════════════════════

def _objective_rerank(
    segments: list[ScoredSegment],
    profile: GenreProfile,
) -> list[ScoredSegment]:
    """Apply genre-specific objective boosts (±5% nudge)."""
    objective = _GENRE_OBJECTIVES.get(profile.name, "retention")
    boosted = []
    for seg in segments:
        boost = 0.0
        if objective == "retention":
            if seg.hook.score > T.boost_hook_strong: boost += 0.02
            if seg.pacing_score > T.boost_pacing_good: boost += 0.02
            if seg.hook.silence_penalty < T.boost_silence_low: boost += 0.01
        elif objective == "shareability":
            if seg.hook.hook_type in ("surprise", "conflict", "reaction"): boost += 0.03
            if seg.genre_cue_score > T.boost_genre_match: boost += 0.02
        elif objective == "clarity":
            if seg.payoff.score > T.boost_payoff_strong: boost += 0.02
            if seg.coherence and seg.coherence.resolution_found: boost += 0.03
        elif objective == "emotional_impact":
            if seg.hook.hook_type == "emotional": boost += 0.03
            if seg.payoff.score > T.boost_payoff_very_strong: boost += 0.02
        elif objective == "insight":
            if seg.content_density_score > T.boost_density_high: boost += 0.02
            if seg.coherence and seg.coherence.resolution_found: boost += 0.02
            if seg.speech_ratio > T.boost_speech_heavy: boost += 0.01
        elif objective == "visual_impact":
            # Nature/visual genres: reward high visual score + low speech
            if seg.visual_score > 0.70: boost += 0.03
            if seg.speech_ratio < 0.30: boost += 0.02  # Less talk = more visual
            if seg.hook.hook_type in ("curiosity", "reaction"): boost += 0.01
        boosted.append((seg, seg.composite_score + boost))
    boosted.sort(key=lambda x: x[1], reverse=True)
    return [seg for seg, _ in boosted]


# ══════════════════════════════════════════════════════════════════════════
# HELPERS (tags, reasoning, logging)
# ══════════════════════════════════════════════════════════════════════════

_GENRE_OBJECTIVES: dict[str, str] = {
    "talking_head": "retention", "podcast": "insight",
    "interview": "emotional_impact", "review": "clarity",
    "storytelling": "emotional_impact", "comedy": "shareability",
    "education": "clarity", "news_commentary": "shareability",
    "nature": "visual_impact", "history": "clarity",
    "action": "shareability", "kids_music": "retention",
    "animation": "emotional_impact",
}


def _generate_tags(seg: ScoredSegment) -> list[str]:
    tags: list[str] = []
    if seg.hook.score > T.tag_hook_strong: tags.append("strong_hook")
    elif seg.hook.score > T.tag_hook_decent: tags.append("decent_hook")
    if seg.payoff.score > T.tag_payoff_strong: tags.append("strong_payoff")
    elif seg.payoff.payoff_type == "incomplete": tags.append("weak_ending")
    if seg.pacing_score > T.tag_pacing_good: tags.append("good_pacing")
    if seg.content_density_score > T.tag_density_rich: tags.append("content_rich")
    if seg.time_range.duration < 20: tags.append("short")
    elif seg.time_range.duration > 50: tags.append("long")
    if seg.hook.hook_type == "question": tags.append("opens_with_question")
    elif seg.hook.hook_type == "bold_statement": tags.append("bold_opening")
    if seg.speech_ratio > T.tag_speech_heavy: tags.append("speech_heavy")
    if seg.genre_cue_score > T.tag_genre_match: tags.append("genre_match")
    intent = getattr(seg, 'clip_intent', 'unknown')
    if intent != 'unknown': tags.append(f"intent:{intent}")
    return tags


def _compute_genre_fit(seg: ScoredSegment, profile: GenreProfile) -> float:
    fit: list[float] = []
    if profile.require_speech:
        fit.append(1.0 if seg.speech_ratio >= profile.min_speech_ratio else 0.4)
    else:
        fit.append(0.8)
    if profile.require_person:
        fit.append(seg.visual_score)
    else:
        fit.append(0.8)
    dur = seg.time_range.duration
    if profile.ideal_min_sec <= dur <= profile.ideal_max_sec:
        fit.append(1.0)
    else:
        dist = min(abs(dur - profile.ideal_min_sec), abs(dur - profile.ideal_max_sec))
        fit.append(max(0.3, 1.0 - dist / 30.0))
    if profile.needs_closure:
        fit.append(seg.payoff.score)
    else:
        fit.append(0.8)
    return sum(fit) / len(fit) if fit else 0.5


def _build_why_selected(seg: ScoredSegment, profile: GenreProfile) -> str:
    parts = []
    if seg.hook.score >= T.explain_hook_strong: parts.append(f"Strong {seg.hook.hook_type} hook")
    elif seg.hook.score >= T.explain_hook_decent: parts.append(f"Decent {seg.hook.hook_type} opening")
    if seg.coherence and seg.coherence.resolution_found:
        parts.append(f"resolved ({seg.coherence.hook_promise}->{seg.coherence.resolution_type})")
    if seg.payoff.score >= T.explain_payoff_strong: parts.append("clear ending")
    if seg.genre_cue_score >= T.explain_genre_match: parts.append(f"strong {profile.name} match")
    if seg.pacing_score >= T.explain_pacing_good: parts.append("good pacing")
    intent = getattr(seg, 'clip_intent', 'unknown')
    if intent != 'unknown': parts.append(f"intent={intent}")
    return "; ".join(parts) if parts else "best available composite"


def _build_why_might_fail(seg: ScoredSegment) -> str:
    w = []
    if seg.hook.score < T.explain_hook_weak: w.append("weak opening")
    if seg.payoff.score < T.explain_payoff_weak: w.append(f"ending={seg.payoff.payoff_type}")
    if seg.coherence and not seg.coherence.resolution_found and seg.coherence.hook_promise != "none":
        w.append(f"{seg.coherence.hook_promise} unresolved")
    if seg.speech_ratio < T.explain_speech_low: w.append("low speech")
    return "; ".join(w) if w else ""


def _build_risk_flags(seg: ScoredSegment) -> list[str]:
    flags = []
    if seg.hook.score < T.explain_hook_weak: flags.append("weak_hook")
    if seg.payoff.payoff_type == "incomplete": flags.append("incomplete_ending")
    if seg.coherence and seg.coherence.score < T.explain_coherence_poor: flags.append("low_coherence")
    if seg.speech_ratio < T.explain_speech_low: flags.append("low_speech")
    if seg.visual_score < T.explain_visual_poor: flags.append("poor_visual")
    if seg.audio_score < T.explain_audio_poor: flags.append("audio_issues")
    if seg.hook.silence_penalty > T.explain_silence_penalty: flags.append("dead_air_start")
    if seg.time_range.duration > 55: flags.append("too_long")
    if seg.time_range.duration < 12: flags.append("too_short")
    return flags


def _apply_titles(candidates: list[CandidateClip], genre: str) -> None:
    try:
        from cutclipshort.editorial.title_generator import generate_titles
        updated: list[CandidateClip] = []
        for cand in candidates:
            result = generate_titles(
                hook_text=cand.hook_text, speech_preview=cand.speech_text_preview,
                hook_type=cand.suggested_hook_type, tags=list(cand.tags),
                genre=genre, score=cand.score.overall,
                candidate_id=cand.candidate_id, duration=cand.time_range.duration,
            )
            updated.append(replace(
                cand, display_title=result.display_title, seo_slug=result.seo_slug,
                suggested_hashtags=result.suggested_hashtags, seo_description=result.seo_description,
            ))
        candidates.clear()
        candidates.extend(updated)
    except Exception as e:
        logger.warning("Title generation skipped: %s", e)


def _log_selection(
    candidates: list[CandidateClip], all_scored: list[ScoredSegment],
    profile: GenreProfile, source_duration: float,
) -> None:
    """Log selection report."""
    logger.info("=" * 60)
    logger.info("RANKING V2 REPORT | Genre: %s | Source: %.0fs", profile.display_name, source_duration)
    logger.info("Proposals: %d | Selected: %d", len(all_scored), len(candidates))

    if candidates:
        # Coverage analysis
        covered = sum(c.time_range.duration for c in candidates)
        logger.info("Coverage: %.0fs / %.0fs (%.0f%%)", covered, source_duration, covered/source_duration*100)

        # Intent distribution
        intents: dict[str, int] = {}
        for c in candidates:
            intents[c.clip_intent] = intents.get(c.clip_intent, 0) + 1
        logger.info("Intents: %s", dict(sorted(intents.items())))

        # Per-clip details
        for i, c in enumerate(candidates):
            logger.info(
                "  #%d %s [%.0f-%.0fs] score=%.1f%% intent=%s | %s",
                i+1, c.candidate_id, c.time_range.start, c.time_range.end,
                c.score.overall_100, c.clip_intent,
                c.why_selected[:60],
            )

    logger.info("=" * 60)
