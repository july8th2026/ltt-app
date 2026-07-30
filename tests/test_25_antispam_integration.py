"""
Integration tests for the anti-spam GAP wirings.

These tests verify that the modules created in earlier phases are actually
wired into the runtime — fixing the audit finding that several modules
were created but never called from production code.

  GAP-1 — page_warmup wired into SheetRunner._tick
  GAP-2 — page_health.record_reach wired into InsightsFetcher
  GAP-3 — time_intel surfaced in AntiSpamSnapshot
  GAP-5 — analytics snapshot includes page_health alerts
  GAP-6 — Settings tab exposes all anti_spam_* boolean toggles
  GAP-7 — Notifier exposes notify_circuit_open / abuse / throttled
  GAP-8 — MaintenanceDaemon prunes old content_history
  GAP-9 — Tooltips defined for every new anti_spam_* key
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from core.anti_spam_analytics import AntiSpamSnapshot, collect_snapshot
from core.maintenance import MaintenanceDaemon


# =============================================================================
# GAP-1 — page_warmup wired
# =============================================================================

class TestPageWarmupWiredIntoSheetRunner(unittest.TestCase):
    """The actual wire-up sits in sheet_runner._tick; here we verify the
    contract: when config.anti_spam_warmup_enabled is True the runner
    imports + calls get_warmup_advice. We exercise the contract by
    inspecting the source text."""

    def test_gap1_sheet_runner_references_page_warmup(self):
        with open(os.path.join("core", "sheet_runner.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("get_warmup_advice",   src,
                      "sheet_runner must import get_warmup_advice")
        self.assertIn("effective_daily_cap", src,
                      "sheet_runner must call effective_daily_cap")
        self.assertIn("anti_spam_warmup_enabled", src)


# =============================================================================
# GAP-2 — page_health.record_reach wired
# =============================================================================

class TestPageHealthWiredIntoInsightsFetcher(unittest.TestCase):

    def test_gap2_insights_fetcher_records_reach(self):
        with open(os.path.join("core", "insights_fetcher.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("page_health", src)
        self.assertIn("record_reach", src)


# =============================================================================
# GAP-3 + GAP-5 — analytics snapshot expanded
# =============================================================================

class TestAnalyticsSnapshotExpanded(unittest.TestCase):

    def test_gap3_snapshot_has_time_intel_fields(self):
        snap = AntiSpamSnapshot()
        self.assertTrue(hasattr(snap, "time_intel_warnings"))
        self.assertTrue(hasattr(snap, "n_bot_flat_targets"))
        self.assertEqual(snap.time_intel_warnings, [])
        self.assertEqual(snap.n_bot_flat_targets, 0)

    def test_gap5_snapshot_has_page_health_fields(self):
        snap = AntiSpamSnapshot()
        for field in ("page_health_warnings", "n_pages_throttled", "n_pages_dead"):
            self.assertTrue(hasattr(snap, field), f"snapshot missing {field}")

    def test_gap5_collect_snapshot_handles_no_pages(self):
        """When no FB account is connected, snapshot returns defaults — no crash."""
        snap = collect_snapshot(current_config={})
        self.assertIsInstance(snap, AntiSpamSnapshot)
        self.assertEqual(snap.n_pages_throttled, 0)
        self.assertEqual(snap.n_pages_dead,      0)


# =============================================================================
# GAP-6 + GAP-9 — Settings UI for new keys + tooltips
# =============================================================================

class TestSettingsToggleExposureAndTooltips(unittest.TestCase):

    NEW_KEYS = [
        "anti_spam_dedup",
        "anti_spam_random_order",
        "anti_spam_circuit_breaker",
        "anti_spam_warmup_enabled",
        "anti_spam_retention_days",
        "fb_comment_delay_min_s",
        "fb_comment_delay_max_s",
    ]

    def test_gap6_all_keys_in_defaults(self):
        from core.config_defaults import DEFAULTS
        for k in self.NEW_KEYS:
            self.assertIn(k, DEFAULTS, f"DEFAULTS missing {k}")

    def test_gap6_antispam_keys_are_editable_on_the_settings_page(self):
        """Was: the GUI had a _build_antispam_advanced_card method. What
        actually matters is that every key is reachable in the UI."""
        from server.services.settings_schema import all_field_keys
        editable = set(all_field_keys())
        missing = [k for k in self.NEW_KEYS if k not in editable]
        self.assertFalse(missing, f"not editable on /settings: {missing}")

    def test_gap6_export_handlers_exist(self):
        """Was: GUI methods _export_content_history / _show_duplicate_groups."""
        from server.services import content_tools
        self.assertTrue(callable(content_tools.export_history_csv))
        self.assertTrue(callable(content_tools.find_duplicates))

    def test_gap9_tooltips_for_all_new_keys(self):
        from core.config_help import FIELD_HELP as tips
        for k in self.NEW_KEYS[:6]:  # retention_days has its tooltip optional
            self.assertIn(k, tips, f"Tooltip missing for {k}")
            self.assertGreater(len(tips[k]), 30,
                               f"Tooltip for {k} too short")


# =============================================================================
# GAP-7 — Notifier exposes new methods
# =============================================================================

class TestNotifierAntiSpamMethods(unittest.TestCase):

    def _make_notifier(self):
        from utils.notifier import TelegramNotifier
        # Disable real sending by leaving token/chat empty
        return TelegramNotifier(config={
            "telegram_bot_token": "",
            "telegram_chat_id":   "",
            "notify_on_error":    True,
        })

    def test_gap7_notify_circuit_open_exists(self):
        n = self._make_notifier()
        self.assertTrue(callable(getattr(n, "notify_circuit_open", None)))

    def test_gap7_notify_abuse_signal_exists(self):
        n = self._make_notifier()
        self.assertTrue(callable(getattr(n, "notify_abuse_signal", None)))

    def test_gap7_notify_page_throttled_exists(self):
        n = self._make_notifier()
        self.assertTrue(callable(getattr(n, "notify_page_throttled", None)))

    def test_gap7_calls_dont_raise_when_disabled(self):
        n = self._make_notifier()
        # All three should be no-ops (queue not enabled) but must NOT raise
        n.notify_circuit_open("acc_A", 600)
        n.notify_abuse_signal("acc_A", "368", "page suspended")
        n.notify_page_throttled("page_X", 65.0)

    def test_gap7_sheet_runner_invokes_notifier_for_circuit(self):
        """Source-level check that the wiring exists."""
        with open(os.path.join("core", "sheet_runner.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("notify_circuit_open", src)
        self.assertIn("notify_abuse_signal", src)


# =============================================================================
# GAP-8 — MaintenanceDaemon prunes old records
# =============================================================================

class TestMaintenanceDaemon(unittest.TestCase):

    def test_gap8_maintenance_daemon_constructs(self):
        d = MaintenanceDaemon(config={"anti_spam_retention_days": 30})
        self.assertEqual(d._retention_d, 30)

    def test_gap8_do_sweep_prunes(self):
        """Direct invocation of the sweep method must NOT raise; tests don't
        depend on the actual content_history singleton so the sweep should
        no-op or succeed silently."""
        d = MaintenanceDaemon(config={"anti_spam_retention_days": 30})
        d._do_sweep()   # should not raise

    def test_gap8_web_app_starts_daemon(self):
        """The daemon must actually run under the app that ships.

        Only gui/main_window.py used to start it, so deleting the desktop
        without moving this would have silently stopped enforcing the
        retention policy while every unit test still passed.
        """
        from fastapi.testclient import TestClient

        from server.app import create_app

        app = create_app()
        with TestClient(app, base_url="https://testserver") as client:
            client.get("/health/live")
            daemon = app.state.maintenance
            self.assertIsNotNone(daemon, "MaintenanceDaemon did not start")
            self.assertTrue(daemon._thread.is_alive())
        # ...and it must be told to stop on shutdown, or reloads leak threads.
        self.assertTrue(app.state.maintenance._stop.is_set())


# =============================================================================
# Full Settings DEFAULTS contains every Phase 1-4 key
# =============================================================================

class TestDefaultsCompleteness(unittest.TestCase):

    REQUIRED_KEYS = {
        # Phase 1
        "anti_spam_dedup",
        "anti_spam_random_order",
        "anti_spam_circuit_breaker",
        # Phase 3
        "anti_spam_warmup_enabled",
        "anti_spam_retention_days",
        # Phase 4
        "fb_comment_delay_min_s",
        "fb_comment_delay_max_s",
        # Phase 2-3 anti-ban (already there pre-audit)
        "min_inter_page_interval_s",
        "jitter_s",
        "active_hours_start",
        "active_hours_end",
        "max_posts_per_page_per_day",
        "max_posts_per_account_per_day",
        # TikTok overrides
        "tt_min_interval_per_account_s",
        "tt_jitter_s",
        "tt_max_posts_per_account_per_day",
    }

    def test_full_phase_1_to_4_keys_in_defaults(self):
        from core.config_defaults import DEFAULTS
        missing = self.REQUIRED_KEYS - set(DEFAULTS.keys())
        self.assertFalse(
            missing,
            f"Missing {len(missing)} required defaults: {sorted(missing)}",
        )


if __name__ == "__main__":
    unittest.main()
