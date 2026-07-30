"""
ConcurrentRunner — runs N SheetRunner workers in parallel.

Each worker handles its own sheet-tab → FB-page pipeline.
All workers share one RateLimiter to prevent per-page rate-limit collisions.

Usage:
    runner = ConcurrentRunner(
        workers=[{"tab": "Tab1", "page": "Page A"}, {"tab": "Tab2", "page": "Page B"}],
        config=config,
        on_log=lambda msg, level: ...,
        on_worker_update=lambda idx, status: ...,
        on_all_stopped=lambda: ...,
    )
    runner.start()
    # later:
    runner.stop()
    runner.is_running        # bool
    runner.worker_statuses() # list[WorkerStatus]
"""
from __future__ import annotations

import logging
import threading
import time
import traceback
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)

from core.rate_limiter import RateLimiter


@dataclass
class WorkerStatus:
    tab: str
    page: str
    sheet_id: str = ""    # multi-sheet: spreadsheet this worker addresses
    page_id: str = ""     # FB Page ID — disambiguates pages with same name
    account_id: str = ""  # FB account id — for log clarity
    account_name: str = ""  # cached account display name (for UI labels)
    state: str = "idle"    # idle | connecting | running | stopped | error
    current_job: str = ""
    jobs_done: int = 0
    jobs_error: int = 0
    last_msg: str = ""


class ConcurrentRunner:
    """Manages N parallel SheetRunner workers sharing one RateLimiter."""

    def __init__(
        self,
        workers: list[dict],
        config: dict,
        on_log: Optional[Callable] = None,
        on_worker_update: Optional[Callable] = None,
        on_all_stopped: Optional[Callable] = None,
        platform_filter: str = "",
    ):
        if not workers:
            raise ValueError("Cần ít nhất 1 worker")

        self._config           = config
        self._platform_filter  = (platform_filter or "").strip().lower()
        self._on_log           = on_log            or (lambda m, l: None)
        self._on_worker_update = on_worker_update  or (lambda i, s: None)
        self._on_all_stopped   = on_all_stopped    or (lambda: None)

        self._stop_event    = threading.Event()
        self._threads:  list[threading.Thread] = []
        self._lock      = threading.Lock()
        self._stopped_count = 0

        self._statuses: list[WorkerStatus] = [
            WorkerStatus(
                tab=w.get("tab", ""),
                page=w.get("page", ""),
                sheet_id=w.get("sheet_id", ""),
                page_id=w.get("page_id", ""),
                account_id=w.get("account_id", ""),
                account_name=w.get("account_name", ""),
            )
            for w in workers
        ]

        # Per-platform rate limit values: a TikTok runner uses tt_* keys (with
        # fallback to shared keys when tt_* is 0/empty); FB runners use the
        # shared keys directly. See core/utils.get_platform_config().
        from core.utils import get_platform_config
        _p = self._platform_filter or "facebook"

        shared_limiter = RateLimiter(
            max_concurrent             = int(config.get("max_concurrent_uploads_per_page", 1)),
            min_interval_s             = float(get_platform_config(config, _p, "min_interval_per_page_s", 30.0)),
            min_inter_page_interval_s  = float(get_platform_config(config, _p, "min_inter_page_interval_s", 0.0)),
            jitter_s                   = float(get_platform_config(config, _p, "jitter_s", 0.0)),
            active_hours_start         = int(get_platform_config(config, _p, "active_hours_start", 0)),
            active_hours_end           = int(get_platform_config(config, _p, "active_hours_end", 0)),
            max_posts_per_page_per_day    = int(get_platform_config(config, _p, "max_posts_per_page_per_day", 0)),
            max_posts_per_account_per_day = int(get_platform_config(config, _p, "max_posts_per_account_per_day", 0)),
            timezone_name                 = str(config.get("timezone", "Asia/Ho_Chi_Minh")),
        )

        from core.sheet_runner import SheetRunner
        self._runners: list[SheetRunner] = [
            SheetRunner(
                config       = config,
                page_name    = workers[i].get("page", ""),
                sheet_tab    = workers[i].get("tab", ""),
                sheet_id     = workers[i].get("sheet_id", ""),
                page_id      = workers[i].get("page_id", ""),
                account_id   = workers[i].get("account_id", ""),
                stop_event   = self._stop_event,
                on_log       = self._make_on_log(i),
                on_status    = self._make_on_status(i),
                on_job_start = self._make_on_job_start(i),
                on_job_done  = self._make_on_job_done(i),
                on_job_error = self._make_on_job_error(i),
                on_idle      = self._make_on_idle(i),
                on_stopped   = self._make_on_stopped(i),
                rate_limiter    = shared_limiter,
                platform_filter = self._platform_filter,
            )
            for i in range(len(workers))
        ]

    # ── Public ────────────────────────────────────────────────────────────────

    def start(self):
        self._stop_event.clear()
        self._stopped_count = 0
        self._threads.clear()
        for i, runner in enumerate(self._runners):
            self._statuses[i].state = "connecting"
            self._on_worker_update(i, self._statuses[i])
            t = threading.Thread(
                target=self._thread_target, args=(i,), daemon=True,
                name=f"CWorker-{i + 1}-{runner.sheet_tab}",
            )
            self._threads.append(t)
            t.start()

    def stop(self):
        self._stop_event.set()

    @property
    def is_running(self) -> bool:
        return any(t.is_alive() for t in self._threads)

    def worker_statuses(self) -> list[WorkerStatus]:
        return list(self._statuses)

    # ── Thread target (crash-safe) ────────────────────────────────────────────

    def _thread_target(self, i: int):
        """
        Safe wrapper around runner.run() with P3 auto-restart.

        Clean exit  → runner.run() calls on_stopped itself → _stopped_count++.
        Crash       → caught here → log + Telegram → restart up to max_restarts.
        After all restarts exhausted → permanent error → _stopped_count++ manually.
        """
        max_restarts = int(self._config.get("worker_max_restarts", 2))
        restart_count = 0

        while True:
            runner = self._runners[i]
            try:
                runner.run()
                # Clean exit — on_stopped already incremented _stopped_count.
                return
            except Exception as exc:
                tb = traceback.format_exc()
                restart_count += 1
                err_msg = f"[W{i + 1}] Crash (lần {restart_count}/{max_restarts}): {exc}"
                logger.error("%s\n%s", err_msg, tb)

                st = self._statuses[i]
                st.last_msg = str(exc)[:80]
                self._on_log(err_msg, "error")

                if restart_count <= max_restarts and not self._stop_event.is_set():
                    wait = 30 * restart_count
                    st.state       = "connecting"
                    st.current_job = f"Restart sau {wait}s..."
                    self._on_worker_update(i, st)
                    self._on_log(
                        f"[W{i + 1}] Tự khởi động lại sau {wait}s "
                        f"(lần {restart_count}/{max_restarts})",
                        "warning",
                    )
                    # Reset stop event only for this runner? No — shared stop_event.
                    # We just sleep and retry; if stop fires during sleep, runner will
                    # detect it on next tick via check_stop().
                    time.sleep(wait)
                    continue

                # Permanent crash — notify and count as stopped
                err_msg_final = f"[W{i + 1}] Crash vĩnh viễn sau {max_restarts} lần restart: {exc}"
                logger.error(err_msg_final)
                st.state       = "error"
                st.current_job = ""
                self._on_worker_update(i, st)
                self._on_log(err_msg_final, "error")

                try:
                    from utils.notifier import get_notifier
                    get_notifier().notify_worker_crash(i + 1, str(exc))
                except Exception:
                    pass

                with self._lock:
                    self._stopped_count += 1
                    all_done = self._stopped_count >= len(self._runners)
                if all_done:
                    self._on_all_stopped()
                return

    # ── Callback factories ────────────────────────────────────────────────────

    def _make_on_log(self, i: int) -> Callable:
        def _cb(msg: str, level: str):
            self._statuses[i].last_msg = msg[:80]
            self._on_log(f"[W{i + 1}] {msg}", level)
        return _cb

    def _make_on_status(self, i: int) -> Callable:
        def _cb(msg: str):
            self._statuses[i].last_msg = msg[:80]
            self._on_worker_update(i, self._statuses[i])
        return _cb

    def _make_on_job_start(self, i: int) -> Callable:
        def _cb(task: dict):
            st = self._statuses[i]
            st.state       = "running"
            st.current_job = f"#{task.get('row_idx', '?')} {task.get('title', '')[:30]}"
            self._on_worker_update(i, st)
        return _cb

    def _make_on_job_done(self, i: int) -> Callable:
        def _cb(task: dict, link: str):
            st = self._statuses[i]
            st.jobs_done  += 1
            st.current_job = ""
            st.state       = "running"
            self._on_worker_update(i, st)
        return _cb

    def _make_on_job_error(self, i: int) -> Callable:
        def _cb(task: dict, error: str):
            st = self._statuses[i]
            st.jobs_error += 1
            st.current_job = ""
            st.last_msg    = error[:60]
            self._on_worker_update(i, st)
        return _cb

    def _make_on_idle(self, i: int) -> Callable:
        def _cb():
            st = self._statuses[i]
            st.current_job = "⏳ Đang chờ job..."
            self._on_worker_update(i, st)
        return _cb

    def _make_on_stopped(self, i: int) -> Callable:
        def _cb():
            st = self._statuses[i]
            st.state       = "stopped"
            st.current_job = ""
            self._on_worker_update(i, st)
            with self._lock:
                self._stopped_count += 1
                all_done = self._stopped_count >= len(self._runners)
            if all_done:
                self._on_all_stopped()
                # P1: notify batch done via Telegram
                try:
                    total_done  = sum(s.jobs_done  for s in self._statuses)
                    total_error = sum(s.jobs_error for s in self._statuses)
                    from utils.notifier import get_notifier
                    get_notifier().notify_batch_done(total_done, total_error)
                except Exception:
                    pass
        return _cb
