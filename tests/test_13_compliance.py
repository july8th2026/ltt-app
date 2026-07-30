"""
test_13_compliance.py — Unit tests for TikTokComplianceGuard.

Coverage:
  C1:  TikTokComplianceError — str format, is_permanent default, fields
  C2:  ComplianceWarning — fields
  C3:  _check_account() — None account raises ERR_NO_ACCOUNT
  C4:  _check_token() — expired+no-refresh raises ERR_TOKEN_EXPIRED_NO_REFRESH
  C5:  _check_token() — expired+refresh-valid → no error (refresh upstream)
  C6:  _check_scopes() — missing video.upload raises ERR_INSUFFICIENT_SCOPE
  C7:  _check_scopes() — direct post missing video.publish raises ERR_INSUFFICIENT_SCOPE
  C8:  _check_video() — empty path raises ERR_NO_VIDEO_PATH
  C9:  _check_video() — nonexistent file raises ERR_VIDEO_NOT_FOUND
  C10: _check_video() — zero-byte file raises ERR_VIDEO_EMPTY
  C11: _check_video() — >4 GB file raises ERR_VIDEO_TOO_LARGE
  C12: _check_caption() — caption >2200 chars raises ERR_CAPTION_TOO_LONG
  C13: _check_caption() — title >150 chars raises ERR_TITLE_TOO_LONG
  C14: _check_caption() — no caption AND no title → WARN_NO_CAPTION warning
  C15: _check_privacy() — unknown value raises ERR_INVALID_PRIVACY
  C16: _check_privacy() — all supported aliases resolve correctly
  C17: _check_audit_gate() — direct_post_disabled → ERR_DIRECT_POST_DISABLED
  C18: _check_audit_gate() — public direct without audit → ERR_AUDIT_NOT_APPROVED
  C19: _check_audit_gate() — draft post always passes regardless of privacy
  C20: _check_audit_gate() — direct+SELF_ONLY passes without audit
  C21: _check_audit_gate() — direct+public+audit_approved=true passes
  C22: _check_publish_mode() — mode mismatch → WARN_MODE_MISMATCH
  C23: _check_user_confirmation() — missing confirmed_at → WARN_NO_USER_CONFIRMATION
  C24: _check_ai_disclosure() — is_ai_generated=true → WARN_AI_CONTENT_FLAGGED
  C25: check() — fully valid task returns empty warning list
  C26: check() — multiple non-blocking warnings accumulate correctly
  C27: SheetRunner._is_retryable_error() — compliance codes [ERR_*] are not retried
  C28: TikTokComplianceError is_permanent=False is retryable via _is_retryable_error logic
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_account(
    scopes=None,
    expires_in=3600,
    refresh_in=86400 * 365,
) -> "TikTokAccount":
    from core.tiktok.token_store import TikTokAccount
    now = time.time()
    return TikTokAccount(
        open_id            = "u_test",
        display_name       = "Test User",
        avatar_url         = "",
        access_token       = "tok_test",
        refresh_token      = "ref_test",
        expires_at         = now + expires_in,
        refresh_expires_at = now + refresh_in,
        scopes             = scopes if scopes is not None else ["video.upload"],
        connected_at       = "2026-01-01T00:00:00",
    )


def _make_guard(config: dict = None) -> "TikTokComplianceGuard":
    from core.tiktok.compliance_guard import TikTokComplianceGuard
    return TikTokComplianceGuard(config or {})


def _draft_config() -> dict:
    """Config that allows only draft uploads (safe/unaudited defaults).

    Sprint TT-5 toggles are opted-OUT here so the legacy test surface stays
    stable. Production DEFAULTS turn them on; tests asserting empty-warning
    happy paths should not be perturbed by added soft checks.
    """
    return {
        "tiktok_publish_mode":        "draft_upload",
        "tiktok_audit_approved":      "false",
        "tiktok_enable_direct_post":  "false",
        "tiktok_require_user_confirm": "false",
        "tiktok_privacy_level":       "SELF_ONLY",
        # Disable F1-F6 in this legacy-tests config; they have dedicated tests
        # in test_29_tiktok_preflight.py.
        "anti_spam_video_validate":       False,
        "anti_spam_scope_verify":         False,
        "anti_spam_watermark_check":      False,
        "anti_spam_audio_rights_check":   False,
        "anti_spam_content_policy":       False,
    }


def _direct_config(audit_approved=False) -> dict:
    """Config for direct posting (enable_direct_post=true)."""
    return {
        "tiktok_publish_mode":        "direct_private",
        "tiktok_audit_approved":      "true" if audit_approved else "false",
        "tiktok_enable_direct_post":  "true",
        "tiktok_require_user_confirm": "false",
        "tiktok_privacy_level":       "SELF_ONLY",
    }


def _make_video(size: int = 1024) -> str:
    """Create a temp video file and return its path."""
    f = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    f.write(b"Z" * size)
    f.close()
    return f.name


# ─────────────────────────────────────────────────────────────────────────────
# C1 — TikTokComplianceError
# ─────────────────────────────────────────────────────────────────────────────

class TestComplianceErrorType(unittest.TestCase):

    def test_str_format_contains_error_code(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        err = TikTokComplianceError("ERR_FOO", "something went wrong")
        self.assertEqual(str(err), "[ERR_FOO] something went wrong")

    def test_is_permanent_defaults_true(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        err = TikTokComplianceError("ERR_X", "msg")
        self.assertTrue(err.is_permanent)

    def test_is_permanent_can_be_false(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        err = TikTokComplianceError("ERR_Y", "msg", is_permanent=False)
        self.assertFalse(err.is_permanent)

    def test_is_exception_subclass(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        err = TikTokComplianceError("ERR_Z", "msg")
        self.assertIsInstance(err, Exception)

    def test_args_contains_message(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        err = TikTokComplianceError("ERR_Q", "human message")
        # Exception.args[0] is the message (set by __post_init__)
        self.assertIn("human message", str(err))


# ─────────────────────────────────────────────────────────────────────────────
# C2 — ComplianceWarning
# ─────────────────────────────────────────────────────────────────────────────

class TestComplianceWarning(unittest.TestCase):

    def test_fields_accessible(self):
        from core.tiktok.compliance_guard import ComplianceWarning
        w = ComplianceWarning(code="WARN_TEST", message="test warning")
        self.assertEqual(w.code, "WARN_TEST")
        self.assertEqual(w.message, "test warning")

    def test_is_not_exception(self):
        from core.tiktok.compliance_guard import ComplianceWarning
        w = ComplianceWarning(code="W", message="m")
        self.assertNotIsInstance(w, Exception)


# ─────────────────────────────────────────────────────────────────────────────
# C3 — _check_account
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckAccount(unittest.TestCase):

    def test_none_account_raises(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        guard = _make_guard()
        with self.assertRaises(TikTokComplianceError) as ctx:
            guard._check_account(None)
        self.assertEqual(ctx.exception.error_code, "ERR_NO_ACCOUNT")
        self.assertTrue(ctx.exception.is_permanent)

    def test_valid_account_passes(self):
        guard  = _make_guard()
        acc    = _make_account()
        # Should not raise
        guard._check_account(acc)


# ─────────────────────────────────────────────────────────────────────────────
# C4 & C5 — _check_token
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckToken(unittest.TestCase):

    def test_expired_no_refresh_raises(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        guard = _make_guard()
        acc   = _make_account(expires_in=-100, refresh_in=-100)   # both expired
        with self.assertRaises(TikTokComplianceError) as ctx:
            guard._check_token(acc)
        self.assertEqual(ctx.exception.error_code, "ERR_TOKEN_EXPIRED_NO_REFRESH")

    def test_expired_but_refresh_valid_does_not_raise(self):
        """Refresh is valid → upstream will refresh; guard should not block."""
        guard = _make_guard()
        acc   = _make_account(expires_in=-100, refresh_in=86400 * 365)
        # Should not raise — publisher will refresh before posting
        guard._check_token(acc)

    def test_fresh_token_passes(self):
        guard = _make_guard()
        acc   = _make_account(expires_in=3600)
        guard._check_token(acc)


# ─────────────────────────────────────────────────────────────────────────────
# C6 & C7 — _check_scopes
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckScopes(unittest.TestCase):

    def test_missing_video_upload_raises(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        guard = _make_guard()
        acc   = _make_account(scopes=[])   # no scopes at all
        warnings: list = []
        with self.assertRaises(TikTokComplianceError) as ctx:
            guard._check_scopes({"post_type": "tiktok_draft"}, acc, warnings)
        self.assertEqual(ctx.exception.error_code, "ERR_INSUFFICIENT_SCOPE")
        self.assertIn("video.upload", ctx.exception.message)

    def test_draft_only_needs_video_upload(self):
        """Draft posts only need video.upload, not video.publish."""
        guard = _make_guard()
        acc   = _make_account(scopes=["video.upload"])
        warnings: list = []
        guard._check_scopes({"post_type": "tiktok_draft"}, acc, warnings)
        # No error — test passes if no exception is raised

    def test_direct_post_needs_video_publish(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        guard = _make_guard()
        acc   = _make_account(scopes=["video.upload"])  # missing video.publish
        warnings: list = []
        with self.assertRaises(TikTokComplianceError) as ctx:
            guard._check_scopes({"post_type": "tiktok_direct"}, acc, warnings)
        self.assertEqual(ctx.exception.error_code, "ERR_INSUFFICIENT_SCOPE")
        self.assertIn("video.publish", ctx.exception.message)

    def test_direct_post_with_both_scopes_passes(self):
        guard = _make_guard()
        acc   = _make_account(scopes=["video.upload", "video.publish"])
        warnings: list = []
        guard._check_scopes({"post_type": "tiktok_direct"}, acc, warnings)


# ─────────────────────────────────────────────────────────────────────────────
# C8–C11 — _check_video
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckVideo(unittest.TestCase):

    def test_empty_path_raises_no_video_path(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        guard = _make_guard()
        with self.assertRaises(TikTokComplianceError) as ctx:
            guard._check_video({"video_path": ""})
        self.assertEqual(ctx.exception.error_code, "ERR_NO_VIDEO_PATH")

    def test_nonexistent_path_raises_video_not_found(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        guard = _make_guard()
        with self.assertRaises(TikTokComplianceError) as ctx:
            guard._check_video({"video_path": "/nonexistent/video.mp4"})
        self.assertEqual(ctx.exception.error_code, "ERR_VIDEO_NOT_FOUND")

    def test_empty_file_raises_video_empty(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        video = _make_video(size=0)
        try:
            guard = _make_guard()
            with self.assertRaises(TikTokComplianceError) as ctx:
                guard._check_video({"video_path": video})
            self.assertEqual(ctx.exception.error_code, "ERR_VIDEO_EMPTY")
        finally:
            os.unlink(video)

    def test_valid_video_passes(self):
        video = _make_video(size=1024)
        try:
            guard = _make_guard()
            guard._check_video({"video_path": video})  # must not raise
        finally:
            os.unlink(video)

    def test_video_too_large_raises(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        video = _make_video(size=1)
        try:
            with patch("os.path.getsize", return_value=4 * 1024 * 1024 * 1024 + 1):
                guard = _make_guard()
                with self.assertRaises(TikTokComplianceError) as ctx:
                    guard._check_video({"video_path": video})
            self.assertEqual(ctx.exception.error_code, "ERR_VIDEO_TOO_LARGE")
        finally:
            os.unlink(video)

    def test_exact_4gb_passes(self):
        """4 GB exactly is still within the limit."""
        video = _make_video(size=1)
        try:
            with patch("os.path.getsize", return_value=4 * 1024 * 1024 * 1024):
                guard = _make_guard()
                guard._check_video({"video_path": video})  # must not raise
        finally:
            os.unlink(video)


# ─────────────────────────────────────────────────────────────────────────────
# C12–C14 — _check_caption
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckCaption(unittest.TestCase):

    def test_caption_too_long_raises(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        guard = _make_guard()
        warnings: list = []
        with self.assertRaises(TikTokComplianceError) as ctx:
            guard._check_caption({"description": "A" * 2201}, warnings)
        self.assertEqual(ctx.exception.error_code, "ERR_CAPTION_TOO_LONG")

    def test_caption_exactly_limit_passes(self):
        guard    = _make_guard()
        warnings: list = []
        guard._check_caption({"description": "B" * 2200, "title": "T"}, warnings)

    def test_title_too_long_raises(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        guard    = _make_guard()
        warnings: list = []
        with self.assertRaises(TikTokComplianceError) as ctx:
            guard._check_caption({"description": "", "title": "T" * 151}, warnings)
        self.assertEqual(ctx.exception.error_code, "ERR_TITLE_TOO_LONG")

    def test_title_exactly_limit_passes(self):
        guard    = _make_guard()
        warnings: list = []
        guard._check_caption({"title": "T" * 150, "description": ""}, warnings)

    def test_no_caption_no_title_yields_warning(self):
        guard    = _make_guard()
        warnings: list = []
        guard._check_caption({"description": "", "title": ""}, warnings)
        codes = [w.code for w in warnings]
        self.assertIn("WARN_NO_CAPTION", codes)

    def test_caption_only_no_warning(self):
        guard    = _make_guard()
        warnings: list = []
        guard._check_caption({"description": "Hello", "title": ""}, warnings)
        self.assertEqual(warnings, [])

    def test_title_only_no_warning(self):
        guard    = _make_guard()
        warnings: list = []
        guard._check_caption({"description": "", "title": "A"}, warnings)
        self.assertEqual(warnings, [])


# ─────────────────────────────────────────────────────────────────────────────
# C15 & C16 — _check_privacy
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckPrivacy(unittest.TestCase):

    def test_invalid_value_raises(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        guard    = _make_guard()
        warnings: list = []
        with self.assertRaises(TikTokComplianceError) as ctx:
            guard._check_privacy({"privacy_level": "EVERYONE"}, warnings)
        self.assertEqual(ctx.exception.error_code, "ERR_INVALID_PRIVACY")

    def test_valid_self_only(self):
        guard    = _make_guard()
        warnings: list = []
        result = guard._check_privacy({"privacy_level": "SELF_ONLY"}, warnings)
        self.assertEqual(result, "SELF_ONLY")

    def test_alias_public_resolves(self):
        guard    = _make_guard()
        warnings: list = []
        result = guard._check_privacy({"privacy_level": "public"}, warnings)
        self.assertEqual(result, "PUBLIC_TO_EVERYONE")

    def test_alias_private_resolves(self):
        guard    = _make_guard()
        warnings: list = []
        result = guard._check_privacy({"privacy_level": "private"}, warnings)
        self.assertEqual(result, "SELF_ONLY")

    def test_alias_followers_resolves(self):
        guard    = _make_guard()
        warnings: list = []
        result = guard._check_privacy({"privacy_level": "followers"}, warnings)
        self.assertEqual(result, "FOLLOWER_OF_CREATOR")

    def test_alias_friends_resolves(self):
        guard    = _make_guard()
        warnings: list = []
        result = guard._check_privacy({"privacy_level": "friends"}, warnings)
        self.assertEqual(result, "MUTUAL_FRIEND_FRIENDS")

    def test_fallback_to_config_when_not_in_task(self):
        """Empty privacy_level in task → reads from config."""
        guard    = _make_guard({"tiktok_privacy_level": "FOLLOWER_OF_CREATOR"})
        warnings: list = []
        result = guard._check_privacy({}, warnings)
        self.assertEqual(result, "FOLLOWER_OF_CREATOR")

    def test_fallback_default_is_self_only(self):
        """No task privacy, no config → defaults to SELF_ONLY."""
        guard    = _make_guard({})
        warnings: list = []
        result = guard._check_privacy({}, warnings)
        self.assertEqual(result, "SELF_ONLY")


# ─────────────────────────────────────────────────────────────────────────────
# C17–C21 — _check_audit_gate
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckAuditGate(unittest.TestCase):

    def test_direct_post_disabled_raises(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        guard = _make_guard(_draft_config())   # enable_direct_post=false
        with self.assertRaises(TikTokComplianceError) as ctx:
            guard._check_audit_gate(
                {"post_type": "tiktok_direct"},
                "SELF_ONLY",
            )
        self.assertEqual(ctx.exception.error_code, "ERR_DIRECT_POST_DISABLED")

    def test_public_direct_without_audit_raises(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        guard = _make_guard(_direct_config(audit_approved=False))
        with self.assertRaises(TikTokComplianceError) as ctx:
            guard._check_audit_gate(
                {"post_type": "tiktok_direct"},
                "PUBLIC_TO_EVERYONE",
            )
        self.assertEqual(ctx.exception.error_code, "ERR_AUDIT_NOT_APPROVED")

    def test_draft_post_always_passes(self):
        """Draft posts must never be blocked by audit gate."""
        for privacy in ("SELF_ONLY", "PUBLIC_TO_EVERYONE", "FOLLOWER_OF_CREATOR"):
            for cfg in (_draft_config(), _direct_config(False), _direct_config(True)):
                guard = _make_guard(cfg)
                # Should not raise
                guard._check_audit_gate({"post_type": "tiktok_draft"}, privacy)

    def test_direct_self_only_passes_without_audit(self):
        """Direct post with SELF_ONLY is safe — no audit needed."""
        guard = _make_guard(_direct_config(audit_approved=False))
        # Should not raise
        guard._check_audit_gate({"post_type": "tiktok_direct"}, "SELF_ONLY")

    def test_direct_public_with_audit_passes(self):
        """Direct public post IS allowed when audit_approved=true."""
        guard = _make_guard(_direct_config(audit_approved=True))
        # Should not raise
        guard._check_audit_gate({"post_type": "tiktok_direct"}, "PUBLIC_TO_EVERYONE")

    def test_follower_privacy_without_audit_blocked(self):
        """FOLLOWER_OF_CREATOR is a public privacy level — blocked without audit."""
        from core.tiktok.compliance_guard import TikTokComplianceError
        guard = _make_guard(_direct_config(audit_approved=False))
        with self.assertRaises(TikTokComplianceError) as ctx:
            guard._check_audit_gate(
                {"post_type": "tiktok_direct"},
                "FOLLOWER_OF_CREATOR",
            )
        self.assertEqual(ctx.exception.error_code, "ERR_AUDIT_NOT_APPROVED")


# ─────────────────────────────────────────────────────────────────────────────
# C22 — _check_publish_mode
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckPublishMode(unittest.TestCase):

    def test_mode_mismatch_yields_warning(self):
        """draft_upload in config but tiktok_direct in task → WARN_MODE_MISMATCH."""
        guard    = _make_guard({"tiktok_publish_mode": "draft_upload"})
        warnings: list = []
        guard._check_publish_mode({"post_type": "tiktok_direct"}, warnings)
        codes = [w.code for w in warnings]
        self.assertIn("WARN_MODE_MISMATCH", codes)

    def test_no_mismatch_no_warning(self):
        guard    = _make_guard({"tiktok_publish_mode": "direct_private"})
        warnings: list = []
        guard._check_publish_mode({"post_type": "tiktok_direct"}, warnings)
        self.assertEqual(warnings, [])

    def test_draft_task_in_draft_mode_no_warning(self):
        guard    = _make_guard({"tiktok_publish_mode": "draft_upload"})
        warnings: list = []
        guard._check_publish_mode({"post_type": "tiktok_draft"}, warnings)
        self.assertEqual(warnings, [])


# ─────────────────────────────────────────────────────────────────────────────
# C23 — _check_user_confirmation
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckUserConfirmation(unittest.TestCase):

    def test_missing_confirmed_at_yields_warning_when_required(self):
        guard    = _make_guard({"tiktok_require_user_confirm": "true"})
        warnings: list = []
        guard._check_user_confirmation({"user_confirmed_at": ""}, warnings)
        codes = [w.code for w in warnings]
        self.assertIn("WARN_NO_USER_CONFIRMATION", codes)

    def test_present_confirmed_at_no_warning(self):
        guard    = _make_guard({"tiktok_require_user_confirm": "true"})
        warnings: list = []
        guard._check_user_confirmation(
            {"user_confirmed_at": "2026-05-14 10:00:00"}, warnings
        )
        self.assertEqual(warnings, [])

    def test_confirm_not_required_no_warning(self):
        guard    = _make_guard({"tiktok_require_user_confirm": "false"})
        warnings: list = []
        guard._check_user_confirmation({"user_confirmed_at": ""}, warnings)
        self.assertEqual(warnings, [])


# ─────────────────────────────────────────────────────────────────────────────
# C24 — _check_ai_disclosure
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckAiDisclosure(unittest.TestCase):

    def test_is_ai_generated_true_yields_warning(self):
        guard    = _make_guard()
        warnings: list = []
        guard._check_ai_disclosure({"is_ai_generated": "true"}, warnings)
        codes = [w.code for w in warnings]
        self.assertIn("WARN_AI_CONTENT_FLAGGED", codes)

    def test_is_ai_generated_1_yields_warning(self):
        guard    = _make_guard()
        warnings: list = []
        guard._check_ai_disclosure({"is_ai_generated": "1"}, warnings)
        codes = [w.code for w in warnings]
        self.assertIn("WARN_AI_CONTENT_FLAGGED", codes)

    def test_tiktok_key_variant_yields_warning(self):
        guard    = _make_guard()
        warnings: list = []
        guard._check_ai_disclosure({"tiktok_is_ai_generated": "true"}, warnings)
        codes = [w.code for w in warnings]
        self.assertIn("WARN_AI_CONTENT_FLAGGED", codes)

    def test_false_no_warning(self):
        guard    = _make_guard()
        warnings: list = []
        guard._check_ai_disclosure({"is_ai_generated": "false"}, warnings)
        self.assertEqual(warnings, [])

    def test_empty_no_warning(self):
        guard    = _make_guard()
        warnings: list = []
        guard._check_ai_disclosure({}, warnings)
        self.assertEqual(warnings, [])


# ─────────────────────────────────────────────────────────────────────────────
# C25 & C26 — check() integration
# ─────────────────────────────────────────────────────────────────────────────

class TestComplianceGuardCheck(unittest.TestCase):

    def _valid_task(self, video_path: str) -> dict:
        return {
            "video_path":       video_path,
            "post_type":        "tiktok_draft",
            "title":            "Test video",
            "description":      "A short test description",
            "privacy_level":    "SELF_ONLY",
            "user_confirmed_at": "2026-05-14 10:00:00",
            "is_ai_generated":  "false",
        }

    def test_happy_path_returns_empty_warnings(self):
        video = _make_video()
        try:
            acc    = _make_account()
            guard  = _make_guard(_draft_config())
            result = guard.check(self._valid_task(video), acc)
            self.assertIsInstance(result, list)
            self.assertEqual(result, [])
        finally:
            os.unlink(video)

    def test_multiple_warnings_accumulate(self):
        """No caption + AI content → two warnings, no exception."""
        video = _make_video()
        try:
            acc    = _make_account()
            guard  = _make_guard({
                "tiktok_require_user_confirm": "false",
                "tiktok_enable_direct_post":   "false",
                "tiktok_audit_approved":       "false",
                "tiktok_publish_mode":         "draft_upload",
            })
            task = {
                "video_path":      video,
                "post_type":       "tiktok_draft",
                "title":           "",
                "description":     "",
                "is_ai_generated": "true",
            }
            warnings = guard.check(task, acc)
            codes    = [w.code for w in warnings]
            self.assertIn("WARN_NO_CAPTION",        codes)
            self.assertIn("WARN_AI_CONTENT_FLAGGED", codes)
        finally:
            os.unlink(video)

    def test_compliance_error_stops_on_first_violation(self):
        """check() raises on first blocking violation — stops processing."""
        from core.tiktok.compliance_guard import TikTokComplianceError
        guard = _make_guard(_draft_config())
        # No account → should raise immediately, never check video
        with self.assertRaises(TikTokComplianceError) as ctx:
            guard.check({"video_path": "/nonexistent.mp4"}, None)
        self.assertEqual(ctx.exception.error_code, "ERR_NO_ACCOUNT")

    def test_check_returns_list_type(self):
        video = _make_video()
        try:
            acc    = _make_account()
            guard  = _make_guard(_draft_config())
            result = guard.check(self._valid_task(video), acc)
            self.assertIsInstance(result, list)
        finally:
            os.unlink(video)


# ─────────────────────────────────────────────────────────────────────────────
# C27 & C28 — SheetRunner._is_retryable_error() with compliance codes
# ─────────────────────────────────────────────────────────────────────────────

class TestSheetRunnerComplianceRetry(unittest.TestCase):

    def _is_retryable(self, err_str: str) -> bool:
        from core.sheet_runner import SheetRunner
        return SheetRunner._is_retryable_error(err_str)

    def test_err_audit_not_approved_not_retried(self):
        err = "[ERR_AUDIT_NOT_APPROVED] Cannot post with privacy_level='PUBLIC_TO_EVERYONE'"
        self.assertFalse(self._is_retryable(err))

    def test_err_no_account_not_retried(self):
        err = "[ERR_NO_ACCOUNT] No TikTok account connected."
        self.assertFalse(self._is_retryable(err))

    def test_err_insufficient_scope_not_retried(self):
        err = "[ERR_INSUFFICIENT_SCOPE] Missing TikTok permission(s): video.publish"
        self.assertFalse(self._is_retryable(err))

    def test_err_direct_post_disabled_not_retried(self):
        err = "[ERR_DIRECT_POST_DISABLED] Direct TikTok posting is disabled"
        self.assertFalse(self._is_retryable(err))

    def test_err_video_not_found_not_retried(self):
        err = "[ERR_VIDEO_NOT_FOUND] Video file not found: clip.mp4"
        self.assertFalse(self._is_retryable(err))

    def test_err_video_too_large_not_retried(self):
        err = "[ERR_VIDEO_TOO_LARGE] Video file is 5.0 GB, which exceeds TikTok's 4 GB limit."
        self.assertFalse(self._is_retryable(err))

    def test_err_token_expired_no_refresh_not_retried(self):
        err = "[ERR_TOKEN_EXPIRED_NO_REFRESH] TikTok session for 'Alice' has expired"
        self.assertFalse(self._is_retryable(err))

    def test_err_caption_too_long_not_retried(self):
        err = "[ERR_CAPTION_TOO_LONG] Caption is 2201 characters"
        self.assertFalse(self._is_retryable(err))

    def test_network_error_is_retried(self):
        """Regular network errors must still be retryable."""
        err = "ConnectionError: network timeout trying to upload"
        self.assertTrue(self._is_retryable(err))

    def test_rate_limit_is_retried(self):
        err = "TikTok 429 rate_limit_exceeded, try again later"
        self.assertTrue(self._is_retryable(err))

    def test_server_500_is_retried(self):
        err = "HTTP 500 server error during upload"
        self.assertTrue(self._is_retryable(err))

    def test_compliance_error_all_codes_pattern(self):
        """Any [ERR_...] pattern should be classified as non-retryable."""
        for code in (
            "ERR_NO_VIDEO_PATH", "ERR_VIDEO_EMPTY",
            "ERR_INVALID_PRIVACY", "ERR_TITLE_TOO_LONG",
        ):
            err = f"[{code}] some message"
            self.assertFalse(
                self._is_retryable(err),
                f"Expected [{code}] to be non-retryable",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
