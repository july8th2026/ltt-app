"""Editorial strategy protocol.

Every genre strategy must implement EditorialStrategy.
Strategies find clip candidates and build edit plans.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from cutclipshort.types import (
    AnalysisResult,
    CandidateClip,
    EditConstraints,
    EditPlan,
)


@runtime_checkable
class EditorialStrategy(Protocol):
    """Contract every genre strategy must implement."""

    @property
    def name(self) -> str:
        """Strategy identifier. e.g. 'talking_head', 'podcast'."""
        ...

    @property
    def display_name(self) -> str:
        """Human-readable name for GUI. e.g. 'Talking Head'."""
        ...

    @property
    def supported_content_types(self) -> list[str]:
        """Content types this strategy handles best."""
        ...

    def find_candidates(
        self,
        analysis: AnalysisResult,
        config: dict[str, Any],
    ) -> list[CandidateClip]:
        """Identify and score potential clip segments.

        Scans the unified analysis result for high-value segments.
        Returns ranked list, highest score first.

        Must not modify analysis (it's frozen).
        """
        ...

    def build_plan(
        self,
        candidates: list[CandidateClip],
        constraints: EditConstraints,
        config: dict[str, Any],
    ) -> EditPlan:
        """Select from candidates and produce a concrete edit plan.

        Selects top candidates within constraints, resolves every render
        parameter into a self-contained EditPlan.

        The EditPlan must be self-contained: the render layer only needs
        the plan + source video path, never the analysis cache.
        """
        ...
