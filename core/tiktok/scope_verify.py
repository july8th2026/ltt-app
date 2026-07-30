"""
TikTok scope runtime verification (Sprint TT-5 / F2).

Compares the SCOPES the user actually granted at OAuth time against the
scopes the bot needs for the current operation. Catches the "you connected
before the app got Comment API approval" footgun where the bot tries to
post comments and gets `scope_not_authorized` for every upload.

Reads granted scopes from TikTokAccount.scopes (list[str]) — already stored
during OAuth callback in token_store.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


# Minimum scopes the bot uses per operation.
# user.info.basic is granted by default by TikTok OAuth so we don't include
# it here — checking it explicitly would false-positive on legacy accounts
# whose scopes field doesn't list the default scope.
_SCOPE_REQUIREMENTS: dict[str, set] = {
    "draft_upload":   {"video.upload"},
    "direct_upload":  {"video.upload", "video.publish"},
    "comment_post":   {"comment.create"},
    "research_read":  {"research.adlib.basic"},   # optional, for analytics
}


@dataclass(frozen=True)
class ScopeCheckResult:
    operation:        str
    granted_scopes:   list
    missing_scopes:   list
    ok:               bool
    message:          str


def check_scopes(
    operation: str,
    granted_scopes: Iterable,
) -> ScopeCheckResult:
    """Verify *granted_scopes* covers what *operation* needs.

    operation: one of "draft_upload", "direct_upload", "comment_post",
               "research_read", or a custom required-set passed as
               iterable in granted_scopes (advanced).
    """
    required = _SCOPE_REQUIREMENTS.get(operation, set())
    granted_set = {str(s).strip().lower() for s in (granted_scopes or []) if s}
    missing = sorted(required - granted_set)
    if missing:
        return ScopeCheckResult(
            operation=operation,
            granted_scopes=sorted(granted_set),
            missing_scopes=missing,
            ok=False,
            message=(
                f"Acc thiếu scope cho '{operation}': {', '.join(missing)}. "
                f"User cần reconnect TT account với scope đầy đủ."
            ),
        )
    return ScopeCheckResult(
        operation=operation,
        granted_scopes=sorted(granted_set),
        missing_scopes=[],
        ok=True,
        message=f"Scopes OK cho '{operation}'",
    )


def required_scopes(operation: str) -> set:
    """Public accessor for required-scope set of an operation."""
    return set(_SCOPE_REQUIREMENTS.get(operation, set()))
