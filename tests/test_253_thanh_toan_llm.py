"""
test_253_thanh_toan_llm — thu tiền một lượt gọi model, phương án C1. (H38)

Chạy trên SQLite tạm, cùng khuôn `test_68_credit.py`.

Năm tính chất neo ở đây; sai bất kỳ cái nào là mất tiền thật hoặc mất khách:

  1. **Giữ chỗ không bao giờ thiếu** — giữ theo trần ước CAO.
  2. **Không đủ credit ⇒ không đốt GPU** — `ThieuCreditError` trước khi gọi model.
  3. **C1: làm tròn LÊN, tối thiểu 1 credit mỗi lượt.**
  4. **Bận ⇒ hoàn đủ.** Bận không phải lỗi của ai, không ai trả tiền cho nó.
  5. **Không đo được ⇒ hoàn đủ, KHÔNG thu.** Thu mà không có bằng chứng còn tệ
     hơn mất một ít tiền.
"""
from __future__ import annotations

import pytest

from tests.conftest import bao_dam_user


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'llm.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


def _nap(db, user_id="u1", so=1000):
    from platform_core import credit
    bao_dam_user(db, user_id)
    credit.cap_tay(db, user_id, so, by="test")
    return user_id


def _su_dung(vao=0, ra=0, cache=0, dang_tin=True):
    from platform_core.llm.cong_vlm import SuDung
    return SuDung(token_vao=vao, token_ra=ra, token_vao_cache=cache,
                  dang_tin=dang_tin)


# ── 1. Giữ chỗ ───────────────────────────────────────────────────────────────

def test_giu_cho_theo_tran_uoc_cao(db):
    from platform_core import credit
    from platform_core.llm import thanh_toan as T
    u = _nap(db)
    so = T.giu_cho_luot(db, user_id=u, request_id="r1",
                        token_vao_uoc=8_000, max_tokens=2_000)
    # 8.000 vao = 400 mcredit, 2.000 ra = 800 mcredit -> 1.200 -> ceil = 2 credit
    assert so == 2
    assert credit.so_du(db, u) == 998


def test_khong_du_credit_thi_khong_giu_va_khong_goi_model(db):
    from platform_core import credit
    from platform_core.llm import thanh_toan as T
    u = _nap(db, so=1)
    with pytest.raises(credit.ThieuCreditError):
        T.giu_cho_luot(db, user_id=u, request_id="r1",
                       token_vao_uoc=1_000_000, max_tokens=100_000)
    assert credit.so_du(db, u) == 1, "khong du tien thi khong duoc dot GPU"


def test_thieu_request_id_bi_chan(db):
    from platform_core.llm import thanh_toan as T
    u = _nap(db)
    with pytest.raises(ValueError):
        T.giu_cho_luot(db, user_id=u, request_id="",
                       token_vao_uoc=100, max_tokens=100)


def test_giu_cho_luon_du_cho_moi_ket_cuc_that(db):
    """Bất biến quan trọng nhất: thu không bao giờ vượt giữ."""
    from platform_core.llm import thanh_toan as T
    u = _nap(db, so=10_000)
    for i, (ra_that, cache) in enumerate(
            [(0, 0), (500, 0), (1_999, 0), (2_000, 0), (2_000, 8_000)]):
        rid = f"r{i}"
        giu = T.giu_cho_luot(db, user_id=u, request_id=rid,
                             token_vao_uoc=8_000, max_tokens=2_000)
        kq = T.quyet_toan_luot(db, user_id=u, request_id=rid,
                               su_dung=_su_dung(vao=8_000, ra=ra_that, cache=cache))
        assert kq.thu_credit <= giu


# ── 2. C1: làm tròn LÊN ──────────────────────────────────────────────────────

def test_C1_luot_nho_van_thu_tron_1_credit(db):
    """2.000 vao + 500 ra = 0,3 credit -> thu 1 credit. Day la cai gia cua C1."""
    from platform_core.llm import thanh_toan as T
    u = _nap(db)
    T.giu_cho_luot(db, user_id=u, request_id="r1",
                   token_vao_uoc=2_000, max_tokens=500)
    kq = T.quyet_toan_luot(db, user_id=u, request_id="r1",
                           su_dung=_su_dung(vao=2_000, ra=500))
    assert kq.chi_phi_mcredit == 300
    assert kq.thu_credit == 1


def test_C1_duoc_cong_bo_trong_bang_gia(db):
    """⛔ Khach gọi nhieu se tu tinh ra trong mot ngay — tha ho doc duoc tu truoc."""
    from platform_core.llm import gia_token
    b = gia_token.bang_gia()
    assert b["toi_thieu_moi_luot_credit"] == 1
    assert "toi thieu 1 credit" in b["ghi_chu"]


def test_luot_khong_dung_gi_thi_thu_0(db):
    """Ceil(0) = 0. Nguong toi thieu chi ap cho luot co lam viec that."""
    from platform_core.llm import thanh_toan as T
    u = _nap(db)
    T.giu_cho_luot(db, user_id=u, request_id="r1",
                   token_vao_uoc=100, max_tokens=100)
    kq = T.quyet_toan_luot(db, user_id=u, request_id="r1", su_dung=_su_dung())
    assert kq.thu_credit == 0


def test_cache_lam_giam_tien_that_su(db):
    from platform_core.llm import thanh_toan as T
    u = _nap(db, so=10_000)
    T.giu_cho_luot(db, user_id=u, request_id="a", token_vao_uoc=100_000, max_tokens=5_000)
    khong = T.quyet_toan_luot(db, user_id=u, request_id="a",
                              su_dung=_su_dung(vao=100_000, ra=5_000))
    T.giu_cho_luot(db, user_id=u, request_id="b", token_vao_uoc=100_000, max_tokens=5_000)
    co = T.quyet_toan_luot(db, user_id=u, request_id="b",
                           su_dung=_su_dung(vao=100_000, ra=5_000, cache=90_000))
    assert co.thu_credit < khong.thu_credit


# ── 3. Bận và lỗi: hoàn đủ ───────────────────────────────────────────────────

def test_ban_thi_hoan_du_so_du_ve_nhu_cu(db):
    from platform_core import credit
    from platform_core.llm import thanh_toan as T
    u = _nap(db)
    truoc = credit.so_du(db, u)
    T.giu_cho_luot(db, user_id=u, request_id="r1",
                   token_vao_uoc=8_000, max_tokens=2_000)
    assert credit.so_du(db, u) < truoc
    T.hoan_luot(db, user_id=u, request_id="r1")
    assert credit.so_du(db, u) == truoc, "ban khong phai loi cua ai — khong ai tra tien"


def test_hoan_hai_lan_khong_tao_tien(db):
    from platform_core import credit
    from platform_core.llm import thanh_toan as T
    u = _nap(db)
    truoc = credit.so_du(db, u)
    T.giu_cho_luot(db, user_id=u, request_id="r1", token_vao_uoc=8_000, max_tokens=2_000)
    T.hoan_luot(db, user_id=u, request_id="r1")
    T.hoan_luot(db, user_id=u, request_id="r1")
    assert credit.so_du(db, u) == truoc


def test_quyet_toan_hai_lan_khong_thu_hai_lan(db):
    from platform_core import credit
    from platform_core.llm import thanh_toan as T
    u = _nap(db)
    T.giu_cho_luot(db, user_id=u, request_id="r1", token_vao_uoc=8_000, max_tokens=2_000)
    a = T.quyet_toan_luot(db, user_id=u, request_id="r1",
                          su_dung=_su_dung(vao=8_000, ra=2_000))
    sau_lan_1 = credit.so_du(db, u)
    b = T.quyet_toan_luot(db, user_id=u, request_id="r1",
                          su_dung=_su_dung(vao=8_000, ra=2_000))
    assert credit.so_du(db, u) == sau_lan_1
    assert a.thu_credit == b.thu_credit


# ── 4. Không đo được ⇒ hoàn đủ, không thu ────────────────────────────────────

def test_khong_do_duoc_thi_hoan_du_va_khong_thu(db):
    from platform_core import credit
    from platform_core.llm import thanh_toan as T
    u = _nap(db)
    truoc = credit.so_du(db, u)
    T.giu_cho_luot(db, user_id=u, request_id="r1", token_vao_uoc=8_000, max_tokens=2_000)
    kq = T.quyet_toan_hoac_hoan(db, user_id=u, request_id="r1",
                                su_dung=_su_dung(dang_tin=False))
    assert kq.da_do_duoc is False
    assert kq.thu_credit == 0
    assert credit.so_du(db, u) == truoc, \
        "thu tien ma khong co bang chung con te hon mat mot it tien"


def test_quyet_toan_luot_van_nem_loi_de_ben_goi_biet(db):
    """`quyet_toan_luot` KHÔNG được tự nuốt — chỉ `quyet_toan_hoac_hoan` mới xử."""
    from platform_core.llm import gia_token, thanh_toan as T
    u = _nap(db)
    T.giu_cho_luot(db, user_id=u, request_id="r1", token_vao_uoc=100, max_tokens=100)
    with pytest.raises(gia_token.KhongDoDuocError):
        T.quyet_toan_luot(db, user_id=u, request_id="r1",
                          su_dung=_su_dung(dang_tin=False))


# ── 5. Mang theo nhãn phiên bản giá ──────────────────────────────────────────

def test_ket_qua_thu_mang_nhan_phien_ban_gia(db):
    from platform_core.llm import gia_token, thanh_toan as T
    u = _nap(db)
    T.giu_cho_luot(db, user_id=u, request_id="r1", token_vao_uoc=8_000, max_tokens=2_000)
    kq = T.quyet_toan_luot(db, user_id=u, request_id="r1",
                           su_dung=_su_dung(vao=8_000, ra=2_000))
    assert kq.phien_ban_gia == gia_token.PHIEN_BAN_GIA
