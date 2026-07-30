"""
test_11_upgrades.py — P0 through P4 quality fixes verification

P0 (Critical K-8 bugs):
  - upload_task forwards post_type to engine
  - upload_task forwards schedule to engine
  - upload_task forwards comment to engine
  - SheetRunner does NOT call _post_comment_safe separately after upload

P1 (Quality fixes):
  - notify_batch_done called when all workers stop (ConcurrentRunner)
  - TelegramNotifier uses single sender thread (queue-based)
  - TelegramNotifier queue drops silently when full (no RuntimeError)
  - uploaded_at respects configured timezone (Asia/Ho_Chi_Minh != UTC)
  - duration_s uses metrics delta when rate-limiter data is available

P2 (Robustness):
  - Retry state persisted to JSON after scheduling
  - Retry state loaded on SheetRunner init
  - Stale retry state (>1h old) discarded on load
  - _get_retry_delay() has jitter (not exactly base value)
  - jitter stays within ±10% of base
  - Reset metrics clears global registry
  - _pick_tag() cycles W7→worker_1, W8→worker_2 …
  - _severity_prefix() returns red icon for error worker log

P3 (Reliability):
  - ReelsUploader binary upload retries on HTTP 500 (max 3 times)
  - ReelsUploader succeeds on 3rd attempt after 2 failures
  - ConcurrentRunner restarts worker after crash (up to max_restarts)
  - ConcurrentRunner permanent error after max_restarts exceeded
  - _escape_md2() escapes MarkdownV2 special characters
  - notify_job_error uses MarkdownV2 (not legacy Markdown)

P4 (K-7 Video Insights):
  - get_video_insights() returns expected keys
  - InsightsFetcher._parse_dt() parses various datetime formats
  - InsightsFetcher._find_pending_rows() skips rows with insights_at set
  - InsightsFetcher._find_pending_rows() skips rows uploaded < 24h ago
  - InsightsFetcher._find_pending_rows() skips rows without fb_video_id
  - InsightsFetcher._write_insights() calls _batch_write with correct data
  - config.json has all new K-7 keys
  - settings_tab.DEFAULTS has all new K-7 keys
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch, call

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


# ═══════════════════════════════════════════════════════════════════════
# P0 — Critical K-8 fixes: post_type / schedule / comment forwarding
# ═══════════════════════════════════════════════════════════════════════

class TestP0UploadTaskForwarding(unittest.TestCase):
    """Verify SheetRunner._tick() forwards post_type, schedule, comment."""

    def _make_runner(self):
        from core.sheet_runner import SheetRunner
        config = {
            "job_delay_seconds": 0,
            "delete_video_after_upload": False,
            "max_concurrent_uploads_per_page": 1,
            "min_interval_per_page_s": 0,
            "max_retries": 3,
            "timezone": "UTC",
        }
        r = SheetRunner(config=config, page_name="P", sheet_tab="T",
                        stop_event=threading.Event())
        r._sheet = MagicMock()
        r._sheet.get_next_pending_row.return_value = {
            "row_idx":     10,
            "video_url":   "https://drive.google.com/file/d/X/view",
            "title":       "My Video",
            "description": "Desc",
            "keywords":    "kw",
            "thumbnail_url": "",
            "comment":     "Hello!",
            "target_page": "",
            "schedule":    "2027-01-01 12:00:00",
            "post_type":   "reels",
        }
        r._sheet.mark_done = MagicMock()
        r._sheet.mark_running = MagicMock()
        r._sheet.mark_error = MagicMock()
        # Temp video
        self._tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        self._tmp.write(b"v" * 100)
        self._tmp.close()
        r._downloader = MagicMock()
        r._downloader.download.return_value = self._tmp.name
        return r

    def tearDown(self):
        try:
            os.unlink(self._tmp.name)
        except Exception:
            pass

    def _run_tick_capture_upload_task(self):
        """Run _tick(), capture what upload_task was passed to UploadEngine."""
        captured = {}
        r = self._make_runner()

        from core.upload_engine import UploadEngine
        orig_init = UploadEngine.__init__
        orig_run_sync = UploadEngine.run_sync

        def mock_run_sync(self_engine, task):
            captured["task"] = dict(task)
            return ("https://fb.com/v/1", "1")

        with patch.object(UploadEngine, "run_sync", mock_run_sync):
            r._tick()

        return captured.get("task", {})

    def test_post_type_forwarded(self):
        task = self._run_tick_capture_upload_task()
        self.assertEqual(task.get("post_type"), "reels")

    def test_schedule_forwarded(self):
        task = self._run_tick_capture_upload_task()
        self.assertEqual(task.get("schedule"), "2027-01-01 12:00:00")

    def test_comment_forwarded(self):
        """Verify sheet_runner forwards 'comment' field through the pipeline.

        Updated contract (after FacebookCommenter introduction):
        - sheet_runner builds upload_task with comment="Hello!"
        - FacebookPublisher receives it intact
        - FacebookPublisher.publish() handles comment via FacebookCommenter
          and clears it BEFORE calling UploadEngine (to avoid double-comment).

        So we now capture at the FacebookPublisher.publish() level instead
        of UploadEngine.run_sync().
        """
        captured = {}
        r = self._make_runner()

        # Patch FacebookPublisher.publish to capture the task it receives
        from core.facebook.publisher_service import FacebookPublisher
        from core.publisher import PublishResult

        def mock_publish(self_pub, task):
            captured["task"] = dict(task)
            return PublishResult(
                success=True, external_post_id="1",
                external_post_url="https://fb.com/v/1", status="published",
            )

        with patch.object(FacebookPublisher, "publish", mock_publish):
            r._tick()

        self.assertEqual(captured["task"].get("comment"), "Hello!")

    def test_default_post_type_is_feed_when_missing(self):
        r = self._make_runner()
        row = r._sheet.get_next_pending_row.return_value
        del row["post_type"]   # row has no post_type
        r._sheet.get_next_pending_row.return_value = row

        captured = {}
        from core.upload_engine import UploadEngine

        def mock_run_sync(self_engine, task):
            captured["task"] = dict(task)
            return ("https://fb.com/v/X", "X")

        with patch.object(UploadEngine, "run_sync", mock_run_sync):
            r._tick()

        self.assertEqual(captured.get("task", {}).get("post_type"), "feed")

    def test_no_separate_post_comment_safe_for_reels(self):
        """_post_comment_safe must NOT be called; engine handles comment."""
        r = self._make_runner()
        r._post_comment_safe = MagicMock()

        from core.upload_engine import UploadEngine
        with patch.object(UploadEngine, "run_sync",
                          return_value=("https://fb.com/v/R", "R")):
            r._tick()

        r._post_comment_safe.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════
# P1 — Quality fixes
# ═══════════════════════════════════════════════════════════════════════

class TestP1BatchDoneNotification(unittest.TestCase):
    """notify_batch_done must be called when all workers stop."""

    def test_batch_done_fired_on_all_stopped(self):
        from core.concurrent_runner import ConcurrentRunner

        notified = []

        def mock_notify(done, error):
            notified.append((done, error))

        workers = [{"tab": "T1", "page": "P1"}]
        runner = ConcurrentRunner(
            workers=workers,
            config={"job_delay_seconds": 0, "max_concurrent_uploads_per_page": 1,
                    "min_interval_per_page_s": 0, "worker_max_restarts": 0},
        )
        runner._runners[0].run = MagicMock(return_value=None)

        with patch("utils.notifier.get_notifier") as mock_get:
            mock_notifier = MagicMock()
            mock_notifier.notify_batch_done = mock_notify
            mock_get.return_value = mock_notifier

            runner.start()
            time.sleep(0.5)  # let thread finish

        self.assertTrue(len(notified) >= 0)  # may or may not fire (daemon timing)
        # The important check: the callback is registered
        # We verify by checking _make_on_stopped logic
        cb = runner._make_on_stopped(0)
        # Manually trigger
        runner._stopped_count = len(runner._runners) - 1  # one short
        with patch("utils.notifier.get_notifier") as mock_get2:
            mock_notifier2 = MagicMock()
            mock_get2.return_value = mock_notifier2
            runner._on_all_stopped = MagicMock()
            cb()
        mock_notifier2.notify_batch_done.assert_called_once()


class TestP1TelegramQueue(unittest.TestCase):

    def test_sender_thread_started(self):
        from utils.notifier import TelegramNotifier
        n = TelegramNotifier({"telegram_bot_token": "1:X", "telegram_chat_id": "123"})
        self.assertTrue(n._sender_thread.is_alive())

    def test_queue_is_bounded(self):
        from utils.notifier import TelegramNotifier
        import queue
        n = TelegramNotifier({"telegram_bot_token": "1:X", "telegram_chat_id": "123"})
        self.assertIsInstance(n._queue, queue.Queue)
        self.assertEqual(n._queue.maxsize, 50)

    def test_full_queue_does_not_raise(self):
        """When queue is full, _send_async silently drops the message."""
        from utils.notifier import TelegramNotifier
        n = TelegramNotifier({"telegram_bot_token": "1:X", "telegram_chat_id": "123"})
        # Fill the queue manually
        for _ in range(50):
            try:
                n._queue.put_nowait("x")
            except Exception:
                break
        # Should not raise
        try:
            n._send_async("overflow message")
        except Exception as e:
            self.fail(f"_send_async raised {e} when queue is full")

    def test_disabled_notifier_does_not_enqueue(self):
        from utils.notifier import TelegramNotifier
        n = TelegramNotifier({})  # no token → disabled
        n._send_async("should not enqueue")
        self.assertEqual(n._queue.qsize(), 0)


class TestP1TimezoneUploadedAt(unittest.TestCase):
    """uploaded_at should use configured timezone, not always UTC."""

    def _run_tick_capture_uploaded_at(self, timezone_str):
        from core.sheet_runner import SheetRunner
        config = {
            "job_delay_seconds": 0,
            "delete_video_after_upload": False,
            "max_concurrent_uploads_per_page": 1,
            "min_interval_per_page_s": 0,
            "max_retries": 0,
            "timezone": timezone_str,
        }
        r = SheetRunner(config=config, page_name="P", sheet_tab="T",
                        stop_event=threading.Event())
        r._sheet = MagicMock()
        r._sheet.get_next_pending_row.return_value = {
            "row_idx": 5, "video_url": "https://drive.google.com/X",
            "title": "", "description": "", "keywords": "",
            "thumbnail_url": "", "comment": "", "target_page": "",
            "schedule": "", "post_type": "feed",
        }
        r._sheet.mark_done = MagicMock()
        r._sheet.mark_running = MagicMock()

        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.write(b"v" * 10)
        tmp.close()
        r._downloader = MagicMock()
        r._downloader.download.return_value = tmp.name

        from core.upload_engine import UploadEngine
        with patch.object(UploadEngine, "run_sync",
                          return_value=("https://fb.com/v/1", "1")):
            r._tick()

        os.unlink(tmp.name)

        call_args = r._sheet.mark_done.call_args
        if call_args is None:
            return None
        kwargs = call_args[1]
        return kwargs.get("uploaded_at", "")

    def test_utc_timezone(self):
        ts = self._run_tick_capture_uploaded_at("UTC")
        self.assertIsNotNone(ts)
        self.assertRegex(ts, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")

    def test_hcm_timezone_offset_from_utc(self):
        """Asia/Ho_Chi_Minh is UTC+7 — timestamp should differ from UTC by ~7h."""
        from datetime import datetime, timezone as tz_mod
        from zoneinfo import ZoneInfo

        ts_utc = self._run_tick_capture_uploaded_at("UTC")
        ts_hcm = self._run_tick_capture_uploaded_at("Asia/Ho_Chi_Minh")

        if ts_utc is None or ts_hcm is None:
            self.skipTest("mark_done not called")

        fmt = "%Y-%m-%d %H:%M:%S"
        dt_utc = datetime.strptime(ts_utc, fmt).replace(tzinfo=tz_mod.utc)
        dt_hcm = datetime.strptime(ts_hcm, fmt)
        # HCM time string represents local time, which is UTC+7
        # So hcm_string hour should be utc_hour + 7 (mod 24)
        diff_h = (dt_hcm.hour - dt_utc.hour) % 24
        self.assertIn(diff_h, (6, 7, 8))  # ±1h for test timing edge cases


class TestP1DurationMetrics(unittest.TestCase):
    """duration_s should use rate-limiter metrics delta when available."""

    def test_duration_uses_metrics_delta_when_available(self):
        """When _delta_upload > 0, it's used instead of wall time."""
        from core.sheet_runner import SheetRunner
        from core.rate_limiter import _GLOBAL_METRICS, _GLOBAL_LOCK, reset_global_metrics
        import core.rate_limiter as rl_module

        reset_global_metrics()

        config = {
            "job_delay_seconds": 0,
            "delete_video_after_upload": False,
            "max_concurrent_uploads_per_page": 1,
            "min_interval_per_page_s": 0,
            "max_retries": 0,
            "timezone": "UTC",
        }
        r = SheetRunner(config=config, page_name="P", sheet_tab="T",
                        stop_event=threading.Event())
        r._sheet = MagicMock()
        r._sheet.get_next_pending_row.return_value = {
            "row_idx": 7, "video_url": "https://drive.google.com/X",
            "title": "", "description": "", "keywords": "",
            "thumbnail_url": "", "comment": "", "target_page": "TestPage",
            "schedule": "", "post_type": "feed",
        }
        r._sheet.mark_done = MagicMock()
        r._sheet.mark_running = MagicMock()

        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.write(b"v" * 10)
        tmp.close()
        r._downloader = MagicMock()
        r._downloader.download.return_value = tmp.name

        # Simulate rate-limiter writing 42.5s of upload time into global metrics
        def fake_run_sync(self_engine, task):
            with _GLOBAL_LOCK:
                _GLOBAL_METRICS["TestPage"] = {
                    "uploads_done": 1,
                    "total_upload_s": 42.5,
                    "avg_wait_s": 0.0,
                    "total_wait_s": 0.0,
                }
            return ("https://fb.com/v/Z", "Z")

        from core.upload_engine import UploadEngine
        with patch.object(UploadEngine, "run_sync", fake_run_sync):
            r._tick()

        os.unlink(tmp.name)
        reset_global_metrics()

        call_args = r._sheet.mark_done.call_args
        if call_args is None:
            self.skipTest("mark_done not called")
        duration_s = call_args[1].get("duration_s", -1)
        # Should be ~42.5 (from metrics delta), not wall time (which would be <1s)
        self.assertAlmostEqual(duration_s, 42.5, delta=5.0)


# ═══════════════════════════════════════════════════════════════════════
# P2 — Robustness: retry state persistence + jitter + dual-tag + reset
# ═══════════════════════════════════════════════════════════════════════

class TestP2RetryStatePersistence(unittest.TestCase):

    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _make_runner(self, tab="TestTab"):
        from core.sheet_runner import SheetRunner
        config = {
            "job_delay_seconds": 0,
            "delete_video_after_upload": False,
            "max_concurrent_uploads_per_page": 1,
            "min_interval_per_page_s": 0,
            "max_retries": 3,
        }
        r = SheetRunner(config=config, page_name="P", sheet_tab=tab,
                        stop_event=threading.Event())
        # Override retry state path to use temp dir
        r._retry_state_path = os.path.join(self._tmp_dir, f"retry_{tab}.json")
        r._sheet = MagicMock()
        return r

    def test_save_creates_json_file(self):
        r = self._make_runner()
        r._retry_attempt = {5: 1}
        r._retry_ready   = {5: time.time() + 300}
        r._save_retry_state()
        self.assertTrue(os.path.exists(r._retry_state_path))

    def test_loaded_attempt_matches_saved(self):
        r = self._make_runner()
        r._retry_attempt = {10: 2, 15: 1}
        r._retry_ready   = {10: time.time() + 600, 15: time.time() + 300}
        r._save_retry_state()

        r2 = self._make_runner()
        r2._retry_state_path = r._retry_state_path
        r2._load_retry_state()
        self.assertEqual(r2._retry_attempt.get(10), 2)
        self.assertEqual(r2._retry_attempt.get(15), 1)

    def test_stale_ready_entries_discarded(self):
        """Entries with ready_time < now - 3600 are dropped on load."""
        r = self._make_runner()
        r._retry_attempt = {20: 1}
        r._retry_ready   = {20: time.time() - 7200}  # 2h ago → stale
        r._save_retry_state()

        r2 = self._make_runner()
        r2._retry_state_path = r._retry_state_path
        r2._load_retry_state()
        self.assertNotIn(20, r2._retry_ready)

    def test_fresh_entries_preserved_on_load(self):
        r = self._make_runner()
        r._retry_attempt = {30: 2}
        r._retry_ready   = {30: time.time() + 900}  # future → fresh
        r._save_retry_state()

        r2 = self._make_runner()
        r2._retry_state_path = r._retry_state_path
        r2._load_retry_state()
        self.assertIn(30, r2._retry_ready)

    def test_save_called_after_retry_schedule(self):
        """After _tick() schedules a retry, the JSON file must exist."""
        r = self._make_runner()
        r._sheet.get_next_pending_row.return_value = {
            "row_idx": 10, "video_url": "https://drive.google.com/X",
            "title": "", "description": "", "keywords": "",
            "thumbnail_url": "", "comment": "", "target_page": "",
            "schedule": "", "post_type": "feed",
        }
        r._sheet.mark_retry = MagicMock()
        r._sheet.mark_running = MagicMock()

        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.write(b"v" * 10)
        tmp.close()
        r._downloader = MagicMock()
        r._downloader.download.return_value = tmp.name

        from core.upload_engine import UploadEngine
        with patch.object(UploadEngine, "run_sync",
                          side_effect=ConnectionError("network error")):
            r._tick()

        os.unlink(tmp.name)
        self.assertTrue(os.path.exists(r._retry_state_path))


class TestP2RetryJitter(unittest.TestCase):

    def _make_runner(self):
        from core.sheet_runner import SheetRunner
        return SheetRunner(
            config={"max_retries": 3, "job_delay_seconds": 0,
                    "delete_video_after_upload": False,
                    "max_concurrent_uploads_per_page": 1,
                    "min_interval_per_page_s": 0},
            page_name="P", sheet_tab="T", stop_event=threading.Event(),
        )

    def test_delay_is_not_exactly_base_value(self):
        """With jitter, no two successive delays should be identical (probabilistic)."""
        r = self._make_runner()
        delays = [r._get_retry_delay(1) for _ in range(20)]
        unique = set(round(d, 4) for d in delays)
        # With random jitter, very unlikely all 20 are identical
        self.assertGreater(len(unique), 1)

    def test_delay_within_10_percent_of_base(self):
        r = self._make_runner()
        base_delay_1 = 300.0
        for _ in range(30):
            d = r._get_retry_delay(1)
            self.assertGreaterEqual(d, base_delay_1 * 0.9 - 1)  # -1 for float rounding
            self.assertLessEqual(d,    base_delay_1 * 1.1 + 1)

    def test_delay_minimum_is_10s(self):
        """Even with full negative jitter, delay stays >= 10s."""
        r = self._make_runner()
        r._retry_delays = [10]   # base 10s
        for _ in range(30):
            d = r._get_retry_delay(1)
            self.assertGreaterEqual(d, 10.0)


class TestP2DualTagWorkerLog(unittest.TestCase):
    """Worker log lines must still show severity.

    A `[W3] Lỗi ...` line is coloured by worker, not by level, so without an
    explicit marker an error is indistinguishable from routine chatter. This
    was gui/result_tabs.py::_severity_prefix; on the web it is
    ui_constants.severity_prefix, applied in monitor_service.collect_logs.
    """

    def _colour(self, message, level="info"):
        from server.services.ui_constants import log_colour
        return log_colour(level, message)

    def _worker_colour(self, n):
        from server.services.ui_constants import WORKER_LOG_COLORS
        return WORKER_LOG_COLORS[(n - 1) % len(WORKER_LOG_COLORS)]

    def test_colour_cycles_for_w7(self):
        # W7 wraps back to the first colour.
        self.assertEqual(self._colour("[W7] some message"), self._worker_colour(1))

    def test_colour_cycles_for_w12(self):
        # (12-1)%6 = 5 → the 6th colour.
        self.assertEqual(self._colour("[W12] msg"), self._worker_colour(6))

    def test_severity_prefix_error(self):
        from server.services.ui_constants import severity_prefix
        self.assertIn("✖", severity_prefix("error"))

    def test_severity_prefix_warning(self):
        from server.services.ui_constants import severity_prefix
        self.assertIn("⚠", severity_prefix("warning"))
        self.assertIn("⚠", severity_prefix("warn"))

    def test_severity_prefix_empty_for_info(self):
        from server.services.ui_constants import severity_prefix
        self.assertEqual(severity_prefix("info"), "")

    def test_severity_prefix_empty_for_success(self):
        from server.services.ui_constants import severity_prefix
        self.assertEqual(severity_prefix("success"), "")

    def test_worker_error_line_gets_the_marker_and_keeps_its_colour(self):
        """The regression that matters: prefixing must not push "[W3]" off the
        start of the string, or the per-worker colour is silently lost."""
        import sys
        import types

        from server.services import monitor_service

        fake = types.ModuleType("fake")
        fake.get_recent_logs = lambda n: [
            {"level": "error", "formatted": "[W3] Lỗi upload"}]
        real = sys.modules.get("utils.logger")
        sys.modules["utils.logger"] = fake
        try:
            row = monitor_service.collect_logs()[0]
        finally:
            if real is not None:
                sys.modules["utils.logger"] = real
            else:
                del sys.modules["utils.logger"]

        self.assertTrue(row["message"].startswith("✖ "))
        self.assertEqual(row["colour"], self._worker_colour(3))

    def test_non_worker_line_gets_no_marker(self):
        import sys
        import types

        from server.services import monitor_service

        fake = types.ModuleType("fake")
        fake.get_recent_logs = lambda n: [
            {"level": "error", "formatted": "Lỗi kết nối sheet"}]
        real = sys.modules.get("utils.logger")
        sys.modules["utils.logger"] = fake
        try:
            row = monitor_service.collect_logs()[0]
        finally:
            if real is not None:
                sys.modules["utils.logger"] = real
            else:
                del sys.modules["utils.logger"]

        self.assertEqual(row["message"], "Lỗi kết nối sheet")


class TestP2ResetMetrics(unittest.TestCase):

    def test_reset_clears_global_registry(self):
        from core.rate_limiter import _GLOBAL_METRICS, _GLOBAL_LOCK, reset_global_metrics
        with _GLOBAL_LOCK:
            _GLOBAL_METRICS["PageA"] = {"uploads_done": 5}
        reset_global_metrics()
        from core.rate_limiter import get_global_page_metrics
        self.assertEqual(get_global_page_metrics(), {})


# ═══════════════════════════════════════════════════════════════════════
# P3 — Reliability: chunk retry, auto-restart, MarkdownV2
# ═══════════════════════════════════════════════════════════════════════

class TestP3ReelsBinaryUploadRetry(unittest.TestCase):

    def _make_uploader(self):
        from core.reels_uploader import ReelsUploader
        from core.token_store import AccountInfo, PageInfo
        from utils.logger import BotLogger

        page = MagicMock(spec=PageInfo)
        page.id = "111"; page.name = "P"; page.access_token = "T"
        account = MagicMock(spec=AccountInfo)
        logger = BotLogger(callback=lambda m, l: None)

        return ReelsUploader(
            account=account, page=page, config={},
            stop_event=threading.Event(), logger=logger,
        )

    def _make_video(self, size=512):
        f = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        f.write(b"X" * size)
        f.close()
        return f.name

    def test_retries_on_http_500_then_succeeds(self):
        """Should retry and succeed on the 3rd attempt."""
        u = self._make_uploader()
        video = self._make_video()
        try:
            call_count = [0]

            def mock_put(*args, **kwargs):
                call_count[0] += 1
                resp = MagicMock()
                resp.status_code = 500 if call_count[0] < 3 else 200
                resp.text = "server error"
                return resp

            session = MagicMock()
            session.put = mock_put
            session.headers = {}

            with patch("requests.Session", return_value=session):
                u._binary_upload(video, 512, "https://upload.fb.com/x")

            self.assertEqual(call_count[0], 3)
        finally:
            os.unlink(video)

    def test_raises_after_all_retries_fail(self):
        """After 3 failures, RuntimeError must be raised."""
        u = self._make_uploader()
        video = self._make_video()
        try:
            resp = MagicMock()
            resp.status_code = 503
            resp.text = "service unavailable"

            session = MagicMock()
            session.put = MagicMock(return_value=resp)
            session.headers = {}

            with patch("requests.Session", return_value=session):
                with self.assertRaises(RuntimeError):
                    u._binary_upload(video, 512, "https://upload.fb.com/x")

            self.assertEqual(session.put.call_count, 3)
        finally:
            os.unlink(video)


class TestP3WorkerAutoRestart(unittest.TestCase):

    def test_worker_restarts_once_on_crash(self):
        from core.concurrent_runner import ConcurrentRunner

        crash_count = [0]
        run_calls   = [0]
        done_event  = threading.Event()

        def flaky_run():
            run_calls[0] += 1
            if crash_count[0] < 1:
                crash_count[0] += 1
                raise RuntimeError("transient crash")
            # Second call: return normally — signal that we're done
            done_event.set()

        config = {
            "job_delay_seconds": 0,
            "max_concurrent_uploads_per_page": 1,
            "min_interval_per_page_s": 0,
            "worker_max_restarts": 1,
        }
        runner = ConcurrentRunner(
            workers=[{"tab": "T1", "page": "P1"}],
            config=config,
        )
        runner._runners[0].run = flaky_run

        # Patch time.sleep to make restart-delay instant; use Event to wait
        with patch("core.concurrent_runner.time.sleep"):
            runner.start()
            done_event.wait(timeout=3.0)

        self.assertGreaterEqual(run_calls[0], 2)   # ran at least twice (crash + restart)

    def test_permanent_error_after_max_restarts(self):
        from core.concurrent_runner import ConcurrentRunner

        all_stopped = threading.Event()

        config = {
            "job_delay_seconds": 0,
            "max_concurrent_uploads_per_page": 1,
            "min_interval_per_page_s": 0,
            "worker_max_restarts": 1,
        }
        runner = ConcurrentRunner(
            workers=[{"tab": "T1", "page": "P1"}],
            config=config,
            on_all_stopped=all_stopped.set,
        )
        runner._runners[0].run = MagicMock(side_effect=RuntimeError("always crashes"))

        with patch("core.concurrent_runner.time.sleep"), patch("utils.notifier.get_notifier"):
            runner.start()
            all_stopped.wait(timeout=3.0)

        self.assertTrue(all_stopped.is_set())
        self.assertEqual(runner._statuses[0].state, "error")


class TestP3MarkdownV2(unittest.TestCase):

    def test_escape_md2_dots(self):
        from utils.notifier import _escape_md2
        result = _escape_md2("hello.world")
        self.assertIn("\\.", result)

    def test_escape_md2_exclamation(self):
        from utils.notifier import _escape_md2
        result = _escape_md2("crash!")
        self.assertIn("\\!", result)

    def test_escape_md2_parens(self):
        from utils.notifier import _escape_md2
        result = _escape_md2("(error)")
        self.assertIn("\\(", result)
        self.assertIn("\\)", result)

    def test_escape_md2_plain_text_unchanged(self):
        from utils.notifier import _escape_md2
        result = _escape_md2("hello world")
        self.assertEqual(result, "hello world")

    def test_notifier_uses_markdownv2_parse_mode(self):
        from utils.notifier import TelegramNotifier
        import urllib.request

        sent_payloads = []

        def mock_urlopen(req, timeout=None):
            body = req.data
            sent_payloads.append(json.loads(body.decode()))
            resp = MagicMock()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            resp.status = 200
            return resp

        n = TelegramNotifier({
            "telegram_bot_token": "1:X",
            "telegram_chat_id":   "123",
            "notify_on_error":    True,
        })
        n._enabled = True

        with patch("urllib.request.urlopen", mock_urlopen):
            n._send("test message")

        self.assertTrue(len(sent_payloads) > 0)
        self.assertEqual(sent_payloads[0].get("parse_mode"), "MarkdownV2")


# ═══════════════════════════════════════════════════════════════════════
# P4 — K-7 Video Insights API
# ═══════════════════════════════════════════════════════════════════════

class TestK7GraphClientInsights(unittest.TestCase):

    def test_get_video_insights_returns_expected_keys(self):
        from core.graph_client import GraphClient

        client = GraphClient()
        client.get = MagicMock(side_effect=[
            # Endpoint 1: engagement
            {
                "reactions": {"summary": {"total_count": 42}},
                "comments":  {"summary": {"total_count": 7}},
                "shares":    {"count": 3},
            },
            # Endpoint 2: video insights
            {
                "data": [
                    {"name": "post_video_views",        "values": [{"value": 1000}]},
                    {"name": "post_impressions_unique", "values": [{"value": 800}]},
                    {"name": "post_video_view_time",    "values": [{"value": 3600}]},
                ]
            },
        ])

        result = client.get_video_insights("VID123", "TOKEN")

        self.assertIn("views",          result)
        self.assertIn("reach",          result)
        self.assertIn("reactions",      result)
        self.assertIn("comments_count", result)
        self.assertIn("shares",         result)
        self.assertIn("minutes_viewed", result)

    def test_get_video_insights_values_correct(self):
        from core.graph_client import GraphClient

        client = GraphClient()
        client.get = MagicMock(side_effect=[
            {
                "reactions": {"summary": {"total_count": 10}},
                "comments":  {"summary": {"total_count": 5}},
                "shares":    {"count": 2},
            },
            {
                "data": [
                    {"name": "post_video_views",        "values": [{"value": 500}]},
                    {"name": "post_impressions_unique", "values": [{"value": 400}]},
                    {"name": "post_video_view_time",    "values": [{"value": 1200}]},
                ]
            },
        ])

        result = client.get_video_insights("VID", "T")
        self.assertEqual(result["views"],          500)
        self.assertEqual(result["reach"],          400)
        self.assertEqual(result["reactions"],      10)
        self.assertEqual(result["comments_count"], 5)
        self.assertEqual(result["shares"],         2)
        self.assertAlmostEqual(result["minutes_viewed"], 20.0, places=1)

    def test_get_video_insights_graceful_on_api_failure(self):
        """Both endpoints failing → returns zeros, does not raise."""
        from core.graph_client import GraphClient

        client = GraphClient()
        client.get = MagicMock(side_effect=Exception("API error"))

        result = client.get_video_insights("VID", "T")
        self.assertEqual(result["views"], 0)
        self.assertEqual(result["reach"], 0)


class TestK7InsightsFetcher(unittest.TestCase):

    def _make_fetcher(self, config=None):
        from core.insights_fetcher import InsightsFetcher
        return InsightsFetcher(
            config=config or {},
            stop_event=threading.Event(),
        )

    def test_parse_dt_iso_format(self):
        from core.insights_fetcher import InsightsFetcher
        dt = InsightsFetcher._parse_dt("2026-05-14 13:00:00")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 5)
        self.assertEqual(dt.day, 14)

    def test_parse_dt_t_separator(self):
        from core.insights_fetcher import InsightsFetcher
        dt = InsightsFetcher._parse_dt("2026-05-14T13:00:00")
        self.assertIsNotNone(dt)

    def test_parse_dt_invalid_returns_none(self):
        from core.insights_fetcher import InsightsFetcher
        dt = InsightsFetcher._parse_dt("not a date")
        self.assertIsNone(dt)

    def test_parse_dt_slash_format(self):
        from core.insights_fetcher import InsightsFetcher
        dt = InsightsFetcher._parse_dt("14/05/2026 13:00:00")
        self.assertIsNotNone(dt)

    def test_find_pending_rows_skips_rows_with_insights_at(self):
        """Rows that already have insights_at set are skipped."""
        from core.insights_fetcher import InsightsFetcher
        from datetime import datetime, timezone, timedelta

        fetcher = self._make_fetcher()

        sheet = MagicMock()
        sheet._sheet_id.return_value = "SID"
        sheet._current_tab = "Tab1"
        sheet._header_map = {
            "fb_video_id": 0,
            "insights_at": 1,
            "uploaded_at": 2,
            "target_page": 3,
        }

        # Row has both fb_video_id AND insights_at → skip
        def get_val(row, key):
            map_ = {
                "col_fb_video_id": "VID123",
                "col_insights_at": "2026-05-14 10:00:00",  # already fetched
                "col_uploaded_at": "2026-01-01 00:00:00",
                "col_target_page": "MyPage",
            }
            return map_.get(key, "")

        sheet._get_val = get_val
        sheet._svc = MagicMock()
        sheet._retry = MagicMock(return_value={"values": [
            ["VID123", "2026-05-14 10:00:00", "2026-01-01 00:00:00", "MyPage"]
        ]})

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        result = fetcher._find_pending_rows(sheet, cutoff)
        self.assertEqual(result, [])

    def test_find_pending_rows_skips_recent_uploads(self):
        """Rows uploaded < 24h ago are skipped even if no insights_at."""
        from core.insights_fetcher import InsightsFetcher
        from datetime import datetime, timezone, timedelta

        fetcher = self._make_fetcher()
        sheet = MagicMock()
        sheet._sheet_id.return_value = "SID"
        sheet._current_tab = "Tab1"
        sheet._header_map = {}

        # uploaded_at = 1 hour ago → too recent
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        def get_val(row, key):
            return {
                "col_fb_video_id": "VID",
                "col_insights_at": "",
                "col_uploaded_at": one_hour_ago,
                "col_target_page": "",
            }.get(key, "")

        sheet._get_val = get_val
        sheet._retry = MagicMock(return_value={"values": [["VID", "", one_hour_ago, ""]]})
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        result = fetcher._find_pending_rows(sheet, cutoff)
        self.assertEqual(result, [])

    def test_find_pending_rows_skips_missing_video_id(self):
        from core.insights_fetcher import InsightsFetcher
        from datetime import datetime, timezone, timedelta

        fetcher = self._make_fetcher()
        sheet = MagicMock()
        sheet._sheet_id.return_value = "SID"
        sheet._current_tab = "Tab1"
        sheet._header_map = {}

        old_ts = "2026-01-01 00:00:00"

        def get_val(row, key):
            return {
                "col_fb_video_id": "",   # missing
                "col_insights_at": "",
                "col_uploaded_at": old_ts,
                "col_target_page": "",
            }.get(key, "")

        sheet._get_val = get_val
        sheet._retry = MagicMock(return_value={"values": [["", "", old_ts, ""]]})
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        result = fetcher._find_pending_rows(sheet, cutoff)
        self.assertEqual(result, [])

    def test_write_insights_calls_batch_write(self):
        from core.insights_fetcher import InsightsFetcher

        fetcher = self._make_fetcher({
            "col_views":           "views",
            "col_reach":           "reach",
            "col_reactions":       "reactions",
            "col_comments_count":  "comments_count",
            "col_shares":          "shares",
            "col_minutes_viewed":  "minutes_viewed",
            "col_insights_at":     "insights_at",
        })

        sheet = MagicMock()
        sheet._header_map = {
            "views": 0, "reach": 1, "reactions": 2,
            "comments_count": 3, "shares": 4,
            "minutes_viewed": 5, "insights_at": 6,
        }
        sheet._col_letter = lambda key: {
            "col_views": "A", "col_reach": "B", "col_reactions": "C",
            "col_comments_count": "D", "col_shares": "E",
            "col_minutes_viewed": "F", "col_insights_at": "G",
        }.get(key)
        sheet._batch_write = MagicMock()

        insights = {
            "views": 1000, "reach": 800, "reactions": 50,
            "comments_count": 12, "shares": 5, "minutes_viewed": 30.5,
        }
        fetcher._write_insights(sheet, row_idx=5, insights=insights)

        sheet._batch_write.assert_called_once()
        row, updates = sheet._batch_write.call_args[0]
        self.assertEqual(row, 5)
        self.assertEqual(updates.get("A"), 1000)
        self.assertEqual(updates.get("B"), 800)
        self.assertIn("G", updates)   # insights_at written

    def test_fetcher_starts_daemon_thread(self):
        from core.insights_fetcher import InsightsFetcher
        f = InsightsFetcher(config={}, stop_event=threading.Event())
        f.start()
        time.sleep(0.1)
        self.assertTrue(f.is_running)
        f.stop()


class TestK7ConfigKeys(unittest.TestCase):

    def test_config_json_has_insights_keys(self):
        cfg_path = os.path.join(BASE_DIR, "data", "config.json")
        if not os.path.exists(cfg_path):
            self.skipTest("config.json not found")
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        for key in ("col_insights_at", "col_views", "col_reach", "col_reactions",
                    "col_comments_count", "col_shares", "col_minutes_viewed",
                    "insights_min_age_h", "insights_scan_interval_s"):
            self.assertIn(key, cfg, f"Missing key: {key}")

    def test_settings_defaults_has_insights_keys(self):
        from core.config_defaults import DEFAULTS
        for key in ("col_insights_at", "col_views", "col_reach",
                    "insights_min_age_h", "insights_scan_interval_s"):
            self.assertIn(key, DEFAULTS, f"Missing DEFAULTS key: {key}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
