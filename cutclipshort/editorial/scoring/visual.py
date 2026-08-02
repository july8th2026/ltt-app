"""Visual scorer — genre-aware person presence, motion, static penalty."""

from __future__ import annotations

from cutclipshort.editorial.genre_profiles import GenreProfile
from cutclipshort.types import SceneInfo, TimeRange, VisualSegment


def score_visual(
    time_range: TimeRange,
    visual_segments: list[VisualSegment],
    scenes: list[SceneInfo],
    profile: GenreProfile,
) -> float:
    """Score visual quality with genre-aware motion preferences."""
    relevant_vs = [
        vs for vs in visual_segments if vs.time_range.overlaps(time_range)
    ]
    if not relevant_vs:
        return 0.4

    scores = []

    # Person presence
    person_frames = sum(1 for vs in relevant_vs if vs.has_person)
    person_ratio = person_frames / len(relevant_vs) if relevant_vs else 0.0
    if profile.require_person:
        scores.append(person_ratio)
    else:
        scores.append(0.5 + person_ratio * 0.5)

    # Motion appropriateness — genre-aware ranges
    avg_motion = sum(vs.motion_avg for vs in relevant_vs) / max(1, len(relevant_vs))
    motion_bonus = profile.high_motion_bonus

    if motion_bonus >= 0.10:
        # Visual-heavy genres (action, nature, animation): higher motion = better
        if avg_motion >= 25.0:
            scores.append(min(1.0, 0.75 + motion_bonus))  # High motion rewarded
        elif avg_motion >= 10.0:
            scores.append(0.9)  # Good motion
        elif avg_motion >= 3.0:
            scores.append(0.7)  # Moderate — OK
        else:
            scores.append(0.4)  # Too static for visual genre
    else:
        # Speech genres: moderate motion preferred
        if 3.0 <= avg_motion <= 25.0:
            scores.append(0.9)
        elif avg_motion < 3.0:
            scores.append(0.5)
        else:
            scores.append(0.6 + motion_bonus)

    # Static frame penalty
    static_count = sum(1 for vs in relevant_vs if vs.is_static)
    if static_count == len(relevant_vs) and len(relevant_vs) > 1:
        scores.append(0.3)
    else:
        scores.append(0.8)

    return sum(scores) / len(scores) if scores else 0.5
