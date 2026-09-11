"""Trusted scheduler classification propagated across request/worker calls.

The default context is deliberately EXTERNAL/unknown. Only platform-owned
boundaries may open a trusted scope; public request fields and headers are
never inputs to this module.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator


_ORIGIN = ContextVar("ltt_job_origin", default="unknown")
_PRIORITY = ContextVar("ltt_job_priority", default="external")


def current() -> tuple[str, str]:
    return _ORIGIN.get(), _PRIORITY.get()


@contextmanager
def trusted_scope(origin: str, priority_class: str) -> Iterator[None]:
    """Set classification for one trusted call tree and restore it safely."""
    origin_token = _ORIGIN.set(str(origin))
    priority_token = _PRIORITY.set(str(priority_class))
    try:
        yield
    finally:
        _PRIORITY.reset(priority_token)
        _ORIGIN.reset(origin_token)
