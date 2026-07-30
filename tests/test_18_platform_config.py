"""
Tests for core.utils.get_platform_config — per-platform config override with
fallback to shared keys. Underpins the Option-A split-tabs architecture so
TikTok runners can have independent rate limits while staying backwards-compat
with pre-split config.json files.
"""
from __future__ import annotations

import unittest

from core.utils import get_platform_config


class TestPlatformConfigFacebook(unittest.TestCase):
    """For platform='facebook', the shared key is always returned as-is.
    tt_* overrides are ignored on the Facebook side."""

    def test_facebook_returns_shared_key(self):
        cfg = {"min_interval_per_page_s": 30, "tt_min_interval_per_account_s": 99}
        self.assertEqual(
            get_platform_config(cfg, "facebook", "min_interval_per_page_s"),
            30,
        )

    def test_facebook_default_when_missing(self):
        cfg = {}
        self.assertEqual(
            get_platform_config(cfg, "facebook", "min_interval_per_page_s", 30.0),
            30.0,
        )

    def test_facebook_unknown_key_returns_default(self):
        self.assertEqual(
            get_platform_config({}, "facebook", "no_such_key", 42), 42,
        )


class TestPlatformConfigTikTok(unittest.TestCase):
    """For platform='tiktok', tt_* override wins when set; otherwise falls
    back to the shared key — and finally to the supplied default."""

    def test_tiktok_uses_override_when_set(self):
        cfg = {
            "min_interval_per_page_s":         30,
            "tt_min_interval_per_account_s":   90,
        }
        self.assertEqual(
            get_platform_config(cfg, "tiktok", "min_interval_per_page_s"),
            90,
        )

    def test_tiktok_falls_back_when_override_is_zero(self):
        """tt_* == 0 means 'unset' → fall back to shared key."""
        cfg = {
            "min_interval_per_page_s":         30,
            "tt_min_interval_per_account_s":   0,
        }
        self.assertEqual(
            get_platform_config(cfg, "tiktok", "min_interval_per_page_s"),
            30,
        )

    def test_tiktok_falls_back_when_override_is_empty_string(self):
        cfg = {
            "min_interval_per_page_s":         30,
            "tt_min_interval_per_account_s":   "",
        }
        self.assertEqual(
            get_platform_config(cfg, "tiktok", "min_interval_per_page_s"),
            30,
        )

    def test_tiktok_falls_back_to_default_when_both_missing(self):
        self.assertEqual(
            get_platform_config({}, "tiktok", "min_interval_per_page_s", 30.0),
            30.0,
        )

    def test_tiktok_unmapped_key_uses_shared(self):
        """Keys with no tt_* mapping (e.g. graph_api_version) just return the
        shared value without override."""
        cfg = {"graph_api_version": "v21.0"}
        self.assertEqual(
            get_platform_config(cfg, "tiktok", "graph_api_version"),
            "v21.0",
        )

    def test_tiktok_jitter_override(self):
        """Sanity check for another mapped key."""
        cfg = {"jitter_s": 30, "tt_jitter_s": 60}
        self.assertEqual(get_platform_config(cfg, "tiktok", "jitter_s"), 60)

    def test_tiktok_active_hours_override(self):
        cfg = {
            "active_hours_start": 8,  "active_hours_end": 23,
            "tt_active_hours_start": 10, "tt_active_hours_end": 22,
        }
        self.assertEqual(get_platform_config(cfg, "tiktok", "active_hours_start"), 10)
        self.assertEqual(get_platform_config(cfg, "tiktok", "active_hours_end"),   22)


class TestPlatformConfigUnknownPlatform(unittest.TestCase):
    """Unknown platform names behave like facebook (return shared key)."""

    def test_unknown_platform_treated_as_default(self):
        cfg = {"min_interval_per_page_s": 30, "tt_min_interval_per_account_s": 99}
        # Empty platform → use shared key directly, ignore tt_* override
        self.assertEqual(
            get_platform_config(cfg, "", "min_interval_per_page_s"),
            30,
        )
        self.assertEqual(
            get_platform_config(cfg, "instagram", "min_interval_per_page_s"),
            30,
        )


if __name__ == "__main__":
    unittest.main()
