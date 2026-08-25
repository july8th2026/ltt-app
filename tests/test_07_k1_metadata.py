"""
test_07_k1_metadata.py — K-1: Metadata writeback
Tests:
  - GraphUploader.upload() returns tuple[str, str]
  - UploadEngine._run_api() / run_sync() propagate tuple
  - SheetClient.mark_done() accepts fb_video_id / uploaded_at / duration_s
  - SheetRunner._tick() captures timing + video_id and passes to mark_done
"""
from __future__ import annotations

import sys
import os
import threading
import types
import unittest
from unittest.mock import MagicMock, patch, call

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


# ─────────────────────────────────────────────────────────────────────────────
# 1.  GraphUploader.upload() signature & return type
# ─────────────────────────────────────────────────────────────────────────────

class TestGraphUploaderReturnTuple(unittest.TestCase):
    """upload() must return (video_url: str, video_id: str)."""

    def _make_uploader(self):
        from core.graph_uploader import GraphUploader
        from core.token_store import AccountInfo, PageInfo

        account = AccountInfo(
            fb_user_id="U1", name="User", user_token="tok",
            token_expires_at="", pages=[], connected_at="",
        )
        page = PageInfo(id="PAGE1", name="Test Page", access_token="page_tok")
        stop = threading.Event()
        logger = MagicMock()
        logger.upload = MagicMock()
        logger.success = MagicMock()
        logger.warning = MagicMock()
        logger.thumb = MagicMock()

        uploader = GraphUploader(
            account=account, page=page,
            config={"verify_video_after_upload": False},
            stop_event=stop, logger=logger,
        )
        return uploader, page

    def test_upload_returns_tuple(self):
        uploader, page = self._make_uploader()

        # Patch all 3 upload phases + _wait_for_video_ready
        uploader._start_session = MagicMock(return_value=("sess1", "vid_start"))
        uploader._transfer_chunks = MagicMock()
        uploader._finish_session = MagicMock(return_value={"video_id": "vid_finish"})
        uploader._wait_for_video_ready = MagicMock()

        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake_video_data")
            tmp = f.name
        try:
            result = uploader.upload({"video_path": tmp, "title": "T"})
        finally:
            os.unlink(tmp)

        self.assertIsInstance(result, tuple, "upload() must return a tuple")
        self.assertEqual(len(result), 2, "tuple must have 2 elements")
        video_url, video_id = result
        self.assertIsInstance(video_url, str)
        self.assertIsInstance(video_id, str)

    def test_upload_url_and_id_correct(self):
        uploader, page = self._make_uploader()

        uploader._start_session = MagicMock(return_value=("sess1", "vid_start"))
        uploader._transfer_chunks = MagicMock()
        uploader._finish_session = MagicMock(return_value={"video_id": "7777777"})
        uploader._wait_for_video_ready = MagicMock()

        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"x")
            tmp = f.name
        try:
            video_url, video_id = uploader.upload({"video_path": tmp})
        finally:
            os.unlink(tmp)

        self.assertEqual(video_id, "7777777")
        self.assertIn("7777777", video_url)
        self.assertIn(page.id, video_url)

    def test_upload_fallback_video_id_from_start(self):
        """If finish phase returns no video_id, fall back to id from start phase."""
        uploader, page = self._make_uploader()

        uploader._start_session = MagicMock(return_value=("sess1", "vid_from_start"))
        uploader._transfer_chunks = MagicMock()
        uploader._finish_session = MagicMock(return_value={})  # no video_id
        uploader._wait_for_video_ready = MagicMock()

        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"x")
            tmp = f.name
        try:
            video_url, video_id = uploader.upload({"video_path": tmp})
        finally:
            os.unlink(tmp)

        self.assertEqual(video_id, "vid_from_start")

    def test_upload_empty_file_raises(self):
        uploader, _ = self._make_uploader()
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            tmp = f.name  # empty file
        try:
            with self.assertRaises(ValueError):
                uploader.upload({"video_path": tmp})
        finally:
            os.unlink(tmp)

    def test_upload_missing_file_raises(self):
        uploader, _ = self._make_uploader()
        with self.assertRaises(FileNotFoundError):
            uploader.upload({"video_path": "/nonexistent/video.mp4"})


# ─────────────────────────────────────────────────────────────────────────────
# 2.  UploadEngine.run_sync() returns tuple
# ─────────────────────────────────────────────────────────────────────────────

class TestUploadEngineRunSyncTuple(unittest.TestCase):

    def _make_engine(self):
        from core.upload_engine import UploadEngine
        stop = threading.Event()
        return UploadEngine(
            config={"fb_comment_enabled": True}, stop_event=stop,
            on_log=lambda m, l: None,
            on_status=lambda m: None,
            on_result=lambda t, s, lnk: None,
            on_done=lambda: None,
            on_error=lambda msg: None,
        )

    def test_run_sync_return_annotation(self):
        import inspect
        from core.upload_engine import UploadEngine
        hints = UploadEngine.run_sync.__annotations__
        ret = hints.get("return", "")
        # Should be tuple[str, str] or similar
        self.assertTrue(
            "tuple" in str(ret).lower() or ret == "str",
            f"Unexpected return annotation: {ret}"
        )

    def test_run_inner_propagates_tuple(self):
        engine = self._make_engine()

        # Patch _run_api to return a known tuple
        engine._run_api = MagicMock(return_value=("https://fb.com/vid/123", "123"))

        # Patch TokenStore so _run_inner doesn't need real creds
        from core.token_store import AccountInfo, PageInfo
        mock_acc = AccountInfo(
            fb_user_id="U1", name="U", user_token="t",
            token_expires_at="", pages=[], connected_at="",
        )
        mock_page = PageInfo(id="P1", name="PageA", access_token="tok")

        # BUG-07 fix: upload_engine now uses get_default_store() singleton
        with patch("core.upload_engine.get_default_store") as mock_get_store:
            instance = MagicMock()
            instance.find_page_by_name.return_value = (mock_acc, mock_page)
            mock_get_store.return_value = instance
            result = engine.run_sync({"page": "PageA", "video_path": "x.mp4"})

        self.assertIsInstance(result, tuple)
        url, vid_id = result
        self.assertEqual(url, "https://fb.com/vid/123")
        self.assertEqual(vid_id, "123")

    def test_run_api_unpacks_uploader_tuple(self):
        """_run_api must unpack (url, id) from GraphUploader.upload()."""
        engine = self._make_engine()

        from core.token_store import AccountInfo, PageInfo
        acc = AccountInfo(fb_user_id="U1", name="U", user_token="t",
                          token_expires_at="", pages=[], connected_at="")
        page = PageInfo(id="P1", name="P1", access_token="tok")

        mock_uploader = MagicMock()
        mock_uploader.upload.return_value = ("https://fb.com/v/9999", "9999")

        # GraphUploader is a local import inside _run_api — patch at source module
        with patch("core.graph_uploader.GraphUploader", return_value=mock_uploader):
            result = engine._run_api({"title": "t"}, acc, page)

        self.assertIsInstance(result, tuple)
        self.assertEqual(result, ("https://fb.com/v/9999", "9999"))

    def test_run_api_comment_uses_video_id_directly(self):
        """post_comment must use video_id from upload(), not re-parse from URL."""
        engine = self._make_engine()

        from core.token_store import AccountInfo, PageInfo
        acc = AccountInfo(fb_user_id="U1", name="U", user_token="t",
                          token_expires_at="", pages=[], connected_at="")
        page = PageInfo(id="P1", name="P1", access_token="tok")

        mock_uploader = MagicMock()
        mock_uploader.upload.return_value = ("https://fb.com/v/DIRECT_ID", "DIRECT_ID")

        # GraphUploader is a local import inside _run_api — patch at source module
        with patch("core.graph_uploader.GraphUploader", return_value=mock_uploader):
            engine._run_api({"title": "t", "comment": "Hi!"}, acc, page)

        # Verify post_comment was called with the exact id returned by upload()
        mock_uploader.post_comment.assert_called_once_with("DIRECT_ID", "Hi!")


# ─────────────────────────────────────────────────────────────────────────────
# 3.  SheetClient.mark_done() keyword params
# ─────────────────────────────────────────────────────────────────────────────

class TestSheetClientMarkDone(unittest.TestCase):

    def _make_client(self, extra_config: dict = None):
        from utils.sheet_client import SheetClient
        config = {
            "sheet_id":         "SID",
            "sheet_tab":        "Tab1",
            "col_status":       "status",
            "col_fb_link":      "VIDEO_URL",
            "col_error":        "error_message",
            "col_fb_video_id":  "fb_video_id",
            "col_uploaded_at":  "uploaded_at",
            "col_upload_duration": "upload_duration_s",
        }
        if extra_config:
            config.update(extra_config)
        client = SheetClient(config)
        # Build a synthetic header map
        headers = [
            "status", "VIDEO_URL", "error_message",
            "fb_video_id", "uploaded_at", "upload_duration_s",
        ]
        client._header_map = {h: i for i, h in enumerate(headers)}
        client._current_tab = "Tab1"
        client._batch_write = MagicMock()
        client._color_row = MagicMock()
        return client

    def test_mark_done_positional_still_works(self):
        """Positional call mark_done(row, url) must not break."""
        client = self._make_client()
        client.mark_done(2, "https://fb.com/v/1")
        client._batch_write.assert_called_once()
        updates = client._batch_write.call_args[0][1]
        self.assertIn("A", updates)  # col_status → A
        self.assertEqual(updates["A"], "DONE")
        self.assertIn("B", updates)  # col_fb_link → B
        self.assertEqual(updates["B"], "https://fb.com/v/1")

    def test_mark_done_writes_fb_video_id(self):
        client = self._make_client()
        client.mark_done(3, "https://fb.com/v/X", fb_video_id="VID123")
        updates = client._batch_write.call_args[0][1]
        # fb_video_id header is at index 3 → column D
        self.assertIn("D", updates)
        self.assertEqual(updates["D"], "VID123")

    def test_mark_done_writes_uploaded_at(self):
        client = self._make_client()
        client.mark_done(3, "https://fb.com/v/X", uploaded_at="2026-05-14 10:00:00")
        updates = client._batch_write.call_args[0][1]
        self.assertIn("E", updates)
        self.assertEqual(updates["E"], "2026-05-14 10:00:00")

    def test_mark_done_writes_duration(self):
        client = self._make_client()
        client.mark_done(3, "https://fb.com/v/X", duration_s=37.5)
        updates = client._batch_write.call_args[0][1]
        self.assertIn("F", updates)
        self.assertAlmostEqual(updates["F"], 37.5, places=1)

    def test_mark_done_all_metadata(self):
        client = self._make_client()
        client.mark_done(
            5, "https://fb.com/v/Y",
            fb_video_id="ABCDE",
            uploaded_at="2026-05-14 12:00:00",
            duration_s=120.3,
        )
        updates = client._batch_write.call_args[0][1]
        self.assertEqual(updates.get("A"), "DONE")
        self.assertEqual(updates.get("B"), "https://fb.com/v/Y")
        self.assertEqual(updates.get("D"), "ABCDE")
        self.assertEqual(updates.get("E"), "2026-05-14 12:00:00")
        self.assertAlmostEqual(updates.get("F", 0), 120.3, places=1)

    def test_mark_done_skips_empty_fb_video_id(self):
        client = self._make_client()
        client.mark_done(3, "https://fb.com/v/X", fb_video_id="")
        updates = client._batch_write.call_args[0][1]
        self.assertNotIn("D", updates)

    def test_mark_done_skips_zero_duration(self):
        client = self._make_client()
        client.mark_done(3, "https://fb.com/v/X", duration_s=0.0)
        updates = client._batch_write.call_args[0][1]
        self.assertNotIn("F", updates)

    def test_mark_done_no_col_configured(self):
        """If col_fb_video_id is not in config, skip silently."""
        from utils.sheet_client import SheetClient
        config = {
            "sheet_id":   "SID",
            "sheet_tab":  "Tab1",
            "col_status": "status",
            "col_fb_link": "VIDEO_URL",
            "col_error":  "error_message",
            # no col_fb_video_id / col_uploaded_at / col_upload_duration
        }
        client = SheetClient(config)
        client._header_map = {"status": 0, "VIDEO_URL": 1, "error_message": 2}
        client._current_tab = "Tab1"
        client._batch_write = MagicMock()
        client._color_row = MagicMock()
        # Should not raise even though columns are absent from config
        client.mark_done(2, "https://fb.com/v/1",
                         fb_video_id="ID1", uploaded_at="ts", duration_s=5.0)
        client._batch_write.assert_called_once()

    def test_mark_done_col_missing_in_sheet_header(self):
        """Col configured but not present in sheet header — skip gracefully."""
        from utils.sheet_client import SheetClient
        config = {
            "sheet_id":         "SID",
            "col_status":       "status",
            "col_fb_link":      "VIDEO_URL",
            "col_error":        "error_message",
            "col_fb_video_id":  "fb_video_id",  # configured
        }
        client = SheetClient(config)
        # fb_video_id NOT in header map
        client._header_map = {"status": 0, "VIDEO_URL": 1, "error_message": 2}
        client._current_tab = "Tab1"
        client._batch_write = MagicMock()
        client._color_row = MagicMock()
        client.mark_done(2, "https://fb.com/v/1", fb_video_id="ID1")
        updates = client._batch_write.call_args[0][1]
        # D column (fb_video_id) should NOT be in updates since it's not in header
        self.assertNotIn("D", updates)

    def test_mark_done_colors_row_done(self):
        client = self._make_client()
        client.mark_done(7, "https://fb.com/v/Z")
        client._color_row.assert_called_once_with(7, "done")


# ─────────────────────────────────────────────────────────────────────────────
# 4.  SheetRunner._tick() — timing + metadata propagation
# ─────────────────────────────────────────────────────────────────────────────

class TestSheetRunnerMetadataWriteback(unittest.TestCase):
    """
    Integration test: SheetRunner._tick() must:
      - Record start time before engine.run_sync()
      - Unpack (video_link, fb_video_id) from engine.run_sync()
      - Call sheet.mark_done() with fb_video_id, uploaded_at, duration_s
    """

    def _make_runner(self):
        from core.sheet_runner import SheetRunner
        config = {
            "job_delay_seconds":             0,
            "delete_video_after_upload":     False,
            "max_concurrent_uploads_per_page": 1,
            "min_interval_per_page_s":       0,
        }
        stop = threading.Event()
        runner = SheetRunner(
            config=config, page_name="TestPage", sheet_tab="Tab1",
            stop_event=stop,
        )
        return runner, stop

    def test_tick_unpacks_video_id(self):
        runner, stop = self._make_runner()

        # Fake task from sheet
        fake_task = {
            "row_idx":       5,
            "video_url":     "https://drive.google.com/file/d/ABC/view",
            "title":         "Test",
            "description":   "",
            "keywords":      "",
            "thumbnail_url": "",
            "comment":       "",
            "target_page":   "TestPage",
            "schedule":      "",
        }

        # Patch sheet client
        runner._sheet = MagicMock()
        runner._sheet.get_next_pending_row.return_value = fake_task
        runner._sheet.mark_done = MagicMock()
        runner._sheet.mark_running = MagicMock()
        runner._sheet.mark_error = MagicMock()
        runner._sheet.count_pending = MagicMock(return_value=0)

        # Patch downloader — return a fake local path
        import tempfile
        tmp_video = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp_video.write(b"fake")
        tmp_video.close()

        runner._downloader = MagicMock()
        runner._downloader.download.return_value = tmp_video.name

        # Patch UploadEngine — return known (url, id) tuple
        from core.upload_engine import UploadEngine
        with patch.object(UploadEngine, "run_sync",
                          return_value=("https://fb.com/v/VID_X", "VID_X")):
            # Do NOT set stop_event before _tick — it would interrupt mid-flow.
            # job_delay_seconds=0 so the trailing sleep is instant.
            runner._tick()

        try:
            os.unlink(tmp_video.name)
        except Exception:
            pass

        # Verify mark_done was called with keyword params
        runner._sheet.mark_done.assert_called_once()
        call_args = runner._sheet.mark_done.call_args

        positional = call_args[0]   # (row_idx, video_link)
        kw = call_args[1]           # keyword args

        self.assertEqual(positional[0], 5)
        self.assertEqual(positional[1], "https://fb.com/v/VID_X")
        self.assertEqual(kw.get("fb_video_id"), "VID_X")
        self.assertIn("uploaded_at", kw)
        self.assertIn("duration_s", kw)

    def test_tick_uploaded_at_is_utc_string(self):
        """uploaded_at must look like '2026-05-14 10:00:00' (ISO-ish, UTC)."""
        runner, stop = self._make_runner()

        fake_task = {
            "row_idx": 6, "video_url": "https://drive.google.com/file/d/XYZ/view",
            "title": "", "description": "", "keywords": "", "thumbnail_url": "",
            "comment": "", "target_page": "", "schedule": "",
        }
        runner._sheet = MagicMock()
        runner._sheet.get_next_pending_row.return_value = fake_task
        runner._sheet.mark_done = MagicMock()
        runner._sheet.mark_running = MagicMock()

        import tempfile, re
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.write(b"v")
        tmp.close()
        runner._downloader = MagicMock()
        runner._downloader.download.return_value = tmp.name

        from core.upload_engine import UploadEngine
        with patch.object(UploadEngine, "run_sync",
                          return_value=("https://fb.com/v/ID2", "ID2")):
            runner._tick()

        try:
            os.unlink(tmp.name)
        except Exception:
            pass

        kw = runner._sheet.mark_done.call_args[1]
        uploaded_at = kw.get("uploaded_at", "")
        # Must be a non-empty datetime-like string
        self.assertTrue(bool(uploaded_at), "uploaded_at should not be empty")
        self.assertTrue(
            re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", uploaded_at),
            f"uploaded_at format wrong: {uploaded_at!r}",
        )

    def test_tick_duration_s_is_non_negative_float(self):
        runner, stop = self._make_runner()

        fake_task = {
            "row_idx": 7, "video_url": "https://drive.google.com/file/d/ZZZ/view",
            "title": "", "description": "", "keywords": "", "thumbnail_url": "",
            "comment": "", "target_page": "", "schedule": "",
        }
        runner._sheet = MagicMock()
        runner._sheet.get_next_pending_row.return_value = fake_task
        runner._sheet.mark_done = MagicMock()
        runner._sheet.mark_running = MagicMock()

        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.write(b"v")
        tmp.close()
        runner._downloader = MagicMock()
        runner._downloader.download.return_value = tmp.name

        from core.upload_engine import UploadEngine
        with patch.object(UploadEngine, "run_sync",
                          return_value=("https://fb.com/v/ID3", "ID3")):
            runner._tick()

        try:
            os.unlink(tmp.name)
        except Exception:
            pass

        kw = runner._sheet.mark_done.call_args[1]
        duration_s = kw.get("duration_s", -1)
        self.assertIsInstance(duration_s, float)
        self.assertGreaterEqual(duration_s, 0.0)


# ─────────────────────────────────────────────────────────────────────────────
# 5.  Config + Settings DEFAULTS coverage
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# 5b. SheetClient.mark_done() — confirmed_at (Phase 4 writeback)
# ─────────────────────────────────────────────────────────────────────────────

class TestSheetClientConfirmedAt(unittest.TestCase):
    """mark_done() must write confirmed_at to col_tiktok_confirmed_at for TikTok rows."""

    def _make_client(self, extra_config: dict = None):
        from utils.sheet_client import SheetClient
        config = {
            "sheet_id":                "SID",
            "sheet_tab":               "Tab1",
            "col_status":              "status",
            "col_fb_link":             "VIDEO_URL",
            "col_error":               "error_message",
            "col_tiktok_link":         "tiktok_link",
            "col_tiktok_id":           "tiktok_id",
            "col_tiktok_confirmed_at": "tiktok_confirmed_at",
        }
        if extra_config:
            config.update(extra_config)
        client = SheetClient(config)
        headers = [
            "status", "VIDEO_URL", "error_message",
            "tiktok_link", "tiktok_id", "tiktok_confirmed_at",
        ]
        client._header_map = {h: i for i, h in enumerate(headers)}
        client._current_tab = "Tab1"
        client._batch_write = MagicMock()
        client._color_row   = MagicMock()
        return client

    def test_confirmed_at_written_for_tiktok(self):
        client = self._make_client()
        client.mark_done(
            3, "https://tiktok.com/v/X",
            platform     = "tiktok",
            confirmed_at = "2026-05-14 10:00:00",
        )
        updates = client._batch_write.call_args[0][1]
        # tiktok_confirmed_at is header index 5 → column F
        self.assertIn("F", updates)
        self.assertEqual(updates["F"], "2026-05-14 10:00:00")

    def test_confirmed_at_not_written_for_facebook(self):
        client = self._make_client()
        client.mark_done(
            3, "https://fb.com/v/X",
            platform     = "facebook",
            confirmed_at = "2026-05-14 10:00:00",
        )
        updates = client._batch_write.call_args[0][1]
        # confirmed_at must NOT be written for Facebook rows
        self.assertNotIn("F", updates)

    def test_empty_confirmed_at_not_written(self):
        client = self._make_client()
        client.mark_done(
            3, "https://tiktok.com/v/X",
            platform     = "tiktok",
            confirmed_at = "",           # empty → skip write
        )
        updates = client._batch_write.call_args[0][1]
        self.assertNotIn("F", updates)

    def test_confirmed_at_absent_col_no_crash(self):
        """If col_tiktok_confirmed_at is not in config, must not raise."""
        from utils.sheet_client import SheetClient
        config = {
            "sheet_id":    "SID",
            "sheet_tab":   "Tab1",
            "col_status":  "status",
            "col_fb_link": "VIDEO_URL",
            "col_error":   "error_message",
            # no col_tiktok_confirmed_at
        }
        client = SheetClient(config)
        client._header_map = {"status": 0, "VIDEO_URL": 1, "error_message": 2}
        client._current_tab = "Tab1"
        client._batch_write = MagicMock()
        client._color_row   = MagicMock()
        # Must not raise even without the column
        client.mark_done(3, "https://tiktok.com/v/X",
                         platform="tiktok", confirmed_at="2026-05-14 10:00:00")


# ─────────────────────────────────────────────────────────────────────────────
# 5c. SheetRunner._tick() — TikTok confirmed_at auto-fill (Phase 4)
# ─────────────────────────────────────────────────────────────────────────────

class TestSheetRunnerTikTokConfirmedAt(unittest.TestCase):
    """
    When platform=tiktok and tiktok_confirmed_at is EMPTY in the sheet row,
    the runner must pass confirmed_at=uploaded_at to mark_done().

    When tiktok_confirmed_at is ALREADY SET, confirmed_at must be "" (preserve).
    """

    def _make_runner(self):
        from core.sheet_runner import SheetRunner
        config = {
            "job_delay_seconds":             0,
            "delete_video_after_upload":     False,
            "max_concurrent_uploads_per_page": 1,
            "min_interval_per_page_s":       0,
        }
        stop = threading.Event()
        return SheetRunner(
            config=config, page_name="Page", sheet_tab="Tab1",
            stop_event=stop,
        )

    def _run_tiktok_tick(self, runner, tiktok_confirmed_at: str = ""):
        """Helper: run one _tick() with a fake TikTok row."""
        import tempfile
        fake_task = {
            "row_idx":              10,
            "video_url":            "https://drive.google.com/file/d/TTT/view",
            "platform":             "tiktok",
            "post_type":            "tiktok_draft",
            "title":                "TikTok test",
            "description":          "",
            "keywords":             "",
            "thumbnail_url":        "",
            "comment":              "",
            "target_page":          "",
            "schedule":             "",
            "tiktok_confirmed_at":  tiktok_confirmed_at,
        }
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.write(b"v")
        tmp.close()

        runner._sheet = MagicMock()
        runner._sheet.get_next_pending_row.return_value = fake_task
        runner._sheet.mark_done   = MagicMock()
        runner._sheet.mark_running = MagicMock()
        runner._downloader = MagicMock()
        runner._downloader.download.return_value = tmp.name

        from core.publisher_registry import get_publisher
        mock_result = MagicMock()
        mock_result.external_post_url = "https://tiktok.com/v/123"
        mock_result.external_post_id  = "pub_123"

        mock_pub = MagicMock()
        mock_pub.publish.return_value = mock_result

        with patch("core.publisher_registry.get_publisher", return_value=mock_pub):
            runner._tick()

        try:
            os.unlink(tmp.name)
        except Exception:
            pass

        return runner._sheet.mark_done.call_args

    def test_empty_confirmed_at_gets_filled(self):
        """Blank tiktok_confirmed_at in row → confirmed_at=uploaded_at passed."""
        import re
        runner = self._make_runner()
        call_args = self._run_tiktok_tick(runner, tiktok_confirmed_at="")
        kw = call_args[1]
        confirmed = kw.get("confirmed_at", "__NOT_SET__")
        # Must be a non-empty timestamp string
        self.assertTrue(bool(confirmed), "confirmed_at should be set when field was empty")
        self.assertTrue(
            re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", confirmed),
            f"confirmed_at bad format: {confirmed!r}",
        )

    def test_existing_confirmed_at_not_overwritten(self):
        """Pre-set tiktok_confirmed_at → confirmed_at='' passed (preserve user value)."""
        runner = self._make_runner()
        call_args = self._run_tiktok_tick(
            runner, tiktok_confirmed_at="2026-05-14 08:00:00"
        )
        kw = call_args[1]
        confirmed = kw.get("confirmed_at", "__NOT_SET__")
        self.assertEqual(confirmed, "", "confirmed_at must be '' to preserve user value")


# ─────────────────────────────────────────────────────────────────────────────
# 5d. SheetClient.mark_done() — tiktok_status (Phase 5)
# ─────────────────────────────────────────────────────────────────────────────

class TestSheetClientTikTokStatus(unittest.TestCase):

    def _make_client(self):
        from utils.sheet_client import SheetClient
        config = {
            "sheet_id":          "SID",
            "sheet_tab":         "Tab1",
            "col_status":        "status",
            "col_fb_link":       "VIDEO_URL",
            "col_error":         "error_message",
            "col_tiktok_link":   "tiktok_link",
            "col_tiktok_id":     "tiktok_id",
            "col_tiktok_status": "tiktok_status",
        }
        client = SheetClient(config)
        headers = [
            "status", "VIDEO_URL", "error_message",
            "tiktok_link", "tiktok_id", "tiktok_status",
        ]
        client._header_map = {h: i for i, h in enumerate(headers)}
        client._current_tab = "Tab1"
        client._batch_write  = MagicMock()
        client._color_row    = MagicMock()
        return client

    def test_tiktok_status_written_for_tiktok(self):
        client = self._make_client()
        client.mark_done(
            3, "https://tiktok.com/v/X",
            platform="tiktok", tiktok_status="DRAFT_UPLOADED",
        )
        updates = client._batch_write.call_args[0][1]
        # tiktok_status is header index 5 → column F
        self.assertEqual(updates.get("F"), "DRAFT_UPLOADED")

    def test_tiktok_status_not_written_for_facebook(self):
        client = self._make_client()
        client.mark_done(
            3, "https://fb.com/v/X",
            platform="facebook", tiktok_status="PUBLISHED",
        )
        updates = client._batch_write.call_args[0][1]
        self.assertNotIn("F", updates)

    def test_empty_tiktok_status_not_written(self):
        client = self._make_client()
        client.mark_done(
            3, "https://tiktok.com/v/X",
            platform="tiktok", tiktok_status="",
        )
        updates = client._batch_write.call_args[0][1]
        self.assertNotIn("F", updates)

    def test_all_status_values_accepted(self):
        for status in ("DRAFT_UPLOADED", "PRIVATE_POSTED", "FOLLOWERS_POSTED", "PUBLISHED"):
            client = self._make_client()
            client.mark_done(
                3, "https://tiktok.com/v/X",
                platform="tiktok", tiktok_status=status,
            )
            updates = client._batch_write.call_args[0][1]
            self.assertEqual(updates.get("F"), status, f"Status '{status}' not written")


# ─────────────────────────────────────────────────────────────────────────────
# 5e. SheetRunner._tick() — TikTok status routing (Phase 5)
# ─────────────────────────────────────────────────────────────────────────────

class TestSheetRunnerTikTokStatusRouting(unittest.TestCase):

    def _make_runner(self):
        from core.sheet_runner import SheetRunner
        config = {
            "job_delay_seconds":               0,
            "delete_video_after_upload":       False,
            "max_concurrent_uploads_per_page": 1,
            "min_interval_per_page_s":         0,
        }
        return SheetRunner(
            config=config, page_name="Page", sheet_tab="Tab1",
            stop_event=threading.Event(),
        )

    def _run_tick(self, runner, post_type: str, privacy_level: str, pub_status: str):
        import tempfile
        fake_task = {
            "row_idx":       20,
            "video_url":     "https://drive.google.com/file/d/DDD/view",
            "platform":      "tiktok",
            "post_type":     post_type,
            "privacy_level": privacy_level,
            "title":         "Test",
            "description":   "", "keywords": "", "thumbnail_url": "",
            "comment":       "", "target_page": "", "schedule":    "",
        }
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.write(b"v")
        tmp.close()

        runner._sheet = MagicMock()
        runner._sheet.get_next_pending_row.return_value = fake_task
        runner._sheet.mark_done   = MagicMock()
        runner._sheet.mark_running = MagicMock()
        runner._downloader = MagicMock()
        runner._downloader.download.return_value = tmp.name

        mock_result = MagicMock()
        mock_result.external_post_url = "https://tiktok.com/v/abc"
        mock_result.external_post_id  = "pub_abc"
        mock_result.status            = pub_status
        mock_pub = MagicMock()
        mock_pub.publish.return_value = mock_result

        with patch("core.publisher_registry.get_publisher", return_value=mock_pub):
            runner._tick()

        try:
            os.unlink(tmp.name)
        except Exception:
            pass

        return runner._sheet.mark_done.call_args[1].get("tiktok_status", "__NOT_SET__")

    def test_draft_post_gets_draft_uploaded(self):
        runner = self._make_runner()
        status = self._run_tick(runner, "tiktok_draft", "SELF_ONLY", "draft")
        self.assertEqual(status, "DRAFT_UPLOADED")

    def test_direct_self_only_gets_private_posted(self):
        runner = self._make_runner()
        status = self._run_tick(runner, "tiktok_direct", "SELF_ONLY", "published")
        self.assertEqual(status, "PRIVATE_POSTED")

    def test_direct_followers_gets_followers_posted(self):
        runner = self._make_runner()
        status = self._run_tick(runner, "tiktok_direct", "FOLLOWER_OF_CREATOR", "published")
        self.assertEqual(status, "FOLLOWERS_POSTED")

    def test_direct_public_gets_published(self):
        runner = self._make_runner()
        status = self._run_tick(runner, "tiktok_direct", "PUBLIC_TO_EVERYONE", "published")
        self.assertEqual(status, "PUBLISHED")


# ─────────────────────────────────────────────────────────────────────────────
# 6.  Config + Settings DEFAULTS coverage
# ─────────────────────────────────────────────────────────────────────────────

class TestK1ConfigKeys(unittest.TestCase):

    def test_config_json_has_new_keys(self):
        import json
        cfg_path = os.path.join(BASE_DIR, "data", "config.json")
        if not os.path.exists(cfg_path):
            self.skipTest("config.json not found")
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        for key in ("col_fb_video_id", "col_uploaded_at", "col_upload_duration"):
            self.assertIn(key, cfg, f"config.json missing key: {key}")

    def test_settings_tab_defaults_has_new_keys(self):
        from core.config_defaults import DEFAULTS
        for key in ("col_fb_video_id", "col_uploaded_at", "col_upload_duration"):
            self.assertIn(key, DEFAULTS, f"DEFAULTS missing key: {key}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
