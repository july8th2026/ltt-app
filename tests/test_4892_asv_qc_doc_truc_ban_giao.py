"""B9-4 — QC phải đo trên trục BẢN GIAO, ⛔ không trên trục GĐ1.

🔴 **Ca thật đã bắt được (T1a, 28/09, production `fd565a474551`).**

   Một lần chạy bật cùng lúc `cat_dau_cuoi` **và** phụ đề **và** `toc_do` giao
   một tệp **ĐÚNG** — `198,002 s`, phụ đề khớp từng dòng, ⛔ không dòng nào treo
   quá cuối — mà `qc_muc_hong = ["T2", "T15"]`.

       T2   mong_doi 220,007  =  275,008 / 1,25   ⛔ không trừ cửa sổ khách
       T15  3 dòng "ngoài biên" ở 209,79–219,84 s  ⛔ không qua bản đồ GĐ2

   Cả hai đọc **trục GĐ1** rồi so với một tệp đã qua **GĐ2**.

⭐ **Vì sao nó sống được tới giờ.** Nó chỉ nổ khi cửa sổ khách cắt **thật sự**
   một thứ gì đó. Mọi fixture trước đây hoặc ⛔ không đặt `cat`, hoặc đặt
   `[0,0 ; 1,0]` — cả hai cho bản đồ ĐỒNG NHẤT, và trên phép đồng nhất thì
   *"đọc trục GĐ1"* và *"đọc trục bản giao"* cho **cùng một số**.

   ⇒ Nên ba bài dưới đây đều **bắt buộc** cửa sổ phải cắt đi một phần khác 0.
      Một bài chốt trên cửa sổ đồng nhất là một bài **luôn xanh**.

🔑 Và mỗi bài đều có vế ĐỐI CHỨNG: sau khi chứng minh bản giao đúng thì QC
   phải XANH, bài còn tiêm một bản giao **sai** và đòi QC ĐỎ. Thiếu vế đó thì
   một hàm `return DAT` cũng qua được cả ba.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import qc
from apps.auto_scan_video.giai_doan_qc import _thoi_luong_mong_doi

#: Đúng số của T1a. Giữ nguyên chứ ⛔ không làm tròn cho đẹp: một hằng số tròn
#: trịa che mất việc phép tính có đi qua `round` nào không.
DAI_NGUON = 275.008
TOC = 1.25
CUA_SO = (0.05, 0.95)
#: `275,008 × 0,90 ÷ 1,25`. Đây là thứ khách nhận, đo bằng `ffprobe`.
DAI_GIAO = 198.006


def _ke_hoach(tong_giay: float = DAI_NGUON) -> dict:
    return {"tong_ms": int(round(tong_giay * 1000))}


def _ke_cat_khong_cat(tong_giay: float = DAI_NGUON) -> dict:
    """Kế cắt TỰ ĐỘNG ⛔ không cắt gì — đúng hình dạng của T1a.

    ⚠️ Đây là mấu chốt: `so_doan_cat = 0` nên bản đồ của kế cắt là phép **đồng
       nhất**. Ai đọc mình nó sẽ thấy `275,008` và tin rằng ⛔ không có phép cắt
       nào — trong khi cửa sổ khách cắt mất 10 %.
    """
    return {"phien_ban": 1, "tran_ti_le": 0.05, "thoi_luong": tong_giay,
            "cat": [], "giay_cat": 0, "ti_le_cat": 0.0, "bo_qua": []}


# ── T2 — thời lượng mong đợi phải biết cửa sổ khách ──────────────────────────

def test_T2_mong_doi_tru_cua_so_khach_chu_khong_chi_ke_cat():
    """Ca T1a: kế cắt ⛔ không cắt gì, cửa sổ khách cắt 10 %."""
    mong_doi = _thoi_luong_mong_doi(
        _ke_hoach(), _ke_cat_khong_cat(), {"toc_do": TOC},
        cua_so_khach=CUA_SO)
    assert mong_doi == pytest.approx(DAI_GIAO, abs=0.01), (
        "QC mong doi %.3f — cua so khach [0,05 ; 0,95] chua vao phep tinh. "
        "Doc mot minh ke cat TU DONG thi ra 220,007 = 275,008/1,25." % mong_doi)


def test_T2_khong_co_cua_so_thi_giu_nguyen_hanh_vi_cu():
    """⛔ Cửa sổ rỗng ⇒ kết quả phải y hệt trước B9 — ⛔ không được đổi."""
    assert _thoi_luong_mong_doi(
        _ke_hoach(), _ke_cat_khong_cat(), {"toc_do": TOC},
        cua_so_khach=None) == pytest.approx(DAI_NGUON / TOC, abs=0.01)


def test_T2_cua_so_dong_nhat_KHONG_phan_biet_duoc_hai_cach_doc():
    """🔑 Bài này chốt **giới hạn của chính bộ kiểm**, ⛔ không chốt sản phẩm.

    Trên cửa sổ `[0,0 ; 1,0]` hai cách đọc cho cùng một số. Ghi ra đây để lần
    sau ⛔ không ai viết một fixture như vậy rồi tưởng mình đã phủ.
    """
    dong_nhat = _thoi_luong_mong_doi(
        _ke_hoach(), _ke_cat_khong_cat(), {"toc_do": TOC},
        cua_so_khach=(0.0, 1.0))
    assert dong_nhat == pytest.approx(DAI_NGUON / TOC, abs=0.01)


# ── T15 — biên phụ đề phải đọc sự kiện ĐÃ đổi trục GĐ2 ───────────────────────

def _ban_hinh(su_kien: list[dict]) -> dict:
    return {"phu_de": {"che_do": "tu_dong", "kieu": "default",
                       "su_kien": su_kien},
            "bien_tap": {"toc_do": TOC}}


#: Khoảng GĐ2 thật sự giữ, đúng số của T1a: `275,008 × [0,05 ; 0,95]`.
KHOANG_GIU = [(13.7504, 261.2579)]


def _kiem(ban_hinh: dict, dai_ra: float = DAI_GIAO, *,
          khoang_giu=KHOANG_GIU) -> dict:
    """Chạy `qc.kiem` với vừa đủ đầu vào để T15 chạy, rồi trả mục T15."""
    bc = qc.kiem(
        tt_ra={"thoi_luong": dai_ra, "co_video": True, "co_tieng": True},
        tt_nguon={"thoi_luong": DAI_NGUON, "co_video": True, "co_tieng": True},
        am_luong={}, ke_hoach={"doan": [], "tong_ms": int(DAI_NGUON * 1000)},
        ban_ke_tieng={}, ban_hinh=ban_hinh,
        khoang_giu=khoang_giu, thoi_luong_vao=DAI_NGUON)
    return next(m for m in bc["muc"] if m["ma"] == "T15")


def test_T15_su_kien_bi_cua_so_khach_cat_thi_KHONG_con_ngoai_bien():
    """Ca T1a: dòng cuối nằm trong phần khách đã cắt ⇒ nó **biến mất**.

    ⛔ Nó ⛔ không phải "ngoài biên" — nó ⛔ không có mặt trong `.ass`.
    """
    # Sự kiện 77 ở 273,8–274,8 s trên trục GĐ1 ⇒ ngoài cửa sổ giữ, bị LOẠI.
    # Sự kiện 5 nằm trong cửa sổ ⇒ còn lại, và phải ĐẠT.
    m = _kiem(_ban_hinh([
        {"index": 5, "start": 20.0, "end": 24.0, "text": "trong cua so"},
        {"index": 77, "start": 273.838, "end": 274.798, "text": "Nhan qua lon."},
    ]))
    assert m["trang_thai"] == qc.DAT, (
        "T15 = %s — no dang doc su kien tren truc GD1. Su kien 273,8 s nam "
        "ngoai cua so khach [0,05 ; 0,95] nen ⛔ khong he duoc dot vao hinh."
        % m["trang_thai"])
    assert m["so_dong"] == 1 and m["so_bi_cat"] == 1


def test_T15_phu_de_roi_HET_vao_phan_cat_KHAC_voi_khong_dat_phu_de():
    """🔑 Hai tình huống ⛔ không được gộp thành một giá trị.

    Cả hai cho danh sách rỗng **sau** khi đổi trục, nhưng chúng nói hai điều
    khác hẳn nhau với người đọc báo cáo:

        ⛔ không đặt phụ đề     -> khách ⛔ không mua thứ đó
        rơi hết vào phần cắt   -> khách CÓ mua, và ⛔ không thấy dòng nào
    """
    khong_dat = _kiem(_ban_hinh([]))
    roi_het = _kiem(_ban_hinh([{"index": 77, "start": 273.838, "end": 274.798,
                                "text": "Nhan qua lon."}]))
    assert khong_dat["trang_thai"] == roi_het["trang_thai"] == qc.KHONG_AP_DUNG
    assert khong_dat.get("so_bi_cat") is None, (
        "'⛔ khong dat phu de' ⛔ khong duoc mang so_bi_cat")
    assert roi_het["so_bi_cat"] == 1 and roi_het["so_dong_goc"] == 1, (
        "'roi het vao phan cat' phai NOI RA con so, neu khong hai trang thai "
        "khac nhau doc len y het nhau")


def test_T15_van_DO_khi_su_kien_that_su_tran_qua_cuoi():
    """⭐ Đối chứng: ⛔ không có bài này thì `return DAT` cũng qua bài trên."""
    # Nằm TRONG cửa sổ giữ (13,75–261,26) nên ⛔ không bị loại; nhưng kéo dài
    # quá cuối bản ra sau khi đổi trục ⇒ phải ĐỎ.
    m = _kiem(_ban_hinh([{"index": 5, "start": 20.0, "end": 30.0,
                          "text": "binh thuong"}]),
              dai_ra=3.0)
    assert m["trang_thai"] == qc.HONG, (
        "T15 = %s — mot dong keo qua cuoi ban ra phai DO." % m["trang_thai"])
