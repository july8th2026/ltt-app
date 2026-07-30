"""
Anti-Spam Phase 3 + 4 tests:
  P3.1 — Adaptive rate tuner (parse_audit_log, recommend_adjustments)
  P4.1 — Anti-spam analytics snapshot
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from core.rate_tuner import (
    TargetStats,
    TunerRecommendation,
    health_summary,
    parse_audit_log,
    recommend_adjustments,
)
from core.anti_spam_analytics import (
    AntiSpamSnapshot,
    collect_snapshot,
    format_oneline,
)


def _write_audit_lines(path: str, records: list[dict]):
    """Helper: write JSONL audit log file from a list of event dicts."""
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            r.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
            r.setdefault("open_id", "u1")
            r.setdefault("display_name", "u1")
            f.write(json.dumps(r) + "\n")


# =============================================================================
# P3.1 — parse_audit_log
# =============================================================================

class TestParseAuditLog(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl", mode="w", encoding="utf-8")
        self.tmp.close()

    def tearDown(self):
        try:
            os.unlink(self.tmp.name)
        except OSError:
            pass

    def test_p3_1_empty_log_returns_empty(self):
        # Empty file
        out = parse_audit_log(self.tmp.name, within_days=7)
        self.assertEqual(out, {})

    def test_p3_1_missing_log_returns_empty(self):
        out = parse_audit_log("/no/such/file.jsonl", within_days=7)
        self.assertEqual(out, {})

    def test_p3_1_counts_attempts_and_successes(self):
        _write_audit_lines(self.tmp.name, [
            {"event": "facebook_publish_attempt"},
            {"event": "facebook_publish_success", "publish_id": "p1"},
            {"event": "facebook_publish_attempt"},
            {"event": "facebook_publish_success", "publish_id": "p2"},
        ])
        out = parse_audit_log(self.tmp.name)
        self.assertIn("u1", out)
        s = out["u1"]
        self.assertEqual(s.total_attempts, 2)
        self.assertEqual(s.successes,      2)
        self.assertEqual(s.success_rate,   1.0)

    def test_p3_1_classifies_rate_limit_failures(self):
        _write_audit_lines(self.tmp.name, [
            {"event": "facebook_publish_attempt"},
            {"event": "facebook_publish_failed",  "error_code": "17"},  # user-level rate
            {"event": "facebook_publish_attempt"},
            {"event": "facebook_publish_failed",  "error_code": "32"},  # page-level rate
        ])
        out = parse_audit_log(self.tmp.name)
        s = out["u1"]
        self.assertEqual(s.failures, 2)
        self.assertEqual(s.rate_limit_hits, 2)
        self.assertEqual(s.abuse_signals,   0)

    def test_p3_1_classifies_abuse_signals(self):
        _write_audit_lines(self.tmp.name, [
            {"event": "facebook_publish_failure", "error_code": "368"},
        ])
        out = parse_audit_log(self.tmp.name)
        self.assertEqual(out["u1"].abuse_signals, 1)

    def test_p3_1_within_days_cutoff(self):
        old_ts = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        fresh_ts = datetime.now(timezone.utc).isoformat()
        _write_audit_lines(self.tmp.name, [
            {"event": "facebook_publish_attempt", "timestamp": old_ts},
            {"event": "facebook_publish_attempt", "timestamp": fresh_ts},
        ])
        out = parse_audit_log(self.tmp.name, within_days=7)
        self.assertEqual(out["u1"].total_attempts, 1)

    def test_p3_1_separate_targets(self):
        _write_audit_lines(self.tmp.name, [
            {"event": "facebook_publish_attempt", "open_id": "acc_A"},
            {"event": "facebook_publish_attempt", "open_id": "acc_B"},
        ])
        out = parse_audit_log(self.tmp.name)
        self.assertEqual(len(out), 2)
        self.assertIn("acc_A", out); self.assertIn("acc_B", out)

    def test_p3_1_ignores_unknown_events(self):
        _write_audit_lines(self.tmp.name, [
            {"event": "some_random_event"},
            {"event": "tiktok_comment_posted"},
            {"event": "facebook_publish_attempt"},  # only this counts
        ])
        out = parse_audit_log(self.tmp.name)
        self.assertEqual(out["u1"].total_attempts, 1)


# =============================================================================
# P3.1 — recommend_adjustments
# =============================================================================

class TestRecommendAdjustments(unittest.TestCase):

    def _stats(self, **kw):
        return {"X": TargetStats(target="X", **kw)}

    def test_p3_1_abuse_signal_tightens_quota(self):
        cfg = {"max_posts_per_page_per_day": 10, "min_inter_page_interval_s": 60}
        recs = recommend_adjustments(
            self._stats(total_attempts=5, successes=4, failures=1, abuse_signals=1),
            cfg,
        )
        tighten = [r for r in recs if r.direction == "tighten"
                   and r.metric == "max_posts_per_page_per_day"]
        self.assertEqual(len(tighten), 1)
        self.assertLess(tighten[0].suggested, 10)
        self.assertEqual(tighten[0].confidence, "high")

    def test_p3_1_rate_hit_lengthens_interval(self):
        cfg = {"min_inter_page_interval_s": 60, "max_posts_per_page_per_day": 10}
        recs = recommend_adjustments(
            self._stats(total_attempts=5, successes=3, failures=2, rate_limit_hits=2),
            cfg,
        )
        loose = [r for r in recs if r.metric == "min_inter_page_interval_s"
                 and r.direction == "tighten"]
        self.assertEqual(len(loose), 1)
        self.assertGreater(loose[0].suggested, 60)

    def test_p3_1_high_success_suggests_loosen(self):
        cfg = {"min_inter_page_interval_s": 200, "max_posts_per_page_per_day": 10}
        recs = recommend_adjustments(
            self._stats(total_attempts=100, successes=99),
            cfg,
        )
        loose = [r for r in recs if r.direction == "loosen"]
        self.assertEqual(len(loose), 1)
        self.assertLess(loose[0].suggested, 200)
        self.assertEqual(loose[0].confidence, "low")

    def test_p3_1_no_recommendations_when_idle(self):
        cfg = {"min_inter_page_interval_s": 60, "max_posts_per_page_per_day": 10}
        recs = recommend_adjustments({}, cfg)
        self.assertEqual(recs, [])

    def test_p3_1_clamps_to_safety_bounds(self):
        """Tightening must not push below the min bound."""
        cfg = {"max_posts_per_page_per_day": 2}
        recs = recommend_adjustments(
            self._stats(total_attempts=5, successes=2, failures=3, abuse_signals=2),
            cfg,
            bounds={"max_posts_per_page_per_day": (1, 50)},
        )
        for r in recs:
            if r.metric == "max_posts_per_page_per_day":
                self.assertGreaterEqual(r.suggested, 1)


# =============================================================================
# P4.1 — Analytics snapshot smoke
# =============================================================================

class TestAntiSpamSnapshot(unittest.TestCase):

    def test_p4_1_collect_snapshot_returns_dataclass(self):
        snap = collect_snapshot(current_config={})
        self.assertIsInstance(snap, AntiSpamSnapshot)
        # Fields should default to safe values
        self.assertEqual(snap.n_critical_tokens, 0)
        self.assertEqual(snap.open_breakers, [])
        self.assertIsInstance(snap.recommendations, list)

    def test_p4_1_format_oneline_when_healthy(self):
        snap = AntiSpamSnapshot()
        snap.success_rate_7d = 1.0
        line = format_oneline(snap)
        self.assertIn("OK", line)

    def test_p4_1_format_oneline_with_alerts(self):
        snap = AntiSpamSnapshot()
        snap.n_critical_tokens = 2
        snap.open_breakers     = [("acc_A", 600)]
        line = format_oneline(snap)
        self.assertIn("token critical", line)
        self.assertIn("breaker", line.lower())


# =============================================================================
# Health summary aggregate
# =============================================================================

class TestHealthSummary(unittest.TestCase):

    def test_p3_1_empty_stats(self):
        s = health_summary({})
        self.assertEqual(s["total_attempts"], 0)
        self.assertEqual(s["success_rate"], 0.0)

    def test_p3_1_aggregates_correctly(self):
        stats = {
            "A": TargetStats(target="A", total_attempts=10, successes=9, failures=1),
            "B": TargetStats(target="B", total_attempts=5,  successes=2, failures=3,
                             abuse_signals=1, rate_limit_hits=2),
        }
        s = health_summary(stats)
        self.assertEqual(s["total_attempts"], 15)
        self.assertEqual(s["successes"],      11)
        self.assertAlmostEqual(s["success_rate"], 11/15, places=2)
        self.assertEqual(s["targets_with_abuse_signal"],   ["B"])
        self.assertEqual(s["targets_with_rate_limit_hit"], ["B"])


if __name__ == "__main__":
    unittest.main()
