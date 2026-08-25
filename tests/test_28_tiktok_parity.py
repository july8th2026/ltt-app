"""
Sprint TT-1..4 — parity tests bringing TikTok to feature equivalence
with the Facebook anti-spam stack.

Sections:
  TT-1.1  Adaptive backoff for TikTok error codes
  TT-1.2  TikTok account warm-up (audit-log first-seen)
  TT-1.3  Network identity wired into TikTokClient
  TT-1.4  TikTokClientPool round-robin
  TT-1.5  check_tiktok_app_status probe
  TT-1.6  TikTokCommenter delay variation
  TT-1.8  Notifier TT-specific methods
  TT-2.3  AntiSpamSnapshot has TikTok fields
  TT-3.1  Settings DEFAULTS + tooltips for new TT keys
  TT-4.1  Audit checklist
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from core.adaptive_backoff import (
    get_backoff_for_tiktok_error,
    is_tiktok_abuse_signal,
    is_tiktok_permanent,
)
from core.tiktok.account_warmup import (
    TikTokWarmupAdvice,
    clear_cache as _clear_tt_warmup_cache,
    effective_daily_cap,
    get_warmup_advice,
    recommended_cap_for_age,
)
from core.tiktok.multi_client import TikTokClientPool, TikTokClientRecord
from core.app_status import (
    AppStatus, check_tiktok_app_status, is_app_disabled,
)
from core.tiktok.audit_checklist import (
    CheckResult, ChecklistReport, run_checklist,
)


# =============================================================================
# TT-1.1 — TikTok adaptive backoff codes
# =============================================================================

class TestTikTokAdaptiveBackoff(unittest.TestCase):

    def test_tt_permanent_codes(self):
        for code in (
            "access_token_invalid",
            "scope_not_authorized",
            "invalid_param",
            "privacy_level_option_mismatch",
            "video_pull_failed",
        ):
            with self.subTest(code=code):
                p = get_backoff_for_tiktok_error(code, jitter=False)
                self.assertEqual(p.severity, "permanent")
                self.assertTrue(is_tiktok_permanent(code))

    def test_tt_rate_limit_codes(self):
        for code in ("rate_limit_exceeded", "daily_publish_cap_exceeded"):
            with self.subTest(code=code):
                p = get_backoff_for_tiktok_error(code, jitter=False)
                self.assertEqual(p.severity, "rate")
                self.assertTrue(p.retryable)
                self.assertGreaterEqual(p.cooldown_s, 3600)

    def test_tt_abuse_codes_flag_and_long_cooldown(self):
        for code in ("spam_risk_text", "spam_risk_user_banned_from_posting",
                     "spam_risk_too_many_posts"):
            with self.subTest(code=code):
                self.assertTrue(is_tiktok_abuse_signal(code))
                p = get_backoff_for_tiktok_error(code, jitter=False)
                self.assertGreaterEqual(p.cooldown_s, 6 * 3600)

    def test_tt_unknown_code_default(self):
        p = get_backoff_for_tiktok_error("never_seen_code", jitter=False)
        self.assertTrue(p.retryable)
        self.assertEqual(p.severity, "transient")

    def test_tt_jitter_perturbs_cooldown(self):
        base = get_backoff_for_tiktok_error("rate_limit_exceeded",
                                            jitter=False).cooldown_s
        seen = {get_backoff_for_tiktok_error(
            "rate_limit_exceeded", jitter=True
        ).cooldown_s for _ in range(20)}
        diffs = [v for v in seen if abs(v - base) > 0.1]
        self.assertGreater(len(diffs), 0)


# =============================================================================
# TT-1.2 — Account warm-up
# =============================================================================

class TestTikTokAccountWarmup(unittest.TestCase):

    def setUp(self):
        _clear_tt_warmup_cache()
        # Custom audit log per-test so we don't depend on shared state
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl",
                                        mode="w", encoding="utf-8")
        f.close()
        self.log_path = f.name

    def tearDown(self):
        _clear_tt_warmup_cache()
        try: os.unlink(self.log_path)
        except OSError: pass

    def _write_audit(self, records):
        with open(self.log_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

    def test_curve_progression(self):
        self.assertEqual(recommended_cap_for_age(0),    1)
        self.assertEqual(recommended_cap_for_age(5),    2)
        self.assertEqual(recommended_cap_for_age(20),   4)
        self.assertEqual(recommended_cap_for_age(100),  0)  # mature

    def test_no_history_treated_as_brand_new(self):
        self._write_audit([])
        advice = get_warmup_advice("u_no_history",
                                    audit_log_path=self.log_path)
        self.assertEqual(advice.age_days, 0)
        self.assertEqual(advice.recommended_max_per_day, 1)

    def test_first_seen_age(self):
        ten_days_ago = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        self._write_audit([
            {"event": "tiktok_publish_attempt", "open_id": "u_ten",
             "timestamp": ten_days_ago},
        ])
        advice = get_warmup_advice("u_ten", audit_log_path=self.log_path)
        # 10 days → falls in <=14 bracket → 3 posts/day
        self.assertGreaterEqual(advice.age_days, 9)
        self.assertLessEqual(advice.age_days, 11)
        self.assertEqual(advice.recommended_max_per_day, 3)

    def test_other_open_ids_ignored(self):
        old = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
        self._write_audit([
            {"event": "tiktok_publish_attempt", "open_id": "u_OTHER",
             "timestamp": old},
        ])
        advice = get_warmup_advice("u_mine", audit_log_path=self.log_path)
        # u_mine has no history → brand-new
        self.assertEqual(advice.age_days, 0)

    def test_effective_daily_cap_combines(self):
        adv = TikTokWarmupAdvice(open_id="u", age_days=5,
                                  recommended_max_per_day=2, note="")
        self.assertEqual(effective_daily_cap(adv, user_cap=10), 2)
        self.assertEqual(effective_daily_cap(adv, user_cap=1),  1)


# =============================================================================
# TT-1.3 — Network identity in TikTokClient
# =============================================================================

class TestTikTokClientIdentity(unittest.TestCase):

    def test_no_identity_when_disabled(self):
        from core.tiktok.client import TikTokClient
        c = TikTokClient(access_token="t", account_id="acc_X", config={})
        self.assertEqual(c._identity_ua, "")
        self.assertEqual(c._identity_proxy, "")

    def test_identity_applied_when_enabled(self):
        from core.network_identity import reset_default_provider
        reset_default_provider()
        from core.tiktok.client import TikTokClient
        c = TikTokClient(
            access_token="t", account_id="acc_X",
            config={"network_identity_enabled": True},
        )
        self.assertIn("Mozilla/5.0", c._identity_ua)

    def test_apply_identity_merges_headers_and_proxies(self):
        from core.tiktok.client import TikTokClient
        c = TikTokClient(access_token="t")
        c._identity_ua    = "TestUA/1.0"
        c._identity_proxy = "http://proxy:8080"
        headers, kw = {}, {}
        c._apply_identity(headers, kw)
        self.assertEqual(headers["User-Agent"], "TestUA/1.0")
        self.assertEqual(kw["proxies"]["https"], "http://proxy:8080")


# =============================================================================
# TT-1.4 — TikTokClientPool
# =============================================================================

class TestTikTokClientPool(unittest.TestCase):

    def test_empty_pool(self):
        p = TikTokClientPool()
        self.assertIsNone(p.next_healthy())

    def test_round_robin(self):
        p = TikTokClientPool([
            TikTokClientRecord(client_key="K1", client_secret="s1"),
            TikTokClientRecord(client_key="K2", client_secret="s2"),
        ])
        keys = {p.next_healthy().client_key for _ in range(6)}
        self.assertEqual(keys, {"K1", "K2"})

    def test_disabled_skipped(self):
        p = TikTokClientPool([
            TikTokClientRecord(client_key="K1", client_secret="s1"),
            TikTokClientRecord(client_key="K2", client_secret="s2"),
        ])
        p.mark_disabled("K1")
        for _ in range(4):
            self.assertEqual(p.next_healthy().client_key, "K2")

    def test_legacy_config_fallback(self):
        p = TikTokClientPool.from_config({
            "tiktok_client_key": "legacy_K",
            "tiktok_client_secret": "legacy_s",
        })
        self.assertEqual(p.healthy_count(), 1)
        self.assertEqual(p.next_healthy().client_key, "legacy_K")

    def test_pool_config_used(self):
        p = TikTokClientPool.from_config({
            "tiktok_client_pool": [
                {"client_key": "P1", "client_secret": "ps1"},
                {"client_key": "P2", "client_secret": "ps2", "disabled": True},
            ],
        })
        self.assertEqual(p.healthy_count(), 1)
        self.assertEqual(p.next_healthy().client_key, "P1")

    def test_auth_manager_uses_pool(self):
        from core.tiktok.auth_manager import TikTokAuthManager
        am = TikTokAuthManager(config={
            "tiktok_client_pool": [
                {"client_key": "POOL_K", "client_secret": "POOL_S",
                 "redirect_uri": "https://x"},
            ],
        })
        self.assertEqual(am.client_key, "POOL_K")
        self.assertEqual(am.redirect_uri, "https://x")


# =============================================================================
# TT-1.5 — TikTok app status probe
# =============================================================================

class TestTikTokAppStatusProbe(unittest.TestCase):

    def test_no_credentials(self):
        report = check_tiktok_app_status({})
        self.assertIs(report.status, AppStatus.NOT_CONFIGURED)

    def test_ok_when_token_returned(self):
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"access_token": "abc", "expires_in": 7200}
        with patch("requests.post", return_value=fake_resp):
            r = check_tiktok_app_status({
                "tiktok_client_key": "K", "tiktok_client_secret": "S",
            })
        self.assertIs(r.status, AppStatus.OK)

    def test_disabled_when_401(self):
        fake_resp = MagicMock()
        fake_resp.status_code = 401
        fake_resp.json.return_value = {"error": "unauthorized_client",
                                        "error_description": "key revoked"}
        with patch("requests.post", return_value=fake_resp):
            r = check_tiktok_app_status({
                "tiktok_client_key": "K", "tiktok_client_secret": "S",
            })
        self.assertIs(r.status, AppStatus.DISABLED)
        self.assertTrue(is_app_disabled(r))


# =============================================================================
# TT-1.6 — Comment delay
# =============================================================================

class TestTikTokCommentDelay(unittest.TestCase):

    def _make_commenter(self, min_s, max_s):
        from core.tiktok.commenter import TikTokCommenter
        from core.tiktok.client import TikTokClient
        client = MagicMock(spec=TikTokClient)
        return TikTokCommenter(
            client=client, stop_event=threading.Event(),
            comment_delay_min_s=min_s, comment_delay_max_s=max_s,
        )

    def test_delay_zero_when_disabled(self):
        c = self._make_commenter(0, 0)
        self.assertEqual(c._compute_comment_delay(), 0.0)

    def test_delay_within_range(self):
        c = self._make_commenter(30, 60)
        for _ in range(20):
            d = c._compute_comment_delay()
            self.assertGreaterEqual(d, 30.0)
            self.assertLessEqual(d, 60.0)

    def test_sleep_interruptible(self):
        c = self._make_commenter(0, 0)
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
        self.assertLess(result["slept"], 2.5)


# =============================================================================
# TT-1.8 — Notifier TT-specific methods
# =============================================================================

class TestNotifierTikTokMethods(unittest.TestCase):

    def _make_notifier(self):
        from utils.notifier import TelegramNotifier
        return TelegramNotifier(config={
            "telegram_bot_token": "", "telegram_chat_id": "",
            "notify_on_error": True,
        })

    def test_tt_methods_exist(self):
        n = self._make_notifier()
        self.assertTrue(callable(getattr(n, "notify_tiktok_compliance_violation", None)))
        self.assertTrue(callable(getattr(n, "notify_tiktok_audit_required",      None)))
        self.assertTrue(callable(getattr(n, "notify_tiktok_post_blocked",        None)))

    def test_tt_methods_do_not_raise(self):
        n = self._make_notifier()
        # Disabled notifier → all no-op, must not raise
        n.notify_tiktok_compliance_violation("acc_X", "code", "msg")
        n.notify_tiktok_audit_required("acc_X", "submit Comment Mgmt API")
        n.notify_tiktok_post_blocked("acc_X", "spam_risk_text")


# =============================================================================
# TT-2.3 — Snapshot has TikTok fields
# =============================================================================

class TestSnapshotTikTokFields(unittest.TestCase):

    def test_has_tiktok_fields(self):
        from core.anti_spam_analytics import AntiSpamSnapshot
        snap = AntiSpamSnapshot()
        for f in (
            "tiktok_app_status",
            "tiktok_app_message",
            "tiktok_client_pool_healthy",
            "tiktok_client_pool_total",
        ):
            self.assertTrue(hasattr(snap, f), f"snapshot missing {f}")

    def test_collect_snapshot_tt_fields_default_safe(self):
        from core.anti_spam_analytics import collect_snapshot
        snap = collect_snapshot(current_config={})
        self.assertIn(snap.tiktok_app_status,
                      ("", "not_configured", "unknown", "ok"))

    def test_format_oneline_shows_disabled_tt(self):
        from core.anti_spam_analytics import AntiSpamSnapshot, format_oneline
        snap = AntiSpamSnapshot()
        snap.tiktok_app_status = "disabled"
        line = format_oneline(snap)
        self.assertIn("TT App", line)


# =============================================================================
# TT-3.1 — Defaults + tooltips for new TT keys
# =============================================================================

class TestTikTokSettingsKeys(unittest.TestCase):

    REQUIRED = {
        "tt_comment_delay_min_s",
        "tt_comment_delay_max_s",
        "tiktok_client_pool",
    }

    def test_all_in_defaults(self):
        from core.config_defaults import DEFAULTS
        for k in self.REQUIRED:
            self.assertIn(k, DEFAULTS, f"DEFAULTS missing {k}")

    def test_all_have_tooltips(self):
        from core.config_help import FIELD_HELP as tips
        for k in self.REQUIRED:
            self.assertIn(k, tips, f"Tooltip missing for {k}")


# =============================================================================
# TT-4.1 — Audit checklist
# =============================================================================

class TestTikTokAuditChecklist(unittest.TestCase):

    def test_empty_config_fails_multiple_checks(self):
        report = run_checklist({})
        self.assertGreater(report.fail_count, 0)
        self.assertFalse(report.ready_to_submit)

    def test_full_config_passes_credentials_and_urls(self):
        """TT-AUDIT-8 fix: run_checklist now does live HEAD + GET on URLs.
        Mock both to make test deterministic + offline-safe."""
        from unittest.mock import patch, MagicMock
        config = {
            "tiktok_client_key":          "abc",
            "tiktok_client_secret":       "secret",
            "tiktok_redirect_uri":        "https://lttstudios.com/legal/callback.html",
            "app_privacy_policy_url":     "https://lttstudios.com/legal/privacy.html",
            "app_terms_url":              "https://lttstudios.com/legal/terms.html",
            "tiktok_scopes":              "user.info.basic,video.upload,video.publish",
            "tiktok_audit_approved":      False,
            "tiktok_enable_direct_post":  False,
            "tiktok_require_user_confirm": True,
            "tiktok_privacy_level":       "SELF_ONLY",
        }
        # Fake live response: privacy policy mentions all required keywords
        fake_text = "tiktok open_id access token video scope policy lttstudio"
        fake_resp = MagicMock(status_code=200, text=fake_text)
        from core.tiktok import audit_checklist as ac
        with patch.object(ac, "_head_url", return_value=(True, "HTTP 200")), \
             patch.object(ac.requests, "get", return_value=fake_resp):
            report = run_checklist(config)
        # Credentials + URIs + scopes + audit flags must pass
        passes = {i.name for i in report.items if i.result is CheckResult.PASS}
        self.assertIn("Client Credentials", passes)
        self.assertIn("Redirect URI",       passes)
        self.assertIn("Privacy + Terms URLs", passes)
        self.assertIn("Scopes",             passes)
        self.assertIn("Audit flags",        passes)

    def test_inconsistent_direct_post_fails(self):
        report = run_checklist({
            "tiktok_client_key": "k", "tiktok_client_secret": "s",
            "tiktok_redirect_uri": "https://x.tld/cb",
            "app_privacy_policy_url": "https://x.tld/p",
            "app_terms_url":          "https://x.tld/t",
            "tiktok_scopes": "user.info.basic,video.upload,video.publish",
            "tiktok_enable_direct_post": True,
            "tiktok_audit_approved":     False,
        })
        fails = {i.name for i in report.items if i.result is CheckResult.FAIL}
        self.assertIn("Audit flags", fails)

    def test_summary_helpful(self):
        report = run_checklist({})
        self.assertTrue(report.summary())


if __name__ == "__main__":
    unittest.main()
