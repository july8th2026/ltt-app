"""Preference engine — computes scoring biases from accumulated feedback.

Algorithm:
1. Compare average score dimensions of accepted vs rejected clips
2. Dimensions where accepted >> rejected = user cares about this → boost
3. Dimensions where accepted << rejected = user doesn't care → reduce
4. Apply as additive bias to future ranking fitness scores

No ML. Pure statistics with exponential decay (recent decisions weigh more).

Output: PreferenceBias — a dict of dimension → bias adjustment (-0.10 to +0.10)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_MIN_DECISIONS = 5       # Need at least 5 decisions before learning kicks in
_MIN_REJECTED = 2        # Need at least 2 rejections to learn from contrast
_DECAY_HALF_LIFE = 50    # Decisions — older decisions decay exponentially
_MAX_BIAS = 0.10         # Maximum bias per dimension
_SCORE_DIMENSIONS = [
    "hook", "pacing", "payoff", "visual", "audio",
    "content", "coherence", "semantic", "genre",
]


@dataclass(frozen=True)
class PreferenceBias:
    """Learned scoring biases from user feedback."""
    dimension_biases: dict[str, float]   # dimension → bias (-0.10 to +0.10)
    intent_biases: dict[str, float]      # intent → bias
    duration_preference: float           # Preferred duration center (seconds)
    confidence: float                    # 0.0-1.0 how much data backs this
    sample_count: int                    # How many decisions this is based on
    summary: str                         # Human-readable preference summary


def compute_preferences(
    records: list[dict[str, Any]],
) -> PreferenceBias:
    """Compute preference biases from feedback records.

    Returns biases that can be applied to future ranking.
    """
    if len(records) < _MIN_DECISIONS:
        return _empty_bias(len(records))

    accepted = [r for r in records if r["decision"] == "accepted"]
    rejected = [r for r in records if r["decision"] == "rejected"]

    if len(rejected) < _MIN_REJECTED:
        return _empty_bias(len(records))

    # Apply exponential decay (recent decisions weigh more)
    a_weights = _decay_weights(accepted, records)
    r_weights = _decay_weights(rejected, records)

    # Compute weighted averages per dimension
    a_avgs = _weighted_dim_averages(accepted, a_weights)
    r_avgs = _weighted_dim_averages(rejected, r_weights)

    # Dimension biases: where accepted differs from rejected
    dim_biases: dict[str, float] = {}
    for dim in _SCORE_DIMENSIONS:
        a_val = a_avgs.get(dim, 0.5)
        r_val = r_avgs.get(dim, 0.5)
        diff = a_val - r_val

        # Only create bias if there's meaningful difference
        if abs(diff) < 0.05:
            dim_biases[dim] = 0.0
        else:
            # Scale: diff of 0.20 → bias of MAX_BIAS
            bias = max(-_MAX_BIAS, min(_MAX_BIAS, diff * 0.5))
            dim_biases[dim] = round(bias, 4)

    # Intent biases: which intents get accepted more
    intent_biases = _compute_intent_biases(accepted, rejected)

    # Duration preference: average duration of accepted clips
    a_durations = [r.get("duration", 30) for r in accepted if r.get("duration", 0) > 0]
    duration_pref = sum(a_durations) / len(a_durations) if a_durations else 30.0

    # Confidence: based on sample count + consistency
    confidence = min(1.0, len(records) / 50.0)

    # Build summary
    summary = _build_summary(dim_biases, intent_biases, duration_pref, len(records))

    return PreferenceBias(
        dimension_biases=dim_biases,
        intent_biases=intent_biases,
        duration_preference=round(duration_pref, 1),
        confidence=round(confidence, 3),
        sample_count=len(records),
        summary=summary,
    )


def apply_bias_to_fitness(
    base_fitness: float,
    bias: PreferenceBias,
    clip_scores: dict[str, float],
    clip_intent: str = "unknown",
    clip_duration: float = 30.0,
) -> float:
    """Apply learned bias to a clip's ranking fitness score.

    Args:
        base_fitness: Original fitness from tournament ranking
        bias: Learned preferences
        clip_scores: This clip's score breakdown {dim: 0.0-1.0}
        clip_intent: This clip's intent type
        clip_duration: This clip's duration in seconds

    Returns:
        Adjusted fitness (can be slightly higher or lower than base)
    """
    if bias.confidence < 0.1 or bias.sample_count < _MIN_DECISIONS:
        return base_fitness  # Not enough data to bias

    adjustment = 0.0

    # 1. Dimension biases: boost/penalize based on which dimensions are strong
    for dim, dim_bias in bias.dimension_biases.items():
        if abs(dim_bias) < 0.005:
            continue
        clip_dim_score = clip_scores.get(dim, 0.5)
        # Bias amplifies high scores in preferred dimensions
        # and reduces high scores in non-preferred dimensions
        adjustment += dim_bias * clip_dim_score

    # 2. Intent bias
    intent_bias = bias.intent_biases.get(clip_intent, 0.0)
    adjustment += intent_bias

    # 3. Duration preference: gentle nudge toward preferred length
    if bias.duration_preference > 0 and clip_duration > 0:
        dur_dist = abs(clip_duration - bias.duration_preference) / bias.duration_preference
        dur_penalty = -min(0.03, dur_dist * 0.05)
        adjustment += dur_penalty

    # Scale by confidence (low confidence = tiny adjustments)
    adjustment *= bias.confidence

    # Clamp total adjustment
    adjustment = max(-0.08, min(0.08, adjustment))

    return base_fitness + adjustment


# ══════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ══════════════════════════════════════════════════════════════════════════

def _empty_bias(sample_count: int) -> PreferenceBias:
    return PreferenceBias(
        dimension_biases={d: 0.0 for d in _SCORE_DIMENSIONS},
        intent_biases={},
        duration_preference=30.0,
        confidence=0.0,
        sample_count=sample_count,
        summary="Not enough data yet (need 5+ decisions)",
    )


def _decay_weights(
    subset: list[dict], all_records: list[dict],
) -> list[float]:
    """Compute exponential decay weights. Recent decisions weigh more."""
    total = len(all_records)
    weights = []
    for record in subset:
        # Find position in all_records (approximate by timestamp order)
        try:
            idx = all_records.index(record)
        except ValueError:
            idx = total // 2

        age = total - idx  # How many decisions ago
        weight = math.exp(-0.693 * age / _DECAY_HALF_LIFE)  # 0.693 = ln(2)
        weights.append(weight)

    return weights


def _weighted_dim_averages(
    records: list[dict], weights: list[float],
) -> dict[str, float]:
    """Compute weighted average of each score dimension."""
    totals: dict[str, float] = {}
    weight_sums: dict[str, float] = {}

    for record, weight in zip(records, weights):
        scores = record.get("scores", {})
        for dim in _SCORE_DIMENSIONS:
            val = scores.get(dim)
            if val is not None:
                totals[dim] = totals.get(dim, 0.0) + val * weight
                weight_sums[dim] = weight_sums.get(dim, 0.0) + weight

    return {
        dim: totals[dim] / weight_sums[dim]
        for dim in totals
        if weight_sums.get(dim, 0) > 0
    }


def _compute_intent_biases(
    accepted: list[dict], rejected: list[dict],
) -> dict[str, float]:
    """Compute per-intent acceptance rate bias."""
    intent_accept: dict[str, int] = {}
    intent_total: dict[str, int] = {}

    for r in accepted:
        intent = r.get("clip_intent", "unknown")
        intent_accept[intent] = intent_accept.get(intent, 0) + 1
        intent_total[intent] = intent_total.get(intent, 0) + 1

    for r in rejected:
        intent = r.get("clip_intent", "unknown")
        intent_total[intent] = intent_total.get(intent, 0) + 1

    biases: dict[str, float] = {}
    for intent, total in intent_total.items():
        if total < 2:
            continue
        accept_rate = intent_accept.get(intent, 0) / total
        # Baseline accept rate
        overall_rate = len(accepted) / max(1, len(accepted) + len(rejected))
        # Bias: how much this intent deviates from baseline
        diff = accept_rate - overall_rate
        biases[intent] = round(max(-_MAX_BIAS, min(_MAX_BIAS, diff * 0.3)), 4)

    return biases


def _build_summary(
    dim_biases: dict[str, float],
    intent_biases: dict[str, float],
    duration_pref: float,
    sample_count: int,
) -> str:
    """Build human-readable preference summary."""
    parts = [f"Based on {sample_count} decisions"]

    # Top liked dimensions
    liked = sorted(
        [(d, b) for d, b in dim_biases.items() if b > 0.01],
        key=lambda x: -x[1],
    )
    if liked:
        dims = ", ".join(d for d, _ in liked[:3])
        parts.append(f"Prefers: {dims}")

    # Disliked dimensions
    disliked = sorted(
        [(d, b) for d, b in dim_biases.items() if b < -0.01],
        key=lambda x: x[1],
    )
    if disliked:
        dims = ", ".join(d for d, _ in disliked[:2])
        parts.append(f"Less important: {dims}")

    # Preferred intents
    liked_intents = sorted(
        [(i, b) for i, b in intent_biases.items() if b > 0.01],
        key=lambda x: -x[1],
    )
    if liked_intents:
        intents = ", ".join(i for i, _ in liked_intents[:2])
        parts.append(f"Prefers: {intents} clips")

    parts.append(f"Duration sweet spot: {duration_pref:.0f}s")

    return " | ".join(parts)
