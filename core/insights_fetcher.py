"""
K-7: Facebook Video Insights Fetcher.

Background daemon: scans DONE rows in the Google Sheet that have a fb_video_id
but no insights yet (col_insights_at empty), waits until 24h after upload, fetches
insights via Graph API, writes back to sheet.

Design:
  - Single daemon thread; scan every `insights_scan_interval_s` seconds (default 1800)
  - Skips rows uploaded < 24h ago (Facebook insights not reliable before that)
  - Gracefully handles missing columns — only writes columns that are configured
  - Retries failed rows next scan cycle
  - Respects stop_event for clean shutdown

Config keys (all optional):
    col_fb_video_id     : "fb_video_id"
    col_uploaded_at     : "uploaded_at"
    col_insights_at     : "insights_at"
    col_views           : "views"
    col_reach           : "reach"
    col_reactions       : "reactions"
    col_comments_count  : "comments_count"
    col_shares          : "shares"
    col_minutes_viewed  : "minutes_viewed"
    insights_min_age_h  : 24   (hours to wait before fetching)
    insights_scan_interval_s : 1800  (scan period seconds)
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

_INSIGHTS_MIN_AGE_H = 24        # hours after upload before fetching
_SCAN_INTERVAL_S    = 1800      # 30 min between scans


class InsightsFetcher:
    """
    Background daemon that fetches video insights and writes them back to sheet.
    """

    def __init__(
        self,
        config: dict,
        stop_event: threading.Event,
        on_log=None,
    ):
        self._config     = config
        self._stop_event = stop_event
        self._on_log     = on_log or (lambda m, l: None)
        self._thread: Optional[threading.Thread] = None
        self._min_age_h  = float(config.get("insights_min_age_h", _INSIGHTS_MIN_AGE_H))
        self._interval_s = float(config.get("insights_scan_interval_s", _SCAN_INTERVAL_S))

    # ── Public ────────────────────────────────────────────────────────────────

    def start(self):
        """Start the background daemon thread."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="InsightsFetcher"
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _run(self):
        self._log("Insights Fetcher khởi động", "info")
        # Initial wait so we don't hammer the API right at startup
        self._sleep(60)
        while not self._stop_event.is_set():
            try:
                self._scan_once()
            except Exception as exc:
                self._log(f"[Insights] Lỗi scan: {exc}", "warning")
            self._sleep(self._interval_s)
        self._log("Insights Fetcher đã dừng", "info")

    def _scan_once(self):
        """
        Read DONE rows from ALL configured sheets and tabs, find rows that
        need insights, and fetch + write for each.

        Multi-sheet: iterate over config["sheets"] (list of {id, alias}).
        Legacy fallback: when sheets[] is empty, use config["sheet_id"].
        """
        from utils.sheet_client import SheetClient
        from core.token_store import TokenStore
        from core.graph_client import GraphClient
        from core.utils import graph_api_version

        # Build list of (sheet_id, alias) to scan
        sheets_list = list(self._config.get("sheets", []) or [])
        if not sheets_list and self._config.get("sheet_id"):
            sheets_list = [{"id": self._config["sheet_id"], "alias": "Default"}]
        if not sheets_list:
            self._log("[Insights] Không có sheet nào để quét", "warning")
            return

        token_store = TokenStore()
        client = GraphClient(
            version=graph_api_version(self._config), timeout=30, max_retries=2
        )
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self._min_age_h)
        tabs_to_scan = self._get_tabs_to_scan()

        for s in sheets_list:
            if self._stop_event.is_set():
                break
            sid = str(s.get("id", "")).strip()
            alias = str(s.get("alias", sid[:8] or "Sheet")).strip()
            if not sid:
                continue

            sheet = SheetClient(self._config, sheet_id_override=sid)
            try:
                sheet.connect()
            except Exception as exc:
                self._log(
                    f"[Insights] Không kết nối được sheet '{alias}': {exc}",
                    "warning",
                )
                continue

            for tab in tabs_to_scan:
                if self._stop_event.is_set():
                    break
                try:
                    sheet.switch_tab(tab)
                    self._scan_tab(sheet, client, token_store, cutoff)
                except Exception as exc:
                    self._log(
                        f"[Insights] Sheet '{alias}' tab '{tab}' lỗi: {exc}",
                        "warning",
                    )

    def _scan_tab(
        self, sheet, client, token_store, cutoff: datetime
    ):
        """Scan one sheet tab for rows needing insights."""
        rows_to_process = self._find_pending_rows(sheet, cutoff)
        if not rows_to_process:
            return

        self._log(
            f"[Insights] Tab '{sheet._current_tab}': "
            f"{len(rows_to_process)} hàng cần fetch insights",
            "info",
        )

        for row_info in rows_to_process:
            if self._stop_event.is_set():
                break
            row_idx    = row_info["row_idx"]
            video_id   = row_info["fb_video_id"]
            target_page = row_info.get("target_page", "")

            # Find page token
            token = self._find_page_token(token_store, target_page)
            if not token:
                self._log(
                    f"[Insights] Hàng #{row_idx}: không tìm thấy token cho page "
                    f"'{target_page}' — bỏ qua",
                    "warning",
                )
                continue

            try:
                insights = client.get_video_insights(video_id, token)
                self._write_insights(sheet, row_idx, insights)
                self._log(
                    f"[Insights] Hàng #{row_idx} (vid={video_id}): "
                    f"views={insights['views']}, reach={insights['reach']}, "
                    f"reactions={insights['reactions']}",
                    "success",
                )
                # GAP-2 (anti-spam P2.3 wiring): persist reach into the page-
                # health store so the throttle-detection model has data to work
                # with. The insights fetcher is the natural producer because
                # it already pulls insights at the right cadence (post-24 h).
                try:
                    from core.page_health import _default_store as _ph_default
                    # target_page is the human-readable name we use as the
                    # PageHealthStore key — sufficient for baseline detection.
                    _ph_default().record_reach(
                        page_id   = str(target_page),
                        video_id  = str(video_id),
                        reach     = int(insights.get("reach", 0) or 0),
                    )
                except Exception as _ph_exc:
                    self._log(
                        f"[Insights] page_health.record_reach failed (non-fatal): {_ph_exc}",
                        "warning",
                    )
            except Exception as exc:
                self._log(f"[Insights] Hàng #{row_idx} lỗi fetch: {exc}", "warning")

            # Polite delay between API calls
            self._sleep(2)

    def _find_pending_rows(self, sheet, cutoff: datetime) -> list[dict]:
        """
        Return rows that:
          - have fb_video_id set
          - have no insights_at value
          - have uploaded_at older than cutoff (or uploaded_at missing → skip)
        """
        # Read all data rows
        try:
            result = sheet._retry(
                lambda: sheet._svc().spreadsheets().values()
                .get(
                    spreadsheetId=sheet._sheet_id(),
                    range=f"'{sheet._current_tab}'!A2:ZZ",
                    valueRenderOption="UNFORMATTED_VALUE",
                )
                .execute()
            )
        except Exception as exc:
            self._log(f"[Insights] Đọc sheet thất bại: {exc}", "warning")
            return []

        rows = result.get("values", [])
        pending = []

        for rel, row in enumerate(rows):
            row_idx = rel + 2

            # Must have fb_video_id
            video_id = sheet._get_val(row, "col_fb_video_id").strip()
            if not video_id:
                continue

            # Must NOT already have insights
            insights_at = sheet._get_val(row, "col_insights_at").strip()
            if insights_at:
                continue  # already fetched

            # Must be old enough
            uploaded_at_str = sheet._get_val(row, "col_uploaded_at").strip()
            if not uploaded_at_str:
                continue  # no upload timestamp → skip (can't verify age)

            upload_dt = self._parse_dt(uploaded_at_str)
            if upload_dt is None or upload_dt > cutoff:
                continue  # too recent

            target_page = sheet._get_val(row, "col_target_page").strip()
            pending.append({
                "row_idx":    row_idx,
                "fb_video_id": video_id,
                "target_page": target_page,
            })

        return pending

    def _write_insights(self, sheet, row_idx: int, insights: dict):
        """Write insight values + insights_at timestamp to sheet."""
        updates = {}

        col_map = {
            "col_views":          insights.get("views", 0),
            "col_reach":          insights.get("reach", 0),
            "col_reactions":      insights.get("reactions", 0),
            "col_comments_count": insights.get("comments_count", 0),
            "col_shares":         insights.get("shares", 0),
            "col_minutes_viewed": insights.get("minutes_viewed", 0.0),
        }
        for cfg_key, value in col_map.items():
            col = sheet._col_letter(cfg_key)
            if col:
                updates[col] = value

        # Timestamp
        col = sheet._col_letter("col_insights_at")
        if col:
            updates[col] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        if updates:
            sheet._batch_write(row_idx, updates)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_tabs_to_scan(self) -> list[str]:
        """Return list of sheet tabs to scan (from page_mapping or single tab)."""
        tabs = [
            m.get("sheet_tab", "")
            for m in self._config.get("page_mapping", [])
            if m.get("sheet_tab", "")
        ]
        if not tabs:
            default_tab = self._config.get("sheet_tab", "")
            if default_tab:
                tabs = [default_tab]
        return list(dict.fromkeys(tabs))  # deduplicate, preserve order

    def _find_page_token(self, token_store, page_name: str) -> Optional[str]:
        """Find valid access_token for page_name."""
        try:
            account, page = token_store.find_page_by_name(page_name)
            if account and page and account.is_token_valid():
                return page.access_token
        except Exception:
            pass

        # Fallback: try any valid account's first page
        try:
            for acc in token_store.all_accounts():
                if not acc.is_token_valid():
                    continue
                for pg in acc.get_selected_pages():
                    return pg.access_token
        except Exception:
            pass
        return None

    @staticmethod
    def _parse_dt(s: str) -> Optional[datetime]:
        """Parse uploaded_at string to UTC datetime."""
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y %H:%M:%S",
        ):
            try:
                dt = datetime.strptime(s.strip(), fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None

    def _sleep(self, seconds: float):
        """Interruptible sleep — wakes up immediately if stop_event fires."""
        deadline = time.time() + seconds
        while time.time() < deadline and not self._stop_event.is_set():
            time.sleep(min(1.0, deadline - time.time()))

    def _log(self, msg: str, level: str = "info"):
        logger.info(msg)
        try:
            self._on_log(msg, level)
        except Exception:
            pass
