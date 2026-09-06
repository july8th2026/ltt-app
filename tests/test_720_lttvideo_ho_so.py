"""Sổ đăng ký hồ sơ (profile) của `lttvideo`.

⛔ Đây **không** là một engine tham số mới. WanGP đã có định dạng settings; thứ
   duy nhất LTT thêm là **nguồn gốc**: bản nào được duyệt, neo vào SHA WanGP nào.
   Xem `docs/VIDEO_AI_V2/REUSE_DELETE_BUILD_MATRIX.md` §B4.
"""
from __future__ import annotations

import json

import pytest

from apps.lttvideo import ho_so


def test_moi_ho_so_deu_neo_vao_mot_sha_wangp():
    """🔴 Bất biến trung tâm: tham số chỉ có nghĩa với đúng engine sinh ra nó.

    Một `profile_id` không neo SHA là một `profile_id` sẽ sai thầm lặng vào ngày
    nâng phiên bản WanGP.
    """
    danh_sach = ho_so.liet_ke()
    assert danh_sach, "phải có ít nhất một hồ sơ đã duyệt"
    for h in danh_sach:
        assert len(h.wangp_sha) == 40, f"{h.profile_id}: SHA phải đủ 40 ký tự"
        assert h.wangp_sha.strip() == h.wangp_sha


def test_doc_duoc_tham_so_that_tu_tep_settings():
    h = ho_so.lay("ltt.video.chuan.v1")
    tham_so = h.doc_tham_so()
    assert tham_so["model_type"] == "t2v_2_2"
    # Con so cua chinh WanGP, bat duoc bang get_default_settings() o P01.
    assert tham_so["flow_shift"] == 12
    assert tham_so["guidance_phases"] == 2


def test_ho_so_khong_ton_tai_thi_bao_loi_ro_rang():
    with pytest.raises(ho_so.KhongCoHoSo):
        ho_so.lay("ltt.video.khong.co.that")


def test_tep_settings_phai_ton_tai_va_la_json_hop_le():
    for h in ho_so.liet_ke():
        assert h.duong_dan().is_file(), f"{h.profile_id}: thiếu tệp settings"
        json.loads(h.duong_dan().read_text(encoding="utf-8"))


def test_ap_dung_chi_de_len_dung_nhung_khoa_duoc_phep():
    """Người dùng chỉ đổi được một tập hẹp; phần còn lại là hồ sơ đã duyệt."""
    h = ho_so.lay("ltt.video.chuan.v1")
    ra = h.ap_dung({"prompt": "một dòng sông", "seed": 7, "video_length": "5s"})
    assert ra["prompt"] == "một dòng sông"
    assert ra["seed"] == 7
    assert ra["video_length"] == "5s"
    assert ra["flow_shift"] == 12, "khoá của hồ sơ không được đổi"


def test_khoa_ngoai_danh_sach_cho_phep_bi_TU_CHOI_chu_khong_bi_bo_qua():
    """⛔ Bỏ qua âm thầm là cách một tham số sai đi tới GPU mà không ai biết."""
    h = ho_so.lay("ltt.video.chuan.v1")
    with pytest.raises(ho_so.KhoaKhongDuocPhep):
        h.ap_dung({"prompt": "x", "flow_shift": 5})


def test_khong_ho_so_nao_bat_wangp_tu_chon_model():
    """`model_type` phải nằm trong hồ sơ — LTT chọn hồ sơ, không chọn model."""
    for h in ho_so.liet_ke():
        assert h.doc_tham_so().get("model_type"), f"{h.profile_id}: thiếu model_type"
