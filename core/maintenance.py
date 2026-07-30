"""
Background maintenance — periodic clean-up tasks (GAP-8).

Runs as a daemon thread. Currently handles:
  • Pruning old content_history records (keeps DB small)
  • Pruning old page_health reach samples
  • Future: log rotation, page_warmup cache refresh

Designed to be fire-and-forget — runs on a long timer (24 h default) so the
overhead is negligible. Errors are swallowed silently to avoid disrupting
the upload pipeline.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

_SLEEP_S            = 24 * 3600    # 24h between sweeps
_DEFAULT_RETENTION  = 90            # keep records 90 days


class MaintenanceDaemon:
    """Single daemon that periodically prunes old DB records."""

    def __init__(
        self,
        config:     dict,
        stop_event: Optional[threading.Event] = None,
    ):
        self._config       = config
        self._stop         = stop_event or threading.Event()
        self._thread:      Optional[threading.Thread] = None
        self._retention_d  = int(config.get("anti_spam_retention_days", _DEFAULT_RETENTION))

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="MaintenanceDaemon",
        )
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        # Run once at startup (after a brief delay so OAuth etc. settles),
        # then every _SLEEP_S seconds.
        if not self._stop.wait(timeout=60):
            self._do_sweep()
        while not self._stop.wait(timeout=_SLEEP_S):
            self._do_sweep()

    def _do_sweep(self):
        """One pass of all maintenance tasks. Never raises."""
        # Task 1 — content_history prune
        try:
            from core.content_history import get_default_store
            n = get_default_store().purge_older_than(self._retention_d)
            if n > 0:
                logger.info("[Maintenance] Pruned %d content_history rows (> %d days)",
                            n, self._retention_d)
        except Exception as exc:
            logger.debug("[Maintenance] content_history prune skipped: %s", exc)

        # Task 2 — Meta App status probe (Round 1.2)
        # Check if the configured Meta App has been disabled/suspended by FB.
        # When it has, Telegram alert the user so they don't waste a day
        # debugging "why are uploads failing".
        if self._config.get("anti_spam_app_status_check", True):
            try:
                from core.app_status import (
                    check_app_status, is_app_disabled, AppStatus,
                )
                report = check_app_status(self._config)
                if is_app_disabled(report):
                    logger.warning(
                        "[Maintenance] Meta App disabled/suspended: %s (%s)",
                        report.message, report.error_code,
                    )
                    try:
                        from utils.notifier import get_notifier
                        get_notifier().notify_abuse_signal(
                            target     = report.app_id or "meta_app",
                            error_code = report.error_code,
                            message    = f"App {report.status.value}: {report.message}",
                        )
                    except Exception:
                        pass
                elif report.status is AppStatus.OK:
                    logger.debug("[Maintenance] Meta App status OK")
            except Exception as exc:
                logger.debug("[Maintenance] app_status check skipped: %s", exc)

            # Sprint TT-1.5: probe TikTok app the same way
            try:
                from core.app_status import (
                    check_tiktok_app_status, is_app_disabled, AppStatus,
                )
                tt_report = check_tiktok_app_status(self._config)
                if is_app_disabled(tt_report):
                    logger.warning(
                        "[Maintenance] TikTok app disabled/suspended: %s (%s)",
                        tt_report.message, tt_report.error_code,
                    )
                    try:
                        from utils.notifier import get_notifier
                        get_notifier().notify_abuse_signal(
                            target     = tt_report.app_id or "tiktok_app",
                            error_code = tt_report.error_code,
                            message    = f"TT App {tt_report.status.value}: {tt_report.message}",
                        )
                    except Exception:
                        pass
                elif tt_report.status is AppStatus.OK:
                    logger.debug("[Maintenance] TikTok app status OK")
            except Exception as exc:
                logger.debug("[Maintenance] tiktok app_status check skipped: %s", exc)

        # Task 3 — varied tmp file cleanup (Sprint A4)
        try:
            from core.video_variation import cleanup_varied_tmp
            cleanup_varied_tmp(older_than_hours=24)
        except Exception as exc:
            logger.debug("[Maintenance] video_variation cleanup skipped: %s", exc)
