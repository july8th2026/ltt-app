"""Scope vocabulary for developer API keys.

Naming is ``<resource>:<action>``, and read is never implied by write: a token
that may submit a job does not automatically get to list every job of the
account, and one that may read jobs cannot cancel them. Whoever adds a resource
adds its scopes here, and the route enforcing them refers to these constants
rather than to string literals.

**Tools are not scopes.** A scope says *what kind of action* a key may take; the
per-key ``allowed_tools`` list says *which tools* it may aim that action at.
Folding tool names into scopes (``tool:image.generate``) looks tempting but ends
with a scope string per tool, forces re-issuing keys whenever the catalog
changes, and gives two half-answers to "may this key call this tool". One model,
one answer — see ``principal.ensure_tool_allowed``.
"""
from __future__ import annotations

SCOPE_TOOLS_READ = "tools:read"
SCOPE_JOBS_CREATE = "jobs:create"
SCOPE_JOBS_READ = "jobs:read"
SCOPE_JOBS_CANCEL = "jobs:cancel"
SCOPE_UPLOADS_WRITE = "uploads:write"
SCOPE_ARTIFACTS_READ = "artifacts:read"
SCOPE_CREDITS_READ = "credits:read"
SCOPE_USAGE_READ = "usage:read"
SCOPE_WEBHOOKS_MANAGE = "webhooks:manage"

KNOWN_SCOPES = frozenset({
    SCOPE_TOOLS_READ,
    SCOPE_JOBS_CREATE,
    SCOPE_JOBS_READ,
    SCOPE_JOBS_CANCEL,
    SCOPE_UPLOADS_WRITE,
    SCOPE_ARTIFACTS_READ,
    SCOPE_CREDITS_READ,
    SCOPE_USAGE_READ,
    SCOPE_WEBHOOKS_MANAGE,
})

# What a key gets when the caller does not ask for anything specific: enough to
# discover the catalog and read its own work, never enough to spend credit.
DEFAULT_SCOPES = (SCOPE_TOOLS_READ, SCOPE_JOBS_READ)

# Scopes that can move money or consume capacity. Listed explicitly so a review
# of "what can this key cost me" is a lookup, not a reading of every route.
SPENDING_SCOPES = frozenset({SCOPE_JOBS_CREATE})


class ScopeError(ValueError):
    """An unknown scope was requested."""


def normalize_scopes(scopes) -> list:
    """Validate, de-duplicate and order scopes. Empty input → defaults."""
    requested = [str(scope).strip() for scope in (scopes or ()) if str(scope).strip()]
    if not requested:
        return list(DEFAULT_SCOPES)
    unknown = sorted({scope for scope in requested if scope not in KNOWN_SCOPES})
    if unknown:
        raise ScopeError(f"Unknown scope(s): {', '.join(unknown)}")
    return sorted(set(requested))
