"""Editorial Brain V2 — orchestrates the full editorial pipeline.

Pipeline:
1. Load genre profile
2. [V2] Build semantic context (tier-aware)
3. Generate candidates (tier-aware passes)
4. Pre-filter outro/CTA
5. Rank and select (with learned preferences)
6. Build edit plan

V2 fixes:
- Passes learned_preferences to ranker
- Reads tier config for semantic/editorial control
- Tier-aware candidate generation passes
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from cutclipshort.editorial.candidate_generator import generate_candidates
from cutclipshort.editorial.clip_ranker import rank_and_select
from cutclipshort.editorial.edit_plan_builder import build_edit_plan
from cutclipshort.editorial.genre_profiles import get_profile
from cutclipshort.types import (
    AnalysisResult,
    CandidateClip,
    EditConstraints,
    EditPlan,
)

logger = logging.getLogger(__name__)


def run_editorial(
    analysis: AnalysisResult,
    constraints: EditConstraints,
    genre: str = "talking_head",
    user_overrides: dict | None = None,
    semantic_context: "SemanticContext | None" = None,
    learned_preferences: Any = None,
    tier_name: str = "balanced",
) -> tuple[list[CandidateClip], EditPlan]:
    """Run the full editorial pipeline.

    Args:
        analysis: Complete analysis result.
        constraints: Platform constraints.
        genre: Content genre name.
        user_overrides: Optional style preferences.
        semantic_context: Pre-computed semantic context (None = auto-build).
        learned_preferences: PreferenceBias from learning system (None = no bias).
        tier_name: Quality tier ("fast", "balanced", "high_quality").

    Returns:
        Tuple of (ranked_candidates, edit_plan).
    """
    t0 = time.perf_counter()
    overrides = user_overrides or {}

    # Load tier config
    tier = _load_tier(tier_name)

    # Load editorial thresholds from config (makes thresholds tier-aware)
    try:
        from cutclipshort.editorial.thresholds import load_thresholds_from_config
        from cutclipshort.core.config import AppConfig
        cfg = AppConfig()
        editorial_config = cfg.get_section("editorial")
        load_thresholds_from_config(editorial_config)
    except Exception as exc:
        logger.debug("Threshold config loading skipped: %s", exc)

    # 1. Load genre profile
    profile = get_profile(genre)
    logger.info(
        "Editorial brain: genre=%s, tier=%s, constraints: %s-%ss, target=%d clips",
        profile.name, tier_name,
        constraints.min_clip_duration_sec,
        constraints.max_clip_duration_sec,
        constraints.target_clip_count,
    )

    # 2. Build semantic context (tier-aware: skip in fast mode)
    if semantic_context is None:
        semantic_enabled = getattr(tier, 'semantic_enabled', True) if tier else True
        if semantic_enabled:
            try:
                from cutclipshort.editorial.semantic import build_semantic_context
                semantic_context = build_semantic_context(analysis)
                logger.info(
                    "Semantic layer: %d topics, %d arcs, %d spikes, %d clusters",
                    semantic_context.topic_count,
                    len(semantic_context.narrative_arcs),
                    len(semantic_context.emotional_spikes),
                    len(semantic_context.concept_clusters),
                )
            except Exception as e:
                logger.warning("Semantic layer failed (degrading gracefully): %s", e)
                semantic_context = None
        else:
            logger.info("Semantic layer: DISABLED by tier '%s'", tier_name)
            semantic_context = None

    # 3. Generate candidates (tier-aware passes)
    max_passes = getattr(tier, 'candidate_generation_passes', 4) if tier else 4
    user_hook_keywords = overrides.get("hook_keywords") or []
    scored_segments = generate_candidates(
        analysis, constraints, profile, semantic_context,
        max_passes=max_passes,
        extra_hook_keywords=user_hook_keywords,
    )
    logger.info("Scored %d candidate proposals (%d passes)", len(scored_segments), max_passes)

    # 3.5 Pre-filter outro/CTA
    scored_segments = _filter_outro_segments(scored_segments, analysis)
    logger.info("After outro filter: %d proposals", len(scored_segments))

    # 3.6 Enforce intent — every candidate MUST have a clear intent
    before_intent = len(scored_segments)
    scored_segments = _enforce_intent(scored_segments)
    dropped = before_intent - len(scored_segments)
    if dropped > 0:
        logger.info("Intent filter: dropped %d/%d proposals with unknown/weak intent",
                     dropped, before_intent)

    if not scored_segments:
        logger.warning("No candidate proposals — returning empty results")
        now = datetime.now(timezone.utc).isoformat()
        empty_plan = EditPlan(
            plan_id="plan_empty", version=1,
            strategy_name=profile.name, genre=genre,
            constraints=constraints, clips=[],
            source_hash=analysis.source.source_hash,
            analysis_versions=analysis.engine_versions,
            created_at=now, modified_at=now,
        )
        return [], empty_plan

    # 4. Rank and select (with learned preferences)
    candidates = rank_and_select(
        scored_segments,
        constraints,
        profile,
        source_duration=analysis.source.duration_sec,
        learned_preferences=learned_preferences,
    )
    logger.info("Selected %d candidates after ranking", len(candidates))

    # 5. Build edit plan
    plan = build_edit_plan(
        candidates, analysis, constraints, profile, overrides,
    )

    elapsed = time.perf_counter() - t0
    logger.info(
        "Editorial brain complete: %d candidates, %d clips in plan, %.2fs",
        len(candidates), len(plan.clips), elapsed,
    )

    for i, c in enumerate(candidates[:5]):
        logger.info(
            "  #%d: [%.1f-%.1fs] score=%.3f intent=%s | %s",
            i + 1, c.time_range.start, c.time_range.end,
            c.score.overall, c.clip_intent,
            c.speech_text_preview[:60] if c.speech_text_preview else "(no speech)",
        )

    return candidates, plan


def _load_tier(tier_name: str):
    """Load tier spec, returns None if not available."""
    try:
        from cutclipshort.core.quality_tiers import get_tier
        return get_tier(tier_name)
    except Exception as exc:
        logger.debug("Tier '%s' not loaded: %s", tier_name, exc)
        return None


# ── Pre-filters ──────────────────────────────────────────────────────────

def _enforce_intent(segments: list) -> list:
    """Filter out candidates with unknown or low-confidence intent.

    Every candidate MUST have a clear editorial purpose.
    Keeps at least 3 candidates even if all have weak intent (graceful degradation).
    Uses T.intent_min_confidence (same as classifier) for consistency.
    """
    if not segments:
        return []

    try:
        from cutclipshort.editorial.thresholds import T
        min_conf = T.intent_min_confidence
    except Exception:
        min_conf = 0.25

    strong = [s for s in segments
              if s.clip_intent != "unknown" and s.intent_confidence >= min_conf]

    if len(strong) >= 3:
        # Log intent distribution
        dist: dict[str, int] = {}
        for s in strong:
            dist[s.clip_intent] = dist.get(s.clip_intent, 0) + 1
        logger.info("Intent enforcement: %d/%d pass (dist: %s)",
                     len(strong), len(segments), dist)
        return strong

    # Graceful degradation: keep top by COMBINED score (composite * 0.7 + intent_conf * 0.3)
    logger.warning(
        "Intent enforcement: only %d/%d have clear intent (min_conf=%.2f) — "
        "using combined score fallback",
        len(strong), len(segments), min_conf,
    )
    fallback = sorted(
        segments,
        key=lambda s: s.composite_score * 0.7 + (s.intent_confidence or 0.0) * 0.3,
        reverse=True,
    )
    keep_n = max(3, len(strong))
    return fallback[:keep_n]


def _get_outro_patterns(language: str = "en") -> tuple:
    """Get CTA/outro patterns for the detected language."""
    try:
        from cutclipshort.editorial.vocabulary import get_vocabulary
        vocab = get_vocabulary(language)
        return vocab.OUTRO_PATTERNS
    except Exception as exc:
        logger.debug("Vocabulary fallback to English: %s", exc)
        # Fallback: English patterns
        return (
            "thank you for watching", "thanks for watching",
            "subscribe", "like and share", "hit the bell",
            "see you next time", "follow me on", "check out my",
            "link in", "don't forget to", "make sure to subscribe",
        )


def _filter_outro_segments(segments: list, analysis: AnalysisResult) -> list:
    """Remove segments dominated by CTA language (multi-language)."""
    # Detect language from transcript
    language = "en"
    if analysis.transcript:
        try:
            from cutclipshort.editorial.vocabulary import detect_language
            sample_text = " ".join(s.text for s in analysis.transcript[:5])
            language = detect_language(sample_text)
        except Exception as e:
            logger.debug("Language detection failed, using English: %s", e)

    patterns = _get_outro_patterns(language)
    filtered = []
    for seg in segments:
        text = seg.speech_text.lower() if seg.speech_text else ""
        if not text:
            filtered.append(seg)
            continue
        cta_hits = sum(1 for p in patterns if p in text)
        if cta_hits >= 3:
            logger.info(
                "Filtered outro [%.1f-%.1fs]: %d CTA phrases",
                seg.time_range.start, seg.time_range.end, cta_hits,
            )
            continue
        filtered.append(seg)
    return filtered
