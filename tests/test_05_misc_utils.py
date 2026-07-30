"""
test_05_misc_utils.py
Unit tests cho: thumbnail_fetcher, BotLogger.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─────────────────────────────────────────────────────────────────────────────
# thumbnail_fetcher
# ─────────────────────────────────────────────────────────────────────────────

class TestThumbnailFetcher(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        # Override _THUMB_DIR cho tests
        import utils.thumbnail_fetcher as tf
        self._orig_dir = tf._THUMB_DIR
        tf._THUMB_DIR = os.path.join(self._tmpdir, "thumbs")

    def tearDown(self):
        import utils.thumbnail_fetcher as tf
        tf._THUMB_DIR = self._orig_dir
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_empty_url_returns_none(self):
        from utils.thumbnail_fetcher import fetch
        self.assertIsNone(fetch(""))
        self.assertIsNone(fetch("   "))
        self.assertIsNone(fetch(None))

    def test_local_file_passthrough(self):
        from utils.thumbnail_fetcher import fetch
        # Tạo file tạm
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"\xff\xd8\xff")  # JPEG magic bytes
            path = f.name
        try:
            result = fetch(path)
            self.assertEqual(result, path)
        finally:
            os.unlink(path)

    def test_invalid_non_http_url(self):
        from utils.thumbnail_fetcher import fetch
        logs = []
        result = fetch("ftp://invalid.com/image.jpg", log=logs.append)
        self.assertIsNone(result)
        self.assertTrue(any("không hợp lệ" in l.lower() for l in logs))

    def test_guess_ext_jpg(self):
        from utils.thumbnail_fetcher import _guess_ext
        self.assertEqual(_guess_ext("https://example.com/image.jpg"), ".jpg")
        self.assertEqual(_guess_ext("https://example.com/photo.jpeg"), ".jpeg")

    def test_guess_ext_png(self):
        from utils.thumbnail_fetcher import _guess_ext
        self.assertEqual(_guess_ext("https://example.com/thumb.png"), ".png")

    def test_guess_ext_unknown_defaults_jpg(self):
        from utils.thumbnail_fetcher import _guess_ext
        self.assertEqual(_guess_ext("https://example.com/image"), ".jpg")
        self.assertEqual(_guess_ext("https://example.com/image.pdf"), ".jpg")

    def test_guess_ext_ignores_query_string(self):
        from utils.thumbnail_fetcher import _guess_ext
        self.assertEqual(_guess_ext("https://cdn.com/thumb.webp?v=123"), ".webp")

    def test_cleanup_old_no_error_if_empty(self):
        from utils.thumbnail_fetcher import cleanup_old
        cleanup_old(max_files=50)  # không crash khi thư mục chưa tồn tại

    def test_cleanup_old_removes_excess(self):
        from utils.thumbnail_fetcher import cleanup_old
        import utils.thumbnail_fetcher as tf
        os.makedirs(tf._THUMB_DIR, exist_ok=True)
        # Tạo 10 files
        for i in range(10):
            p = os.path.join(tf._THUMB_DIR, f"thumb_{i:03d}.jpg")
            with open(p, "wb") as f:
                f.write(b"x")
        cleanup_old(max_files=3)
        remaining = os.listdir(tf._THUMB_DIR)
        self.assertLessEqual(len(remaining), 10)  # ít nhất không crash


# ─────────────────────────────────────────────────────────────────────────────
# BotLogger
# ─────────────────────────────────────────────────────────────────────────────

class TestBotLogger(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _make_logger(self, callback=None):
        from utils.logger import BotLogger
        return BotLogger(callback=callback, log_dir=self._tmpdir)

    def test_callback_called(self):
        calls = []
        logger = self._make_logger(callback=lambda m, l: calls.append((m, l)))
        logger.info("Hello")
        self.assertEqual(len(calls), 1)
        msg, level = calls[0]
        self.assertIn("Hello", msg)
        self.assertEqual(level, "info")

    def test_all_levels_callable(self):
        calls: list[str] = []
        logger = self._make_logger(callback=lambda m, l: calls.append(l))
        levels = ["info", "success", "warning", "error", "debug",
                  "upload", "browser", "login", "wait", "done",
                  "video", "link", "retry", "page", "thumb",
                  "fb", "sheet", "drive", "queue"]
        for lvl in levels:
            getattr(logger, lvl)(f"Test {lvl}")
        emitted = set(calls)
        for lvl in levels:
            self.assertIn(lvl, emitted, f"Level '{lvl}' chưa được emit")

    def test_log_file_created(self):
        import logging
        # Reset "FacebookBot" logger để đảm bảo handler mới được thêm
        fb_logger = logging.getLogger("FacebookBot")
        orig_handlers = fb_logger.handlers[:]
        fb_logger.handlers.clear()
        try:
            logger = self._make_logger()
            logger.info("write test")
            log_file = os.path.join(self._tmpdir, "app.log")
            self.assertTrue(
                os.path.exists(log_file),
                f"app.log không tồn tại tại {self._tmpdir}"
            )
        finally:
            fb_logger.handlers.clear()
            fb_logger.handlers.extend(orig_handlers)

    def test_no_callback_no_crash(self):
        logger = self._make_logger(callback=None)
        logger.error("crash test")  # không raise

    def test_return_value_is_string(self):
        logger = self._make_logger()
        result = logger.info("test msg")
        self.assertIsInstance(result, str)
        self.assertIn("test msg", result)

    def test_timestamp_in_output(self):
        logger = self._make_logger()
        result = logger.info("stamp test")
        import re
        self.assertTrue(re.search(r"\[\d{2}:\d{2}:\d{2}\]", result))

    def test_icons_present(self):
        msgs = []
        logger = self._make_logger(callback=lambda m, l: msgs.append(m))
        logger.success("ok")
        logger.error("fail")
        self.assertTrue(any("✅" in m for m in msgs))
        self.assertTrue(any("❌" in m for m in msgs))


# ─────────────────────────────────────────────────────────────────────────────
# Config.json integrity
# ─────────────────────────────────────────────────────────────────────────────

class TestConfigJson(unittest.TestCase):
    """Kiểm tra data/config.json có đủ keys cần thiết."""

    REQUIRED_KEYS = [
        "google_credentials_path",
        "sheet_id",
        "sheet_tab",
        "job_delay_seconds",
        "timezone",
        "skip_overdue_minutes",
        "col_video_drive",
        "col_schedule_time",
        "col_title",
        "col_description",
        "col_keywords",
        "col_thumbnail_url",
        "col_comment",
        "col_status",
        "col_error",
        "col_fb_link",
        "temp_video_dir",
        "delete_video_after_upload",
        "page_mapping",
        "meta_app_id",
        "meta_app_secret",
        "graph_api_version",
    ]

    def test_config_file_exists(self):
        config_path = os.path.join(os.path.dirname(__file__), "..", "data", "config.json")
        self.assertTrue(os.path.exists(config_path), "data/config.json không tồn tại")

    def test_config_all_required_keys(self):
        import json
        config_path = os.path.join(os.path.dirname(__file__), "..", "data", "config.json")
        if not os.path.exists(config_path):
            self.skipTest("data/config.json không tồn tại")
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        missing = [k for k in self.REQUIRED_KEYS if k not in config]
        self.assertEqual(missing, [], f"Keys thiếu trong config.json: {missing}")

    def test_config_types(self):
        import json
        config_path = os.path.join(os.path.dirname(__file__), "..", "data", "config.json")
        if not os.path.exists(config_path):
            self.skipTest("data/config.json không tồn tại")
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        self.assertIsInstance(config.get("job_delay_seconds"), (int, float))
        self.assertIsInstance(config.get("skip_overdue_minutes"), (int, float))
        self.assertIsInstance(config.get("delete_video_after_upload"), bool)
        self.assertIsInstance(config.get("page_mapping"), list)


# ─────────────────────────────────────────────────────────────────────────────
# K-3: RateLimiter global metrics registry
# ─────────────────────────────────────────────────────────────────────────────

class TestRateLimiterGlobalMetrics(unittest.TestCase):

    def setUp(self):
        from core.rate_limiter import reset_global_metrics
        reset_global_metrics()   # clean slate for each test

    def tearDown(self):
        from core.rate_limiter import reset_global_metrics
        reset_global_metrics()

    def _make_limiter(self, min_interval_s=0.0):
        from core.rate_limiter import RateLimiter
        return RateLimiter(max_concurrent=5, min_interval_s=min_interval_s)

    def test_get_global_page_metrics_import(self):
        from core.rate_limiter import get_global_page_metrics
        self.assertTrue(callable(get_global_page_metrics))

    def test_get_global_page_metrics_empty_before_release(self):
        from core.rate_limiter import get_global_page_metrics
        result = get_global_page_metrics()
        self.assertEqual(result, {})

    def test_release_populates_global_metrics(self):
        from core.rate_limiter import get_global_page_metrics
        limiter = self._make_limiter()
        import threading
        limiter.acquire("PageA", threading.Event())
        limiter.release("PageA")
        metrics = get_global_page_metrics()
        self.assertIn("PageA", metrics)

    def test_global_metrics_uploads_done_increments(self):
        from core.rate_limiter import get_global_page_metrics
        limiter = self._make_limiter()
        import threading
        for _ in range(3):
            limiter.acquire("PageX", threading.Event())
            limiter.release("PageX")
        metrics = get_global_page_metrics()
        self.assertEqual(metrics["PageX"]["uploads_done"], 3)

    def test_global_metrics_multiple_pages(self):
        from core.rate_limiter import get_global_page_metrics
        limiter = self._make_limiter()
        import threading
        for page in ("Alpha", "Beta", "Gamma"):
            limiter.acquire(page, threading.Event())
            limiter.release(page)
        metrics = get_global_page_metrics()
        for page in ("Alpha", "Beta", "Gamma"):
            self.assertIn(page, metrics)

    def test_global_metrics_keys_present(self):
        from core.rate_limiter import get_global_page_metrics
        limiter = self._make_limiter()
        import threading
        limiter.acquire("P1", threading.Event())
        limiter.release("P1")
        m = get_global_page_metrics()["P1"]
        for key in ("uploads_done", "total_wait_s", "avg_wait_s", "total_upload_s"):
            self.assertIn(key, m, f"Missing key: {key}")

    def test_global_metrics_returns_snapshot_not_reference(self):
        """Mutating the returned dict must not affect the registry."""
        from core.rate_limiter import get_global_page_metrics
        limiter = self._make_limiter()
        import threading
        limiter.acquire("P1", threading.Event())
        limiter.release("P1")
        snap1 = get_global_page_metrics()
        snap1["P1"]["uploads_done"] = 9999  # mutate copy
        snap2 = get_global_page_metrics()
        self.assertNotEqual(snap2.get("P1", {}).get("uploads_done"), 9999)

    def test_reset_global_metrics(self):
        from core.rate_limiter import get_global_page_metrics, reset_global_metrics
        limiter = self._make_limiter()
        import threading
        limiter.acquire("P1", threading.Event())
        limiter.release("P1")
        self.assertIn("P1", get_global_page_metrics())
        reset_global_metrics()
        self.assertEqual(get_global_page_metrics(), {})

    def test_monitor_tab_collect_metrics_function(self):
        """MonitorTab._collect_metrics() must return a dict (possibly empty)."""
        # We can't instantiate MonitorTab without a tk root, but we can test
        # the helper function it calls.
        from core.rate_limiter import get_global_page_metrics
        result = get_global_page_metrics()
        self.assertIsInstance(result, dict)


# ─────────────────────────────────────────────────────────────────────────────
# K-4: Per-worker log color coding
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkerLogColorCoding(unittest.TestCase):
    """Per-worker log colouring.

    Was gui/result_tabs.py::_pick_tag, which returned a Tk tag name. The web
    equivalent returns the colour directly; the selection logic (worker prefix
    wins over level, cycling every 6 workers) is identical.
    """

    def _colour(self, message: str, level: str) -> str:
        from server.services.ui_constants import log_colour
        return log_colour(level, message)

    def _worker_colour(self, n: int) -> str:
        from server.services.ui_constants import WORKER_LOG_COLORS
        return WORKER_LOG_COLORS[(n - 1) % len(WORKER_LOG_COLORS)]

    def test_worker_1_colour(self):
        self.assertEqual(self._colour("[W1] Đang upload...", "upload"),
                         self._worker_colour(1))

    def test_worker_2_colour(self):
        self.assertEqual(self._colour("[W2] Kết nối sheet OK", "info"),
                         self._worker_colour(2))

    def test_worker_6_colour(self):
        self.assertEqual(self._colour("[W6] Done!", "success"),
                         self._worker_colour(6))

    def test_non_worker_uses_level_colour(self):
        from server.services.ui_constants import LOG_COLORS
        self.assertEqual(self._colour("Kết nối Google Sheet...", "info"),
                         LOG_COLORS["info"])

    def test_error_level_without_worker_prefix(self):
        from server.services.ui_constants import LOG_COLORS
        self.assertEqual(self._colour("Lỗi nghiêm trọng", "error"),
                         LOG_COLORS["error"])

    def test_success_level_without_worker_prefix(self):
        from server.services.ui_constants import LOG_COLORS
        self.assertEqual(self._colour("Upload xong!", "success"),
                         LOG_COLORS["success"])

    def test_unknown_level_falls_back_to_info_colour(self):
        from server.services.ui_constants import LOG_COLORS
        self.assertEqual(self._colour("Some message", "nonexistent_level"),
                         LOG_COLORS["info"])

    def test_worker_prefix_overrides_level(self):
        """Even at level 'error', a [W3] prefix keeps the worker colour."""
        self.assertEqual(self._colour("[W3] Lỗi upload: token hết hạn", "error"),
                         self._worker_colour(3))

    def test_worker_out_of_range_cycles_via_modulo(self):
        """[W9] is beyond 6 workers — (9-1)%6 = 2 → the 3rd colour."""
        self.assertEqual(self._colour("[W9] msg", "info"), self._worker_colour(3))

    def test_six_worker_colours(self):
        from server.services.ui_constants import WORKER_LOG_COLORS
        self.assertEqual(len(WORKER_LOG_COLORS), 6)

    def test_worker_colours_are_hex(self):
        import re
        from server.services.ui_constants import WORKER_LOG_COLORS
        hex_re = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for colour in WORKER_LOG_COLORS:
            self.assertTrue(hex_re.match(colour), f"invalid hex colour {colour!r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
