"""
P1 — headless core boundary tests.

Verifies:
  - worker_main.py never imports customtkinter or gui.*
  - worker_main's CLI wiring (config load, default worker, start/stop
    callback plumbing) runs end-to-end in-process without network access
  - WorkerApplication start/stop/status lifecycle is idempotent
  - a crashing runner still releases the ownership lock exactly once
    (crash safety net)
  - the whole-run ownership lock rejects a second runner targeting the same
    account before it can race a real job
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading

import pytest

import worker_main
from core.session_lock import SessionLock
from core.worker_app import WorkerApplication, WorkerOwnershipError


# ─── No-GUI import boundary ───────────────────────────────────────────────────

def test_worker_main_does_not_import_gui_or_customtkinter():
    script = (
        "import sys\n"
        "import worker_main\n"
        "bad = [m for m in sys.modules if m == 'customtkinter' or m.startswith('gui.') or m == 'gui']\n"
        "assert not bad, bad\n"
        "print('OK')\n"
    )
    proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=proj_root, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout


# ─── worker_main CLI wiring, end-to-end, no network ──────────────────────────

def _isolated_worker_store(tmp_path, monkeypatch, workers=None):
    """Point core.worker_store at a temp file so these tests never read or
    write the developer's real data/workers.json. Returns the path."""
    from core.worker_store import save_workers

    store = str(tmp_path / "workers.json")
    monkeypatch.setattr("core.worker_store.default_path", lambda env=None: store)
    if workers:
        save_workers(workers, platform="facebook", path=store)
    return store


def test_worker_main_end_to_end_with_stored_workers(tmp_path, monkeypatch):
    """Worker list now comes from the shared store the desktop app writes.

    Behavior change (PA-5, docs/_luutru/AUDIT_REPORT.md D3): this used to build a
    worker by guessing from the legacy top-level `sheet_tab`/`sheet_id`
    config keys. The audit proved that guess targeted a tab whose columns
    did not match the configured mapping, producing a run that connected
    and then failed mid-flight. Guessing was removed deliberately.
    """
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"sheet_id": "abc123"}), encoding="utf-8")
    _isolated_worker_store(tmp_path, monkeypatch, [
        {"tab": "MyTab", "page": "MyPage", "sheet_id": "abc123"},
    ])

    captured = {}

    class _FakeApp:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def start(self):
            # Simulate a worker that finishes immediately.
            captured["on_all_stopped"]()

        def stop(self):
            captured["stopped_called"] = True

    monkeypatch.setattr(worker_main, "WorkerApplication", _FakeApp)

    rc = worker_main.main(["--config", str(cfg_path)])

    assert rc == 0
    assert [w["tab"] for w in captured["workers"]] == ["MyTab"]
    assert captured["config"]["sheet_id"] == "abc123"


def test_worker_main_reports_ownership_conflict_as_exit_code(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"sheet_id": "S"}), encoding="utf-8")
    _isolated_worker_store(tmp_path, monkeypatch, [{"tab": "T", "sheet_id": "S"}])

    class _FakeApp:
        def __init__(self, **kwargs):
            pass

        def start(self):
            raise WorkerOwnershipError("already owned")

    monkeypatch.setattr(worker_main, "WorkerApplication", _FakeApp)

    rc = worker_main.main(["--config", str(cfg_path)])
    assert rc == 2


# ─── WorkerApplication lifecycle (SheetRunner stubbed — no network) ──────────

class _StubSheetRunner:
    """Drop-in for core.sheet_runner.SheetRunner: honors stop_event, never
    touches Google Sheets / Graph API."""

    def __init__(self, *, stop_event=None, **_kwargs):
        self.stop_event = stop_event or threading.Event()

    def run(self):
        self.stop_event.wait()


class _CrashingSheetRunner(_StubSheetRunner):
    def run(self):
        raise RuntimeError("simulated crash before any job ran")


@pytest.fixture
def _stub_single_runner(monkeypatch):
    monkeypatch.setattr("core.worker_app.SheetRunner", _StubSheetRunner)


@pytest.fixture
def _crashing_single_runner(monkeypatch):
    monkeypatch.setattr("core.worker_app.SheetRunner", _CrashingSheetRunner)


def _unique_target(name: str) -> dict:
    return {"tab": name, "page": "", "sheet_id": "", "account_id": name}


def test_worker_application_start_stop_lifecycle(_stub_single_runner):
    app = WorkerApplication(
        workers=[_unique_target("__test_lifecycle_worker__")],
        config={"anti_spam_session_lock_enabled": False},
    )
    assert not app.is_running

    app.start()
    assert app.is_running

    # start() while running is a no-op, not a second runner.
    app.start()
    assert app.is_running

    app.stop()
    assert app.wait_stopped(timeout=5)
    assert not app.is_running


def test_worker_application_releases_lock_on_crash(_crashing_single_runner):
    target = "__test_crash_release__"
    stopped = threading.Event()
    app = WorkerApplication(
        workers=[_unique_target(target)],
        config={"anti_spam_session_lock_enabled": True},
        on_all_stopped=stopped.set,
    )
    try:
        app.start()
        assert stopped.wait(timeout=5), "crash should still fire on_all_stopped exactly once"
        assert app.wait_stopped(timeout=5)

        # Lock must be released — a second app targeting the same account
        # must be able to start cleanly right after the crash.
        app2 = WorkerApplication(
            workers=[_unique_target(target)],
            config={"anti_spam_session_lock_enabled": True},
        )
        app2.start()  # must not raise WorkerOwnershipError
        app2.wait_stopped(timeout=5)
    finally:
        lock_path = SessionLock(account_id=target, platform="facebook")._path
        try:
            os.remove(lock_path)
        except OSError:
            pass


def test_worker_application_ownership_lock_blocks_second_runner(_stub_single_runner):
    target = "__test_ownership_conflict__"
    lock = SessionLock(account_id=target, platform="facebook")
    try:
        lock.acquire()
        # Simulate "another process" by making is_us False. This also makes
        # our own lock.release() below unable to recognize the file as ours
        # (by design — that's the scenario under test), so cleanup happens
        # via os.remove in the finally block instead.
        _rewrite_owner_as_foreign_pid(lock)

        app = WorkerApplication(
            workers=[_unique_target(target)],
            config={"anti_spam_session_lock_enabled": True},
        )
        with pytest.raises(WorkerOwnershipError):
            app.start()
        assert not app.is_running
    finally:
        lock.release()
        try:
            os.remove(lock._path)
        except OSError:
            pass


def _rewrite_owner_as_foreign_pid(lock: SessionLock) -> None:
    """Rewrite the lock file so it looks owned by a different (live-looking)
    process, without needing to actually spawn one."""
    with open(lock._path, encoding="utf-8") as f:
        data = json.load(f)
    data["pid"] = data["pid"] + 1  # different pid → is_us becomes False
    with open(lock._path, "w", encoding="utf-8") as f:
        json.dump(data, f)
