"""
Rolling-window error-rate circuit breaker.

Purpose:
  Detect a sustained spike of failed publishes — usually a sign that Facebook
  is actively throttling the account — and AUTO-PAUSE further work until the
  storm passes. Pulling the brake fast is the difference between a "soft
  warning" period (where FB watches but doesn't ban) and a "hard limit"
  (where the account loses posting privileges for days).

Triggers (configurable, OR-combined):
  • >= MIN_SAMPLES events in window
  • AND failure_rate >= FAIL_RATE_THRESHOLD
  • OR last K events were all failures

Action:
  • State transitions: closed → open → half-open → closed
  • In OPEN state, allow_attempt() returns False until cooldown expires.
  • HALF_OPEN: lets exactly 1 attempt through to probe recovery.

Thread-safe. Per-key (use platform or account_id as the key).
"""
from __future__ import annotations

import collections
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BreakerState(Enum):
    CLOSED    = "closed"      # normal — attempts allowed
    OPEN      = "open"        # paused — attempts blocked
    HALF_OPEN = "half_open"   # probing — 1 attempt allowed


@dataclass
class _BreakerStats:
    """Per-key rolling event log."""
    events:        collections.deque = field(default_factory=lambda: collections.deque(maxlen=50))
    state:         BreakerState  = BreakerState.CLOSED
    opened_at:     float         = 0.0
    cooldown_s:    float         = 0.0
    consecutive_failures: int    = 0


class CircuitBreaker:
    """
    Per-key error-rate breaker. The key is typically platform name or
    account_id; the breaker is independent for each so a bad FB account
    doesn't stop a healthy TikTok upload pipeline.

    Usage:
        cb = CircuitBreaker()

        if not cb.allow("acc_X"):
            log("Breaker open — skipping")
            return

        try:
            do_upload(...)
            cb.record_success("acc_X")
        except Exception:
            cb.record_failure("acc_X")
            raise
    """

    def __init__(
        self,
        window_size:           int   = 20,
        fail_rate_threshold:   float = 0.40,    # 40% fails → trip
        min_samples_to_trip:   int   = 5,
        consecutive_fails_trip: int  = 3,
        initial_cooldown_s:    float = 600,     # 10 min first trip
        max_cooldown_s:        float = 14400,   # 4 h cap
        cooldown_multiplier:   float = 2.0,     # exponential per re-trip
    ):
        self.window_size            = max(1, window_size)
        self.fail_rate_threshold    = max(0.0, min(1.0, fail_rate_threshold))
        self.min_samples_to_trip    = max(1, min_samples_to_trip)
        self.consecutive_fails_trip = max(1, consecutive_fails_trip)
        # Floor at 0.01 so tests can simulate fast cooldowns; production values
        # come from settings (default 600 s) so the floor is never hit in real use.
        self.initial_cooldown_s     = max(0.01, initial_cooldown_s)
        self.max_cooldown_s         = max(self.initial_cooldown_s, max_cooldown_s)
        self.cooldown_multiplier    = max(1.0, cooldown_multiplier)

        self._lock: threading.Lock = threading.Lock()
        self._by_key: dict[str, _BreakerStats] = {}

    # ── Public: pre-attempt check ─────────────────────────────────────────────

    def allow(self, key: str) -> bool:
        """Return True if an attempt for *key* should proceed.
        Side effect: may transition OPEN → HALF_OPEN when cooldown expires.
        """
        now = time.time()
        with self._lock:
            s = self._stats(key)
            if s.state is BreakerState.CLOSED:
                return True
            if s.state is BreakerState.OPEN:
                # Cooldown elapsed? → probe with HALF_OPEN
                if now - s.opened_at >= s.cooldown_s:
                    s.state = BreakerState.HALF_OPEN
                    return True
                return False
            # HALF_OPEN: only one probe allowed; flip back to OPEN until result
            s.state = BreakerState.OPEN
            return True

    def seconds_until_allowed(self, key: str) -> float:
        """How many seconds remain in the current OPEN cooldown."""
        with self._lock:
            s = self._stats(key)
            if s.state is BreakerState.CLOSED:
                return 0.0
            remain = (s.opened_at + s.cooldown_s) - time.time()
            return max(0.0, remain)

    def state(self, key: str) -> str:
        with self._lock:
            return self._stats(key).state.value

    # ── Public: record outcomes ───────────────────────────────────────────────

    def record_success(self, key: str) -> None:
        with self._lock:
            s = self._stats(key)
            s.events.append(("ok", time.time()))
            s.consecutive_failures = 0
            # Success in HALF_OPEN → recovery confirmed → CLOSED + reset cooldown
            if s.state is BreakerState.HALF_OPEN:
                s.state = BreakerState.CLOSED
                s.cooldown_s = 0.0

    def record_failure(self, key: str) -> None:
        with self._lock:
            s = self._stats(key)
            s.events.append(("fail", time.time()))
            s.consecutive_failures += 1
            # Failure in HALF_OPEN → still broken → back to OPEN with longer cooldown
            if s.state is BreakerState.HALF_OPEN:
                s.cooldown_s = min(
                    s.cooldown_s * self.cooldown_multiplier,
                    self.max_cooldown_s,
                )
                s.opened_at  = time.time()
                s.state      = BreakerState.OPEN
                return
            # Closed → check trip conditions
            if s.state is BreakerState.CLOSED and self._should_trip(s):
                s.cooldown_s = self.initial_cooldown_s if s.cooldown_s == 0 else min(
                    s.cooldown_s * self.cooldown_multiplier,
                    self.max_cooldown_s,
                )
                s.opened_at = time.time()
                s.state     = BreakerState.OPEN

    # ── Public: stats ─────────────────────────────────────────────────────────

    def stats_for(self, key: str) -> dict:
        with self._lock:
            s = self._stats(key)
            n = len(s.events)
            fails = sum(1 for e, _ in s.events if e == "fail")
            return {
                "state":             s.state.value,
                "events":            n,
                "fail_rate":         (fails / n) if n else 0.0,
                "consecutive_fails": s.consecutive_failures,
                "cooldown_s":        s.cooldown_s,
                "opened_at":         s.opened_at,
            }

    def reset(self, key: Optional[str] = None) -> None:
        with self._lock:
            if key is None:
                self._by_key.clear()
            else:
                self._by_key.pop(key, None)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _stats(self, key: str) -> _BreakerStats:
        s = self._by_key.get(key)
        if s is None:
            s = _BreakerStats(events=collections.deque(maxlen=self.window_size))
            self._by_key[key] = s
        return s

    def _should_trip(self, s: _BreakerStats) -> bool:
        """Internal trip-test (caller already holds lock)."""
        if s.consecutive_failures >= self.consecutive_fails_trip:
            return True
        n = len(s.events)
        if n < self.min_samples_to_trip:
            return False
        fails = sum(1 for e, _ in s.events if e == "fail")
        return (fails / n) >= self.fail_rate_threshold


# ─── Module-level singleton for the publish pipeline ─────────────────────────

_default: Optional[CircuitBreaker] = None
_default_lock = threading.Lock()


def get_default_breaker() -> CircuitBreaker:
    """Process-wide breaker shared by publishers + sheet runner."""
    global _default
    with _default_lock:
        if _default is None:
            _default = CircuitBreaker()
        return _default


class CircuitOpenError(RuntimeError):
    """Raised when the breaker is OPEN and an attempt is requested.
    Caller should defer the job rather than retry immediately."""
