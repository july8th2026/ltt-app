"""Strategy registry — maps genre names to EditorialStrategy instances."""

from __future__ import annotations

from cutclipshort.editorial.strategies.generic import GenericStrategy
from cutclipshort.editorial.strategies.talking_head import TalkingHeadStrategy

# Registry: genre name → strategy instance
_STRATEGIES: dict[str, object] = {}


def get_strategy(genre: str) -> object:
    """Get or create a strategy for the given genre.

    TalkingHead has a dedicated class. All other genres use GenericStrategy
    with genre-specific profiles.
    """
    if genre not in _STRATEGIES:
        if genre == "talking_head":
            _STRATEGIES[genre] = TalkingHeadStrategy()
        else:
            _STRATEGIES[genre] = GenericStrategy(genre)

    return _STRATEGIES[genre]


def list_strategies() -> list[str]:
    """List all available genre strategy names."""
    from cutclipshort.editorial.genre_profiles import list_profiles
    return list_profiles()
