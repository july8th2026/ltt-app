"""Evaluation layer types — post-render quality scoring.

Dependencies: base only
Consumed by: evaluation, GUI
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cutclipshort.types.editorial import ClipExplanation


@dataclass(frozen=True)
class EvalMetric:
    """Result from a single quality evaluator."""
    evaluator_name: str
    score: float
    weight: float = 0.0
    passed: bool = True
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ClipScore:
    """Composite quality score for a RENDERED clip."""
    clip_id: Any
    composite_score: float
    per_evaluator: list[EvalMetric]
    gate_passed: bool
    risk_flags: list[str] = field(default_factory=list)
    quality_tier: str = "unknown"
    summary: str = ""
    veto_reason: str = ""
    explanation: ClipExplanation | None = None

    @property
    def failed_metrics(self) -> list[str]:
        return [m.evaluator_name for m in self.per_evaluator if not m.passed]

    @property
    def metrics(self) -> list[EvalMetric]:
        """Deprecated alias — use per_evaluator directly."""
        return self.per_evaluator


@dataclass(frozen=True)
class QualityReport:
    """Complete quality report for a candidate."""
    candidate_id: str
    clip_score: ClipScore | None = None
    pre_export_passed: bool = True
    pre_export_issues: list[str] = field(default_factory=list)
    pre_export_suggestions: list[str] = field(default_factory=list)
    overall_passed: bool = True
