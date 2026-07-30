"""
Sprint TT-5 (F1-F6) — TikTok pre-flight validation tests.

Each module is testable in isolation; the wiring into compliance_guard is
verified separately via source-level checks at the bottom.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from core.tiktok.video_validator import (
    CheckResult as _VR, VideoReport, is_ffprobe_available, validate_video,
)
from core.tiktok.content_validator import (
    ContentReport, CheckResult as _CR, validate_content,
)
from core.tiktok.scope_verify import (
    ScopeCheckResult, check_scopes, required_scopes,
)
from core.tiktok.watermark_detector import (
    WatermarkSignal, detect_watermark,
)
from core.tiktok.audio_rights import (
    AudioRightsSignal, check_audio_rights,
)


# =============================================================================
# F1 — Video validator
# =============================================================================

class TestVideoValidator(unittest.TestCase):

    def test_missing_file_fails(self):
        rep = validate_video("/nope.mp4")
        self.assertEqual(rep.fail_count, 1)
        self.assertFalse(rep.ready_to_upload)

    def test_empty_file_fails(self):
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        f.close()  # 0 bytes
        try:
            rep = validate_video(f.name)
            self.assertEqual(rep.fail_count, 1)
        finally:
            os.unlink(f.name)

    def test_normal_file_size_passes(self):
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        f.write(b"x" * 1000)
        f.close()
        try:
            rep = validate_video(f.name)
            # At minimum, "File size" check should pass
            file_size_items = [i for i in rep.items if i.name == "File size"]
            self.assertEqual(len(file_size_items), 1)
            self.assertEqual(file_size_items[0].result, _VR.PASS)
        finally:
            os.unlink(f.name)

    def test_oversize_file_fails(self):
        # Mock os.path.getsize to return > 4 GB without actually creating the file
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        f.write(b"x")
        f.close()
        try:
            with patch("os.path.getsize", return_value=5 * 1024 ** 3):
                rep = validate_video(f.name)
            file_size_items = [i for i in rep.items if i.name == "File size"]
            self.assertEqual(file_size_items[0].result, _VR.FAIL)
        finally:
            os.unlink(f.name)

    def test_ffprobe_availability_is_bool(self):
        self.assertIsInstance(is_ffprobe_available(), bool)


# =============================================================================
# F2 — Scope verification
# =============================================================================

class TestScopeVerify(unittest.TestCase):

    def test_required_scopes_known_op(self):
        self.assertIn("video.upload",  required_scopes("draft_upload"))
        self.assertIn("video.publish", required_scopes("direct_upload"))
        # user.info.basic is NOT required (granted by default at OAuth time)
        self.assertNotIn("user.info.basic", required_scopes("draft_upload"))

    def test_required_scopes_unknown_op_is_empty(self):
        self.assertEqual(required_scopes("nope"), set())

    def test_check_ok_when_all_granted(self):
        result = check_scopes("draft_upload", ["video.upload"])
        self.assertTrue(result.ok)
        self.assertEqual(result.missing_scopes, [])

    def test_check_fails_when_missing(self):
        result = check_scopes("direct_upload", ["video.upload"])
        self.assertFalse(result.ok)
        self.assertIn("video.publish", result.missing_scopes)

    def test_check_handles_string_input(self):
        # granted_scopes can be any iterable of strings
        result = check_scopes("draft_upload", ("video.upload",))
        self.assertTrue(result.ok)

    def test_check_case_insensitive(self):
        result = check_scopes("draft_upload", ["Video.Upload"])
        self.assertTrue(result.ok)

    def test_comment_post_scopes(self):
        result = check_scopes("comment_post", ["video.upload"])
        self.assertFalse(result.ok)
        self.assertIn("comment.create", result.missing_scopes)


# =============================================================================
# F4 — Watermark detector
# =============================================================================

class TestWatermarkDetector(unittest.TestCase):

    def _make_named(self, name: str) -> str:
        d = tempfile.mkdtemp()
        path = os.path.join(d, name)
        with open(path, "wb") as f:
            f.write(b"x" * 100)
        return path

    def test_capcut_filename_detected(self):
        path = self._make_named("VID_20260516_capcut_export.mp4")
        try:
            sig = detect_watermark(path)
            self.assertTrue(sig.detected)
            self.assertEqual(sig.editor_name, "CapCut")
            self.assertEqual(sig.confidence, "high")
        finally:
            os.unlink(path); os.rmdir(os.path.dirname(path))

    def test_clean_filename_no_signal(self):
        path = self._make_named("my_clean_video.mp4")
        try:
            sig = detect_watermark(path)
            self.assertFalse(sig.detected)
        finally:
            os.unlink(path); os.rmdir(os.path.dirname(path))

    def test_missing_file_no_signal(self):
        sig = detect_watermark("/nope.mp4")
        self.assertFalse(sig.detected)

    def test_inshot_detected(self):
        path = self._make_named("output_inshot.mp4")
        try:
            sig = detect_watermark(path)
            self.assertTrue(sig.detected)
            self.assertEqual(sig.editor_name, "InShot")
        finally:
            os.unlink(path); os.rmdir(os.path.dirname(path))


# =============================================================================
# F5 — Audio rights pre-check
# =============================================================================

class TestAudioRights(unittest.TestCase):

    def _make_named(self, name: str) -> str:
        d = tempfile.mkdtemp()
        path = os.path.join(d, name)
        with open(path, "wb") as f:
            f.write(b"x" * 100)
        return path

    def test_official_music_video_high_risk(self):
        path = self._make_named("Justin_Bieber_Ghost_official_music_video.mp4")
        try:
            sig = check_audio_rights(path)
            self.assertEqual(sig.risk_level, "high")
            self.assertIn("filename_pattern", sig.detected_tags)
        finally:
            os.unlink(path); os.rmdir(os.path.dirname(path))

    def test_feat_filename_high_risk(self):
        path = self._make_named("Track feat. Artist.mp4")
        try:
            sig = check_audio_rights(path)
            self.assertEqual(sig.risk_level, "high")
        finally:
            os.unlink(path); os.rmdir(os.path.dirname(path))

    def test_clean_filename(self):
        path = self._make_named("my_morning_routine_2026.mp4")
        try:
            sig = check_audio_rights(path)
            # Without ffprobe, risk is "none" or "low"
            self.assertIn(sig.risk_level, ("none", "low"))
        finally:
            os.unlink(path); os.rmdir(os.path.dirname(path))

    def test_missing_file(self):
        sig = check_audio_rights("/nope.mp4")
        self.assertEqual(sig.risk_level, "none")
        self.assertFalse(sig.has_audio)


# =============================================================================
# F6 — Content (caption + hashtag) policy
# =============================================================================

class TestContentValidator(unittest.TestCase):

    def test_empty_caption_warns(self):
        rep = validate_content("")
        warns = [i for i in rep.items if i.result is _CR.WARN]
        self.assertTrue(any("Length" in i.name for i in warns))
        self.assertTrue(rep.ready_to_upload)   # warn doesn't block

    def test_normal_caption_passes(self):
        rep = validate_content("Helpful morning routine #productivity #morning")
        self.assertTrue(rep.ready_to_upload)
        self.assertEqual(rep.hashtag_count, 2)

    def test_too_long_caption_fails(self):
        long_text = "x" * 2300
        rep = validate_content(long_text)
        self.assertFalse(rep.ready_to_upload)

    def test_too_many_hashtags_fails(self):
        caption = "post " + " ".join(f"#tag{i}" for i in range(35))
        rep = validate_content(caption)
        self.assertFalse(rep.ready_to_upload)

    def test_banned_hashtag_flagged(self):
        rep = validate_content("Check this out #fyp #foryou")
        self.assertFalse(rep.ready_to_upload)

    def test_url_in_caption_warns(self):
        rep = validate_content("Check https://example.com #news")
        warns = [i for i in rep.items if "URL" in i.name and i.result is _CR.WARN]
        self.assertEqual(len(warns), 1)
        self.assertTrue(rep.ready_to_upload)   # warn only

    def test_emoji_only_warns(self):
        rep = validate_content("🌟🔥💖")
        warns = [i for i in rep.items if "Text content" in i.name and i.result is _CR.WARN]
        self.assertEqual(len(warns), 1)

    def test_all_caps_warns(self):
        rep = validate_content("WATCH THIS AMAZING VIDEO NOW")
        warns = [i for i in rep.items if "Text content" in i.name and i.result is _CR.WARN]
        self.assertEqual(len(warns), 1)

    def test_extra_banned_extends_list(self):
        rep = validate_content("Check #customban", extra_banned={"customban"})
        self.assertFalse(rep.ready_to_upload)


# =============================================================================
# Wire-check: compliance_guard imports + uses F1-F6 modules
# =============================================================================

class TestComplianceGuardWiring(unittest.TestCase):

    def test_compliance_guard_imports_all_phase5_modules(self):
        with open(os.path.join("core", "tiktok", "compliance_guard.py"),
                  encoding="utf-8") as f:
            src = f.read()
        for module_marker in (
            "from core.tiktok.video_validator import validate_video",
            "from core.tiktok.scope_verify import check_scopes",
            "from core.tiktok.watermark_detector import detect_watermark",
            "from core.tiktok.audio_rights import check_audio_rights",
            "from core.tiktok.content_validator import",
        ):
            self.assertIn(module_marker, src, f"Missing: {module_marker}")

    def test_compliance_guard_has_phase5_methods(self):
        from core.tiktok.compliance_guard import TikTokComplianceGuard
        for method in (
            "_check_video_properties",
            "_check_oauth_scopes",     # renamed to avoid clash with existing _check_scopes
            "_check_watermark",
            "_check_audio_rights",
            "_check_content_policy",
        ):
            self.assertTrue(
                hasattr(TikTokComplianceGuard, method),
                f"Guard missing {method}"
            )

    def test_defaults_has_phase5_toggles(self):
        from core.config_defaults import DEFAULTS
        for k in (
            "anti_spam_video_validate",
            "anti_spam_scope_verify",
            "anti_spam_watermark_check",
            "anti_spam_audio_rights_check",
            "anti_spam_content_policy",
            "tiktok_banned_hashtags",
        ):
            self.assertIn(k, DEFAULTS, f"DEFAULTS missing {k}")


if __name__ == "__main__":
    unittest.main()
