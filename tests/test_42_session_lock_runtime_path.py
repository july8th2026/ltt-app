"""
SessionLock must resolve its directory through the P2 runtime-path
boundary, not a CWD-relative constant.

Found during the P6 real-server smoke test: the lock directory was a
module-level `os.path.join("data", "session_locks")`. A server started
with LTT_DATA_DIR pointing at an external data directory therefore wrote
locks somewhere different from the desktop app, which would silently
break the desktop/server mutual exclusion that AGENTS.md requires —
exactly the failure that lets two runners publish the same job twice.
"""
from __future__ import annotations

import os

from core.session_lock import SessionLock


def test_lock_dir_follows_ltt_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "custom_data"))
    lock = SessionLock(account_id="acct1", platform="facebook")
    assert str(tmp_path / "custom_data") in lock.lock_dir
    assert lock.lock_dir.endswith("session_locks")


def test_lock_dir_is_independent_of_cwd(tmp_path, monkeypatch):
    """The original bug: a CWD-relative default silently moved the lock
    directory when a process ran from elsewhere."""
    monkeypatch.delenv("LTT_DATA_DIR", raising=False)
    monkeypatch.chdir(tmp_path)

    lock = SessionLock(account_id="acct2", platform="facebook")

    assert os.path.isabs(lock.lock_dir)
    assert str(tmp_path) not in lock.lock_dir


def test_explicit_lock_dir_still_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "ignored"))
    explicit = str(tmp_path / "explicit")
    lock = SessionLock(account_id="acct3", lock_dir=explicit)
    assert lock.lock_dir == explicit


def test_two_locks_in_same_data_dir_see_each_other(tmp_path, monkeypatch):
    """Mutual exclusion only works if both processes agree on the path."""
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "shared"))

    first = SessionLock(account_id="shared_acct", platform="facebook")
    first.acquire()
    try:
        second = SessionLock(account_id="shared_acct", platform="facebook")
        owner = second.current_owner()
        assert owner is not None
        assert owner.account_id == "shared_acct"
    finally:
        first.release()


def test_runtime_paths_are_gitignored():
    """Locks and the worker list are machine-specific runtime state."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, ".gitignore"), encoding="utf-8") as f:
        ignored = f.read()
    assert "data/session_locks/" in ignored
    assert "data/workers.json" in ignored
