"""
test_839 — vòng nghiên cứu: KIỂM TRÍCH DẪN là bước quyết định. (H44 B6 bước 2)

Năm bước đầu của vòng (mục tiêu → kế hoạch → thu nguồn → trích → tổng hợp) ai
cũng nghĩ ra. Bước thứ sáu — **kiểm trích dẫn** — là bước phân biệt một sản phẩm
nghiên cứu với *"một cái máy nói linh tinh có tự tin"*.

🔴 Issue #1846 của `gpt-researcher` cho thấy nó hỏng thế nào: một nguồn không
   bao giờ được đọc ⇒ báo cáo kết thúc **không có trích dẫn kiểm được**. Báo cáo
   vẫn trôi chảy; không ai thấy gì sai.

⇒ Ở đây một khẳng định không phân giải được về nguồn đã thu thì **biến mất khỏi
  báo cáo**, và số bị loại được **nói ra**.

⛔ Không phép kiểm nào ở đây gọi model thật. `goi_model` được **tiêm vào**, nên
   ta chốt được cả những ca model cư xử tệ — bịa số nguồn, viết câu không nguồn
   — mà không phải chờ nó tệ thật.
"""
from __future__ import annotations

import pytest

from apps.chatltt.services import nghien_cuu as NC
from apps.chatltt.services.nguon import Nguon


def _n(chu: str, doan_id: str = "") -> Nguon:
    return Nguon(loai="doan_tai_lieu", chu=chu,
                 trich_dan={"doan_id": doan_id or chu[:8], "tep_id": "t1",
                            "trang": 1})


def _thu_co(*nguon):
    """Bộ thu trả về đúng những nguồn này ở lần gọi đầu, rồi rỗng."""
    hop = {"lan": 0}

    def thu(cau_hoi, so_toi_da):
        hop["lan"] += 1
        return list(nguon) if hop["lan"] == 1 else []
    return thu


def _model(*tra_loi):
    """Model giả: trả lần lượt các câu đã định."""
    hop = {"i": 0}

    def goi(nhac):
        i = hop["i"]
        hop["i"] += 1
        return tra_loi[i] if i < len(tra_loi) else ""
    return goi


# ── 1. Kiểm trích dẫn — phép kiểm quyết định ───────────────────────────────

def test_cau_TRO_VAO_NGUON_KHONG_TON_TAI_bi_loai():
    """🔴 Một khẳng định trỏ vào `[7]` khi chỉ có 3 nguồn là một khẳng định
    **bịa**. Nó phải biến mất, không phải được giữ kèm một cảnh báo nhỏ."""
    nguon = [_n("a"), _n("b"), _n("c")]
    kd, loai = NC.kiem_trich_dan("Cau that [2]\nCau bia [7]", nguon)
    assert [k.chu for k in kd] == ["Cau that"]
    assert loai == 1


def test_cau_KHONG_CO_trich_dan_nao_cung_bi_loai():
    """⛔ Nghe khắt khe, nhưng đó chính là lời hứa: sản phẩm này không viết câu
    nào nó không chỉ được nguồn."""
    kd, loai = NC.kiem_trich_dan("Duoi day la tong hop\nCau co nguon [1]",
                                 [_n("a")])
    assert [k.chu for k in kd] == ["Cau co nguon"]
    assert loai == 1


def test_trich_dan_PHAN_GIAI_ve_dung_nguon():
    nguon = [_n("nguon mot", "d1"), _n("nguon hai", "d2")]
    kd, _ = NC.kiem_trich_dan("Cau nay [2]", nguon)
    assert kd[0].nguon[0].trich_dan["doan_id"] == "d2"


def test_mot_cau_co_NHIEU_nguon():
    nguon = [_n("a", "d1"), _n("b", "d2"), _n("c", "d3")]
    kd, _ = NC.kiem_trich_dan("Cau tong hop [1][3]", nguon)
    assert [n.trich_dan["doan_id"] for n in kd[0].nguon] == ["d1", "d3"]


def test_so_nguon_bi_XOA_khoi_chu_hien_ra():
    """Người đọc thấy một câu sạch; nguồn đi kèm ở cấu trúc, không lẫn vào chữ."""
    kd, _ = NC.kiem_trich_dan("Dieu khoan la 30 ngay [1]", [_n("a")])
    assert kd[0].chu == "Dieu khoan la 30 ngay"
    assert "[1]" not in kd[0].chu


def test_tach_theo_DONG_khong_theo_dau_cham():
    """⭐ Model viết theo gạch đầu dòng, và một dấu chấm trong *"12,5 tr.đ"* hay
    *"tr. 7"* sẽ cắt giữa câu — rồi nửa sau mất trích dẫn và bị **loại oan**."""
    kd, loai = NC.kiem_trich_dan("- Chi phi la 12,5 tr.d moi thang [1]", [_n("a")])
    assert len(kd) == 1 and loai == 0
    assert "12,5 tr.d" in kd[0].chu


# ── 2. Kho rỗng thì KHÔNG gọi model ────────────────────────────────────────

def test_kho_RONG_thi_khong_goi_model_va_noi_ra():
    """⛔ Gọi model với không nguồn nào là mời nó viết một bài trôi chảy không
    trích dẫn — rồi `kiem_trich_dan` loại sạch, và ta đã tiêu tiền của khách cho
    một lượt **chắc chắn** ra rỗng."""
    da_goi = []

    def goi(nhac):
        da_goi.append(nhac)
        return "khong bao gio duoc goi"

    bc = NC.chay(cau_hoi="dieu khoan thanh toan",
                 thu=lambda q, n: [], goi_model=goi)
    assert bc.rong
    assert bc.ly_do_dung == "khong_co_nguon"
    assert da_goi == [], "da goi model du khong co nguon nao"


def test_kho_rong_KHONG_bia_ra_khang_dinh():
    bc = NC.chay(cau_hoi="x", thu=lambda q, n: [], goi_model=_model("bai viet troi chay"))
    assert bc.khang_dinh == []


# ── 3. Trần nói ra khi chạm ────────────────────────────────────────────────

def test_cham_TRAN_VONG_thi_noi_ra():
    """Chạm trần phải hiện trong báo cáo. Cắt im lặng là để khách trả tiền cho
    một câu trả lời thiếu mà tưởng là đủ."""
    def thu(q, n):
        return [_n(f"nguon {q}-{n}", f"d{len(q)}{n}")]

    bc = NC.chay(cau_hoi="x", thu=thu,
                 goi_model=_model("q1", "q2", "Ket qua [1]"),
                 tran_vong=2, tran_nguon=50)
    assert bc.ly_do_dung == "tran_vong"
    assert bc.so_vong == 2


def test_cham_TRAN_NGUON_thi_noi_ra():
    dem = {"i": 0}

    def thu(q, n):
        dem["i"] += 1
        return [_n(f"n{dem['i']}-{k}", f"d{dem['i']}-{k}") for k in range(n)]

    bc = NC.chay(cau_hoi="x", thu=thu,
                 goi_model=_model("q1", "q2", "Ket qua [1]"),
                 tran_vong=9, tran_nguon=6)
    assert bc.ly_do_dung == "tran_nguon"
    assert len(bc.nguon) <= 6


def test_ly_do_dung_nam_trong_ban_khai():
    """Bánh cóc: thêm một lý do mà quên khai ⇒ đỏ."""
    for ly_do in ("xong", "tran_vong", "tran_nguon", "khong_co_nguon"):
        assert ly_do in NC.LY_DO


# ── 4. Nguồn không trùng, và model không thấy id ───────────────────────────

def test_nguon_TRUNG_chi_gom_mot_lan():
    def thu(q, n):
        return [_n("cung mot doan", "d-trung")]

    bc = NC.chay(cau_hoi="x", thu=thu,
                 goi_model=_model("q1", "q2", "Ket qua [1]"), tran_vong=3)
    assert len(bc.nguon) == 1


def test_model_KHONG_nhin_thay_doan_id():
    """⛔ Model không nhìn thấy id thì không bịa được một id trông giống thật —
    thứ mà một phép kiểm chuỗi sẽ cho qua. Cùng luật `thi_hanh(boi_canh=…)`."""
    nhac_da_thay = []

    def goi(nhac):
        nhac_da_thay.append(nhac)
        return "Ket qua [1]"

    NC.chay(cau_hoi="x", thu=_thu_co(_n("noi dung that", "doan_bi_mat_123")),
            goi_model=goi, tran_vong=1)
    assert nhac_da_thay, "khong goi model lan nao"
    for nhac in nhac_da_thay:
        assert "doan_bi_mat_123" not in nhac
        assert "doan_id" not in nhac


def test_nguon_danh_so_TU_1_trong_nhac():
    nhac = []
    NC.chay(cau_hoi="x", thu=_thu_co(_n("dau tien"), _n("thu hai")),
            goi_model=lambda n: (nhac.append(n), "Ket qua [1]")[1], tran_vong=1)
    assert "[1] dau tien" in nhac[-1]
    assert "[2] thu hai" in nhac[-1]


# ── 5. Đường xuôi ──────────────────────────────────────────────────────────

def test_duong_xuoi_bao_cao_co_khang_dinh_va_nguon():
    """Đường xuôi THẬT: vòng 1 thu được, vòng 2 hết nguồn ⇒ `break` ⇒ `"xong"`.

    ⚠️ Bản đầu của phép kiểm này dùng `tran_vong=1` và đòi `"xong"`. Sai — với
       một vòng thì vòng lặp **chưa bao giờ hỏi lại** xem còn gì không, nên báo
       `"xong"` là khẳng định một sự đầy đủ chưa kiểm. `tran_vong` mới đúng.
    """
    bc = NC.chay(cau_hoi="dieu khoan thanh toan",
                 thu=_thu_co(_n("thanh toan 30 ngay", "d1")),
                 goi_model=_model("truy van hep hon", "Thoi han la 30 ngay [1]"),
                 tran_vong=3)
    assert bc.ly_do_dung == "xong"
    assert len(bc.khang_dinh) == 1
    assert bc.khang_dinh[0].nguon[0].trich_dan["doan_id"] == "d1"
    assert bc.so_bi_loai == 0


def test_MOT_vong_luon_bao_tran_vong_va_do_la_dung():
    """⭐ Một vòng không bao giờ kiểm được rằng còn hay hết. Nói `"xong"` ở đây
    là khẳng định một sự đầy đủ chưa ai kiểm."""
    bc = NC.chay(cau_hoi="x", thu=_thu_co(_n("a", "d1")),
                 goi_model=_model("Ket qua [1]"), tran_vong=1)
    assert bc.ly_do_dung == "tran_vong"
    assert len(bc.khang_dinh) == 1, "van phai co bao cao, chi la co canh bao"


def test_cau_hoi_rong_bi_tu_choi():
    with pytest.raises(NC.LoiNghienCuu):
        NC.chay(cau_hoi="   ", thu=lambda q, n: [], goi_model=_model())
