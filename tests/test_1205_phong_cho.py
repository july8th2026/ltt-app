"""multijob Task 6 — phòng chờ `phong_cho`: vào, chờ theo nhịp, được nhận, hết hạn, rời.

Đồng hồ và hàm ngủ đều TIÊM (memory "tiêm nửa đối tượng thì phép đo vẫn sai": tiêm
đồng hồ mà quên hàm ngủ là test xanh mà quay CPU thật).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from platform_core.llm import luat_nhan as L

POOL = 204_800
T0 = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)


class DongHo:
    def __init__(self, t0=T0):
        self.t = t0

    def __call__(self):
        return self.t

    def ngu(self, s):
        self.t += timedelta(seconds=s)


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


def _yc(rid, user="u", slots=1, tok=10_000, lop=L.TUONG_TAC, prefill=1_000):
    from platform_core.llm.phong_cho import YeuCauCho

    return YeuCauCho(resource="llm_remote", slots=slots, token_pool=POOL, user_id=user,
                     mode="stream", holder_id=rid, request_id=rid, cua="stream",
                     lop=lop, token_dat_truoc=tok, token_prefill_moi=prefill)


def _vao(db, yc, dh):
    from platform_core.llm import phong_cho

    wid = phong_cho.vao(db, yc, now=dh())
    db.commit()
    return wid


def _chiem(db, user="khac", slot=0):
    from platform_core.models import ExecutionLease

    lease = ExecutionLease(resource="llm_remote", slot=slot, user_id=user,
                           mode="stream", holder_id=f"chiem-{user}", lop=L.TUONG_TAC,
                           token_dat_truoc=10_000)
    db.add(lease)
    db.commit()
    return lease


def _dong(db, wid):
    from platform_core.models import LlmWaiter

    db.expire_all()
    return db.get(LlmWaiter, wid)


def test_con_cho_thi_duoc_nhan_ngay_va_so_luot_ghi_lai(db):
    from platform_core.llm import phong_cho

    dh = DongHo()
    yc = _yc("r1")
    wid = _vao(db, yc, dh)
    lease_id = phong_cho.cho_nhan_chan(yc, waiter_id=wid, han_s=10, dong_ho=dh, ngu=dh.ngu)
    w = _dong(db, wid)
    assert lease_id and w.trang_thai == "nhan" and w.lease_id == lease_id
    assert w.admitted_at is not None and w.so_nhip == 1


def test_day_thi_yield_ly_do_roi_nhan_khi_co_cho(db):
    from platform_core.llm import admission, phong_cho

    dh = DongHo()
    chiem = _chiem(db)
    yc = _yc("r1")
    wid = _vao(db, yc, dh)
    g = phong_cho.cho_nhan(yc, waiter_id=wid, han_s=60, dong_ho=dh, ngu=dh.ngu)
    assert next(g) == L.CHO_SLOT
    assert _dong(db, wid).ly_do_cho == L.CHO_SLOT
    admission.release(db, chiem.id)
    db.commit()
    with pytest.raises(StopIteration) as ket:
        next(g)
    assert ket.value.value and _dong(db, wid).trang_thai == "nhan"


def test_qua_tran_cho_thi_het_cho_va_ghi_so(db):
    from platform_core.llm import phong_cho

    dh = DongHo()
    _chiem(db)
    yc = _yc("r1")
    wid = _vao(db, yc, dh)
    with pytest.raises(phong_cho.HetCho) as e:
        phong_cho.cho_nhan_chan(yc, waiter_id=wid, han_s=2, dong_ho=dh, ngu=dh.ngu)
    assert e.value.ly_do == L.CHO_SLOT
    w = _dong(db, wid)
    assert w.trang_thai == "het_han" and w.ket_qua == "het_cho" and w.finished_at


def test_khach_di_giua_luc_cho_thi_roi_hang(db):
    from platform_core.llm import phong_cho

    dh = DongHo()
    _chiem(db)
    yc = _yc("r1")
    wid = _vao(db, yc, dh)
    g = phong_cho.cho_nhan(yc, waiter_id=wid, han_s=60, dong_ho=dh, ngu=dh.ngu)
    next(g)
    g.close()                       # Starlette đóng generator khi khách ngắt
    w = _dong(db, wid)
    assert w.trang_thai == "roi" and w.ket_qua == "khach_di"


def _yc_whale(rid, user):
    from dataclasses import replace

    return replace(_yc(rid, user=user, prefill=150_000, tok=180_000), la_whale=True)


def test_phong_day_theo_so_nguoi_va_theo_so_whale(db):
    """L-12b (17/09/2026): phòng chờ chặn ĐỘ DÀI HÀNG bằng số người, không bằng token.

    Trần token cũ (`phong_day_token_prefill`) đã gỡ — "có vừa pool KV không" là
    việc của `luat_nhan` luật 2, lượt chưa vừa thì CHỜ chứ không 429.
    """
    from platform_core.llm import phong_cho

    dh = DongHo()
    _vao(db, _yc_whale("a", user="a"), dh)
    _vao(db, _yc("b", user="b", prefill=50_000), dh)
    with pytest.raises(phong_cho.PhongDay) as e:
        phong_cho.kiem_phong(db, resource="llm_remote", so_nguoi_toi_da=2, now=dh())
    assert e.value.ly_do == "phong_day_so_nguoi"
    # Σ token mới đang chờ 200K: lượt thường VẪN vào hàng (trước 17/09: 429).
    phong_cho.kiem_phong(db, resource="llm_remote", so_nguoi_toi_da=32, now=dh())
    # Whale thứ hai vào được khi trần là 2; whale thứ hai ĐANG CHỜ thì whale thứ ba 429.
    phong_cho.kiem_phong(db, resource="llm_remote", so_nguoi_toi_da=32,
                         la_whale=True, so_ca_voi_toi_da=2, now=dh())
    _vao(db, _yc_whale("c", user="c"), dh)
    with pytest.raises(phong_cho.PhongDay) as e:
        phong_cho.kiem_phong(db, resource="llm_remote", so_nguoi_toi_da=32,
                             la_whale=True, so_ca_voi_toi_da=2, now=dh())
    assert e.value.ly_do == "phong_day_ca_voi"


def test_phong_trong_thi_whale_lon_van_vao_duoc_hang(db):
    from platform_core.llm import phong_cho

    phong_cho.kiem_phong(db, resource="llm_remote", so_nguoi_toi_da=32,
                         la_whale=True, now=T0)


def test_fcfs_nguoi_vao_truoc_duoc_nhan_truoc(db):
    from platform_core.llm import admission, phong_cho

    dh = DongHo()
    chiem = _chiem(db)
    ya, yb = _yc("a", user="a"), _yc("b", user="b")
    wa = _vao(db, ya, dh)
    dh.ngu(1)
    wb = _vao(db, yb, dh)
    ga = phong_cho.cho_nhan(ya, waiter_id=wa, han_s=60, dong_ho=dh, ngu=dh.ngu)
    gb = phong_cho.cho_nhan(yb, waiter_id=wb, han_s=60, dong_ho=dh, ngu=dh.ngu)
    next(ga)
    next(gb)
    admission.release(db, chiem.id)
    db.commit()
    assert next(gb) == L.XEP_SAU            # B hỏi trước nhưng A đứng trước
    with pytest.raises(StopIteration):
        next(ga)                            # A được nhận


def test_ghi_ket_thuc_chot_so_luot(db):
    from platform_core.llm import phong_cho

    dh = DongHo()
    yc = _yc("r1")
    wid = _vao(db, yc, dh)
    phong_cho.cho_nhan_chan(yc, waiter_id=wid, han_s=10, dong_ho=dh, ngu=dh.ngu)
    phong_cho.ghi_ket_thuc(wid, "khach_ngat", now=dh())
    w = _dong(db, wid)
    assert w.trang_thai == "xong" and w.ket_qua == "khach_ngat" and w.finished_at


def test_dong_da_bi_chot_thi_khach_di(db):
    from platform_core.llm import phong_cho
    from platform_core.models import LlmWaiter

    dh = DongHo()
    _chiem(db)
    yc = _yc("r1")
    wid = _vao(db, yc, dh)
    db.get(LlmWaiter, wid).trang_thai = "het_han"
    db.commit()
    with pytest.raises(phong_cho.KhachDi):
        phong_cho.cho_nhan_chan(yc, waiter_id=wid, han_s=60, dong_ho=dh, ngu=dh.ngu)
