"""
Thread-safe per-page upload rate limiter with metrics + production-safety features.

Controls multiple dimensions:
  max_concurrent              — simultaneous uploads allowed per page (default 1)
  min_interval_s              — min seconds between finished uploads on SAME page
  min_inter_page_interval_s   — min seconds between ANY two finished uploads (global)
  jitter_s                    — random ±seconds added to each wait (anti-fingerprint)
  active_hours_start/end      — clock window e.g. 8-23 (block outside)
  max_posts_per_page_per_day  — daily cap per page
  timezone_name               — clock used for day boundary + active hours

All new dimensions are opt-in: 0/empty defaults preserve legacy behaviour.

Metrics collected per page:
  uploads_done    — completed upload count
  total_wait_s    — cumulative seconds spent waiting for rate-limit
  total_upload_s  — cumulative seconds spent in upload (acquire→release)

Usage:
    limiter = RateLimiter(max_concurrent=1, min_interval_s=30)
    limiter.acquire("My Page", stop_event)   # blocks until slot is ready
    try:
        do_upload()
    finally:
        limiter.release("My Page")
"""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# ─── Global metrics registry ─────────────────────────────────────────────────
# Populated on every release() so any consumer (MonitorTab) can read stats
# without needing a reference to a specific RateLimiter instance.

_GLOBAL_LOCK: threading.Lock = threading.Lock()
_GLOBAL_METRICS: dict[str, dict] = {}   # page_name → aggregated PageMetrics.to_dict()


def get_global_page_metrics() -> dict[str, dict]:
    """Return a deep snapshot of cumulative upload metrics for all pages."""
    with _GLOBAL_LOCK:
        return {name: dict(m) for name, m in _GLOBAL_METRICS.items()}


def reset_global_metrics():
    """Clear the global metrics registry (useful for testing)."""
    with _GLOBAL_LOCK:
        _GLOBAL_METRICS.clear()


class QuotaExceededError(RuntimeError):
    """Daily post quota for a page has been reached. Caller should defer the job."""


@dataclass
class PageMetrics:
    uploads_done:   int   = 0
    total_wait_s:   float = 0.0
    total_upload_s: float = 0.0
    _acquire_at:    float = field(default=0.0, repr=False)
    _upload_start:  float = field(default=0.0, repr=False)

    @property
    def avg_wait_s(self) -> float:
        return self.total_wait_s / self.uploads_done if self.uploads_done else 0.0

    def to_dict(self) -> dict:
        return {
            "uploads_done":   self.uploads_done,
            "total_wait_s":   round(self.total_wait_s, 1),
            "avg_wait_s":     round(self.avg_wait_s, 1),
            "total_upload_s": round(self.total_upload_s, 1),
        }


class RateLimiter:
    def __init__(
        self,
        max_concurrent: int   = 1,
        min_interval_s: float = 30.0,
        # ─── Production-safety dimensions (opt-in) ──────────────────────────
        min_inter_page_interval_s: float = 0.0,
        jitter_s:                  float = 0.0,
        active_hours_start:        int   = 0,
        active_hours_end:          int   = 0,
        max_posts_per_page_per_day: int  = 0,
        max_posts_per_account_per_day: int = 0,
        timezone_name:             str   = "Asia/Ho_Chi_Minh",
    ):
        self.max_concurrent                = max(1, max_concurrent)
        self.min_interval_s                = max(0.0, min_interval_s)
        self.min_inter_page_interval_s     = max(0.0, min_inter_page_interval_s)
        self.jitter_s                      = max(0.0, jitter_s)
        self.active_hours_start            = active_hours_start if 0 <= active_hours_start <= 23 else 0
        self.active_hours_end              = active_hours_end   if 0 <= active_hours_end   <= 23 else 0
        self.max_posts_per_page_per_day    = max(0, max_posts_per_page_per_day)
        self.max_posts_per_account_per_day = max(0, max_posts_per_account_per_day)
        self.timezone_name                 = timezone_name

        self._lock       = threading.Lock()
        self._semaphores: dict[str, threading.Semaphore] = {}
        self._last_done:  dict[str, float] = {}          # per-page
        self._last_done_any: float = 0.0                  # ANY page (global)
        self._daily_counts:         dict[tuple[str, str], int] = {}   # (page,    day_key) → count
        self._account_daily_counts: dict[tuple[str, str], int] = {}   # (account, day_key) → count
        self._metrics:    dict[str, PageMetrics] = {}

    # ── Public ────────────────────────────────────────────────────────────────

    def acquire(
        self,
        page_name: str,
        stop_event: Optional[threading.Event] = None,
        *,
        account_id: str = "",
    ):
        """
        Block until conditions are met for *page_name*:
          1. Current time is inside the active-hours window (if configured).
          2. Daily quota for this page is not exhausted.
          3. Daily quota for *account_id* is not exhausted (when provided).
          4. A concurrent-upload slot is free.
          5. At least min_interval_s has passed since the last finished upload
             on this page; AND min_inter_page_interval_s since any page.
          6. Apply jitter delay if configured.

        Raises:
          InterruptedError — if stop_event fires while waiting.
          QuotaExceededError — if daily cap for this page OR account is hit.

        account_id (keyword-only): the owning Facebook user account id. When
        provided AND max_posts_per_account_per_day > 0, enforces a daily cap
        across all pages belonging to that account. Empty string disables the
        check (backwards compat — old call sites that don't pass account_id).
        """
        acquire_at = time.time()

        # Step 1: active-hours window. Blocks (sleeps) outside window.
        self._wait_for_active_window(stop_event)

        # Step 2-3: daily quotas. Raise BEFORE grabbing the slot.
        self._check_daily_quota(page_name)
        self._check_account_quota(account_id)

        # Step 3: concurrency slot
        sem = self._semaphore_for(page_name)
        while not sem.acquire(timeout=0.5):
            if stop_event and stop_event.is_set():
                raise InterruptedError("Dừng bởi người dùng")

        # Step 4 + 5: interval waits + jitter
        try:
            self._wait_for_intervals(page_name, stop_event)
        except BaseException:
            sem.release()
            raise

        # Record wait time and upload start
        with self._lock:
            m = self._metrics.setdefault(page_name, PageMetrics())
            m.total_wait_s += time.time() - acquire_at
            m._acquire_at   = acquire_at
            m._upload_start = time.time()

    def release(self, page_name: str, *, account_id: str = ""):
        """Record completion timestamp, update metrics, free the concurrency slot.

        account_id (keyword-only): when provided, also increments the account
        daily count used to enforce max_posts_per_account_per_day.
        """
        now = time.time()
        day_key = self._current_day_key()
        with self._lock:
            self._last_done[page_name] = now
            self._last_done_any        = now
            self._daily_counts[(page_name, day_key)] = (
                self._daily_counts.get((page_name, day_key), 0) + 1
            )
            if account_id:
                self._account_daily_counts[(account_id, day_key)] = (
                    self._account_daily_counts.get((account_id, day_key), 0) + 1
                )
            self._purge_old_day_keys(day_key)
            m = self._metrics.setdefault(page_name, PageMetrics())
            m.uploads_done   += 1
            m.total_upload_s += now - m._upload_start
            snapshot = m.to_dict()
        # Propagate to module-level global registry so MonitorTab can read
        # the latest stats without holding a reference to this instance.
        with _GLOBAL_LOCK:
            _GLOBAL_METRICS[page_name] = snapshot
        self._semaphore_for(page_name).release()

    def wait_until_ready(self, page_name: str) -> float:
        """
        Returns estimated seconds until the page is ready.
        0 means ready now. Does NOT acquire a slot.
        Accounts for per-page interval AND inter-page interval.
        """
        with self._lock:
            now = time.time()
            per_page_remain = max(
                0.0, self.min_interval_s - (now - self._last_done.get(page_name, 0.0))
            )
            inter_page_remain = max(
                0.0, self.min_inter_page_interval_s - (now - self._last_done_any)
            )
            return max(per_page_remain, inter_page_remain)

    # ── Metrics ───────────────────────────────────────────────────────────────

    def page_metrics(self, page_name: str) -> dict:
        """Metrics for a single page."""
        with self._lock:
            m = self._metrics.get(page_name)
            return m.to_dict() if m else PageMetrics().to_dict()

    def all_metrics(self) -> dict[str, dict]:
        """Metrics for all pages that have been through this limiter."""
        with self._lock:
            return {name: m.to_dict() for name, m in self._metrics.items()}

    def reset_metrics(self, page_name: str = ""):
        """Reset metrics for one page (or all if page_name is empty)."""
        with self._lock:
            if page_name:
                self._metrics.pop(page_name, None)
            else:
                self._metrics.clear()

    def daily_count(self, page_name: str) -> int:
        """How many uploads completed for this page today (in configured TZ)."""
        with self._lock:
            return self._daily_counts.get((page_name, self._current_day_key()), 0)

    def account_daily_count(self, account_id: str) -> int:
        """How many uploads completed across all pages of *account_id* today."""
        if not account_id:
            return 0
        with self._lock:
            return self._account_daily_counts.get(
                (account_id, self._current_day_key()), 0
            )

    # ── Private: production-safety helpers ───────────────────────────────────

    def _wait_for_active_window(self, stop_event: Optional[threading.Event]):
        """Block (interruptible sleep) until inside the active-hours window."""
        if self.active_hours_start == self.active_hours_end:
            return  # disabled
        while True:
            if stop_event and stop_event.is_set():
                raise InterruptedError("Dừng bởi người dùng")
            now = datetime.now(self._tz())
            hour = now.hour
            start = self.active_hours_start
            end   = self.active_hours_end
            in_window = (
                start <= hour < end if start < end
                # window crosses midnight (e.g. 22-6)
                else (hour >= start or hour < end)
            )
            if in_window:
                return
            # Sleep until next minute boundary, then re-check. Cheap polling
            # avoids needing to compute "exactly when window opens" in TZ math.
            time.sleep(min(30.0, 60 - now.second))

    def _check_daily_quota(self, page_name: str):
        """Raise QuotaExceededError if daily cap reached. Read-only check."""
        if self.max_posts_per_page_per_day <= 0:
            return  # disabled
        with self._lock:
            count = self._daily_counts.get(
                (page_name, self._current_day_key()), 0
            )
        if count >= self.max_posts_per_page_per_day:
            raise QuotaExceededError(
                f"Daily quota reached for page '{page_name}': "
                f"{count}/{self.max_posts_per_page_per_day} posts today"
            )

    def _check_account_quota(self, account_id: str):
        """Raise QuotaExceededError if the owning account's daily cap is hit.
        Protects against velocity-flagging the FB user account itself when
        it admins many pages (e.g. 5 pages × 10 posts/day = 50 posts/day per
        account; FB flags users posting > N times/day across many pages).
        """
        if not account_id or self.max_posts_per_account_per_day <= 0:
            return  # disabled or no account context
        with self._lock:
            count = self._account_daily_counts.get(
                (account_id, self._current_day_key()), 0
            )
        if count >= self.max_posts_per_account_per_day:
            raise QuotaExceededError(
                f"Daily quota reached for account '{account_id}': "
                f"{count}/{self.max_posts_per_account_per_day} posts today"
            )

    def _wait_for_intervals(
        self, page_name: str, stop_event: Optional[threading.Event],
    ):
        """Wait until BOTH the per-page and inter-page intervals are satisfied,
        then apply jitter. Interruptible by stop_event.

        Combined into one method to avoid double-sleeping and to compute the
        max-remaining wait in a single tick.
        """
        jitter = random.uniform(0.0, self.jitter_s) if self.jitter_s > 0 else 0.0
        while True:
            if stop_event and stop_event.is_set():
                raise InterruptedError("Dừng bởi người dùng")
            now = time.time()
            with self._lock:
                per_page_remain = (
                    self.min_interval_s - (now - self._last_done.get(page_name, 0.0))
                )
                inter_page_remain = (
                    self.min_inter_page_interval_s - (now - self._last_done_any)
                )
            remaining = max(per_page_remain, inter_page_remain) + jitter
            jitter = 0.0   # apply only once
            if remaining <= 0:
                return
            time.sleep(min(remaining, 0.5))

    def _current_day_key(self) -> str:
        """Day boundary in configured timezone. Format YYYY-MM-DD."""
        return datetime.now(self._tz()).strftime("%Y-%m-%d")

    def _tz(self):
        try:
            return ZoneInfo(self.timezone_name)
        except (ZoneInfoNotFoundError, Exception):
            return ZoneInfo("UTC")

    def _purge_old_day_keys(self, today_key: str):
        """Drop daily-count entries for past days. Keeps dicts tiny."""
        stale = [k for k in self._daily_counts if k[1] != today_key]
        for k in stale:
            self._daily_counts.pop(k, None)
        stale_acc = [k for k in self._account_daily_counts if k[1] != today_key]
        for k in stale_acc:
            self._account_daily_counts.pop(k, None)

    # ── Private: existing ─────────────────────────────────────────────────────

    def _semaphore_for(self, page_name: str) -> threading.Semaphore:
        with self._lock:
            if page_name not in self._semaphores:
                self._semaphores[page_name] = threading.Semaphore(self.max_concurrent)
            return self._semaphores[page_name]
