"""
test_14_audit.py — Unit tests for Phase 7: Audit Logging.

Coverage:
  A1:  append_event writes a valid JSON line to the file
  A2:  appended record contains all expected fields
  A3:  timestamp field is a valid UTC ISO-8601 string
  A4:  multiple events accumulate (one line per event)
  A5:  details dict is serialised correctly
  A6:  empty details defaults to {}
  A7:  custom log_path overrides the default
  A8:  missing parent directory is created automatically
  A9:  all standard fields default to empty/zero when omitted
  A10: concurrent writes from multiple threads produce uncorrupted lines
  A11: TikTokPublisher logs tiktok_publish_attempt before upload
  A12: tiktok_publish_attempt carries open_id, display_name, post_type, privacy_level, row_idx
  A13: TikTokPublisher logs tiktok_publish_success after successful draft upload
  A14: tiktok_publish_success carries publish_id
  A15: TikTokPublisher logs tiktok_publish_success after successful direct upload
  A16: TikTokPublisher logs tiktok_publish_failure on generic exception
  A17: tiktok_publish_failure carries error_code
  A18: TikTokPublisher logs tiktok_compliance_violation on TikTokComplianceError
  A19: tiktok_compliance_violation carries error_code and details.message
  A20: compliance violation is re-raised after logging
  A21: generic failure is re-raised after logging
  A22: TikTokPublisher._ensure_token_fresh() logs tiktok_token_refreshed after refresh
  A23: tiktok_token_refreshed carries open_id and display_name
  A24: SheetRunner forwards row_idx in upload_task
  A25: audit_logger._write creates nested directories
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_account(open_id="u_audit", display_name="Audit User", valid=True):
    from core.tiktok.token_store import TikTokAccount
    now = time.time()
    return TikTokAccount(
        open_id            = open_id,
        display_name       = display_name,
        avatar_url         = "",
        access_token       = "tok_test",
        refresh_token      = "ref_test",
        expires_at         = now + (3600 if valid else -10),
        refresh_expires_at = now + 86400 * 365,
        scopes             = ["video.upload", "video.publish"],
        connected_at       = "2026-01-01T00:00:00",
    )


def _read_events(path: str) -> list:
    """Parse all non-empty lines in the JSONL log file."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _make_publisher(log_path: str, accounts=None):
    """Build a TikTokPublisher with an in-memory token store and custom log path."""
    from core.tiktok.publisher_service import TikTokPublisher
    pub = TikTokPublisher(
        config     = {"tiktok_audit_log_path": log_path},
        stop_event = threading.Event(),
    )
    accs = accounts or [_make_account()]
    store = MagicMock()
    store.all_accounts.return_value = accs
    store.get_account.side_effect   = lambda oid: next(
        (a for a in accs if a.open_id == oid), None
    )
    pub._token_store = store
    return pub


# ─────────────────────────────────────────────────────────────────────────────
# A1–A10  append_event() — unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAppendEventWrite(unittest.TestCase):
    """A1–A6: basic write behaviour."""

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(
            suffix=".jsonl", delete=False, mode="w"
        )
        self._tmp.close()
        self._path = self._tmp.name

    def tearDown(self):
        try:
            os.unlink(self._path)
        except OSError:
            pass

    # A1 ─────────────────────────────────────────────────────────────────────
    def test_writes_valid_json_line(self):
        from utils.audit_logger import append_event
        append_event("tiktok_publish_attempt", log_path=self._path)
        events = _read_events(self._path)
        self.assertEqual(len(events), 1)

    # A2 ─────────────────────────────────────────────────────────────────────
    def test_record_contains_all_expected_fields(self):
        from utils.audit_logger import append_event
        append_event(
            "tiktok_publish_success",
            log_path      = self._path,
            open_id       = "uid_1",
            display_name  = "Bob",
            row_idx       = 42,
            post_type     = "tiktok_draft",
            privacy_level = "SELF_ONLY",
            publish_id    = "pub_99",
            error_code    = "",
            details       = {"extra": "info"},
        )
        ev = _read_events(self._path)[0]
        self.assertEqual(ev["event"],         "tiktok_publish_success")
        self.assertEqual(ev["open_id"],       "uid_1")
        self.assertEqual(ev["display_name"],  "Bob")
        self.assertEqual(ev["row_idx"],       42)
        self.assertEqual(ev["post_type"],     "tiktok_draft")
        self.assertEqual(ev["privacy_level"], "SELF_ONLY")
        self.assertEqual(ev["publish_id"],    "pub_99")
        self.assertEqual(ev["error_code"],    "")
        self.assertEqual(ev["details"],       {"extra": "info"})

    # A3 ─────────────────────────────────────────────────────────────────────
    def test_timestamp_is_valid_iso_utc(self):
        from utils.audit_logger import append_event
        from datetime import datetime, timezone
        append_event("tiktok_publish_attempt", log_path=self._path)
        ev = _read_events(self._path)[0]
        ts = ev["timestamp"]
        # Must parse without error
        dt = datetime.fromisoformat(ts)
        # Must be timezone-aware UTC
        self.assertIsNotNone(dt.tzinfo)

    # A4 ─────────────────────────────────────────────────────────────────────
    def test_multiple_events_accumulate(self):
        from utils.audit_logger import append_event
        append_event("tiktok_publish_attempt", log_path=self._path)
        append_event("tiktok_publish_success",  log_path=self._path)
        append_event("tiktok_publish_failure",  log_path=self._path)
        events = _read_events(self._path)
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0]["event"], "tiktok_publish_attempt")
        self.assertEqual(events[1]["event"], "tiktok_publish_success")
        self.assertEqual(events[2]["event"], "tiktok_publish_failure")

    # A5 ─────────────────────────────────────────────────────────────────────
    def test_details_dict_serialised(self):
        from utils.audit_logger import append_event
        append_event(
            "tiktok_compliance_violation",
            log_path   = self._path,
            details    = {"message": "Nội dung vi phạm", "code": "ERR_X"},
        )
        ev = _read_events(self._path)[0]
        self.assertEqual(ev["details"]["message"], "Nội dung vi phạm")
        self.assertEqual(ev["details"]["code"],    "ERR_X")

    # A6 ─────────────────────────────────────────────────────────────────────
    def test_empty_details_defaults_to_empty_dict(self):
        from utils.audit_logger import append_event
        append_event("tiktok_token_refreshed", log_path=self._path)
        ev = _read_events(self._path)[0]
        self.assertEqual(ev["details"], {})


class TestAppendEventPath(unittest.TestCase):
    """A7–A9: path and default-field behaviour."""

    def setUp(self):
        self._dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._dir, ignore_errors=True)

    # A7 ─────────────────────────────────────────────────────────────────────
    def test_custom_log_path_used(self):
        from utils.audit_logger import append_event
        custom = os.path.join(self._dir, "custom_audit.jsonl")
        append_event("tiktok_publish_attempt", log_path=custom)
        self.assertTrue(os.path.exists(custom))
        events = _read_events(custom)
        self.assertEqual(len(events), 1)

    # A8 ─────────────────────────────────────────────────────────────────────
    def test_missing_parent_directory_created(self):
        from utils.audit_logger import append_event
        nested = os.path.join(self._dir, "deep", "nested", "dir", "audit.jsonl")
        self.assertFalse(os.path.exists(os.path.dirname(nested)))
        append_event("tiktok_publish_attempt", log_path=nested)
        self.assertTrue(os.path.exists(nested))

    # A9 ─────────────────────────────────────────────────────────────────────
    def test_omitted_fields_default_to_empty(self):
        from utils.audit_logger import append_event
        path = os.path.join(self._dir, "minimal.jsonl")
        append_event("tiktok_publish_attempt", log_path=path)
        ev = _read_events(path)[0]
        self.assertEqual(ev["open_id"],       "")
        self.assertEqual(ev["display_name"],  "")
        self.assertEqual(ev["row_idx"],       "")
        self.assertEqual(ev["post_type"],     "")
        self.assertEqual(ev["privacy_level"], "")
        self.assertEqual(ev["publish_id"],    "")
        self.assertEqual(ev["error_code"],    "")
        self.assertEqual(ev["details"],       {})


class TestAppendEventThreadSafety(unittest.TestCase):
    """A10: concurrent writes are safe."""

    def test_concurrent_writes_produce_uncorrupted_lines(self):
        from utils.audit_logger import append_event
        tmp = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        tmp.close()
        path = tmp.name
        n_threads = 10
        n_per_thread = 10
        barrier = threading.Barrier(n_threads)

        def writer(tid):
            barrier.wait()  # all start simultaneously
            for i in range(n_per_thread):
                append_event(
                    "tiktok_publish_attempt",
                    log_path    = path,
                    open_id     = f"u_{tid}",
                    row_idx     = tid * 100 + i,
                )

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(n_threads)]
        for th in threads:
            th.start()
        for th in threads:
            th.join(timeout=10)

        events = _read_events(path)
        os.unlink(path)

        # All 100 events must be present and valid JSON
        self.assertEqual(len(events), n_threads * n_per_thread)
        for ev in events:
            self.assertIn("timestamp", ev)
            self.assertIn("open_id",   ev)


# ─────────────────────────────────────────────────────────────────────────────
# A11–A15  Publisher → attempt + success
# ─────────────────────────────────────────────────────────────────────────────

class TestPublisherAuditAttempt(unittest.TestCase):
    """A11–A12: tiktok_publish_attempt is logged before upload."""

    def setUp(self):
        self._dir = tempfile.mkdtemp()
        self._log = os.path.join(self._dir, "audit.jsonl")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._dir, ignore_errors=True)

    def _publish_draft(self, task_extra=None):
        pub = _make_publisher(self._log)
        task = {
            "video_path":   "/tmp/v.mp4",
            "post_type":    "tiktok_draft",
            "title":        "Test",
            "privacy_level": "SELF_ONLY",
            "row_idx":      7,
        }
        if task_extra:
            task.update(task_extra)
        with patch("core.tiktok.publisher_service.TikTokClient"), \
             patch("core.tiktok.uploader_draft.TikTokDraftUploader.upload",
                   return_value=("pub_a1", "")), \
             patch("core.tiktok.compliance_guard.TikTokComplianceGuard.check",
                   return_value=[]):
            pub.publish(task)

    # A11 ────────────────────────────────────────────────────────────────────
    def test_attempt_event_is_first_event(self):
        self._publish_draft()
        events = _read_events(self._log)
        self.assertGreaterEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "tiktok_publish_attempt")

    # A12 ────────────────────────────────────────────────────────────────────
    def test_attempt_carries_account_and_task_fields(self):
        self._publish_draft()
        attempt = _read_events(self._log)[0]
        self.assertEqual(attempt["open_id"],       "u_audit")
        self.assertEqual(attempt["display_name"],  "Audit User")
        self.assertEqual(attempt["post_type"],      "tiktok_draft")
        self.assertEqual(attempt["privacy_level"],  "SELF_ONLY")
        self.assertEqual(attempt["row_idx"],        7)


class TestPublisherAuditSuccess(unittest.TestCase):
    """A13–A15: tiktok_publish_success logged correctly."""

    def setUp(self):
        self._dir = tempfile.mkdtemp()
        self._log = os.path.join(self._dir, "audit.jsonl")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._dir, ignore_errors=True)

    # A13 ────────────────────────────────────────────────────────────────────
    def test_success_event_logged_after_draft_upload(self):
        pub = _make_publisher(self._log)
        with patch("core.tiktok.publisher_service.TikTokClient"), \
             patch("core.tiktok.uploader_draft.TikTokDraftUploader.upload",
                   return_value=("pub_draft_42", "")), \
             patch("core.tiktok.compliance_guard.TikTokComplianceGuard.check",
                   return_value=[]):
            pub.publish({"video_path": "/v.mp4", "post_type": "tiktok_draft"})

        events = _read_events(self._log)
        event_names = [e["event"] for e in events]
        self.assertIn("tiktok_publish_success", event_names)

    # A14 ────────────────────────────────────────────────────────────────────
    def test_success_carries_publish_id(self):
        pub = _make_publisher(self._log)
        with patch("core.tiktok.publisher_service.TikTokClient"), \
             patch("core.tiktok.uploader_draft.TikTokDraftUploader.upload",
                   return_value=("pub_ABCDEF", "")), \
             patch("core.tiktok.compliance_guard.TikTokComplianceGuard.check",
                   return_value=[]):
            pub.publish({"video_path": "/v.mp4", "post_type": "tiktok_draft"})

        success = next(
            e for e in _read_events(self._log) if e["event"] == "tiktok_publish_success"
        )
        self.assertEqual(success["publish_id"], "pub_ABCDEF")

    # A15 ────────────────────────────────────────────────────────────────────
    def test_success_logged_after_direct_upload(self):
        pub = _make_publisher(self._log)
        with patch("core.tiktok.publisher_service.TikTokClient"), \
             patch("core.tiktok.uploader_direct.TikTokDirectUploader.upload",
                   return_value=("pub_DIRECT_77", "")), \
             patch("core.tiktok.compliance_guard.TikTokComplianceGuard.check",
                   return_value=[]):
            pub.publish({"video_path": "/v.mp4", "post_type": "tiktok_direct"})

        success = next(
            e for e in _read_events(self._log) if e["event"] == "tiktok_publish_success"
        )
        self.assertEqual(success["publish_id"], "pub_DIRECT_77")


# ─────────────────────────────────────────────────────────────────────────────
# A16–A17  Publisher → generic failure
# ─────────────────────────────────────────────────────────────────────────────

class TestPublisherAuditFailure(unittest.TestCase):
    """A16–A17: tiktok_publish_failure is logged and exception re-raised."""

    def setUp(self):
        self._dir = tempfile.mkdtemp()
        self._log = os.path.join(self._dir, "audit.jsonl")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._dir, ignore_errors=True)

    # A16 ────────────────────────────────────────────────────────────────────
    def test_failure_event_logged_on_exception(self):
        from core.tiktok.client import TikTokError
        pub = _make_publisher(self._log)
        with patch("core.tiktok.publisher_service.TikTokClient"), \
             patch("core.tiktok.uploader_draft.TikTokDraftUploader.upload",
                   side_effect=TikTokError("server error", error_code="server_error")), \
             patch("core.tiktok.compliance_guard.TikTokComplianceGuard.check",
                   return_value=[]):
            with self.assertRaises(TikTokError):
                pub.publish({"video_path": "/v.mp4", "post_type": "tiktok_draft"})

        event_names = [e["event"] for e in _read_events(self._log)]
        self.assertIn("tiktok_publish_failure", event_names)

    # A17 ────────────────────────────────────────────────────────────────────
    def test_failure_carries_error_code(self):
        from core.tiktok.client import TikTokError
        pub = _make_publisher(self._log)
        with patch("core.tiktok.publisher_service.TikTokClient"), \
             patch("core.tiktok.uploader_draft.TikTokDraftUploader.upload",
                   side_effect=TikTokError("oops", error_code="rate_limit_exceeded")), \
             patch("core.tiktok.compliance_guard.TikTokComplianceGuard.check",
                   return_value=[]):
            with self.assertRaises(TikTokError):
                pub.publish({"video_path": "/v.mp4", "post_type": "tiktok_draft"})

        failure = next(
            e for e in _read_events(self._log) if e["event"] == "tiktok_publish_failure"
        )
        self.assertEqual(failure["error_code"], "rate_limit_exceeded")

    def test_failure_exception_is_reraised(self):
        """Exception must propagate after logging."""
        from core.tiktok.client import TikTokError
        pub = _make_publisher(self._log)
        with patch("core.tiktok.publisher_service.TikTokClient"), \
             patch("core.tiktok.uploader_draft.TikTokDraftUploader.upload",
                   side_effect=TikTokError("boom", error_code="server_error")), \
             patch("core.tiktok.compliance_guard.TikTokComplianceGuard.check",
                   return_value=[]):
            with self.assertRaises(TikTokError):
                pub.publish({"video_path": "/v.mp4", "post_type": "tiktok_draft"})


# ─────────────────────────────────────────────────────────────────────────────
# A18–A21  Publisher → compliance violation
# ─────────────────────────────────────────────────────────────────────────────

class TestPublisherAuditComplianceViolation(unittest.TestCase):
    """A18–A21: tiktok_compliance_violation is logged and exception re-raised."""

    def setUp(self):
        self._dir = tempfile.mkdtemp()
        self._log = os.path.join(self._dir, "audit.jsonl")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._dir, ignore_errors=True)

    def _raise_compliance(self, *args, **kwargs):
        """Side-effect helper; accepts any args so it works as a mock side_effect."""
        from core.tiktok.compliance_guard import TikTokComplianceError
        raise TikTokComplianceError(
            error_code="ERR_AUDIT_NOT_APPROVED",
            message="App not audited",
        )

    # A18 ────────────────────────────────────────────────────────────────────
    def test_compliance_violation_event_logged(self):
        pub = _make_publisher(self._log)
        with patch("core.tiktok.compliance_guard.TikTokComplianceGuard.check",
                   side_effect=self._raise_compliance):
            with self.assertRaises(Exception):
                pub.publish({"video_path": "/v.mp4", "post_type": "tiktok_direct"})

        event_names = [e["event"] for e in _read_events(self._log)]
        self.assertIn("tiktok_compliance_violation", event_names)

    # A19 ────────────────────────────────────────────────────────────────────
    def test_compliance_violation_carries_error_code_and_message(self):
        pub = _make_publisher(self._log)
        with patch("core.tiktok.compliance_guard.TikTokComplianceGuard.check",
                   side_effect=self._raise_compliance):
            with self.assertRaises(Exception):
                pub.publish({"video_path": "/v.mp4", "post_type": "tiktok_direct"})

        violation = next(
            e for e in _read_events(self._log)
            if e["event"] == "tiktok_compliance_violation"
        )
        self.assertEqual(violation["error_code"], "ERR_AUDIT_NOT_APPROVED")
        self.assertEqual(violation["details"]["message"], "App not audited")

    # A20 ────────────────────────────────────────────────────────────────────
    def test_compliance_violation_is_reraised(self):
        from core.tiktok.compliance_guard import TikTokComplianceError
        pub = _make_publisher(self._log)
        with patch("core.tiktok.compliance_guard.TikTokComplianceGuard.check",
                   side_effect=self._raise_compliance):
            with self.assertRaises(TikTokComplianceError):
                pub.publish({"video_path": "/v.mp4", "post_type": "tiktok_direct"})

    # A21 ────────────────────────────────────────────────────────────────────
    def test_no_success_event_on_compliance_violation(self):
        """tiktok_publish_success must NOT appear when compliance blocks."""
        pub = _make_publisher(self._log)
        with patch("core.tiktok.compliance_guard.TikTokComplianceGuard.check",
                   side_effect=self._raise_compliance):
            with self.assertRaises(Exception):
                pub.publish({"video_path": "/v.mp4", "post_type": "tiktok_direct"})

        event_names = [e["event"] for e in _read_events(self._log)]
        self.assertNotIn("tiktok_publish_success", event_names)


# ─────────────────────────────────────────────────────────────────────────────
# A22–A23  Publisher → token refresh
# ─────────────────────────────────────────────────────────────────────────────

class TestPublisherAuditTokenRefresh(unittest.TestCase):
    """A22–A23: tiktok_token_refreshed is logged after successful refresh."""

    def setUp(self):
        self._dir = tempfile.mkdtemp()
        self._log = os.path.join(self._dir, "audit.jsonl")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._dir, ignore_errors=True)

    def _build_publisher_with_expired_account(self):
        from core.tiktok.publisher_service import TikTokPublisher
        expired  = _make_account(open_id="u_exp", display_name="Expired User", valid=False)
        refreshed = _make_account(open_id="u_exp", display_name="Expired User", valid=True)
        pub = TikTokPublisher(
            config     = {"tiktok_audit_log_path": self._log},
            stop_event = threading.Event(),
        )
        store = MagicMock()
        store.all_accounts.return_value = [expired]
        pub._token_store = store

        # Patch auth_manager to return a refreshed account
        mock_mgr = MagicMock()
        mock_mgr.refresh_access_token.return_value = refreshed

        return pub, mock_mgr

    # A22 ────────────────────────────────────────────────────────────────────
    def test_token_refreshed_event_logged(self):
        pub, mock_mgr = self._build_publisher_with_expired_account()
        # TikTokAuthManager is imported locally inside _ensure_token_fresh(),
        # so we patch at the source module, not at publisher_service.
        with patch("core.tiktok.auth_manager.TikTokAuthManager",
                   return_value=mock_mgr), \
             patch("core.tiktok.publisher_service.TikTokClient"), \
             patch("core.tiktok.uploader_draft.TikTokDraftUploader.upload",
                   return_value=("pub_r1", "")), \
             patch("core.tiktok.compliance_guard.TikTokComplianceGuard.check",
                   return_value=[]):
            pub.publish({"video_path": "/v.mp4", "post_type": "tiktok_draft"})

        event_names = [e["event"] for e in _read_events(self._log)]
        self.assertIn("tiktok_token_refreshed", event_names)

    # A23 ────────────────────────────────────────────────────────────────────
    def test_token_refreshed_carries_open_id_and_display_name(self):
        pub, mock_mgr = self._build_publisher_with_expired_account()
        with patch("core.tiktok.auth_manager.TikTokAuthManager",
                   return_value=mock_mgr), \
             patch("core.tiktok.publisher_service.TikTokClient"), \
             patch("core.tiktok.uploader_draft.TikTokDraftUploader.upload",
                   return_value=("pub_r2", "")), \
             patch("core.tiktok.compliance_guard.TikTokComplianceGuard.check",
                   return_value=[]):
            pub.publish({"video_path": "/v.mp4", "post_type": "tiktok_draft"})

        refresh_ev = next(
            e for e in _read_events(self._log) if e["event"] == "tiktok_token_refreshed"
        )
        self.assertEqual(refresh_ev["open_id"],      "u_exp")
        self.assertEqual(refresh_ev["display_name"], "Expired User")


# ─────────────────────────────────────────────────────────────────────────────
# A24  SheetRunner → row_idx forwarded in upload_task
# ─────────────────────────────────────────────────────────────────────────────

class TestSheetRunnerRowIdxForwarded(unittest.TestCase):
    """A24: SheetRunner._tick() includes row_idx in upload_task."""

    def test_row_idx_in_upload_task(self):
        """
        Verify that row_idx appears in the task dict passed to publisher.publish().
        We intercept the publish() call and inspect its argument.
        """
        import tempfile, threading
        from core.sheet_runner import SheetRunner

        captured_task: dict = {}

        def fake_publish(task):
            captured_task.update(task)
            from core.publisher import PublishResult
            return PublishResult(
                success=True,
                external_post_id="pid",
                external_post_url="",
                status="draft",
            )

        # Minimal config
        config = {
            "delete_video_after_upload": False,
            "job_delay_seconds": 0,
        }
        stop = threading.Event()

        runner = SheetRunner(
            config=config,
            page_name="TestPage",
            sheet_tab="",
            stop_event=stop,
        )

        # Fake sheet row for TikTok task
        fake_task = {
            "row_idx":     99,
            "platform":    "tiktok",
            "video_url":   "https://drive.google.com/file/d/fake_id/view",
            "title":       "Audit Test",
            "description": "",
            "keywords":    "",
            "schedule":    "",
            "post_type":   "tiktok_draft",
            "account":     "",
            "privacy_level": "",
        }

        fake_pub = MagicMock()
        fake_pub.publish = fake_publish

        with patch.object(runner._sheet, "get_next_pending_row", return_value=fake_task), \
             patch.object(runner._sheet, "mark_running"), \
             patch.object(runner._sheet, "mark_done"), \
             patch("core.publisher_registry.get_publisher", return_value=fake_pub), \
             patch("utils.drive_downloader.DriveDownloader.download",
                   return_value="/tmp/fake_video.mp4"), \
             patch("os.path.isfile", return_value=True), \
             patch("core.rate_limiter.get_global_page_metrics", return_value={}):
            # Run _tick() directly (single iteration)
            runner._tick()
            stop.set()

        self.assertEqual(captured_task.get("row_idx"), 99)


# ─────────────────────────────────────────────────────────────────────────────
# A25  _write() creates nested dirs
# ─────────────────────────────────────────────────────────────────────────────

class TestAuditLoggerWriteCreatesDir(unittest.TestCase):
    """A25: _write() handles deeply nested new directories."""

    def test_write_creates_nested_directories(self):
        from utils.audit_logger import _write
        tmp = tempfile.mkdtemp()
        try:
            deep = os.path.join(tmp, "a", "b", "c", "test.jsonl")
            _write(deep, {"event": "test", "timestamp": "now", "open_id": "",
                          "display_name": "", "row_idx": "", "post_type": "",
                          "privacy_level": "", "publish_id": "", "error_code": "",
                          "details": {}})
            self.assertTrue(os.path.exists(deep))
            with open(deep, encoding="utf-8") as fh:
                data = json.loads(fh.readline())
            self.assertEqual(data["event"], "test")
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
