"""One gate for every test that wants a real PostgreSQL database.

These tests call ``Base.metadata.drop_all()``. That is correct for a scratch
database and catastrophic for any other one, and the only thing standing between
the two is an environment variable — on a machine where the platform's own
PostgreSQL is running, a single typo in ``LTT_TEST_DATABASE_URL`` drops the
tables serving real customers.

So the rule is not "be careful". The rule is that a URL has to **prove** it is
disposable before anything destructive touches it:

* its database name must contain ``test`` — a production database will not be
  named that by accident, and naming one that way is a deliberate act;
* it must not be the URL this deployment actually runs on.

A URL that fails those checks is a **hard failure**, never a skip. Skipping is
how a mistake becomes silence: the suite goes green, and nobody learns that the
guard fired.
"""
from __future__ import annotations

import os

import pytest

ENV = "LTT_TEST_DATABASE_URL"


def _database_name(url: str) -> str:
    """The database part of a SQLAlchemy URL, without parsing credentials out.

    Deliberately string-level: this never needs to see the password, and code
    that does not hold a secret cannot leak one.
    """
    tail = url.rsplit("/", 1)[-1]
    return tail.split("?", 1)[0].strip().lower()


def scratch_url() -> str:
    """The scratch PostgreSQL URL, or "" when the suite should skip.

    Raises when the variable is set to something that is not obviously a
    throwaway — refusing loudly beats running destructively.
    """
    url = (os.environ.get(ENV) or "").strip()
    if not url:
        return ""

    live = (os.environ.get("LTT_DATABASE_URL") or "").strip()
    if live and url == live:
        pytest.fail(
            f"{ENV} is the same database this deployment runs on. These tests "
            f"drop every table; point it at a scratch database.")

    name = _database_name(url)
    if "test" not in name:
        pytest.fail(
            f"{ENV} names database {name!r}, which does not look disposable. "
            f"These tests drop every table, so the name must contain 'test'.")
    return url


def skip_without_postgres():
    """`pytest.mark.skipif` for tests that need a real PostgreSQL.

    The reason string names the variable, because a skipped test whose reason is
    "not configured" teaches nobody how to configure it.
    """
    return pytest.mark.skipif(
        not (os.environ.get(ENV) or "").strip(),
        reason=f"Set {ENV} to a scratch PostgreSQL database (name must "
               f"contain 'test').")
