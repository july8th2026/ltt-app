"""
worker_store.py — persist the Sheet Runner worker list (PA-5).

Before this, the worker list lived only in `gui/sheet_runner_tab.py`'s
in-memory `self._workers` (docs/_luutru/AUDIT_REPORT.md finding D3):

  - the operator had to re-add every worker on each app launch;
  - no headless/server process could reproduce the real configuration,
    which is why `worker_main.py`'s legacy "guess from config.sheet_tab"
    fallback pointed at a tab whose columns did not match.

Storage: `data/workers.json`, written atomically, schema-versioned so a
future shape change cannot be silently misread by an older build.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from core.runtime_paths import resolve_runtime_paths
from utils.atomic_io import atomic_write_json

WORKERS_SCHEMA_VERSION = 1

# Only these keys are persisted. GUI rows may carry extra display-only
# fields (e.g. cached account_name); persisting them would let stale
# display data outlive the account it described.
_WORKER_FIELDS = ("tab", "page", "sheet_id", "page_id", "account_id", "platform")


class WorkerStoreError(RuntimeError):
    """workers.json exists but cannot be used."""


def default_path(env: Optional[dict] = None) -> str:
    return os.path.join(resolve_runtime_paths(env).data_dir, "workers.json")


def _clean(worker: dict) -> dict:
    return {k: str(worker.get(k, "") or "").strip() for k in _WORKER_FIELDS}


def _normalise_platform(platform: str) -> str:
    """'' (legacy single-platform mode) is stored as 'facebook' so the
    Sheet-FB and Sheet-TikTok tabs never overwrite each other's lists."""
    return (platform or "").strip().lower() or "facebook"


def _read_all(target: str) -> list:
    """Every stored worker across all platforms. [] when no file yet."""
    if not os.path.exists(target):
        return []

    try:
        # utf-8-sig: tolerate a BOM from a hand-edited file.
        with open(target, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        raise WorkerStoreError(f"Không đọc được {target}: {exc}") from exc

    if not isinstance(data, dict):
        raise WorkerStoreError(f"{target} sai định dạng (mong đợi một object JSON).")

    declared = data.get("_schema_version", WORKERS_SCHEMA_VERSION)
    try:
        declared = int(declared)
    except (TypeError, ValueError):
        raise WorkerStoreError(f"{target}: '_schema_version' phải là số nguyên.")
    if declared > WORKERS_SCHEMA_VERSION:
        raise WorkerStoreError(
            f"{target} dùng schema version {declared}, bản build này chỉ hỗ trợ "
            f"tới {WORKERS_SCHEMA_VERSION}. Cập nhật ứng dụng."
        )

    workers = data.get("workers", [])
    if not isinstance(workers, list):
        raise WorkerStoreError(f"{target}: 'workers' phải là một mảng.")

    return [_clean(w) for w in workers if isinstance(w, dict) and w.get("tab")]


def save_workers(workers: list, *, platform: str = "",
                 path: Optional[str] = None,
                 env: Optional[dict] = None) -> str:
    """Atomically persist *workers* for one platform.

    Other platforms' entries in the same file are preserved — the desktop
    app has a Sheet-FB tab and a Sheet-TikTok tab, each owning its own
    list, and saving one must not wipe the other.
    """
    target = path or default_path(env)
    plat = _normalise_platform(platform)

    try:
        others = [w for w in _read_all(target)
                  if _normalise_platform(w.get("platform", "")) != plat]
    except WorkerStoreError:
        # An unreadable existing file must not block saving a good list;
        # it is replaced rather than silently merged with garbage.
        others = []

    incoming = []
    for w in workers:
        cleaned = _clean(w)
        cleaned["platform"] = plat
        incoming.append(cleaned)

    atomic_write_json(target, {
        "_schema_version": WORKERS_SCHEMA_VERSION,
        "workers": others + incoming,
    })
    return target


def load_workers(*, platform: Optional[str] = None,
                 path: Optional[str] = None,
                 env: Optional[dict] = None) -> list:
    """Return stored workers, or [] when nothing is stored.

    `platform=None` returns every platform's workers; passing a platform
    filters to just that one. Raises WorkerStoreError only when the file
    exists but cannot be trusted — a missing file is a normal first-run
    state, not an error.
    """
    all_workers = _read_all(path or default_path(env))
    if platform is None:
        return all_workers
    plat = _normalise_platform(platform)
    return [w for w in all_workers
            if _normalise_platform(w.get("platform", "")) == plat]
