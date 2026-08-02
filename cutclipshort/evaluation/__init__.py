"""Evaluation system V2 — quality analysis with tier-aware evaluator selection.

Usage:
    from cutclipshort.evaluation import build_evaluators_for_tier
    from cutclipshort.evaluation.composite_scorer import CompositeScorer

    evaluators = build_evaluators_for_tier("balanced")
    scorer = CompositeScorer(evaluators)
    result = scorer.score(clip_id, rendered_path, clip_spec, analysis)
"""

from __future__ import annotations

from typing import Any


def build_default_evaluators() -> list:
    """Build full evaluator set (balanced tier default)."""
    return build_evaluators_for_tier("balanced")


def build_evaluators_for_tier(tier_name: str = "balanced") -> list:
    """Build evaluator set based on quality tier.

    fast:         4 core evaluators only
    balanced:     4 core + 4 advanced (8 total)
    high_quality: 4 core + 4 advanced (8 total, stricter thresholds)
    """
    from cutclipshort.core.quality_tiers import get_tier

    tier = get_tier(tier_name)
    evaluators = []

    # Core evaluators (always on)
    if tier.eval_core_evaluators:
        from cutclipshort.evaluation.metrics.pacing_evaluator import PacingEvaluator
        from cutclipshort.evaluation.metrics.audio_evaluator import AudioEvaluator
        from cutclipshort.evaluation.metrics.visual_evaluator import VisualEvaluator
        from cutclipshort.evaluation.metrics.content_evaluator import ContentEvaluator
        evaluators.extend([
            PacingEvaluator(),
            AudioEvaluator(),
            VisualEvaluator(),
            ContentEvaluator(),
        ])

    # Advanced evaluators (tier-dependent)
    if tier.eval_opening_strength:
        from cutclipshort.evaluation.metrics.opening_evaluator import OpeningEvaluator
        evaluators.append(OpeningEvaluator())

    if tier.eval_retention_potential:
        from cutclipshort.evaluation.metrics.retention_evaluator import RetentionEvaluator
        evaluators.append(RetentionEvaluator())

    if tier.eval_semantic_completeness:
        from cutclipshort.evaluation.metrics.semantic_evaluator import SemanticEvaluator
        evaluators.append(SemanticEvaluator())

    if tier.eval_subtitle_density:
        from cutclipshort.evaluation.metrics.subtitle_density_evaluator import SubtitleDensityEvaluator
        evaluators.append(SubtitleDensityEvaluator())

    return evaluators
