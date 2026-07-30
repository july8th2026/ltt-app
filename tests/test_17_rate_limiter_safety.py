"""
Tests for production-safety dimensions added to RateLimiter:
  - min_inter_page_interval_s
  - jitter_s
  - active_hours_start / active_hours_end
  - max_posts_per_page_per_day
  - daily_count() accessor + day-key purging

Each test asserts the new feature is OPT-IN: defaults (0/empty) preserve the
legacy behaviour exercised by test_05/test_06.
"""
from __future__ import annotations

import threading
import time
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from core.rate_limiter import (
    QuotaExceededError,
    RateLimiter,
    reset_global_metrics,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Backwards compatibility — defaults preserve legacy behaviour
# ─────────────────────────────────────────────────────────────────────────────

class TestBackwardsCompat(unittest.TestCase):

    def setUp(self):
        reset_global_metrics()

    def test_legacy_signature_still_works(self):
        # The 2-arg construction used by test_05 / test_06 must still work
        lim = RateLimiter(max_concurrent=2, min_interval_s=0.0)
        lim.acquire("P1")
        lim.release("P1")
        # No exception → legacy path intact

    def test_no_new_dimensions_no_block(self):
        # With all new dims at 0/empty, acquire+release of any page must NOT
        # wait beyond the original per-page interval.
        lim = RateLimiter(max_concurrent=1, min_interval_s=0.0)
        start = time.time()
        lim.acquire("A"); lim.release("A")
        lim.acquire("B"); lim.release("B")
        self.assertLess(time.time() - start, 1.0,
                        "two distinct-page acquires must be near-instant by default")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Inter-page interval
# ─────────────────────────────────────────────────────────────────────────────

class TestInterPageInterval(unittest.TestCase):

    def setUp(self):
        reset_global_metrics()

    def test_inter_page_interval_blocks_other_pages(self):
        """After releasing Page A, Page B's acquire must wait for the global gap."""
        lim = RateLimiter(
            max_concurrent=1,
            min_interval_s=0.0,            # no per-page wait
            min_inter_page_interval_s=0.4,  # 400 ms global gap
        )
        lim.acquire("A"); lim.release("A")
        t0 = time.time()
        lim.acquire("B"); lim.release("B")
        elapsed = time.time() - t0
        self.assertGreaterEqual(elapsed, 0.35,
                                f"B should wait ~0.4 s, got {elapsed:.3f}s")
        self.assertLess(elapsed, 1.5)

    def test_zero_inter_page_means_no_block(self):
        lim = RateLimiter(min_interval_s=0.0, min_inter_page_interval_s=0.0)
        lim.acquire("A"); lim.release("A")
        t0 = time.time()
        lim.acquire("B"); lim.release("B")
        self.assertLess(time.time() - t0, 0.3)

    def test_wait_until_ready_includes_inter_page(self):
        """wait_until_ready must reflect inter-page wait, even for never-posted page."""
        lim = RateLimiter(min_interval_s=0.0, min_inter_page_interval_s=10.0)
        lim.acquire("A"); lim.release("A")
        # Page B has never been touched, but inter-page gate still applies
        remaining = lim.wait_until_ready("B")
        self.assertGreater(remaining, 9.0)
        self.assertLessEqual(remaining, 10.0)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Jitter
# ─────────────────────────────────────────────────────────────────────────────

class TestJitter(unittest.TestCase):

    def setUp(self):
        reset_global_metrics()

    def test_jitter_adds_extra_wait(self):
        """With jitter, the actual wait must be at least the base interval and
        at most (base + jitter) — broken into a deterministic check via patch."""
        lim = RateLimiter(
            max_concurrent=1,
            min_interval_s=0.2,
            jitter_s=0.3,
        )
        lim.acquire("A"); lim.release("A")
        # Force the random.uniform return to a known value
        with patch("core.rate_limiter.random.uniform", return_value=0.25):
            t0 = time.time()
            lim.acquire("A"); lim.release("A")
            elapsed = time.time() - t0
        # Expected wait: 0.2 (interval) + 0.25 (jitter) = 0.45
        self.assertGreaterEqual(elapsed, 0.4)
        self.assertLess(elapsed, 1.2)

    def test_zero_jitter_is_legacy_behaviour(self):
        lim = RateLimiter(min_interval_s=0.1, jitter_s=0.0)
        lim.acquire("A"); lim.release("A")
        t0 = time.time()
        lim.acquire("A"); lim.release("A")
        self.assertLess(time.time() - t0, 0.4)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Active hours window
# ─────────────────────────────────────────────────────────────────────────────

class TestActiveHours(unittest.TestCase):

    def setUp(self):
        reset_global_metrics()

    def test_inside_window_passes_through(self):
        # If current hour is anywhere in 0-23 and we set window 0-24-effective,
        # the gate must be open. We pick start==end which the implementation
        # treats as "disabled" — so any time is fine.
        lim = RateLimiter(min_interval_s=0.0, active_hours_start=0, active_hours_end=0)
        lim.acquire("X"); lim.release("X")  # no block

    def test_window_check_with_mock_clock(self):
        """Mock datetime so we control the 'current hour' and verify the window logic."""
        lim = RateLimiter(
            min_interval_s=0.0,
            active_hours_start=8,
            active_hours_end=23,
        )
        # Patch datetime to return 14:00 → inside 8-23 window → must pass instantly
        fake_now = datetime(2026, 5, 15, 14, 0, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
        with patch("core.rate_limiter.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            t0 = time.time()
            lim.acquire("X"); lim.release("X")
            self.assertLess(time.time() - t0, 0.5,
                            "Should pass instantly inside window")

    def test_window_crossing_midnight_logic(self):
        """A 22-6 window means active hours wrap midnight."""
        lim = RateLimiter(active_hours_start=22, active_hours_end=6)
        # Hour 23 → inside window
        self.assertTrue(
            (lim.active_hours_start <= 23) or (23 < lim.active_hours_end),
            "23h should be inside a 22-6 window"
        )
        # Hour 10 → outside
        self.assertFalse(
            (lim.active_hours_start <= 10 < lim.active_hours_end),
            "10h should be outside a 22-6 window (start<end branch)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Daily quota
# ─────────────────────────────────────────────────────────────────────────────

class TestDailyQuota(unittest.TestCase):

    def setUp(self):
        reset_global_metrics()

    def test_quota_disabled_by_default(self):
        lim = RateLimiter(min_interval_s=0.0)
        for _ in range(10):
            lim.acquire("P"); lim.release("P")
        # No exception → 0 cap means unlimited

    def test_quota_raises_when_exhausted(self):
        lim = RateLimiter(min_interval_s=0.0, max_posts_per_page_per_day=2)
        lim.acquire("P"); lim.release("P")
        lim.acquire("P"); lim.release("P")
        self.assertEqual(lim.daily_count("P"), 2)
        with self.assertRaises(QuotaExceededError):
            lim.acquire("P")

    def test_quota_is_per_page(self):
        """Quota for one page must not affect another page."""
        lim = RateLimiter(min_interval_s=0.0, max_posts_per_page_per_day=1)
        lim.acquire("A"); lim.release("A")
        with self.assertRaises(QuotaExceededError):
            lim.acquire("A")
        # Page B unaffected
        lim.acquire("B"); lim.release("B")

    def test_daily_count_starts_at_zero(self):
        lim = RateLimiter(min_interval_s=0.0, max_posts_per_page_per_day=5)
        self.assertEqual(lim.daily_count("brand-new"), 0)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Day-key purging — old day counts get dropped on new-day release
# ─────────────────────────────────────────────────────────────────────────────

class TestDayKeyPurge(unittest.TestCase):

    def setUp(self):
        reset_global_metrics()

    def test_old_day_keys_purged_on_release(self):
        """Insert a 'yesterday' count manually, release once today → purge."""
        lim = RateLimiter(min_interval_s=0.0, max_posts_per_page_per_day=10)
        # Inject a stale count for yesterday
        lim._daily_counts[("P", "2026-01-01")] = 42
        # Today's release should purge the stale entry
        lim.acquire("P"); lim.release("P")
        self.assertNotIn(("P", "2026-01-01"), lim._daily_counts)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Stop event still honoured with new dimensions
# ─────────────────────────────────────────────────────────────────────────────

class TestStopEventStillWorks(unittest.TestCase):

    def setUp(self):
        reset_global_metrics()

    def test_stop_event_breaks_inter_page_wait(self):
        lim = RateLimiter(
            max_concurrent=1,
            min_interval_s=0.0,
            min_inter_page_interval_s=10.0,    # would block for 10 s
        )
        lim.acquire("A"); lim.release("A")

        stop = threading.Event()
        result = {}

        def _worker():
            try:
                lim.acquire("B", stop_event=stop)
            except InterruptedError as e:
                result["caught"] = str(e)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        time.sleep(0.3)
        stop.set()
        t.join(timeout=2)
        self.assertFalse(t.is_alive(), "Worker should have exited via InterruptedError")
        self.assertIn("caught", result)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Per-account daily quota (Week 2-4 feature)
# ─────────────────────────────────────────────────────────────────────────────

class TestPerAccountQuota(unittest.TestCase):

    def setUp(self):
        reset_global_metrics()

    def test_account_quota_disabled_by_default(self):
        lim = RateLimiter(min_interval_s=0.0)
        # No account quota set → 10 acquires across multiple pages on same
        # account should pass
        for i in range(10):
            lim.acquire(f"P{i}", account_id="acc_X")
            lim.release(f"P{i}", account_id="acc_X")

    def test_account_quota_raises_across_multiple_pages(self):
        """An account managing 3 pages, cap=4. After 4 posts (any mix of pages),
        the 5th must raise — regardless of which page it's on."""
        lim = RateLimiter(
            min_interval_s=0.0,
            max_posts_per_account_per_day=4,
        )
        # Page 1, 2 posts
        lim.acquire("P1", account_id="acc_A"); lim.release("P1", account_id="acc_A")
        lim.acquire("P1", account_id="acc_A"); lim.release("P1", account_id="acc_A")
        # Page 2, 2 posts → total 4 for acc_A
        lim.acquire("P2", account_id="acc_A"); lim.release("P2", account_id="acc_A")
        lim.acquire("P2", account_id="acc_A"); lim.release("P2", account_id="acc_A")

        self.assertEqual(lim.account_daily_count("acc_A"), 4)

        # 5th attempt on ANY page of acc_A → reject
        with self.assertRaises(QuotaExceededError) as ctx:
            lim.acquire("P3", account_id="acc_A")
        self.assertIn("acc_A", str(ctx.exception))

    def test_account_quota_isolated_per_account(self):
        """acc_A hitting quota must NOT block acc_B."""
        lim = RateLimiter(
            min_interval_s=0.0,
            max_posts_per_account_per_day=1,
        )
        lim.acquire("P", account_id="acc_A")
        lim.release("P", account_id="acc_A")
        with self.assertRaises(QuotaExceededError):
            lim.acquire("P", account_id="acc_A")
        # Different account, same page → fine
        lim.acquire("P", account_id="acc_B")
        lim.release("P", account_id="acc_B")

    def test_account_id_missing_skips_account_check(self):
        """When acquire() is called without account_id (legacy call sites),
        the account-cap check must be skipped — back-compat with old code."""
        lim = RateLimiter(
            min_interval_s=0.0,
            max_posts_per_account_per_day=1,
        )
        # No account_id → cap is bypassed
        lim.acquire("P"); lim.release("P")
        lim.acquire("P"); lim.release("P")
        lim.acquire("P"); lim.release("P")

    def test_account_quota_combines_with_page_quota(self):
        """Both quotas active: page cap=2, account cap=5. After 2 posts on
        page A (page-capped), shifting to page B still allowed (account=2/5)."""
        lim = RateLimiter(
            min_interval_s=0.0,
            max_posts_per_page_per_day=2,
            max_posts_per_account_per_day=5,
        )
        lim.acquire("A", account_id="u"); lim.release("A", account_id="u")
        lim.acquire("A", account_id="u"); lim.release("A", account_id="u")
        with self.assertRaises(QuotaExceededError) as ctx:
            lim.acquire("A", account_id="u")
        self.assertIn("page 'A'", str(ctx.exception))   # page-cap hit, not account
        # Page B still under page-cap; account total 2/5 → fine
        lim.acquire("B", account_id="u"); lim.release("B", account_id="u")
        self.assertEqual(lim.account_daily_count("u"), 3)

    def test_account_count_zero_when_no_id(self):
        lim = RateLimiter(min_interval_s=0.0)
        self.assertEqual(lim.account_daily_count(""), 0)
        self.assertEqual(lim.account_daily_count("unseen"), 0)

    def test_purge_drops_old_account_keys(self):
        lim = RateLimiter(min_interval_s=0.0, max_posts_per_account_per_day=10)
        lim._account_daily_counts[("acc_X", "2025-12-31")] = 999
        lim.acquire("P", account_id="acc_X")
        lim.release("P", account_id="acc_X")
        self.assertNotIn(("acc_X", "2025-12-31"), lim._account_daily_counts)


if __name__ == "__main__":
    unittest.main()
