"""Explainability engine — generates human-readable explanations for clips.

Two entry points:
1. explain_candidate() — pre-render: why was this clip selected/rejected?
2. explain_score()     — post-render: what's the quality verdict?

Both produce a ClipExplanation object consumable by GUI, logs, and debug.
"""

from __future__ import annotations

import logging
from typing import Any

from cutclipshort.types import (
    ClipExplanation,
    EvalMetric,
    StrengthWeakness,
)

logger = logging.getLogger(__name__)

# ── Dimension labels (human-readable names for scoring dimensions) ────
_DIM_LABELS = {
    "hook": "Hook / Opening",
    "pacing": "Pacing & Duration",
    "payoff": "Payoff / Ending",
    "visual": "Visual Quality",
    "audio": "Audio Quality",
    "content": "Content Density",
    "coherence": "Coherence",
    "semantic": "Semantic Richness",
    "genre": "Genre Match",
    "retention": "Retention Potential",
    "opening": "Opening Strength",
    "subtitle": "Subtitle Readability",
}

# ── Strength/weakness thresholds ─────────────────────────────────────
_STRONG_THRESHOLD = 0.70
_WEAK_THRESHOLD = 0.40
_CRITICAL_THRESHOLD = 0.25

# ── Risk escalation ─────────────────────────────────────────────────
_RISK_LEVELS = {
    0: "low",
    1: "low",
    2: "medium",
    3: "high",
    4: "critical",
}


# ══════════════════════════════════════════════════════════════════════════
# CANDIDATE EXPLANATION (pre-render)
# ══════════════════════════════════════════════════════════════════════════

def explain_candidate(
    *,
    composite_score: float,
    hook_score: float,
    hook_type: str,
    hook_text: str,
    payoff_score: float,
    payoff_type: str,
    pacing_score: float,
    visual_score: float,
    audio_score: float,
    content_density: float,
    coherence_score: float,
    coherence_resolved: bool,
    hook_promise: str,
    resolution_type: str,
    genre_cue_score: float,
    semantic_score: float,
    speech_ratio: float,
    clip_intent: str,
    intent_confidence: float,
    topic_label: str,
    filler_ratio: float,
    reasoning: str,
    is_selected: bool = True,
    rejection_reason: str = "",
    # V4: Comparative + intent explanation inputs
    rank_position: int = 0,
    total_candidates: int = 0,
    runner_up_score: float = 0.0,
    runner_up_intent: str = "",
    selection_breakdown: dict[str, float] | None = None,
    intent_features: dict[str, float] | None = None,
    intent_reasoning: str = "",
    generation_reason: str = "",
) -> ClipExplanation:
    """Build complete explanation for a candidate clip.

    V4 additions:
    - why_not_others: Comparative explanation vs alternatives
    - intent_explanation: Feature-level intent assignment reasoning
    """

    # ── Score breakdown ──────────────────────────────────────────
    breakdown = {
        "hook": round(hook_score, 3),
        "pacing": round(pacing_score, 3),
        "payoff": round(payoff_score, 3),
        "visual": round(visual_score, 3),
        "audio": round(audio_score, 3),
        "content": round(content_density, 3),
        "coherence": round(coherence_score, 3),
        "semantic": round(semantic_score, 3),
        "genre": round(genre_cue_score, 3),
    }

    # ── Detect strengths ─────────────────────────────────────────
    strengths: list[StrengthWeakness] = []

    if hook_score >= _STRONG_THRESHOLD:
        detail = _hook_detail(hook_type, hook_text, hook_score)
        strengths.append(StrengthWeakness(
            label=f"Strong {hook_type} hook",
            dimension="hook", score=hook_score,
            detail=detail, impact="positive",
        ))

    if payoff_score >= _STRONG_THRESHOLD:
        strengths.append(StrengthWeakness(
            label=f"Clear {payoff_type} ending",
            dimension="payoff", score=payoff_score,
            detail=f"Payoff type: {payoff_type}, score: {payoff_score:.0%}",
            impact="positive",
        ))

    if coherence_resolved:
        strengths.append(StrengthWeakness(
            label=f"{hook_promise} resolved with {resolution_type}",
            dimension="coherence", score=coherence_score,
            detail=f"Hook promise ({hook_promise}) is resolved in the payoff zone",
            impact="positive",
        ))

    if pacing_score >= _STRONG_THRESHOLD:
        strengths.append(StrengthWeakness(
            label="Good pacing",
            dimension="pacing", score=pacing_score,
            detail="Duration and speech rate are optimal for the platform",
            impact="positive",
        ))

    if content_density >= _STRONG_THRESHOLD:
        strengths.append(StrengthWeakness(
            label="Information dense",
            dimension="content", score=content_density,
            detail="High unique concept count with good words-per-second ratio",
            impact="positive",
        ))

    if genre_cue_score >= 0.5:
        strengths.append(StrengthWeakness(
            label="Strong genre match",
            dimension="genre", score=genre_cue_score,
            detail=f"Content matches genre expectations (score: {genre_cue_score:.0%})",
            impact="positive",
        ))

    if semantic_score >= _STRONG_THRESHOLD:
        strengths.append(StrengthWeakness(
            label="Semantically rich",
            dimension="semantic", score=semantic_score,
            detail="Good narrative structure, emotional depth, and topic coherence",
            impact="positive",
        ))

    # Sort by score descending
    strengths.sort(key=lambda s: s.score, reverse=True)

    # ── Detect weaknesses ────────────────────────────────────────
    weaknesses: list[StrengthWeakness] = []

    if hook_score < _WEAK_THRESHOLD:
        weaknesses.append(StrengthWeakness(
            label="Weak opening",
            dimension="hook", score=hook_score,
            detail="First 3 seconds lack a clear hook to grab attention",
            impact="negative",
        ))

    if payoff_score < _WEAK_THRESHOLD:
        weaknesses.append(StrengthWeakness(
            label=f"Incomplete ending ({payoff_type})",
            dimension="payoff", score=payoff_score,
            detail="Clip ends without clear resolution or natural stopping point",
            impact="negative",
        ))

    if not coherence_resolved and hook_promise != "none":
        weaknesses.append(StrengthWeakness(
            label=f"Unresolved {hook_promise}",
            dimension="coherence", score=coherence_score,
            detail=f"Hook promises a {hook_promise} but payoff doesn't deliver",
            impact="negative",
        ))

    if speech_ratio < 0.3:
        weaknesses.append(StrengthWeakness(
            label="Low speech content",
            dimension="content", score=speech_ratio,
            detail=f"Only {speech_ratio:.0%} of clip has speech",
            impact="negative",
        ))

    if filler_ratio > 0.10:
        weaknesses.append(StrengthWeakness(
            label="Filler word heavy",
            dimension="content", score=max(0, 1.0 - filler_ratio * 5),
            detail=f"Filler ratio: {filler_ratio:.0%} (um, like, basically...)",
            impact="negative",
        ))

    if visual_score < _WEAK_THRESHOLD:
        weaknesses.append(StrengthWeakness(
            label="Visual quality issues",
            dimension="visual", score=visual_score,
            detail="Low person presence, static frames, or poor framing",
            impact="negative",
        ))

    if audio_score < _WEAK_THRESHOLD:
        weaknesses.append(StrengthWeakness(
            label="Audio quality issues",
            dimension="audio", score=audio_score,
            detail="Inconsistent energy, excessive silence, or noise",
            impact="negative",
        ))

    weaknesses.sort(key=lambda w: w.score)  # Worst first

    # ── Risk flags ───────────────────────────────────────────────
    risk_flags: list[str] = []
    if hook_score < _CRITICAL_THRESHOLD:
        risk_flags.append("very_weak_hook")
    if payoff_type == "incomplete":
        risk_flags.append("incomplete_ending")
    if not coherence_resolved and hook_promise != "none":
        risk_flags.append("unresolved_promise")
    if speech_ratio < 0.2:
        risk_flags.append("minimal_speech")
    if filler_ratio > 0.15:
        risk_flags.append("excessive_filler")
    if pacing_score < _CRITICAL_THRESHOLD:
        risk_flags.append("poor_pacing")

    risk_level = _RISK_LEVELS.get(min(len(risk_flags), 4), "critical")

    # ── Build summary ────────────────────────────────────────────
    summary_parts: list[str] = []
    if strengths:
        summary_parts.append(strengths[0].label)
    if len(strengths) > 1:
        summary_parts.append(strengths[1].label)
    if weaknesses:
        summary_parts.append(weaknesses[0].label)
    if clip_intent != "unknown":
        summary_parts.append(f"Intent: {clip_intent}")

    summary = " | ".join(summary_parts) if summary_parts else f"Score: {composite_score:.0%}"

    # ── Why selected/rejected ────────────────────────────────────
    if is_selected:
        why_parts = []
        if strengths:
            why_parts.append(strengths[0].detail)
        if coherence_resolved:
            why_parts.append(f"Coherent: {hook_promise} -> {resolution_type}")
        if topic_label:
            why_parts.append(f"Topic: {topic_label}")
        why_selected = "; ".join(why_parts) if why_parts else f"Composite score {composite_score:.0%}"
    else:
        why_selected = ""

    why_rejected = rejection_reason if not is_selected else ""

    # ── V4: Comparative explanation (why this over others) ──────
    why_not_others = _build_why_not_others(
        composite_score=composite_score,
        rank_position=rank_position,
        total_candidates=total_candidates,
        runner_up_score=runner_up_score,
        runner_up_intent=runner_up_intent,
        selection_breakdown=selection_breakdown,
        strengths=strengths,
        generation_reason=generation_reason,
    )

    # ── V4: Intent explanation (feature-level) ──────────────────
    intent_expl = _build_intent_explanation(
        clip_intent=clip_intent,
        intent_confidence=intent_confidence,
        intent_features=intent_features,
        intent_reasoning=intent_reasoning,
    )

    return ClipExplanation(
        summary=summary,
        why_selected=why_selected,
        why_rejected=why_rejected,
        why_not_others=why_not_others,
        intent_explanation=intent_expl,
        strengths=strengths,
        weaknesses=weaknesses,
        risk_flags=risk_flags,
        risk_level=risk_level,
        score_breakdown=breakdown,
        debug_trace=reasoning,
    )


# ══════════════════════════════════════════════════════════════════════════
# CLIP SCORE EXPLANATION (post-render)
# ══════════════════════════════════════════════════════════════════════════

def explain_score(
    per_evaluator: list[EvalMetric],
    composite_100: float,
    quality_tier: str,
    gate_passed: bool,
    veto_reason: str = "",
) -> ClipExplanation:
    """Build explanation from post-render evaluation results."""

    strengths: list[StrengthWeakness] = []
    weaknesses: list[StrengthWeakness] = []
    risk_flags: list[str] = []
    breakdown: dict[str, float] = {}

    for m in per_evaluator:
        # Extract dimension from evaluator name
        dim = m.evaluator_name.split("_")[0] if "_" in m.evaluator_name else m.evaluator_name
        dim_label = _DIM_LABELS.get(dim, m.evaluator_name)
        breakdown[m.evaluator_name] = round(m.score, 3)

        reason = m.diagnostics.get("reason", "")

        if m.score >= _STRONG_THRESHOLD:
            strengths.append(StrengthWeakness(
                label=f"{dim_label}: {m.score:.0%}",
                dimension=dim, score=m.score,
                detail=reason or f"{m.evaluator_name} scored {m.score:.0%}",
                impact="positive",
            ))
        elif m.score < _WEAK_THRESHOLD:
            weaknesses.append(StrengthWeakness(
                label=f"{dim_label}: {m.score:.0%}",
                dimension=dim, score=m.score,
                detail=reason or f"{m.evaluator_name} scored {m.score:.0%}",
                impact="negative",
            ))

            if m.score < _CRITICAL_THRESHOLD:
                risk_flags.append(f"critical_{m.evaluator_name}")

        if not m.passed:
            risk_flags.append(f"failed_{m.evaluator_name}")

    strengths.sort(key=lambda s: s.score, reverse=True)
    weaknesses.sort(key=lambda w: w.score)
    risk_level = _RISK_LEVELS.get(min(len(risk_flags), 4), "critical")

    # Summary
    parts = [f"{quality_tier.upper()} ({composite_100:.0f}/100)"]
    if strengths:
        parts.append(f"Best: {strengths[0].label}")
    if weaknesses:
        parts.append(f"Worst: {weaknesses[0].label}")
    summary = " | ".join(parts)

    why = f"Composite {composite_100:.0f}/100, tier={quality_tier}"
    if veto_reason:
        why_rejected = f"VETOED: {veto_reason}"
    elif not gate_passed:
        why_rejected = f"Gate failed: {', '.join(risk_flags[:3])}"
    else:
        why_rejected = ""

    return ClipExplanation(
        summary=summary,
        why_selected=why if gate_passed else "",
        why_rejected=why_rejected,
        strengths=strengths,
        weaknesses=weaknesses,
        risk_flags=risk_flags,
        risk_level=risk_level,
        score_breakdown=breakdown,
        debug_trace=f"evaluators={[m.evaluator_name for m in per_evaluator]}",
    )


# ══════════════════════════════════════════════════════════════════════════
# REJECTION EXPLANATION (for candidates that didn't make the cut)
# ══════════════════════════════════════════════════════════════════════════

def explain_rejection(
    reason: str,
    composite_score: float,
    breakdown: dict[str, float] | None = None,
) -> ClipExplanation:
    """Minimal explanation for a rejected candidate."""
    return ClipExplanation(
        summary=f"Rejected: {reason}",
        why_selected="",
        why_rejected=reason,
        risk_flags=["rejected"],
        risk_level="critical" if composite_score < 0.2 else "high",
        score_breakdown=breakdown or {},
        debug_trace=f"rejection: {reason}, score={composite_score:.3f}",
    )


# ══════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════

def _hook_detail(hook_type: str, hook_text: str, score: float) -> str:
    """Generate detailed hook explanation."""
    preview = hook_text[:50] + "..." if len(hook_text) > 50 else hook_text
    type_desc = {
        "question": "Creates curiosity gap — viewer wants the answer",
        "statistic": "Numbers establish authority and specificity",
        "keyword": "Attention keyword triggers engagement",
        "curiosity": "Teases information — viewer must keep watching",
        "bold": "Strong claim demands viewer attention",
        "conflict": "Contrarian position creates tension",
        "surprise": "Unexpected statement disrupts scroll pattern",
        "emotional": "Personal/emotional connection draws viewer in",
        "reaction": "High energy captures immediate attention",
    }
    desc = type_desc.get(hook_type, "Organic opening")
    return f'"{preview}" — {desc} ({score:.0%})'


# ══════════════════════════════════════════════════════════════════════════
# V4: COMPARATIVE EXPLANATION
# ══════════════════════════════════════════════════════════════════════════

def _build_why_not_others(
    *,
    composite_score: float,
    rank_position: int,
    total_candidates: int,
    runner_up_score: float,
    runner_up_intent: str,
    selection_breakdown: dict[str, float] | None,
    strengths: list[StrengthWeakness],
    generation_reason: str,
) -> str:
    """Build comparative explanation: why THIS clip over alternatives.

    Combines:
    - Score gap vs runner-up
    - Which fitness objectives gave this clip the edge
    - What unique strengths this clip has
    - Where this clip came from (generation pass)
    """
    parts: list[str] = []

    if rank_position > 0 and total_candidates > 0:
        parts.append(f"Ranked #{rank_position} of {total_candidates}")

    # Score margin over runner-up
    if runner_up_score > 0 and composite_score > 0:
        margin = (composite_score - runner_up_score) * 100
        if margin > 5:
            parts.append(f"Score +{margin:.0f} pts above next candidate")
        elif margin > 0:
            parts.append(f"Narrowly ahead (+{margin:.1f} pts)")
        else:
            parts.append("Selected despite lower score (diversity bonus)")

    # Fitness breakdown: what gave the edge
    if selection_breakdown:
        top_factors = sorted(
            [(k, v) for k, v in selection_breakdown.items() if k != "fitness"],
            key=lambda x: x[1], reverse=True,
        )[:2]
        if top_factors:
            edge = " + ".join(f"{k}={v:.2f}" for k, v in top_factors)
            parts.append(f"Won by: {edge}")

    # Unique strength
    if strengths:
        top = strengths[0]
        parts.append(f"Standout: {top.label} ({top.score:.0%})")

    # Generation origin
    if generation_reason:
        parts.append(f"Source: {generation_reason[:60]}")

    # Runner-up context
    if runner_up_intent and runner_up_intent != "unknown":
        parts.append(f"Runner-up was {runner_up_intent} clip")

    return " | ".join(parts) if parts else "Selected by composite score"


# ══════════════════════════════════════════════════════════════════════════
# V4: INTENT EXPLANATION
# ══════════════════════════════════════════════════════════════════════════

_INTENT_DESCRIPTIONS = {
    "hook": "Grabs attention in first 3 seconds — designed to stop the scroll",
    "story": "Complete narrative arc — setup, development, resolution",
    "payoff": "Satisfying conclusion — resolves a question or delivers value",
    "shock": "Unexpected moment — surprise, drama, or controversy",
    "insight": "Dense information — key learning or unique perspective",
    "loop": "Replay-worthy moment — short, visual, satisfying",
}

_FEATURE_IMPACT_LABELS = {
    "hook_score": "hook strength",
    "payoff_score": "ending quality",
    "emotional_intensity": "emotional impact",
    "narrative_completeness": "story arc",
    "content_density": "information density",
    "audio_energy": "audio energy",
    "motion_intensity": "visual motion",
    "conflict_hits": "conflict vocabulary",
    "insight_hits": "educational markers",
    "loop_hits": "replay markers",
    "exclamation_count": "exclamation energy",
    "question_count": "question hooks",
}


def _build_intent_explanation(
    *,
    clip_intent: str,
    intent_confidence: float,
    intent_features: dict[str, float] | None,
    intent_reasoning: str,
) -> str:
    """Build feature-level intent assignment explanation.

    Explains WHY this intent was assigned by showing which features
    drove the classification decision.
    """
    parts: list[str] = []

    # Intent description
    desc = _INTENT_DESCRIPTIONS.get(clip_intent, "Unclassified clip")
    parts.append(f"{clip_intent.upper()}: {desc}")

    # Confidence level
    if intent_confidence >= 0.8:
        parts.append(f"Confidence: {intent_confidence:.0%} (strong)")
    elif intent_confidence >= 0.5:
        parts.append(f"Confidence: {intent_confidence:.0%} (moderate)")
    elif intent_confidence >= 0.25:
        parts.append(f"Confidence: {intent_confidence:.0%} (weak)")
    else:
        parts.append(f"Confidence: {intent_confidence:.0%} (very weak)")

    # Top driving features
    if intent_features:
        scored = [
            (k, v) for k, v in intent_features.items()
            if v > 0.5 and k in _FEATURE_IMPACT_LABELS
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        if scored:
            drivers = [
                f"{_FEATURE_IMPACT_LABELS[k]} ({v:.0%})"
                for k, v in scored[:3]
            ]
            parts.append(f"Driven by: {', '.join(drivers)}")

    # Raw classifier reasoning (from intent_classifier)
    if intent_reasoning:
        parts.append(f"Classifier: {intent_reasoning[:80]}")

    return " | ".join(parts)
