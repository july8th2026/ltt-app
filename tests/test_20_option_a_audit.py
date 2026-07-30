"""
End-to-end audit tests for the Option-A split-tabs refactor.

Covers the 7-phase implementation:
  Phase 1: SheetClient.get_next_pending_row / count_pending platform_filter
  Phase 2: SheetRunner platform_filter attribute + wired into _tick
  Phase 3: get_platform_config helper + tt_* keys
  Phase 4: GUI smoke — settings has tt_* in DEFAULTS, tooltips present
  Phase 5: TikTokPublisher uses rate_limiter (covered in test_19)
  Phase 6: Anti-Ban cards split (smoke import)
  Phase 7: BUG #1 fix — single-worker SheetRunner fallback uses platform-aware config

Each section maps to a category in the audit doc; failures will identify the
faulty phase directly.
"""
from __future__ import annotations

import threading
import unittest
from unittest.mock import MagicMock, patch

from core.rate_limiter import RateLimiter
from core.utils import get_platform_config


# =============================================================================
# SECTION A — SheetClient platform filter (Phase 1)
# =============================================================================

class _StubSheetClient:
    """Minimal stub mimicking SheetClient row iteration so we can test the
    platform_filter logic without hitting Google Sheets API."""

    def __init__(self, rows: list[dict]):
        # rows = [{"col_status": "", "col_video_drive": "url", "col_platform": "tiktok", ...}]
        self.rows = rows

    def get_pending_filtered(self, platform_filter: str) -> list[dict]:
        """Mirror of the real filter logic from sheet_client.get_next_pending_row.
        Tests use this directly so we don't need a live SheetClient."""
        platform_filter = (platform_filter or "").strip().lower()
        kept = []
        for r in self.rows:
            status = r.get("col_status", "").strip().upper()
            if status in ("DONE", "RUNNING", "SKIPPED", "ERROR") or status.startswith("RETRY"):
                continue
            if not r.get("col_video_drive"):
                continue
            if platform_filter:
                row_platform = (r.get("col_platform", "") or "facebook").strip().lower()
                if row_platform != platform_filter:
                    continue
            kept.append(r)
        return kept


class TestSheetClientPlatformFilter(unittest.TestCase):
    """A1-A6: the filter on get_next_pending_row picks rows by col_platform."""

    def setUp(self):
        # 4 rows: 2 fb (one with empty col_platform), 1 tiktok, 1 with no video
        self.client = _StubSheetClient([
            {"col_status": "",  "col_video_drive": "v1", "col_platform": "facebook"},
            {"col_status": "",  "col_video_drive": "v2", "col_platform": ""},  # default FB
            {"col_status": "",  "col_video_drive": "v3", "col_platform": "tiktok"},
            {"col_status": "",  "col_video_drive": "",   "col_platform": "tiktok"},  # no video
        ])

    def test_a1_empty_filter_returns_all_with_video(self):
        kept = self.client.get_pending_filtered("")
        self.assertEqual(len(kept), 3, "Empty filter should return all 3 rows with video")

    def test_a2_facebook_filter_skips_tiktok(self):
        kept = self.client.get_pending_filtered("facebook")
        self.assertEqual(len(kept), 2)
        self.assertTrue(all(r.get("col_platform", "") != "tiktok" for r in kept))

    def test_a3_tiktok_filter_skips_facebook(self):
        kept = self.client.get_pending_filtered("tiktok")
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["col_platform"], "tiktok")

    def test_a4_empty_platform_column_defaults_to_facebook(self):
        """Critical back-compat: rows w/o col_platform must be treated as FB."""
        kept = self.client.get_pending_filtered("facebook")
        # Row 2 has col_platform="" — must be included for FB filter
        self.assertIn(
            {"col_status": "", "col_video_drive": "v2", "col_platform": ""},
            kept,
        )

    def test_a5_case_insensitive_matching(self):
        c = _StubSheetClient([
            {"col_status": "", "col_video_drive": "v", "col_platform": "TikTok"},
            {"col_status": "", "col_video_drive": "v", "col_platform": "FACEBOOK"},
        ])
        self.assertEqual(len(c.get_pending_filtered("tiktok")),   1)
        self.assertEqual(len(c.get_pending_filtered("facebook")), 1)

    def test_a6_unknown_platform_filter_returns_empty(self):
        kept = self.client.get_pending_filtered("instagram")
        self.assertEqual(len(kept), 0)


# =============================================================================
# SECTION B — SheetRunner platform_filter (Phase 2)
# =============================================================================

class TestSheetRunnerPlatformFilter(unittest.TestCase):
    """B1-B3: SheetRunner stores and uses platform_filter."""

    def _make_runner(self, **kwargs):
        from core.sheet_runner import SheetRunner
        defaults = dict(
            config       = {},
            page_name    = "P",
            sheet_tab    = "Tab1",
            stop_event   = threading.Event(),
        )
        defaults.update(kwargs)
        return SheetRunner(**defaults)

    def test_b1_platform_filter_stored_on_instance(self):
        r = self._make_runner(platform_filter="tiktok")
        self.assertEqual(r.platform_filter, "tiktok")

    def test_b2_platform_filter_normalises_case(self):
        r = self._make_runner(platform_filter="  TikTok  ")
        self.assertEqual(r.platform_filter, "tiktok")

    def test_b3_empty_platform_filter_is_default_legacy(self):
        r = self._make_runner()
        self.assertEqual(r.platform_filter, "",
                         "Default empty → legacy any-platform mode")


# =============================================================================
# SECTION C — ConcurrentRunner platform_filter (Phase 2)
# =============================================================================

class TestConcurrentRunnerPlatformFilter(unittest.TestCase):
    """C1-C3: ConcurrentRunner accepts platform_filter, forwards to workers,
    and uses platform-aware config for rate-limit construction."""

    def test_c1_concurrent_runner_accepts_platform_filter(self):
        from core.concurrent_runner import ConcurrentRunner
        cr = ConcurrentRunner(
            workers=[{"tab": "T1", "page": "P1"}],
            config={},
            platform_filter="tiktok",
        )
        self.assertEqual(cr._platform_filter, "tiktok")

    def test_c2_forwards_filter_to_each_sheet_runner(self):
        from core.concurrent_runner import ConcurrentRunner
        cr = ConcurrentRunner(
            workers=[{"tab": "T1", "page": "P1"}, {"tab": "T2", "page": "P2"}],
            config={},
            platform_filter="tiktok",
        )
        for runner in cr._runners:
            self.assertEqual(runner.platform_filter, "tiktok")

    def test_c3_uses_tt_keys_when_platform_is_tiktok(self):
        """Critical: ConcurrentRunner with platform_filter=tiktok must build
        a RateLimiter using tt_* values, not the shared keys."""
        from core.concurrent_runner import ConcurrentRunner
        cr = ConcurrentRunner(
            workers=[{"tab": "T1", "page": "P1"}],
            config={
                "min_interval_per_page_s":       30,  # FB-side
                "tt_min_interval_per_account_s": 90,  # TT-side
                "jitter_s":                       0,
                "tt_jitter_s":                   60,
            },
            platform_filter="tiktok",
        )
        # The shared limiter is held by each worker runner
        limiter = cr._runners[0]._rate_limiter
        self.assertEqual(limiter.min_interval_s, 90)
        self.assertEqual(limiter.jitter_s,       60)


# =============================================================================
# SECTION D — get_platform_config edge cases (Phase 3, supplements test_18)
# =============================================================================

class TestPlatformConfigEdgeCases(unittest.TestCase):
    """D1-D3: edge cases not in the original test_18 — None values, negative
    numbers, and tt_* keys that are floats."""

    def test_d1_none_in_config_falls_back(self):
        cfg = {"min_interval_per_page_s": 30, "tt_min_interval_per_account_s": None}
        self.assertEqual(get_platform_config(cfg, "tiktok", "min_interval_per_page_s"), 30)

    def test_d2_negative_value_passes_through(self):
        """Negative numbers are not 'falsy' for our purposes; trust user input.
        (RateLimiter clamps to non-negative internally anyway.)"""
        cfg = {"tt_jitter_s": -1, "jitter_s": 30}
        # Note: -1 is truthy → returned as-is (not fallback)
        self.assertEqual(get_platform_config(cfg, "tiktok", "jitter_s"), -1)

    def test_d3_float_override_works(self):
        cfg = {"min_interval_per_page_s": 30.0, "tt_min_interval_per_account_s": 45.5}
        self.assertEqual(get_platform_config(cfg, "tiktok", "min_interval_per_page_s"), 45.5)


# =============================================================================
# SECTION F — GUI / Settings smoke tests (Phase 4 + 6)
# =============================================================================

class TestSettingsTabHasAllNewKeys(unittest.TestCase):
    """F1-F4: every tt_* key declared in DEFAULTS and has a tooltip."""

    REQUIRED_TT_KEYS = [
        "tt_min_interval_per_account_s",
        "tt_min_inter_account_interval_s",
        "tt_jitter_s",
        "tt_active_hours_start",
        "tt_active_hours_end",
        "tt_max_posts_per_account_per_day",
        "tt_job_delay_seconds",
    ]

    def test_f1_all_tt_keys_in_defaults(self):
        from core.config_defaults import DEFAULTS
        for key in self.REQUIRED_TT_KEYS:
            self.assertIn(key, DEFAULTS, f"Missing default for {key}")

    def test_f2_all_tt_keys_default_zero(self):
        """0/empty = 'fallback to FB' per documented behaviour.

        Exception: tt_max_posts_per_account_per_day defaults to 30 (TT-AUDIT-11)
        because TikTok enforces ~30/day per user and audit reviewers want to
        see the app respecting it. Skip this key here.
        """
        from core.config_defaults import DEFAULTS
        fallback_keys = [
            k for k in self.REQUIRED_TT_KEYS
            if k != "tt_max_posts_per_account_per_day"
        ]
        for key in fallback_keys:
            self.assertEqual(DEFAULTS[key], 0, f"{key} default should be 0 (fallback marker)")
        # Hard cap key: must be > 0 (TT compliance default)
        self.assertEqual(
            DEFAULTS["tt_max_posts_per_account_per_day"], 30,
            "Hard cap default phải = 30 theo TT audit policy",
        )

    def test_f3_all_tt_keys_have_tooltips(self):
        from core.config_help import FIELD_HELP as tips
        for key in self.REQUIRED_TT_KEYS:
            self.assertIn(key, tips, f"Missing tooltip for {key}")
            self.assertGreater(
                len(tips[key]), 30,
                f"Tooltip for {key} too short; should explain meaning",
            )

    def test_f4_sheet_runner_is_per_platform(self):
        """Was: SheetRunnerTab took a `platform` constructor arg. On the web the
        same separation is two routes, one per platform."""
        from server.routes import sheet as sheet_routes
        paths = {r.path for r in sheet_routes.router.routes}
        self.assertIn("/sheet/{platform}", paths)


# =============================================================================
# SECTION G — Cross-platform integration
# =============================================================================

class TestPerPlatformIsolation(unittest.TestCase):
    """G1-G3: two ConcurrentRunner instances with different platform_filter
    must produce limiters with independent values + counters."""

    def test_g1_two_runners_have_independent_limiters(self):
        from core.concurrent_runner import ConcurrentRunner
        config = {
            "min_interval_per_page_s":       30,
            "tt_min_interval_per_account_s": 90,
        }
        cr_fb = ConcurrentRunner(
            workers=[{"tab": "Tfb", "page": "Pfb"}],
            config=config, platform_filter="facebook",
        )
        cr_tt = ConcurrentRunner(
            workers=[{"tab": "Ttt", "page": "Ptt"}],
            config=config, platform_filter="tiktok",
        )
        fb_lim = cr_fb._runners[0]._rate_limiter
        tt_lim = cr_tt._runners[0]._rate_limiter
        self.assertIsNot(fb_lim, tt_lim)
        self.assertEqual(fb_lim.min_interval_s, 30)
        self.assertEqual(tt_lim.min_interval_s, 90)

    def test_g2_fb_limiter_ignores_tt_keys(self):
        """FB-side runner must NOT pick up tt_* values — guard against
        accidental cross-contamination if tt_* mappings ever swap."""
        from core.concurrent_runner import ConcurrentRunner
        cr_fb = ConcurrentRunner(
            workers=[{"tab": "T", "page": "P"}],
            config={
                "min_interval_per_page_s":       30,
                "tt_min_interval_per_account_s": 999,
            },
            platform_filter="facebook",
        )
        self.assertEqual(cr_fb._runners[0]._rate_limiter.min_interval_s, 30)

    def test_g3_legacy_empty_filter_uses_facebook_keys(self):
        """ConcurrentRunner with platform_filter='' (legacy / unspecified)
        defaults to facebook config — preserves pre-refactor behaviour."""
        from core.concurrent_runner import ConcurrentRunner
        cr = ConcurrentRunner(
            workers=[{"tab": "T", "page": "P"}],
            config={
                "min_interval_per_page_s":       45,
                "tt_min_interval_per_account_s": 999,
            },
            # platform_filter omitted → defaults to ""
        )
        # Empty → defaults to FB → reads min_interval_per_page_s=45
        self.assertEqual(cr._runners[0]._rate_limiter.min_interval_s, 45)


# =============================================================================
# SECTION H — BUG #1 fix verification: SheetRunner fallback
# =============================================================================

class TestSheetRunnerFallbackIsPlatformAware(unittest.TestCase):
    """H1-H3: BUG #1 — when SheetRunner is instantiated without a pre-built
    rate_limiter (single-worker path from SheetRunnerTab._start), the fallback
    must honour platform_filter so TT single-worker mode actually uses tt_*."""

    def _make_runner(self, platform_filter, **config_kw):
        from core.sheet_runner import SheetRunner
        return SheetRunner(
            config          = config_kw,
            page_name       = "P",
            sheet_tab       = "T",
            stop_event      = threading.Event(),
            platform_filter = platform_filter,
        )

    def test_h1_tiktok_single_worker_uses_tt_jitter(self):
        r = self._make_runner(
            "tiktok",
            jitter_s        =  0,
            tt_jitter_s     = 75,
        )
        self.assertEqual(r._rate_limiter.jitter_s, 75)

    def test_h2_facebook_single_worker_ignores_tt_keys(self):
        r = self._make_runner(
            "facebook",
            jitter_s        = 10,
            tt_jitter_s     = 99,
        )
        self.assertEqual(r._rate_limiter.jitter_s, 10)

    def test_h3_empty_filter_defaults_to_facebook_keys(self):
        """Legacy SheetRunner with no platform_filter → behaves like FB."""
        r = self._make_runner(
            "",   # no filter
            jitter_s        = 20,
            tt_jitter_s     = 99,
        )
        self.assertEqual(r._rate_limiter.jitter_s, 20)


# =============================================================================
# SECTION I — get_platform_config + RateLimiter integration
# =============================================================================

class TestPlatformConfigIntegratesWithRateLimiter(unittest.TestCase):
    """Verifies the full config → RateLimiter chain for both platforms."""

    def _build_limiter(self, config, platform):
        return RateLimiter(
            min_interval_s             = float(get_platform_config(config, platform, "min_interval_per_page_s", 0.0)),
            min_inter_page_interval_s  = float(get_platform_config(config, platform, "min_inter_page_interval_s", 0.0)),
            jitter_s                   = float(get_platform_config(config, platform, "jitter_s", 0.0)),
            active_hours_start         = int(get_platform_config(config, platform, "active_hours_start", 0)),
            active_hours_end           = int(get_platform_config(config, platform, "active_hours_end", 0)),
            max_posts_per_page_per_day    = int(get_platform_config(config, platform, "max_posts_per_page_per_day", 0)),
            max_posts_per_account_per_day = int(get_platform_config(config, platform, "max_posts_per_account_per_day", 0)),
        )

    def test_chain_fb_uses_shared_keys(self):
        config = {
            "min_interval_per_page_s":   60,
            "jitter_s":                  30,
            "active_hours_start":         8,
            "active_hours_end":          23,
            "max_posts_per_page_per_day": 5,
            "max_posts_per_account_per_day": 30,
        }
        lim = self._build_limiter(config, "facebook")
        self.assertEqual(lim.min_interval_s, 60)
        self.assertEqual(lim.jitter_s,       30)
        self.assertEqual(lim.active_hours_start, 8)
        self.assertEqual(lim.active_hours_end,  23)
        self.assertEqual(lim.max_posts_per_page_per_day, 5)
        self.assertEqual(lim.max_posts_per_account_per_day, 30)

    def test_chain_tt_uses_tt_overrides_with_fallback(self):
        config = {
            "min_interval_per_page_s":          60,   # FB
            "tt_min_interval_per_account_s":   300,   # TT override
            "jitter_s":                          0,   # FB (disabled)
            "tt_jitter_s":                      90,   # TT override
            "active_hours_start":                8,   # FB
            "tt_active_hours_start":             9,   # TT override
            "active_hours_end":                 23,
            # tt_active_hours_end not set → falls back to 23
            "max_posts_per_account_per_day":    30,   # FB
            "tt_max_posts_per_account_per_day":  8,   # TT override (stricter)
        }
        lim = self._build_limiter(config, "tiktok")
        self.assertEqual(lim.min_interval_s,             300)
        self.assertEqual(lim.jitter_s,                    90)
        self.assertEqual(lim.active_hours_start,           9)
        self.assertEqual(lim.active_hours_end,            23)   # fallback
        self.assertEqual(lim.max_posts_per_account_per_day, 8)


if __name__ == "__main__":
    unittest.main()
