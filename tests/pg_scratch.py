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

    # Chỉ kiểm TÊN, không so với `LTT_DATABASE_URL`. Phép so đó từng có ở đây và
    # nó bắn nhầm đúng vào tình huống rào sinh ra để bảo vệ: một test đa tiến
    # trình trỏ `LTT_DATABASE_URL` về chính CSDL vứt đi, rồi tiến trình con
    # (Windows dùng `spawn`) nạp lại module test — rào thấy hai giá trị bằng
    # nhau, kết luận "đây là production", và giết mọi worker **trước khi in ra
    # được gì**. Cả bộ test vẫn xanh, vì không có gì chạy thì cũng không có gì
    # xảy ra hai lần.
    #
    # Phép kiểm tên đủ mạnh mà không có mặt trái đó: CSDL production của nền
    # tảng không tình cờ mang chữ `test`, và đặt tên như vậy là một hành động
    # cố ý.
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
