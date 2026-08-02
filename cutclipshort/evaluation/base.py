"""Evaluator protocol for quality scoring.

Every quality metric must implement the Evaluator protocol.
The composite scorer aggregates all evaluators into a ClipScore.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from cutclipshort.types import AnalysisResult, ClipSpec, EvalMetric


@runtime_checkable
class Evaluator(Protocol):
    """Contract every quality metric must implement."""

    @property
    def name(self) -> str:
        """Metric identifier. e.g. 'pacing', 'audio_loudness'."""
        ...

    @property
    def weight(self) -> float:
        """Weight in composite score. CompositeScorer normalizes."""
        ...

    def evaluate(
        self,
        rendered_path: Path,
        clip_spec: ClipSpec,
        analysis: AnalysisResult,
    ) -> EvalMetric:
        """Score a single rendered clip.

        Args:
            rendered_path: Path to the rendered clip file.
            clip_spec: The ClipSpec used to render.
            analysis: The full analysis result (for context).

        Returns:
            EvalResult with score and diagnostics.
        """
        ...
