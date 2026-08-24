"""
test_252_gia_token — bảng giá token của model nhà. (H38)

Đây là **đường tiền**. Ba thứ neo ở đây:

  1. **Số chốt đúng là số chốt.** 50 / 10 / 400 credit mỗi 1M. Đổi một con số mà
     không đổi test là đổi giá lén.
  2. **Toàn số nguyên, không float.** Dấu phẩy động trong đường tiền là cách chắc
     nhất để hai lần cộng ra hai kết quả.
  3. **Không đo được thì KHÔNG tính tiền** — ném lỗi, đừng trả 0. Một hoá đơn 0đ
     âm thầm là một lỗ hổng doanh thu im lặng.
"""
from __future__ import annotations

import pytest

from platform_core.llm import gia_token as G
from platform_core.llm.cong_vlm import SuDung


def _su_dung(vao=0, ra=0, cache=0):
    return SuDung(token_vao=vao, token_ra=ra, token_vao_cache=cache, dang_tin=True)


# ── 1. Ba con số đã chốt ─────────────────────────────────────────────────────

def test_bang_gia_dung_so_da_chot():
    b = G.bang_gia()
    assert b["token_vao"] == 50
    assert b["token_vao_cache"] == 10
    assert b["token_ra"] == 400
    assert b["don_vi"] == "credit / 1.000.000 token"


def test_mot_trieu_token_ra_dung_400_credit():
    cp = G.tinh(_su_dung(ra=1_000_000))
    assert cp.ra_mcredit == 400 * G.MCREDIT_MOI_CREDIT
    assert cp.tong_credit_lam_tron_len == 400


def test_mot_trieu_token_vao_dung_50_credit():
    cp = G.tinh(_su_dung(vao=1_000_000))
    assert cp.tong_credit_lam_tron_len == 50


def test_mot_trieu_token_cache_dung_10_credit():
    """Toàn bộ prompt lấy từ cache ⇒ chỉ tính 20 % giá vào."""
    cp = G.tinh(_su_dung(vao=1_000_000, cache=1_000_000))
    assert cp.vao_moi_mcredit == 0
    assert cp.vao_cache_mcredit == 10 * G.MCREDIT_MOI_CREDIT
    assert cp.tong_credit_lam_tron_len == 10


# ── 2. Cache làm giảm giá đúng phần đáng giảm ────────────────────────────────

def test_cache_mot_phan_tinh_tach_hai_khoan():
    """8.000 token vào, 6.000 lấy từ cache ⇒ 2.000 tính giá đầy, 6.000 tính 20 %."""
    cp = G.tinh(_su_dung(vao=8_000, cache=6_000))
    assert cp.vao_moi_mcredit == (2_000 * 50 * 1_000) // 1_000_000     # = 100
    assert cp.vao_cache_mcredit == (6_000 * 10 * 1_000) // 1_000_000   # = 60
    assert cp.tong_mcredit == 160


def test_cache_lam_re_hon_that_su():
    khong_cache = G.tinh(_su_dung(vao=8_000, ra=1_500)).tong_mcredit
    co_cache = G.tinh(_su_dung(vao=8_000, ra=1_500, cache=6_400)).tong_mcredit
    assert co_cache < khong_cache
    # ⛔ Tính đủ giá cho phần cache là tính tiền khách hai lần cho cùng ngữ cảnh.
    assert co_cache == khong_cache - ((6_400 * 40 * 1_000) // 1_000_000)


# ── 3. Lượt gọi thật ─────────────────────────────────────────────────────────

def test_luot_bot_dien_hinh_ton_0_phay_3_credit():
    """2.000 vào + 500 ra = 0,3 credit = 30đ. Đây là con số làm lộ ra vấn đề
    'credit là số nguyên' — xem `tong_credit_lam_tron_len` ở dưới."""
    cp = G.tinh(_su_dung(vao=2_000, ra=500))
    assert cp.tong_mcredit == 300
    assert cp.tong_credit_lam_tron_len == 1, "lam tron len thu vuot 3,3 lan (phuong an C1)"


def test_goi_500k_mua_duoc_bao_nhieu_luot_bot():
    """500.000đ = 5.000 credit gốc + 15 % bonus = 5.750 credit."""
    from platform_core import billing_math
    tong = billing_math.tong_credits(billing_math.credits_base_tu_vnd(500_000), 15)
    assert tong == 5_750
    moi_luot = G.tinh(_su_dung(vao=2_000, ra=500)).tong_mcredit      # 300 mcredit
    assert (tong * G.MCREDIT_MOI_CREDIT) // moi_luot == 19_166       # ~19.000 luot


def test_luot_tro_ly_code():
    cp = G.tinh(_su_dung(vao=8_000, ra=1_500))
    assert cp.tong_mcredit == 400 + 600      # 0,4 vao + 0,6 ra = 1,0 credit


# ── 4. Không đo được thì không tính tiền ─────────────────────────────────────

def test_khong_co_usage_thi_nem_loi_chu_khong_tra_0():
    with pytest.raises(G.KhongDoDuocError):
        G.tinh(SuDung(dang_tin=False))


def test_usage_dang_tin_nhung_toan_0_thi_van_tinh_duoc():
    """Khác hẳn ở trên: đo được và bằng 0 là hợp lệ (yêu cầu bị từ chối sớm)."""
    assert G.tinh(_su_dung()).tong_mcredit == 0


# ── 5. Giữ chỗ ước CAO ───────────────────────────────────────────────────────

def test_uoc_tran_gia_dinh_khong_co_cache_va_sinh_du_max_tokens():
    tran = G.uoc_tran(token_vao_uoc=8_000, max_tokens=2_000)
    assert tran.vao_cache_mcredit == 0, "gia dinh khong cache — uoc CAO"
    assert tran.ra_mcredit == (2_000 * 400 * 1_000) // 1_000_000


def test_giu_cho_luon_du_cho_chi_phi_that():
    """Neo bất biến quan trọng nhất của phần giữ chỗ: giữ không bao giờ thiếu."""
    tran = G.uoc_tran(token_vao_uoc=8_000, max_tokens=2_000)
    for ra_that in (0, 500, 1_999, 2_000):
        for cache in (0, 4_000, 8_000):
            that = G.tinh(_su_dung(vao=8_000, ra=ra_that, cache=cache))
            assert that.tong_mcredit <= tran.tong_mcredit


def test_uoc_tran_khong_nhan_so_am():
    assert G.uoc_tran(token_vao_uoc=-5, max_tokens=-9).tong_mcredit == 0


# ── 6. Số nguyên, và nhãn phiên bản giá ──────────────────────────────────────

def test_moi_con_so_deu_la_int_khong_phai_float():
    cp = G.tinh(_su_dung(vao=1_234, ra=567, cache=890))
    for gt in (cp.vao_moi_mcredit, cp.vao_cache_mcredit, cp.ra_mcredit,
               cp.tong_mcredit, cp.tong_credit_lam_tron_len):
        assert isinstance(gt, int) and not isinstance(gt, bool)


def test_cong_don_khong_lech_so_voi_tinh_mot_lan():
    """1.000 lượt nhỏ cộng lại phải bằng đúng tổng — không trôi vì làm tròn."""
    mot_luot = G.tinh(_su_dung(vao=2_000, ra=500)).tong_mcredit
    assert mot_luot * 1_000 == 300_000


def test_chi_phi_mang_theo_nhan_phien_ban_gia():
    """`public_api/pricing.py`: hoà giải một khoản thu vài tháng sau nghĩa là đọc
    hai sự thật đều được ghi lúc đó — số tiền VÀ chế độ giá nào đang hiệu lực."""
    assert G.tinh(_su_dung(ra=10)).phien_ban_gia == G.PHIEN_BAN_GIA
    assert G.bang_gia()["phien_ban_gia"] == G.PHIEN_BAN_GIA
    assert G.PHIEN_BAN_GIA


def test_bang_gia_noi_ro_reasoning_va_cache():
    """⛔ Đừng để khách phát hiện sau khi nhận hoá đơn."""
    ghi_chu = G.bang_gia()["ghi_chu"].lower()
    assert "reasoning" in ghi_chu and "cache" in ghi_chu
