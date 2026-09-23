"""Migration bước 2 §17.5 — drop `agent_runs`, và `downgrade` phải dựng lại.

## Vì sao `downgrade` được canh chặt hơn `upgrade`

`upgrade` sai thì gate đỏ ngay. `downgrade` sai chỉ lộ vào **đúng lúc đang có
sự cố** — lúc người trực cần lùi bản. Một `downgrade` chỉ có `pass` trông vô
hại trong diff và biến đường lui thành một câu nói suông.

## Vì sao đọc NGUỒN chứ không chạy migration ở ba bài đầu

Ba bài dưới đọc văn bản revision: chúng trả lời *"người viết đã viết gì"*. Bài
cuối **chạy thật** lên/xuống/lên trên một CSDL SQLite tạm: nó trả lời *"thứ đã
viết có chạy được không"*. Hai câu hỏi khác nhau, và bài đọc-văn-bản một mình
sẽ xanh cho một `downgrade` gọi `create_table` với một cột sai kiểu.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

GOC = pathlib.Path(__file__).resolve().parent.parent


def _scripts() -> ScriptDirectory:
    cfg = Config(str(GOC / "alembic.ini"))
    cfg.set_main_option("script_location", str(GOC / "alembic"))
    return ScriptDirectory.from_config(cfg)


@pytest.fixture(scope="module")
def rev():
    ds = [s for s in _scripts().walk_revisions()
          if "go_agent_runs" in (s.path or "")]
    assert ds, "chua co migration go_agent_runs"
    return ds[0]


@pytest.fixture(scope="module")
def nguon(rev) -> str:
    return pathlib.Path(rev.path).read_text(encoding="utf-8")


def test_la_mot_head_duy_nhat(rev):
    # `get_heads()` tra ve `list`, khong phai `tuple` — so bang `list(...)`
    # chu khong so thang voi mot tuple (bay cua ban nhap trong plan).
    heads = list(_scripts().get_heads())
    assert heads == [rev.revision], f"phai la head duy nhat, dang co {heads}"


def test_upgrade_drop_bang(nguon):
    than = nguon.split("def upgrade()")[1].split("def downgrade()")[0]
    assert re.search(r'drop_table\(\s*"agent_runs"', than)


def test_downgrade_dung_lai_bang_chu_khong_pass(nguon):
    than = nguon.split("def downgrade()")[1]
    assert re.search(r'create_table\(\s*"agent_runs"', than)
    for cot in ("id", "user_id", "app_slug", "goal", "plan", "checkpoint",
                "status", "budget_max", "estimated", "actual", "approved_at",
                "approved_by", "decision_log", "version", "created_at",
                "finished_at"):
        assert f'"{cot}"' in than, f"downgrade thieu cot {cot}"
    for chi_muc in ("ix_agent_runs_user_id", "ix_agent_runs_status",
                    "ix_agent_runs_created_at", "ix_agent_runs_user_created"):
        assert chi_muc in than, f"downgrade thieu chi muc {chi_muc}"


def test_LEN_XUONG_LEN_chay_that_tren_sqlite(tmp_path):
    """🔑 Vế đối chứng của ba bài đọc-văn-bản ở trên.

    Xoá một BẢNG là thao tác không đảo được. Đường lui chỉ tồn tại nếu nó
    **chạy**, nên bài này chạy nó — trên một tệp SQLite dùng một lần, không
    phải trên CSDL nào đang sống.

    Sau `downgrade`, bảng phải **có mặt trở lại** và chèn được một hàng đủ cột:
    đó là điều bản cũ cần để khởi động. Đọc `sqlite_master` một mình sẽ xanh
    cả cho một bảng dựng thiếu ràng buộc.
    """
    import os

    db = tmp_path / "go_agent_runs.db"
    env = dict(os.environ)
    env["LTT_DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
    env["PYTHONPATH"] = str(GOC)

    def alembic(*args: str) -> None:
        ra = subprocess.run([sys.executable, "-m", "alembic", *args],
                            cwd=str(GOC), env=env, capture_output=True, text=True)
        assert ra.returncode == 0, f"alembic {' '.join(args)} -> {ra.returncode}\n{ra.stderr[-2000:]}"

    def co_bang() -> bool:
        import sqlalchemy as sa
        e = sa.create_engine(f"sqlite:///{db.as_posix()}")
        try:
            with e.connect() as c:
                return bool(c.execute(sa.text(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='agent_runs'")).first())
        finally:
            e.dispose()

    alembic("upgrade", "head")
    assert not co_bang(), "sau upgrade bang agent_runs phai BIEN MAT"

    alembic("downgrade", "-1")
    assert co_bang(), "downgrade phai DUNG LAI bang agent_runs"

    import sqlalchemy as sa
    e = sa.create_engine(f"sqlite:///{db.as_posix()}")
    try:
        with e.begin() as c:
            c.execute(sa.text(
                "INSERT INTO agent_runs (id, user_id, created_at) "
                "VALUES ('r1', 'u1', '2026-09-24 10:00:00')"))
            assert c.execute(sa.text(
                "SELECT status, budget_max, version FROM agent_runs")).first() == (
                "planning", 0, 1), "downgrade mat server_default cua bang cu"
    finally:
        e.dispose()

    alembic("upgrade", "head")
    assert not co_bang(), "len lai lan hai phai drop lai bang"
