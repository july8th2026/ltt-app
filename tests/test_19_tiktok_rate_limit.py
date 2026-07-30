"""
Tests for the TikTokPublisher rate-limit integration (Phase 5 fix).

Before the fix, rate_limiter was accepted as a parameter but completely ignored
inside TikTokPublisher — meaning all of the anti-ban mechanisms (per-account
interval, daily quota, jitter, active hours) silently didn't apply to TikTok
uploads. These tests lock that behaviour in place going forward.
"""
from __future__ import annotations

import threading
import unittest
from unittest.mock import MagicMock, patch

from core.rate_limiter import QuotaExceededError, RateLimiter, reset_global_metrics
from core.tiktok.publisher_service import TikTokPublisher
from core.tiktok.token_store import TikTokAccount


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_account(open_id="u1", display_name="TestUser"):
    """Construct a minimal TikTokAccount sufficient for publish() exercises."""
    import time
    future = time.time() + 30 * 24 * 3600
    return TikTokAccount(
        open_id            = open_id,
        display_name       = display_name,
        avatar_url         = "",
        access_token       = "fake_access_token",
        refresh_token      = "fake_refresh",
        expires_at         = future,
        refresh_expires_at = future,
        scopes             = ["user.info.basic", "video.upload", "video.publish"],
    )


def _make_publisher(rate_limiter=None, audit_approved=True):
    """Spawn a TikTokPublisher with a stub stop_event and minimal config."""
    config = {
        "tiktok_audit_approved":    audit_approved,
        "tiktok_enable_direct_post": True,
        "tiktok_request_timeout_s": 5,
    }
    return TikTokPublisher(
        config       = config,
        stop_event   = threading.Event(),
        on_log       = lambda m, l: None,
        on_status    = lambda m: None,
        rate_limiter = rate_limiter,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Publisher stores the rate_limiter (no longer "ignored")
# ─────────────────────────────────────────────────────────────────────────────

class TestRateLimiterAccepted(unittest.TestCase):

    def setUp(self):
        reset_global_metrics()

    def test_publisher_keeps_rate_limiter_reference(self):
        rl = RateLimiter(min_interval_s=0.0)
        pub = _make_publisher(rate_limiter=rl)
        self.assertIs(pub._rate_limiter, rl)

    def test_publisher_accepts_none_for_back_compat(self):
        pub = _make_publisher(rate_limiter=None)
        self.assertIsNone(pub._rate_limiter)


# ─────────────────────────────────────────────────────────────────────────────
# 2. acquire/release happens during publish — checked via direct invocation
#    of the rate limiter's daily counters (no need to mock the upload path).
# ─────────────────────────────────────────────────────────────────────────────

class TestPublishCallsAcquireRelease(unittest.TestCase):

    def setUp(self):
        reset_global_metrics()

    def test_publish_increments_account_daily_count(self):
        """A successful publish must release() → which bumps account_daily_count.
        We mock everything past compliance check to avoid touching network."""
        rl = RateLimiter(min_interval_s=0.0)
        pub = _make_publisher(rate_limiter=rl)

        account = _make_account(open_id="u_quota_test", display_name="QT")

        # Mock the inner pipeline so publish() returns without network I/O
        pub._resolve_account     = MagicMock(return_value=account)
        pub._ensure_token_fresh  = MagicMock(return_value=account)
        pub._upload_draft        = MagicMock(return_value=MagicMock(
            success=True, external_post_id="pid_1", status="draft",
        ))

        with patch(
            "core.tiktok.compliance_guard.TikTokComplianceGuard.check",
            return_value=[],
        ):
            pub.publish({
                "video_path": "/tmp/x.mp4",
                "post_type":  "tiktok_draft",
            })

        self.assertEqual(rl.account_daily_count("u_quota_test"), 1)

    def test_publish_releases_even_on_exception(self):
        """If upload raises, release() must still be called so the slot is
        freed and the daily counter still increments (penalises a failed
        attempt the same way as a success — protects against retry loops)."""
        rl = RateLimiter(min_interval_s=0.0)
        pub = _make_publisher(rate_limiter=rl)

        account = _make_account(open_id="u_err_test", display_name="ER")
        pub._resolve_account    = MagicMock(return_value=account)
        pub._ensure_token_fresh = MagicMock(return_value=account)
        pub._upload_draft       = MagicMock(side_effect=RuntimeError("boom"))

        with patch(
            "core.tiktok.compliance_guard.TikTokComplianceGuard.check",
            return_value=[],
        ):
            with self.assertRaises(RuntimeError):
                pub.publish({
                    "video_path": "/tmp/x.mp4",
                    "post_type":  "tiktok_draft",
                })

        # Even on failure, release ran → daily count = 1
        self.assertEqual(rl.account_daily_count("u_err_test"), 1)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Quota enforcement actually blocks TikTok publishes
# ─────────────────────────────────────────────────────────────────────────────

class TestTikTokQuotaEnforced(unittest.TestCase):

    def setUp(self):
        reset_global_metrics()

    def test_per_account_quota_blocks_third_attempt(self):
        rl = RateLimiter(
            min_interval_s=0.0,
            max_posts_per_account_per_day=2,
        )
        pub = _make_publisher(rate_limiter=rl)
        account = _make_account(open_id="u_cap", display_name="Capped")
        pub._resolve_account    = MagicMock(return_value=account)
        pub._ensure_token_fresh = MagicMock(return_value=account)
        pub._upload_draft       = MagicMock(return_value=MagicMock(
            success=True, external_post_id="pid", status="draft",
        ))

        with patch(
            "core.tiktok.compliance_guard.TikTokComplianceGuard.check",
            return_value=[],
        ):
            # 2 successful publishes — within cap
            pub.publish({"video_path": "/tmp/x.mp4", "post_type": "tiktok_draft"})
            pub.publish({"video_path": "/tmp/x.mp4", "post_type": "tiktok_draft"})
            # 3rd → QuotaExceededError before any network call
            with self.assertRaises(QuotaExceededError):
                pub.publish({"video_path": "/tmp/x.mp4", "post_type": "tiktok_draft"})


# ─────────────────────────────────────────────────────────────────────────────
# 4. Back-compat: rate_limiter=None still works (legacy path)
# ─────────────────────────────────────────────────────────────────────────────

class TestNoneRateLimiterBackCompat(unittest.TestCase):

    def setUp(self):
        reset_global_metrics()

    def test_publish_without_limiter_doesnt_crash(self):
        """Tests that pre-existed (test_15_tiktok_commenter) called the publisher
        with rate_limiter=None and expected nothing weird to happen."""
        pub = _make_publisher(rate_limiter=None)
        account = _make_account(open_id="u_none")
        pub._resolve_account    = MagicMock(return_value=account)
        pub._ensure_token_fresh = MagicMock(return_value=account)
        pub._upload_draft       = MagicMock(return_value=MagicMock(
            success=True, external_post_id="pid", status="draft",
        ))

        with patch(
            "core.tiktok.compliance_guard.TikTokComplianceGuard.check",
            return_value=[],
        ):
            result = pub.publish({
                "video_path": "/tmp/x.mp4",
                "post_type":  "tiktok_draft",
            })
        # No exception, returns the mocked result — confirming None path works
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
