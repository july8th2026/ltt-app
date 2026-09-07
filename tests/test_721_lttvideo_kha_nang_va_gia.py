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


def test_admin_duoc_dung_nang_luc_da_mo():
    assert kha_nang.duoc_phep("tao_video", vai="admin") is True


def test_vai_KHONG_CO_THAT_thi_bi_tu_choi():
    """🔴 `"nhan_vien"` từng nằm trong `VAI_DUOC_DUNG` nhưng **không tồn tại**:
    `User` chỉ có cột `role` với hai giá trị `admin`/`user`. Phép kiểm này chốt
    rằng từ vựng của app là từ vựng của nền tảng, không phải một bảng tự chế."""
    for vai in ("nhan_vien", "staff", "user"):
        assert kha_nang.duoc_phep("tao_video", vai=vai) is False


def test_nang_luc_chua_mo_thi_TU_CHOI_kem_ly_do_doc_duoc():
    ok, ly_do = kha_nang.kiem("dien_hoat_nhan_vat", vai="admin")
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


def test_quyet_toan_theo_SO_GIAY_DA_GIAO():
    """Giao gì trừ nấy — cùng một mức phẳng với lúc giữ chỗ."""
    assert cost.quyet_toan_credit(giay_video_giao=10.0) > cost.quyet_toan_credit(
        giay_video_giao=5.0
    )
    assert cost.quyet_toan_credit(giay_video_giao=5.0) == cost.uoc_credit(giay_video=5)


def test_khong_giao_duoc_gi_thi_KHONG_TRU_DONG_NAO():
    """⛔ Huỷ hoặc hỏng ⇒ 0. Không ai trả tiền cho một tệp không tồn tại."""
    assert cost.quyet_toan_credit(giay_video_giao=0) == 0


def test_quyet_toan_khong_bao_gio_vuot_uoc_giu_cho():
    """⛔ Trần cứng: không được trừ nhiều hơn số đã báo cho người dùng."""
    giu = cost.uoc_credit(giay_video=5)
    assert cost.quyet_toan_credit(giay_video_giao=99999.0, tran=giu) == giu


def test_gia_la_MOT_num_chinh_duoc_chu_khong_phai_mot_chuoi_phai_sinh():
    """🔴 Bản trước phái sinh giá qua BỐN phép nhân, mỗi phép một hằng số đo được.

    Chuỗi ấy chỉ đúng khi cả bốn còn đúng: đổi độ phân giải / số bước / profile
    là `GIAY_GPU_MOI_GIAY_VIDEO` sai ngay mà **không có gì đỏ lên**. Giai đoạn
    nội bộ dùng một mức phẳng, và phép kiểm này chốt rằng nó vẫn phẳng.
    """
    assert cost.CREDIT_MOI_GIAY_VIDEO > 0
    assert cost.uoc_credit(giay_video=7) == 7 * cost.CREDIT_MOI_GIAY_VIDEO
    # gia von van duoc ghi lai, nhung KHONG duoc tham gia vao gia ban
    assert not hasattr(cost, "HE_SO_BAN"), "hệ số bán quay lại ⇒ giá lại phái sinh"
    assert not hasattr(cost, "GIAY_GPU_MOI_GIAY_VIDEO"), "hằng số đã vô hiệu quay lại"


@pytest.mark.parametrize("giay", [0, -5])
def test_do_dai_khong_hop_le_bi_tu_choi(giay):
    with pytest.raises(ValueError):
        cost.uoc_credit(giay_video=giay)
