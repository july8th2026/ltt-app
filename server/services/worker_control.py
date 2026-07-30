"""
worker_control.py — start/stop/inspect the publishing worker from the web
dashboard (P6).

Architecture (ADR-004): the dashboard is a *control plane*. Starting a run
here hands work to P1's `WorkerApplication`, which owns its own daemon
threads. Closing the browser, logging out, or losing the HTTP connection
does not stop the run — only an explicit stop, or the process exiting,
does.

Single-orchestrator invariant (ADR-005): exactly one `WorkerApplication`
per process, held here as module state. Cross-process safety comes from
`WorkerApplication`'s own SessionLock, which is what stops a second runner
and this server from driving the same account simultaneously.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

from core.worker_app import WorkerApplication, WorkerOwnershipError

# Bounded so a long-running worker cannot grow this without limit.
_LOG_CAPACITY = 300


class WorkerBusyError(RuntimeError):
    """A run is already in progress in this process."""


class NoWorkersConfiguredError(RuntimeError):
    """Nothing to run — the worker list is empty."""


@dataclass
class WorkerSnapshot:
    running:   bool = False
    platform:  str = ""
    workers:   list = field(default_factory=list)   # list[dict] view models
    log:       list = field(default_factory=list)   # newest last
    last_error: str = ""


class WorkerController:
    """Process-wide worker lifecycle owner. Thread-safe."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._app: WorkerApplication | None = None
        self._platform = ""
        self._log: list = []
        self._last_error = ""

    # ── logging adapter ──────────────────────────────────────────────────

    def _on_log(self, message: str, level: str) -> None:
        with self._lock:
            self._log.append({"level": level, "message": str(message)[:400]})
            if len(self._log) > _LOG_CAPACITY:
                del self._log[: len(self._log) - _LOG_CAPACITY]

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self, workers: list, config: dict, platform: str = "") -> None:
        """Begin a run. Raises WorkerBusyError / NoWorkersConfiguredError /
        WorkerOwnershipError — all of which the caller should surface to the
        operator rather than swallow."""
        if not workers:
            raise NoWorkersConfiguredError(
                "Chưa có worker nào được cấu hình. Thêm worker ở tab Sheet "
                "ở trang Sheet FB / Sheet TikTok (danh sách được lưu và dùng chung)."
            )

        with self._lock:
            if self._app is not None and self._app.is_running:
                raise WorkerBusyError(
                    "Đang có một phiên chạy. Dừng phiên hiện tại trước khi bắt đầu phiên mới."
                )
            self._log = []
            self._last_error = ""
            self._platform = platform
            app = WorkerApplication(
                workers=workers, config=config, platform_filter=platform,
                on_log=self._on_log,
            )
            self._app = app

        # start() outside the lock: it acquires SessionLocks and spawns
        # threads, and a stop callback firing immediately would otherwise
        # contend for a lock this thread still holds.
        try:
            app.start()
        except WorkerOwnershipError as exc:
            with self._lock:
                self._app = None
                self._last_error = str(exc)
            raise

    def stop(self) -> None:
        app = self._app
        if app is not None:
            app.stop()

    def snapshot(self) -> WorkerSnapshot:
        with self._lock:
            app = self._app
            log = list(self._log)
            last_error = self._last_error
            platform = self._platform

        if app is None:
            return WorkerSnapshot(running=False, platform=platform,
                                  log=log, last_error=last_error)

        statuses = []
        for s in app.worker_statuses():
            statuses.append({
                "tab":         getattr(s, "tab", ""),
                "page":        getattr(s, "page", ""),
                "state":       getattr(s, "state", ""),
                "current_job": getattr(s, "current_job", ""),
                "jobs_done":   getattr(s, "jobs_done", 0),
                "jobs_error":  getattr(s, "jobs_error", 0),
                "last_msg":    getattr(s, "last_msg", ""),
            })

        return WorkerSnapshot(
            running=app.is_running, platform=platform, workers=statuses,
            log=log, last_error=last_error,
        )


_controller: WorkerController | None = None
_controller_lock = threading.Lock()


def get_controller() -> WorkerController:
    """Process-wide singleton — enforces the one-orchestrator invariant."""
    global _controller
    if _controller is None:
        with _controller_lock:
            if _controller is None:
                _controller = WorkerController()
    return _controller


def reset_controller_for_tests() -> None:
    """Drop the singleton. Tests only — module state would otherwise leak
    a running worker between test cases."""
    global _controller
    with _controller_lock:
        _controller = None
