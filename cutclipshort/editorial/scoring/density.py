"""Content density scorer — genre-aware words per second, information density."""

from __future__ import annotations

from cutclipshort.editorial.genre_profiles import GenreProfile
from cutclipshort.types import TimeRange


def score_content_density(
    time_range: TimeRange,
    word_count: int,
    speech_ratio: float,
    profile: GenreProfile,
) -> float:
    """Score information density with genre-specific thresholds.

    Speech genres: reward high WPS (1.5-3.5).
    Visual genres (nature, action, kids_music, animation):
      don't penalize low word count — visual content IS the content.
    Education: reward higher WPS (2.0-4.0) for information density.
    """
    duration = time_range.duration
    if duration <= 0:
        return 0.0

    words_per_sec = word_count / duration if duration > 0 else 0.0

    # Visual-heavy genres: speech is optional, don't penalize low WPS
    if not profile.require_speech:
        # For visual genres, low speech is fine — score neutrally
        if words_per_sec >= 1.0:
            wps_score = 1.0  # Has some narration = bonus
        elif words_per_sec >= 0.3:
            wps_score = 0.8  # Minimal narration = OK
        else:
            wps_score = 0.7  # No narration = acceptable
        # Speech ratio matters less for visual genres
        density = wps_score * 0.8 + speech_ratio * 0.2
        return min(1.0, density)

    # Education: higher WPS threshold (information-dense content)
    if profile.name == "education":
        if 2.0 <= words_per_sec <= 4.0:
            wps_score = 1.0
        elif words_per_sec < 2.0:
            wps_score = max(0.3, words_per_sec / 2.0)
        else:
            wps_score = max(0.5, 1.0 - (words_per_sec - 4.0) * 0.2)
        density = wps_score * 0.6 + speech_ratio * 0.4
        return min(1.0, density)

    # Default speech genres: standard WPS range
    if 1.5 <= words_per_sec <= 3.5:
        wps_score = 1.0
    elif words_per_sec < 1.5:
        wps_score = max(0.2, words_per_sec / 1.5)
    else:
        wps_score = max(0.5, 1.0 - (words_per_sec - 3.5) * 0.2)

    density = wps_score * 0.6 + speech_ratio * 0.4
    return min(1.0, density)
