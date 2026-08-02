"""Composite scorer V2: quality analysis engine with risk profiling.

Beyond weighted scoring — analyzes the PATTERN of evaluator results
to produce quality tiers, risk flags, and actionable summaries.

V2 architecture:
1. Run all evaluators (parallel-safe, fail-isolated)
2. Compute weighted composite score
3. Analyze result pattern → quality tier
4. Detect risk flags from evaluator diagnostics
5. Generate human-readable summary
6. Gate check: veto + soft gate + pattern gate
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cutclipshort.evaluation.base import Evaluator
from cutclipshort.types import AnalysisResult, ClipScore, ClipSpec, EvalMetric

logger = logging.getLogger(__name__)

# ── Quality tiers ────────────────────────────────────────────────────
_TIER_THRESHOLDS = {
    "excellent": 80.0,
    "good": 65.0,
    "acceptable": 50.0,
    "poor": 35.0,
    # Below 35 = "reject"
}

# ── Genre-aware gate adjustments ─────────────────────────────────────
# Some genres are harder to score well (action has poor "visual quality"
# from blur, comedy may have "weak pacing" due to timing pauses).
_GENRE_GATE_ADJUSTMENTS: dict[str, dict[str, Any]] = {
    "action": {"veto_threshold": 0.30, "max_soft_failures": 3},
    "comedy": {"veto_threshold": 0.30, "max_soft_failures": 3},
    "nature": {"veto_threshold": 0.25, "max_soft_failures": 3},
    "kids_music": {"veto_threshold": 0.25, "max_soft_failures": 3},
    "animation": {"veto_threshold": 0.25, "max_soft_failures": 3},
    # Speech-heavy genres: stricter
    "talking_head": {"veto_threshold": 0.35, "max_soft_failures": 2},
    "education": {"veto_threshold": 0.35, "max_soft_failures": 2},
    "podcast": {"veto_threshold": 0.35, "max_soft_failures": 2},
}

# ── Veto evaluators (hard fail below threshold) ──────────────────────
_VETO_EVALUATORS = {"pacing", "opening_strength", "semantic_completeness"}
_VETO_THRESHOLD = 0.35  # V3: raised from 0.20 — actually reject bad clips

# ── Soft gate ────────────────────────────────────────────────────────
_MAX_SOFT_FAILURES = 2  # Allow up to 2 minor failures

# ── Risk flag detection rules ────────────────────────────────────────
_RISK_RULES = {
    "dead_air_start": lambda results: _check_diag(results, "opening_strength", "has_filler", True),
    "weak_hook": lambda results: _check_score(results, "opening_strength", 0.35),
    "energy_drop": lambda results: _check_diag(results, "retention_potential", "sub_energy_arc", 0.5, "<"),
    "mid_clip_silence": lambda results: _check_diag(results, "retention_potential", "sub_sustained_speech", 0.5, "<"),
    "weak_ending": lambda results: _check_diag(results, "retention_potential", "sub_ending_energy", 0.4, "<"),
    "cut_mid_sentence": lambda results: _check_diag(results, "semantic_completeness", "ends_with_punctuation", False),
    "no_resolution": lambda results: _check_diag(results, "semantic_completeness", "has_resolution", False),
    "subtitle_too_fast": lambda results: _check_diag(results, "subtitle_density", "overall_wps", 3.5, ">"),
    "clipping_detected": lambda results: _check_diag(results, "audio_loudness", "clipping_detected", True),
    "low_bitrate": lambda results: _check_diag(results, "visual_quality", "bitrate_kbps", 500, "<"),
    "too_short": lambda results: _check_diag(results, "pacing", "effective_duration_sec", 15, "<"),
    "too_long": lambda results: _check_diag(results, "pacing", "effective_duration_sec", 60, ">"),
}


class CompositeScorer:
    """Quality analysis engine with risk profiling.

    Produces:
    - Composite score (0-100)
    - Quality tier (excellent/good/acceptable/poor/reject)
    - Risk flags (actionable issues)
    - Summary (human-readable)
    - Gate result (pass/fail/veto)
    """

    def __init__(self, evaluators: list[Evaluator]) -> None:
        self._evaluators = evaluators
        total_weight = sum(e.weight for e in evaluators)
        if total_weight > 0:
            self._normalized_weights = {
                e.name: e.weight / total_weight for e in evaluators
            }
        else:
            self._normalized_weights = {
                e.name: 1.0 / max(1, len(evaluators)) for e in evaluators
            }

    def score(
        self,
        clip_id: Any,
        rendered_path: Path,
        clip_spec: ClipSpec,
        analysis: AnalysisResult,
        genre: str = "",
    ) -> ClipScore:
        """Run all evaluators and produce comprehensive quality analysis."""
        # 1. Run evaluators
        results = self._run_evaluators(clip_id, rendered_path, clip_spec, analysis)

        # 2. Weighted composite
        composite = 0.0
        for r in results:
            weight = self._normalized_weights.get(r.evaluator_name, 0.0)
            composite += r.score * weight
        composite_100 = round(composite * 100, 1)

        # 3. Quality tier
        quality_tier = _compute_tier(composite_100)

        # 4. Risk flags
        risk_flags = _detect_risk_flags(results)

        # 5. Gate check (genre-aware)
        gate_passed, veto_reason = self._check_gate(results, composite_100, genre)

        # 6. Summary
        summary = _build_summary(results, composite_100, quality_tier, risk_flags, gate_passed)

        # 7. Build explanation
        from cutclipshort.evaluation.explainability import explain_score
        explanation = explain_score(
            per_evaluator=results,
            composite_100=composite_100,
            quality_tier=quality_tier,
            gate_passed=gate_passed,
            veto_reason=veto_reason,
        )

        clip_score = ClipScore(
            clip_id=clip_id,
            composite_score=composite_100,
            per_evaluator=results,
            gate_passed=gate_passed,
            risk_flags=risk_flags,
            quality_tier=quality_tier,
            summary=summary,
            veto_reason=veto_reason,
            explanation=explanation,
        )

        log_level = logging.INFO if gate_passed else logging.WARNING
        logger.log(
            log_level,
            "Clip %s: %.1f/100 [%s] gate=%s%s%s",
            clip_id, composite_100, quality_tier,
            "PASS" if gate_passed else "FAIL",
            f" veto={veto_reason}" if veto_reason else "",
            f" risks={risk_flags}" if risk_flags else "",
        )

        return clip_score

    def _run_evaluators(
        self, clip_id: Any, rendered_path: Path,
        clip_spec: ClipSpec, analysis: AnalysisResult,
    ) -> list[EvalMetric]:
        """Run all evaluators with fail isolation."""
        results: list[EvalMetric] = []
        for evaluator in self._evaluators:
            try:
                result = evaluator.evaluate(rendered_path, clip_spec, analysis)
                results.append(result)
            except Exception as e:
                logger.error(
                    "Evaluator '%s' failed for clip %s: %s",
                    evaluator.name, clip_id, e,
                )
                results.append(EvalMetric(
                    evaluator_name=evaluator.name,
                    score=0.0, weight=evaluator.weight,
                    passed=False, diagnostics={"error": str(e)},
                ))
        return results

    def _check_gate(
        self, results: list[EvalMetric], composite_100: float,
        genre: str = "",
    ) -> tuple[bool, str]:
        """Multi-level gate check with genre-aware adjustments.

        Returns: (passed, veto_reason)
        """
        # Genre-aware thresholds
        genre_adj = _GENRE_GATE_ADJUSTMENTS.get(genre, {})
        veto_threshold = genre_adj.get("veto_threshold", _VETO_THRESHOLD)
        max_soft = genre_adj.get("max_soft_failures", _MAX_SOFT_FAILURES)

        # Level 1: Veto evaluators (hard fail)
        for r in results:
            if r.evaluator_name in _VETO_EVALUATORS and r.score < veto_threshold:
                reason = f"{r.evaluator_name} scored {r.score:.2f} (veto threshold {veto_threshold:.2f})"
                return False, reason

        # Level 2: Pattern-based veto (AI-like rules)
        # Multiple critical failures = systemic problem
        critical_failures = [
            r for r in results
            if r.score < 0.3 and r.evaluator_name not in _VETO_EVALUATORS
        ]
        if len(critical_failures) >= 3:
            names = [r.evaluator_name for r in critical_failures]
            return False, f"3+ critical failures: {', '.join(names)}"

        # Level 3: Composite too low
        if composite_100 < 25.0:
            return False, f"composite {composite_100:.1f} below minimum 25.0"

        # Level 4: Soft gate (count non-critical failures, genre-aware)
        soft_failures = sum(1 for r in results if not r.passed)
        if soft_failures > max_soft:
            return False, ""  # Soft fail, no veto reason

        return True, ""


# ══════════════════════════════════════════════════════════════════════════
# QUALITY ANALYSIS FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════

def _compute_tier(composite_100: float) -> str:
    """Map composite score to quality tier."""
    for tier, threshold in _TIER_THRESHOLDS.items():
        if composite_100 >= threshold:
            return tier
    return "reject"


def _detect_risk_flags(results: list[EvalMetric]) -> list[str]:
    """Detect risk flags from evaluator diagnostics."""
    flags: list[str] = []
    for flag_name, check_fn in _RISK_RULES.items():
        try:
            if check_fn(results):
                flags.append(flag_name)
        except Exception as exc:
            logger.debug("Risk rule '%s' check failed: %s", flag_name, exc)
    return flags


def _check_diag(
    results: list[EvalMetric],
    evaluator: str,
    diag_key: str,
    value: Any,
    op: str = "==",
) -> bool:
    """Check a specific diagnostic value from an evaluator result."""
    for r in results:
        if r.evaluator_name == evaluator:
            diag_val = r.diagnostics.get(diag_key)
            if diag_val is None:
                return False
            if op == "==":
                return diag_val == value
            if op == "<":
                return diag_val < value
            if op == ">":
                return diag_val > value
    return False


def _check_score(results: list[EvalMetric], evaluator: str, threshold: float) -> bool:
    """Check if an evaluator scored below threshold."""
    for r in results:
        if r.evaluator_name == evaluator:
            return r.score < threshold
    return False


def _build_summary(
    results: list[EvalMetric],
    composite: float,
    tier: str,
    risk_flags: list[str],
    gate_passed: bool,
) -> str:
    """Build human-readable quality summary."""
    parts: list[str] = []

    # Top-level
    parts.append(f"{tier.upper()} ({composite:.0f}/100)")

    # Best metrics
    top = sorted(results, key=lambda r: r.score, reverse=True)
    if top and top[0].score >= 0.7:
        parts.append(f"Strengths: {top[0].evaluator_name}={top[0].score:.0%}")

    # Worst metrics
    if top and top[-1].score < 0.5:
        parts.append(f"Weakness: {top[-1].evaluator_name}={top[-1].score:.0%}")

    # Risk summary
    if risk_flags:
        parts.append(f"Risks: {', '.join(risk_flags[:3])}")

    if not gate_passed:
        parts.append("BLOCKED by quality gate")

    return " | ".join(parts)
