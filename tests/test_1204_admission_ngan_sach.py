"""multijob Task 5 — `admission.xet_va_giu()`: luật nhận chạy trên CSDL thật.

`test_1203` chứng minh LUẬT; tệp này chứng minh luật được áp đúng lên ẢNH CHỤP
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
    """Lease tạo trước multijob (không `lop`) vẫn được ĐỌC là nền.

    ⛔ Cơ chế cũ của ca này CHẾT ngày 14/09/2026, và nó chết lặng lẽ. Bản cũ
       chứng minh mệnh đề trên bằng cách đẩy 3 lease `mode="job"` lên tài nguyên
       4 suất rồi đòi lượt nền thứ tư phải bị `CHO_SLOT` — tức dựa hoàn toàn vào
       `tran_nen(4) = 3`. Từ khi `ThamSo.chua_slot_tuong_tac` mặc định 0 thì
       `tran_nen(N, 0) = N`, nên **nhánh đầu của luật 3 không bao giờ chạy nữa**:
       luật 1 (`len(giu) >= so_slot`) chặn trước nó, và luật 1 chặn mọi lớp như
       nhau. Lớp của lease ĐANG GIỮ chỉ còn đi vào quyết định khi bật núm.

    ⇒ Giữ nguyên bản cũ là giữ một phép kiểm luôn đỏ; xoá nó là mất mệnh đề.
      Nên nó được viết lại quanh CHÍNH thứ nó đặt tên: phép ánh xạ.
    """
    from platform_core.llm import admission
    from platform_core.models import ExecutionLease

    for i in range(3):
        db.add(ExecutionLease(resource="llm_remote", slot=i, user_id=f"j{i}",
                              mode="job", holder_id=f"cu{i}"))
    db.commit()
    song = (db.query(ExecutionLease)
            .filter(ExecutionLease.resource == "llm_remote")
            .order_by(ExecutionLease.slot).all())

    # 1. Ánh xạ: `mode="job"` mà KHÔNG có `lop` phải đọc thành nền...
    assert [admission._lop_cua(x) for x in song] == [L.NEN, L.NEN, L.NEN]
    # ...còn mọi mode khác thì không. Thiếu vế này, một `_lop_cua` trả NEN cho
    # MỌI lease cũng làm vế trên xanh.
    assert admission._lop_cua(
        ExecutionLease(resource="llm_remote", slot=9, user_id="s",
                       mode="stream", holder_id="st")) == L.TUONG_TAC

    # 2. Và lớp ấy phải THẬT SỰ đi vào quyết định. Kiểm ở cấu hình duy nhất còn
    #    phân biệt được — `chua_slot_tuong_tac=1`, tức hành vi trước 14/09.
    giu = [L.Luot(id=x.holder_id, user_id=x.user_id, lop=admission._lop_cua(x))
           for x in song]
    ts = L.ThamSo(so_slot=4, chua_slot_tuong_tac=1)
    nen_moi = L.Luot(id="jm", user_id="job-moi", lop=L.NEN)
    assert L.xet(nen_moi, giu, [], ts) == L.PhanXu(False, L.CHO_SLOT)
    # đối chứng: cùng ảnh chụp ấy, lượt TƯƠNG TÁC vào được suất chừa.
    assert L.xet(L.Luot(id="tt", user_id="nguoi"), giu, [], ts).nhan

    # 3. Và trên CSDL thật, với mặc định hiện hành, khách tương tác vẫn vào được.
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


def test_lease_job_chet_duoc_thu_hoi_theo_NHIP_TIM_chu_khong_doi_20_phut(db):
    """Sự cố 14/09/2026: deploy giết worker ⇒ suất GPU bị xác chiếm 20 phút.

    Đường lỗi KHÔNG hỏng — `luong.py:_nha_suat` nhả suất đúng khi có handler
    chạy. Thứ hỏng là **hạn đỡ** cho ca worker bị giết: `job` dùng
    `ORPHAN_TIMEOUT` 1.200 s = **20 nhịp tim**, trong khi `stream` đã được hạ
    xuống 180 s = 3 nhịp từ L-11 (13/09) vì đúng loại sự cố ấy.

    Đo được lúc xảy ra: 3090 giữ **3 lease / 2 job thật**, và có **1 job đang
    xếp hàng** — tức cái xác ăn đúng suất người ta đang chờ.

    ⭐ Con số suy từ `HEARTBEAT_SECONDS`, không mượn của ai: `reclaim_expired` đo
       `heartbeat_at` chứ không đo `acquired_at`, nên ta có bằng chứng TRỰC TIẾP
       worker còn sống hay không. (Các hàng đợi chỉ-có-đồng-hồ như `river` để
       mặc định 1 giờ đúng vì họ không có bằng chứng ấy — mượn số của họ là
       mượn cả điều kiện họ đang chịu.)
    """
    from datetime import timedelta

    from platform_core.llm import admission
    from platform_core.models import ExecutionLease

    assert admission.ORPHAN_TIMEOUT_JOB.total_seconds() == \
        5 * admission.HEARTBEAT_SECONDS, "hạn phải suy từ nhịp tim"

    cu = admission._now() - timedelta(seconds=400)   # 6+ nhịp lỡ
    moi = admission._now() - timedelta(seconds=120)  # 2 nhịp lỡ — còn sống
    for slot, (mode, nhip) in enumerate([("job", cu), ("job", moi),
                                         ("sync", cu)]):
        db.add(ExecutionLease(resource="r_thu", slot=slot, user_id=f"u{slot}",
                              mode=mode, holder_id=f"h{slot}",
                              heartbeat_at=nhip))
    db.commit()

    assert admission.reclaim_expired(db, resource="r_thu") == 1
    db.commit()
    con = {(x.mode, x.slot) for x in db.query(ExecutionLease)
           .filter(ExecutionLease.resource == "r_thu").all()}
    assert con == {("job", 1), ("sync", 2)}, (
        f"phai xoa DUNG lease job chet: con {con}")
    # đối chứng: `sync` 400 s vẫn sống, vì nó theo `ORPHAN_TIMEOUT` 20 phút —
    # thiếu vế này thì một `reclaim_expired` xoá sạch mọi thứ cũng xanh.
