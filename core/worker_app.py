"""
WorkerApplication — headless publishing worker lifecycle (P1).

Wraps a single SheetRunner / ConcurrentRunner (N workers) behind one
start()/stop()/status() interface so callers (worker_main.py, GUI, future
server code) never need to import gui.* or branch on worker count.

Ownership boundary (AGENTS.md: "Never allow the desktop runner and the
web/server runner to process the same account, page, sheet tab, or job
concurrently"):

  core.sheet_runner already acquires a per-account SessionLock before each
  row is processed, but only once a job is picked up — two runners started
  against the same account can both sit idle "connected" at the same time
  and only collide once a row appears. WorkerApplication closes that gap by
  acquiring a SessionLock for every worker's target account *up front*, for
  the whole run — so the second runner to start fails immediately with
  WorkerOwnershipError instead of racing later.

Crash safety: core.sheet_runner.SheetRunner.run() already catches its own
errors internally and never expected to raise, but the single-worker path
here still runs it under a guarded thread wrapper that guarantees the
stop/lock-release callback fires exactly once even if run() does raise —
otherwise a crash would leak the whole-run ownership lock forever.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from core.concurrent_runner import ConcurrentRunner, WorkerStatus
from core.session_lock import SessionLock, SessionLockError
from core.sheet_runner import SheetRunner

log = logging.getLogger(__name__)


class WorkerOwnershipError(RuntimeError):
    """Another runner (desktop or headless) already owns a target account."""


@dataclass
class WorkerApplicationStatus:
    running: bool
    workers: list = field(default_factory=list)  # list[WorkerStatus]


class _GuardedRunnerThread:
    """Runs `run_fn()` in a daemon thread; guarantees `on_done` fires exactly
    once — on clean return AND on an unexpected exception — so a crashed
    runner can never leave the ownership lock held forever."""

    def __init__(self, run_fn: Callable[[], None], stop_fn: Callable[[], None],
                 on_done: Callable[[], None]):
        self._run_fn  = run_fn
        self._stop_fn = stop_fn
        self._on_done = on_done
        self._thread: Optional[threading.Thread] = None
        self._fire_lock = threading.Lock()
        self._fired = False

    def start(self) -> None:
        self._thread = threading.Thread(target=self._guarded_run, daemon=True)
        self._thread.start()

    def _guarded_run(self) -> None:
        try:
            self._run_fn()
        except Exception:
            log.exception("Worker runner crashed")
        finally:
            self._fire_once()

    def _fire_once(self) -> None:
        with self._fire_lock:
            if self._fired:
                return
            self._fired = True
        self._on_done()

    def stop(self) -> None:
        self._stop_fn()

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def worker_statuses(self) -> list:
        return []


class WorkerApplication:
    """Headless-safe lifecycle wrapper. No gui.* import anywhere in this module."""

    def __init__(
        self,
        workers: list[dict],
        config: dict,
        *,
        platform_filter: str = "",
        on_log: Optional[Callable] = None,
        on_worker_update: Optional[Callable] = None,
        on_all_stopped: Optional[Callable] = None,
    ):
        if not workers:
            raise ValueError("Cần ít nhất 1 worker")

        self._workers_cfg      = list(workers)
        self._config           = config
        self._platform_filter  = (platform_filter or "").strip().lower()
        self._on_log           = on_log           or (lambda m, l: None)
        self._on_worker_update = on_worker_update or (lambda i, s: None)
        self._on_all_stopped   = on_all_stopped   or (lambda: None)

        # Two separate locks by design: _state_lock guards start()/stop()'s
        # transition of self._runner; _notify_lock guards the stopped-once
        # flag. A runner thread that finishes almost immediately (or a stub
        # in tests) can call the stop callback while start() still holds
        # _state_lock — sharing one lock for both would deadlock that case.
        self._state_lock  = threading.Lock()
        self._notify_lock = threading.Lock()
        self._locks:  list[SessionLock] = []
        self._runner = None  # _GuardedRunnerThread | ConcurrentRunner
        self._stopped_notified = False
        self._single_runner_status: Optional[WorkerStatus] = None

    # ── Public lifecycle ────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return bool(self._runner is not None and self._runner.is_running)

    def worker_statuses(self) -> list:
        if self._runner is None:
            return []
        return self._runner.worker_statuses()

    def status(self) -> WorkerApplicationStatus:
        return WorkerApplicationStatus(running=self.is_running, workers=self.worker_statuses())

    def start(self) -> None:
        """Idempotent: calling start() while already running is a no-op."""
        with self._state_lock:
            if self.is_running:
                return
            self._stopped_notified = False
            self._acquire_ownership_locks()
            try:
                self._runner = self._build_runner()
                self._runner.start()
            except Exception:
                self._release_ownership_locks()
                self._runner = None
                raise

    def stop(self) -> None:
        """Signal all workers to stop. Non-blocking — poll is_running or use
        wait_stopped() to observe completion."""
        runner = self._runner
        if runner is not None:
            runner.stop()

    def wait_stopped(self, timeout: Optional[float] = None, poll_interval: float = 0.2) -> bool:
        """Block until all workers report stopped, or timeout elapses.
        Returns True if stopped, False on timeout."""
        deadline = None if timeout is None else time.monotonic() + timeout
        while self.is_running:
            if deadline is not None and time.monotonic() >= deadline:
                return False
            time.sleep(poll_interval)
        return True

    # ── Internals ────────────────────────────────────────────────────────────

    def _build_runner(self):
        if len(self._workers_cfg) == 1:
            w = self._workers_cfg[0]
            stop_event = threading.Event()
            runner = SheetRunner(
                config          = self._config,
                page_name       = w.get("page", ""),
                sheet_tab       = w.get("tab", ""),
                sheet_id        = w.get("sheet_id", ""),
                page_id         = w.get("page_id", ""),
                account_id      = w.get("account_id", ""),
                stop_event      = stop_event,
                on_log          = self._on_log,
                on_status       = lambda m: self._on_worker_update(0, self._single_status(m)),
                platform_filter = self._platform_filter,
            )
            self._single_runner_status = WorkerStatus(
                tab=w.get("tab", ""), page=w.get("page", ""),
                sheet_id=w.get("sheet_id", ""), page_id=w.get("page_id", ""),
                account_id=w.get("account_id", ""),
            )
            return _GuardedRunnerThread(
                run_fn=runner.run, stop_fn=stop_event.set, on_done=self._notify_stopped_once,
            )

        return ConcurrentRunner(
            workers          = list(self._workers_cfg),
            config           = self._config,
            on_log           = self._on_log,
            on_worker_update = self._on_worker_update,
            on_all_stopped   = self._notify_stopped_once,
            platform_filter  = self._platform_filter,
        )

    def _single_status(self, msg: str) -> WorkerStatus:
        self._single_runner_status.last_msg = msg[:80]
        return self._single_runner_status

    def _notify_stopped_once(self) -> None:
        with self._notify_lock:
            if self._stopped_notified:
                return
            self._stopped_notified = True
        self._release_ownership_locks()
        self._on_all_stopped()

    # ── Ownership lock ──────────────────────────────────────────────────────

    def _lock_target(self, w: dict) -> str:
        return (
            str(w.get("account_id", "") or "").strip()
            or str(w.get("page_id", "") or "").strip()
            or str(w.get("page", "") or "").strip()
            or str(w.get("tab", "") or "").strip()
        )

    def _acquire_ownership_locks(self) -> None:
        if not self._config.get("anti_spam_session_lock_enabled", True):
            return
        platform = self._platform_filter or "facebook"
        acquired: list[SessionLock] = []
        try:
            for w in self._workers_cfg:
                target = self._lock_target(w)
                if not target:
                    continue
                lock = SessionLock(account_id=target, platform=platform)
                try:
                    lock.acquire()
                except SessionLockError as exc:
                    raise WorkerOwnershipError(str(exc)) from exc
                acquired.append(lock)
        except WorkerOwnershipError:
            for lock in acquired:
                lock.release()
            raise
        self._locks = acquired

    def _release_ownership_locks(self) -> None:
        for lock in self._locks:
            try:
                lock.release()
            except Exception:
                pass
        self._locks = []
