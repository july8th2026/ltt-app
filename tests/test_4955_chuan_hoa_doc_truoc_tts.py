"""N7 (V4_GIONG_AM.md hang N7) -- `apps/auto_scan_video/chuan_hoa_doc.py`,
lop TINH thuan, CHUA duoc noi vao duong san pham (xem docstring dau tep do).

Dai 4955-4956. Khong can khoa, khong can model: ham thuan tren str.
"""
from __future__ import annotations

from apps.auto_scan_video.chuan_hoa_doc import (
    NGUONG_HAN_LOT_TANG_TTS,
    TEN_PHEP_DAU_CAU_TRUNG,
    TEN_PHEP_HAN_LOT_TANG_TTS,
    TEN_PHEP_SO_DIEN_THOAI,
    TEN_PHEP_SO_LA_MA,
    chuan_hoa_dau_cau_trung,
    chuan_hoa_so_dien_thoai,
    chuan_hoa_so_la_ma,
    chuan_hoa_truoc_tts,
    phat_hien_han_lot_tang_tts,
)

# ============================================================================
# 1) SO LA MA -- phep chinh, port tts_chuan_hoa.py:86-100,126-130
# ============================================================================


def test_so_la_ma_the_ky_xxi_doc_dung():
    ket = chuan_hoa_so_la_ma("Thế kỷ XXI bắt đầu")
    assert ket.van_ban == "Thế kỷ hai mươi mốt bắt đầu"
    assert ket.phep_da_ap == [TEN_PHEP_SO_LA_MA]


def test_so_la_ma_chuong_iv():
    ket = chuan_hoa_so_la_ma("chương IV")
    assert ket.van_ban == "chương bốn"
    assert ket.phep_da_ap == [TEN_PHEP_SO_LA_MA]


def test_so_la_ma_hai_lan_trong_mot_cau_dem_dung_so_lan():
    ket = chuan_hoa_so_la_ma("Từ chương II đến chương IV")
    assert ket.van_ban == "Từ chương hai đến chương bốn"
    assert ket.phep_da_ap == [TEN_PHEP_SO_LA_MA, TEN_PHEP_SO_LA_MA]


def test_doi_chung_am_chu_i_dung_mot_minh_khong_doi():
    """Brief: 'I' dung mot minh (dai tu tieng Anh? mot muc danh sach?) ->
    KHONG duoc doi. Mau chi khop chuoi >=2 ky tu nen "I" don doc khong bao
    gio bi thay."""
    ket = chuan_hoa_so_la_ma("Đáp án là I.")
    assert ket.van_ban == "Đáp án là I."
    assert ket.phep_da_ap == []


def test_doi_chung_am_chuoi_la_ma_khong_hop_le_giu_nguyen():
    """'IIII' khong phai so La Ma hop le (dung chuan 'IV') -> giu nguyen."""
    ket = chuan_hoa_so_la_ma("mã lỗi IIII")
    assert ket.van_ban == "mã lỗi IIII"
    assert ket.phep_da_ap == []


def test_so_la_ma_khong_dung_sat_chu_co_dau_tieng_viet():
    """Tu-bien phai gom ca dai co dau (À-ỹ), khong chi ASCII \\w -- neu
    chuoi hoa I/V/X dinh lien vao mot chu co dau thi KHONG duoc tach ra doi."""
    ket = chuan_hoa_so_la_ma("XIín")
    # "XIín" khong tach duoc thanh "XI" + "ín" vi bien phai la chu co dau,
    # nen toan chuoi khong khop mau tu-bien -> giu nguyen.
    assert ket.van_ban == "XIín"
    assert ket.phep_da_ap == []


# ============================================================================
# 2) SO DIEN THOAI -- port tts_chuan_hoa.py:151-152
# ============================================================================


def test_so_dien_thoai_10_so_doc_tung_so():
    ket = chuan_hoa_so_dien_thoai("Gọi 0987654321 nhé")
    assert ket.van_ban == "Gọi không chín tám bảy sáu năm bốn ba hai một nhé"
    assert ket.phep_da_ap == [TEN_PHEP_SO_DIEN_THOAI]


def test_so_dien_thoai_khong_bat_dau_bang_0_khong_doi():
    ket = chuan_hoa_so_dien_thoai("mã đơn 1987654321")
    assert ket.van_ban == "mã đơn 1987654321"
    assert ket.phep_da_ap == []


# ============================================================================
# 3) DAU CAU TRUNG -- ta tu them
# ============================================================================


def test_dau_cau_trung_doi_sang_dau_viet():
    ket = chuan_hoa_dau_cau_trung("Xin chào，tôi khỏe。Bạn thế nào？")
    assert ket.van_ban == "Xin chào,tôi khỏe.Bạn thế nào?"
    assert ket.phep_da_ap == [
        TEN_PHEP_DAU_CAU_TRUNG,
        TEN_PHEP_DAU_CAU_TRUNG,
        TEN_PHEP_DAU_CAU_TRUNG,
    ]


def test_dau_cau_viet_binh_thuong_khong_doi():
    ket = chuan_hoa_dau_cau_trung("Xin chào, tôi khỏe. Bạn thế nào?")
    assert ket.van_ban == "Xin chào, tôi khỏe. Bạn thế nào?"
    assert ket.phep_da_ap == []


# ============================================================================
# 4) LUOI THU HAI CHO HAN LOT -- CHI PHAT HIEN, KHONG XOA (khac Viral)
# ============================================================================


def test_han_lot_vuot_nguong_duoc_gan_co_nhung_van_ban_khong_doi():
    """Cau toan chu Han (ty le 1.0 >= 0.35) -- PHAT HIEN nhung KHONG duoc
    xoa mot ky tu nao (khac hanh dong cua Viral, ho tra rong)."""
    goc = "这是一个测试句子"
    ket = phat_hien_han_lot_tang_tts(goc)
    assert ket.van_ban == goc, "khong duoc lam mat noi dung"
    assert ket.phep_da_ap == [TEN_PHEP_HAN_LOT_TANG_TTS]


def test_han_lot_duoi_nguong_khong_gan_co():
    """Mot cau Viet lan MOT chu Han duy nhat giua nhieu ky tu -> ty le << 0.35
    -> khong gan co (dung nguong lay nguyen tu Viral, khong phai '0 khoan
    dung')."""
    goc = "Hôm nay 好 trời đẹp quá, mọi người đi chơi nhé"
    ket = phat_hien_han_lot_tang_tts(goc)
    assert ket.van_ban == goc
    assert ket.phep_da_ap == []


def test_nguong_han_lot_dung_dung_gia_tri_viral():
    assert NGUONG_HAN_LOT_TANG_TTS == 0.35


# ============================================================================
# 5) HAM TONG -- chuan_hoa_truoc_tts, doi chung am bat buoc cua brief
# ============================================================================


def test_ham_tong_gop_ca_bon_phep():
    ket = chuan_hoa_truoc_tts("Thế kỷ XXI，gọi 0987654321！")
    assert ket.van_ban == "Thế kỷ hai mươi mốt,gọi không chín tám bảy sáu năm bốn ba hai một!"
    assert ket.phep_da_ap == [
        TEN_PHEP_DAU_CAU_TRUNG,
        TEN_PHEP_DAU_CAU_TRUNG,
        TEN_PHEP_SO_LA_MA,
        TEN_PHEP_SO_DIEN_THOAI,
    ]


def test_doi_chung_am_cau_toan_tieng_viet_danh_sach_phep_rong():
    """Brief: mot cau TOAN tieng Viet -> khong doi gi, va ham phai tra danh
    sach phep RONG."""
    goc = "Hôm nay trời đẹp quá, mọi người đi chơi nhé."
    ket = chuan_hoa_truoc_tts(goc)
    assert ket.van_ban == goc
    assert ket.phep_da_ap == []


def test_doi_chung_am_van_ban_da_sach_ra_y_het_dau_vao_tung_ky_tu():
    """Brief: van ban da sach -> ra Y HET dau vao, tung ky tu (khong chi
    "gan bang" -- phai == tuyet doi, va la object string co the khac nhau ve
    danh tinh nhung phai bang nhau ve gia tri)."""
    goc = "Không có số, không có ký tự lạ, không có gì để chuẩn hoá cả."
    ket = chuan_hoa_truoc_tts(goc)
    assert ket.van_ban == goc
    for i, (a, b) in enumerate(zip(ket.van_ban, goc, strict=True)):
        assert a == b, f"lech ky tu tai vi tri {i}: {a!r} != {b!r}"
    assert len(ket.van_ban) == len(goc)
    assert ket.phep_da_ap == []


def test_doi_chung_am_so_thuong_khong_thuoc_pham_vi_khong_bi_dung():
    """Brief: nam 2005 / 15% cung mot ho voi cac phep BO (da co tuong duong
    o text_pipeline.py) -- ham nay KHONG duoc dung vao, giu nguyen."""
    goc = "Năm 2005 có 15% dân số, giá 1.000.000đ giảm còn 500000 đồng"
    ket = chuan_hoa_truoc_tts(goc)
    assert ket.van_ban == goc
    assert ket.phep_da_ap == []


def test_khong_bao_gio_lam_mat_noi_dung_moi_ky_tu_goc_van_con_mat_trong_ket_qua():
    """Kiem tra 'khong mat noi dung' o muc THO: moi ky tu KHONG-PHAI-KHOANG-
    TRANG trong van ban goc (sau khi go bo cac ky tu dau cau Trung DA DUOC
    THAY the, vi day la doi-cach-viet duoc phep) van con mat trong tap ky tu
    ket qua -- khong co ky tu nao bi ruong bo thang."""
    goc = "Chương IV，gọi 0987654321"
    ket = chuan_hoa_truoc_tts(goc)
    # Dau cau Trung duoc THAY (khong xoa) nen so ky tu khong-khoang-trang
    # phai >= so ky tu khong-khoang-trang cua ban goc (so La Ma/SDT co the
    # NO ROI vi doi tu vai chu cai/so thanh nhieu chu).
    so_ky_tu_goc = sum(1 for c in goc if not c.isspace())
    so_ky_tu_ket_qua = sum(1 for c in ket.van_ban if not c.isspace())
    assert so_ky_tu_ket_qua >= so_ky_tu_goc
