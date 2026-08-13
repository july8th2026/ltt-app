"""Pagination primitives shared by every ``/api/v1`` list endpoint.

COMMON_RULES §6 requires a hard maximum on list endpoints. Putting that ceiling
in one place means no future route can forget it, and a client that asks for
``limit=100000`` gets a clamped page instead of a table scan that ties up a
worker connection.

The shape is offset-based on purpose. Cursor pagination is better for large,
mutating tables, but it needs a stable sort key exposed to callers; the tables
this API will list first (jobs, uploads, artifacts for **one** owner) are small
enough that offset is honest and simple. When a listing outgrows it, add a
cursor variant here rather than in a route.
"""
from __future__ import annotations

from dataclasses import dataclass

from platform_core.public_api.errors import invalid_request

DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100
MAX_PAGE_OFFSET = 100_000


@dataclass(frozen=True)
class PageRequest:
    """A validated ``limit``/``offset`` pair."""

    limit: int = DEFAULT_PAGE_LIMIT
    offset: int = 0

    @classmethod
    def parse(cls, limit=None, offset=None) -> "PageRequest":
        """Build from raw query values. Raises :class:`ApiError` on nonsense.

        Clamping silently would hide a caller's mistake; rejecting a negative
        limit tells them why their loop never advances. An oversized limit is
        clamped rather than rejected because that one is usually "give me
        everything", and a clamped page still answers it correctly.
        """
        parsed_limit = _positive_int("limit", limit, DEFAULT_PAGE_LIMIT)
        parsed_offset = _positive_int("offset", offset, 0)
        if parsed_limit == 0:
            raise invalid_request("limit must be at least 1.")
        if parsed_offset > MAX_PAGE_OFFSET:
            raise invalid_request(
                f"offset must not exceed {MAX_PAGE_OFFSET}.")
        return cls(limit=min(parsed_limit, MAX_PAGE_LIMIT), offset=parsed_offset)

    @property
    def fetch_limit(self) -> int:
        """Rows to ask the database for: one extra reveals ``has_more``."""
        return self.limit + 1


@dataclass(frozen=True)
class Page:
    """A page of already-serialized items plus its navigation block."""

    items: tuple
    limit: int
    offset: int
    has_more: bool

    @classmethod
    def of(cls, rows, request: PageRequest) -> "Page":
        """Trim ``rows`` fetched with :attr:`PageRequest.fetch_limit`."""
        materialized = list(rows)
        has_more = len(materialized) > request.limit
        return cls(items=tuple(materialized[:request.limit]), limit=request.limit,
                   offset=request.offset, has_more=has_more)

    def to_dict(self) -> dict:
        page = {"limit": self.limit, "offset": self.offset,
                "has_more": self.has_more}
        if self.has_more:
            page["next_offset"] = self.offset + self.limit
        return {"items": list(self.items), "page": page}


def _positive_int(name: str, value, default: int) -> int:
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise invalid_request(f"{name} must be an integer.") from exc
    if parsed < 0:
        raise invalid_request(f"{name} must not be negative.")
    return parsed
