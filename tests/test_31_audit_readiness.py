"""
TT-AUDIT Sprint 1-3 wiring + behavior tests.

Verifies tất cả các fix audit của TikTok có wire đúng + activate đúng path:
  - OAuth button label "Continue with TikTok" + logo path
  - Pre-OAuth disclosure modal có function entry point
  - Publish dialog có privacy dropdown, interaction toggles, AI/Branded
  - creator_info helper hoạt động đúng (CreatorInfo dataclass + safe defaults)
  - audit_checklist: URL HEAD check + privacy policy content check + branding check
  - main_window: 9 tab + audit_tab wired
"""
from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# =============================================================================
# A — OAuth button + disclosure modal
# =============================================================================

class TestOAuthBranding(unittest.TestCase):
    """TikTok branding + disclosure requirements, now enforced in the web app
    (was gui/tiktok_account_tab.py + gui/tiktok_oauth_disclosure.py)."""

    def setUp(self):
        self.src = _read(os.path.join("server", "templates", "accounts.html"))

    def test_a1_uses_continue_with_tiktok_text(self):
        """TT-AUDIT requires the English text "Continue with TikTok"."""
        self.assertIn("Continue with TikTok", self.src)

    def test_a2_logo_asset_is_checked_by_the_audit_checklist(self):
        """The official-logo requirement is reported by run_checklist, so a
        missing logo surfaces on /audit instead of failing silently."""
        src = _read(os.path.join("core", "tiktok", "audit_checklist.py"))
        self.assertIn("tiktok_logo.png", src)

    def test_a3_disclosure_is_on_the_only_path_to_oauth(self):
        """Consent must be recorded before any redirect to TikTok: the start
        route is POST-only and refuses without consent=yes."""
        src = _read(os.path.join("server", "routes", "oauth.py"))
        self.assertIn('@router.get("/oauth/tiktok/disclosure"', src)
        self.assertIn('@router.post("/oauth/tiktok/start"', src)
        self.assertIn('if consent != "yes":', src)
        self.assertNotIn('@router.get("/oauth/tiktok/start"', src)


class TestOAuthDisclosureModule(unittest.TestCase):

    def test_b1_scope_catalog_covers_the_core_scopes(self):
        from server.services.audit_service import SCOPE_EXPLAIN
        self.assertIn("user.info.basic", SCOPE_EXPLAIN)
        self.assertIn("video.upload", SCOPE_EXPLAIN)
        self.assertIn("video.publish", SCOPE_EXPLAIN)

    def test_b2_each_scope_has_reason(self):
        """TikTok requires a clear justification per scope."""
        from server.services.audit_service import SCOPE_EXPLAIN
        for scope, reason in SCOPE_EXPLAIN.items():
            self.assertGreater(len(reason), 20,
                               f"Scope {scope} co reason qua ngan: {reason!r}")

    def test_b3_every_requested_scope_is_disclosed(self):
        """A scope requested but not explained is an audit failure."""
        from server.services.audit_service import SCOPE_EXPLAIN, SCOPE_UNKNOWN
        from server.services.oauth_service import tiktok_scopes
        requested = tiktok_scopes(
            {"tiktok_scopes": "user.info.basic,video.upload,video.publish"})
        for scope in requested:
            self.assertNotEqual(SCOPE_EXPLAIN.get(scope, SCOPE_UNKNOWN),
                                SCOPE_UNKNOWN, f"{scope} chua co mo ta")


# =============================================================================
# C — creator_info helper
# =============================================================================

class TestCreatorInfo(unittest.TestCase):

    def test_c1_dataclass_defaults_safe(self):
        from core.tiktok.creator_info import CreatorInfo
        info = CreatorInfo()
        # Default state: không có public option
        self.assertEqual(info.privacy_level_options, [])
        # Safe default privacy → fallback SELF_ONLY
        self.assertEqual(info.safe_default_privacy(), "SELF_ONLY")

    def test_c2_has_public_option_only_when_listed(self):
        from core.tiktok.creator_info import CreatorInfo
        only_self = CreatorInfo(privacy_level_options=["SELF_ONLY"])
        self.assertFalse(only_self.has_public_option)

        full = CreatorInfo(privacy_level_options=["SELF_ONLY", "PUBLIC_TO_EVERYONE"])
        self.assertTrue(full.has_public_option)

    def test_c3_label_translation(self):
        """i18n: label_for_privacy returns localized label per current language."""
        from core.i18n import init as i18n_init, set_language
        from core.tiktok.creator_info import label_for_privacy, PRIVACY_LABELS_VI

        # Load translations before testing
        i18n_init({"app_language": "en"})

        self.assertIn("SELF_ONLY", PRIVACY_LABELS_VI)

        # Test English default
        set_language("en")
        self.assertIn("Only me", label_for_privacy("SELF_ONLY"))

        # Switch to Vietnamese
        set_language("vi")
        self.assertIn("Chỉ mình tôi", label_for_privacy("SELF_ONLY"))

        # Unknown enum → fallback raw enum (regardless of language)
        set_language("en")
        self.assertEqual(label_for_privacy("UNKNOWN"), "UNKNOWN")

    def test_c4_query_creator_info_parses_response(self):
        """Mock TikTokClient.post → CreatorInfo parsed đúng."""
        from core.tiktok import creator_info as mod
        fake_resp = {
            "creator_username":             "klcloset96",
            "creator_nickname":             "KL Closet",
            "creator_avatar_url":           "https://example.com/avatar.jpg",
            "privacy_level_options":        ["SELF_ONLY", "PUBLIC_TO_EVERYONE"],
            "comment_disabled":             False,
            "duet_disabled":                True,
            "stitch_disabled":              False,
            "max_video_post_duration_sec":  300,
        }
        with patch.object(mod, "TikTokClient") as MockClient:
            inst = MockClient.return_value
            inst.post.return_value = fake_resp
            info = mod.query_creator_info("fake_token")
        self.assertEqual(info.creator_username, "klcloset96")
        self.assertTrue(info.has_public_option)
        self.assertTrue(info.duet_disabled)
        self.assertEqual(info.max_video_post_duration_sec, 300)

    def test_c5_empty_privacy_falls_back_self_only(self):
        """API trả về privacy_level_options=[] → fallback SELF_ONLY (audit-safe)."""
        from core.tiktok import creator_info as mod
        with patch.object(mod, "TikTokClient") as MockClient:
            inst = MockClient.return_value
            inst.post.return_value = {"privacy_level_options": []}
            info = mod.query_creator_info("fake_token")
        self.assertEqual(info.privacy_level_options, ["SELF_ONLY"])


# =============================================================================
# D — Publish dialog: code-level checks
# =============================================================================

class TestPublishDialogStructure(unittest.TestCase):
    """The publish-confirm step is a web page now
    (server/templates/manual_tiktok.html + server/routes/manual.py) rather than
    a Tk dialog. Every audit requirement it carried still has to hold.
    """

    def setUp(self):
        self.src = _read(os.path.join("server", "templates", "manual_tiktok.html"))
        self.route = _read(os.path.join("server", "routes", "manual.py"))

    def test_d1_confirm_step_uses_creator_info(self):
        self.assertIn("from core.tiktok.creator_info import query_creator_info",
                      self.route)

    def test_d2_privacy_is_a_dropdown_the_user_picks(self):
        """Audit requires privacy to be user-selectable, with options coming
        from creator_info rather than a fixed list."""
        self.assertIn('<select name="privacy_level"', self.src)
        self.assertIn("pending.privacy_options", self.src)

    def test_d3_interaction_toggles_present(self):
        """Allow Comment / Duet / Stitch — 3 toggles required by TT policy."""
        for name in ("allow_comment", "allow_duet", "allow_stitch"):
            self.assertIn(f'name="{name}"', self.src,
                          f"Missing interaction toggle: {name}")

    def test_d4_ai_and_branded_user_controlled(self):
        """AI + Branded must be user-toggleable, not display-only, and must
        reach the task."""
        self.assertIn('name="is_ai"', self.src)
        self.assertIn('name="branded"', self.src)
        self.assertIn("is_ai_generated", self.route)
        self.assertIn("brand_content_toggle", self.route)

    def test_d5_creator_disabled_toggles_locked(self):
        """If the creator disabled comment/duet/stitch, the app must not be
        able to override it — the checkbox is disabled in the form AND the
        server ignores the submitted value."""
        for flag in ("comment_disabled", "duet_disabled", "stitch_disabled"):
            self.assertIn(f"pending.info.{flag}", self.src,
                          f"Toggle not locked in the form for {flag}")
            self.assertIn(flag, self.route,
                          f"Server does not re-check {flag}")

    def test_d6_consent_timestamp_utc(self):
        """user_confirmed_at is stored as a UTC ISO timestamp."""
        self.assertIn("user_confirmed_at", self.route)
        self.assertIn("timezone.utc", self.route)


class TestOperationTabCallsCreatorInfo(unittest.TestCase):

    def test_e1_publish_queries_creator_info_before_confirming(self):
        src = _read(os.path.join("server", "routes", "manual.py"))
        self.assertIn("query_creator_info(", src)


# =============================================================================
# F — audit_checklist enhancements
# =============================================================================

class TestAuditChecklistEnhancements(unittest.TestCase):

    def setUp(self):
        from core.tiktok import audit_checklist
        self.mod = audit_checklist

    def test_f1_head_url_helper_exists(self):
        self.assertTrue(callable(self.mod._head_url))

    def test_f2_head_url_handles_success(self):
        """HTTP 200 → reachable=True."""
        with patch.object(self.mod, "requests") as mock_req:
            mock_resp = MagicMock(status_code=200)
            mock_req.head.return_value = mock_resp
            ok, msg = self.mod._head_url("https://example.com")
            self.assertTrue(ok)
            self.assertIn("200", msg)

    def test_f3_head_url_handles_404(self):
        with patch.object(self.mod, "requests") as mock_req:
            mock_resp = MagicMock(status_code=404)
            mock_req.head.return_value = mock_resp
            ok, msg = self.mod._head_url("https://example.com/missing")
            self.assertFalse(ok)
            self.assertIn("404", msg)

    def test_f4_head_url_fallback_to_get_on_405(self):
        """Vài CDN reject HEAD → must fall back to GET stream."""
        with patch.object(self.mod, "requests") as mock_req:
            mock_head = MagicMock(status_code=405)
            mock_get  = MagicMock(status_code=200)
            mock_req.head.return_value = mock_head
            mock_req.get.return_value  = mock_get
            ok, _ = self.mod._head_url("https://cdn.example.com/x")
            self.assertTrue(ok)
            self.assertTrue(mock_req.get.called)

    def test_f5_check_privacy_terms_urls_does_head(self):
        """Reachability check phải thực thi qua _head_url."""
        config = {
            "app_privacy_policy_url": "https://example.com/privacy",
            "app_terms_url":          "https://example.com/terms",
        }
        with patch.object(self.mod, "_head_url", return_value=(True, "HTTP 200")) as mock_head:
            item = self.mod.check_privacy_terms_urls(config)
            self.assertEqual(item.result, self.mod.CheckResult.PASS)
            # Cả 2 URL đều được check
            self.assertEqual(mock_head.call_count, 2)

    def test_f6_check_privacy_terms_urls_fails_on_404(self):
        config = {
            "app_privacy_policy_url": "https://example.com/privacy",
            "app_terms_url":          "https://example.com/terms",
        }
        with patch.object(self.mod, "_head_url", return_value=(False, "HTTP 404")):
            item = self.mod.check_privacy_terms_urls(config)
            self.assertEqual(item.result, self.mod.CheckResult.FAIL)

    def test_f7_check_login_button_branding_warns_when_missing(self):
        """Logo file thiếu → WARN (graceful, không FAIL)."""
        # Backup nếu file tồn tại
        path = os.path.join("data", "assets", "tiktok_logo.png")
        existed = os.path.exists(path)
        try:
            if existed:
                os.rename(path, path + ".bak")
            item = self.mod.check_login_button_branding({})
            self.assertEqual(item.result, self.mod.CheckResult.WARN)
        finally:
            if existed:
                os.rename(path + ".bak", path)

    def test_f8_check_privacy_mentions_tiktok_exists(self):
        self.assertTrue(callable(self.mod.check_privacy_policy_mentions_tiktok))

    def test_f9_check_privacy_mentions_tiktok_fails_on_missing_keyword(self):
        config = {"app_privacy_policy_url": "https://example.com/privacy"}
        fake_resp = MagicMock(status_code=200, text="generic privacy policy without keywords")
        with patch.object(self.mod, "requests") as mock_req:
            mock_req.get.return_value = fake_resp
            item = self.mod.check_privacy_policy_mentions_tiktok(config)
            self.assertEqual(item.result, self.mod.CheckResult.FAIL)

    def test_f10_run_checklist_includes_new_checks(self):
        """All check functions are registered in _ALL_CHECKS."""
        names = {c.__name__ for c in self.mod._ALL_CHECKS}
        self.assertIn("check_privacy_policy_mentions_tiktok", names)
        self.assertIn("check_login_button_branding", names)


# =============================================================================
# G — main_window: 9-tab wiring + AuditTab
# =============================================================================

class TestMainWindowAuditWiring(unittest.TestCase):
    """The audit screen must be reachable from the navigation, not merely exist."""

    def test_g1_audit_page_is_routed_and_built(self):
        from server.routes import monitor as monitor_routes
        from server.templating import BUILT_PAGES
        paths = {r.path for r in monitor_routes.router.routes}
        self.assertIn("/audit", paths)
        self.assertTrue(BUILT_PAGES.get("audit"))

    def test_g2_navigation_links_every_page(self):
        """Moi trang phai vao duoc tu dieu huong.

        Truoc day sidebar viet cung nen test grep base.html. Gio sidebar sinh
        tu apps/*/manifest.py, nen kiem tra o dung nguon: moi app dang bat phai
        khai it nhat mot muc nav, va base.html phai render tu nav_apps().

        Khop "nav_apps(" (khong phai "nav_apps()"): bat bien la sidebar sinh tu
        registry, khong phai so tham so cua ham. H1.4 them tham so `request` de
        loc app theo quyen (nav_apps(request)) — mot thay doi hop le lam
        assertion khoa cung "()" hong ma bat bien van dung.
        """
        from platform_core.registry import discover

        # UX Pha 2: dieu huong chuyen tu sidebar (base.html) sang HEADER ngang
        # (_header.html), sinh tu registry qua nav_groups(); base.html include
        # _header.html. Bat bien VAN la: nav sinh tu registry, khong hardcode.
        base_src = _read(os.path.join("server", "templates", "base.html"))
        self.assertIn("_header.html", base_src,
                      "base.html khong con include header dieu huong")
        header_src = _read(os.path.join("server", "templates", "_header.html"))
        self.assertIn("nav_groups(", header_src,
                      "_header.html khong con sinh nav tu registry")

        for item in discover():
            if not item.manifest.enabled or item.error:
                continue
            entries = item.manifest.nav_entries()
            self.assertTrue(entries,
                            f"{item.slug} khong co muc nav nao -> khong vao duoc")
            for e in entries:
                self.assertTrue(e.path.startswith("/"),
                                f"{item.slug}: nav path phai tuyet doi: {e.path}")


# =============================================================================
# H — Daily quota default
# =============================================================================

class TestDailyQuotaDefault(unittest.TestCase):

    def test_h1_settings_default_is_30(self):
        from core.config_defaults import DEFAULTS
        self.assertEqual(DEFAULTS.get("tt_max_posts_per_account_per_day"), 30)


if __name__ == "__main__":
    unittest.main()
