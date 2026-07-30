"""
Shared pytest fixtures.

Anti-spam dedup uses a SQLite singleton at data/content_history.db. Without
isolation, test #1 records a hash → test #2 sees it as a "duplicate" → skips
the upload path → assertions on the upload pipeline fail.

This conftest:
  • points the singleton at a per-session temp DB
  • clears that DB before every test function so cross-test state can't leak

Tests that explicitly exercise dedup (test_21_antispam_phase1) construct
their own ContentHistoryStore with their own tempfile, so they are unaffected.
"""
from __future__ import annotations

import os
import tempfile

import pytest


@pytest.fixture(scope="session", autouse=True)
def _isolate_content_history_db():
    """Repoint the module-level singleton at a temp file for the whole test run."""
    import core.content_history as ch
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    ch._default_store = None  # force re-creation under new path
    original_default = ch._DEFAULT_DB_PATH
    ch._DEFAULT_DB_PATH = tmp.name
    yield
    # Cleanup at end of session
    ch._DEFAULT_DB_PATH = original_default
    try:
        os.unlink(tmp.name)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def _clear_content_history_each_test():
    """Wipe rows between tests so a successful publish in test A doesn't
    flag test B's upload as a duplicate."""
    yield
    try:
        import core.content_history as ch
        store = ch._default_store
        if store is None:
            return
        with store._connect() as conn:
            conn.execute("DELETE FROM content_history")
            conn.commit()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _reset_circuit_breaker():
    """Reset the shared CircuitBreaker between tests so a 'tripped' state in
    test A doesn't bleed into test B's first allow() check."""
    yield
    try:
        import core.circuit_breaker as cb
        if cb._default is not None:
            cb._default.reset()
    except Exception:
        pass
