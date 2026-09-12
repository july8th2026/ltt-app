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

#: Model mà bảng giá của tệp này neo vào. D07 (dual-model 2.5) tách giá
#: theo model; những con số dưới đây là của model mặc định. Giá của
#: CẢ HAI model neo ở `test_1213_gia_theo_model.py`.
from platform_core.llm.gia_token import MODEL_GIA_MAC_DINH as _M


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
                        token_vao_uoc=8_000, max_tokens=2_000, model=_M)
    # 8.000 vao = 400 mcredit, 2.000 ra = 800 mcredit -> 1.200 -> ceil = 2 credit
    assert so == 2
    assert credit.so_du(db, u) == 998


def test_khong_du_credit_thi_khong_giu_va_khong_goi_model(db):
    from platform_core import credit
    from platform_core.llm import thanh_toan as T
    u = _nap(db, so=1)
    with pytest.raises(credit.ThieuCreditError):
        T.giu_cho_luot(db, user_id=u, request_id="r1",
                       token_vao_uoc=1_000_000, max_tokens=100_000, model=_M)
    assert credit.so_du(db, u) == 1, "khong du tien thi khong duoc dot GPU"


def test_thieu_request_id_bi_chan(db):
    from platform_core.llm import thanh_toan as T
    u = _nap(db)
    with pytest.raises(ValueError):
        T.giu_cho_luot(db, user_id=u, request_id="",
                       token_vao_uoc=100, max_tokens=100, model=_M)


def test_giu_cho_luon_du_cho_moi_ket_cuc_that(db):
    """Bất biến quan trọng nhất: thu không bao giờ vượt giữ."""
    from platform_core.llm import thanh_toan as T
    u = _nap(db, so=10_000)
    for i, (ra_that, cache) in enumerate(
            [(0, 0), (500, 0), (1_999, 0), (2_000, 0), (2_000, 8_000)]):
        rid = f"r{i}"
        giu = T.giu_cho_luot(db, user_id=u, request_id=rid,
                             token_vao_uoc=8_000, max_tokens=2_000, model=_M)
        kq = T.quyet_toan_luot(db, user_id=u, request_id=rid,
                               su_dung=_su_dung(vao=8_000, ra=ra_that, cache=cache), model=_M)
        assert kq.thu_credit <= giu


# ── 2. C1: làm tròn LÊN ──────────────────────────────────────────────────────

def test_MAC_DINH_la_C3_tich_luy_phan_le(db, monkeypatch):
    """2.000 vào + 500 ra = **0,3 credit** → thu **0**, phần lẻ ở lại.

    🟢 Chủ dự án chốt 2026-09-06: C3 là mặc định. Trước đó phép kiểm này ghim
    chiều ngược lại (*"mặc định vẫn là C1, thu 1"*) vì C3 đổi
    `toi_thieu_moi_luot_credit` — một điều khoản **công bố** — nên việc bật là
    quyết định của chủ dự án, không phải của bản vá. Quyết định ấy nay đã có.

    ⭐ Bản mới **khó xanh hơn** bản cũ: nó đòi một lượt 0,3 credit thu đúng
    **0**, trong khi `thu == 1` là thứ mọi chính sách làm tròn LÊN đều thoả.
    Đường lùi về C1: `LTT_TINH_TIEN_SAN_MOI_LUOT=1`.
    """
    from platform_core.llm import thanh_toan as T
    # ⭐ TU DUNG trang thai "khong co nao", dung muon trang thai cua nguoi
    #    chay. Do 06/09: chay ca cum voi `LTT_TINH_TIEN_SAN_MOI_LUOT=1` thi
    #    phep kiem nay DO — khong phai vi ma sai, ma vi no chua tu dung lay
    #    cau hinh ma no khang dinh.
    monkeypatch.delenv(T.CO_SAN_MOI_LUOT, raising=False)
    monkeypatch.delenv(T.CO_TICH_LUY, raising=False)
    u = _nap(db)
    T.giu_cho_luot(db, user_id=u, request_id="r1",
                   token_vao_uoc=2_000, max_tokens=500, model=_M)
    kq = T.quyet_toan_luot(db, user_id=u, request_id="r1",
                           su_dung=_su_dung(vao=2_000, ra=500), model=_M)
    assert kq.chi_phi_mcredit == 300, "bang gia KHONG doi — 50/10/400 credit/1M"
    assert kq.thu_credit == 0, "mac dinh la C3: 0,3 credit thi thu 0"


def test_BAT_C3_thi_thu_dung_phan_nguyen_cua_TONG(db, monkeypatch):
    """🔑 Mệnh đề của C3, phát biểu sao cho **không đổi theo số lượt**: tổng thu
    qua N lượt bằng đúng phần nguyên của tổng chi phí — không phải bằng N."""
    from platform_core.llm import thanh_toan as T
    # Duong lui THANG khi hai co mau thuan, nen phai tat no RO RANG.
    monkeypatch.delenv(T.CO_SAN_MOI_LUOT, raising=False)
    monkeypatch.setenv(T.CO_TICH_LUY, "1")
    u = _nap(db)
    tong = 0
    for i in range(7):
        T.giu_cho_luot(db, user_id=u, request_id=f"r{i}",
                       token_vao_uoc=2_000, max_tokens=500, model=_M)
        tong += T.quyet_toan_luot(db, user_id=u, request_id=f"r{i}",
                                  su_dung=_su_dung(vao=2_000, ra=500), model=_M).thu_credit
    assert tong == 2, "7 x 300 mcredit = 2.100 => 2 credit, khong phai 7"


def test_dieu_khoan_cong_bo_KHOP_voi_cach_thu_that(db, monkeypatch):
    """🔴 Mệnh đề đắt nhất, và nó **không đổi theo chính sách nào đang bật**.

    `public_api/dieu_khoan.py` công bố `gia_token.bang_gia()` ra ngoài. Đổi cách
    làm tròn mà quên đổi điều khoản là **công bố một lời hứa không còn đúng** —
    tệ hơn cả thu thừa.

    ⛔ Nên phép kiểm này không ghim 0 hay 1; nó ghim **hai thứ đó khớp nhau** ở
       CẢ HAI chính sách.
    """
    from platform_core.llm import gia_token
    from platform_core.llm import thanh_toan as T

    # (co duong lui, toi thieu cong bo) — MAC DINH la C3 (0), lui ve C1 (1).
    for co, toi_thieu in ((None, 0), ("1", 1)):
        if co is None:
            monkeypatch.delenv(T.CO_SAN_MOI_LUOT, raising=False)
        else:
            monkeypatch.setenv(T.CO_SAN_MOI_LUOT, co)
        assert gia_token.bang_gia()["toi_thieu_moi_luot_credit"] == toi_thieu

        u = _nap(db, user_id=f"dk-{co}")
        rid = f"dk{co}"
        T.giu_cho_luot(db, user_id=u, request_id=rid,
                       token_vao_uoc=2_000, max_tokens=500, model=_M)
        thu = T.quyet_toan_luot(db, user_id=u, request_id=rid,
                                su_dung=_su_dung(vao=2_000, ra=500), model=_M).thu_credit
        assert thu == toi_thieu, f"dieu khoan noi {toi_thieu} ma thu {thu} (co={co})"


def test_luot_khong_dung_gi_thi_thu_0(db):
    """Ceil(0) = 0. Nguong toi thieu chi ap cho luot co lam viec that."""
    from platform_core.llm import thanh_toan as T
    u = _nap(db)
    T.giu_cho_luot(db, user_id=u, request_id="r1",
                   token_vao_uoc=100, max_tokens=100, model=_M)
    kq = T.quyet_toan_luot(db, user_id=u, request_id="r1", su_dung=_su_dung(), model=_M)
    assert kq.thu_credit == 0


def test_cache_lam_giam_tien_that_su(db):
    from platform_core.llm import thanh_toan as T
    u = _nap(db, so=10_000)
    T.giu_cho_luot(db, user_id=u, request_id="a", token_vao_uoc=100_000, max_tokens=5_000, model=_M)
    khong = T.quyet_toan_luot(db, user_id=u, request_id="a",
                              su_dung=_su_dung(vao=100_000, ra=5_000), model=_M)
    T.giu_cho_luot(db, user_id=u, request_id="b", token_vao_uoc=100_000, max_tokens=5_000, model=_M)
    co = T.quyet_toan_luot(db, user_id=u, request_id="b",
                           su_dung=_su_dung(vao=100_000, ra=5_000, cache=90_000), model=_M)
    assert co.thu_credit < khong.thu_credit


# ── 3. Bận và lỗi: hoàn đủ ───────────────────────────────────────────────────

def test_ban_thi_hoan_du_so_du_ve_nhu_cu(db):
    from platform_core import credit
    from platform_core.llm import thanh_toan as T
    u = _nap(db)
    truoc = credit.so_du(db, u)
    T.giu_cho_luot(db, user_id=u, request_id="r1",
                   token_vao_uoc=8_000, max_tokens=2_000, model=_M)
    assert credit.so_du(db, u) < truoc
    T.hoan_luot(db, user_id=u, request_id="r1")
    assert credit.so_du(db, u) == truoc, "ban khong phai loi cua ai — khong ai tra tien"


def test_hoan_hai_lan_khong_tao_tien(db):
    from platform_core import credit
    from platform_core.llm import thanh_toan as T
    u = _nap(db)
    truoc = credit.so_du(db, u)
    T.giu_cho_luot(db, user_id=u, request_id="r1", token_vao_uoc=8_000, max_tokens=2_000, model=_M)
    T.hoan_luot(db, user_id=u, request_id="r1")
    T.hoan_luot(db, user_id=u, request_id="r1")
    assert credit.so_du(db, u) == truoc


def test_quyet_toan_hai_lan_khong_thu_hai_lan(db):
    from platform_core import credit
    from platform_core.llm import thanh_toan as T
    u = _nap(db)
    T.giu_cho_luot(db, user_id=u, request_id="r1", token_vao_uoc=8_000, max_tokens=2_000, model=_M)
    a = T.quyet_toan_luot(db, user_id=u, request_id="r1",
                          su_dung=_su_dung(vao=8_000, ra=2_000), model=_M)
    sau_lan_1 = credit.so_du(db, u)
    b = T.quyet_toan_luot(db, user_id=u, request_id="r1",
                          su_dung=_su_dung(vao=8_000, ra=2_000), model=_M)
    assert credit.so_du(db, u) == sau_lan_1
    assert a.thu_credit == b.thu_credit


# ── 4. Không đo được ⇒ hoàn đủ, không thu ────────────────────────────────────

def test_khong_do_duoc_thi_hoan_du_va_khong_thu(db):
    from platform_core import credit
    from platform_core.llm import thanh_toan as T
    u = _nap(db)
    truoc = credit.so_du(db, u)
    T.giu_cho_luot(db, user_id=u, request_id="r1", token_vao_uoc=8_000, max_tokens=2_000, model=_M)
    kq = T.quyet_toan_hoac_hoan(db, user_id=u, request_id="r1",
                                su_dung=_su_dung(dang_tin=False), model=_M)
    assert kq.da_do_duoc is False
    assert kq.thu_credit == 0
    assert credit.so_du(db, u) == truoc, \
        "thu tien ma khong co bang chung con te hon mat mot it tien"


def test_quyet_toan_luot_van_nem_loi_de_ben_goi_biet(db):
    """`quyet_toan_luot` KHÔNG được tự nuốt — chỉ `quyet_toan_hoac_hoan` mới xử."""
    from platform_core.llm import gia_token, thanh_toan as T
    u = _nap(db)
    T.giu_cho_luot(db, user_id=u, request_id="r1", token_vao_uoc=100, max_tokens=100, model=_M)
    with pytest.raises(gia_token.KhongDoDuocError):
        T.quyet_toan_luot(db, user_id=u, request_id="r1",
                          su_dung=_su_dung(dang_tin=False), model=_M)


# ── 5. Mang theo nhãn phiên bản giá ──────────────────────────────────────────

def test_ket_qua_thu_mang_nhan_phien_ban_gia(db):
    from platform_core.llm import gia_token, thanh_toan as T
    u = _nap(db)
    T.giu_cho_luot(db, user_id=u, request_id="r1", token_vao_uoc=8_000, max_tokens=2_000, model=_M)
    kq = T.quyet_toan_luot(db, user_id=u, request_id="r1",
                           su_dung=_su_dung(vao=8_000, ra=2_000), model=_M)
    assert kq.phien_ban_gia == gia_token.PHIEN_BAN_GIA
