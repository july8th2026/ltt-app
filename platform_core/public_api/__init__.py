"""Public API domain layer (Q92).

This package holds the framework-free half of the Public API: configuration and
kill switches, the machine-readable error contract and pagination primitives.
The HTTP surface lives in ``server/api``; nothing here imports FastAPI, Starlette
or ``server.*`` so the rules can be unit-tested without booting an app.

Two boundaries this package must keep:

* it never learns the name of an app — the platform discovers apps through
  ``platform_core.registry`` (``AGENTS.md`` 8.4);
* it never creates a second queue, ledger, provider pool or storage lifecycle —
  the Public API is an adapter in front of what already exists.
"""
from __future__ import annotations

from platform_core.public_api.config import (PublicApiConfig, load_public_api_config)
from platform_core.public_api.errors import (ApiError, ApiProblem, PROBLEM_CONTENT_TYPE,
                                             problem_for_status, scrub_detail)
from platform_core.public_api.pagination import (DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT,
                                                 Page, PageRequest)

__all__ = [
    "ApiError", "ApiProblem", "PROBLEM_CONTENT_TYPE", "problem_for_status",
    "scrub_detail", "PublicApiConfig", "load_public_api_config",
    "Page", "PageRequest", "DEFAULT_PAGE_LIMIT", "MAX_PAGE_LIMIT",
]
