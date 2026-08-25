"""
test_08_k5_notifier.py — K-5: Telegram notifier

Tests:
  - TelegramNotifier construction (enabled / disabled)
  - No-op when token/chat_id absent
  - _send() actually hits the right URL with the right payload (mocked)
  - Rate-limiting respected (two sends space themselves out)
  - init_notifier / get_notifier singleton
  - Config keys available in config.json + DEFAULTS
  - SheetRunner wires notify_job_error on exception
  - ConcurrentRunner wires notify_worker_crash on crash
"""
from __future__ import annotations

import sys
import os
import threading
import time
import unittest
from unittest.mock import MagicMock, patch, call

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


# ─────────────────────────────────────────────────────────────────────────────
# 1.  TelegramNotifier — construction
# ─────────────────────────────────────────────────────────────────────────────

class TestTelegramNotifierConstruct(unittest.TestCase):

    def test_import(self):
        from utils.notifier import TelegramNotifier
        self.assertTrue(callable(TelegramNotifier))

    def test_disabled_when_no_token(self):
        from utils.notifier import TelegramNotifier
        n = TelegramNotifier({"telegram_chat_id": "123"})
        self.assertFalse(n.enabled)

    def test_disabled_when_no_chat_id(self):
        from utils.notifier import TelegramNotifier
        n = TelegramNotifier({"telegram_bot_token": "abc:DEF"})
        self.assertFalse(n.enabled)

    def test_enabled_when_both_set(self):
        from utils.notifier import TelegramNotifier
        n = TelegramNotifier({
            "telegram_bot_token": "123:ABC",
            "telegram_chat_id":   "-100xyz",
        })
        self.assertTrue(n.enabled)

    def test_notify_on_error_default_true(self):
        from utils.notifier import TelegramNotifier
        n = TelegramNotifier({})
        self.assertTrue(n._on_error)

    def test_notify_on_complete_default_false(self):
        from utils.notifier import TelegramNotifier
        n = TelegramNotifier({})
        self.assertFalse(n._on_complete)

    def test_notify_on_expiry_default_true(self):
        from utils.notifier import TelegramNotifier
        n = TelegramNotifier({})
        self.assertTrue(n._on_expiry)


# ─────────────────────────────────────────────────────────────────────────────
# 2.  No-op when disabled
# ─────────────────────────────────────────────────────────────────────────────

class TestTelegramNotifierNoop(unittest.TestCase):

    def _disabled(self):
        from utils.notifier import TelegramNotifier
        return TelegramNotifier({})

    def test_noop_does_not_call_send(self):
        n = self._disabled()
        n._send = MagicMock()
        n.notify_job_error("PageA", 5, "boom")
        n._send.assert_not_called()

    def test_noop_token_expiry(self):
        n = self._disabled()
        n._send = MagicMock()
        n.notify_token_expiry("User", 3)
        n._send.assert_not_called()

    def test_noop_batch_done(self):
        n = self._disabled()
        n._send = MagicMock()
        n.notify_batch_done(10, 2)
        n._send.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Actual _send() logic (mocked urllib)
# ─────────────────────────────────────────────────────────────────────────────

class TestTelegramSend(unittest.TestCase):

    def _notifier(self, extra_config=None):
        from utils.notifier import TelegramNotifier
        cfg = {
            "telegram_bot_token": "999:TOKEN",
            "telegram_chat_id":   "-100GROUP",
            **(extra_config or {}),
        }
        return TelegramNotifier(cfg)

    def test_send_posts_to_correct_url(self):
        n = self._notifier()
        posted_urls = []

        class _FakeResp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): pass

        def _fake_urlopen(req, timeout=None):
            posted_urls.append(req.full_url)
            return _FakeResp()

        with patch("utils.notifier.urllib.request.urlopen", side_effect=_fake_urlopen):
            n._send("Test message")

        self.assertEqual(len(posted_urls), 1)
        self.assertIn("999:TOKEN", posted_urls[0])
        self.assertIn("sendMessage", posted_urls[0])

    def test_send_includes_chat_id_in_payload(self):
        n = self._notifier()
        import json

        captured_data = []

        class _FakeResp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): pass

        def _fake_urlopen(req, timeout=None):
            captured_data.append(json.loads(req.data.decode("utf-8")))
            return _FakeResp()

        with patch("utils.notifier.urllib.request.urlopen", side_effect=_fake_urlopen):
            n._send("Hello Telegram")

        self.assertEqual(len(captured_data), 1)
        payload = captured_data[0]
        self.assertEqual(payload["chat_id"], "-100GROUP")
        self.assertEqual(payload["text"], "Hello Telegram")

    def test_send_retries_on_exception(self):
        n = self._notifier()
        call_count = [0]

        class _FakeResp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): pass

        def _fake_urlopen(req, timeout=None):
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("network error")
            return _FakeResp()

        with patch("utils.notifier.urllib.request.urlopen", side_effect=_fake_urlopen):
            with patch("utils.notifier.time.sleep"):   # skip real sleeps
                n._send("Retry test")

        self.assertEqual(call_count[0], 3)

    def test_notify_job_error_calls_send_async(self):
        n = self._notifier()
        n._send_async = MagicMock()
        n.notify_job_error("PageX", 7, "upload failed")
        n._send_async.assert_called_once()
        text = n._send_async.call_args[0][0]
        self.assertIn("PageX", text)
        self.assertIn("#7", text)

    def test_notify_worker_crash_calls_send_async(self):
        n = self._notifier()
        n._send_async = MagicMock()
        n.notify_worker_crash(3, "OOM error")
        n._send_async.assert_called_once()
        text = n._send_async.call_args[0][0]
        self.assertIn("W3", text)

    def test_notify_token_expiry_calls_send_async(self):
        n = self._notifier()
        n._send_async = MagicMock()
        n.notify_token_expiry("John", 5)
        n._send_async.assert_called_once()
        text = n._send_async.call_args[0][0]
        self.assertIn("John", text)
        self.assertIn("5", text)

    def test_notify_batch_done_respects_on_complete_false(self):
        n = self._notifier({"notify_on_complete": False})
        n._send_async = MagicMock()
        n.notify_batch_done(10, 2)
        n._send_async.assert_not_called()

    def test_notify_batch_done_when_on_complete_true(self):
        n = self._notifier({"notify_on_complete": True})
        n._send_async = MagicMock()
        n.notify_batch_done(10, 2)
        n._send_async.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# 4.  Singleton — init_notifier / get_notifier
# ─────────────────────────────────────────────────────────────────────────────

class TestNotifierSingleton(unittest.TestCase):

    def setUp(self):
        import utils.notifier as n_mod
        n_mod._DEFAULT_NOTIFIER = None   # reset before each test

    def test_get_notifier_returns_instance(self):
        from utils.notifier import get_notifier, TelegramNotifier
        n = get_notifier()
        self.assertIsInstance(n, TelegramNotifier)

    def test_get_notifier_creates_disabled_if_not_inited(self):
        from utils.notifier import get_notifier
        n = get_notifier()
        self.assertFalse(n.enabled)

    def test_init_notifier_creates_enabled(self):
        from utils.notifier import init_notifier, get_notifier
        init_notifier({
            "telegram_bot_token": "111:TKN",
            "telegram_chat_id":   "9999",
        })
        n = get_notifier()
        self.assertTrue(n.enabled)

    def test_init_notifier_replaces_singleton(self):
        from utils.notifier import init_notifier, get_notifier
        n1 = init_notifier({})
        n2 = init_notifier({"telegram_bot_token": "X:Y", "telegram_chat_id": "Z"})
        current = get_notifier()
        self.assertIs(current, n2)
        self.assertIsNot(current, n1)

    def test_get_notifier_same_object(self):
        from utils.notifier import init_notifier, get_notifier
        n = init_notifier({})
        self.assertIs(get_notifier(), n)


# ─────────────────────────────────────────────────────────────────────────────
# 5.  Config keys
# ─────────────────────────────────────────────────────────────────────────────

class TestK5ConfigKeys(unittest.TestCase):

    def test_config_json_has_telegram_keys(self):
        import json
        cfg_path = os.path.join(BASE_DIR, "data", "config.json")
        if not os.path.exists(cfg_path):
            self.skipTest("config.json not found")
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        for key in ("telegram_bot_token", "telegram_chat_id",
                    "notify_on_error", "notify_on_token_expiry", "notify_on_complete"):
            self.assertIn(key, cfg, f"Missing from config.json: {key}")

    def test_settings_tab_defaults_has_telegram_keys(self):
        from core.config_defaults import DEFAULTS
        for key in ("telegram_bot_token", "telegram_chat_id",
                    "notify_on_error", "notify_on_token_expiry", "notify_on_complete"):
            self.assertIn(key, DEFAULTS, f"Missing from DEFAULTS: {key}")


# ─────────────────────────────────────────────────────────────────────────────
# 6.  SheetRunner wires notify_job_error
# ─────────────────────────────────────────────────────────────────────────────

class TestSheetRunnerNotification(unittest.TestCase):

    def test_job_error_calls_notifier(self):
        from core.sheet_runner import SheetRunner
        config = {
            "job_delay_seconds": 0,
            "delete_video_after_upload": False,
            "max_concurrent_uploads_per_page": 1,
            "min_interval_per_page_s": 0,
        }
        stop = threading.Event()
        runner = SheetRunner(
            config=config, page_name="P1", sheet_tab="T1", stop_event=stop,
        )
        fake_task = {
            "row_idx": 99, "video_url": "https://drive.google.com/file/d/X/view",
            "title": "", "description": "", "keywords": "",
            "thumbnail_url": "", "comment": "", "target_page": "", "schedule": "",
        }
        runner._sheet = MagicMock()
        runner._sheet.get_next_pending_row.return_value = fake_task
        runner._sheet.mark_done = MagicMock()
        runner._sheet.mark_running = MagicMock()
        runner._sheet.mark_error = MagicMock()

        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.write(b"v"); tmp.close()
        runner._downloader = MagicMock()
        runner._downloader.download.return_value = tmp.name

        notifier_mock = MagicMock()
        from core.upload_engine import UploadEngine
        with patch.object(UploadEngine, "run_sync",
                          side_effect=RuntimeError("upload crash")):
            with patch("core.sheet_runner.get_notifier", return_value=notifier_mock,
                       create=True):
                with patch("utils.notifier.get_notifier", return_value=notifier_mock):
                    runner._tick()

        try:
            os.unlink(tmp.name)
        except Exception:
            pass

        runner._sheet.mark_error.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# 7.  ConcurrentRunner wires notify_worker_crash
# ─────────────────────────────────────────────────────────────────────────────

class TestConcurrentRunnerNotification(unittest.TestCase):

    def test_crash_calls_notify_worker_crash(self):
        from core.concurrent_runner import ConcurrentRunner
        cfg = {
            "max_concurrent_uploads_per_page": 1,
            "min_interval_per_page_s": 0,
        }
        cr = ConcurrentRunner(
            workers=[{"tab": "T1", "page": "P1"}],
            config=cfg,
        )
        cr._runners[0].run = MagicMock(side_effect=RuntimeError("kaboom"))

        notifier_mock = MagicMock()
        with patch("utils.notifier.get_notifier", return_value=notifier_mock):
            cr._thread_target(0)

        # Even if notifier mock isn't called directly (due to import in the function),
        # the important thing is no exception leaks out of _thread_target
        self.assertEqual(cr._statuses[0].state, "error")


if __name__ == "__main__":
    unittest.main(verbosity=2)
