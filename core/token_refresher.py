"""
Background token refresher.

Runs as a daemon thread. Every `check_interval_s` seconds it scans all accounts
in TokenStore and, for any token within `refresh_threshold_days` days of expiry,
attempts to extend it using the fb_exchange_token endpoint.

Facebook long-lived tokens (60-day) can be refreshed by passing them as the
fb_exchange_token again — this resets the 60-day clock.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Optional

from core.graph_client import GraphClient, GraphError
from core.token_store import AccountInfo, TokenStore
from core.utils import graph_api_version


class TokenRefresher:
    """
    Daemon thread that keeps Facebook user tokens alive.

    Callbacks (called from the refresher thread — GUI must use after()):
        on_refreshed(account_name)      — token successfully refreshed
        on_expired(account_name)        — token already expired, cannot refresh
        on_error(account_name, msg)     — refresh attempt failed
        on_status(msg)                  — informational status message
    """

    def __init__(
        self,
        config: dict,
        token_store: TokenStore,
        check_interval_s: int  = 3600,
        refresh_threshold_days: int = 7,
        on_refreshed: Callable[[str], None]       = None,
        on_expired:   Callable[[str], None]       = None,
        on_error:     Callable[[str, str], None]  = None,
        on_status:    Callable[[str], None]       = None,
    ):
        self._config    = config
        self._store     = token_store
        self._interval  = check_interval_s
        self._threshold = refresh_threshold_days

        self._on_refreshed = on_refreshed or (lambda name: None)
        self._on_expired   = on_expired   or (lambda name: None)
        self._on_error     = on_error     or (lambda name, msg: None)
        self._on_status    = on_status    or (lambda msg: None)

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="TokenRefresher"
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _run(self):
        self._on_status("[Refresher] Token refresher bắt đầu")
        # First check immediately
        self._check_all()
        while not self._stop_event.wait(timeout=self._interval):
            self._check_all()
        self._on_status("[Refresher] Token refresher dừng")

    def _check_all(self):
        accounts = self._store.all_accounts()
        if not accounts:
            return

        app_id     = self._config.get("meta_app_id", "").strip()
        app_secret = self._config.get("meta_app_secret", "").strip()

        if not app_id or not app_secret:
            return   # Can't refresh without app credentials

        client = GraphClient(
            version=graph_api_version(self._config), timeout=30, max_retries=2
        )

        for account in accounts:
            if self._stop_event.is_set():
                break
            self._check_one(account, app_id, app_secret, client)

    def _check_one(
        self,
        account: AccountInfo,
        app_id: str,
        app_secret: str,
        client: GraphClient,
    ):
        # System User (BM) tokens cannot be refreshed via fb_exchange_token.
        # They are either never-expiring or renewed manually in Business
        # Settings — attempting an exchange would only spam errors.
        if getattr(account, "is_system_user", False):
            return

        days = account.days_until_expiry()

        if days == -1:
            return   # permanent token (page access token), no refresh needed

        if days <= 0:
            self._on_expired(account.name)
            return

        if days > self._threshold:
            return   # still fresh, skip

        # Attempt refresh
        self._on_status(
            f"[Refresher] Làm mới token: {account.name} (còn {days} ngày)"
        )
        try:
            new_token, expires_in = client.exchange_short_for_long(
                app_id, app_secret, account.user_token
            )
            expires_at = (
                datetime.now() + timedelta(seconds=expires_in)
            ).isoformat()

            account.user_token        = new_token
            account.token_expires_at  = expires_at
            self._store.save_account(account)

            self._on_refreshed(account.name)
            self._on_status(
                f"[Refresher] Token {account.name} đã làm mới — "
                f"hết hạn {expires_in // 86400} ngày nữa"
            )
        except GraphError as exc:
            self._on_error(account.name, str(exc))
            self._on_status(
                f"[Refresher] Lỗi làm mới token {account.name}: {exc}"
            )
        except Exception as exc:
            self._on_error(account.name, str(exc))

    # ── One-shot health check ──────────────────────────────────────────────────

    def health_summary(self) -> list[dict]:
        """
        Return status for each account: {name, days, status}.
        status: 'ok' | 'warning' | 'expired' | 'permanent'
        """
        result = []
        for acc in self._store.all_accounts():
            days = acc.days_until_expiry()
            if days == -1:
                status = "permanent"
            elif days > self._threshold:
                status = "ok"
            elif days > 0:
                status = "warning"
            else:
                status = "expired"
            result.append({
                "name":   acc.name,
                "days":   days,
                "status": status,
            })
        return result
