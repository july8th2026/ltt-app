"""
Google Sheets client: Sheets API v4 + dual auth (Service Account / OAuth2).

Lần đầu chạy với OAuth2 sẽ mở browser để xác thực.
Token cache tại {credentials_path}.token.json (cùng thư mục credentials).
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

_MAX_RETRIES    = 5
_RETRY_BASE_SEC = 2.0
_QUOTA_CODES    = {429, 503}

_SCHEDULE_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
]

_ROW_COLORS = {
    "default": {"red": 1.0,  "green": 1.0,  "blue": 1.0},
    "running": {"red": 1.0,  "green": 1.0,  "blue": 0.80},
    "done":    {"red": 0.72, "green": 0.88, "blue": 0.60},
    "error":   {"red": 0.95, "green": 0.80, "blue": 0.80},
    "skipped": {"red": 0.85, "green": 0.85, "blue": 0.85},
}


def _idx_to_col_letter(zero_based: int) -> str:
    result, n = "", zero_based + 1
    while n > 0:
        n, r = divmod(n - 1, 26)
        result = chr(65 + r) + result
    return result


class SheetClient:
    """
    Đọc/ghi Google Sheet qua Sheets API v4.

    Config keys cần thiết:
        google_credentials_path  : credentials.json hoặc service_account.json
        sheet_id                 : ID sheet (lấy từ URL)
        sheet_tab                : tên tab mặc định
        timezone                 : vd 'Asia/Ho_Chi_Minh'
        skip_overdue_minutes     : bỏ qua job trễ hơn N phút (0 = không giới hạn)
        col_*                    : tên header của từng cột trong sheet
    """

    def __init__(self, config: dict, sheet_id_override: Optional[str] = None):
        self.config = config
        # Per-instance override — multi-sheet workers pass the spreadsheet id
        # they should address; falls back to config["sheet_id"] when None.
        self._sheet_id_override: Optional[str] = (
            sheet_id_override.strip() if isinstance(sheet_id_override, str) and sheet_id_override.strip()
            else None
        )
        self._service = None
        self._cred_type: Optional[str] = None
        self._header_map: dict[str, int] = {}   # header_name → 0-based index
        self._sheet_id_int_cache: dict[str, int] = {}  # tab_name → internal sheetId
        self._current_tab: str = config.get("sheet_tab", "").strip()

    # ─── Auth & connect ──────────────────────────────────────────────────────

    def connect(self):
        """Xác thực + khởi tạo Sheets API service. OAuth2 mở browser lần đầu."""
        creds_path = self.config.get("google_credentials_path", "").strip()
        if not creds_path:
            raise ValueError("Chưa cấu hình đường dẫn credentials trong Cài đặt")
        if not os.path.isfile(creds_path):
            raise FileNotFoundError(
                f"Không tìm thấy credentials tại: {creds_path}\n"
                "Tải về từ Google Cloud Console → APIs & Services → Credentials"
            )

        creds = self._load_credentials(creds_path)
        from googleapiclient.discovery import build
        self._service = build("sheets", "v4", credentials=creds, cache_discovery=False)

        if self._current_tab:
            self._refresh_header_map()

    def _load_credentials(self, path: str):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        if data.get("type") == "service_account":
            from google.oauth2 import service_account
            creds = service_account.Credentials.from_service_account_file(
                path, scopes=SCOPES
            )
            self._cred_type = "service_account"
            logger.info("Service Account: %s", data.get("client_email", "?"))
            return creds

        # OAuth2 ("installed" / "web" client).
        #
        # A pre-authorised token beside the client file still works, and is
        # refreshed while its refresh_token holds. What is gone is the
        # interactive fallback: `InstalledAppFlow.run_local_server()` binds a
        # local port and waits for a browser to visit it. On a headless server
        # that never happens, so the call blocked forever — and it blocked
        # inside a request, with no error and no log line explaining why the
        # page had stopped responding. Refusing with an explanation is the
        # only honest option here.
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        token_file = Path(path).with_suffix(".token.json")
        creds = None

        if token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
            except Exception:
                creds = None

        if not creds or not getattr(creds, "valid", False):
            if creds and getattr(creds, "expired", False) and creds.refresh_token:
                creds.refresh(Request())
                token_file.write_text(creds.to_json(), encoding="utf-8")
            else:
                raise RuntimeError(
                    f"File credentials `{path}` là OAuth client (type="
                    f"{data.get('type', '?')!r}), cần mở trình duyệt để người "
                    f"dùng bấm đồng ý — không làm được trên máy chủ.\n"
                    f"Hãy dùng Service Account: vào Cài đặt → tải lên file "
                    f"JSON của Service Account, rồi chia sẻ Google Sheet cho "
                    f"địa chỉ email trong file đó (quyền Editor)."
                )

        self._cred_type = "oauth2"
        logger.info("OAuth2 credentials loaded từ %s", path)
        return creds

    # ─── Tab ─────────────────────────────────────────────────────────────────

    def get_all_tabs(self) -> list[str]:
        meta = self._retry(
            lambda: self._svc().spreadsheets()
            .get(spreadsheetId=self._sheet_id(), fields="sheets.properties.title")
            .execute()
        )
        return [s["properties"]["title"] for s in meta.get("sheets", [])]

    def switch_tab(self, tab_name: str):
        self._current_tab = tab_name
        self._refresh_header_map()

    def test_connection(self) -> tuple[bool, str]:
        try:
            self.connect()
            tabs = self.get_all_tabs()
            snippet = ", ".join(tabs[:5])
            return True, f"OK ({self._cred_type}) — {len(tabs)} tab: {snippet}"
        except Exception as e:
            return False, str(e)

    # ─── Header map ──────────────────────────────────────────────────────────

    def _refresh_header_map(self):
        """Đọc hàng 1 và build map header → 0-based index."""
        tab = self._current_tab
        result = self._retry(
            lambda: self._svc().spreadsheets().values()
            .get(
                spreadsheetId=self._sheet_id(),
                range=f"'{tab}'!A1:ZZ1",
                valueRenderOption="UNFORMATTED_VALUE",
            )
            .execute()
        )
        rows = result.get("values", [[]])
        headers = rows[0] if rows else []
        self._header_map = {
            str(h).strip(): i for i, h in enumerate(headers) if str(h).strip()
        }
        logger.debug("Header map (%s): %s", tab, self._header_map)

    def _col_idx(self, config_key: str) -> Optional[int]:
        name = self.config.get(config_key, "").strip()
        if not name:
            return None
        return self._header_map.get(name)

    # P1-10 fix: public alias for external callers (GUI etc.)
    # Underscore-prefixed methods are private; this is the stable API.
    def get_column_index(self, config_key: str) -> Optional[int]:
        """Return the 0-based column index for a column name in config.

        Returns None if the column is not configured or not found in the sheet.
        Stable public API — _col_idx may be renamed in future refactors.
        """
        return self._col_idx(config_key)

    def get_header_names(self) -> list[str]:
        """Return the actual header names present in the current tab.

        Used by core.preflight to tell an operator which column names the
        sheet really has when a configured name does not match.
        """
        return list(self._header_map.keys())

    def get_all_rows(self) -> list[list]:
        """Return every data row (header excluded) of the current tab.

        Public bulk reader for callers that need the whole tab — e.g. the
        desktop queue-preview panel. Added because that panel previously
        reached for a non-existent `client.worksheet` attribute left over
        from the gspread migration (docs/_luutru/AUDIT_REPORT.md finding D1).
        """
        return self._retry(
            lambda: self._svc().spreadsheets().values()
            .get(
                spreadsheetId=self._sheet_id(),
                range=f"'{self._current_tab}'!A2:ZZ",
                valueRenderOption="UNFORMATTED_VALUE",
                dateTimeRenderOption="FORMATTED_STRING",
            )
            .execute()
        ).get("values", [])

    def _col_letter(self, config_key: str) -> Optional[str]:
        idx = self._col_idx(config_key)
        return _idx_to_col_letter(idx) if idx is not None else None

    def _get_val(self, row: list, config_key: str) -> str:
        idx = self._col_idx(config_key)
        if idx is None or idx >= len(row):
            return ""
        return str(row[idx]).strip()

    # ─── Đọc dữ liệu ─────────────────────────────────────────────────────────

    def get_next_pending_row(self, platform_filter: str = "") -> Optional[dict]:
        """
        Tìm hàng đầu tiên đủ điều kiện:
          - status ∉ DONE / RUNNING / SKIPPED / ERROR
          - có video Drive URL
          - schedule_time có giá trị hợp lệ VÀ <= now (BẮT BUỘC)
          - (NEW) platform của row khớp platform_filter (nếu provided)

        platform_filter:
          ""          → mọi platform (backwards compat)
          "facebook"  → chỉ row có col_platform = facebook (hoặc empty → default FB)
          "tiktok"    → chỉ row có col_platform = tiktok

        Trả về dict task, hoặc None nếu không có.
        """
        platform_filter = (platform_filter or "").strip().lower()
        self._refresh_header_map()

        status_idx = self._col_idx("col_status")
        if status_idx is None:
            raise ValueError(
                f"Không tìm thấy cột status '{self.config.get('col_status')}' "
                "trong header row. Kiểm tra tên cột trong Cài đặt."
            )

        tz = self._get_tz()
        now = datetime.now(tz)
        skip_min = int(self.config.get("skip_overdue_minutes", 60))
        sched_idx = self._col_idx("col_schedule_time")
        if sched_idx is None:
            raise ValueError(
                f"Không tìm thấy cột schedule_time "
                f"'{self.config.get('col_schedule_time')}' trong header row. "
                "Cột này BẮT BUỘC — bot chỉ xử lý row khi đã đặt lịch."
            )

        all_rows: list[list] = self._retry(
            lambda: self._svc().spreadsheets().values()
            .get(
                spreadsheetId=self._sheet_id(),
                range=f"'{self._current_tab}'!A2:ZZ",
                valueRenderOption="UNFORMATTED_VALUE",
                dateTimeRenderOption="FORMATTED_STRING",
            )
            .execute()
        ).get("values", [])

        # P1.2 — Random row ordering. Default ON. The original first-row-first
        # behaviour is preserved when anti_spam_random_order=false.
        # Anti-pattern protection: posting in sheet order every day = bot
        # signature. Shuffling rows that are all "ready now" breaks that.
        row_iter = list(enumerate(all_rows))
        if self.config.get("anti_spam_random_order", True):
            import random as _random
            _random.shuffle(row_iter)

        for rel, row in row_iter:
            row_num = rel + 2  # 1-based, skip header

            if not any(str(c).strip() for c in row):
                continue

            status = ""
            if status_idx < len(row):
                status = str(row[status_idx]).strip().upper()
            if status in ("DONE", "RUNNING", "SKIPPED", "ERROR") or status.startswith("RETRY"):
                continue

            video_url = self._get_val(row, "col_video_drive")
            if not video_url:
                continue

            # Platform filter: skip rows whose target platform doesn't match.
            # Empty col_platform defaults to "facebook" — same as the row dict below.
            if platform_filter:
                row_platform = (
                    self._get_val(row, "col_platform") or "facebook"
                ).strip().lower()
                if row_platform != platform_filter:
                    continue

            # Kiểm tra schedule_time — BẮT BUỘC. Row chỉ được pickup khi:
            #   (a) ô có giá trị,
            #   (b) đúng định dạng parse được,
            #   (c) đã đến giờ (sched_dt <= now),
            #   (d) chưa quá hạn skip_overdue_minutes.
            raw = str(row[sched_idx]).strip() if sched_idx < len(row) else ""
            if not raw:
                continue  # chưa điền lịch → bot chưa "quét tới"
            sched_dt = self._parse_schedule(raw, tz)
            if not sched_dt:
                self.mark_skipped(
                    row_num,
                    f"schedule_time không hợp lệ: {raw[:40]}",
                )
                continue
            if sched_dt > now:
                continue  # chưa đến giờ
            if skip_min > 0:
                diff = (now - sched_dt).total_seconds() / 60
                if diff > skip_min:
                    self.mark_skipped(row_num, f"Quá hạn {diff:.0f} phút")
                    continue

            return {
                "row_idx":        row_num,
                "video_url":      video_url,
                "schedule":       self._get_val(row, "col_schedule_time"),
                "title":          self._get_val(row, "col_title"),
                "description":    self._get_val(row, "col_description"),
                "keywords":       self._get_val(row, "col_keywords"),
                "thumbnail_url":  self._get_val(row, "col_thumbnail_url"),
                "comment":        self._get_val(row, "col_comment"),
                "target_page":    self._get_val(row, "col_target_page"),
                "post_type":      self._get_val(row, "col_post_type") or "feed",
                # Multi-platform fields (default to facebook for backward compat)
                "platform":       self._get_val(row, "col_platform") or "facebook",
                "tiktok_account": self._get_val(row, "col_tiktok_account"),
            }

        return None

    def count_pending(self, platform_filter: str = "") -> int:
        """Count rows in PENDING state. Optionally filter by platform.

        platform_filter same semantics as get_next_pending_row():
          ""         → all rows
          "facebook" → only col_platform=facebook (or empty → defaults to FB)
          "tiktok"   → only col_platform=tiktok
        """
        platform_filter = (platform_filter or "").strip().lower()
        try:
            self._refresh_header_map()
            status_idx = self._col_idx("col_status")
            if status_idx is None:
                return 0
            sched_idx = self._col_idx("col_schedule_time")
            if sched_idx is None:
                return 0
            rows = self._retry(
                lambda: self._svc().spreadsheets().values()
                .get(
                    spreadsheetId=self._sheet_id(),
                    range=f"'{self._current_tab}'!A2:ZZ",
                    valueRenderOption="UNFORMATTED_VALUE",
                )
                .execute()
            ).get("values", [])

            def _row_pending(row):
                if not any(str(c).strip() for c in row):
                    return False
                if status_idx < len(row):
                    s = str(row[status_idx]).strip().upper()
                    if s in ("DONE", "RUNNING", "SKIPPED", "ERROR") or s.startswith("RETRY"):
                        return False
                if platform_filter:
                    rp = (self._get_val(row, "col_platform") or "facebook").strip().lower()
                    if rp != platform_filter:
                        return False
                # schedule_time bắt buộc — row không có lịch không tính pending
                raw = str(row[sched_idx]).strip() if sched_idx < len(row) else ""
                if not raw:
                    return False
                return True

            return sum(1 for row in rows if _row_pending(row))
        except Exception:
            return 0

    # ─── Ghi trạng thái ──────────────────────────────────────────────────────

    def mark_running(self, row_idx: int):
        updates = {}
        col = self._col_letter("col_status")
        if col:
            updates[col] = "RUNNING"
        self._batch_write(row_idx, updates)
        self._color_row(row_idx, "running")

    def mark_done(
        self,
        row_idx: int,
        video_link: str,
        *,
        fb_video_id: str = "",
        uploaded_at: str = "",
        duration_s: float = 0.0,
        platform: str = "",       # "facebook" | "tiktok" | "tiktok_draft" …
        confirmed_at: str = "",   # TikTok: write consent timestamp if column is empty
        tiktok_status: str = "",  # TikTok: "DRAFT_UPLOADED" | "PRIVATE_POSTED" | "PUBLISHED" …
    ):
        updates = {}
        for key, val in [
            ("col_status",  "DONE"),
            ("col_fb_link", video_link),
            ("col_error",   ""),
        ]:
            col = self._col_letter(key)
            if col:
                updates[col] = val
        # Optional metadata columns (only written if column header exists in sheet)
        if fb_video_id:
            col = self._col_letter("col_fb_video_id")
            if col:
                updates[col] = fb_video_id
        if uploaded_at:
            col = self._col_letter("col_uploaded_at")
            if col:
                updates[col] = uploaded_at
        if duration_s > 0:
            col = self._col_letter("col_upload_duration")
            if col:
                updates[col] = round(duration_s, 1)
        # TikTok-specific write-back (additive — does not change FB behaviour)
        if platform and platform.lower().startswith("tiktok"):
            if video_link:
                col = self._col_letter("col_tiktok_link")
                if col:
                    updates[col] = video_link
            if fb_video_id:
                col = self._col_letter("col_tiktok_id")
                if col:
                    updates[col] = fb_video_id
            # Write user_confirmed_at timestamp for TikTok audit trail.
            # Only written when the caller supplies the value (i.e. the field
            # was empty in the sheet — we do not overwrite a user-set consent time).
            if confirmed_at:
                col = self._col_letter("col_tiktok_confirmed_at")
                if col:
                    updates[col] = confirmed_at
            # Write TikTok-specific publish status for fine-grained tracking.
            # Values: "DRAFT_UPLOADED" | "PRIVATE_POSTED" | "FOLLOWERS_POSTED" | "PUBLISHED"
            if tiktok_status:
                col = self._col_letter("col_tiktok_status")
                if col:
                    updates[col] = tiktok_status
        self._batch_write(row_idx, updates)
        self._color_row(row_idx, "done")

    def mark_error(self, row_idx: int, error: str):
        updates = {}
        for key, val in [("col_status", "ERROR"), ("col_error", error[:300])]:
            col = self._col_letter(key)
            if col:
                updates[col] = val
        self._batch_write(row_idx, updates)
        self._color_row(row_idx, "error")

    def mark_retry(self, row_idx: int, attempt: int, max_retries: int, error: str):
        """Mark row as pending-retry (skipped by get_next_pending_row until reset)."""
        updates = {}
        col = self._col_letter("col_status")
        if col:
            updates[col] = f"RETRY {attempt}/{max_retries}"
        col = self._col_letter("col_error")
        if col:
            updates[col] = f"[Retry {attempt}/{max_retries}] {error[:200]}"
        self._batch_write(row_idx, updates)
        self._color_row(row_idx, "error")   # amber-ish via error color for visibility

    def clear_retry_status(self, row_idx: int):
        """Reset RETRY row back to pending so it gets picked up again."""
        updates = {}
        col = self._col_letter("col_status")
        if col:
            updates[col] = ""
        self._batch_write(row_idx, updates)
        self._color_row(row_idx, "default")

    def mark_skipped(self, row_idx: int, reason: str):
        updates = {}
        for key, val in [("col_status", "SKIPPED"), ("col_error", reason[:200])]:
            col = self._col_letter(key)
            if col:
                updates[col] = val
        self._batch_write(row_idx, updates)
        self._color_row(row_idx, "skipped")

    # ─── Helpers nội bộ ──────────────────────────────────────────────────────

    def _batch_write(self, row_idx: int, updates: dict[str, Any]):
        if not updates:
            return
        tab = self._current_tab
        data = [
            {"range": f"'{tab}'!{col}{row_idx}", "values": [[val]]}
            for col, val in updates.items()
        ]
        try:
            self._retry(
                lambda: self._svc().spreadsheets().values()
                .batchUpdate(
                    spreadsheetId=self._sheet_id(),
                    body={"valueInputOption": "USER_ENTERED", "data": data},
                )
                .execute()
            )
        except Exception as e:
            logger.warning("Batch write row %d thất bại: %s", row_idx, e)

    def _color_row(self, row_num: int, color_key: str):
        try:
            color = _ROW_COLORS.get(color_key, _ROW_COLORS["default"])
            int_id = self._get_internal_sheet_id(self._current_tab)
            self._retry(
                lambda: self._svc().spreadsheets()
                .batchUpdate(
                    spreadsheetId=self._sheet_id(),
                    body={
                        "requests": [{
                            "repeatCell": {
                                "range": {
                                    "sheetId": int_id,
                                    "startRowIndex": row_num - 1,
                                    "endRowIndex":   row_num,
                                    "startColumnIndex": 0,
                                    "endColumnIndex": 26,
                                },
                                "cell": {
                                    "userEnteredFormat": {"backgroundColor": color}
                                },
                                "fields": "userEnteredFormat.backgroundColor",
                            }
                        }]
                    },
                )
                .execute()
            )
        except Exception as e:
            logger.debug("Tô màu row %d bỏ qua: %s", row_num, e)

    def _get_internal_sheet_id(self, tab_name: str) -> int:
        if tab_name not in self._sheet_id_int_cache:
            meta = self._retry(
                lambda: self._svc().spreadsheets()
                .get(spreadsheetId=self._sheet_id(), fields="sheets.properties")
                .execute()
            )
            for s in meta.get("sheets", []):
                p = s.get("properties", {})
                self._sheet_id_int_cache[p.get("title", "")] = p.get("sheetId", 0)
        return self._sheet_id_int_cache.get(tab_name, 0)

    def _sheet_id(self) -> str:
        # Override (multi-sheet workers) takes priority over global config.
        sid = self._sheet_id_override or self.config.get("sheet_id", "").strip()
        if not sid:
            raise ValueError("Chưa nhập Sheet ID trong Cài đặt")
        return sid

    def _svc(self):
        if self._service is None:
            raise RuntimeError("Chưa connect — gọi connect() trước")
        return self._service

    def _get_tz(self):
        tz_name = self.config.get("timezone", "Asia/Ho_Chi_Minh")
        try:
            return ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, Exception):
            try:
                import pytz
                return pytz.timezone(tz_name)
            except Exception:
                return ZoneInfo("UTC")

    def _retry(self, fn, max_retries: int = _MAX_RETRIES):
        last_exc = None
        for attempt in range(max_retries):
            try:
                return fn()
            except Exception as exc:
                last_exc = exc
                http_code = getattr(getattr(exc, "resp", None), "status", None)
                if http_code and int(http_code) not in _QUOTA_CODES:
                    raise
                if attempt < max_retries - 1:
                    wait = _RETRY_BASE_SEC * (2 ** attempt)
                    logger.warning(
                        "Sheets API retry %d/%d sau %.1fs: %s",
                        attempt + 1, max_retries, wait, exc,
                    )
                    time.sleep(wait)
        raise last_exc  # type: ignore[misc]

    @staticmethod
    def _parse_schedule(s: str, tz) -> Optional[datetime]:
        """Thử nhiều format ngày giờ → datetime có timezone."""
        s = s.strip()

        # Google Sheets serial date float
        try:
            val = float(s)
            if 40000 < val < 60000:
                epoch = datetime(1899, 12, 30)
                dt = epoch + timedelta(days=val)
                if hasattr(tz, "localize"):
                    return tz.localize(dt)
                return dt.replace(tzinfo=tz)
        except ValueError:
            pass

        for fmt in _SCHEDULE_FORMATS:
            try:
                dt = datetime.strptime(s, fmt)
                if hasattr(tz, "localize"):
                    return tz.localize(dt)
                return dt.replace(tzinfo=tz)
            except ValueError:
                continue
        return None
