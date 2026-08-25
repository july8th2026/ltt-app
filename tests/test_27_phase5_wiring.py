"""
Phase 5 wiring audit — verifies that the 5 modules created in Sprint A/B/C/D
are actually called from production code paths.

Without these tests it's easy to ship a module that's tested in isolation
but never invoked by the runtime — exactly the audit gap that prompted
this iteration.
"""
from __future__ import annotations

import os
import unittest


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# =============================================================================
# Round 1.1 — session_lock wired into sheet_runner
# =============================================================================

class TestSessionLockWired(unittest.TestCase):

    def test_sheet_runner_imports_session_lock(self):
        src = _read(os.path.join("core", "sheet_runner.py"))
        self.assertIn("SessionLock", src)
        self.assertIn("anti_spam_session_lock_enabled", src)

    def test_sheet_runner_acquires_and_releases(self):
        src = _read(os.path.join("core", "sheet_runner.py"))
        self.assertIn("_session_lock_obj.acquire()", src)
        self.assertIn("_session_lock_obj.release()", src)

    def test_session_lock_skips_on_conflict(self):
        """Source check: SessionLockError → mark_skipped."""
        src = _read(os.path.join("core", "sheet_runner.py"))
        self.assertIn("SessionLockError", src)
        self.assertIn("Locked by other bot instance", src)


# =============================================================================
# Round 1.2 — app_status wired into MaintenanceDaemon
# =============================================================================

class TestAppStatusWired(unittest.TestCase):

    def test_maintenance_calls_check_app_status(self):
        src = _read(os.path.join("core", "maintenance.py"))
        self.assertIn("check_app_status", src)
        self.assertIn("is_app_disabled", src)
        self.assertIn("anti_spam_app_status_check", src)

    def test_maintenance_alerts_when_disabled(self):
        src = _read(os.path.join("core", "maintenance.py"))
        self.assertIn("notify_abuse_signal", src)


# =============================================================================
# Round 1.3 — content_calendar wired into Settings UI
# =============================================================================

class TestContentCalendarWired(unittest.TestCase):

    def test_settings_has_import_handler(self):
        from server.services import content_tools
        self.assertTrue(callable(content_tools.import_calendar_csv))

    def test_settings_uses_the_shared_csv_parser(self):
        """The route must not grow its own CSV parsing — core.content_calendar
        is the tested implementation."""
        import inspect

        from server.services import content_tools
        src = inspect.getsource(content_tools)
        self.assertIn("from core.content_calendar import import_csv", src)


# =============================================================================
# Round 1.4 — network_identity wired into GraphClient
# =============================================================================

class TestNetworkIdentityWired(unittest.TestCase):

    def test_graph_client_accepts_account_id_and_config(self):
        import inspect
        from core.graph_client import GraphClient
        sig = inspect.signature(GraphClient.__init__)
        self.assertIn("account_id", sig.parameters)
        self.assertIn("config",     sig.parameters)

    def test_graph_uploader_passes_account_id(self):
        src = _read(os.path.join("core", "graph_uploader.py"))
        self.assertIn("account_id=str(getattr(account, \"fb_user_id\"", src)
        self.assertIn("config=config", src)

    def test_reels_uploader_passes_account_id(self):
        src = _read(os.path.join("core", "reels_uploader.py"))
        self.assertIn("account_id=str(getattr(account, \"fb_user_id\"", src)

    def test_graph_client_request_uses_identity_headers(self):
        src = _read(os.path.join("core", "graph_client.py"))
        self.assertIn("_request_headers", src)
        self.assertIn("_request_kwargs",  src)
        self.assertIn("_identity_ua",     src)
        self.assertIn("_identity_proxy",  src)


# =============================================================================
# Round 1.5 — multi_app wired into AuthManager
# =============================================================================

class TestMultiAppWired(unittest.TestCase):

    def test_auth_manager_builds_pool_from_config(self):
        src = _read(os.path.join("core", "auth_manager.py"))
        self.assertIn("MetaAppPool.from_config", src)
        self.assertIn("next_healthy",            src)

    def test_legacy_config_still_works(self):
        """When meta_app_pool is empty, AuthManager must fall back to
        legacy meta_app_id / meta_app_secret — verifies back-compat."""
        from core.auth_manager import AuthManager
        am = AuthManager(config={
            "meta_app_id":     "legacy_123",
            "meta_app_secret": "legacy_secret",
        })
        self.assertEqual(am.app_id,     "legacy_123")
        self.assertEqual(am.app_secret, "legacy_secret")

    def test_pool_config_selects_first_healthy(self):
        from core.auth_manager import AuthManager
        am = AuthManager(config={
            "meta_app_pool": [
                {"app_id": "POOL_X", "app_secret": "sx", "redirect_uri": "https://x"},
                {"app_id": "POOL_Y", "app_secret": "sy"},
            ],
        })
        # First healthy is round-robined; X is first
        self.assertEqual(am.app_id,       "POOL_X")
        self.assertEqual(am.redirect_uri, "https://x")


# =============================================================================
# DEFAULTS completeness check
# =============================================================================

class TestDefaultsHaveAllPhase5Keys(unittest.TestCase):

    REQUIRED = {
        # Sprint A
        "caption_rotator_enabled",
        "caption_rotator_templates",
        "caption_rotator_pools",
        "caption_rotator_keep_original",
        "anti_spam_video_variation_mode",
        "anti_spam_cross_target_warn_threshold",
        # Sprint B+C runtime
        "anti_spam_session_lock_enabled",
        "anti_spam_app_status_check",
        "meta_app_pool",
        "network_identity_enabled",
        "network_user_agents",
        "network_proxies",
    }

    def test_all_keys_present(self):
        from core.config_defaults import DEFAULTS
        missing = self.REQUIRED - set(DEFAULTS.keys())
        self.assertFalse(missing, f"Missing defaults: {sorted(missing)}")

    def test_all_keys_have_tooltips(self):
        """The toggles + threshold keys should have tooltips. Pool/list
        keys are exempt (they're rarely edited via the tab)."""
        from core.config_help import FIELD_HELP as tips
        # Keys that SHOULD have tooltips (user-facing toggles)
        expected_tooltipped = {
            "caption_rotator_enabled",
            "anti_spam_video_variation_mode",
            "anti_spam_cross_target_warn_threshold",
            "anti_spam_session_lock_enabled",
            "anti_spam_app_status_check",
            "meta_app_pool",
            "network_identity_enabled",
            "network_user_agents",
            "network_proxies",
        }
        missing = expected_tooltipped - set(tips.keys())
        self.assertFalse(missing, f"Tooltips missing for: {sorted(missing)}")


# =============================================================================
# Round 2 — Dashboard surfaces Phase 5 signals
# =============================================================================

class TestDashboardSurfacesPhase5(unittest.TestCase):

    def test_snapshot_has_app_status_fields(self):
        from core.anti_spam_analytics import AntiSpamSnapshot
        snap = AntiSpamSnapshot()
        self.assertTrue(hasattr(snap, "meta_app_status"))
        self.assertTrue(hasattr(snap, "meta_app_pool_healthy"))
        self.assertTrue(hasattr(snap, "meta_app_pool_total"))

    def test_snapshot_collects_pool_health(self):
        from core.anti_spam_analytics import collect_snapshot
        config = {"meta_app_pool": [
            {"app_id": "A", "app_secret": "sa"},
            {"app_id": "B", "app_secret": "sb"},
        ]}
        snap = collect_snapshot(config)
        self.assertEqual(snap.meta_app_pool_total, 2)
        self.assertEqual(snap.meta_app_pool_healthy, 2)

    def test_format_oneline_shows_disabled_app(self):
        from core.anti_spam_analytics import AntiSpamSnapshot, format_oneline
        snap = AntiSpamSnapshot()
        snap.meta_app_status = "disabled"
        line = format_oneline(snap)
        self.assertIn("Meta App", line)
        self.assertIn("DISABLED", line.upper())

    def test_format_oneline_shows_empty_pool(self):
        from core.anti_spam_analytics import AntiSpamSnapshot, format_oneline
        snap = AntiSpamSnapshot()
        snap.meta_app_pool_total   = 3
        snap.meta_app_pool_healthy = 0
        line = format_oneline(snap)
        self.assertIn("0 healthy", line)


# =============================================================================
# Round 2 — Phase 5 UI toggles wired into card
# =============================================================================

class TestPhase5TogglesInUI(unittest.TestCase):

    def test_phase5_toggle_keys_rendered(self):
        """Every Phase 5 toggle must be editable on the Settings page.

        Was a source-level grep of the desktop settings card; the web renders
        from a schema, so this asks the schema directly.
        """
        from server.services.settings_schema import all_field_keys
        editable = set(all_field_keys())
        for key in [
            "caption_rotator_enabled",
            "anti_spam_video_variation_mode",
            "anti_spam_cross_target_warn_threshold",
            "anti_spam_session_lock_enabled",
            "anti_spam_app_status_check",
            "network_identity_enabled",
        ]:
            self.assertIn(key, editable, f"{key} not editable on /settings")


if __name__ == "__main__":
    unittest.main()
