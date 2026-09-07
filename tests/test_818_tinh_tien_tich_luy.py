"""
test_818 — C3: tích luỹ phần lẻ thay vì làm tròn LÊN mỗi lượt gọi. (R2b)

Đo 05/09 (`docs/CHATLTT_V3/04_ADR_R2B_TINH_TIEN_LUOT.md`): C1 làm một hội thoại
20 lượt ngắn bị thu **20 credit** trong khi giá niêm yết của chính ta là **~3**,
và mọi lượt dưới ~1 credit làm ta **đắt hơn giá bán lẻ**.

Ba nhóm mệnh đề, và nhóm 2 là nhóm đắt:

  1. Cộng dồn đúng: phần lẻ ở lại, phần nguyên được thu.
  2. **Không thu hai lần, không mất phần lẻ** — phát lại và bị cap.
  3. Đường lùi `LTT_TINH_TIEN_SAN_MOI_LUOT=1` trả lại đúng hành vi C1.

🟢 **C3 là MẶC ĐỊNH từ 06/09** (chủ dự án chốt). Trước đó nó là opt-in, và
tệp này ghim chiều ngược lại — mục 3 đã đổi theo, xem
`test_C3_la_MAC_DINH_khong_phai_opt_in`.
"""
from __future__ import annotations

import pytest

from platform_core import credit
from platform_core.llm import gia_token, thanh_toan
from platform_core.llm.cong_vlm import SuDung


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "t.db").as_posix())
    # ⭐ KHONG bat co gi: C3 la MAC DINH tu 06/09. Mot fixture phai bat co
    #    de co hanh vi mac dinh la mot fixture noi doi ve mac dinh.
    monkeypatch.delenv(thanh_toan.CO_SAN_MOI_LUOT, raising=False)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session
    from platform_core.registry import load_app_tables
    load_app_tables()
    Base.metadata.create_all(get_engine())
    gen = get_session()
    s = next(gen)
    yield s
    try:
        next(gen)
    except StopIteration:
        pass
    dbmod.reset_engine()


def _user(db, credits=10_000):
    from platform_core.users import tao_nguoi_dung
    u = tao_nguoi_dung(db, email="t818@example.com", password="a-good-password-12",
                       is_verified=True)
    db.flush()
    credit.cap_tay(db, u.id, credits, by="test")
    db.commit()
    return u.id


def _du(db, uid) -> int:
    from platform_core.models import User
    db.expire_all()
    return int(db.get(User, uid).mcredit_du or 0)


def _luot(vao=2000, ra=500, cache=0):
    """Một lượt gọi. 2.000 vào + 500 ra = 100 + 200 = **300 mcredit**."""
    return SuDung(token_vao=vao, token_ra=ra, token_vao_cache=cache, dang_tin=True)


def _thu(db, uid, rid, su_dung=None, giu=5):
    credit.giu_cho(db, uid, giu, rid)
    return thanh_toan.quyet_toan_luot(db, user_id=uid, request_id=rid,
                                      su_dung=su_dung or _luot())


# ── 0. Neo: một lượt điển hình tốn bao nhiêu ───────────────────────────────

def test_mot_luot_dien_hinh_ton_300_mcredit(db):
    cp = gia_token.tinh(_luot())
    assert cp.tong_mcredit == 300, "2.000 vao (50/1M) + 500 ra (400/1M)"
    assert cp.tong_credit_lam_tron_len == 1, "C1 lam tron len => 1 credit"


# ── 1. Cộng dồn ────────────────────────────────────────────────────────────

def test_luot_dau_KHONG_thu_gi_va_giu_lai_phan_le(db):
    """🔴 Đây là khác biệt trung tâm với C1: 0,3 credit thì thu **0**, không thu 1."""
    uid = _user(db)
    kq = _thu(db, uid, "r1")
    assert kq.thu_credit == 0
    assert _du(db, uid) == 300


def test_bon_luot_moi_luot_300_thi_thu_1_o_luot_thu_TU(db):
    """300 × 4 = 1.200 ⇒ thu 1 credit, còn lại 200 mcredit."""
    uid = _user(db)
    thu = [_thu(db, uid, f"r{i}").thu_credit for i in range(1, 5)]
    assert thu == [0, 0, 0, 1]
    assert _du(db, uid) == 200


def test_hai_muoi_luot_ngan_thu_6_thay_vi_20(db):
    """⭐ Con số của ADR: C1 thu 20, C3 thu đúng phần nguyên của tổng thật."""
    uid = _user(db)
    tong = sum(_thu(db, uid, f"r{i}").thu_credit for i in range(20))
    assert tong == 6, "20 x 300 mcredit = 6.000 => 6 credit"
    assert _du(db, uid) == 0
    # C1 se thu 20 cho dung tap luot nay.
    assert 20 / max(tong, 1) > 3, "C1 dat hon C3 hon 3 lan"


def test_mot_luot_LON_van_thu_ngay(db):
    """Tích luỹ không làm chậm việc thu: lượt lớn vẫn thu đủ phần nguyên ngay."""
    uid = _user(db)
    kq = _thu(db, uid, "r1", _luot(vao=100_000, ra=10_000), giu=99)
    assert kq.thu_credit == 9, "100k vao=5.000 + 10k ra=4.000 = 9.000 mcredit"
    assert _du(db, uid) == 0


def test_bac_CACHE_duoc_tinh_dung(db):
    """Vòng lặp agentic sống nhờ bậc cache — nó phải đi vào phép cộng."""
    uid = _user(db)
    _thu(db, uid, "r1", _luot(vao=10_000, ra=0, cache=9_000), giu=9)
    # 1.000 moi x50 + 9.000 cache x10 = 50 + 90 = 140 mcredit
    assert _du(db, uid) == 140


# ── 2. Không thu hai lần, không mất phần lẻ ────────────────────────────────

def test_PHAT_LAI_khong_cong_phan_le_lan_hai(db):
    """🔴 `credit.quyet_toan` idempotent theo `request_id`, nhưng `mcredit_du`
    **không tự biết**. Cộng hai lần là thu của khách một khoản không có bút toán
    nào đối chứng."""
    uid = _user(db)
    _thu(db, uid, "r1")
    assert _du(db, uid) == 300
    lai = thanh_toan.quyet_toan_luot(db, user_id=uid, request_id="r1",
                                     su_dung=_luot())
    assert _du(db, uid) == 300, "phat lai KHONG duoc cong them"
    assert lai.thu_credit == 0


def test_phat_lai_mot_luot_DA_THU_khong_doi_gi(db):
    uid = _user(db)
    for i in range(4):
        _thu(db, uid, f"r{i}")
    du_truoc = _du(db, uid)
    thanh_toan.quyet_toan_luot(db, user_id=uid, request_id="r3", su_dung=_luot())
    assert _du(db, uid) == du_truoc


def test_bi_CAP_o_muc_da_giu_thi_phan_chua_thu_O_LAI(db):
    """🔴 `credit.quyet_toan` cap `charged = min(de_nghi, held)`. Trừ theo số ĐỀ
    NGHỊ thay vì số THẬT SỰ THU sẽ làm phần bị cap **bốc hơi** — mất doanh thu
    im lặng, và không dòng lỗi nào báo."""
    uid = _user(db)
    # Giu 2 credit nhung chi phi that la 9 credit.
    credit.giu_cho(db, uid, 2, "r1")
    kq = thanh_toan.quyet_toan_luot(db, user_id=uid, request_id="r1",
                                    su_dung=_luot(vao=100_000, ra=10_000))
    assert kq.thu_credit == 2, "chi thu duoc bang muc da giu"
    assert _du(db, uid) == 9_000 - 2_000, "phan chua thu O LAI, khong boc hoi"


def test_phan_le_KHONG_bao_gio_am(db):
    uid = _user(db)
    credit.giu_cho(db, uid, 5, "r1")
    thanh_toan.quyet_toan_luot(db, user_id=uid, request_id="r1", su_dung=_luot())
    assert _du(db, uid) >= 0


def test_du_luon_nho_hon_1000_khi_khong_bi_cap(db):
    """Bất biến: không bị cap thì phần lẻ luôn trong [0, 1.000)."""
    uid = _user(db)
    for i in range(13):
        _thu(db, uid, f"r{i}", _luot(vao=3_333, ra=777))
        assert 0 <= _du(db, uid) < 1000, f"luot {i}"


# ── 3. Đường lùi ───────────────────────────────────────────────────────────

def test_DUONG_LUI_tra_lai_dung_hanh_vi_C1(db, monkeypatch):
    """`LTT_TINH_TIEN_SAN_MOI_LUOT=1` phải quay về C1 trong một biến môi
    trường — vì đây là **tiền**, và người trực phải tắt được trong một
    phút chứ không phải chờ một lượt phát hành."""
    monkeypatch.setenv(thanh_toan.CO_SAN_MOI_LUOT, "1")
    uid = _user(db)
    thu = [_thu(db, uid, f"r{i}").thu_credit for i in range(4)]
    assert thu == [1, 1, 1, 1], "C1: moi luot lam tron LEN"
    assert _du(db, uid) == 0, "duong lui KHONG dung toi phan le"


def test_C3_la_MAC_DINH_khong_phai_opt_in(db, monkeypatch):
    """🟢 Chủ dự án chốt 06/09: C3 là mặc định. Không cờ nào ⇒ vẫn là C3.

    ⛔ Mệnh đề này ĐỔI CHIỀU so với bản 05/09 (*"mặc định phải là hành vi
    cũ"*), và đổi vì một **quyết định**, không vì mã dễ hơn. Bản mới KHÓ
    xanh hơn: nó đòi một lượt 0,3 credit thu **0**, trong khi bản cũ chỉ
    đòi nó thu 1 — thứ mọi chính sách làm tròn đều thoả."""
    monkeypatch.delenv(thanh_toan.CO_TICH_LUY, raising=False)
    monkeypatch.delenv(thanh_toan.CO_SAN_MOI_LUOT, raising=False)
    uid = _user(db)
    assert _thu(db, uid, "r1").thu_credit == 0, "khong co nao => C3"
    assert _du(db, uid) == 300, "phan le phai o lai"


@pytest.mark.parametrize("gt", ["0", "", "yes", "off", "2"])
def test_co_fail_closed_moi_cach_viet_la_deu_la_TAT(db, monkeypatch, gt):
    """Mọi cách viết ngoài `1/true/on` đều là TẮT ⇒ **không** lùi về C1.

    ⭐ Fail-closed ở đây nghĩa là *giữ chính sách đang chạy*, và chính sách
    đang chạy nay là C3. Một cờ nhận nhiều cách viết là một cờ mà người ta
    tưởng đã bật trong khi chưa."""
    monkeypatch.setenv(thanh_toan.CO_SAN_MOI_LUOT, gt)
    uid = _user(db)
    assert _thu(db, uid, "r1").thu_credit == 0, "cach viet la => KHONG lui"


# ── 4. Sổ cái vẫn là sự thật ───────────────────────────────────────────────

def test_so_du_khop_voi_tong_da_thu(db):
    """⛔ `mcredit_du` là bộ đếm dẫn xuất. Số dư phải chỉ phản ánh `credit_entries`."""
    uid = _user(db, credits=1000)
    tong_thu = sum(_thu(db, uid, f"r{i}").thu_credit for i in range(20))
    db.commit()
    assert credit.so_du(db, uid) == 1000 - tong_thu


def test_mat_phan_le_thi_KHACH_duoc_loi_khong_ai_mat_tien(db):
    """Xoá `mcredit_du` (mô phỏng hạ migration) không tạo bút toán sai nào."""
    from platform_core.models import User
    uid = _user(db, credits=1000)
    for i in range(3):
        _thu(db, uid, f"r{i}")
    truoc = credit.so_du(db, uid)
    db.get(User, uid).mcredit_du = 0          # mat phan le
    db.commit()
    assert credit.so_du(db, uid) == truoc, "so du KHONG doi — phan le chua tung la tien"
