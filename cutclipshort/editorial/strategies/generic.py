"""Generic editorial strategy — works for any genre via the Editorial Brain.

All genre-specific behavior comes from the GenreProfile.
This strategy is the default fallback and also serves as the base
for genre strategies that don't need custom logic beyond their profile.
"""

from __future__ import annotations

import logging
from typing import Any

from cutclipshort.editorial.brain import run_editorial
from cutclipshort.editorial.genre_profiles import get_profile
from cutclipshort.types import (
    AnalysisResult,
    CandidateClip,
    EditConstraints,
    EditPlan,
)

logger = logging.getLogger(__name__)


class GenericStrategy:
    """Genre-agnostic strategy powered by GenreProfile weights.

    Works for: podcast, interview, review, storytelling, comedy,
    education, news_commentary — or any future genre.
    """

    def __init__(self, genre: str = "talking_head") -> None:
        self._genre = genre
        self._profile = get_profile(genre)

    @property
    def name(self) -> str:
        return self._genre

    @property
    def display_name(self) -> str:
        return self._profile.display_name

    @property
    def supported_content_types(self) -> list[str]:
        return [self._genre]

    def find_candidates(
        self,
        analysis: AnalysisResult,
        config: dict[str, Any],
    ) -> list[CandidateClip]:
        constraints = EditConstraints(
            min_clip_duration_sec=config.get(
                "min_clip_duration_sec",
                self._profile.ideal_min_sec,
            ),
            max_clip_duration_sec=config.get(
                "max_clip_duration_sec",
                self._profile.ideal_max_sec + 10,
            ),
            target_clip_count=config.get("target_clip_count", 5),
            max_clip_count=config.get("max_clip_count", 20),
        )

        candidates, _plan = run_editorial(
            analysis=analysis,
            constraints=constraints,
            genre=self._genre,
            user_overrides=config,
        )
        return candidates

    def build_plan(
        self,
        candidates: list[CandidateClip],
        constraints: EditConstraints,
        config: dict[str, Any],
    ) -> EditPlan:
        from cutclipshort.editorial.edit_plan_builder import build_edit_plan
        analysis = config.get("_analysis")
        if analysis is None:
            raise ValueError("config['_analysis'] required for build_plan")
        return build_edit_plan(
            candidates, analysis, constraints, self._profile, config,
        )
