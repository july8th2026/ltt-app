"""multijob Task 5 — `admission.xet_va_giu()`: luật nhận chạy trên CSDL thật.

`test_953` chứng minh LUẬT; tệp này chứng minh luật được áp đúng lên ẢNH CHỤP
CSDL (lease sống + người chờ còn nhịp), và đường cũ không đổi một hành vi nào.
"""
from __future__ import annotations

import os
import threading
from datetime import datetime, timedelta, timezone

import pytest

from platform_core.llm import luat_nhan as L

POOL = 204_800


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'adm.db').as_posix()}")
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


def _xet(db, **kw):
    from platform_core.llm import admission

    mac_dinh = dict(resource="llm_remote", slots=4, user_id="u", mode="stream",
                    holder_id=kw.pop("holder_id", "h"), token_pool=POOL,
                    lop=L.TUONG_TAC, token_dat_truoc=10_000)
    mac_dinh.update(kw)
    return admission.xet_va_giu(db, **mac_dinh)


def test_duong_cu_khong_doi_khi_khong_khai_ngan_sach(db):
    from platform_core.llm import admission

    a = admission.acquire(db, resource="r", slots=1, user_id="u1", mode="sync",
                          holder_id="h1")
    assert a is not None and a.lop == "" and a.token_dat_truoc == 0
    db.commit()
    assert admission.acquire(db, resource="r", slots=1, user_id="u2", mode="sync",
                             holder_id="h2") is None


def test_ngan_sach_chan_luot_khong_vua_roi_nhan_sau_khi_nha(db):
    from platform_core.llm import admission

    dai, ly_do = _xet(db, user_id="a", holder_id="dai", token_dat_truoc=170_000)
    assert dai is not None and ly_do == ""
    assert dai.token_dat_truoc == 170_000 and dai.lop == L.TUONG_TAC
    db.commit()

    moi, ly_do = _xet(db, user_id="b", holder_id="moi", token_dat_truoc=60_000)
    assert moi is None and ly_do == L.CHO_NGAN_SACH
    db.rollback()

    admission.release(db, dai.id)
    db.commit()
    moi, ly_do = _xet(db, user_id="b", holder_id="moi", token_dat_truoc=60_000)
    assert moi is not None, ly_do


def test_bon_slot_that_su_cap_bon_lease(db):
    for i in range(4):
        lease, ly_do = _xet(db, user_id=f"u{i}", holder_id=f"h{i}")
        assert lease is not None, ly_do
        db.commit()
    lease, ly_do = _xet(db, user_id="u9", holder_id="h9")
    assert lease is None and ly_do == L.CHO_SLOT


def test_nguoi_tuong_tac_dang_cho_lam_nen_nhuong(db):
    from platform_core.models import LlmWaiter

    now = datetime.now(timezone.utc)
    db.add(LlmWaiter(resource="llm_remote", user_id="khach", request_id="r1",
                     lop=L.TUONG_TAC, token_dat_truoc=5_000, trang_thai="cho",
                     created_at=now, heartbeat_at=now))
    db.commit()
    lease, ly_do = _xet(db, user_id="job", holder_id="j1", lop=L.NEN, mode="job")
    assert lease is None and ly_do == L.NEN_NHUONG


def test_nguoi_cho_mat_nhip_khong_con_tranh_cho(db):
    from platform_core.models import LlmWaiter

    cu = datetime.now(timezone.utc) - timedelta(minutes=5)
    db.add(LlmWaiter(resource="llm_remote", user_id="khach", request_id="r1",
                     lop=L.TUONG_TAC, trang_thai="cho", created_at=cu, heartbeat_at=cu))
    db.commit()
    lease, ly_do = _xet(db, user_id="job", holder_id="j1", lop=L.NEN, mode="job")
    assert lease is not None, ly_do


def test_lease_cu_mode_job_duoc_hieu_la_nen(db):
    """Lease tạo trước multijob (không `lop`) vẫn tính đúng vào trần nền."""
    from platform_core.models import ExecutionLease

    for i in range(3):
        db.add(ExecutionLease(resource="llm_remote", slot=i, user_id=f"j{i}",
                              mode="job", holder_id=f"cu{i}"))
    db.commit()
    lease, ly_do = _xet(db, user_id="job-moi", holder_id="jm", lop=L.NEN, mode="job")
    assert lease is None and ly_do == L.CHO_SLOT
    lease, ly_do = _xet(db, user_id="khach", holder_id="k")
    assert lease is not None, ly_do


def test_xoa_co_whale_khi_prefill_xong(db):
    from platform_core.llm import admission
    from platform_core.models import ExecutionLease

    w, _ = _xet(db, user_id="a", holder_id="w", la_whale=True, tuoi_cho_s=99)
    db.commit()
    assert admission.xoa_co_whale(w.id) is True
    db.expire_all()
    assert db.get(ExecutionLease, w.id).la_whale is False
    assert admission.xoa_co_whale(w.id) is False      # idempotent


@pytest.mark.skipif(not os.environ.get("LTT_TEST_DATABASE_URL"),
                    reason="can PostgreSQL test (LTT_TEST_DATABASE_URL) — khuon test_73")
def test_race_postgresql_khong_bao_gio_vuot_pool(monkeypatch):
    """20 luồng cùng xin 60K trên pool 204.800 ⇒ tối đa 3 được nhận (advisory lock)."""
    monkeypatch.setenv("LTT_DATABASE_URL", os.environ["LTT_TEST_DATABASE_URL"])
    import platform_core.db as dbmod
    from platform_core.llm import admission
    from platform_core.models import ExecutionLease

    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session()
    s = next(gen)
    s.query(ExecutionLease).filter(ExecutionLease.resource == "race").delete()
    s.commit()
    s.close()

    nhan = []

    def mot(i):
        g = dbmod.get_session()
        d = next(g)
        try:
            lease, _ = admission.xet_va_giu(
                d, resource="race", slots=8, user_id=f"u{i}", mode="stream",
                holder_id=f"h{i}", token_pool=POOL, lop=L.TUONG_TAC,
                token_dat_truoc=60_000)
            d.commit()
            if lease is not None:
                nhan.append(lease.id)
        finally:
            d.close()

    ts = [threading.Thread(target=mot, args=(i,)) for i in range(20)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert len(nhan) == 3, f"vuot pool: {len(nhan)} luot 60K tren pool {POOL}"
    dbmod.reset_engine()
