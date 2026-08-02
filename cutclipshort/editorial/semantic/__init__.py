"""Semantic analysis layer — Editorial Brain V2.

Entry point: build_semantic_context(analysis) → SemanticContext

This layer enriches the editorial pipeline with deeper content understanding:
- Topic segmentation (vocabulary divergence boundaries)
- Narrative arc detection (intro → climax → resolution)
- Emotional spike mapping (multi-signal intensity peaks)
- Concept clustering (semantic grouping of related segments)

All modules are optional and fail gracefully — the existing editorial
pipeline works unchanged if this layer produces empty results.
"""

from __future__ import annotations

import logging

from cutclipshort.types import AnalysisResult, SemanticContext

logger = logging.getLogger(__name__)


def build_semantic_context(analysis: AnalysisResult) -> SemanticContext:
    """Build semantic enrichment from analysis data.

    Graceful degradation:
    - No transcript → returns empty SemanticContext
    - Short transcript (<3 segments) → minimal results
    - Each sub-module catches its own exceptions → partial results OK
    """
    if not analysis.transcript or len(analysis.transcript) < 3:
        logger.debug("Semantic layer: insufficient transcript (%d segments), skipping",
                      len(analysis.transcript) if analysis.transcript else 0)
        return SemanticContext()

    # Topic segmentation
    topics = []
    try:
        from cutclipshort.editorial.semantic.topic_segmenter import segment_topics
        topics = segment_topics(analysis.transcript)
        logger.info("Topic segmenter: %d topics found", len(topics))
    except Exception as e:
        logger.warning("Topic segmenter failed: %s", e)

    # Narrative arc detection
    arcs = []
    try:
        from cutclipshort.editorial.semantic.narrative_segmenter import detect_arcs
        arcs = detect_arcs(analysis.transcript, analysis.audio_segments)
        # Assign sequential IDs
        arcs = [
            type(arc)(arc_id=i, **{k: v for k, v in arc.__dict__.items() if k != 'arc_id'})
            for i, arc in enumerate(arcs)
        ]
        logger.info("Narrative segmenter: %d arcs found", len(arcs))
    except Exception as e:
        logger.warning("Narrative segmenter failed: %s", e)

    # Emotional spike detection
    spikes = []
    try:
        from cutclipshort.editorial.semantic.emotion_mapper import detect_spikes
        spikes = detect_spikes(analysis.transcript, analysis.audio_segments)
        logger.info("Emotion mapper: %d spikes found", len(spikes))
    except Exception as e:
        logger.warning("Emotion mapper failed: %s", e)

    # Concept clustering
    clusters = []
    try:
        from cutclipshort.editorial.semantic.concept_clusterer import cluster_segments
        clusters = cluster_segments(analysis.transcript)
        logger.info("Concept clusterer: %d clusters found", len(clusters))
    except Exception as e:
        logger.warning("Concept clusterer failed: %s", e)

    # Summary stats
    has_narrative = any(a.completeness > 0.5 for a in arcs)
    has_emotions = any(s.intensity > 0.5 for s in spikes)
    dominant_emotion = _find_dominant_emotion(spikes)

    ctx = SemanticContext(
        topic_segments=topics,
        narrative_arcs=arcs,
        emotional_spikes=spikes,
        concept_clusters=clusters,
        has_narrative=has_narrative,
        has_emotions=has_emotions,
        topic_count=len(topics),
        dominant_emotion=dominant_emotion,
    )

    logger.info(
        "Semantic context built: %d topics, %d arcs, %d spikes, %d clusters "
        "(narrative=%s, emotions=%s, dominant=%s)",
        len(topics), len(arcs), len(spikes), len(clusters),
        has_narrative, has_emotions, dominant_emotion,
    )

    return ctx


def _find_dominant_emotion(spikes) -> str:
    """Find the most common emotion type across all spikes."""
    if not spikes:
        return "neutral"

    counts: dict[str, float] = {}
    for s in spikes:
        counts[s.emotion_type] = counts.get(s.emotion_type, 0) + s.intensity

    return max(counts, key=counts.get) if counts else "neutral"
