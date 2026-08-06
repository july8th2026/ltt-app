"""
Session lock (Sprint B2) — prevent concurrent bot instances stealing the
same account.

Problem:
  Two team members running the same bot on the same Facebook account
  simultaneously → FB sees parallel logins from 2 IPs → checkpoint /
  password reset / 2FA prompt. The user account ends up locked for 24-72 h.

Solution:
  File-based advisory lock per (account_id, machine). When a bot acquires
  the lock for an account, others see the lock file and refuse to start
  upload for that account. The lock auto-expires if not renewed within
  REFRESH_MIN minutes, so a crashed bot doesn't permanently block.

Lock file format (JSON):
  {
    "account_id":  "u1234",
    "platform":    "facebook",
    "hostname":    "WORKSTATION-A",
    "pid":         12345,
    "acquired_at": "2026-05-15T10:00:00+00:00",
    "renewed_at":  "2026-05-15T10:14:30+00:00"
  }

Atomic write via os.replace().
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


_RENEW_SEC       = 60                   # renewer thread tick
_LOCK_TTL_S      = 5 * 60               # lock expires after 5 min without renewal


def _default_lock_dir() -> str:
    """Resolve the lock directory through the P2 runtime-path boundary.

    Previously a module-level `os.path.join("data", "session_locks")`,
    which is relative to the *current working directory*. That silently
    put locks somewhere else when a process ran from another directory,
    and ignored LTT_DATA_DIR entirely — so a server configured with an
    external data directory would not see the other process's locks, and
    the desktop/server mutual exclusion would quietly stop working.
    """
    try:
        from platform_core.runtime_paths import resolve_runtime_paths
        return os.path.join(resolve_runtime_paths().data_dir, "session_locks")
    except Exception:
        # Never let path resolution break locking outright.
        return os.path.join("data", "session_locks")


@dataclass
class LockOwner:
    """Identifies who holds a lock — parsed from the lock file."""
    account_id:    str
    platform:      str
    hostname:      str
    pid:           int
    acquired_at:   str
    renewed_at:    str

    @property
    def is_stale(self) -> bool:
        """True if last renewal was > _LOCK_TTL_S ago — owner likely crashed."""
        try:
            last = datetime.fromisoformat(self.renewed_at.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return True
        return (datetime.now(timezone.utc) - last).total_seconds() > _LOCK_TTL_S

    @property
    def is_us(self) -> bool:
        """True if this lock belongs to the current process."""
        return self.hostname == socket.gethostname() and self.pid == os.getpid()


class SessionLockError(RuntimeError):
    """Raised when a lock cannot be acquired (another instance owns it)."""


class SessionLock:
    """Acquire/renew/release a per-account file lock.

    Usage:
        lock = SessionLock(account_id="u1234", platform="facebook")
        with lock:
            do_upload_work()
    """

    def __init__(
        self,
        account_id: str,
        platform:   str = "facebook",
        *,
        lock_dir:   Optional[str] = None,
    ):
        if not account_id:
            raise ValueError("account_id is required")
        self.account_id = account_id
        self.platform   = platform
        # Resolved at construction (not import) so LTT_DATA_DIR set after
        # import — or differing between processes — is still honoured.
        lock_dir        = lock_dir or _default_lock_dir()
        self.lock_dir   = lock_dir
        os.makedirs(lock_dir, exist_ok=True)
        self._path:    str = os.path.join(
            lock_dir, f"{platform}_{_safe_name(account_id)}.lock"
        )
        self._renewer: Optional[threading.Thread] = None
        self._stop:    threading.Event = threading.Event()
        self._held:    bool = False

    # ── Context manager interface ────────────────────────────────────────

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()

    # ── Public API ───────────────────────────────────────────────────────

    def acquire(self) -> None:
        """Acquire the lock. Raises SessionLockError if another live owner
        holds it. Steals the lock if existing owner is stale (TTL expired)."""
        if os.path.exists(self._path):
            owner = self._read_owner()
            if owner is not None and not owner.is_stale and not owner.is_us:
                raise SessionLockError(
                    f"Account '{self.account_id}' đã được khóa bởi "
                    f"{owner.hostname} (pid={owner.pid}) lúc {owner.acquired_at}. "
                    "Đợi process kia release, hoặc xoá lock file bằng tay nếu chắc chắn."
                )
        self._write_owner()
        self._held = True
        self._start_renewer()

    def release(self) -> None:
        """Release the lock. No-op if we don't hold it."""
        self._stop.set()
        if self._renewer:
            self._renewer.join(timeout=2)
        if self._held and os.path.exists(self._path):
            owner = self._read_owner()
            if owner is None or owner.is_us:
                try:
                    os.unlink(self._path)
                except OSError:
                    pass
        self._held = False

    def renew(self) -> None:
        """Update renewed_at — called by the background thread."""
        if not self._held:
            return
        try:
            self._write_owner(acquired_at_override=None)
        except Exception:
            pass

    def current_owner(self) -> Optional[LockOwner]:
        """Read the lock file and return its owner. Returns None when no file."""
        if not os.path.exists(self._path):
            return None
        return self._read_owner()

    # ── Internals ────────────────────────────────────────────────────────

    def _write_owner(self, acquired_at_override: Optional[str] = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        existing = self._read_owner() if os.path.exists(self._path) else None
        acquired_at = (
            acquired_at_override
            or (existing.acquired_at if existing and existing.is_us else now)
        )
        data = {
            "account_id":   self.account_id,
            "platform":     self.platform,
            "hostname":     socket.gethostname(),
            "pid":          os.getpid(),
            "acquired_at":  acquired_at,
            "renewed_at":   now,
        }
        # Atomic via tmp + replace
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self._path)

    def _read_owner(self) -> Optional[LockOwner]:
        try:
            with open(self._path, encoding="utf-8") as f:
                d = json.load(f)
            return LockOwner(
                account_id  = str(d.get("account_id", "")),
                platform    = str(d.get("platform",   "")),
                hostname    = str(d.get("hostname",   "")),
                pid         = int(d.get("pid",        0)),
                acquired_at = str(d.get("acquired_at","")),
                renewed_at  = str(d.get("renewed_at", "")),
            )
        except (OSError, ValueError, KeyError):
            return None

    def _start_renewer(self) -> None:
        if self._renewer and self._renewer.is_alive():
            return
        self._stop.clear()
        self._renewer = threading.Thread(
            target=self._renew_loop, daemon=True, name=f"SessionLockRenewer-{self.account_id}",
        )
        self._renewer.start()

    def _renew_loop(self) -> None:
        while not self._stop.wait(_RENEW_SEC):
            self.renew()


# ─── Helpers ────────────────────────────────────────────────────────────────

def _safe_name(s: str) -> str:
    """Sanitize for use as a file name."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s)
