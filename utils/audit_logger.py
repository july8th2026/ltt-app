"""
Append-only JSONL audit log for TikTok publish events.

Default path : data/audit_log.jsonl  (relative to CWD)
Override via : config["tiktok_audit_log_path"] in global settings

Format  : UTF-8, one JSON object per line.
Safety  : thread-safe (module-level Lock); never raises (exceptions → stderr).

Event types
-----------
tiktok_publish_attempt       — before every upload attempt
tiktok_publish_success       — after successful publish / draft inbox delivery
tiktok_publish_failure       — after any exception that aborts publishing
tiktok_compliance_violation  — when TikTokComplianceError is raised (blocking)
tiktok_token_refreshed       — after a successful access-token refresh
"""
from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

_lock = threading.Lock()

# None = tu dong giai qua LTT_DATA_DIR luc ghi. Dat duong dan cu the de ep buoc.
_DEFAULT_PATH: Optional[str] = None


def default_log_path() -> str:
    """Nơi ghi nhật ký kiểm toán, giải qua ranh giới đường dẫn của P2.

    Công khai (không có gạch dưới) vì `core/time_intel.py` và
    `core/rate_tuner.py` **đọc lại chính file này** để dựng thống kê. Trước đây
    mỗi nơi tự viết `os.path.join("data", "audit_log.jsonl")`, nên chỉ cần một
    chỗ đặt thư mục dữ liệu khác là bên ghi và bên đọc trỏ vào hai file khác
    nhau — thống kê sẽ rỗng mà không có lỗi nào hiện ra.
    """
    if _DEFAULT_PATH:
        return _DEFAULT_PATH
    try:
        from core.runtime_paths import data_path
        return data_path("audit_log.jsonl")
    except Exception:
        return os.path.join("data", "audit_log.jsonl")


def append_event(
    event: str,
    *,
    log_path: str = "",
    open_id: str = "",
    display_name: str = "",
    row_idx: Union[int, str] = "",
    post_type: str = "",
    privacy_level: str = "",
    publish_id: str = "",
    error_code: str = "",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Append one audit event to the JSONL log file.

    All keyword arguments are optional; only pass what's relevant to the event.
    Never raises — exceptions are printed to stderr so publish flow is never blocked.

    Parameters
    ----------
    event         : event type string (e.g. "tiktok_publish_attempt")
    log_path      : override path for the log file (default: data/audit_log.jsonl)
    open_id       : TikTok account open_id
    display_name  : TikTok account display name
    row_idx       : Google Sheet row index (int or empty string)
    post_type     : "tiktok_draft" | "tiktok_direct"
    privacy_level : "SELF_ONLY" | "PUBLIC_TO_EVERYONE" | etc.
    publish_id    : TikTok publish_id returned after successful init
    error_code    : error code string (on failure / compliance violation)
    details       : additional key/value pairs
    """
    record: Dict[str, Any] = {
        "timestamp":     datetime.now(timezone.utc).isoformat(),
        "event":         event,
        "open_id":       open_id,
        "display_name":  display_name,
        "row_idx":       row_idx,
        "post_type":     post_type,
        "privacy_level": privacy_level,
        "publish_id":    publish_id,
        "error_code":    error_code,
        "details":       details or {},
    }
    path = log_path or default_log_path()
    try:
        _write(path, record)
    except Exception as exc:  # pragma: no cover
        print(f"[AuditLogger] Failed to write event '{event}': {exc}", file=sys.stderr)


# F2-02 fix: rotation config — prevents silent disk-fill on long-running deployments
_MAX_LOG_BYTES = 10 * 1024 * 1024   # 10 MB per file
_MAX_BACKUPS   = 5                  # keep audit_log.jsonl.1 .. .5


def _rotate_if_needed(path: str) -> None:
    """Rotate the audit log if it exceeds _MAX_LOG_BYTES.

    Strategy: rename to .1, shift older backups to higher numbers, drop oldest.
    Called inside _lock so no concurrent writer interferes.
    """
    try:
        if not os.path.exists(path):
            return
        if os.path.getsize(path) < _MAX_LOG_BYTES:
            return
        # Shift older backups: .4→.5, .3→.4, …, .1→.2
        for i in range(_MAX_BACKUPS - 1, 0, -1):
            src = f"{path}.{i}"
            dst = f"{path}.{i + 1}"
            if os.path.exists(src):
                try:
                    if os.path.exists(dst):
                        os.remove(dst)
                    os.rename(src, dst)
                except OSError:
                    pass
        # Rename current to .1
        try:
            if os.path.exists(f"{path}.1"):
                os.remove(f"{path}.1")
            os.rename(path, f"{path}.1")
        except OSError:
            pass
    except Exception:
        # Rotation is best-effort; do not crash the write
        pass


def _write(path: str, record: dict) -> None:
    """Thread-safe append of one JSON line to *path*.

    F2-02 fix: rotates the file when it exceeds 10MB to prevent unbounded growth.
    """
    with _lock:
        # Ensure parent directory exists (handles both absolute and relative paths)
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        # Check + rotate before appending
        _rotate_if_needed(path)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
