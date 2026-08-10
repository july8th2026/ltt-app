"""
worker_main.py — headless CLI entry point for the publishing worker (P1).

Starts the same SheetRunner/ConcurrentRunner pipeline the desktop GUI uses,
without importing customtkinter or any gui.* module. Intended for future
server/service use, driven by the same store the web app writes
until a later phase's exit gate.

Usage:
    python worker_main.py [--config data/config.json] [--workers workers.json]
                           [--platform facebook|tiktok]

Without --workers, the worker list comes from data/workers.json — the same
store the desktop Sheet Runner tab writes, so a headless run reproduces
exactly what the operator configured in the GUI. If neither source yields
a worker, this exits with code 3 rather than guessing.

--workers points to a JSON file containing a list of worker dicts, e.g.:
    [{"tab": "Tab1", "page": "Page A", "sheet_id": "...", "page_id": "...",
      "account_id": "..."}]

Stops cleanly on SIGINT/SIGTERM: signals set the stop event, workers finish
their current step, and the process exits after all workers report stopped.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import threading

from core.worker_app import WorkerApplication, WorkerOwnershipError
from platform_core.observability import configure_logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
configure_logging(component="publisher-worker")
log = logging.getLogger("worker_main")


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class NoWorkersError(RuntimeError):
    """No worker list could be resolved — refuse to guess."""


def resolve_workers(path: str | None, platform: str) -> list[dict]:
    """Resolve the worker list, in precedence order:

      1. an explicit --workers file;
      2. the shared store the web app writes (data/workers.json).

    There is deliberately NO fallback to the legacy top-level
    `sheet_tab`/`sheet_id` config keys. The 2026-07-29 audit
    (docs/_luutru/AUDIT_REPORT.md) showed that guess targeted a tab whose columns
    did not match the configured mapping, so the "fallback" produced a run
    that connected successfully and then failed mid-flight. Failing loudly
    here is strictly better than silently running the wrong tab.
    """
    if path:
        with open(path, "r", encoding="utf-8") as f:
            workers = json.load(f)
        if not isinstance(workers, list) or not workers:
            raise ValueError(
                f"{path} must contain a non-empty JSON array of worker dicts"
            )
        return workers

    from core.worker_store import default_path, load_workers as load_stored
    stored = load_stored(platform=platform or None)
    if stored:
        return stored

    raise NoWorkersError(
        "Không tìm thấy worker nào để chạy.\n"
        f"  - Chưa có worker đã lưu trong {default_path()}\n"
        "  - Và không có --workers <file.json>\n"
        "Cách sửa: mở trang Sheet FB / Sheet TikTok trên web → thêm worker "
        "(sẽ tự lưu), "
        "hoặc truyền --workers với một file JSON."
    )


def _on_log(msg: str, level: str) -> None:
    getattr(log, level if level in ("debug", "info", "warning", "error") else "info")(msg)


def _on_worker_update(idx: int, status) -> None:
    log.info("[W%d] %s | job=%s done=%d error=%s", idx + 1, status.state,
              status.current_job, status.jobs_done, status.jobs_error)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Headless publishing worker")
    # Mac dinh phai giai qua ranh gioi duong dan, khong phai chuoi tuong doi
    # theo thu muc lam viec: worker chay nhu mot dich vu Windows, thu muc lam
    # viec cua no la app\ chu khong phai goc du an.
    parser.add_argument("--config", default=None,
                        help="Mac dinh: LTT_CONFIG_PATH, hoac data/config.json "
                             "trong thu muc du lieu dang chay")
    parser.add_argument("--workers", default=None, help="Path to a JSON worker-list file")
    parser.add_argument("--platform", default="", choices=["", "facebook", "tiktok"])
    args = parser.parse_args(argv)

    config_path = args.config
    if config_path is None:
        from platform_core.runtime_paths import resolve_runtime_paths
        config_path = resolve_runtime_paths().config_path
    config = load_config(config_path)
    try:
        workers = resolve_workers(args.workers, args.platform)
    except NoWorkersError as exc:
        log.error("%s", exc)
        return 3

    stopped = threading.Event()
    app = WorkerApplication(
        workers          = workers,
        config           = config,
        platform_filter  = args.platform,
        on_log           = _on_log,
        on_worker_update = _on_worker_update,
        on_all_stopped   = stopped.set,
    )

    def _handle_signal(signum, _frame):
        log.info("Received signal %s — stopping workers...", signum)
        app.stop()

    signal.signal(signal.SIGINT, _handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_signal)

    try:
        app.start()
    except WorkerOwnershipError as exc:
        log.error("Cannot start — target already owned by another runner: %s", exc)
        return 2

    log.info("Worker started. Press Ctrl+C to stop.")
    stopped.wait()
    log.info("All workers stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
