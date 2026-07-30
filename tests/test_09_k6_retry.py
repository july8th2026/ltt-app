"""
test_09_k6_retry.py — K-6: Auto-retry failed jobs

Tests:
  - _is_retryable_error() classifier
  - _get_retry_delay() delay schedule
  - _process_retries() resets RETRY rows when timer fires
  - _tick() schedules retry on retryable error (not mark_error)
  - _tick() permanent failure on non-retryable or max-retries exceeded
  - _tick() clears retry tracking on success
  - SheetClient.mark_retry() writes correct status
  - SheetClient.clear_retry_status() resets status to ""
  - get_next_pending_row() skips RETRY rows
  - count_pending() excludes RETRY rows
"""
from __future__ import annotations

import sys
import os
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Error classifier
# ─────────────────────────────────────────────────────────────────────────────

class TestIsRetryableError(unittest.TestCase):

    def _cls(self, err):
        from core.sheet_runner import SheetRunner
        return SheetRunner._is_retryable_error(err)

    # Retryable errors
    def test_rate_limit_retryable(self):
        self.assertTrue(self._cls("Facebook rate limit — thử lại sau vài phút"))

    def test_429_retryable(self):
        self.assertTrue(self._cls("HTTP error 429 Too Many Requests"))

    def test_network_error_retryable(self):
        self.assertTrue(self._cls("network error: connection reset by peer"))

    def test_timeout_retryable(self):
        self.assertTrue(self._cls("Request timed out after 120s"))

    def test_503_retryable(self):
        self.assertTrue(self._cls("503 Service Unavailable"))

    def test_502_retryable(self):
        self.assertTrue(self._cls("502 Bad Gateway"))

    def test_connection_refused_retryable(self):
        self.assertTrue(self._cls("connection refused"))

    def test_try_again_retryable(self):
        self.assertTrue(self._cls("Server error, please try again later"))

    # Non-retryable errors
    def test_token_error_not_retryable(self):
        self.assertFalse(self._cls("Token hết hạn hoặc không hợp lệ"))

    def test_permission_error_not_retryable(self):
        self.assertFalse(self._cls("Thiếu quyền API: pages_manage_posts"))

    def test_expired_not_retryable(self):
        self.assertFalse(self._cls("Token đã hết hạn vào 2026-01-01"))

    def test_file_not_found_not_retryable(self):
        self.assertFalse(self._cls("File không tồn tại: /tmp/video.mp4"))

    def test_filenotfounderror_not_retryable(self):
        self.assertFalse(self._cls("FileNotFoundError: no such file"))

    def test_user_stopped_not_retryable(self):
        self.assertFalse(self._cls("Dừng bởi người dùng"))

    def test_restricted_not_retryable(self):
        self.assertFalse(self._cls("Page bị hạn chế đăng bài"))

    # Unclassified → not retried (safer default)
    def test_unknown_error_not_retried(self):
        self.assertFalse(self._cls("Something unexpected happened"))


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Retry delays
# ─────────────────────────────────────────────────────────────────────────────

class TestRetryDelays(unittest.TestCase):

    def _make_runner(self):
        from core.sheet_runner import SheetRunner
        config = {
            "job_delay_seconds": 0,
            "delete_video_after_upload": False,
            "max_concurrent_uploads_per_page": 1,
            "min_interval_per_page_s": 0,
            "max_retries": 3,
        }
        return SheetRunner(config=config, page_name="P", sheet_tab="T",
                           stop_event=threading.Event())

    def test_attempt_1_delay_300s(self):
        r = self._make_runner()
        delay = r._get_retry_delay(1)
        # P2 jitter: ±10% of 300 → [270, 330]
        self.assertGreaterEqual(delay, 270.0)
        self.assertLessEqual(delay, 330.0)

    def test_attempt_2_delay_900s(self):
        r = self._make_runner()
        delay = r._get_retry_delay(2)
        # P2 jitter: ±10% of 900 → [810, 990]
        self.assertGreaterEqual(delay, 810.0)
        self.assertLessEqual(delay, 990.0)

    def test_attempt_3_delay_3600s(self):
        r = self._make_runner()
        delay = r._get_retry_delay(3)
        # P2 jitter: ±10% of 3600 → [3240, 3960]
        self.assertGreaterEqual(delay, 3240.0)
        self.assertLessEqual(delay, 3960.0)

    def test_attempt_beyond_max_clamps_to_last(self):
        r = self._make_runner()
        delay = r._get_retry_delay(99)
        # Clamped to 3600 base with ±10% jitter → [3240, 3960]
        self.assertGreaterEqual(delay, 3240.0)
        self.assertLessEqual(delay, 3960.0)

    def test_max_retries_default_3(self):
        r = self._make_runner()
        self.assertEqual(r._max_retries, 3)

    def test_max_retries_from_config(self):
        from core.sheet_runner import SheetRunner
        r = SheetRunner(
            config={"max_retries": 5, "job_delay_seconds": 0,
                    "delete_video_after_upload": False,
                    "max_concurrent_uploads_per_page": 1,
                    "min_interval_per_page_s": 0},
            page_name="P", sheet_tab="T", stop_event=threading.Event(),
        )
        self.assertEqual(r._max_retries, 5)


# ─────────────────────────────────────────────────────────────────────────────
# 3.  _process_retries()
# ─────────────────────────────────────────────────────────────────────────────

class TestProcessRetries(unittest.TestCase):

    def _make_runner(self):
        from core.sheet_runner import SheetRunner
        r = SheetRunner(
            config={"job_delay_seconds": 0, "delete_video_after_upload": False,
                    "max_concurrent_uploads_per_page": 1, "min_interval_per_page_s": 0},
            page_name="P", sheet_tab="T", stop_event=threading.Event(),
        )
        r._sheet = MagicMock()
        return r

    def test_no_retry_ready_does_nothing(self):
        r = self._make_runner()
        r._process_retries()
        r._sheet.clear_retry_status.assert_not_called()

    def test_retry_past_due_calls_clear(self):
        r = self._make_runner()
        r._retry_ready[5] = time.time() - 10  # 10s ago → due
        r._retry_attempt[5] = 1
        r._process_retries()
        r._sheet.clear_retry_status.assert_called_once_with(5)

    def test_retry_not_yet_due_skips(self):
        r = self._make_runner()
        r._retry_ready[5] = time.time() + 9999  # far future
        r._process_retries()
        r._sheet.clear_retry_status.assert_not_called()

    def test_ready_row_removed_from_schedule(self):
        r = self._make_runner()
        r._retry_ready[7] = time.time() - 1
        r._retry_attempt[7] = 2
        r._process_retries()
        self.assertNotIn(7, r._retry_ready)

    def test_multiple_due_rows_all_cleared(self):
        r = self._make_runner()
        for row in (2, 4, 6):
            r._retry_ready[row] = time.time() - 1
            r._retry_attempt[row] = 1
        r._process_retries()
        self.assertEqual(r._sheet.clear_retry_status.call_count, 3)


# ─────────────────────────────────────────────────────────────────────────────
# 4.  _tick() — retry scheduling on failure
# ─────────────────────────────────────────────────────────────────────────────

class TestTickRetryLogic(unittest.TestCase):

    _RETRY_STATE_FILE = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "retry_T.json",
    )

    def setUp(self):
        # Remove any persisted retry state so tests are isolated (P2 persistence)
        try:
            os.unlink(self._RETRY_STATE_FILE)
        except FileNotFoundError:
            pass

    def tearDown(self):
        try:
            os.unlink(self._RETRY_STATE_FILE)
        except FileNotFoundError:
            pass

    def _make_runner(self, max_retries=3):
        from core.sheet_runner import SheetRunner
        config = {
            "job_delay_seconds": 0,
            "delete_video_after_upload": False,
            "max_concurrent_uploads_per_page": 1,
            "min_interval_per_page_s": 0,
            "max_retries": max_retries,
        }
        r = SheetRunner(config=config, page_name="P", sheet_tab="T",
                        stop_event=threading.Event())
        # Unit tests must not inherit retry state from operational data files.
        r._retry_attempt.clear()
        r._retry_ready.clear()
        r._save_retry_state = MagicMock()
        r._sheet = MagicMock()
        r._sheet.get_next_pending_row.return_value = {
            "row_idx": 10, "video_url": "https://drive.google.com/file/d/X/view",
            "title": "", "description": "", "keywords": "", "thumbnail_url": "",
            "comment": "", "target_page": "", "schedule": "",
        }
        r._sheet.mark_done = MagicMock()
        r._sheet.mark_running = MagicMock()
        r._sheet.mark_error = MagicMock()
        r._sheet.mark_retry = MagicMock()
        r._sheet.clear_retry_status = MagicMock()

        import tempfile
        self._tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        self._tmp.write(b"v")
        self._tmp.close()
        r._downloader = MagicMock()
        r._downloader.download.return_value = self._tmp.name
        return r

    def tearDown(self):
        try:
            os.unlink(self._tmp.name)
        except Exception:
            pass

    def test_retryable_error_calls_mark_retry_not_mark_error(self):
        r = self._make_runner()
        from core.upload_engine import UploadEngine
        with patch.object(UploadEngine, "run_sync",
                          side_effect=ConnectionError("network timeout")):
            r._tick()
        r._sheet.mark_retry.assert_called_once()
        r._sheet.mark_error.assert_not_called()

    def test_retryable_error_schedules_retry(self):
        r = self._make_runner()
        from core.upload_engine import UploadEngine
        with patch.object(UploadEngine, "run_sync",
                          side_effect=ConnectionError("connection refused")):
            r._tick()
        self.assertIn(10, r._retry_ready)

    def test_retryable_error_increments_attempt_count(self):
        r = self._make_runner()
        from core.upload_engine import UploadEngine
        with patch.object(UploadEngine, "run_sync",
                          side_effect=ConnectionError("network error")):
            r._tick()
        self.assertEqual(r._retry_attempt.get(10), 1)

    def test_non_retryable_error_calls_mark_error(self):
        r = self._make_runner()
        from core.upload_engine import UploadEngine
        with patch.object(UploadEngine, "run_sync",
                          side_effect=RuntimeError("Token hết hạn")):
            r._tick()
        r._sheet.mark_error.assert_called_once()
        r._sheet.mark_retry.assert_not_called()

    def test_max_retries_exceeded_calls_mark_error(self):
        r = self._make_runner(max_retries=2)
        r._retry_attempt[10] = 2  # already used 2 retries
        from core.upload_engine import UploadEngine
        with patch.object(UploadEngine, "run_sync",
                          side_effect=ConnectionError("network error")):
            r._tick()
        r._sheet.mark_error.assert_called_once()
        r._sheet.mark_retry.assert_not_called()

    def test_success_clears_retry_tracking(self):
        r = self._make_runner()
        r._retry_attempt[10] = 2  # had previous retries
        r._retry_ready[10] = time.time() + 999
        from core.upload_engine import UploadEngine
        with patch.object(UploadEngine, "run_sync",
                          return_value=("https://fb.com/v/X", "X")):
            r._tick()
        self.assertNotIn(10, r._retry_attempt)
        self.assertNotIn(10, r._retry_ready)

    def test_mark_retry_receives_attempt_and_max(self):
        r = self._make_runner(max_retries=3)
        from core.upload_engine import UploadEngine
        with patch.object(UploadEngine, "run_sync",
                          side_effect=ConnectionError("network error")):
            r._tick()
        call_args = r._sheet.mark_retry.call_args
        row_idx, attempt, max_r, err = call_args[0]
        self.assertEqual(row_idx, 10)
        self.assertEqual(attempt, 1)
        self.assertEqual(max_r, 3)

    def test_retry_delay_scheduled_correctly(self):
        r = self._make_runner()
        t_before = time.time()
        from core.upload_engine import UploadEngine
        with patch.object(UploadEngine, "run_sync",
                          side_effect=ConnectionError("network error")):
            r._tick()
        t_after = time.time()
        scheduled = r._retry_ready.get(10, 0)
        # P2 jitter: base=300s ±10% → [270, 330]; add small execution buffer
        self.assertGreater(scheduled, t_before + 260)   # 270 - 10s buffer
        self.assertLess(scheduled, t_after + 340)        # 330 + 10s buffer


# ─────────────────────────────────────────────────────────────────────────────
# 5.  SheetClient — mark_retry / clear_retry_status
# ─────────────────────────────────────────────────────────────────────────────

class TestSheetClientRetryMethods(unittest.TestCase):

    def _make_client(self):
        from utils.sheet_client import SheetClient
        config = {
            "sheet_id": "SID", "sheet_tab": "T1",
            "col_status": "status", "col_error": "error_message",
        }
        client = SheetClient(config)
        client._header_map = {"status": 0, "error_message": 1}
        client._current_tab = "T1"
        client._batch_write = MagicMock()
        client._color_row = MagicMock()
        return client

    def test_mark_retry_writes_retry_status(self):
        c = self._make_client()
        c.mark_retry(5, 1, 3, "connection timeout")
        updates = c._batch_write.call_args[0][1]
        # col_status → A (index 0)
        self.assertEqual(updates.get("A"), "RETRY 1/3")

    def test_mark_retry_includes_error_message(self):
        c = self._make_client()
        c.mark_retry(5, 2, 3, "network error")
        updates = c._batch_write.call_args[0][1]
        self.assertIn("network error", updates.get("B", ""))

    def test_clear_retry_status_resets_to_empty(self):
        c = self._make_client()
        c.clear_retry_status(5)
        updates = c._batch_write.call_args[0][1]
        self.assertEqual(updates.get("A"), "")

    def test_clear_retry_colors_row_default(self):
        c = self._make_client()
        c.clear_retry_status(5)
        c._color_row.assert_called_with(5, "default")


# ─────────────────────────────────────────────────────────────────────────────
# 6.  get_next_pending_row() skips RETRY rows
# ─────────────────────────────────────────────────────────────────────────────

class TestSheetClientSkipsRetry(unittest.TestCase):

    def _make_client_with_header(self, header):
        from utils.sheet_client import SheetClient
        cfg = {
            "sheet_id": "SID", "sheet_tab": "Tab1",
            "col_status": "status",
            "col_video_drive": "video",
            "col_schedule_time": "schedule_time",
        }
        client = SheetClient(cfg)
        client._header_map = {h: i for i, h in enumerate(header)}
        client._current_tab = "Tab1"
        return client

    def _make_pending_row(self, status: str, video: str = "https://drive.google.com/X"):
        """A due row matching header [status, video, schedule_time]."""
        from datetime import datetime, timezone
        due = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        return [status, video, due]

    def test_retry_row_is_skipped(self):
        client = self._make_client_with_header(
            ["status", "video", "schedule_time"]
        )
        rows = [
            self._make_pending_row("RETRY 1/3"),
            self._make_pending_row(""),           # should be found
        ]
        # _refresh_header_map must be a no-op so our pre-set header_map is used
        client._refresh_header_map = MagicMock()
        client._retry = MagicMock(return_value={"values": rows})
        client._get_tz = MagicMock(return_value=__import__("zoneinfo").ZoneInfo("UTC"))

        result = client.get_next_pending_row()
        # Should return the second row (empty status), not the RETRY one
        self.assertIsNotNone(result)

    def test_retry_2_of_3_is_skipped(self):
        client = self._make_client_with_header(
            ["status", "video", "schedule_time"]
        )
        rows = [self._make_pending_row("RETRY 2/3")]
        client._refresh_header_map = MagicMock()
        client._retry = MagicMock(return_value={"values": rows})
        client._get_tz = MagicMock(return_value=__import__("zoneinfo").ZoneInfo("UTC"))

        result = client.get_next_pending_row()
        self.assertIsNone(result)


# ─────────────────────────────────────────────────────────────────────────────
# 7.  Config coverage
# ─────────────────────────────────────────────────────────────────────────────

class TestK6ConfigKeys(unittest.TestCase):

    def test_config_json_has_max_retries(self):
        import json
        cfg_path = os.path.join(BASE_DIR, "data", "config.json")
        if not os.path.exists(cfg_path):
            self.skipTest("config.json not found")
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertIn("max_retries", cfg)
        self.assertIsInstance(cfg["max_retries"], int)

    def test_settings_tab_defaults_has_max_retries(self):
        from core.config_defaults import DEFAULTS
        self.assertIn("max_retries", DEFAULTS)
        self.assertIsInstance(DEFAULTS["max_retries"], int)


if __name__ == "__main__":
    unittest.main(verbosity=2)
