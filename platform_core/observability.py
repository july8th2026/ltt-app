"""Structured process logging for the LTT platform.

Job history is the durable source of truth for a customer's job.  This module
owns the second layer: short-lived process logs for diagnosing worker/server
failures.  Records are JSONL, redacted at the boundary and rotated by size;
old files created by this module are pruned by age.  It deliberately does not
log request bodies, prompts, provider payloads or credentials.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Iterator


_context: ContextVar[dict[str, str]] = ContextVar("ltt_log_context", default={})
_configured: set[tuple[str, str]] = set()
_lock = threading.Lock()


def _int_env(env: dict, name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(str(env.get(name, default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def _redact(value: object) -> str:
    """Use the JobEvent boundary for the same secret/PII policy."""
    from platform_core.job_events import sanitize_text
    return sanitize_text(value, limit=8000)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        try:
            message = record.getMessage()
        except Exception as exc:  # pragma: no cover - defensive logging path
            # Do not lose the record if a third-party logger passes a broken
            # ``msg`` object; include only its type, never its raw value.
            message = f"<unformattable log message: {type(exc).__name__}>"
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": _redact(message),
            "pid": os.getpid(),
            "thread": record.threadName,
        }
        # ⭐ `run_id` (25/09): khoa tuong quan xuyen HANG NGHIN job `advance` cua
        #    mot lan chay ASV. Rong voi moi app khac — `if value:` ben duoi bo
        #    qua no y het cac khoa con lai, nen them khoa nay vo hai voi phan
        #    con lai cua nen tang.
        for key in ("job_id", "app_slug", "job_type", "worker_id",
                    "correlation_id", "run_id"):
            value = getattr(record, key, "") or _context.get({}).get(key, "")
            if value:
                payload[key] = _redact(value)[:128]
        if record.exc_info:
            payload["exception"] = _redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in _context.get({}).items():
            if not hasattr(record, key):
                setattr(record, key, value)
        return True


def cleanup_rotated_logs(*, logs_dir: str, retention_days: int = 30,
                         prefix: str = "ltt-") -> int:
    """Remove only this module's rotated files older than ``retention_days``."""
    cutoff = datetime.now(timezone.utc).timestamp() - max(1, int(retention_days)) * 86400
    removed = 0
    root = Path(logs_dir)
    if not root.exists():
        return 0
    for path in root.glob(f"{prefix}*.jsonl*"):
        if not path.is_file() or path.stat().st_mtime >= cutoff:
            continue
        try:
            path.unlink()
            removed += 1
        except OSError:
            logging.getLogger(__name__).warning("cannot prune log file %s", path.name)
    return removed


def configure_logging(*, component: str, env: dict | None = None) -> str | None:
    """Install one redacted rotating JSONL handler and return its path.

    ``LTT_FILE_LOGGING=0`` disables file output (stdout remains available).
    The handler is idempotent per process/component and never logs secrets.
    """
    values = os.environ if env is None else env
    if str(values.get("LTT_FILE_LOGGING", "1")).strip().lower() in {"0", "false", "off", "no"}:
        return None
    from platform_core.runtime_paths import resolve_runtime_paths
    paths = resolve_runtime_paths(values)
    logs_dir = Path(paths.logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)
    name = str(component or "process").replace("/", "_").replace("\\", "_")[:40]
    key = (str(logs_dir), name)
    path = logs_dir / f"ltt-{name}.jsonl"
    with _lock:
        if key not in _configured:
            handler = RotatingFileHandler(
                path, maxBytes=_int_env(values, "LTT_LOG_MAX_BYTES", 10 * 1024 * 1024,
                                        64 * 1024, 1024 * 1024 * 1024),
                backupCount=_int_env(values, "LTT_LOG_BACKUP_COUNT", 5, 1, 100),
                encoding="utf-8",
            )
            handler.setFormatter(_JsonFormatter())
            handler.addFilter(_ContextFilter())
            logging.getLogger().addHandler(handler)
            _configured.add(key)
        cleanup_rotated_logs(
            logs_dir=str(logs_dir),
            retention_days=_int_env(values, "LTT_LOG_RETENTION_DAYS", 30, 1, 3650),
        )
    return str(path)


@contextmanager
def job_logging_context(**values: str) -> Iterator[None]:
    """Bind safe correlation fields to process log records for one job."""
    clean = {key: str(value)[:128] for key, value in values.items() if value}
    token = _context.set({**_context.get({}), **clean})
    try:
        yield
    finally:
        _context.reset(token)


def push_logging_context(**values: str) -> object:
    """Bien ban thu cong cua `job_logging_context` cho noi KHONG dung duoc
    `with` (mot khoi `try`/`finally` da qua lon de long them mot cap thut —
    xem `apps/auto_scan_video/thi_hanh.py:chay_giai_doan`, noi mot loi goi
    TRUC TIEP ngoai hang doi, vd script/test, khong co `ctx` van can `run_id`
    di vao process log).

    ⚠️ Nguoi goi PHAI goi `pop_logging_context(token)` trong `finally` cua
       chinh minh — ham nay khong tu don, khac `job_logging_context`.
    """
    clean = {key: str(value)[:128] for key, value in values.items() if value}
    return _context.set({**_context.get({}), **clean})


def pop_logging_context(token: object) -> None:
    _context.reset(token)
