"""
Anti-Spam Phase 2 tests:
  P2.1 — Adaptive backoff mapped to FB error codes
  P2.2 — Token health reports
  P4.3 — Comment-timing variation (covered here because it's a small module)
"""
from __future__ import annotations

import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from core.adaptive_backoff import (
    BackoffPolicy,
    get_backoff_for_fb_error,
    is_abuse_signal,
    is_permanent,
    is_rate_limit_error,
)
from core.token_health import (
    TokenHealthLevel,
    assess_expiry,
    report_facebook_account,
    report_tiktok_account,
)


# =============================================================================
# P2.1 — Adaptive backoff
# =============================================================================

class TestAdaptiveBackoffMapping(unittest.TestCase):

    def test_p2_1_permanent_errors_not_retryable(self):
        for code in (190, 102, 200, 104, 10, 230):
            with self.subTest(code=code):
                p = get_backoff_for_fb_error(code, jitter=False)
                self.assertFalse(p.retryable, f"code {code} should be permanent")
                self.assertEqual(p.severity, "permanent")
                self.assertTrue(is_permanent(code))

    def test_p2_1_rate_errors_have_long_cooldown(self):
        for code in (4, 17, 32, 613):
            with self.subTest(code=code):
                p = get_backoff_for_fb_error(code, jitter=False)
                self.assertTrue(p.retryable)
                self.assertEqual(p.severity, "rate")
                self.assertGreaterEqual(p.cooldown_s, 1800,
                                        f"code {code} should pause >= 30 min")
                self.assertTrue(is_rate_limit_error(code))

    def test_p2_1_abuse_errors_24h_or_more(self):
        p = get_backoff_for_fb_error(368, jitter=False)
        self.assertEqual(p.severity, "abuse")
        self.assertGreaterEqual(p.cooldown_s, 21600)  # ≥ 6 h
        self.assertTrue(p.notify_user)
        self.assertTrue(is_abuse_signal(368))

    def test_p2_1_transient_short_cooldown(self):
        p = get_backoff_for_fb_error(503, jitter=False)
        self.assertEqual(p.severity, "transient")
        self.assertLess(p.cooldown_s, 600)
        self.assertTrue(p.retryable)

    def test_p2_1_unknown_code_uses_default(self):
        p = get_backoff_for_fb_error(999999, jitter=False)
        self.assertTrue(p.retryable)
        self.assertEqual(p.severity, "transient")
        self.assertEqual(p.cooldown_s, 60)

    def test_p2_1_jitter_varies_cooldown(self):
        """Two calls with jitter should USUALLY differ by a bit. Run a few
        attempts to avoid spurious failure when random.uniform happens to
        return the same float twice."""
        base = get_backoff_for_fb_error(17, jitter=False).cooldown_s
        seen = {get_backoff_for_fb_error(17, jitter=True).cooldown_s for _ in range(20)}
        # Most should differ from the base; allow exact equality for at most 1/20
        diffs = [v for v in seen if abs(v - base) > 0.1]
        self.assertGreater(len(diffs), 0, "jitter must perturb the cooldown")

    def test_p2_1_jitter_within_15_percent(self):
        base = get_backoff_for_fb_error(17, jitter=False).cooldown_s
        for _ in range(50):
            v = get_backoff_for_fb_error(17, jitter=True).cooldown_s
            self.assertGreaterEqual(v, base * 0.84)
            self.assertLessEqual(v, base * 1.16)

    def test_p2_1_video_format_errors_permanent(self):
        for code in (6000, 6001, 6002):
            with self.subTest(code=code):
                self.assertTrue(is_permanent(code))


# =============================================================================
# P2.2 — Token health
# =============================================================================

class TestAssessExpiry(unittest.TestCase):

    def test_p2_2_no_expiry_is_healthy(self):
        level, days = assess_expiry(None)
        self.assertIs(level, TokenHealthLevel.HEALTHY)

    def test_p2_2_far_future_healthy(self):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        level, days = assess_expiry(future)
        self.assertIs(level, TokenHealthLevel.HEALTHY)
        self.assertGreater(days, 14)

    def test_p2_2_aging_window(self):
        ts = datetime.now(timezone.utc) + timedelta(days=10)
        level, _ = assess_expiry(ts)
        self.assertIs(level, TokenHealthLevel.AGING)

    def test_p2_2_warn_window(self):
        ts = datetime.now(timezone.utc) + timedelta(days=3)
        level, _ = assess_expiry(ts)
        self.assertIs(level, TokenHealthLevel.WARN)

    def test_p2_2_critical_window(self):
        ts = datetime.now(timezone.utc) + timedelta(hours=12)
        level, _ = assess_expiry(ts)
        self.assertIs(level, TokenHealthLevel.CRITICAL)

    def test_p2_2_expired(self):
        ts = datetime.now(timezone.utc) - timedelta(days=2)
        level, days = assess_expiry(ts)
        self.assertIs(level, TokenHealthLevel.EXPIRED)
        self.assertLess(days, 0)


class TestReportBuilders(unittest.TestCase):

    def test_p2_2_facebook_report_from_account(self):
        future = (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()
        account = MagicMock()
        account.fb_user_id = "u_1"
        account.name = "Test User"
        account.token_expires_at = future
        r = report_facebook_account(account)
        self.assertEqual(r.platform, "facebook")
        self.assertEqual(r.account_id, "u_1")
        self.assertIs(r.level, TokenHealthLevel.HEALTHY)

    def test_p2_2_tiktok_report_from_account(self):
        future_ts = (datetime.now(timezone.utc) + timedelta(hours=12)).timestamp()
        account = MagicMock()
        account.open_id = "tt_1"
        account.display_name = "TTUser"
        account.expires_at = future_ts
        r = report_tiktok_account(account)
        self.assertEqual(r.platform, "tiktok")
        self.assertEqual(r.account_id, "tt_1")
        self.assertIs(r.level, TokenHealthLevel.CRITICAL)

    def test_p2_2_handles_string_iso_with_z(self):
        ts = (datetime.now(timezone.utc) + timedelta(days=8)).isoformat()
        # ISO ends with +00:00; verify a Z-terminated variant also parses
        ts_z = ts.replace("+00:00", "Z")
        account = MagicMock()
        account.fb_user_id = "x"; account.name = "n"
        account.token_expires_at = ts_z
        r = report_facebook_account(account)
        self.assertIn(r.level, (TokenHealthLevel.AGING, TokenHealthLevel.WARN))

    def test_p2_2_invalid_expiry_treated_healthy(self):
        """Garbage expiry string → treated as 'no expiry' → HEALTHY (don't
        accidentally panic the user over a parse failure)."""
        account = MagicMock()
        account.fb_user_id = "x"; account.name = "n"
        account.token_expires_at = "garbage"
        r = report_facebook_account(account)
        self.assertIs(r.level, TokenHealthLevel.HEALTHY)


# =============================================================================
# P4.3 — Comment-timing variation
# =============================================================================

class TestCommenterDelay(unittest.TestCase):
    """The FacebookCommenter._compute_comment_delay helper used by P4.3."""

    def _make_commenter(self, min_s, max_s):
        from core.facebook.commenter import FacebookCommenter
        client = MagicMock()
        return FacebookCommenter(
            client            = client,
            page_access_token = "tok",
            stop_event        = threading.Event(),
            comment_delay_min_s = min_s,
            comment_delay_max_s = max_s,
        )

    def test_p4_3_delay_zero_when_disabled(self):
        c = self._make_commenter(0, 0)
        self.assertEqual(c._compute_comment_delay(), 0.0)

    def test_p4_3_delay_within_range(self):
        c = self._make_commenter(30, 60)
        for _ in range(20):
            d = c._compute_comment_delay()
            self.assertGreaterEqual(d, 30.0)
            self.assertLessEqual(d, 60.0)

    def test_p4_3_zero_min_zero_max_means_disabled(self):
        c = self._make_commenter(0, 0)
        self.assertEqual(c._compute_comment_delay(), 0.0)

    def test_p4_3_sleep_interruptible_wakes_on_stop(self):
        c = self._make_commenter(0, 0)
        # Start a worker that sleeps 5s, then stop after 0.3s
        result = {"slept": 0.0}

        def worker():
            t0 = time.time()
            c._sleep_interruptible(5.0)
            result["slept"] = time.time() - t0

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        time.sleep(0.3)
        c._stop.set()
        t.join(timeout=3)
        self.assertLess(result["slept"], 2.5,
                        "stop_event should break the sleep within 1-2 s")


if __name__ == "__main__":
    unittest.main()
