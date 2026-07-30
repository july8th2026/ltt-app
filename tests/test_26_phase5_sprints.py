"""
Phase 5 — Sprint A/B/C/D module tests.

Each test class targets one Sprint module. Module-only tests (no full
integration via sheet_runner) — runtime wiring is exercised by the
existing integration tests in test_25.
"""
from __future__ import annotations

import csv
import os
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

# Sprint A
from core.caption_rotator import (
    CaptionRotationConfig, CaptionRotator,
)
from core.perceptual_hash import (
    MATCH_THRESHOLD, find_perceptual_match, hamming_distance,
    is_perceptually_same, perceptual_video_hash,
)
from core.video_variation import (
    cleanup_varied_tmp, is_ffmpeg_available, vary_video,
)

# Sprint B
from core.session_lock import SessionLock, SessionLockError
from core.app_status import (
    AppStatus, check_app_status, is_app_disabled,
)
from core.multi_app import MetaAppPool, MetaAppRecord

# Sprint C
from core.network_identity import (
    NetworkIdentityProvider, get_default_provider, reset_default_provider,
)

# Sprint D
from core.content_calendar import CalendarRow, ImportResult, import_csv


# =============================================================================
# SPRINT A1 — Caption rotator
# =============================================================================

class TestCaptionRotator(unittest.TestCase):

    def test_a1_deterministic_per_target_day(self):
        cfg = CaptionRotationConfig(
            pools={"emoji": ["🌟", "🔥"]},
            templates=["Hello {emoji}!"],
            keep_original=False,
        )
        r = CaptionRotator(cfg)
        a = r.variant_for("orig", target_id="T1", video_hash="V1", day_key="2026-05-15")
        b = r.variant_for("orig", target_id="T1", video_hash="V1", day_key="2026-05-15")
        self.assertEqual(a, b, "Same (target, video, day) must produce same caption")

    def test_a1_different_targets_likely_different(self):
        cfg = CaptionRotationConfig(
            pools={"emoji": list("🌟🔥💖✨💯")},
            templates=["Caption {emoji}"],
            keep_original=False,
        )
        r = CaptionRotator(cfg)
        variants = set()
        for i in range(10):
            v = r.variant_for("orig", target_id=f"T{i}", day_key="2026-05-15")
            variants.add(v)
        self.assertGreater(len(variants), 1, "Different targets should produce variation")

    def test_a1_keep_original_means_original_in_pool(self):
        cfg = CaptionRotationConfig(
            pools={}, templates=[], keep_original=True,
        )
        r = CaptionRotator(cfg)
        v = r.variant_for("My original caption", target_id="T", day_key="d")
        # With no templates other than the original, output must be original
        self.assertEqual(v, "My original caption")

    def test_a1_empty_pool_leaves_placeholder(self):
        cfg = CaptionRotationConfig(
            pools={}, templates=["Has {missing}"], keep_original=False,
        )
        r = CaptionRotator(cfg)
        v = r.variant_for("", target_id="T", day_key="d")
        self.assertIn("{missing}", v)

    def test_a1_similarity_identical_text(self):
        self.assertEqual(CaptionRotator.similarity("hello world", "hello world"), 1.0)

    def test_a1_similarity_no_overlap(self):
        self.assertEqual(CaptionRotator.similarity("alpha beta", "gamma delta"), 0.0)

    def test_a1_similarity_partial(self):
        # "Hello World" vs "Hello There" — 1/3 overlap (hello)
        s = CaptionRotator.similarity("Hello World", "Hello There")
        self.assertAlmostEqual(s, 1/3, places=2)

    def test_a1_from_app_config_uses_defaults(self):
        cfg = CaptionRotationConfig.from_app_config({})
        self.assertTrue(cfg.pools)   # default pools loaded
        self.assertEqual(cfg.templates, [])
        self.assertTrue(cfg.keep_original)


# =============================================================================
# SPRINT A2 — Perceptual hash
# =============================================================================

class TestPerceptualHash(unittest.TestCase):

    def _make_tmp_file(self, content: bytes) -> str:
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        f.write(content)
        f.close()
        return f.name

    def test_a2_hash_deterministic(self):
        path = self._make_tmp_file(b"x" * 100000)
        try:
            self.assertEqual(perceptual_video_hash(path), perceptual_video_hash(path))
        finally:
            os.unlink(path)

    def test_a2_hash_missing_file(self):
        self.assertEqual(perceptual_video_hash("/no/such/file"), "")
        self.assertEqual(perceptual_video_hash(""), "")

    def test_a2_hamming_distance_basic(self):
        self.assertEqual(hamming_distance("0000000000000000", "0000000000000000"), 0)
        self.assertEqual(hamming_distance("ffffffffffffffff", "0000000000000000"), 64)

    def test_a2_hamming_invalid_returns_64(self):
        self.assertEqual(hamming_distance("", "0000"), 64)
        self.assertEqual(hamming_distance("xyz", "abc"), 64)

    def test_a2_is_perceptually_same(self):
        h = "abcdef0123456789"
        self.assertTrue(is_perceptually_same(h, h))
        # 64-bit Hamming threshold 8 → flipping 1 bit = same
        h2 = format(int(h, 16) ^ 1, "016x")
        self.assertTrue(is_perceptually_same(h, h2))

    def test_a2_find_perceptual_match(self):
        h = "abcdef0123456789"
        known = ["0000000000000000", h, "ffffffffffffffff"]
        self.assertEqual(find_perceptual_match(h, known), h)

    def test_a2_no_match_returns_empty(self):
        h = "abcdef0123456789"
        # very different hashes
        known = ["0000000000000000"]
        self.assertEqual(find_perceptual_match(h, known), "")


# =============================================================================
# SPRINT A4 — Video variation
# =============================================================================

class TestVideoVariation(unittest.TestCase):

    def _make_tmp(self, content=b"v" * 10000) -> str:
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        f.write(content); f.close()
        return f.name

    def test_a4_off_mode_returns_original(self):
        path = self._make_tmp()
        try:
            r = vary_video(path, "tgt_A", mode="off")
            self.assertEqual(r.out_path, path)
            self.assertFalse(r.changed)
        finally:
            os.unlink(path)

    def test_a4_metadata_pad_changes_file(self):
        path = self._make_tmp()
        try:
            r = vary_video(path, "tgt_A", mode="metadata_pad")
            self.assertTrue(r.changed)
            self.assertNotEqual(r.out_path, path)
            self.assertTrue(os.path.exists(r.out_path))
            # File should differ at byte level
            self.assertGreater(
                os.path.getsize(r.out_path),
                os.path.getsize(path),
            )
        finally:
            os.unlink(path)

    def test_a4_metadata_pad_deterministic(self):
        path = self._make_tmp()
        try:
            r1 = vary_video(path, "tgt_A", mode="metadata_pad")
            r2 = vary_video(path, "tgt_A", mode="metadata_pad")
            # Cache hit: same out_path
            self.assertEqual(r1.out_path, r2.out_path)
        finally:
            os.unlink(path)

    def test_a4_different_targets_different_outputs(self):
        path = self._make_tmp()
        try:
            r1 = vary_video(path, "tgt_A", mode="metadata_pad")
            r2 = vary_video(path, "tgt_B", mode="metadata_pad")
            self.assertNotEqual(r1.out_path, r2.out_path)
        finally:
            os.unlink(path)

    def test_a4_missing_file_returns_original(self):
        r = vary_video("/no/such/file.mp4", "tgt", mode="metadata_pad")
        self.assertFalse(r.changed)

    def test_a4_cleanup_does_not_raise(self):
        # Smoke: never raises even when tmp dir is empty
        cleanup_varied_tmp(older_than_hours=0)


# =============================================================================
# SPRINT B2 — Session lock
# =============================================================================

class TestSessionLock(unittest.TestCase):

    def setUp(self):
        self.lock_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.lock_dir, ignore_errors=True)

    def test_b2_acquire_creates_lock_file(self):
        lock = SessionLock("acc_X", lock_dir=self.lock_dir)
        lock.acquire()
        try:
            self.assertTrue(os.path.exists(lock._path))
        finally:
            lock.release()

    def test_b2_release_removes_lock_file(self):
        lock = SessionLock("acc_X", lock_dir=self.lock_dir)
        lock.acquire()
        lock.release()
        self.assertFalse(os.path.exists(lock._path))

    def test_b2_context_manager(self):
        lock = SessionLock("acc_X", lock_dir=self.lock_dir)
        with lock:
            self.assertTrue(os.path.exists(lock._path))
        self.assertFalse(os.path.exists(lock._path))

    def test_b2_same_process_can_reacquire(self):
        """Same process holding lock can re-acquire (idempotent for our PID)."""
        l1 = SessionLock("acc_X", lock_dir=self.lock_dir)
        l1.acquire()
        try:
            # Different SessionLock instance, same process → should succeed
            l2 = SessionLock("acc_X", lock_dir=self.lock_dir)
            l2.acquire()
            l2.release()
        finally:
            l1.release()

    def test_b2_foreign_owner_blocks(self):
        """If another hostname/pid owns the lock and it's not stale → raises."""
        lock = SessionLock("acc_X", lock_dir=self.lock_dir)
        # Inject a foreign owner directly
        import json
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        with open(lock._path, "w", encoding="utf-8") as f:
            json.dump({
                "account_id":  "acc_X",
                "platform":    "facebook",
                "hostname":    "OTHER_BOX",
                "pid":         99999,
                "acquired_at": now,
                "renewed_at":  now,
            }, f)
        with self.assertRaises(SessionLockError):
            lock.acquire()

    def test_b2_steals_stale_lock(self):
        """If the foreign lock has an old renewed_at → can be stolen."""
        lock = SessionLock("acc_X", lock_dir=self.lock_dir)
        import json
        from datetime import datetime, timedelta, timezone
        old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        with open(lock._path, "w", encoding="utf-8") as f:
            json.dump({
                "account_id":  "acc_X",
                "platform":    "facebook",
                "hostname":    "OTHER_BOX",
                "pid":         99999,
                "acquired_at": old,
                "renewed_at":  old,
            }, f)
        # Should succeed because lock is stale
        lock.acquire()
        lock.release()


# =============================================================================
# SPRINT B3 — App status monitor
# =============================================================================

class TestAppStatus(unittest.TestCase):

    def test_b3_no_credentials_returns_not_configured(self):
        report = check_app_status({})
        self.assertEqual(report.status, AppStatus.NOT_CONFIGURED)

    def test_b3_is_app_disabled_predicate(self):
        from core.app_status import AppStatusReport
        ok_r = AppStatusReport("x", AppStatus.OK, "", "", "")
        bad_r = AppStatusReport("x", AppStatus.DISABLED, "", "", "")
        sus_r = AppStatusReport("x", AppStatus.SUSPENDED, "", "", "")
        unk_r = AppStatusReport("x", AppStatus.UNKNOWN, "", "", "")
        self.assertFalse(is_app_disabled(ok_r))
        self.assertTrue(is_app_disabled(bad_r))
        self.assertTrue(is_app_disabled(sus_r))
        self.assertFalse(is_app_disabled(unk_r))


# =============================================================================
# SPRINT B1 — Multi-Meta-App pool
# =============================================================================

class TestMetaAppPool(unittest.TestCase):

    def test_b1_empty_pool_returns_none(self):
        p = MetaAppPool()
        self.assertIsNone(p.next_healthy())
        self.assertEqual(p.healthy_count(), 0)

    def test_b1_round_robin(self):
        p = MetaAppPool([
            MetaAppRecord(app_id="A", app_secret="sa"),
            MetaAppRecord(app_id="B", app_secret="sb"),
            MetaAppRecord(app_id="C", app_secret="sc"),
        ])
        picks = [p.next_healthy().app_id for _ in range(6)]
        # Round-robin should cycle through all three
        self.assertEqual(set(picks), {"A", "B", "C"})

    def test_b1_disabled_app_skipped(self):
        p = MetaAppPool([
            MetaAppRecord(app_id="A", app_secret="sa"),
            MetaAppRecord(app_id="B", app_secret="sb"),
        ])
        p.mark_disabled("A", reason="banned")
        picks = {p.next_healthy().app_id for _ in range(4)}
        self.assertEqual(picks, {"B"})
        self.assertEqual(p.healthy_count(), 1)

    def test_b1_mark_healthy_restores(self):
        p = MetaAppPool([MetaAppRecord(app_id="A", app_secret="sa")])
        p.mark_disabled("A")
        self.assertEqual(p.healthy_count(), 0)
        p.mark_healthy("A")
        self.assertEqual(p.healthy_count(), 1)

    def test_b1_from_legacy_config(self):
        cfg = {"meta_app_id": "legacy_id", "meta_app_secret": "legacy_secret"}
        p = MetaAppPool.from_config(cfg)
        self.assertEqual(p.healthy_count(), 1)
        self.assertEqual(p.next_healthy().app_id, "legacy_id")

    def test_b1_from_pool_config(self):
        cfg = {"meta_app_pool": [
            {"app_id": "X", "app_secret": "sx"},
            {"app_id": "Y", "app_secret": "sy", "disabled": True},
        ]}
        p = MetaAppPool.from_config(cfg)
        self.assertEqual(p.healthy_count(), 1)
        self.assertEqual(p.next_healthy().app_id, "X")

    def test_b1_find(self):
        p = MetaAppPool([MetaAppRecord(app_id="A", app_secret="sa")])
        self.assertIsNotNone(p.find("A"))
        self.assertIsNone(p.find("Z"))


# =============================================================================
# SPRINT C — Network identity
# =============================================================================

class TestNetworkIdentity(unittest.TestCase):

    def setUp(self):
        reset_default_provider()

    def tearDown(self):
        reset_default_provider()

    def test_c_disabled_returns_noop(self):
        p = NetworkIdentityProvider({})
        ident = p.identity_for("acc_X")
        self.assertEqual(ident.user_agent, "")
        self.assertEqual(ident.proxy, "")

    def test_c_enabled_picks_real_ua(self):
        p = NetworkIdentityProvider({"network_identity_enabled": True})
        ident = p.identity_for("acc_X")
        self.assertIn("Mozilla/5.0", ident.user_agent)

    def test_c_same_account_same_ua(self):
        p = NetworkIdentityProvider({"network_identity_enabled": True})
        a = p.identity_for("acc_X")
        b = p.identity_for("acc_X")
        self.assertEqual(a.user_agent, b.user_agent)

    def test_c_different_accounts_likely_different(self):
        p = NetworkIdentityProvider({"network_identity_enabled": True})
        uas = {p.identity_for(f"acc_{i}").user_agent for i in range(20)}
        self.assertGreater(len(uas), 1, "20 accounts should yield >1 UA")

    def test_c_custom_pool_used(self):
        custom = ["AgentA/1.0", "AgentB/2.0"]
        p = NetworkIdentityProvider({
            "network_identity_enabled": True,
            "network_user_agents": custom,
        })
        for i in range(20):
            ident = p.identity_for(f"a{i}")
            self.assertIn(ident.user_agent, custom)

    def test_c_proxy_applied_when_configured(self):
        p = NetworkIdentityProvider({
            "network_identity_enabled": True,
            "network_proxies": ["http://user:pass@proxy:8080"],
        })
        ident = p.identity_for("acc_X")
        self.assertIn("proxy:8080", ident.proxy)


# =============================================================================
# SPRINT D2 — Content calendar CSV
# =============================================================================

class TestContentCalendar(unittest.TestCase):

    def _write_csv(self, rows: list[dict]) -> str:
        f = tempfile.NamedTemporaryFile(
            delete=False, suffix=".csv", mode="w", encoding="utf-8-sig", newline="",
        )
        keys = sorted({k for r in rows for k in r.keys()})
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)
        f.close()
        return f.name

    def test_d2_missing_file(self):
        res = import_csv("/no/such/file.csv")
        self.assertEqual(res.rows, [])
        self.assertTrue(res.errors)

    def test_d2_imports_valid_rows(self):
        path = self._write_csv([
            {"video_url": "https://drive.google.com/x", "title": "T1", "platform": "facebook"},
            {"video_url": "https://drive.google.com/y", "title": "T2", "platform": "tiktok"},
        ])
        try:
            res = import_csv(path)
            self.assertEqual(len(res.rows), 2)
            self.assertEqual(len(res.errors), 0)
            self.assertEqual(res.rows[0].title, "T1")
            self.assertEqual(res.rows[1].platform, "tiktok")
        finally:
            os.unlink(path)

    def test_d2_invalid_platform_skipped(self):
        path = self._write_csv([
            {"video_url": "u1", "platform": "instagram"},   # invalid
            {"video_url": "u2", "platform": "facebook"},
        ])
        try:
            res = import_csv(path)
            self.assertEqual(len(res.rows), 1)
            self.assertEqual(len(res.errors), 1)
        finally:
            os.unlink(path)

    def test_d2_missing_video_url_skipped(self):
        path = self._write_csv([
            {"title": "no url"},   # missing video_url
            {"video_url": "u1"},
        ])
        try:
            res = import_csv(path)
            self.assertEqual(len(res.rows), 1)
            self.assertEqual(len(res.errors), 1)
        finally:
            os.unlink(path)

    def test_d2_bad_schedule_format_skipped(self):
        path = self._write_csv([
            {"video_url": "u1", "schedule_time": "tomorrow 8pm"},   # invalid format
        ])
        try:
            res = import_csv(path)
            self.assertEqual(len(res.rows), 0)
            self.assertEqual(len(res.errors), 1)
        finally:
            os.unlink(path)

    def test_d2_to_sheet_dict_round_trip(self):
        row = CalendarRow(video_url="u1", title="T", platform="facebook")
        d = row.to_sheet_dict()
        self.assertEqual(d["video_url"], "u1")
        self.assertEqual(d["platform"], "facebook")
        # All expected keys present
        for k in ("video_url", "title", "description", "target_page", "platform"):
            self.assertIn(k, d)


if __name__ == "__main__":
    unittest.main()
