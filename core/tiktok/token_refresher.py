"""
token_refresher.py — Background daemon that proactively refreshes TikTok
access tokens before they expire.

Design:
  • Runs in a daemon thread; caller passes a threading.Event to stop it.
  • Every `check_interval_s` seconds it scans all saved TikTok accounts.
  • If an account's access token expires within `refresh_before_h` hours,
    it calls TikTokAuthManager.refresh_access_token() automatically.
  • On failure it logs a warning but does NOT crash — the upload path has
    its own just-in-time refresh fallback.
  • Optionally calls `on_token_refreshed(account)` callback after a
    successful refresh so the GUI can update its display.

Usage (start once at app startup):
    from core.tiktok.token_refresher import TikTokTokenRefresher

    refresher = TikTokTokenRefresher(
        config        = config,
        stop_event    = app_stop_event,
        on_log        = logger.info,
        on_refreshed  = account_tab.refresh_list,   # optional
    )
    refresher.start()   # non-blocking; runs as daemon thread
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Optional

_DEFAULT_CHECK_INTERVAL_S = 3600   # scan every hour
_DEFAULT_REFRESH_BEFORE_H = 6     # refresh if < 6 h until expiry


class TikTokTokenRefresher:
    """
    Proactive TikTok access-token refresh daemon.

    Parameters
    ----------
    config : dict
        The app config dict (must contain tiktok_client_key / tiktok_client_secret).
    stop_event : threading.Event
        Signal the daemon to stop cleanly; set it before joining the thread.
    on_log : callable, optional
        ``on_log(message: str)`` — receives human-readable status lines.
    on_refreshed : callable, optional
        ``on_refreshed(account: TikTokAccount)`` — called after each successful
        refresh so the GUI can reload the account list.
    check_interval_s : int
        How often to scan accounts (default 3 600 s = 1 h).
    refresh_before_h : int
        Refresh when access-token lifetime drops below this many hours (default 6).
    """

    def __init__(
        self,
        config: dict,
        stop_event: threading.Event,
        on_log: Optional[Callable[[str], None]] = None,
        on_refreshed: Optional[Callable] = None,
        check_interval_s: int = _DEFAULT_CHECK_INTERVAL_S,
        refresh_before_h: int = _DEFAULT_REFRESH_BEFORE_H,
    ):
        self._config           = config
        self._stop_event       = stop_event
        self._on_log           = on_log or (lambda _: None)
        self._on_refreshed     = on_refreshed or (lambda _: None)
        self._check_interval_s = check_interval_s
        self._refresh_before_h = refresh_before_h

        self._thread: Optional[threading.Thread] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background refresh daemon (non-blocking)."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run_loop,
            name="TikTokTokenRefresher",
            daemon=True,
        )
        self._thread.start()
        self._on_log("[TikTok Refresher] Đã khởi động daemon làm mới token.")

    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run_loop(self) -> None:
        """Main loop: sleep → scan → sleep → …"""
        self._on_log(
            f"[TikTok Refresher] Vòng lặp bắt đầu "
            f"(kiểm tra mỗi {self._check_interval_s // 60} phút, "
            f"refresh nếu còn < {self._refresh_before_h} giờ)."
        )

        while not self._stop_event.is_set():
            try:
                self._scan_and_refresh()
            except Exception as exc:
                self._on_log(f"[TikTok Refresher] Lỗi không mong đợi: {exc}")

            # Sleep in 60-second chunks so we respond promptly to stop_event
            waited = 0
            while waited < self._check_interval_s:
                if self._stop_event.is_set():
                    break
                time.sleep(min(60, self._check_interval_s - waited))
                waited += 60

        self._on_log("[TikTok Refresher] Daemon đã dừng.")

    def _scan_and_refresh(self) -> None:
        """Load all accounts and refresh any that are close to expiry."""
        from core.tiktok.token_store import TikTokTokenStore

        store = TikTokTokenStore()   # BUG-05 fix: was incorrectly passing config dict as path
        accounts = store.all_accounts()

        if not accounts:
            return

        self._on_log(
            f"[TikTok Refresher] Kiểm tra {len(accounts)} tài khoản…"
        )

        for account in accounts:
            if self._stop_event.is_set():
                return
            self._maybe_refresh(store, account)

    def _maybe_refresh(self, store, account) -> None:
        """Refresh *account* if its access token is about to expire."""
        from core.tiktok.token_store import TikTokTokenStore  # noqa: F401

        days = account.days_until_expiry()
        hours_remaining = days * 24

        # Nothing to do if still plenty of time
        if hours_remaining > self._refresh_before_h and account.is_token_valid():
            return

        # Can't refresh if refresh token is also expired
        if not account.is_refresh_valid():
            self._on_log(
                f"[TikTok Refresher] ⚠  {account.display_name}: "
                f"refresh token hết hạn — cần đăng nhập lại."
            )
            return

        self._on_log(
            f"[TikTok Refresher] 🔄 {account.display_name}: "
            f"access token còn {hours_remaining:.1f}h — đang làm mới…"
        )

        try:
            from core.tiktok.auth_manager import TikTokAuthManager
            mgr = TikTokAuthManager(self._config)
            new_account = mgr.refresh_access_token(account)
            store.upsert_account(new_account)
            self._on_log(
                f"[TikTok Refresher] ✅ {new_account.display_name}: "
                f"token mới hết hạn sau {new_account.days_until_expiry():.1f} ngày."
            )
            self._on_refreshed(new_account)

        except Exception as exc:
            self._on_log(
                f"[TikTok Refresher] ❌ {account.display_name}: "
                f"làm mới thất bại — {exc}"
            )
