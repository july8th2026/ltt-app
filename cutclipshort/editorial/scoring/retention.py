"""Retention-based scoring metrics — predict viewer retention behavior.

7 metrics that model HOW a real viewer watches and decides to stay or leave:

1. opening_arrest    — Will the first 3s stop the scroll?
2. curiosity_gap     — Does the clip create a "need to know" tension?
3. narrative_arc      — Does the clip have a complete story shape?
4. payoff_satisfaction — Does the ending feel satisfying?
5. redundancy_penalty  — Does the clip repeat itself or drag?
6. loop_potential      — Would a viewer re-watch this?
7. cut_naturalness     — Do the start/end feel natural (not mid-word)?

Each function returns (score: float 0.0-1.0, reason: str).
All inputs are signals already computed by the pipeline.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


def opening_arrest(
    hook_score: float,
    first_3s_energy: float,
    has_question: bool,
    has_number: bool,
    filler_in_opening: bool,
) -> tuple[float, str]:
    """Will the first 3 seconds stop the scroll?

    Formula:
      base = hook_score × 0.40
           + first_3s_energy × 0.25
           + question_bonus (0.15 if question in opener)
           + number_bonus (0.10 if statistic in opener)
           + filler_penalty (-0.20 if filler word starts clip)
      = clamp(0, 1)

    Signals:
      hook_score     — from hook_detector (0-1)
      first_3s_energy — audio energy in first 3 seconds (0-1)
      has_question   — opener contains "?" or question word
      has_number     — opener contains statistic/number
      filler_in_opening — first word is filler (um, uh, so...)
    """
    base = hook_score * 0.40 + first_3s_energy * 0.25
    parts = [f"hook={hook_score:.2f}", f"energy={first_3s_energy:.2f}"]

    if has_question:
        base += 0.15
        parts.append("question")
    if has_number:
        base += 0.10
        parts.append("statistic")
    if filler_in_opening:
        base -= 0.20
        parts.append("filler_penalty")

    score = max(0.0, min(1.0, base))
    return score, " + ".join(parts)


def curiosity_gap(
    hook_score: float,
    payoff_score: float,
    question_count: int,
    claim_detected: bool,
    speech_text: str,
) -> tuple[float, str]:
    """Does the clip create a 'need to know' tension?

    Formula:
      gap_tension = hook_score - payoff_score  (positive = unresolved hook)
      base = gap_tension × 0.30
           + question_density × 0.25
           + claim_bonus (0.20 if bold claim without proof)
           + tease_patterns × 0.15
      = clamp(0, 1)

    A high curiosity gap means the viewer MUST keep watching.
    """
    gap_tension = max(0.0, hook_score - payoff_score * 0.5)
    parts = [f"tension={gap_tension:.2f}"]

    base = gap_tension * 0.30

    # Questions create open loops
    q_density = min(1.0, question_count / 3.0)
    base += q_density * 0.25
    if question_count > 0:
        parts.append(f"questions={question_count}")

    # Unproven claims
    if claim_detected:
        base += 0.20
        parts.append("unresolved_claim")

    # Tease patterns in text
    lower = speech_text.lower() if speech_text else ""
    tease_patterns = ["wait", "you won't believe", "the secret", "but here's",
                      "what if", "turns out", "the real reason", "nobody"]
    tease_hits = sum(1 for p in tease_patterns if p in lower)
    if tease_hits > 0:
        base += min(0.25, tease_hits * 0.08)
        parts.append(f"tease={tease_hits}")

    score = max(0.0, min(1.0, base))
    return score, " + ".join(parts)


def narrative_arc_score(
    narrative_completeness: float,
    coherence_score: float,
    has_setup: bool,
    has_development: bool,
    has_resolution: bool,
) -> tuple[float, str]:
    """Does the clip have a complete story shape?

    Formula:
      stage_count = count(setup, development, resolution)
      completeness_base = narrative_completeness × 0.40
      coherence_base = coherence_score × 0.25
      stage_bonus = stage_count / 3 × 0.25
      full_arc_bonus = 0.10 if all 3 stages present
      = clamp(0, 1)
    """
    stages = sum([has_setup, has_development, has_resolution])
    parts = [f"completeness={narrative_completeness:.2f}", f"stages={stages}/3"]

    base = narrative_completeness * 0.40
    base += coherence_score * 0.25
    base += (stages / 3.0) * 0.25

    if stages == 3:
        base += 0.10
        parts.append("full_arc")

    score = max(0.0, min(1.0, base))
    return score, " + ".join(parts)


def payoff_satisfaction(
    payoff_score: float,
    coherence_resolution_found: bool,
    ending_energy: float,
    has_callback: bool,
) -> tuple[float, str]:
    """Does the ending feel satisfying?

    Formula:
      base = payoff_score × 0.40
           + resolution_bonus (0.20 if hook resolved)
           + ending_energy × 0.20 (strong finish)
           + callback_bonus (0.10 if references opening)
      = clamp(0, 1)

    A satisfying payoff makes the viewer feel the clip was worth watching.
    """
    base = payoff_score * 0.40
    parts = [f"payoff={payoff_score:.2f}"]

    if coherence_resolution_found:
        base += 0.20
        parts.append("resolved")

    base += ending_energy * 0.20
    if ending_energy > 0.5:
        parts.append(f"strong_end={ending_energy:.2f}")

    if has_callback:
        base += 0.10
        parts.append("callback")

    score = max(0.0, min(1.0, base))
    return score, " + ".join(parts)


def redundancy_penalty(
    speech_text: str,
    duration: float,
    unique_concept_ratio: float,
) -> tuple[float, str]:
    """Does the clip repeat itself or drag?

    Formula:
      repetition_ratio = 1 - (unique_words / total_words)
      drag_factor = max(0, (duration - 45) / 30)  # Penalty starts at 45s
      concept_sparsity = 1 - unique_concept_ratio

      penalty = repetition_ratio × 0.40
             + drag_factor × 0.30
             + concept_sparsity × 0.30
      retention_score = 1.0 - penalty  (inverted: high = no redundancy)
      = clamp(0, 1)

    Returns score where 1.0 = zero redundancy, 0.0 = very repetitive/draggy.
    """
    words = speech_text.lower().split() if speech_text else []
    total = len(words) or 1
    unique = len(set(words))
    repetition = 1.0 - (unique / total)
    parts = [f"repeat={repetition:.2f}"]

    drag = max(0.0, (duration - 45.0) / 30.0)
    drag = min(1.0, drag)
    if drag > 0:
        parts.append(f"drag={drag:.2f}")

    sparsity = 1.0 - unique_concept_ratio
    parts.append(f"sparsity={sparsity:.2f}")

    penalty = repetition * 0.40 + drag * 0.30 + sparsity * 0.30
    score = max(0.0, min(1.0, 1.0 - penalty))
    return score, " + ".join(parts)


def loop_potential(
    duration: float,
    motion_intensity: float,
    emotional_intensity: float,
    word_count: int,
    has_visual_payoff: bool,
) -> tuple[float, str]:
    """Would a viewer re-watch this? (loop/replay score)

    Formula:
      short_bonus = max(0, 1 - duration/30) × 0.25  (shorter = more loopable)
      motion_base = motion_intensity × 0.25
      emotion_base = emotional_intensity × 0.20
      visual_payoff_bonus = 0.15 if has visual resolution
      low_speech_bonus = max(0, 1 - word_count/50) × 0.15
      = clamp(0, 1)

    Short + visual + emotional = perfect loop.
    """
    short_b = max(0.0, 1.0 - duration / 30.0) * 0.25
    parts = []
    if short_b > 0.05:
        parts.append(f"short={duration:.0f}s")

    motion_b = motion_intensity * 0.25
    if motion_intensity > 0.5:
        parts.append(f"motion={motion_intensity:.2f}")

    emotion_b = emotional_intensity * 0.20
    if emotional_intensity > 0.5:
        parts.append(f"emotion={emotional_intensity:.2f}")

    visual_b = 0.15 if has_visual_payoff else 0.0
    if has_visual_payoff:
        parts.append("visual_payoff")

    low_speech_b = max(0.0, 1.0 - word_count / 50.0) * 0.15
    if word_count < 30:
        parts.append(f"low_speech={word_count}w")

    score = max(0.0, min(1.0, short_b + motion_b + emotion_b + visual_b + low_speech_b))
    return score, " + ".join(parts) or "no loop signals"


def cut_naturalness(
    starts_mid_word: bool,
    ends_mid_word: bool,
    starts_mid_sentence: bool,
    ends_mid_sentence: bool,
    boundary_snapped: bool,
) -> tuple[float, str]:
    """Do the start/end feel natural (not jarring)?

    Formula:
      base = 1.0
      - 0.30 if starts mid-word (hard cut)
      - 0.30 if ends mid-word
      - 0.15 if starts mid-sentence (soft cut)
      - 0.15 if ends mid-sentence
      + 0.10 if boundaries snapped to silence/scene change
      = clamp(0, 1)

    Natural cuts = high retention at start + satisfying stop at end.
    """
    base = 1.0
    parts = []

    if starts_mid_word:
        base -= 0.30
        parts.append("cut_start_word")
    if ends_mid_word:
        base -= 0.30
        parts.append("cut_end_word")
    if starts_mid_sentence and not starts_mid_word:
        base -= 0.15
        parts.append("cut_start_sentence")
    if ends_mid_sentence and not ends_mid_word:
        base -= 0.15
        parts.append("cut_end_sentence")
    if boundary_snapped:
        base += 0.10
        parts.append("snapped")

    score = max(0.0, min(1.0, base))
    return score, " + ".join(parts) or "natural_cuts"


# ══════════════════════════════════════════════════════════════════════
# INTENT-AWARE WEIGHT PROFILES
# ══════════════════════════════════════════════════════════════════════

# Weight vectors per intent (7 metrics, sum ~= 1.0)
# Order: [opening_arrest, curiosity_gap, narrative_arc, payoff_satisfaction,
#         redundancy_penalty, loop_potential, cut_naturalness]

INTENT_RETENTION_WEIGHTS: dict[str, tuple[float, ...]] = {
    "hook":    (0.30, 0.25, 0.05, 0.05, 0.15, 0.10, 0.10),
    "story":   (0.10, 0.10, 0.30, 0.20, 0.15, 0.05, 0.10),
    "payoff":  (0.05, 0.05, 0.15, 0.35, 0.15, 0.10, 0.15),
    "shock":   (0.25, 0.15, 0.05, 0.10, 0.10, 0.25, 0.10),
    "insight": (0.10, 0.20, 0.15, 0.10, 0.25, 0.05, 0.15),
    "loop":    (0.10, 0.05, 0.05, 0.10, 0.10, 0.45, 0.15),
    "unknown": (0.15, 0.15, 0.15, 0.15, 0.15, 0.10, 0.15),
}

RETENTION_METRIC_NAMES = (
    "opening_arrest", "curiosity_gap", "narrative_arc",
    "payoff_satisfaction", "redundancy_penalty", "loop_potential",
    "cut_naturalness",
)


def compute_retention_composite(
    metrics: tuple[float, ...],
    intent: str,
) -> tuple[float, dict[str, float]]:
    """Compute intent-weighted retention score.

    Args:
        metrics: 7 metric scores in RETENTION_METRIC_NAMES order.
        intent: The classified editorial intent.

    Returns:
        (composite_score, breakdown_dict)
    """
    weights = INTENT_RETENTION_WEIGHTS.get(intent, INTENT_RETENTION_WEIGHTS["unknown"])
    total = sum(m * w for m, w in zip(metrics, weights))
    breakdown = {
        name: round(score, 3)
        for name, score in zip(RETENTION_METRIC_NAMES, metrics)
    }
    return round(max(0.0, min(1.0, total)), 4), breakdown
