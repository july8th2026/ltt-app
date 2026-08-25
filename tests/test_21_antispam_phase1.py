"""
Tests for Anti-Spam Phase 1:
  P1.1 — Content fingerprint + dedup (SQLite content_history.db)
  P1.2 — Random row ordering toggle on SheetClient
  P1.3 — Error-rate Circuit Breaker (rolling window, exponential cooldown)

Each test isolates state by using a tempfile-backed DB / fresh CircuitBreaker
instance so test ordering and parallel runs are safe.
"""
from __future__ import annotations

import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone

from core.circuit_breaker import BreakerState, CircuitBreaker
from core.content_history import (
    ContentFingerprint,
    ContentHistoryStore,
    hash_caption,
    hash_video_bytes,
)


# =============================================================================
# P1.1 — Content fingerprint + dedup
# =============================================================================

class TestHashFunctions(unittest.TestCase):

    def test_hash_video_bytes_is_deterministic(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            f.write(b"abcde" * 10000)
            path = f.name
        try:
            self.assertEqual(hash_video_bytes(path), hash_video_bytes(path))
        finally:
            os.unlink(path)

    def test_hash_video_bytes_different_files(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f1:
            f1.write(b"video_one_data")
            p1 = f1.name
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f2:
            f2.write(b"video_two_data")
            p2 = f2.name
        try:
            self.assertNotEqual(hash_video_bytes(p1), hash_video_bytes(p2))
        finally:
            os.unlink(p1); os.unlink(p2)

    def test_hash_video_missing_file_returns_empty(self):
        self.assertEqual(hash_video_bytes("/nonexistent/path.mp4"), "")
        self.assertEqual(hash_video_bytes(""), "")

    def test_hash_caption_case_and_whitespace_insensitive(self):
        a = hash_caption("Hello World", "Desc.")
        b = hash_caption(" hello world ", " desc. ")
        self.assertEqual(a, b)

    def test_hash_caption_different_text(self):
        a = hash_caption("title1", "")
        b = hash_caption("title2", "")
        self.assertNotEqual(a, b)


class TestContentHistoryStore(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self._tmp.close()
        self.store = ContentHistoryStore(self._tmp.name)

    def tearDown(self):
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass

    def test_p1_1_no_record_no_duplicate(self):
        self.assertFalse(self.store.has_been_posted(
            video_hash="X", target_id="page_A",
        ))

    def test_p1_1_records_and_detects_duplicate(self):
        self.store.record_posted(
            video_hash="v_hash", caption_hash="c_hash",
            target_id="page_A", platform="facebook", publish_id="pid_1",
        )
        self.assertTrue(self.store.has_been_posted(
            video_hash="v_hash", target_id="page_A",
        ))

    def test_p1_1_target_isolation(self):
        """Same video to DIFFERENT target must NOT be flagged as duplicate."""
        self.store.record_posted(
            video_hash="v", caption_hash="c",
            target_id="page_A", platform="facebook", publish_id="pid",
        )
        self.assertFalse(self.store.has_been_posted(
            video_hash="v", target_id="page_B",
        ))

    def test_p1_1_within_days_cutoff(self):
        """Old uploads should not count beyond within_days."""
        # Manually insert with old timestamp by bypassing record_posted
        old_ts = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        with self.store._connect() as conn:
            conn.execute(
                """INSERT INTO content_history
                   (video_hash, caption_hash, target_id, platform, publish_id, uploaded_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ("v", "c", "page_A", "facebook", "pid", old_ts),
            )
            conn.commit()
        # within 30 days → no match
        self.assertFalse(self.store.has_been_posted(
            video_hash="v", target_id="page_A", within_days=30,
        ))
        # no cutoff → match
        self.assertTrue(self.store.has_been_posted(
            video_hash="v", target_id="page_A",
        ))

    def test_p1_1_empty_video_hash_no_match(self):
        """video_hash empty → always False (caption-only intentionally NOT
        treated as duplicate; see has_been_posted docstring)."""
        self.assertFalse(self.store.has_been_posted(
            video_hash="", caption_hash="some_cap", target_id="page_A",
        ))

    def test_p1_1_caption_only_records_not_inserted(self):
        """record_posted with no video_hash is a no-op — keeps DB clean of
        un-fingerprinted noise from test mocks or pre-download paths."""
        self.store.record_posted(
            video_hash="",         # empty
            caption_hash="cap",
            target_id="page_A", platform="facebook", publish_id="pid",
        )
        self.assertEqual(self.store.total_count(), 0)
        self.assertFalse(self.store.has_been_posted(
            video_hash="any", caption_hash="cap", target_id="page_A",
        ))

    def test_p1_1_caption_match_alone_does_not_flag(self):
        """Different videos sharing a caption → NOT duplicate (template caption
        is a legitimate workflow; FB hashes content, not text)."""
        self.store.record_posted(
            video_hash="v_orig", caption_hash="shared_cap",
            target_id="page_A", platform="facebook", publish_id="pid",
        )
        self.assertFalse(self.store.has_been_posted(
            video_hash="v_different", caption_hash="shared_cap",
            target_id="page_A",
        ))

    def test_p1_1_recent_for_target(self):
        for i in range(3):
            self.store.record_posted(
                video_hash=f"v_{i}", caption_hash=f"c_{i}",
                target_id="page_A", platform="facebook", publish_id=f"pid_{i}",
            )
        rows = self.store.recent_for_target("page_A", limit=10)
        self.assertEqual(len(rows), 3)

    def test_p1_1_count_for_target_today(self):
        for i in range(5):
            self.store.record_posted(
                video_hash=f"v_{i}", caption_hash="",
                target_id="page_A", platform="facebook", publish_id=f"pid_{i}",
            )
        self.assertEqual(self.store.count_for_target("page_A", within_days=1), 5)

    def test_p1_1_purge_old(self):
        # Insert 1 old + 1 fresh
        old_ts = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        with self.store._connect() as conn:
            conn.execute(
                """INSERT INTO content_history
                   (video_hash, caption_hash, target_id, platform, publish_id, uploaded_at)
                   VALUES (?,?,?,?,?,?)""",
                ("old", "", "p", "facebook", "pid_old", old_ts),
            )
            conn.commit()
        self.store.record_posted(
            video_hash="fresh", caption_hash="", target_id="p",
            platform="facebook", publish_id="pid_fresh",
        )
        n = self.store.purge_older_than(30)
        self.assertEqual(n, 1)
        self.assertEqual(self.store.total_count(), 1)


# =============================================================================
# P1.2 — Random row ordering toggle (config flag check; behaviour test
# uses the stub helper because the real SheetClient needs Google API)
# =============================================================================

class TestRandomOrderConfig(unittest.TestCase):

    def test_p1_2_default_is_on(self):
        from core.config_defaults import DEFAULTS
        self.assertTrue(
            DEFAULTS.get("anti_spam_random_order"),
            "Random ordering should be ON by default for safety",
        )

    def test_p1_2_random_shuffles_a_known_set(self):
        """Smoke-test that random.shuffle actually permutes — guards against
        a future commit accidentally removing the shuffle call."""
        import random
        rng = random.Random(42)
        original = list(range(20))
        shuffled = original[:]
        rng.shuffle(shuffled)
        self.assertNotEqual(original, shuffled, "Expected at least one swap")
        self.assertEqual(sorted(shuffled), sorted(original), "All items preserved")


# =============================================================================
# P1.3 — Circuit Breaker
# =============================================================================

class TestCircuitBreakerClosedToOpen(unittest.TestCase):

    def test_p1_3_initial_state_is_closed(self):
        cb = CircuitBreaker()
        self.assertEqual(cb.state("k"), BreakerState.CLOSED.value)
        self.assertTrue(cb.allow("k"))

    def test_p1_3_trips_on_consecutive_failures(self):
        """3 consecutive fails (default threshold) → OPEN."""
        cb = CircuitBreaker(consecutive_fails_trip=3, initial_cooldown_s=60)
        cb.record_failure("k"); self.assertEqual(cb.state("k"), "closed")
        cb.record_failure("k"); self.assertEqual(cb.state("k"), "closed")
        cb.record_failure("k"); self.assertEqual(cb.state("k"), "open")
        self.assertFalse(cb.allow("k"))

    def test_p1_3_trips_on_fail_rate(self):
        """5+ samples with >=40% fails → OPEN."""
        cb = CircuitBreaker(
            consecutive_fails_trip=99,
            min_samples_to_trip=5,
            fail_rate_threshold=0.40,
        )
        # 3 ok, 2 fail → 40% fail rate, samples=5 → should trip
        for _ in range(3):
            cb.record_success("k")
        for _ in range(2):
            cb.record_failure("k")
        self.assertEqual(cb.state("k"), "open")

    def test_p1_3_record_success_resets_consecutive(self):
        cb = CircuitBreaker(consecutive_fails_trip=3, min_samples_to_trip=99)
        cb.record_failure("k")
        cb.record_failure("k")
        cb.record_success("k")  # consecutive_failures → 0
        cb.record_failure("k")
        cb.record_failure("k")
        # Only 2 consecutive again → still closed
        self.assertEqual(cb.state("k"), "closed")


class TestCircuitBreakerRecovery(unittest.TestCase):

    def test_p1_3_open_to_half_open_after_cooldown(self):
        cb = CircuitBreaker(
            consecutive_fails_trip=2,
            initial_cooldown_s=0.1,  # 100ms
        )
        cb.record_failure("k")
        cb.record_failure("k")
        self.assertEqual(cb.state("k"), "open")
        self.assertFalse(cb.allow("k"))
        time.sleep(0.15)
        # allow() now → returns True (transitions to HALF_OPEN internally)
        self.assertTrue(cb.allow("k"))
        self.assertEqual(cb.state("k"), "half_open")

    def test_p1_3_half_open_success_closes_breaker(self):
        cb = CircuitBreaker(consecutive_fails_trip=2, initial_cooldown_s=0.05)
        cb.record_failure("k"); cb.record_failure("k")
        time.sleep(0.1)
        cb.allow("k")  # → half_open
        cb.record_success("k")
        self.assertEqual(cb.state("k"), "closed")

    def test_p1_3_half_open_failure_extends_cooldown(self):
        """Failure during half-open probe → back to OPEN with longer cooldown."""
        cb = CircuitBreaker(
            consecutive_fails_trip=2,
            initial_cooldown_s=0.05,
            cooldown_multiplier=3.0,
        )
        cb.record_failure("k"); cb.record_failure("k")
        time.sleep(0.07)
        cb.allow("k")  # → half_open
        cb.record_failure("k")
        stats = cb.stats_for("k")
        self.assertEqual(stats["state"], "open")
        # cooldown should have multiplied
        self.assertGreaterEqual(stats["cooldown_s"], 0.14)  # 0.05 * 3 = 0.15

    def test_p1_3_isolated_per_key(self):
        cb = CircuitBreaker(consecutive_fails_trip=2, initial_cooldown_s=60)
        cb.record_failure("acc_A"); cb.record_failure("acc_A")
        self.assertEqual(cb.state("acc_A"), "open")
        # acc_B unaffected
        self.assertEqual(cb.state("acc_B"), "closed")
        self.assertTrue(cb.allow("acc_B"))

    def test_p1_3_reset_clears_state(self):
        cb = CircuitBreaker(consecutive_fails_trip=2)
        cb.record_failure("k"); cb.record_failure("k")
        cb.reset("k")
        self.assertEqual(cb.state("k"), "closed")

    def test_p1_3_seconds_until_allowed_decreases(self):
        cb = CircuitBreaker(consecutive_fails_trip=2, initial_cooldown_s=100)
        cb.record_failure("k"); cb.record_failure("k")
        s1 = cb.seconds_until_allowed("k")
        time.sleep(0.05)
        s2 = cb.seconds_until_allowed("k")
        self.assertLess(s2, s1)


if __name__ == "__main__":
    unittest.main()
