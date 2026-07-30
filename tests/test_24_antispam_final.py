"""
Tests for the final batch of anti-spam modules:
  P2.3 — Page health tracker (reach baseline / throttle detection)
  P3.2 — Page warm-up (FB page age → recommended daily cap)
  P3.3 — Time-of-day intelligence (hourly distribution + bot-flat detector)
  P4.2 — Content vault (CSV export + cross-target duplicate finder)
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from core.page_health import (
    PageHealthLevel,
    PageHealthStore,
    assess_page_health,
    update_page_reach_from_insights,
)
from core.page_warmup import (
    WarmupAdvice,
    clear_cache,
    effective_daily_cap,
    get_warmup_advice,
    recommended_cap_for_age,
)
from core.time_intel import (
    HourlyDistribution,
    build_distributions,
    health_warnings,
    pick_post_hour,
    weighted_peak_hours,
)
from core.content_history import ContentHistoryStore
from core.content_vault import (
    DuplicateGroup,
    export_to_csv,
    find_cross_target_duplicates,
    summary_by_target,
)


# =============================================================================
# P2.3 — Page health tracker
# =============================================================================

class TestPageHealthStore(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self._tmp.close()
        self.store = PageHealthStore(self._tmp.name)

    def tearDown(self):
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass

    def test_p2_3_record_and_recent(self):
        for i, reach in enumerate([100, 150, 200]):
            self.store.record_reach("page_A", f"vid_{i}", reach)
        samples = self.store.recent_samples("page_A", limit=10)
        self.assertEqual(sorted(samples), [100, 150, 200])

    def test_p2_3_record_replaces_same_video(self):
        """UPSERT semantics: re-recording same (page, video) updates reach."""
        self.store.record_reach("page_A", "vid_X", 100)
        self.store.record_reach("page_A", "vid_X", 200)
        samples = self.store.recent_samples("page_A")
        self.assertEqual(samples, [200])

    def test_p2_3_baseline_and_current(self):
        # 3 current + 10 baseline samples
        for r in range(10):
            self.store.record_reach("page_A", f"old_{r}", 1000)
        for r in range(3):
            self.store.record_reach("page_A", f"new_{r}", 200)
        current, baseline, n = self.store.baseline_and_current("page_A")
        self.assertEqual(n, 13)
        self.assertAlmostEqual(current,  200, places=0)
        self.assertAlmostEqual(baseline, 1000, places=0)

    def test_p2_3_assess_unknown_with_few_samples(self):
        self.store.record_reach("page_A", "v1", 100)
        report = assess_page_health("page_A", "Page A", store=self.store)
        self.assertIs(report.level, PageHealthLevel.UNKNOWN)

    def test_p2_3_assess_healthy(self):
        for r in range(10):
            self.store.record_reach("page_A", f"old_{r}", 1000)
        for r in range(3):
            self.store.record_reach("page_A", f"new_{r}", 1000)
        report = assess_page_health("page_A", "Page A", store=self.store)
        self.assertIs(report.level, PageHealthLevel.HEALTHY)

    def test_p2_3_assess_throttled(self):
        for r in range(10):
            self.store.record_reach("page_A", f"old_{r}", 1000)
        for r in range(3):
            self.store.record_reach("page_A", f"new_{r}", 200)   # 80% drop
        report = assess_page_health("page_A", "Page A", store=self.store)
        self.assertIs(report.level, PageHealthLevel.THROTTLED)
        self.assertGreaterEqual(report.drop_pct, 40)

    def test_p2_3_assess_dead(self):
        for r in range(10):
            self.store.record_reach("page_A", f"old_{r}", 1000)
        for r in range(3):
            self.store.record_reach("page_A", f"new_{r}", 0)
        report = assess_page_health("page_A", "Page A", store=self.store)
        self.assertIs(report.level, PageHealthLevel.DEAD)

    def test_p2_3_update_from_insights_uses_graph(self):
        gc = MagicMock()
        gc.get_video_insights.side_effect = [
            {"reach": 500}, {"reach": 600}, Exception("boom"),
        ]
        n = update_page_reach_from_insights(
            gc, "page_A", "tok", ["v1", "v2", "v3"], store=self.store,
        )
        self.assertEqual(n, 2)
        self.assertEqual(set(self.store.recent_samples("page_A")), {500, 600})


# =============================================================================
# P3.2 — Page warm-up
# =============================================================================

class TestPageWarmupCurve(unittest.TestCase):

    def test_p3_2_day_zero_one_post(self):
        self.assertEqual(recommended_cap_for_age(0), 1)
        self.assertEqual(recommended_cap_for_age(1), 1)

    def test_p3_2_week_one_two_posts(self):
        self.assertEqual(recommended_cap_for_age(5), 2)

    def test_p3_2_month_three_then_eight(self):
        self.assertEqual(recommended_cap_for_age(20), 5)
        self.assertEqual(recommended_cap_for_age(45), 8)

    def test_p3_2_past_90_days_zero(self):
        """Mature pages: no warm-up cap — user config rules."""
        self.assertEqual(recommended_cap_for_age(120), 0)
        self.assertEqual(recommended_cap_for_age(365), 0)

    def test_p3_2_negative_age_clamped_to_zero(self):
        self.assertEqual(recommended_cap_for_age(-5), 1)


class TestEffectiveDailyCap(unittest.TestCase):

    def test_p3_2_warmup_overrides_user_when_stricter(self):
        advice = WarmupAdvice(page_id="p", age_days=10,
                              recommended_max_per_day=3, note="")
        self.assertEqual(effective_daily_cap(advice, user_cap=10), 3)

    def test_p3_2_user_keeps_when_stricter(self):
        advice = WarmupAdvice(page_id="p", age_days=10,
                              recommended_max_per_day=5, note="")
        self.assertEqual(effective_daily_cap(advice, user_cap=2), 2)

    def test_p3_2_no_warmup_uses_user(self):
        advice = WarmupAdvice(page_id="p", age_days=180,
                              recommended_max_per_day=0, note="")
        self.assertEqual(effective_daily_cap(advice, user_cap=10), 10)

    def test_p3_2_user_unlimited_with_warmup_uses_warmup(self):
        advice = WarmupAdvice(page_id="p", age_days=5,
                              recommended_max_per_day=2, note="")
        self.assertEqual(effective_daily_cap(advice, user_cap=0), 2)


class TestWarmupAdviceFetch(unittest.TestCase):

    def setUp(self):
        clear_cache()

    def tearDown(self):
        clear_cache()

    def test_p3_2_no_client_returns_no_cap(self):
        advice = get_warmup_advice("page_X")
        self.assertEqual(advice.recommended_max_per_day, 0)
        self.assertEqual(advice.age_days, 999)

    def test_p3_2_with_client_fetches_age(self):
        # Page created 5 days ago
        created = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        gc = MagicMock()
        gc.get.return_value = {"created_time": created}
        advice = get_warmup_advice(
            "page_Y", graph_client=gc, page_access_token="tok",
        )
        self.assertEqual(advice.age_days, 5)
        self.assertEqual(advice.recommended_max_per_day, 2)

    def test_p3_2_cache_avoids_second_fetch(self):
        created = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        gc = MagicMock()
        gc.get.return_value = {"created_time": created}
        get_warmup_advice("page_Z", graph_client=gc, page_access_token="tok")
        # Second call uses cache
        gc.get.reset_mock()
        get_warmup_advice("page_Z", graph_client=gc, page_access_token="tok")
        gc.get.assert_not_called()


# =============================================================================
# P3.3 — Time-of-day intelligence
# =============================================================================

class TestHourlyDistribution(unittest.TestCase):

    def test_p3_3_peak_hours(self):
        d = HourlyDistribution(target="X")
        d.histogram[12] = 20
        d.histogram[18] = 30
        d.histogram[ 8] = 10
        d.total = 60
        self.assertEqual(d.peak_hours(2), [18, 12])

    def test_p3_3_bot_flat_detector(self):
        # Even distribution → bot-flat
        d = HourlyDistribution(target="bot")
        for h in range(24):
            d.histogram[h] = 5
        d.total = 120
        self.assertTrue(d.is_bot_flat())

    def test_p3_3_concentrated_not_bot_flat(self):
        d = HourlyDistribution(target="human")
        # All posts in 3 peak hours
        for h in [9, 13, 19]:
            d.histogram[h] = 20
        d.total = 60
        self.assertFalse(d.is_bot_flat())

    def test_p3_3_low_samples_no_flag(self):
        d = HourlyDistribution(target="rare", total=5)
        self.assertFalse(d.is_bot_flat())


class TestBuildDistributions(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl",
                                                mode="w", encoding="utf-8")
        self.tmp.close()

    def tearDown(self):
        try:
            os.unlink(self.tmp.name)
        except OSError:
            pass

    def _write(self, records):
        with open(self.tmp.name, "w", encoding="utf-8") as f:
            for r in records:
                r.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
                r.setdefault("open_id", "u1")
                f.write(json.dumps(r) + "\n")

    def test_p3_3_counts_success_events(self):
        # 5 success at 14:00 UTC + 3 success at 03:00 UTC
        recent = datetime.now(timezone.utc) - timedelta(days=1)
        utc14 = recent.replace(
            hour=14, minute=0, second=0, microsecond=0
        ).isoformat()
        utc03 = recent.replace(
            hour=3, minute=0, second=0, microsecond=0
        ).isoformat()
        self._write(
            [{"event": "facebook_publish_success", "timestamp": utc14}] * 5 +
            [{"event": "facebook_publish_success", "timestamp": utc03}] * 3
        )
        # With +7 offset: 14 UTC = 21 local, 03 UTC = 10 local
        dists = build_distributions(self.tmp.name, timezone_offset_hours=7)
        d = dists["u1"]
        self.assertEqual(d.histogram[21], 5)
        self.assertEqual(d.histogram[10], 3)
        self.assertEqual(d.total, 8)

    def test_p3_3_ignores_other_events(self):
        self._write([
            {"event": "facebook_publish_success"},
            {"event": "facebook_publish_failure"},
            {"event": "tiktok_comment_posted"},
        ])
        dists = build_distributions(self.tmp.name)
        self.assertEqual(dists["u1"].total, 1)


class TestPickPostHour(unittest.TestCase):

    def test_p3_3_uniform_when_no_data(self):
        import random as rnd
        d = HourlyDistribution(target="X", total=0)
        rng = rnd.Random(42)
        hour = pick_post_hour(d, active_hours=(8, 22), rng=rng)
        self.assertGreaterEqual(hour, 8)
        self.assertLess(hour, 22)

    def test_p3_3_weighted_picks_within_active(self):
        import random as rnd
        d = HourlyDistribution(target="X")
        d.histogram[10] = 100; d.histogram[20] = 100
        d.total = 200
        rng = rnd.Random(0)
        picks = {pick_post_hour(d, active_hours=(8, 22), rng=rng) for _ in range(50)}
        self.assertTrue(picks.issubset(range(8, 22)))


class TestHealthWarnings(unittest.TestCase):

    def test_p3_3_flat_pattern_warned(self):
        d = HourlyDistribution(target="bot")
        for h in range(24):
            d.histogram[h] = 5
        d.total = 120
        warnings = health_warnings({"bot": d})
        self.assertTrue(any("đều" in w for w in warnings))

    def test_p3_3_night_posts_warned(self):
        d = HourlyDistribution(target="night-bot")
        for h in [1, 2, 3, 4]:
            d.histogram[h] = 10  # 40 posts in deep night
        for h in [10, 11, 12]:
            d.histogram[h] = 10  # 30 daytime posts
        d.total = 70
        warnings = health_warnings({"night-bot": d})
        self.assertTrue(any("1-5h" in w for w in warnings))


# =============================================================================
# P4.2 — Content vault
# =============================================================================

class TestContentVaultExport(unittest.TestCase):

    def setUp(self):
        self._db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self._db.close()
        self.store = ContentHistoryStore(self._db.name)
        for i in range(3):
            self.store.record_posted(
                video_hash=f"vid_{i}", caption_hash=f"cap_{i}",
                target_id="page_A", platform="facebook",
                publish_id=f"pid_{i}",
            )

    def tearDown(self):
        for p in (self._db.name,):
            try: os.unlink(p)
            except OSError: pass

    def test_p4_2_csv_export_writes_rows(self):
        out = tempfile.NamedTemporaryFile(delete=False, suffix=".csv").name
        try:
            n = export_to_csv(out, store=self.store)
            self.assertEqual(n, 3)
            with open(out, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("video_hash", content)   # header
            self.assertIn("vid_0", content)
        finally:
            try: os.unlink(out)
            except OSError: pass

    def test_p4_2_csv_export_empty_writes_header_only(self):
        self.store.purge_older_than(0)   # wipe all rows
        out = tempfile.NamedTemporaryFile(delete=False, suffix=".csv").name
        try:
            n = export_to_csv(out, store=self.store)
            self.assertEqual(n, 0)
            with open(out, encoding="utf-8") as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 1)   # header only
        finally:
            try: os.unlink(out)
            except OSError: pass

    def test_p4_2_cross_target_duplicates(self):
        # Add cross-target duplicate: same video, 2 different targets
        for tgt in ("page_B", "page_C", "page_D"):
            self.store.record_posted(
                video_hash="shared_vid", caption_hash="c",
                target_id=tgt, platform="facebook", publish_id=f"pid_{tgt}",
            )
        groups = find_cross_target_duplicates(store=self.store, min_targets=2)
        # shared_vid was uploaded to B, C, D → 3 targets
        shared = [g for g in groups if g.video_hash == "shared_vid"]
        self.assertEqual(len(shared), 1)
        self.assertEqual(shared[0].count, 3)
        self.assertEqual(sorted(shared[0].targets), ["page_B", "page_C", "page_D"])

    def test_p4_2_summary_by_target(self):
        rows = summary_by_target(store=self.store)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["target_id"], "page_A")
        self.assertEqual(r["total_posts"], 3)
        self.assertEqual(r["distinct_videos"], 3)
        self.assertEqual(r["reuse_pct"], 0.0)

    def test_p4_2_summary_reuse_pct_reflects_duplicates(self):
        # Add 2 reuse of vid_0 to same target
        for i in range(2):
            self.store.record_posted(
                video_hash="vid_0", caption_hash="c",
                target_id="page_A", platform="facebook",
                publish_id=f"reuse_{i}",
            )
        rows = summary_by_target(store=self.store)
        # 5 total posts, 3 distinct video_hashes → reuse = (1 - 3/5) = 40%
        r = next(r for r in rows if r["target_id"] == "page_A")
        self.assertEqual(r["total_posts"], 5)
        self.assertEqual(r["distinct_videos"], 3)
        self.assertEqual(r["reuse_pct"], 40.0)


if __name__ == "__main__":
    unittest.main()
