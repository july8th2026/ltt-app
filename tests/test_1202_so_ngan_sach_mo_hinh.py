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


#: Nam migration cua chuong trinh dual-model, theo dung thu tu chuoi.
CHUOI_DUAL = ("7c1e4b9a2d58", "b4d7f2c19e30", "c7a3f1e5b904",
              "d91f6c37ab24", "a3f7c214e8b9")


def test_migration_noi_dung_chuoi_va_mot_head():
    """Chuoi dual phai NOI VAO dong kia va khong de ra head thu hai.

    🔴 BAN TRUOC GHIM MOT CHUOI CU THE: `rev.down_revision == "e26c9a41d8b5"`.
       Do la head cua trunk **luc viet** (H45.1), khong phai mot bat bien — va no
       do ngay lan dau ai do forward-port chuoi nay len mot head moi hon, du viec
       forward-port ay CHINH LA dieu dung phai lam.

       Da xay ra 12/09: CSDL production dung o `d9a1f6c2b3e5` (head do Voice RC1
       tao), con `alembic/versions` cua nhanh dual khong co revision ay ⇒
       `alembic upgrade head` khong ve duoc duong di, deploy may A chet va
       production tat ~4 phut. Ban sua la doi `down_revision` sang head hien
       hanh — va phep kiem cu do vi chinh ban sua do.

    ⭐ Nen o day ghim DIEU CAN DUNG, khong ghim CON SO:
         1. dung MOT head;
         2. goc chuoi dual noi vao mot revision CO THAT va KHONG thuoc chuoi dual
            (tuc no bam vao dong kia, khong lo lung, khong tu vong);
         3. ca nam mat xich deu di den duoc head.

    ⛔ Menh de 2 la thu giu lai suc manh cua ban cu: mot `down_revision = None`
       hay tro vao chinh chuoi dual van de ra head thu hai, va van bi bat.
    """
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    scripts = ScriptDirectory.from_config(Config(str(GOC / "alembic.ini")))
    assert len(scripts.get_heads()) == 1, scripts.get_heads()

    goc = scripts.get_revision(REV)
    assert goc.down_revision, "goc chuoi dual khong duoc lo lung (down_revision None)"
    assert goc.down_revision not in CHUOI_DUAL, (
        f"goc chuoi dual tro vao chinh chuoi ({goc.down_revision}) - do la mot "
        f"vong, khong phai mot moi noi sang dong kia")
    cha = scripts.get_revision(goc.down_revision)
    assert cha is not None, f"down_revision {goc.down_revision} khong ton tai"

    duong = {r.revision for r in scripts.walk_revisions("base", "heads")}
    thieu = [r for r in CHUOI_DUAL if r not in duong]
    assert not thieu, f"mat xich khong den duoc head: {thieu}"

    assert "llm_waiters" in (goc.doc or "") or "ngân sách" in (goc.doc or "")


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
    uq = {u["name"] for u in insp.get_unique_constraints("llm_waiters")}
    assert "uq_llm_waiters_request" in uq

    # ⭐ Mô hình và migration phải nói CÙNG một tập cột — lệch là `create_all`
    #    (test) và `alembic upgrade` (production) dựng hai lược đồ khác nhau.
    #
    # 🔴 NHƯNG PHÉP SO ẤY PHẢI ĐO Ở `heads`, KHÔNG Ở `REV`. `platform_core.models`
    #    luôn tả lược đồ MỚI NHẤT, nên so nó với lược đồ tại REV là so hai mốc
    #    thời gian khác nhau: phép kiểm sẽ đỏ vì **người sau thêm một cột**, chứ
    #    không vì migration của REV sai. Đã xảy ra thật — dual-model 5.3 thêm
    #    `llm_waiters.cho_residency_s` (rev `d91f6c37ab24`) và ca này đỏ trong
    #    khi cả mô hình lẫn cả hai migration đều đúng. Viết lại cho **bất biến
    #    với việc tập cột rộng ra**: lên `heads` rồi mới so, rồi quay về REV để
    #    phần kiểm lên/xuống một bước bên dưới vẫn đo đúng thứ nó muốn đo.
    command.upgrade(cfg, "heads")
    insp_head = inspect(create_engine(url))
    assert {c.name for c in LlmWaiter.__table__.columns} == {
        c["name"] for c in insp_head.get_columns("llm_waiters")}
    assert {c.name for c in ExecutionLease.__table__.columns} == {
        c["name"] for c in insp_head.get_columns("execution_leases")}
    command.downgrade(cfg, REV)

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
