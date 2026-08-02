"""Topic segmenter — detects topic boundaries using vocabulary divergence.

Segments transcript into coherent topic blocks by measuring Jaccard
similarity between sliding windows of concept sets. Where similarity
drops below threshold = topic boundary.

Algorithm:
1. Extract concept set per sentence (reuses semantic_scorer._extract_concepts)
2. Sliding window Jaccard similarity between consecutive N-sentence windows
3. Boundaries where similarity < threshold
4. Merge micro-segments (< min_sentences) into neighbors
5. Label each topic by TF-IDF keywords (within-segment vs corpus)
"""

from __future__ import annotations

import logging
from collections import Counter

from cutclipshort.editorial.semantic_scorer import _extract_concepts
from cutclipshort.types import TimeRange, TranscriptSegment
from cutclipshort.types.semantic import TopicSegment

logger = logging.getLogger(__name__)

_DEFAULT_WINDOW = 3
_DEFAULT_SIMILARITY_THRESHOLD = 0.30
_DEFAULT_MIN_SENTENCES = 3


def segment_topics(
    transcript: list[TranscriptSegment],
    window: int = _DEFAULT_WINDOW,
    similarity_threshold: float = _DEFAULT_SIMILARITY_THRESHOLD,
    min_sentences: int = _DEFAULT_MIN_SENTENCES,
) -> list[TopicSegment]:
    """Segment transcript by topic changes using vocabulary divergence."""
    if len(transcript) < min_sentences:
        if not transcript:
            return []
        return [_single_topic(transcript, 0)]

    # 1. Extract concepts per sentence
    concepts_per = [_extract_concepts(seg.text) for seg in transcript]

    # 2. Compute similarity between consecutive windows
    boundaries: list[int] = []
    similarities: list[float] = []

    for i in range(len(concepts_per) - window):
        left = set()
        for j in range(i, min(i + window, len(concepts_per))):
            left |= concepts_per[j]

        right = set()
        for j in range(i + window, min(i + 2 * window, len(concepts_per))):
            right |= concepts_per[j]

        if not left or not right:
            # Empty concept set = likely topic boundary (not "similar")
            similarities.append(0.0)
            boundaries.append(i + window)
            continue

        jaccard = len(left & right) / len(left | right)
        similarities.append(jaccard)

        if jaccard < similarity_threshold:
            boundaries.append(i + window)

    # 3. Split at boundaries
    groups = _split_at_boundaries(transcript, boundaries)

    # 4. Merge micro-segments
    groups = _merge_small(groups, min_sentences)

    # 5. Build TopicSegments with TF-IDF labels
    all_concepts = Counter()
    for cs in concepts_per:
        all_concepts.update(cs)

    topics = []
    for i, group in enumerate(groups):
        group_concepts = Counter()
        for seg in group:
            group_concepts.update(_extract_concepts(seg.text))

        keywords = _tfidf_keywords(group_concepts, all_concepts, top_k=5)
        label = " ".join(keywords[:3]) if keywords else f"topic_{i}"

        coherence = _internal_coherence(group, concepts_per, transcript)

        # Boundary confidence from similarity values
        bc = _boundary_confidence(i, boundaries, similarities, window)

        topics.append(TopicSegment(
            topic_id=i,
            time_range=TimeRange(start=group[0].start, end=group[-1].end),
            topic_label=label,
            keywords=keywords,
            transcript_segment_ids=[s.id for s in group],
            coherence_score=round(coherence, 3),
            boundary_confidence=round(bc, 3),
        ))

    return topics


def _single_topic(
    transcript: list[TranscriptSegment], topic_id: int,
) -> TopicSegment:
    """Create a single topic from all segments."""
    concepts = Counter()
    for seg in transcript:
        concepts.update(_extract_concepts(seg.text))
    keywords = [w for w, _ in concepts.most_common(5)]
    return TopicSegment(
        topic_id=topic_id,
        time_range=TimeRange(transcript[0].start, transcript[-1].end),
        topic_label=" ".join(keywords[:3]) if keywords else "topic_0",
        keywords=keywords,
        transcript_segment_ids=[s.id for s in transcript],
        coherence_score=0.8,
        boundary_confidence=1.0,
    )


def _split_at_boundaries(
    transcript: list[TranscriptSegment],
    boundaries: list[int],
) -> list[list[TranscriptSegment]]:
    """Split transcript at boundary indices."""
    if not boundaries:
        return [list(transcript)]

    groups: list[list[TranscriptSegment]] = []
    prev = 0
    for b in sorted(set(boundaries)):
        if b > prev:
            groups.append(list(transcript[prev:b]))
        prev = b
    if prev < len(transcript):
        groups.append(list(transcript[prev:]))
    return [g for g in groups if g]


def _merge_small(
    groups: list[list[TranscriptSegment]],
    min_size: int,
) -> list[list[TranscriptSegment]]:
    """Merge groups smaller than min_size into neighbors."""
    if len(groups) <= 1:
        return groups

    merged: list[list[TranscriptSegment]] = [groups[0]]
    for g in groups[1:]:
        if len(merged[-1]) < min_size:
            merged[-1].extend(g)
        else:
            merged.append(g)

    # Final pass: merge trailing small group
    if len(merged) > 1 and len(merged[-1]) < min_size:
        merged[-2].extend(merged[-1])
        merged.pop()

    return merged


def _tfidf_keywords(
    group_freq: Counter, corpus_freq: Counter, top_k: int,
) -> list[str]:
    """Simple TF-IDF keyword extraction."""
    total_corpus = sum(corpus_freq.values()) or 1
    total_group = sum(group_freq.values()) or 1

    scores: dict[str, float] = {}
    for word, count in group_freq.items():
        tf = count / total_group
        # IDF approximation: inverse document frequency
        idf = total_corpus / max(1, corpus_freq.get(word, 1))
        scores[word] = tf * idf

    ranked = sorted(scores, key=scores.get, reverse=True)
    return ranked[:top_k]


def _internal_coherence(
    group: list[TranscriptSegment],
    all_concepts: list[set[str]],
    transcript: list[TranscriptSegment],
) -> float:
    """Measure how coherent a group is (vocabulary overlap between sentences)."""
    if len(group) < 2:
        return 0.8

    group_ids = {s.id for s in group}
    group_concepts = [
        all_concepts[i] for i, seg in enumerate(transcript)
        if seg.id in group_ids and i < len(all_concepts)
    ]

    if len(group_concepts) < 2:
        return 0.5

    overlaps = []
    for i in range(len(group_concepts) - 1):
        a, b = group_concepts[i], group_concepts[i + 1]
        if a and b:
            overlaps.append(len(a & b) / len(a | b))

    return sum(overlaps) / len(overlaps) if overlaps else 0.5


def _boundary_confidence(
    topic_idx: int,
    boundaries: list[int],
    similarities: list[float],
    window: int,
) -> float:
    """Estimate confidence of boundary detection."""
    if topic_idx == 0:
        return 1.0  # First topic starts at beginning
    if not boundaries or not similarities:
        return 0.5

    # Find the boundary that starts this topic
    if topic_idx - 1 < len(boundaries):
        b_pos = boundaries[topic_idx - 1]
        sim_idx = b_pos - window
        if 0 <= sim_idx < len(similarities):
            sim = similarities[sim_idx]
            return min(1.0, max(0.0, 1.0 - sim))  # Lower similarity = higher confidence

    return 0.5
