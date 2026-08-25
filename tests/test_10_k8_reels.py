"""
test_10_k8_reels.py — K-8: Facebook Reels upload support

Tests:
  - ReelsUploader construction
  - upload() return type (video_url, video_id)
  - _start_session() extracts upload_url + video_id from API response
  - _start_session() raises if upload_url missing
  - _binary_upload() sends PUT with correct headers (offset, file_size, auth)
  - _binary_upload() raises on HTTP != 200/201
  - _finish_session() sends correct metadata (description, video_state)
  - _finish_session() schedules future post (video_state=SCHEDULED)
  - _finish_session() publishes immediately for past/empty schedule
  - upload() raises FileNotFoundError for missing video
  - upload() raises ValueError for empty video file
  - UploadEngine._run_api() routes "reels" → ReelsUploader
  - UploadEngine._run_api() routes "feed" → GraphUploader
  - UploadEngine._run_api() routes "" → GraphUploader (default)
  - UploadEngine._run_api() does NOT post comment for Reels
  - UploadEngine._run_api() posts comment for feed videos
  - col_post_type present in config.json
  - col_post_type present in settings_tab.DEFAULTS
  - get_next_pending_row() includes post_type field (defaults to "feed")
  - get_next_pending_row() reads post_type from col_post_type column
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch, call

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_stop():
    return threading.Event()


def _make_reels_uploader(config=None, page_access_token="PAGE_TOKEN"):
    from core.reels_uploader import ReelsUploader
    from core.token_store import AccountInfo, PageInfo

    account = MagicMock(spec=AccountInfo)
    account.user_token = "USER_TOKEN"

    page = MagicMock(spec=PageInfo)
    page.id = "1234567890"
    page.name = "TestPage"
    page.access_token = page_access_token

    cfg = config or {
        "graph_api_version": "v21.0",
        "temp_video_dir": "temp_videos",
    }

    from utils.logger import BotLogger
    logger = BotLogger(callback=lambda msg, lvl: None)

    return ReelsUploader(
        account=account,
        page=page,
        config=cfg,
        stop_event=_make_stop(),
        logger=logger,
        on_status=lambda m: None,
        on_progress=lambda done, total: None,
    )


def _make_video_file(size_bytes=1024):
    """Create a real temp file for upload tests."""
    f = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    f.write(b"X" * size_bytes)
    f.close()
    return f.name


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Construction
# ─────────────────────────────────────────────────────────────────────────────

class TestReelsUploaderConstruction(unittest.TestCase):

    def test_init_stores_page(self):
        u = _make_reels_uploader()
        self.assertEqual(u.page.id, "1234567890")

    def test_init_stores_config(self):
        cfg = {"graph_api_version": "v20.0"}
        u = _make_reels_uploader(config=cfg)
        self.assertEqual(u.config, cfg)

    def test_init_creates_graph_client(self):
        u = _make_reels_uploader()
        from core.graph_client import GraphClient
        self.assertIsInstance(u._client, GraphClient)

    def test_on_status_defaults_to_noop(self):
        from core.reels_uploader import ReelsUploader
        from core.token_store import AccountInfo, PageInfo
        from utils.logger import BotLogger

        page = MagicMock(spec=PageInfo)
        page.id = "1"; page.name = "P"; page.access_token = "T"
        account = MagicMock(spec=AccountInfo)
        logger = BotLogger(callback=lambda m, l: None)

        # Should not raise even without on_status/on_progress
        u = ReelsUploader(
            account=account, page=page,
            config={}, stop_event=_make_stop(), logger=logger,
        )
        u.on_status("hello")   # noop, no exception
        u.on_progress(0, 100)  # noop, no exception


# ─────────────────────────────────────────────────────────────────────────────
# 2.  _start_session()
# ─────────────────────────────────────────────────────────────────────────────

class TestStartSession(unittest.TestCase):

    def setUp(self):
        self.u = _make_reels_uploader()

    def test_returns_upload_url_and_video_id(self):
        self.u._client.post = MagicMock(return_value={
            "upload_url": "https://rupload.facebook.com/xyz",
            "video_id": "9876543210",
        })
        url, vid = self.u._start_session({"title": "My Reel", "video_path": "x.mp4"})
        self.assertEqual(url, "https://rupload.facebook.com/xyz")
        self.assertEqual(vid, "9876543210")

    def test_raises_if_upload_url_missing(self):
        self.u._client.post = MagicMock(return_value={"video_id": "123"})
        with self.assertRaises(RuntimeError):
            self.u._start_session({"title": "", "video_path": "x.mp4"})

    def test_calls_correct_endpoint(self):
        self.u._client.post = MagicMock(return_value={
            "upload_url": "https://rupload.fb.com/abc",
            "video_id": "111",
        })
        self.u._start_session({"title": "T", "video_path": "v.mp4"})
        endpoint = self.u._client.post.call_args[0][0]
        self.assertIn("video_reels", endpoint)
        self.assertIn(self.u.page.id, endpoint)

    def test_sends_upload_phase_start(self):
        self.u._client.post = MagicMock(return_value={
            "upload_url": "https://rupload.fb.com/xyz",
            "video_id": "222",
        })
        self.u._start_session({"title": "T", "video_path": "v.mp4"})
        data = self.u._client.post.call_args[1].get("data") or \
               self.u._client.post.call_args[0][1] if len(self.u._client.post.call_args[0]) > 1 \
               else self.u._client.post.call_args[1].get("data", {})
        # Check via call_args
        kwargs = self.u._client.post.call_args[1]
        data_sent = kwargs.get("data", {})
        self.assertEqual(data_sent.get("upload_phase"), "start")

    def test_uses_page_access_token(self):
        self.u._client.post = MagicMock(return_value={
            "upload_url": "https://rupload.fb.com/xyz",
            "video_id": "333",
        })
        self.u._start_session({"title": "T", "video_path": "v.mp4"})
        kwargs = self.u._client.post.call_args[1]
        self.assertEqual(kwargs.get("token"), self.u.page.access_token)

    def test_uses_filename_as_clip_title_when_title_empty(self):
        self.u._client.post = MagicMock(return_value={
            "upload_url": "https://rupload.fb.com/x",
            "video_id": "444",
        })
        self.u._start_session({"title": "", "video_path": "/tmp/my_video.mp4"})
        kwargs = self.u._client.post.call_args[1]
        data = kwargs.get("data", {})
        self.assertEqual(data.get("clip_title"), "my_video")


# ─────────────────────────────────────────────────────────────────────────────
# 3.  _binary_upload()
# ─────────────────────────────────────────────────────────────────────────────

class TestBinaryUpload(unittest.TestCase):

    def setUp(self):
        self.u = _make_reels_uploader()
        self.video_path = _make_video_file(1024)

    def tearDown(self):
        try:
            os.unlink(self.video_path)
        except Exception:
            pass

    def _mock_put(self, status_code=200):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = ""
        session = MagicMock()
        session.put = MagicMock(return_value=resp)
        return session

    def test_put_called_with_correct_url(self):
        import requests
        session = self._mock_put()
        with patch("requests.Session", return_value=session):
            self.u._binary_upload(self.video_path, 1024, "https://upload.fb.com/x")
        session.put.assert_called()
        url_used = session.put.call_args[0][0]
        self.assertEqual(url_used, "https://upload.fb.com/x")

    def test_put_headers_contain_authorization(self):
        session = self._mock_put()
        with patch("requests.Session", return_value=session):
            self.u._binary_upload(self.video_path, 1024, "https://upload.fb.com/x")
        headers = session.put.call_args[1].get("headers", {})
        self.assertIn("Authorization", headers)
        self.assertIn("PAGE_TOKEN", headers["Authorization"])

    def test_put_headers_contain_file_size(self):
        session = self._mock_put()
        with patch("requests.Session", return_value=session):
            self.u._binary_upload(self.video_path, 1024, "https://upload.fb.com/x")
        headers = session.put.call_args[1].get("headers", {})
        self.assertEqual(headers.get("file_size"), "1024")

    def test_put_headers_first_chunk_offset_zero(self):
        session = self._mock_put()
        with patch("requests.Session", return_value=session):
            self.u._binary_upload(self.video_path, 1024, "https://upload.fb.com/x")
        # First call (only one chunk for 1024-byte file)
        headers = session.put.call_args_list[0][1].get("headers", {})
        self.assertEqual(headers.get("offset"), "0")

    def test_put_headers_content_type_octet_stream(self):
        session = self._mock_put()
        with patch("requests.Session", return_value=session):
            self.u._binary_upload(self.video_path, 1024, "https://upload.fb.com/x")
        headers = session.put.call_args[1].get("headers", {})
        self.assertEqual(headers.get("Content-Type"), "application/octet-stream")

    def test_raises_on_http_error(self):
        session = self._mock_put(status_code=500)
        with patch("requests.Session", return_value=session):
            with self.assertRaises(RuntimeError):
                self.u._binary_upload(self.video_path, 1024, "https://upload.fb.com/x")

    def test_multiple_chunks_for_large_file(self):
        """File larger than _CHUNK_SIZE should produce multiple PUT calls."""
        from core.reels_uploader import _CHUNK_SIZE
        large_path = _make_video_file(_CHUNK_SIZE + 1)
        try:
            session = self._mock_put()
            with patch("requests.Session", return_value=session):
                self.u._binary_upload(large_path, _CHUNK_SIZE + 1, "https://upload.fb.com/x")
            self.assertEqual(session.put.call_count, 2)
        finally:
            os.unlink(large_path)


# ─────────────────────────────────────────────────────────────────────────────
# 4.  _finish_session()
# ─────────────────────────────────────────────────────────────────────────────

class TestFinishSession(unittest.TestCase):

    def setUp(self):
        self.u = _make_reels_uploader()
        self.u._client.post = MagicMock(return_value={"success": True})

    def test_sends_finish_phase(self):
        self.u._finish_session("VID123", {"description": "", "keywords": "", "schedule": ""})
        kwargs = self.u._client.post.call_args[1]
        self.assertEqual(kwargs.get("data", {}).get("upload_phase"), "finish")

    def test_sends_video_id(self):
        self.u._finish_session("VID456", {"description": "", "keywords": "", "schedule": ""})
        kwargs = self.u._client.post.call_args[1]
        self.assertEqual(kwargs.get("data", {}).get("video_id"), "VID456")

    def test_published_state_when_no_schedule(self):
        self.u._finish_session("VID", {"description": "", "keywords": "", "schedule": ""})
        kwargs = self.u._client.post.call_args[1]
        self.assertEqual(kwargs.get("data", {}).get("video_state"), "PUBLISHED")

    def test_scheduled_state_for_future_schedule(self):
        future = time.strftime("%Y-%m-%d %H:%M:%S",
                               time.localtime(time.time() + 3600))
        self.u._finish_session("VID", {"description": "", "keywords": "", "schedule": future})
        kwargs = self.u._client.post.call_args[1]
        data = kwargs.get("data", {})
        self.assertEqual(data.get("video_state"), "SCHEDULED")
        self.assertIn("scheduled_publish_time", data)

    def test_published_state_for_past_schedule(self):
        past = "2020-01-01 00:00:00"
        self.u._finish_session("VID", {"description": "", "keywords": "", "schedule": past})
        kwargs = self.u._client.post.call_args[1]
        self.assertEqual(kwargs.get("data", {}).get("video_state"), "PUBLISHED")

    def test_description_included_when_provided(self):
        self.u._finish_session("VID", {
            "description": "My Reel description",
            "keywords": "",
            "schedule": "",
        })
        kwargs = self.u._client.post.call_args[1]
        self.assertIn("My Reel description", kwargs.get("data", {}).get("description", ""))

    def test_keywords_appended_to_description(self):
        self.u._finish_session("VID", {
            "description": "Desc",
            "keywords": "tag1 tag2",
            "schedule": "",
        })
        kwargs = self.u._client.post.call_args[1]
        desc = kwargs.get("data", {}).get("description", "")
        self.assertIn("tag1", desc)

    def test_no_description_field_when_empty(self):
        self.u._finish_session("VID", {"description": "", "keywords": "", "schedule": ""})
        kwargs = self.u._client.post.call_args[1]
        self.assertNotIn("description", kwargs.get("data", {}))

    def test_uses_page_access_token(self):
        self.u._finish_session("VID", {"description": "", "keywords": "", "schedule": ""})
        kwargs = self.u._client.post.call_args[1]
        self.assertEqual(kwargs.get("token"), self.u.page.access_token)


# ─────────────────────────────────────────────────────────────────────────────
# 5.  upload() — full flow
# ─────────────────────────────────────────────────────────────────────────────

class TestReelsUploaderUpload(unittest.TestCase):

    def _make_uploader_with_mocked_phases(self):
        u = _make_reels_uploader()
        u._start_session = MagicMock(return_value=("https://rupload.fb.com/xyz", "VID999"))
        u._binary_upload = MagicMock()
        u._finish_session = MagicMock()
        return u

    def test_upload_returns_tuple(self):
        u = self._make_uploader_with_mocked_phases()
        video = _make_video_file(512)
        try:
            result = u.upload({"video_path": video, "title": "T",
                               "description": "", "keywords": "", "schedule": ""})
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 2)
        finally:
            os.unlink(video)

    def test_upload_video_url_contains_page_and_video_id(self):
        u = self._make_uploader_with_mocked_phases()
        video = _make_video_file(512)
        try:
            url, vid = u.upload({"video_path": video, "title": "T",
                                  "description": "", "keywords": "", "schedule": ""})
            self.assertIn("1234567890", url)   # page.id
            self.assertIn("VID999", url)       # video_id from start_session
            self.assertEqual(vid, "VID999")
        finally:
            os.unlink(video)

    def test_upload_raises_file_not_found(self):
        u = self._make_uploader_with_mocked_phases()
        with self.assertRaises(FileNotFoundError):
            u.upload({"video_path": "/nonexistent/path/video.mp4",
                      "title": "", "description": "", "keywords": "", "schedule": ""})

    def test_upload_raises_value_error_for_empty_file(self):
        u = self._make_uploader_with_mocked_phases()
        empty = _make_video_file(0)
        try:
            with self.assertRaises(ValueError):
                u.upload({"video_path": empty, "title": "",
                           "description": "", "keywords": "", "schedule": ""})
        finally:
            os.unlink(empty)

    def test_upload_calls_all_three_phases(self):
        u = self._make_uploader_with_mocked_phases()
        video = _make_video_file(512)
        try:
            u.upload({"video_path": video, "title": "T",
                      "description": "", "keywords": "", "schedule": ""})
            u._start_session.assert_called_once()
            u._binary_upload.assert_called_once()
            u._finish_session.assert_called_once()
        finally:
            os.unlink(video)

    def test_upload_passes_task_to_finish_session(self):
        u = self._make_uploader_with_mocked_phases()
        video = _make_video_file(256)
        task = {"video_path": video, "title": "T", "description": "D",
                "keywords": "kw", "schedule": ""}
        try:
            u.upload(task)
            finish_args = u._finish_session.call_args[0]
            # finish_session(video_id, task)
            self.assertEqual(finish_args[0], "VID999")
            self.assertEqual(finish_args[1], task)
        finally:
            os.unlink(video)


# ─────────────────────────────────────────────────────────────────────────────
# 6.  UploadEngine routing by post_type
# ─────────────────────────────────────────────────────────────────────────────

def _make_engine():
    from core.upload_engine import UploadEngine
    config = {
        "graph_api_version": "v21.0",
        "temp_video_dir": "temp_videos",
        "min_interval_per_page_s": 0,
        "max_concurrent_uploads_per_page": 1,
        "fb_comment_enabled": True,
    }
    return UploadEngine(
        config=config,
        stop_event=_make_stop(),
        on_log=lambda m, l: None,
        on_status=lambda m: None,
        on_result=lambda task, status, link: None,
        on_done=lambda: None,
        on_error=lambda m: None,
    )


def _make_account_page():
    from core.token_store import AccountInfo, PageInfo
    account = MagicMock(spec=AccountInfo)
    account.is_token_valid.return_value = True

    page = MagicMock(spec=PageInfo)
    page.id = "1234567890"
    page.name = "TestPage"
    page.access_token = "TOKEN"
    return account, page


class TestUploadEngineRouting(unittest.TestCase):

    def test_reels_post_type_uses_reels_uploader(self):
        engine = _make_engine()
        account, page = _make_account_page()

        with patch("core.reels_uploader.ReelsUploader") as MockReels, \
             patch("core.graph_uploader.GraphUploader"):
            mock_instance = MagicMock()
            mock_instance.upload.return_value = ("https://fb.com/v/X", "X")
            MockReels.return_value = mock_instance

            task = {"post_type": "reels", "comment": ""}
            engine._run_api(task, account, page)

            MockReels.assert_called_once()

    def test_feed_post_type_uses_graph_uploader(self):
        engine = _make_engine()
        account, page = _make_account_page()

        with patch("core.graph_uploader.GraphUploader") as MockGraph, \
             patch("core.reels_uploader.ReelsUploader"):
            mock_instance = MagicMock()
            mock_instance.upload.return_value = ("https://fb.com/v/Y", "Y")
            MockGraph.return_value = mock_instance

            task = {"post_type": "feed", "comment": ""}
            engine._run_api(task, account, page)

            MockGraph.assert_called_once()

    def test_empty_post_type_defaults_to_graph_uploader(self):
        engine = _make_engine()
        account, page = _make_account_page()

        with patch("core.graph_uploader.GraphUploader") as MockGraph, \
             patch("core.reels_uploader.ReelsUploader"):
            mock_instance = MagicMock()
            mock_instance.upload.return_value = ("https://fb.com/v/Z", "Z")
            MockGraph.return_value = mock_instance

            task = {"comment": ""}   # no post_type key
            engine._run_api(task, account, page)

            MockGraph.assert_called_once()

    def test_reels_does_not_post_comment(self):
        engine = _make_engine()
        account, page = _make_account_page()

        with patch("core.reels_uploader.ReelsUploader") as MockReels:
            mock_instance = MagicMock()
            mock_instance.upload.return_value = ("https://fb.com/v/R", "R")
            MockReels.return_value = mock_instance

            task = {"post_type": "reels", "comment": "Hello World"}
            engine._run_api(task, account, page)

            # post_comment should NOT be called on a ReelsUploader
            mock_instance.post_comment.assert_not_called()

    def test_feed_posts_comment_when_provided(self):
        engine = _make_engine()
        account, page = _make_account_page()

        with patch("core.graph_uploader.GraphUploader") as MockGraph:
            mock_instance = MagicMock()
            mock_instance.upload.return_value = ("https://fb.com/v/F", "F")
            MockGraph.return_value = mock_instance

            task = {"post_type": "feed", "comment": "Test comment"}
            engine._run_api(task, account, page)

            mock_instance.post_comment.assert_called_once_with("F", "Test comment")

    def test_feed_does_not_post_empty_comment(self):
        engine = _make_engine()
        account, page = _make_account_page()

        with patch("core.graph_uploader.GraphUploader") as MockGraph:
            mock_instance = MagicMock()
            mock_instance.upload.return_value = ("https://fb.com/v/G", "G")
            MockGraph.return_value = mock_instance

            task = {"post_type": "feed", "comment": ""}
            engine._run_api(task, account, page)

            mock_instance.post_comment.assert_not_called()

    def test_run_api_returns_tuple(self):
        engine = _make_engine()
        account, page = _make_account_page()

        with patch("core.graph_uploader.GraphUploader") as MockGraph:
            mock_instance = MagicMock()
            mock_instance.upload.return_value = ("https://fb.com/v/H", "H")
            MockGraph.return_value = mock_instance

            result = engine._run_api({"post_type": "feed", "comment": ""}, account, page)
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0], "https://fb.com/v/H")
            self.assertEqual(result[1], "H")

    def test_reels_uppercase_normalized(self):
        """'REELS' should still route to ReelsUploader."""
        engine = _make_engine()
        account, page = _make_account_page()

        with patch("core.reels_uploader.ReelsUploader") as MockReels:
            mock_instance = MagicMock()
            mock_instance.upload.return_value = ("https://fb.com/v/RL", "RL")
            MockReels.return_value = mock_instance

            task = {"post_type": "REELS", "comment": ""}
            engine._run_api(task, account, page)

            MockReels.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# 7.  Config / DEFAULTS coverage
# ─────────────────────────────────────────────────────────────────────────────

class TestK8ConfigKeys(unittest.TestCase):

    def test_config_json_has_col_post_type(self):
        import json
        cfg_path = os.path.join(BASE_DIR, "data", "config.json")
        if not os.path.exists(cfg_path):
            self.skipTest("config.json not found")
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertIn("col_post_type", cfg)

    def test_col_post_type_default_value(self):
        import json
        cfg_path = os.path.join(BASE_DIR, "data", "config.json")
        if not os.path.exists(cfg_path):
            self.skipTest("config.json not found")
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertIsInstance(cfg["col_post_type"], str)

    def test_settings_tab_defaults_has_col_post_type(self):
        from core.config_defaults import DEFAULTS
        self.assertIn("col_post_type", DEFAULTS)

    def test_settings_tab_col_post_type_is_string(self):
        from core.config_defaults import DEFAULTS
        self.assertIsInstance(DEFAULTS["col_post_type"], str)


# ─────────────────────────────────────────────────────────────────────────────
# 8.  get_next_pending_row() — post_type field
# ─────────────────────────────────────────────────────────────────────────────

class TestSheetClientPostType(unittest.TestCase):

    def _make_client(self, header, col_post_type_name="post_type"):
        from utils.sheet_client import SheetClient
        cfg = {
            "sheet_id": "SID",
            "sheet_tab": "Tab1",
            "col_status": "status",
            "col_video_drive": "video",
            "col_post_type": col_post_type_name,
            "col_schedule_time": "schedule_time",
        }
        client = SheetClient(cfg)
        client._header_map = {h: i for i, h in enumerate(header)}
        client._current_tab = "Tab1"
        client._refresh_header_map = MagicMock()
        client._get_tz = MagicMock(
            return_value=__import__("zoneinfo").ZoneInfo("UTC")
        )
        return client

    @staticmethod
    def _due():
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    def test_post_type_defaults_to_feed_when_col_absent(self):
        """If col_post_type column doesn't exist in header, default = 'feed'."""
        client = self._make_client(
            ["status", "video", "schedule_time"]
        )   # no post_type column
        rows = [["", "https://drive.google.com/X", self._due()]]
        client._retry = MagicMock(return_value={"values": rows})

        task = client.get_next_pending_row()
        self.assertIsNotNone(task)
        self.assertEqual(task.get("post_type"), "feed")

    def test_post_type_read_from_column(self):
        """When col_post_type column exists and has 'reels', task should have 'reels'."""
        client = self._make_client(
            ["status", "video", "post_type", "schedule_time"]
        )
        rows = [["", "https://drive.google.com/X", "reels", self._due()]]
        client._retry = MagicMock(return_value={"values": rows})

        task = client.get_next_pending_row()
        self.assertIsNotNone(task)
        self.assertEqual(task.get("post_type"), "reels")

    def test_post_type_feed_from_column(self):
        """When col_post_type column has 'feed', task should have 'feed'."""
        client = self._make_client(
            ["status", "video", "post_type", "schedule_time"]
        )
        rows = [["", "https://drive.google.com/X", "feed", self._due()]]
        client._retry = MagicMock(return_value={"values": rows})

        task = client.get_next_pending_row()
        self.assertIsNotNone(task)
        self.assertEqual(task.get("post_type"), "feed")

    def test_empty_post_type_column_defaults_to_feed(self):
        """When col_post_type column exists but cell is blank, default = 'feed'."""
        client = self._make_client(
            ["status", "video", "post_type", "schedule_time"]
        )
        rows = [["", "https://drive.google.com/X", "", self._due()]]
        client._retry = MagicMock(return_value={"values": rows})

        task = client.get_next_pending_row()
        self.assertIsNotNone(task)
        self.assertEqual(task.get("post_type"), "feed")

    def test_post_type_in_returned_task_dict(self):
        """post_type is always present in the returned task dict."""
        client = self._make_client(["status", "video", "schedule_time"])
        rows = [["", "https://drive.google.com/X", self._due()]]
        client._retry = MagicMock(return_value={"values": rows})

        task = client.get_next_pending_row()
        self.assertIn("post_type", task)


if __name__ == "__main__":
    unittest.main(verbosity=2)
