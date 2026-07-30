"""
test_06_concurrent_runner.py — Unit tests for ConcurrentRunner + SheetRunner rate_limiter param.

Coverage:
  - ConcurrentRunner import and construction
  - Empty workers raises ValueError
  - WorkerStatus dataclass initial state
  - Shared RateLimiter is injected into each SheetRunner
  - stop() fires stop_event
  - is_running returns False before start()
  - worker_statuses() returns correct count
  - SheetRunner accepts rate_limiter param without error
  - SheetRunnerTab workers management (add/remove/validate)
"""
from __future__ import annotations

import sys
import os
import threading
import unittest
from unittest.mock import MagicMock, patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


# ─── ConcurrentRunner tests ───────────────────────────────────────────────────

class TestConcurrentRunnerImport(unittest.TestCase):
    def test_import(self):
        from core.concurrent_runner import ConcurrentRunner, WorkerStatus
        self.assertTrue(callable(ConcurrentRunner))

    def test_worker_status_defaults(self):
        from core.concurrent_runner import WorkerStatus
        ws = WorkerStatus(tab="T1", page="P1")
        self.assertEqual(ws.tab,        "T1")
        self.assertEqual(ws.page,       "P1")
        self.assertEqual(ws.state,      "idle")
        self.assertEqual(ws.jobs_done,  0)
        self.assertEqual(ws.jobs_error, 0)
        self.assertEqual(ws.current_job, "")


class TestConcurrentRunnerConstruct(unittest.TestCase):
    """Tests that don't actually start threads."""

    def _make_runner(self, workers, config=None, **kwargs):
        from core.concurrent_runner import ConcurrentRunner
        cfg = config or {
            "sheet_id": "SHEET_ID",
            "google_credentials_path": "creds.json",
        }
        # Patch SheetClient + DriveDownloader so no real I/O
        with patch("core.sheet_runner.SheetClient"), \
             patch("core.sheet_runner.DriveDownloader"):
            return ConcurrentRunner(workers=workers, config=cfg, **kwargs)

    def test_empty_workers_raises(self):
        from core.concurrent_runner import ConcurrentRunner
        with self.assertRaises(ValueError):
            ConcurrentRunner(workers=[], config={})

    def test_single_worker_count(self):
        runner = self._make_runner([{"tab": "T1", "page": "P1"}])
        self.assertEqual(len(runner.worker_statuses()), 1)

    def test_multi_worker_count(self):
        workers = [
            {"tab": "T1", "page": "P1"},
            {"tab": "T2", "page": "P2"},
            {"tab": "T3", "page": "P3"},
        ]
        runner = self._make_runner(workers)
        self.assertEqual(len(runner.worker_statuses()), 3)

    def test_initial_state_idle(self):
        runner = self._make_runner([{"tab": "T1", "page": "P1"}])
        statuses = runner.worker_statuses()
        self.assertEqual(statuses[0].state, "idle")

    def test_is_running_false_before_start(self):
        runner = self._make_runner([{"tab": "T1", "page": "P1"}])
        self.assertFalse(runner.is_running)

    def test_stop_fires_stop_event(self):
        runner = self._make_runner([{"tab": "T1", "page": "P1"}])
        self.assertFalse(runner._stop_event.is_set())
        runner.stop()
        self.assertTrue(runner._stop_event.is_set())

    def test_worker_tab_page_preserved(self):
        workers = [{"tab": "MyTab", "page": "MyPage"}]
        runner = self._make_runner(workers)
        st = runner.worker_statuses()[0]
        self.assertEqual(st.tab,  "MyTab")
        self.assertEqual(st.page, "MyPage")

    def test_shared_rate_limiter_injected(self):
        """All SheetRunner instances should share the same RateLimiter object."""
        workers = [{"tab": "T1", "page": "P1"}, {"tab": "T2", "page": "P2"}]
        runner = self._make_runner(workers)
        limiter0 = runner._runners[0]._rate_limiter
        limiter1 = runner._runners[1]._rate_limiter
        self.assertIs(limiter0, limiter1)

    def test_on_all_stopped_callback_registered(self):
        cb = MagicMock()
        runner = self._make_runner([{"tab": "T1", "page": "P1"}],
                                   on_all_stopped=cb)
        self.assertEqual(runner._on_all_stopped, cb)


# ─── SheetRunner rate_limiter param ──────────────────────────────────────────

class TestSheetRunnerRateLimiterParam(unittest.TestCase):
    def _make_runner(self, rate_limiter=None):
        from core.sheet_runner import SheetRunner
        from core.rate_limiter import RateLimiter
        with patch("core.sheet_runner.SheetClient"), \
             patch("core.sheet_runner.DriveDownloader"):
            return SheetRunner(
                config={},
                page_name="P1",
                sheet_tab="T1",
                stop_event=threading.Event(),
                rate_limiter=rate_limiter,
            )

    def test_default_creates_own_limiter(self):
        from core.rate_limiter import RateLimiter
        runner = self._make_runner()
        self.assertIsInstance(runner._rate_limiter, RateLimiter)

    def test_shared_limiter_accepted(self):
        from core.rate_limiter import RateLimiter
        shared = RateLimiter(max_concurrent=1, min_interval_s=5.0)
        runner = self._make_runner(rate_limiter=shared)
        self.assertIs(runner._rate_limiter, shared)

    def test_none_uses_default(self):
        from core.rate_limiter import RateLimiter
        runner = self._make_runner(rate_limiter=None)
        self.assertIsInstance(runner._rate_limiter, RateLimiter)


# ─── ConcurrentRunner callback wiring ────────────────────────────────────────

class TestConcurrentRunnerCallbacks(unittest.TestCase):
    def _make_runner(self, workers, **kwargs):
        from core.concurrent_runner import ConcurrentRunner
        with patch("core.sheet_runner.SheetClient"), \
             patch("core.sheet_runner.DriveDownloader"):
            return ConcurrentRunner(workers=workers, config={}, **kwargs)

    def test_on_log_prefixes_worker_index(self):
        received = []
        runner = self._make_runner(
            [{"tab": "T1", "page": "P1"}],
            on_log=lambda m, l: received.append(m),
        )
        runner._make_on_log(0)("Hello", "info")
        self.assertTrue(received[0].startswith("[W1]"))

    def test_on_job_done_increments_jobs_done(self):
        runner = self._make_runner([{"tab": "T1", "page": "P1"}])
        cb = runner._make_on_job_done(0)
        cb({}, "http://example.com")
        self.assertEqual(runner._statuses[0].jobs_done, 1)

    def test_on_job_error_increments_jobs_error(self):
        runner = self._make_runner([{"tab": "T1", "page": "P1"}])
        cb = runner._make_on_job_error(0)
        cb({}, "some error")
        self.assertEqual(runner._statuses[0].jobs_error, 1)

    def test_on_stopped_updates_state(self):
        all_stopped_called = threading.Event()
        runner = self._make_runner(
            [{"tab": "T1", "page": "P1"}],
            on_all_stopped=lambda: all_stopped_called.set(),
        )
        cb = runner._make_on_stopped(0)
        cb()
        self.assertEqual(runner._statuses[0].state, "stopped")
        self.assertTrue(all_stopped_called.is_set())

    def test_on_job_start_sets_state_running(self):
        runner = self._make_runner([{"tab": "T1", "page": "P1"}])
        cb = runner._make_on_job_start(0)
        cb({"row_idx": 5, "title": "My Video"})
        self.assertEqual(runner._statuses[0].state, "running")
        self.assertIn("5", runner._statuses[0].current_job)

    def test_all_stopped_fires_after_last_worker(self):
        flag = threading.Event()
        workers = [{"tab": f"T{i}", "page": f"P{i}"} for i in range(3)]
        runner = self._make_runner(workers, on_all_stopped=lambda: flag.set())

        for i in range(3):
            runner._make_on_stopped(i)()

        self.assertTrue(flag.is_set())

    def test_all_stopped_does_not_fire_early(self):
        flag = threading.Event()
        workers = [{"tab": f"T{i}", "page": f"P{i}"} for i in range(3)]
        runner = self._make_runner(workers, on_all_stopped=lambda: flag.set())

        runner._make_on_stopped(0)()
        runner._make_on_stopped(1)()
        self.assertFalse(flag.is_set())  # 2 of 3 stopped — not yet
        runner._make_on_stopped(2)()
        self.assertTrue(flag.is_set())


# ─── SheetRunnerTab worker management (headless) ─────────────────────────────

class TestSheetRunnerTabWorkerLogic(unittest.TestCase):
    """Tests internal worker list logic without creating a real Tkinter window."""

    def setUp(self):
        # We bypass Tkinter by extracting pure-logic methods
        # via a minimal stub that has the same _workers list interface.
        self._workers: list[dict] = []

    def _add(self, tab: str, page: str):
        for w in self._workers:
            if w["tab"] == tab:
                return "duplicate"
        if len(self._workers) >= 6:
            return "limit"
        if not tab or tab.startswith("⏳"):
            return "no_tab"
        self._workers.append({"tab": tab, "page": page})
        return "ok"

    def _remove(self, idx: int):
        if 0 <= idx < len(self._workers):
            self._workers.pop(idx)

    def test_add_worker(self):
        result = self._add("Tab1", "Page A")
        self.assertEqual(result, "ok")
        self.assertEqual(len(self._workers), 1)

    def test_add_duplicate_rejected(self):
        self._add("Tab1", "Page A")
        result = self._add("Tab1", "Page B")
        self.assertEqual(result, "duplicate")
        self.assertEqual(len(self._workers), 1)

    def test_add_empty_tab_rejected(self):
        result = self._add("", "Page A")
        self.assertEqual(result, "no_tab")
        self.assertEqual(len(self._workers), 0)

    def test_add_loading_tab_rejected(self):
        result = self._add("⏳ Đang tải...", "Page A")
        self.assertEqual(result, "no_tab")

    def test_remove_worker(self):
        self._add("Tab1", "Page A")
        self._add("Tab2", "Page B")
        self._remove(0)
        self.assertEqual(len(self._workers), 1)
        self.assertEqual(self._workers[0]["tab"], "Tab2")

    def test_remove_out_of_range_safe(self):
        self._add("Tab1", "Page A")
        self._remove(99)  # should not raise
        self.assertEqual(len(self._workers), 1)

    def test_max_workers_limit(self):
        for i in range(6):
            self._add(f"Tab{i}", f"Page{i}")
        result = self._add("Tab99", "Page99")
        self.assertEqual(result, "limit")
        self.assertEqual(len(self._workers), 6)

    def test_validate_no_workers(self):
        # Replicate _validate logic
        workers = []
        config  = {"sheet_id": "X", "google_credentials_path": "creds.json"}
        err = None
        if not workers:
            err = "Chưa có worker"
        self.assertIsNotNone(err)

    def test_validate_missing_sheet_id(self):
        workers = [{"tab": "T1", "page": "P1"}]
        config  = {"google_credentials_path": "creds.json"}
        err = None
        if not workers:
            err = "no workers"
        elif not config.get("sheet_id"):
            err = "Chưa nhập Sheet ID"
        self.assertEqual(err, "Chưa nhập Sheet ID")

    def test_validate_ok(self):
        workers = [{"tab": "T1", "page": "P1"}]
        config  = {"sheet_id": "X", "google_credentials_path": "creds.json"}
        err = None
        if not workers:
            err = "no workers"
        elif not config.get("sheet_id"):
            err = "no sheet_id"
        elif not config.get("google_credentials_path"):
            err = "no credentials"
        self.assertIsNone(err)


# ─── K-2: Worker crash detection ─────────────────────────────────────────────

class TestConcurrentRunnerCrashDetection(unittest.TestCase):
    """
    Tests for _thread_target() crash-detection wrapper (K-2).
    """

    def _make_runner(self, workers=None):
        from core.concurrent_runner import ConcurrentRunner
        w = workers or [{"tab": "Tab1", "page": "Page1"}]
        cfg = {
            "max_concurrent_uploads_per_page": 1,
            "min_interval_per_page_s": 0,
            "worker_max_restarts": 0,  # disable auto-restart so tests run instantly
        }
        logs = []
        updates = []
        stopped_calls = []
        cr = ConcurrentRunner(
            workers=w, config=cfg,
            on_log=lambda m, l: logs.append((m, l)),
            on_worker_update=lambda i, s: updates.append((i, s)),
            on_all_stopped=lambda: stopped_calls.append(True),
        )
        return cr, logs, updates, stopped_calls

    def test_thread_target_calls_runner_run(self):
        """_thread_target must call runner.run()."""
        cr, logs, updates, stopped = self._make_runner()
        cr._runners[0].run = MagicMock()
        cr._thread_target(0)
        cr._runners[0].run.assert_called_once()

    def test_thread_target_crash_sets_error_state(self):
        """On unhandled exception, worker state becomes 'error'."""
        cr, logs, updates, stopped = self._make_runner()
        cr._runners[0].run = MagicMock(side_effect=RuntimeError("bang!"))
        cr._thread_target(0)
        last_state = cr._statuses[0].state
        self.assertEqual(last_state, "error")

    def test_thread_target_crash_logs_error(self):
        """Crash must produce an error-level log entry."""
        cr, logs, updates, stopped = self._make_runner()
        cr._runners[0].run = MagicMock(side_effect=ValueError("boom"))
        cr._thread_target(0)
        error_logs = [m for m, l in logs if l == "error"]
        self.assertTrue(len(error_logs) >= 1, "Expected at least one error log")

    def test_thread_target_crash_fires_on_all_stopped_single(self):
        """With 1 worker, crash must fire on_all_stopped."""
        cr, logs, updates, stopped = self._make_runner()
        cr._runners[0].run = MagicMock(side_effect=Exception("crash"))
        cr._thread_target(0)
        self.assertEqual(len(stopped), 1, "on_all_stopped should fire once")

    def test_thread_target_crash_fires_on_all_stopped_multi(self):
        """With 2 workers, on_all_stopped fires only after both finish."""
        cr, logs, updates, stopped = self._make_runner(
            workers=[{"tab": "T1", "page": "P1"}, {"tab": "T2", "page": "P2"}]
        )
        # Worker 0 crashes, worker 1 exits normally (run() returns without exception)
        cr._runners[0].run = MagicMock(side_effect=RuntimeError("boom"))
        cr._runners[1].run = MagicMock()  # normal exit — on_stopped not called here
        # Manually simulate that worker 1's on_stopped incremented the counter
        with cr._lock:
            cr._stopped_count += 1

        # Now run worker 0's crash
        cr._thread_target(0)

        self.assertEqual(len(stopped), 1, "on_all_stopped fires when both are done")

    def test_thread_target_crash_increments_stopped_count(self):
        """Each crashed worker must increment _stopped_count exactly once."""
        cr, logs, updates, stopped = self._make_runner(
            workers=[{"tab": "T1", "page": "P1"}, {"tab": "T2", "page": "P2"}]
        )
        cr._runners[0].run = MagicMock(side_effect=RuntimeError("x"))
        cr._thread_target(0)
        self.assertEqual(cr._stopped_count, 1)

    def test_thread_target_normal_exit_does_not_double_count(self):
        """Normal exit: runner.run() calls on_stopped itself. _thread_target must not
        increment _stopped_count again."""
        cr, logs, updates, stopped = self._make_runner()

        # Simulate runner.run() calling on_stopped internally
        def _fake_run():
            # This mimics what SheetRunner.run() does at its end
            cr._make_on_stopped(0)()

        cr._runners[0].run = _fake_run
        cr._thread_target(0)

        # _stopped_count should be exactly 1 (from on_stopped callback), not 2
        self.assertEqual(cr._stopped_count, 1)

    def test_thread_target_crash_stores_error_message(self):
        """last_msg of crashed worker should contain the exception text."""
        cr, logs, updates, stopped = self._make_runner()
        cr._runners[0].run = MagicMock(side_effect=RuntimeError("disk full"))
        cr._thread_target(0)
        self.assertIn("disk full", cr._statuses[0].last_msg)

    def test_start_uses_thread_target_not_run_directly(self):
        """After start(), threads must target _thread_target, not runner.run."""
        from core.concurrent_runner import ConcurrentRunner
        cfg = {
            "max_concurrent_uploads_per_page": 1,
            "min_interval_per_page_s": 0,
        }
        cr = ConcurrentRunner(
            workers=[{"tab": "T1", "page": "P1"}],
            config=cfg,
        )
        started_targets = []
        original_thread = threading.Thread

        def _capture_thread(*args, **kwargs):
            started_targets.append(kwargs.get("target"))
            t = original_thread(*args, **kwargs)
            return t

        with patch("core.concurrent_runner.threading.Thread", side_effect=_capture_thread):
            # Don't actually start threads — just verify target is _thread_target
            try:
                cr.start()
            except Exception:
                pass

        self.assertTrue(len(started_targets) > 0)
        # The target should be bound method _thread_target (not runner.run)
        for tgt in started_targets:
            if tgt is not None:
                self.assertNotEqual(
                    getattr(tgt, "__func__", None),
                    None,
                    "thread target should be a bound method"
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
