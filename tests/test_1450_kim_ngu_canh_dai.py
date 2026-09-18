"""test_1450 — bộ kim trong đống cỏ cho LTT-3.8 (llama.cpp #27756): đề, chấm, phân loại. Thuần, không mạng."""
from __future__ import annotations

from tools import kim_ngu_canh_dai as K


def test_de_giu_cong_thuc_issue_va_hai_ghi_chu_dung_vi_tri():
    de = K.dung_de(10, "m1")
    assert de.startswith("[probe m1]\n" + K.GHI_DAU)
    assert de.count(K.DOAN) == 10
    # ghi chú cuối nằm giữa hai nửa, câu hỏi ở cuối
    assert de.index(K.GHI_CUOI) == len("[probe m1]\n" + K.GHI_DAU + K.DOAN * 5)
    assert de.endswith(K.CAU_HOI)


def test_muoi_khac_nhau_thi_tien_to_khac_nhau():
    """Không lượt nào được hưởng cache tiền tố của lượt trước (issue loại nhiễm cache)."""
    assert K.dung_de(4, "a")[:12] != K.dung_de(4, "b")[:12]


def test_so_doan_suy_tu_token_that():
    assert K.so_doan_cho(100_000, 25.0, 100) == 3996
    assert K.so_doan_cho(50, 25.0, 100) == 0


def test_cham_dem_du_bon_su_kien():
    assert K.cham("northern ZEBRA-4711, southern falcon-8802; Marlene and Otto") == 4
    assert K.cham("ZEBRA-4711 only") == 1
    assert K.cham("") == 0


def test_dau_van_tay_eos_tuc_thi():
    """#27756: tokens_predicted=1, content rỗng, không có suy nghĩ ⇒ eos_tuc_thi (không phải 'hết token')."""
    assert K.phan_loai({"status": 200, "text": "", "reasoning": "", "token_ra": 1, "finish": "stop"}) == "eos_tuc_thi"


def test_nho_du_la_dat_nho_thieu_la_suy_giam():
    du = "ZEBRA-4711 FALCON-8802 Marlene Otto"
    assert K.phan_loai({"status": 200, "text": du, "token_ra": 300, "finish": "stop"}) == "dat"
    assert K.phan_loai({"status": 200, "text": "The codes are unclear.", "reasoning": "hmm",
                        "token_ra": 900, "finish": "stop"}) == "suy_giam"


def test_nghi_het_token_khong_bi_goi_la_eos():
    luot = {"status": 200, "text": "", "reasoning": "x" * 5000, "token_ra": 6000, "finish": "length"}
    assert K.phan_loai(luot) == "het_token"


def test_loi_http_khong_do_duoc():
    assert K.phan_loai({"status": 0}) == "khong_do_duoc"
    assert K.phan_loai({"status": 503}) == "khong_do_duoc"
