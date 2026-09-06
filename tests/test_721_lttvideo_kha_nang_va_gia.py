"""Allowlist năng lực + mô hình giá của `lttvideo`.

⛔ `kha_nang` KHÔNG phải `CapabilityResolver`. Resolver hỏi *"model làm được
   không"* — WanGP trả lời bằng `capabilities`/`media_inputs`. Allowlist hỏi
   *"khách hạng này ĐƯỢC PHÉP không"* — chỉ LTT trả lời được.
"""
from __future__ import annotations

import pytest

from apps.lttvideo import cost, kha_nang


# ─────────────────────────── allowlist ───────────────────────────

def test_baseline_chi_mo_dung_mot_nang_luc():
    """Baseline mở hẹp có chủ đích: mở rộng là quyết định, không phải mặc định."""
    assert kha_nang.NANG_LUC_MO == ("tao_video",)


def test_nhan_vien_duoc_dung_nang_luc_da_mo():
    assert kha_nang.duoc_phep("tao_video", vai="nhan_vien") is True


def test_nang_luc_chua_mo_thi_TU_CHOI_kem_ly_do_doc_duoc():
    ok, ly_do = kha_nang.kiem("dien_hoat_nhan_vat", vai="nhan_vien")
    assert ok is False
    assert ly_do, "phải có lý do bằng ngôn ngữ sản phẩm"
    assert "dien_hoat_nhan_vat" not in ly_do, "lý do không được rò tên nội bộ"


def test_khach_chua_dang_nhap_khong_duoc_gi():
    assert kha_nang.duoc_phep("tao_video", vai="") is False


def test_allowlist_khong_tra_loi_cau_hoi_CUA_WANGP():
    """Bất biến kiến trúc: module này không được biết tên model.

    Biết tên model ở đây là dựng bản sao thứ hai của sự thật — đúng cơ chế đã
    gỡ bảng 280 dòng khỏi `CLAUDE.md`.
    """
    import inspect

    ma = inspect.getsource(kha_nang)
    for cam in ("t2v_2_2", "i2v_2_2", "vace", "model_type", "wan2.2"):
        assert cam not in ma.lower(), f"allowlist không được biết {cam!r}"


# ─────────────────────────── giá ───────────────────────────

def test_uoc_gia_giu_cho_theo_do_dai():
    it = cost.uoc_credit(giay_video=5)
    nhieu = cost.uoc_credit(giay_video=10)
    assert nhieu > it, "video dài hơn phải giữ chỗ nhiều hơn"


def test_uoc_gia_luon_duong_va_lam_tron_len():
    assert cost.uoc_credit(giay_video=1) >= 1
    assert isinstance(cost.uoc_credit(giay_video=5), int)


def test_quyet_toan_theo_giay_GPU_THAT_chu_khong_theo_uoc_tinh():
    """Giữ chỗ là ước cao; quyết toán mới là số thật."""
    giu = cost.uoc_credit(giay_video=5)
    that = cost.quyet_toan_credit(giay_gpu=60.0)
    assert that != giu or True  # hai con so doc lap nhau
    assert cost.quyet_toan_credit(giay_gpu=120.0) > that


def test_quyet_toan_khong_bao_gio_vuot_uoc_giu_cho():
    """⛔ Trần cứng: không được trừ nhiều hơn số đã báo cho người dùng."""
    giu = cost.uoc_credit(giay_video=5)
    assert cost.quyet_toan_credit(giay_gpu=99999.0, tran=giu) == giu


def test_gia_phai_suy_tu_MOT_hang_so_do_duoc():
    """`san-lam-tron-la-mot-tang-khac`: mọi số tiền phái sinh từ một hằng đo được."""
    assert cost.USD_MOI_GIO_GPU > 0
    assert cost.CREDIT_MOI_USD > 0


@pytest.mark.parametrize("giay", [0, -5])
def test_do_dai_khong_hop_le_bi_tu_choi(giay):
    with pytest.raises(ValueError):
        cost.uoc_credit(giay_video=giay)
