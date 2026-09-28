"""N1 (B14 §3) — `tools/asv_so_ke_toan_cau.py`, lop TINH thuan.

Ba ca theo dung yeu cau cua brief: (1) ROI THAT — mot vai dong bi LOAI HAN
khoi ke hoach timing_align (khong phai gop); (2) CHI GOP KHE — content_process
-> voice_synthesis giam vi gop, KHONG duoc bao la roi; (3) GIAI DOAN CHUA CHAY
— outputs vang mat phai in `⛔ chưa có`, KHONG bao gio in `0`.

⛔ KHONG can CSDL: `so_ke_toan()`/`dinh_dang_bang()` la ham THUAN tren cac dict
`outputs` dung tay, dung khuon voi `tools/asv_doi_soat.py::doi_soat()`.
"""
from __future__ import annotations

from tools.asv_so_ke_toan_cau import (
    CONTENT_PROCESS,
    THIEU_GIAI_DOAN,
    TIMING_ALIGN,
    TRANSCRIBE,
    VOICE_SYNTHESIS,
    _hien_thi_so,
    dinh_dang_bang,
    so_ke_toan,
)


def _tt_tat_ca_xong(*ten_da_chay: str) -> dict[str, str | None]:
    """Trang thai `succeeded` cho moi ten trong `ten_da_chay`, `None` cho con lai."""
    ca_bon = (TRANSCRIBE, CONTENT_PROCESS, VOICE_SYNTHESIS, TIMING_ALIGN)
    return {t: ("succeeded" if t in ten_da_chay else None) for t in ca_bon}


def test_roi_that_o_timing_align_duoc_bao_dung_va_khong_lan_voi_gop():
    """content_process (10) -> voice_synthesis (10, khong gop) -> timing_align
    (7) — 3 dong bi LOAI HAN. `so_doan_bi_cat=3` khop TRON VEN voi 3 dong loai
    han (khong con dong nao bi cat-ve-0-ma-con-dong).
    """
    outs = {
        TRANSCRIBE: {"so_doan": 10},
        CONTENT_PROCESS: {"so_doan_goc": 10, "so_doan": 10},
        VOICE_SYNTHESIS: {"so_ma_noi_dung": 10, "so_doan": 10,
                          "so_khe_da_gop": 0, "so_doan_im_lang": 0},
        TIMING_ALIGN: {"so_doan": 7, "so_doan_bi_cat": 3},
    }
    tt = _tt_tat_ca_xong(TRANSCRIBE, CONTENT_PROCESS, VOICE_SYNTHESIS,
                         TIMING_ALIGN)

    ket = so_ke_toan(outs, tt)

    roi = [c for c in ket["chan_doan"] if c["loai"] == "roi_that"]
    assert len(roi) == 1, ket["chan_doan"]
    assert "RƠI 3 CÂU" in roi[0]["cau"]
    assert "content_process -> timing_align" == roi[0]["chang"]

    # `so_doan_bi_cat` khop tron ven voi so dong loai han => KHONG co dong nao
    # "cat-ve-0-ma-con-dong" o day.
    con_dong = [c for c in ket["chan_doan"] if c["loai"] == "con_dong_mat_tieng"]
    assert con_dong == [], ket["chan_doan"]
    doi_chieu_cat = [c for c in ket["chan_doan"]
                     if c["chang"] == "timing_align (so_doan_bi_cat đối chiếu)"]
    assert len(doi_chieu_cat) == 1
    assert doi_chieu_cat[0]["loai"] == "khop"

    # ⛔ Hien thi trong bang phai co dau hieu "RƠI" — dung dinh dang cua
    # `localize.py:114-172` ma brief yeu cau lay HINH DANG.
    bang = dinh_dang_bang(ket)
    assert "◄── RƠI 3 CÂU Ở ĐÂY" in bang
    assert "🔴 TÓM TẮT: 1 chặng RƠI THẬT." in bang


def test_chi_gop_khe_KHONG_duoc_bao_la_roi():
    """8 mã -> 5 khe do GOP (3 nhóm giảm 3 mã) — timing_align nổ lại đúng 8
    dòng. ⛔ Không được có bất kỳ dòng `loai == "roi_that"` nào ở đây: đây
    chính xác là ca `78 → 69` của brief (thu nhỏ để test rõ ràng).
    """
    outs = {
        TRANSCRIBE: {"so_doan": 8},
        CONTENT_PROCESS: {"so_doan_goc": 8, "so_doan": 8},
        VOICE_SYNTHESIS: {"so_ma_noi_dung": 8, "so_doan": 5,
                          "so_khe_da_gop": 3, "so_doan_im_lang": 0},
        TIMING_ALIGN: {"so_doan": 8, "so_doan_bi_cat": 0},
    }
    tt = _tt_tat_ca_xong(TRANSCRIBE, CONTENT_PROCESS, VOICE_SYNTHESIS,
                         TIMING_ALIGN)

    ket = so_ke_toan(outs, tt)

    roi = [c for c in ket["chan_doan"] if c["loai"] == "roi_that"]
    assert roi == [], ket["chan_doan"]

    gop = [c for c in ket["chan_doan"] if c["loai"] == "gop_khong_roi"]
    assert len(gop) == 1, ket["chan_doan"]
    assert "GỘP (không rơi thật): 8 → 5 khe, giảm 3 mã" in gop[0]["cau"]
    # so_khe_da_gop=3 khop dung hieu so (3 nhom deu 2 thanh vien).
    assert "khớp đúng hiệu số" in gop[0]["cau"]

    # timing_align no lai dung 8 dong => khop, khong roi.
    ta = [c for c in ket["chan_doan"] if c["chang"] == "content_process -> timing_align"]
    assert len(ta) == 1
    assert ta[0]["loai"] == "khop"

    bang = dinh_dang_bang(ket)
    assert "◄──" not in bang, bang  # ⛔ không dấu hiệu "rơi" nào trong bảng in
    assert "✅ TÓM TẮT: không chặng nào rơi thật" in bang


def test_gop_voi_nhom_lon_hon_2_khong_khop_so_khe_da_gop_nhung_van_KHONG_roi():
    """Mot nhom co 3 thanh vien: giam 2 mã nhưng `so_khe_da_gop` chỉ đếm 1
    NHÓM. Công cụ ⛔ không được suy hiệu số từ `so_khe_da_gop` (cảnh báo 1 của
    module) — vẫn phải báo GỘP, không phải rơi, và phải NÓI RÕ so_khe_da_gop
    không khớp hiệu số.
    """
    outs = {
        TRANSCRIBE: {"so_doan": 6},
        CONTENT_PROCESS: {"so_doan_goc": 6, "so_doan": 6},
        # 6 ma -> 4 khe: MOT nhom 3 thanh vien (giam 2) + 2 khe le, hoac tuong
        # duong — hieu so = 2 nhung chi 1 NHOM co >1 thanh vien.
        VOICE_SYNTHESIS: {"so_ma_noi_dung": 6, "so_doan": 4,
                          "so_khe_da_gop": 1, "so_doan_im_lang": 0},
        TIMING_ALIGN: {"so_doan": 6, "so_doan_bi_cat": 0},
    }
    tt = _tt_tat_ca_xong(TRANSCRIBE, CONTENT_PROCESS, VOICE_SYNTHESIS,
                         TIMING_ALIGN)

    ket = so_ke_toan(outs, tt)
    roi = [c for c in ket["chan_doan"] if c["loai"] == "roi_that"]
    assert roi == [], ket["chan_doan"]
    gop = [c for c in ket["chan_doan"] if c["loai"] == "gop_khong_roi"]
    assert len(gop) == 1
    assert "giảm 2 mã" in gop[0]["cau"]
    assert "KHÔNG nhất thiết bằng hiệu số" in gop[0]["cau"]


def test_giai_doan_chua_chay_in_chua_co_khong_bao_gio_in_khong():
    """content_process/voice_synthesis/timing_align CHƯA chạy (không có dòng
    `AsvStage`). Số phải hiện `⛔ chưa có`, TUYỆT ĐỐI không phải `"0"`.
    """
    outs = {
        TRANSCRIBE: {"so_doan": 5},
        CONTENT_PROCESS: {}, VOICE_SYNTHESIS: {}, TIMING_ALIGN: {},
    }
    tt = _tt_tat_ca_xong(TRANSCRIBE)  # chi transcribe da succeeded

    ket = so_ke_toan(outs, tt)

    hang_cp = next(h for h in ket["hang"] if h["giai_doan"] == CONTENT_PROCESS)
    assert hang_cp["so_doan"] is None
    assert hang_cp["ly_do"] == THIEU_GIAI_DOAN
    assert _hien_thi_so(hang_cp["so_doan"], hang_cp["ly_do"]) == (
        "⛔ chưa có (giai đoạn chưa chạy)")

    bang = dinh_dang_bang(ket)
    # ⛔ Không cứng khoảng trắng canh cột (định dạng `:<18` là chi tiết trình
    # bày) — chỉ chốt NỘI DUNG: dòng của content_process phải mang đúng nhãn.
    dong_cp = next(d for d in bang.splitlines() if d.startswith("content_process"))
    assert dong_cp.split("so_doan = ", 1)[1] == "⛔ chưa có (giai đoạn chưa chạy)"
    # Khong dong nao trong bang duoc phep bao "so_doan = 0" cho mot giai doan
    # chua chay — kiem tra tho: khong co chuoi "so_doan = 0" nao xuat hien vi
    # KHONG giai doan nao trong ca nay thuc su do duoc 0.
    assert "so_doan = 0" not in bang

    chua_du = [c for c in ket["chan_doan"] if c["loai"] == "chua_du_so"]
    assert len(chua_du) >= 1, ket["chan_doan"]


def test_thieu_khoa_khi_giai_doan_da_xong_phan_biet_voi_that_su_bang_khong():
    """`so_doan_im_lang=0` (đo được, bằng 0) và `so_doan_im_lang` VẮNG MẶT
    (chưa đo được) phải hiện KHÁC NHAU — đúng bài học "0 cần đối chứng" của
    kho này (`docs/.../khong-doi-chung-thi-so-khong-khong-phai-phat-hien.md`).
    """
    tt = _tt_tat_ca_xong(TRANSCRIBE, CONTENT_PROCESS, VOICE_SYNTHESIS,
                         TIMING_ALIGN)

    outs_bang_khong = {
        TRANSCRIBE: {"so_doan": 4},
        CONTENT_PROCESS: {"so_doan_goc": 4, "so_doan": 4},
        VOICE_SYNTHESIS: {"so_ma_noi_dung": 4, "so_doan": 4,
                          "so_khe_da_gop": 0, "so_doan_im_lang": 0},
        TIMING_ALIGN: {"so_doan": 4, "so_doan_bi_cat": 0},
    }
    ket_bang_khong = so_ke_toan(outs_bang_khong, tt)
    hang_vs = next(h for h in ket_bang_khong["hang"]
                   if h["giai_doan"] == VOICE_SYNTHESIS)
    gt_im_lang, ly_do_im_lang = hang_vs["phu"]["so_doan_im_lang"]
    assert gt_im_lang == 0
    assert _hien_thi_so(gt_im_lang, ly_do_im_lang) == "0"

    outs_thieu_khoa = {
        TRANSCRIBE: {"so_doan": 4},
        CONTENT_PROCESS: {"so_doan_goc": 4, "so_doan": 4},
        # ⛔ thieu han khoa "so_doan_im_lang" du giai doan da succeeded.
        VOICE_SYNTHESIS: {"so_ma_noi_dung": 4, "so_doan": 4,
                          "so_khe_da_gop": 0},
        TIMING_ALIGN: {"so_doan": 4, "so_doan_bi_cat": 0},
    }
    ket_thieu = so_ke_toan(outs_thieu_khoa, tt)
    hang_vs2 = next(h for h in ket_thieu["hang"]
                    if h["giai_doan"] == VOICE_SYNTHESIS)
    gt2, ly_do2 = hang_vs2["phu"]["so_doan_im_lang"]
    assert gt2 is None
    assert _hien_thi_so(gt2, ly_do2).startswith("⛔ chưa có")
