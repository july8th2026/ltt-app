"""
In-memory login rate limiter (P3).

Deliberately in-memory, not Redis-backed — matches ADR-005/ADR-011 (one
orchestrator process, no Celery/Redis in the first web release). A
restart clears all counters, which is an acceptable trade-off for a
single-operator local/VPS dashboard, not a public multi-tenant service.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, *, max_attempts: int = 5, window_seconds: float = 60.0):
        self._max_attempts = max_attempts
        self._window = window_seconds
        self._attempts: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """Record an attempt for *key* and return True if it's within the
        allowed rate, False if the caller should be rejected."""
        now = time.monotonic()
        with self._lock:
            bucket = self._attempts[key]
            while bucket and now - bucket[0] > self._window:
                bucket.popleft()
            if len(bucket) >= self._max_attempts:
                return False
            bucket.append(now)
            return True

    def reset(self, key: str) -> None:
        """Call after a successful login so a legitimate user isn't
        penalized by their own prior failed attempts."""
        with self._lock:
            self._attempts.pop(key, None)
