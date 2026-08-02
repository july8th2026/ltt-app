"""Concept clusterer — groups transcript segments by shared meaning.

Uses Union-Find connected components on a Jaccard similarity graph
to identify semantically related segments (even non-contiguous ones).
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict

from cutclipshort.editorial.semantic_scorer import _extract_concepts
from cutclipshort.types import ConceptCluster, TimeRange, TranscriptSegment

logger = logging.getLogger(__name__)

_SIMILARITY_THRESHOLD = 0.25
_MIN_CLUSTER_SIZE = 2


def cluster_segments(
    transcript: list[TranscriptSegment],
    similarity_threshold: float = _SIMILARITY_THRESHOLD,
    min_cluster_size: int = _MIN_CLUSTER_SIZE,
) -> list[ConceptCluster]:
    """Cluster transcript segments by shared semantic concepts."""
    if len(transcript) < min_cluster_size:
        return []

    # 1. Extract concepts per segment
    concepts: dict[int, set[str]] = {
        seg.id: _extract_concepts(seg.text) for seg in transcript
    }

    # 2. Union-Find setup
    parent: dict[int, int] = {seg.id: seg.id for seg in transcript}
    rank: dict[int, int] = {seg.id: 0 for seg in transcript}

    # 3. Build similarity edges and union
    seg_list = list(transcript)
    for i in range(len(seg_list)):
        for j in range(i + 1, len(seg_list)):
            id_a, id_b = seg_list[i].id, seg_list[j].id
            ca, cb = concepts[id_a], concepts[id_b]
            if not ca or not cb:
                continue
            jaccard = len(ca & cb) / len(ca | cb)
            if jaccard >= similarity_threshold:
                _union(parent, rank, id_a, id_b)

    # 4. Group by root
    groups: dict[int, list[int]] = defaultdict(list)
    seg_by_id = {seg.id: seg for seg in transcript}
    for seg in transcript:
        root = _find(parent, seg.id)
        groups[root].append(seg.id)

    # 5. Build clusters
    clusters: list[ConceptCluster] = []
    cluster_id = 0

    for root, seg_ids in groups.items():
        if len(seg_ids) < min_cluster_size:
            continue

        # Shared concepts (intersection of all)
        all_concepts = [concepts[sid] for sid in seg_ids if concepts[sid]]
        if not all_concepts:
            continue

        shared = set(all_concepts[0])
        for cs in all_concepts[1:]:
            shared &= cs

        # All concepts (union)
        all_union = set()
        for cs in all_concepts:
            all_union |= cs

        cohesion = len(shared) / max(1, len(all_union))

        # Label: most frequent concept across cluster
        freq = Counter()
        for sid in seg_ids:
            freq.update(concepts[sid])
        label = freq.most_common(1)[0][0] if freq else f"cluster_{cluster_id}"

        # Time ranges
        time_ranges = [
            TimeRange(seg_by_id[sid].start, seg_by_id[sid].end)
            for sid in seg_ids if sid in seg_by_id
        ]

        # Top keywords
        keywords = frozenset(w for w, _ in freq.most_common(10))

        clusters.append(ConceptCluster(
            cluster_id=cluster_id,
            concept_label=label,
            keywords=keywords,
            segment_ids=sorted(seg_ids),
            time_ranges=time_ranges,
            cohesion_score=round(cohesion, 3),
        ))
        cluster_id += 1

    return clusters


def _find(parent: dict[int, int], x: int) -> int:
    """Union-Find: find with path compression."""
    while parent[x] != x:
        parent[x] = parent[parent[x]]  # Path compression
        x = parent[x]
    return x


def _union(
    parent: dict[int, int],
    rank: dict[int, int],
    a: int,
    b: int,
) -> None:
    """Union-Find: union by rank."""
    ra, rb = _find(parent, a), _find(parent, b)
    if ra == rb:
        return
    if rank[ra] < rank[rb]:
        parent[ra] = rb
    elif rank[ra] > rank[rb]:
        parent[rb] = ra
    else:
        parent[rb] = ra
        rank[ra] += 1
