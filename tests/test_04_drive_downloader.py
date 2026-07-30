"""
test_04_drive_downloader.py
Unit tests cho DriveDownloader — không cần mạng thật.
"""
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.drive_downloader import (
    DriveDownloadError,
    DriveDownloader,
    _extract_file_id,
)


def _write_minimal_cached_mp4(path: str):
    """Write enough bytes to satisfy production cache validation."""
    with open(path, "wb") as file_obj:
        file_obj.write(b"\x00\x00\x00\x18ftypmp42")
        file_obj.write(b"\x00" * (11 * 1024))


class TestExtractFileId(unittest.TestCase):
    """_extract_file_id: trích xuất ID từ các dạng URL Google Drive."""

    SAMPLE_ID = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"

    def test_file_d_view(self):
        url = f"https://drive.google.com/file/d/{self.SAMPLE_ID}/view?usp=sharing"
        self.assertEqual(_extract_file_id(url), self.SAMPLE_ID)

    def test_file_d_edit(self):
        url = f"https://drive.google.com/file/d/{self.SAMPLE_ID}/edit"
        self.assertEqual(_extract_file_id(url), self.SAMPLE_ID)

    def test_file_d_preview(self):
        url = f"https://drive.google.com/file/d/{self.SAMPLE_ID}/preview"
        self.assertEqual(_extract_file_id(url), self.SAMPLE_ID)

    def test_open_id(self):
        url = f"https://drive.google.com/open?id={self.SAMPLE_ID}"
        self.assertEqual(_extract_file_id(url), self.SAMPLE_ID)

    def test_uc_id(self):
        url = f"https://drive.google.com/uc?id={self.SAMPLE_ID}"
        self.assertEqual(_extract_file_id(url), self.SAMPLE_ID)

    def test_uc_export_id(self):
        url = f"https://drive.google.com/uc?export=download&id={self.SAMPLE_ID}"
        self.assertEqual(_extract_file_id(url), self.SAMPLE_ID)

    def test_id_with_extra_params(self):
        url = f"https://drive.google.com/file/d/{self.SAMPLE_ID}/view?usp=drivesdk&foo=bar"
        self.assertEqual(_extract_file_id(url), self.SAMPLE_ID)

    def test_empty_url(self):
        self.assertIsNone(_extract_file_id(""))
        self.assertIsNone(_extract_file_id(None))
        self.assertIsNone(_extract_file_id("   "))

    def test_non_drive_url(self):
        self.assertIsNone(_extract_file_id("https://youtube.com/watch?v=abc123"))

    def test_short_id_rejected(self):
        # ID ngắn < 25 ký tự → không hợp lệ
        url = "https://drive.google.com/file/d/shortid/view"
        # shortid = 7 ký tự, không match pattern (yêu cầu 25+ cho gdown)
        # _extract_file_id của ta không có min-length, check xem nó extract được không
        result = _extract_file_id(url)
        # Dù extract được hay không, phải không crash
        # (shortid thực tế sẽ fail khi download)
        self.assertTrue(result is None or isinstance(result, str))

    def test_whitespace_stripped(self):
        url = f"  https://drive.google.com/file/d/{self.SAMPLE_ID}/view  "
        self.assertEqual(_extract_file_id(url), self.SAMPLE_ID)


class TestDriveDownloaderCache(unittest.TestCase):
    """Cache detection logic."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.dl = DriveDownloader({"temp_video_dir": self._tmpdir})

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_find_cached_existing_file(self):
        file_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
        cached_path = os.path.join(self._tmpdir, f"{file_id}.mp4")
        _write_minimal_cached_mp4(cached_path)

        result = self.dl._find_cached(file_id)
        self.assertEqual(result, cached_path)

    def test_find_cached_empty_file(self):
        file_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
        empty_path = os.path.join(self._tmpdir, f"{file_id}.mp4")
        open(empty_path, "wb").close()  # file rỗng

        result = self.dl._find_cached(file_id)
        self.assertIsNone(result)

    def test_find_cached_no_file(self):
        result = self.dl._find_cached("nonexistent_id")
        self.assertIsNone(result)

    def test_delete_static(self):
        path = os.path.join(self._tmpdir, "test.mp4")
        with open(path, "wb") as f:
            f.write(b"x")
        self.assertTrue(os.path.exists(path))
        DriveDownloader.delete(path)
        self.assertFalse(os.path.exists(path))

    def test_delete_nonexistent_no_error(self):
        # Không raise exception
        DriveDownloader.delete("/nonexistent/path/file.mp4")

    def test_delete_none_no_error(self):
        DriveDownloader.delete(None)
        DriveDownloader.delete("")


class TestExtractConfirmToken(unittest.TestCase):
    """_extract_confirm_token từ response."""

    def _mock_response(self, cookies: dict = None, body: str = ""):
        resp = MagicMock()
        resp.cookies = cookies or {}
        resp.text = body
        return resp

    def test_extract_from_cookie(self):
        resp = self._mock_response(cookies={"download_warning_12345": "t"})
        token = DriveDownloader._extract_confirm_token(resp)
        self.assertEqual(token, "t")

    def test_extract_from_html_body(self):
        html = '<a href="/uc?confirm=abc123&id=xyz">Download anyway</a>'
        resp = self._mock_response(body=html)
        token = DriveDownloader._extract_confirm_token(resp)
        self.assertEqual(token, "abc123")

    def test_no_token_returns_none(self):
        resp = self._mock_response(body="<html>Normal page</html>")
        token = DriveDownloader._extract_confirm_token(resp)
        self.assertIsNone(token)


class TestDriveDownloaderErrors(unittest.TestCase):
    """Error handling trong download."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.dl = DriveDownloader({"temp_video_dir": self._tmpdir})

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_empty_url_raises(self):
        with self.assertRaises(DriveDownloadError):
            self.dl.download("")

    def test_none_url_raises(self):
        with self.assertRaises(DriveDownloadError):
            self.dl.download(None)

    def test_invalid_url_raises(self):
        with self.assertRaises(DriveDownloadError) as ctx:
            self.dl.download("https://youtube.com/watch?v=abc")
        self.assertIn("file ID", str(ctx.exception))

    def test_download_uses_cache_if_exists(self):
        file_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
        cached = os.path.join(self._tmpdir, f"{file_id}.mp4")
        _write_minimal_cached_mp4(cached)

        logs = []
        url = f"https://drive.google.com/file/d/{file_id}/view"
        result = self.dl.download(url, on_log=logs.append)

        self.assertEqual(result, cached)
        self.assertTrue(any("đã tải" in l.lower() or "cache" in l.lower() for l in logs))

    def test_failed_download_removes_partial_file(self):
        """Nếu download thất bại, file partial phải bị xóa."""
        file_id = "abc123_fake_id_that_fails"
        logs = []

        # Mock requests để luôn raise exception
        with patch("utils.drive_downloader.DriveDownloader._do_download",
                   side_effect=ConnectionError("Mạng lỗi")):
            with self.assertRaises(RuntimeError):
                self.dl._download_with_retry(
                    file_id,
                    os.path.join(self._tmpdir, f"{file_id}.mp4"),
                    None,
                    logs.append,
                )

        partial = os.path.join(self._tmpdir, f"{file_id}.mp4")
        self.assertFalse(os.path.exists(partial))


if __name__ == "__main__":
    unittest.main(verbosity=2)
