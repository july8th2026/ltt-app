"""Semantic layer types — editorial brain V2 enrichment.

Dependencies: base (TimeRange)
Consumed by: editorial, evaluation
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cutclipshort.types.base import TimeRange


@dataclass(frozen=True)
class TopicSegment:
    """A semantically coherent topic block in the transcript."""
    topic_id: int
    time_range: TimeRange
    topic_label: str
    keywords: list[str]
    transcript_segment_ids: list[int]
    coherence_score: float
    boundary_confidence: float


@dataclass(frozen=True)
class NarrativeArc:
    """A detected story arc spanning multiple transcript segments."""
    arc_id: int
    time_range: TimeRange
    stages: dict[str, TimeRange]
    completeness: float
    climax_intensity: float
    transcript_segment_ids: list[int]


@dataclass(frozen=True)
class EmotionalSpike:
    """A detected emotional intensity peak in the timeline."""
    spike_id: int
    time_range: TimeRange
    peak_time: float
    intensity: float
    emotion_type: str
    source: str
    transcript_segment_ids: list[int]


@dataclass(frozen=True)
class ConceptCluster:
    """A group of transcript segments sharing semantic meaning."""
    cluster_id: int
    concept_label: str
    keywords: frozenset[str]
    segment_ids: list[int]
    time_ranges: list[TimeRange]
    cohesion_score: float


@dataclass(frozen=True)
class SemanticContext:
    """Aggregated output of the semantic analysis layer."""
    topic_segments: list[TopicSegment] = field(default_factory=list)
    narrative_arcs: list[NarrativeArc] = field(default_factory=list)
    emotional_spikes: list[EmotionalSpike] = field(default_factory=list)
    concept_clusters: list[ConceptCluster] = field(default_factory=list)
    has_narrative: bool = False
    has_emotions: bool = False
    topic_count: int = 0
    dominant_emotion: str = "neutral"

    @property
    def is_empty(self) -> bool:
        return not self.topic_segments and not self.narrative_arcs and not self.emotional_spikes
