"""multijob Task 3 — sổ ngân sách KV trên `ExecutionLease` + bảng `llm_waiters`.

Ba nghĩa vụ của một bảng mới ở nền tảng (memory "bảng mới có ba nghĩa vụ"), cả ba
chỉ lộ ở gate đầy đủ nếu quên: xếp loại lưu trữ (governance) · hàm dọn THẬT ·
ràng buộc UNIQUE vào drill khôi phục. Tệp này chốt cả ba ngay tại chỗ, cộng
migration lên/xuống sạch trên SQLite.
"""
from __future__ import annotations

import pathlib

import pytest

REV = "7c1e4b9a2d58"
GOC = pathlib.Path(__file__).resolve().parents[1]
COT_LEASE_MOI = {"lop", "token_dat_truoc", "token_prefill_moi", "la_whale"}


def test_migration_noi_dung_chuoi_va_mot_head():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    scripts = ScriptDirectory.from_config(Config(str(GOC / "alembic.ini")))
    assert len(scripts.get_heads()) == 1, scripts.get_heads()
    rev = scripts.get_revision(REV)
    assert rev.down_revision == "e26c9a41d8b5"
    assert "llm_waiters" in (rev.doc or "") or "ngân sách" in (rev.doc or "")


@pytest.mark.timeout(240)
def test_len_roi_xuong_mot_buoc_sach_va_khop_mo_hinh(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect

    from platform_core.models import ExecutionLease, LlmWaiter

    url = "sqlite:///" + (tmp_path / "mig.db").as_posix()
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.chdir(GOC)
    cfg = Config("alembic.ini")
    command.upgrade(cfg, REV)
    insp = inspect(create_engine(url))

    cot_lease = {c["name"] for c in insp.get_columns("execution_leases")}
    assert COT_LEASE_MOI <= cot_lease
    # Mô hình và migration phải nói CÙNG một tập cột — lệch là `create_all` (test)
    # và `alembic upgrade` (production) dựng hai lược đồ khác nhau.
    assert {c.name for c in LlmWaiter.__table__.columns} == {
        c["name"] for c in insp.get_columns("llm_waiters")}
    assert {c.name for c in ExecutionLease.__table__.columns} == cot_lease
    uq = {u["name"] for u in insp.get_unique_constraints("llm_waiters")}
    assert "uq_llm_waiters_request" in uq

    command.downgrade(cfg, "-1")
    insp = inspect(create_engine(url))
    assert "llm_waiters" not in insp.get_table_names()
    assert not (COT_LEASE_MOI & {c["name"] for c in insp.get_columns("execution_leases")})


def test_governance_xep_loai_llm_waiters():
    from platform_core.public_api import governance

    s = governance.store_for("llm_waiters")
    assert s is not None, "llm_waiters chua duoc xep loai luu tru"
    assert s.klass == governance.OPERATIONAL
    assert s.retention_days == 30
    assert "phong_cho.don_het_han" in s.purged_by


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'pc.db').as_posix()}")
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    session = next(gen)
    try:
        yield session
    finally:
        session.close()
        dbmod.reset_engine()


def test_ham_don_that_su_don(db):
    """Nghĩa vụ 'hàm dọn THẬT': không chỉ tồn tại mà phải đổi được dữ liệu."""
    from datetime import datetime, timedelta, timezone

    from platform_core.llm import phong_cho
    from platform_core.models import LlmWaiter

    now = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)
    db.add_all([
        LlmWaiter(resource="r", user_id="u", request_id="song", trang_thai="cho",
                  created_at=now, heartbeat_at=now),
        LlmWaiter(resource="r", user_id="u", request_id="mo-coi", trang_thai="cho",
                  created_at=now - timedelta(hours=1),
                  heartbeat_at=now - timedelta(minutes=30)),
        LlmWaiter(resource="r", user_id="u", request_id="cu", trang_thai="xong",
                  created_at=now - timedelta(days=31),
                  heartbeat_at=now - timedelta(days=31)),
    ])
    db.commit()

    assert phong_cho.don_het_han(db, now=now) == 2
    db.commit()
    con = {w.request_id: w for w in db.query(LlmWaiter).all()}
    assert set(con) == {"song", "mo-coi"}
    assert con["song"].trang_thai == "cho"
    assert con["mo-coi"].trang_thai == "het_han" and con["mo-coi"].finished_at
    # Idempotent: chạy lại không đụng thêm gì.
    assert phong_cho.don_het_han(db, now=now) == 0


def test_drill_khoi_phuc_biet_uq_moi():
    van = (GOC / "tools" / "restore_drill_schema.py").read_text(encoding="utf-8")
    assert '"uq_llm_waiters_request"' in van
