"""test_3602 — `tools/do_luong.py`: lớp đếm phải CHẶN được ba lỗi ngày 24/09.

⭐ ĐỐI CHỨNG, KHÔNG PHẢI "CHẠY ĐƯỢC LÀ XANH"

   Bài học `khong-doi-chung-thi-so-khong-khong-phai-phat-hien`: một phép kiểm
   nói *"cách mới không mắc lỗi"* mà **không tiêm lỗi vào** thì nó chưa chứng
   minh gì — nó chỉ chứng minh hôm nay không có lỗi nào để bắt.

   Nên mỗi lỗi ở đây có ĐÔI phép kiểm:

       `test_*_tiem_*`   tiêm ĐÚNG lỗi cũ  -> phải NỔ   (bánh cóc còn răng)
       `test_*_sach_*`   dữ liệu đúng      -> phải LẶNG (không báo động giả)

   Thiếu vế sau thì một hàm `raise` vô điều kiện cũng qua được cả bộ.

Ba lỗi được tiêm (nguyên văn brief 24/09):

   #1 gộp "lô HỎNG" với "model không nhắc = ĐẠT" ⇒ mẫu số 30 → 16
   #2 ghép theo `tu`/`n` trên dải RỜI RẠC        ⇒ mẫu số phồng
   #3 bench xin trần token 32 768, sản phẩm 16 384
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from tools.do_luong import (  # noqa: E402
    DINH_NGHIA,
    GopPhan,
    LechSanPham,
    LoiMauSo,
    MauSo,
    dong_thuan,
    kiem_tham_so,
    ma_tran_va_diem,
    so_hai_ti_le,
    ti_le_kem_ktc,
)

# ───────────────────────────────────────────────────────────────────────────
# LỖI #1 — hai loại vắng mặt gộp làm một ⇒ mẫu số 30 → 16
# ───────────────────────────────────────────────────────────────────────────

#: Dựng lại ĐÚNG hoàn cảnh đã đo 24/09: 30 mã hỏi, lô 200-209 chạy được nhưng
#: model không nhắc tới (⇒ ĐẠT), lô 220-229 model trả lời đủ, 10 mã còn lại đạt.
_MA_30 = [f"ma_{i:03d}" for i in range(200, 230)]


def _nhan_that() -> dict[str, bool | None]:
    """Nhãn ĐÚNG: model im lặng về 200-209 nghĩa là ĐẠT, không phải 'mất'."""
    nhan: dict[str, bool | None] = {}
    for i, m in enumerate(_MA_30):
        # 223-229 bị model báo sai (7 mã); 200-213 model IM LẶNG (⇒ đạt, 14 mã).
        nhan[m] = not (223 <= 200 + i < 230)
    return nhan


def test_3602_tiem_loi_1_hai_loai_vang_mat_gop_lam_mot():
    """Coi 'model không nhắc' là 'chưa hỏi' ⇒ mẫu số phải bị TỪ CHỐI."""
    nhan = _nhan_that()
    # ⛔ lỗi cũ: 14 mã model không nhắc tới bị đánh rơi khỏi kết quả.
    nhan_hong = {m: v for m, v in nhan.items() if not (200 <= int(m[3:]) < 214)}
    with pytest.raises(LoiMauSo, match="KHONG co nhan"):
        MauSo.tu_nhan(_MA_30, nhan_hong)


def test_3602_tiem_loi_1_mau_so_tut_thi_ti_le_nhay_23_len_44():
    """Chứng minh lỗi cũ ĐỔI CON SỐ — và cách mới giữ nguyên mẫu số 30.

    ⭐ Đây là vế "vì sao phải chặn": không phải vì xấu, mà vì nó làm tỉ lệ
    nhảy gần gấp đôi **mà không một phán quyết nào đổi**.
    """
    nhan = _nhan_that()
    dung = MauSo.tu_nhan(_MA_30, nhan)
    assert dung.n_do_duoc == 30, "mau so THAT phai la 30"
    assert len(dung.khong_dat) == 7  # 223..229

    # Cách CŨ: 14 mã im lặng bị coi là 'chưa trả lời' ⇒ mẫu số 16.
    mau_so_cu = 30 - 14
    assert mau_so_cu == 16
    ti_le_cu = len(dung.khong_dat) / mau_so_cu
    ti_le_moi = len(dung.khong_dat) / dung.n_do_duoc
    assert ti_le_moi < ti_le_cu, "loi cu PHAI thoi phong ti le"
    assert round(ti_le_moi, 3) == 0.233 and round(ti_le_cu, 3) == 0.438


def test_3602_sach_loi_1_lo_hong_that_van_ra_khoi_mau_so():
    """Lô HỎNG thật (`None`) vẫn phải ra khỏi mẫu số — và HIỆN RA, không giấu."""
    nhan = _nhan_that()
    nhan["ma_205"] = None  # lô này hỏng thật
    ms = MauSo.tu_nhan(_MA_30, nhan)
    assert ms.n_hoi == 30 and ms.n_do_duoc == 29
    assert len(ms.khong_do_duoc) == 1
    assert "KHONG DO DUOC=1" in str(ms), "mau so tut PHAI hien tren bao cao"


def test_3602_sach_loi_1_du_nhan_thi_khong_bao_dong_gia():
    ms = MauSo.tu_nhan(_MA_30, _nhan_that())
    assert ms.n_do_duoc == 30 and not ms.khong_do_duoc
    assert "KHONG DO DUOC" not in str(ms)


# ───────────────────────────────────────────────────────────────────────────
# LỖI #2 — ghép theo `tu`/`n` trên dải RỜI RẠC ⇒ mẫu số phồng
# ───────────────────────────────────────────────────────────────────────────

#: Dải RỜI RẠC — đúng hình dạng đã làm lỗi #2 nổ: mẫu ngẫu nhiên, không liền.
_DAI_ROI_RAC = [503, 509, 514, 519, 522, 530, 537, 542, 552, 556]


def test_3602_tiem_loi_2_sinh_ma_cua_dong_chua_he_hoi():
    """`range(tu, tu+n)` sinh mã chưa hỏi ⇒ phải bị TỪ CHỐI là 'mẫu số phồng'."""
    hoi = [f"flores_{d:04d}" for d in _DAI_ROI_RAC]
    nhan = {m: True for m in hoi}
    # ⛔ lỗi cũ: suy ra danh sách mã từ mốc đầu + số lượng.
    tu, n = _DAI_ROI_RAC[0], len(_DAI_ROI_RAC)
    nhan_phong = {f"flores_{d:04d}": True for d in range(tu, tu + n)}
    assert len(nhan_phong) == len(nhan), "hai ben cung SO LUONG — do la cai bay"
    assert set(nhan_phong) != set(nhan), "nhung KHAC TAP HOP"
    with pytest.raises(LoiMauSo, match="CHUA HE duoc hoi|KHONG co nhan"):
        MauSo.tu_nhan(hoi, nhan_phong)


def test_3602_tiem_loi_2_gop_phan_chong_ma():
    """Hai phần cùng khai một mã ⇒ mẫu số phồng, phải NỔ."""
    g = GopPhan().them("phan_0", MauSo.tu_nhan(["a", "b"], {"a": True, "b": False}))
    with pytest.raises(LoiMauSo, match="dung chung ma"):
        g.them("phan_1", MauSo.tu_nhan(["b", "c"], {"b": True, "c": True}))


def test_3602_tiem_loi_2_hop_cac_phan_khac_vu_tru():
    """Hợp các phần thiếu/thừa so với vũ trụ đã khai ⇒ phải NỔ."""
    g = GopPhan().them("phan_0", MauSo.tu_nhan(["a", "b"], {"a": True, "b": True}))
    with pytest.raises(LoiMauSo, match="khac vu tru"):
        g.tong(vu_tru=["a", "b", "c"])


def test_3602_sach_loi_2_dai_roi_rac_ghep_theo_ma_thi_dung():
    """Ghép theo MÃ thì dải rời rạc chạy đúng — không báo động giả."""
    hoi = [f"flores_{d:04d}" for d in _DAI_ROI_RAC]
    g = GopPhan()
    for i in range(0, len(hoi), 5):
        lat = hoi[i : i + 5]
        g.them(f"phan_{i//5}", MauSo.tu_nhan(lat, {m: (j % 2 == 0) for j, m in enumerate(lat)}))
    tong = g.tong(vu_tru=hoi)
    assert tong.n_hoi == 10 and tong.n_do_duoc == 10
    assert len(tong.khong_dat) == 4


# ───────────────────────────────────────────────────────────────────────────
# LỖI #3 — bench đo một thứ KHÔNG PHẢI sản phẩm
# ───────────────────────────────────────────────────────────────────────────

_TRAN_SAN_PHAM = 16_384


def test_3602_tiem_loi_3_tran_token_lech_san_pham():
    """32 768 ≠ 16 384 ⇒ bench đang đo một hệ thống khác, phải NỔ."""
    with pytest.raises(LechSanPham, match="max_tokens"):
        kiem_tham_so(
            {"max_tokens": 32_768, "temperature": 0.0},
            {"max_tokens": _TRAN_SAN_PHAM, "temperature": 0.0},
        )


def test_3602_tiem_loi_3_bench_khong_khai_tham_so():
    """Không khai một tham số sản phẩm ⇒ NỔ. Im lặng không phải là 'giống'."""
    with pytest.raises(LechSanPham, match="khong khai"):
        kiem_tham_so({"max_tokens": _TRAN_SAN_PHAM}, {"max_tokens": _TRAN_SAN_PHAM,
                                                      "temperature": 0.0})


def test_3602_sach_loi_3_dung_tham_so_san_pham_thi_lang():
    kiem_tham_so(
        {"max_tokens": _TRAN_SAN_PHAM, "temperature": 0.0},
        {"max_tokens": _TRAN_SAN_PHAM, "temperature": 0.0},
    )


# ───────────────────────────────────────────────────────────────────────────
# LỚP THỐNG KÊ — phải ủy cho thư viện, và ủy ĐÚNG
# ───────────────────────────────────────────────────────────────────────────


def test_3602_ktc_wilson_khong_sup_o_bien():
    """0/30 phải cho KTC có bề rộng > 0 — xấp xỉ chuẩn cho [0;0] ở đây."""
    d = ti_le_kem_ktc(0, 30)
    lo, hi = d["ktc"]
    assert lo == pytest.approx(0.0, abs=1e-9)
    assert hi > 0.10, "Wilson phai cho can tren khac 0 khi k=0"
    assert d["ti_le"] == 0.0


def test_3602_kappa_phat_hien_dong_thuan_gia_khi_lop_hiem():
    """⭐ Việc 1b: khớp thô THỔI PHỒNG đồng thuận khi lớp lỗi hiếm.

    Hai người đọc **bừa** trên nền 10 % lỗi vẫn khớp ~80 %. Kappa phải thấy
    xuyên qua chuyện đó; tỉ lệ khớp thô thì không.
    """
    # 100 mục, mỗi người đọc gắn cờ 10 mục — nhưng KHÔNG TRÙNG mục nào.
    a = [1] * 10 + [0] * 90
    b = [0] * 10 + [1] * 10 + [0] * 80
    kq = dong_thuan(a, b, lan_bootstrap=400)
    assert kq["khop_tho"]["ti_le"] == pytest.approx(0.80), "khop tho van 80 %"
    assert kq["kappa"] < 0.0, "kappa PHAI lo ra khong he co dong thuan"
    assert "yếu" in kq["doc_la"]


def test_3602_kappa_khop_hoan_toan_la_1():
    kq = dong_thuan([1, 0, 1, 0, 1, 0], [1, 0, 1, 0, 1, 0], lan_bootstrap=200)
    assert kq["kappa"] == pytest.approx(1.0)


def test_3602_ma_tran_uy_cho_sklearn_va_cong_dung_mau_so():
    """TP+FP+FN+TN phải bằng n — mẫu số không được rơi ở lớp thống kê."""
    that = [1, 1, 0, 0, 0, 1]
    du_doan = [1, 0, 1, 0, 0, 1]
    m = ma_tran_va_diem(that, du_doan)
    assert m["tp"] + m["fp"] + m["fn"] + m["tn"] == m["n"] == 6
    assert m["tp"] == 2 and m["fn"] == 1 and m["fp"] == 1 and m["tn"] == 2
    assert m["so_gan_co"] == 3 and m["so_loi_that"] == 3
    assert m["do_nhay"] == pytest.approx(2 / 3)
    assert m["do_chinh_xac"] == pytest.approx(2 / 3)


def test_3602_ma_tran_tu_choi_hai_vector_lech_dai():
    with pytest.raises(LoiMauSo, match="lech do dai"):
        ma_tran_va_diem([1, 0, 1], [1, 0])


def test_3602_fisher_khong_ket_luan_bua_tren_mau_nho():
    """13 vs 13 mục: chênh 77 % vs 62 % KHÔNG đủ để kết luận — p phải lớn."""
    f = so_hai_ti_le(10, 13, 8, 13)
    assert f["p"] > 0.2, "mau nho the nay khong duoc phep 'co y nghia'"


# ───────────────────────────────────────────────────────────────────────────
# BẢN THÂN BỘ ĐO — không được tự tính
# ───────────────────────────────────────────────────────────────────────────


def test_3602_dinh_nghia_long_dan_theo_dung_thu_tu():
    """Ba định nghĩa 'lỗi thật' phải là tập LỒNG NHAU, rộng dần."""
    chinh, rong, rong_nhat = (set(DINH_NGHIA[k]) for k in ("chinh", "rong", "rong_nhat"))
    assert chinh < rong < rong_nhat


def test_3602_khong_tu_cai_cong_thuc_thong_ke():
    """⛔ Bánh cóc: tệp `do_luong.py` không được tự cài lại phép thống kê.

    Luật 24/09 là *"nghiên cứu, tải về, dùng lại"*. Phép kiểm này đọc mã
    nguồn và đòi các tên thư viện phải CÓ MẶT — nếu ai đó thay
    `cohen_kappa_score` bằng một công thức viết tay, chỗ này đỏ.
    """
    ma = (pathlib.Path(__file__).resolve().parent.parent / "tools" / "do_luong.py").read_text(
        encoding="utf-8"
    )
    for ten in (
        "from sklearn.metrics import",
        "cohen_kappa_score",
        "confusion_matrix",
        "precision_recall_fscore_support",
        "binomtest",
        "fisher_exact",
    ):
        assert ten in ma, f"thieu {ten} — co ai do dang tu viet lai phep tinh"
    # ⛔ Dấu hiệu tự tính khoảng tin cậy bằng xấp xỉ chuẩn.
    assert "1.96" not in ma and "1,96" not in ma.replace("`p ± 1,96", "")


# ───────────────────────────────────────────────────────────────────────────
# LỚP PHÁN QUYẾT — "không đủ đỡ" ⛔ KHÔNG được lẫn với "sai"
# ───────────────────────────────────────────────────────────────────────────


def test_3602_phan_quyet_nguong_ktc_cat_thi_khong_du_do():
    """7/30 = 23,3 % vs cổng 15 %: KTC cắt ngưỡng ⇒ ⛔ chưa được tuyên TRƯỢT."""
    from tools.do_luong import CONG_BAO_DONG_GIA, _phan_quyet_nguong

    r = _phan_quyet_nguong("t", 7, 30, CONG_BAO_DONG_GIA, phai_duoi=True)
    assert r["ktc_cat_nguong"] is True
    assert r["phan_quyet"] == "KHÔNG ĐỦ ĐỠ"
    assert r["dung"] is False


def test_3602_phan_quyet_nguong_ktc_khong_cat_thi_dung():
    """33/100 vs cổng 15 %: KTC nằm trọn trên ngưỡng ⇒ TRƯỢT cổng, kết luận ĐỨNG."""
    from tools.do_luong import CONG_BAO_DONG_GIA, _phan_quyet_nguong

    r = _phan_quyet_nguong("t", 33, 100, CONG_BAO_DONG_GIA, phai_duoi=True)
    assert r["ktc_cat_nguong"] is False
    assert r["phan_quyet"] == "TRƯỢT cổng"


def test_3602_khang_dinh_tuong_duong_khong_bao_gio_duoc_tuyen_dung():
    """🔴 p = 1,0 trên hai tỉ lệ y hệt ⛔ KHÔNG chứng minh 'giống nhau'.

    Đây là bẫy `khong-doi-chung-thi-so-khong-khong-phai-phat-hien`: vắng bằng
    chứng về khác biệt ⛔ không phải bằng chứng về vắng khác biệt.
    """
    from tools.do_luong import _phan_quyet_so_doi

    r = _phan_quyet_so_doi("t", "fa_v1_dai_giu_rieng", "fa_v1_temp_mac_dinh",
                           tuong_duong=True)
    assert r["p"] == pytest.approx(1.0)
    assert r["phan_quyet"] == "KHÔNG ĐỦ ĐỠ", "p=1,0 KHONG duoc thanh 'DUNG'"
    assert r["be_rong_ktc_con_tron_duoc"] > 0.30, "phai khai mot khac biet lon van tron duoc"


def test_3602_ktc_chong_nhau_khong_phai_phep_kiem():
    """⭐ V1 vs V2: hai KTC CHỒNG nhau nhưng Fisher p < 0,05 ⇒ vẫn ĐỨNG.

    Chứng minh vì sao phán quyết lấy theo Fisher: "hai KTC chồng nhau" là một
    phép kiểm QUÁ DÈ DẶT, nó sẽ bắt ta vứt đi một khác biệt có thật.
    """
    from tools.do_luong import _phan_quyet_so_doi

    r = _phan_quyet_so_doi("t", "fa_v1_dai_giu_rieng", "fa_v2_dai_giu_rieng")
    assert r["ktc_chong_nhau"] is True
    assert r["p"] < 0.05
    assert r["phan_quyet"] == "ĐỨNG"


def test_3602_moi_so_quyet_dinh_deu_co_mau_so():
    """⛔ Bánh cóc: không con số quyết định nào được ghi dạng phần trăm trần."""
    from tools.do_luong import SO_DA_QUYET_DINH

    for ten, gia_tri in SO_DA_QUYET_DINH.items():
        k, n = gia_tri
        assert isinstance(k, int) and isinstance(n, int), f"{ten} phai la (k, n)"
        assert 0 <= k <= n and n > 0, f"{ten} co mau so vo nghia"


def test_3602_bang_quyet_dinh_chay_duoc_va_phu_ca_hai_ket_luan_chinh():
    from tools.do_luong import lenh_quyet_dinh

    rs = lenh_quyet_dinh()
    ten = " | ".join(r["ten"] for r in rs)
    assert "V3 TRƯỢT cổng 15 %" in ten and "V2 loại dứt khoát" in ten
    assert all(r["phan_quyet"] in {"ĐỨNG", "KHÔNG ĐỦ ĐỠ", "TRƯỢT cổng", "ĐẠT cổng"} for r in rs)
