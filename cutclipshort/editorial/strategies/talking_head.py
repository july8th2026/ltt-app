"""Talking head editorial strategy — uses the Editorial Brain.

This strategy class is a thin adapter that satisfies the EditorialStrategy
protocol using the new editorial brain pipeline.
"""

from __future__ import annotations

import logging
from typing import Any

from cutclipshort.editorial.brain import run_editorial
from cutclipshort.editorial.constraints import get_constraints
from cutclipshort.editorial.genre_profiles import get_profile
from cutclipshort.types import (
    AnalysisResult,
    CandidateClip,
    EditConstraints,
    EditPlan,
)

logger = logging.getLogger(__name__)


class TalkingHeadStrategy:
    """Editorial strategy for talking head content.

    Uses the editorial brain with the talking_head genre profile.
    """

    @property
    def name(self) -> str:
        return "talking_head"

    @property
    def display_name(self) -> str:
        return "Talking Head"

    @property
    def supported_content_types(self) -> list[str]:
        return ["talking_head"]

    def find_candidates(
        self,
        analysis: AnalysisResult,
        config: dict[str, Any],
    ) -> list[CandidateClip]:
        """Find candidates using the editorial brain."""
        constraints = EditConstraints(
            min_clip_duration_sec=config.get("min_clip_duration_sec", 15.0),
            max_clip_duration_sec=config.get("max_clip_duration_sec", 60.0),
            target_clip_count=config.get("target_clip_count", 5),
            max_clip_count=config.get("max_clip_count", 20),
        )

        candidates, _plan = run_editorial(
            analysis=analysis,
            constraints=constraints,
            genre="talking_head",
            user_overrides=config,
        )
        return candidates

    def build_plan(
        self,
        candidates: list[CandidateClip],
        constraints: EditConstraints,
        config: dict[str, Any],
    ) -> EditPlan:
        """Build plan — requires analysis in config['_analysis']."""
        from cutclipshort.editorial.edit_plan_builder import build_edit_plan
        profile = get_profile("talking_head")
        analysis = config.get("_analysis")
        if analysis is None:
            raise ValueError("config['_analysis'] required for build_plan")
        return build_edit_plan(candidates, analysis, constraints, profile, config)
