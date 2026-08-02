"""Editorial layer types — what the editorial brain produces.

Dependencies: base (TimeRange, PersonDetection, ContentType)
Consumed by: render, evaluation, GUI
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cutclipshort.types.base import (
    ContentType,
    PersonDetection,
    TimeRange,
)


class EditorialIntent(Enum):
    """What editorial purpose a clip serves.

    Each clip MUST be assigned exactly one intent with a confidence score.
    Clips with unknown intent or confidence < 0.3 are filtered out.
    """

    HOOK = "hook"                # Strong opening — grabs attention in first 3s
    STORY = "story"              # Complete narrative arc — setup → development → resolution
    PAYOFF = "payoff"            # Clear conclusion/resolution — satisfying ending
    SHOCK = "shock"              # Unexpected twist, surprise, or dramatic moment
    INSIGHT = "insight"          # Dense information, key learning, or unique perspective
    LOOP = "loop"                # Self-contained moment ideal for infinite replay
    UNKNOWN = "unknown"          # Unclassifiable — will be filtered from final output

    @classmethod
    def from_str(cls, value: str) -> EditorialIntent:
        """Convert string to EditorialIntent, defaulting to UNKNOWN."""
        try:
            return cls(value)
        except ValueError:
            # Handle legacy names
            legacy = {"viral_moment": cls.SHOCK, "controversial": cls.SHOCK, "dense_info": cls.INSIGHT}
            return legacy.get(value, cls.UNKNOWN)


@dataclass(frozen=True)
class CandidateScore:
    """Score breakdown for a clip candidate (pre-render)."""
    overall: float
    hook_strength: float
    pacing: float
    completeness: float
    visual_quality: float
    audio_quality: float
    topic_coherence: float = 0.0
    semantic_richness: float = 0.0

    @property
    def overall_100(self) -> float:
        return round(self.overall * 100, 1)


@dataclass(frozen=True)
class StrengthWeakness:
    """A single strength or weakness with label, score, and detail."""
    label: str
    dimension: str
    score: float
    detail: str
    impact: str = "neutral"


@dataclass(frozen=True)
class ClipExplanation:
    """Complete explainability package for a clip."""
    summary: str
    why_selected: str
    why_rejected: str = ""
    why_not_others: str = ""         # Comparative: why THIS over alternatives
    intent_explanation: str = ""     # Why this intent was assigned (feature-level)
    strengths: list[StrengthWeakness] = field(default_factory=list)
    weaknesses: list[StrengthWeakness] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    risk_level: str = "low"
    score_breakdown: dict[str, float] = field(default_factory=dict)
    debug_trace: str = ""

    @property
    def top_strength(self) -> str:
        return self.strengths[0].label if self.strengths else ""

    @property
    def top_weakness(self) -> str:
        return self.weaknesses[0].label if self.weaknesses else ""

    @property
    def is_risky(self) -> bool:
        return self.risk_level in ("high", "critical")


@dataclass(frozen=True)
class CandidateClip:
    """A potential clip identified by the editorial strategy."""
    candidate_id: str
    time_range: TimeRange
    score: CandidateScore
    content_type: ContentType
    genre_fit: float
    motion_avg: float
    has_speech: bool
    speech_text_preview: str
    transcript_segment_ids: list[int] = field(default_factory=list)
    has_person: bool = True
    person_count: int = 1
    dominant_person_bbox: PersonDetection | None = None
    tags: list[str] = field(default_factory=list)
    hook_text: str = ""
    suggested_hook_type: str = "organic"
    strategy_name: str = ""
    strategy_reasoning: str = ""
    why_selected: str = ""
    why_ranked_higher: str = ""
    why_might_fail: str = ""
    why_not_others: str = ""         # Comparative explanation
    intent_explanation: str = ""     # Why this intent was assigned
    risk_flags: list[str] = field(default_factory=list)
    objective: str = ""
    hook_promise: str = ""
    payoff_resolution: str = ""
    display_title: str = ""
    seo_slug: str = ""
    suggested_hashtags: list[str] = field(default_factory=list)
    seo_description: str = ""
    clip_intent: str = "unknown"
    intent_confidence: float = 0.0
    intent_reasoning: str = ""
    intent_features: dict[str, float] = field(default_factory=dict)
    generation_reason: str = ""    # Why this candidate was proposed (from generator)
    cluster_id: int = -1           # Diversity cluster assignment
    topic_label: str = ""
    emotional_peak_intensity: float = 0.0
    narrative_completeness: float = 0.0
    explanation: ClipExplanation | None = None
