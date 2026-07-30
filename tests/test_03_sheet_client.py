"""
test_03_sheet_client.py
Unit tests cho SheetClient — không cần kết nối Google API.
Dùng mock để kiểm tra logic parsing, column mapping, eligibility.
"""
import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.sheet_client import SheetClient, _idx_to_col_letter


class TestColLetterConversion(unittest.TestCase):
    """_idx_to_col_letter: chuyển index 0-based → chữ cột Excel."""

    def test_single_letters(self):
        self.assertEqual(_idx_to_col_letter(0),  "A")
        self.assertEqual(_idx_to_col_letter(1),  "B")
        self.assertEqual(_idx_to_col_letter(25), "Z")

    def test_double_letters(self):
        self.assertEqual(_idx_to_col_letter(26), "AA")
        self.assertEqual(_idx_to_col_letter(27), "AB")
        self.assertEqual(_idx_to_col_letter(51), "AZ")
        self.assertEqual(_idx_to_col_letter(52), "BA")

    def test_triple_letters(self):
        self.assertEqual(_idx_to_col_letter(702), "AAA")

    def test_known_columns(self):
        # Col M (13th) = index 12
        self.assertEqual(_idx_to_col_letter(12), "M")
        # Col L = index 11
        self.assertEqual(_idx_to_col_letter(11), "L")


class TestParseSchedule(unittest.TestCase):
    """_parse_schedule: thử nhiều format ngày giờ."""

    def _tz(self):
        try:
            from zoneinfo import ZoneInfo
            return ZoneInfo("Asia/Ho_Chi_Minh")
        except Exception:
            import pytz
            return pytz.timezone("Asia/Ho_Chi_Minh")

    def _parse(self, s):
        return SheetClient._parse_schedule(s, self._tz())

    def test_iso_format(self):
        dt = self._parse("2025-06-15 14:30")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2025)
        self.assertEqual(dt.month, 6)
        self.assertEqual(dt.day, 15)
        self.assertEqual(dt.hour, 14)
        self.assertEqual(dt.minute, 30)

    def test_iso_with_seconds(self):
        dt = self._parse("2025-06-15 14:30:00")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.hour, 14)

    def test_vn_format(self):
        dt = self._parse("15/06/2025 14:30")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.day, 15)
        self.assertEqual(dt.month, 6)

    def test_vn_format_with_seconds(self):
        dt = self._parse("15/06/2025 14:30:00")
        self.assertIsNotNone(dt)

    def test_iso_t_format(self):
        dt = self._parse("2025-06-15T14:30")
        self.assertIsNotNone(dt)

    def test_iso_t_with_seconds(self):
        dt = self._parse("2025-06-15T14:30:00")
        self.assertIsNotNone(dt)

    def test_dash_vn_format(self):
        dt = self._parse("15-06-2025 14:30")
        self.assertIsNotNone(dt)

    def test_invalid_returns_none(self):
        self.assertIsNone(self._parse(""))
        self.assertIsNone(self._parse("not-a-date"))
        self.assertIsNone(self._parse("2025/06/15"))  # không có giờ

    def test_google_sheets_serial_date(self):
        # 45000.0 ≈ 2023-03-15 trong Excel/Sheets serial
        dt = self._parse("45000.0")
        self.assertIsNotNone(dt)
        self.assertGreater(dt.year, 2000)

    def test_timezone_attached(self):
        dt = self._parse("2025-06-15 14:30")
        self.assertIsNotNone(dt.tzinfo)


class TestSheetClientHeaderMap(unittest.TestCase):
    """SheetClient header map logic (no network)."""

    def _make_client(self, headers: list, config_extra: dict = None):
        config = {
            "sheet_id":           "fake_id",
            "sheet_tab":          "Sheet1",
            "timezone":           "Asia/Ho_Chi_Minh",
            "skip_overdue_minutes": 60,
            "col_status":         "status",
            "col_video_drive":    "video short",
            "col_schedule_time":  "schedule_time",
            "col_title":          "title",
            "col_description":    "description",
            "col_keywords":       "keywords",
            "col_thumbnail_url":  "thumbnail",
            "col_comment":        "comment",
            "col_fb_link":        "VIDEO_URL",
            "col_error":          "error_message",
        }
        if config_extra:
            config.update(config_extra)
        client = SheetClient(config)
        # Inject fake service + header map
        client._service = MagicMock()
        client._current_tab = "Sheet1"
        client._header_map = {
            h.strip(): i for i, h in enumerate(headers) if h.strip()
        }
        return client

    def test_col_idx_found(self):
        client = self._make_client(["status", "video short", "title"])
        self.assertEqual(client._col_idx("col_status"), 0)
        self.assertEqual(client._col_idx("col_video_drive"), 1)
        self.assertEqual(client._col_idx("col_title"), 2)

    def test_col_idx_not_found(self):
        client = self._make_client(["status"])
        self.assertIsNone(client._col_idx("col_title"))  # không có header "title"

    def test_col_letter(self):
        client = self._make_client(["status", "video short", "title"])
        self.assertEqual(client._col_letter("col_status"), "A")
        self.assertEqual(client._col_letter("col_video_drive"), "B")
        self.assertEqual(client._col_letter("col_title"), "C")

    def test_get_val_found(self):
        client = self._make_client(["status", "video short", "title"])
        row = ["DONE", "https://drive.google.com/...", "My Title"]
        self.assertEqual(client._get_val(row, "col_title"), "My Title")
        self.assertEqual(client._get_val(row, "col_video_drive"), "https://drive.google.com/...")

    def test_get_val_out_of_bounds(self):
        client = self._make_client(["status", "video short", "title"])
        row = ["DONE"]  # chỉ có 1 phần tử
        self.assertEqual(client._get_val(row, "col_title"), "")

    def test_get_val_empty_cell(self):
        client = self._make_client(["status", "video short"])
        row = ["PENDING", "   "]  # khoảng trắng
        self.assertEqual(client._get_val(row, "col_video_drive"), "")


class TestSheetClientEligibility(unittest.TestCase):
    """Logic lọc hàng eligible trong get_next_pending_row."""

    def _make_client_with_rows(self, rows: list, headers: list = None):
        if headers is None:
            headers = ["status", "video short", "schedule_time", "title",
                       "description", "keywords", "thumbnail", "comment",
                       "error_message", "VIDEO_URL"]
        config = {
            "sheet_id": "fake_id",
            "sheet_tab": "Sheet1",
            "timezone": "Asia/Ho_Chi_Minh",
            "skip_overdue_minutes": 60,
            "col_status": "status",
            "col_video_drive": "video short",
            "col_schedule_time": "schedule_time",
            "col_title": "title",
            "col_description": "description",
            "col_keywords": "keywords",
            "col_thumbnail_url": "thumbnail",
            "col_comment": "comment",
            "col_fb_link": "VIDEO_URL",
            "col_error": "error_message",
        }
        client = SheetClient(config)
        client._current_tab = "Sheet1"
        client._header_map = {h: i for i, h in enumerate(headers)}

        # Mock _refresh_header_map (no-op) và API call
        client._refresh_header_map = lambda: None
        client._sheet_id = lambda: "fake_id"
        mock_svc = MagicMock()
        mock_svc.return_value = mock_svc
        # Chuỗi call: _svc().spreadsheets().values().get(...).execute()
        mock_values_result = {"values": rows}
        mock_svc.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = mock_values_result
        client._service = mock_svc
        return client

    def _make_row(self, status="", video="https://drive.google.com/abc",
                  schedule=None, title="Test", **extra):
        if schedule is None:
            schedule = datetime.now().strftime("%Y-%m-%d %H:%M")
        return [status, video, schedule, title, "", "", "", ""]

    def test_skip_done_rows(self):
        rows = [self._make_row("DONE"), self._make_row("PENDING")]
        client = self._make_client_with_rows(rows)
        task = client.get_next_pending_row()
        self.assertIsNotNone(task)
        self.assertEqual(task["row_idx"], 3)  # hàng 2 là header, 3 là row thứ 2

    def test_skip_running_rows(self):
        rows = [self._make_row("RUNNING"), self._make_row("PENDING")]
        client = self._make_client_with_rows(rows)
        task = client.get_next_pending_row()
        self.assertIsNotNone(task)
        self.assertEqual(task["row_idx"], 3)

    def test_skip_error_rows(self):
        rows = [self._make_row("ERROR"), self._make_row("PENDING")]
        client = self._make_client_with_rows(rows)
        task = client.get_next_pending_row()
        self.assertIsNotNone(task)
        self.assertEqual(task["row_idx"], 3)

    def test_skip_skipped_rows(self):
        rows = [self._make_row("SKIPPED"), self._make_row("PENDING")]
        client = self._make_client_with_rows(rows)
        task = client.get_next_pending_row()
        self.assertIsNotNone(task)

    def test_skip_empty_video_url(self):
        rows = [
            ["PENDING", "", self._make_row()[2], "Title"],
            ["PENDING", "https://drive.google.com/file/d/abc",
             self._make_row()[2], "Title2"],
        ]
        client = self._make_client_with_rows(rows)
        task = client.get_next_pending_row()
        self.assertIsNotNone(task)
        self.assertEqual(task["title"], "Title2")

    def test_skip_future_schedule(self):
        from datetime import timedelta
        future = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
        rows = [
            ["PENDING", "https://drive.google.com/x", future, "Future"],
            ["PENDING", "https://drive.google.com/y",
             self._make_row()[2], "Now"],
        ]
        client = self._make_client_with_rows(rows)
        task = client.get_next_pending_row()
        self.assertIsNotNone(task)
        self.assertEqual(task["title"], "Now")

    def test_past_schedule_ok(self):
        from datetime import timedelta
        past = (datetime.now() - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M")
        rows = [["PENDING", "https://drive.google.com/x", past, "Past"]]
        client = self._make_client_with_rows(rows)
        task = client.get_next_pending_row()
        self.assertIsNotNone(task)
        self.assertEqual(task["title"], "Past")

    def test_no_pending_returns_none(self):
        rows = [
            self._make_row("DONE"),
            self._make_row("DONE"),
        ]
        client = self._make_client_with_rows(rows)
        self.assertIsNone(client.get_next_pending_row())

    def test_empty_sheet_returns_none(self):
        client = self._make_client_with_rows([])
        self.assertIsNone(client.get_next_pending_row())

    def test_task_dict_fields(self):
        rows = [["PENDING", "https://drive.google.com/file/d/abc123",
                 self._make_row()[2],
                 "My Title", "My Desc", "kw1, kw2", "https://img.com/t.jpg", "Comment"]]
        client = self._make_client_with_rows(rows)
        task = client.get_next_pending_row()
        self.assertIsNotNone(task)
        self.assertIn("row_idx", task)
        self.assertIn("video_url", task)
        self.assertIn("title", task)
        self.assertIn("description", task)
        self.assertIn("keywords", task)
        self.assertIn("thumbnail_url", task)
        self.assertIn("comment", task)
        self.assertEqual(task["title"], "My Title")
        self.assertEqual(task["row_idx"], 2)


class TestSheetClientStatusMissing(unittest.TestCase):
    """Kiểm tra lỗi khi thiếu cột status trong header."""

    def test_missing_status_col_raises(self):
        config = {
            "sheet_id": "fake",
            "sheet_tab": "Sheet1",
            "timezone": "Asia/Ho_Chi_Minh",
            "skip_overdue_minutes": 0,
            "col_status": "nonexistent_column",
            "col_video_drive": "video",
        }
        client = SheetClient(config)
        client._current_tab = "Sheet1"
        client._header_map = {"video": 0, "status": 1}  # thiếu "nonexistent_column"
        client._refresh_header_map = lambda: None
        client._sheet_id = lambda: "fake"
        mock_svc = MagicMock()
        mock_svc.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
            "values": [["PENDING", "https://drive.google.com/x"]]
        }
        client._service = mock_svc
        with self.assertRaises(ValueError):
            client.get_next_pending_row()


if __name__ == "__main__":
    unittest.main(verbosity=2)
