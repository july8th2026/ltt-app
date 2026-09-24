"""V2 — lớp chấm ngữ nghĩa chuyển từ NHỊ PHÂN sang PHÂN MỨC MQM.

🔴 **Vì sao đổi:** đo 24/09 trên 100 cặp FLORES-200 zh→vi **do NGƯỜI dịch**, bộ
   chấm gán **45%** là *"dịch sai"* cho bản dịch chuyên nghiệp — gần trùng 46%
   mà nó gán cho lượt thật của ta. Đọc 122 lý do báo động giả: gần hết là lỗi
   **nhẹ** theo MQM (mất sắc thái, thiếu một bổ ngữ, thêm một chữ, thay tên
   riêng bằng đại từ). Lời nhắc cũ **không có ô để nói "nhẹ"** — chỉ có `false`.

⭐ Giao thức: **GEMBA-MQM** (arXiv 2310.13988), họ với AutoMQM (2308.07286) và
   xCOMET (2310.10482). ⛔ Lấy **đặc tả** (thang mức MQM là chuẩn công khai),
   ⛔ **không** chép lời văn — GEMBA là CC BY-SA 4.0, ShareAlike phủ cả mã.

Bảng ánh xạ + ngưỡng: `docs/auto_scan_video_final/B2_XAC_THUC_BO_CHAM.md` §8.
⛔ Không gọi máy B trong tệp này — mọi phép kiểm ở đây là TĨNH.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import qc_ai, sua_chua

#: Một cặp thật, đủ để mọi đoạn trích dưới đây có chỗ khớp vào.
GOC = "源 产量 增加 了 百分之 二十"
DICH = "Sản lượng tăng hai mươi phần trăm trong năm nay."
VAN_BAN = {"seg_0001": (GOC, DICH)}


def _doc(loi, ma="seg_0001"):
    return qc_ai.doc_ngu_nghia({"doan": {ma: {"loi": loi}}}, {ma}, VAN_BAN)[0]


# ══════════════════════════════════════════════════════════════════════════════
#  1. Bảng ánh xạ mức -> `dat` — viết TRƯỚC khi đo, ⛔ không chỉnh sau khi thấy số
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("muc,dat", [
    ("nghiem_trong", False),   # cản hiểu
    ("nang", False),           # phá mạch, vẫn hiểu được
    ("nhe", True),             # là lỗi thật, nhưng không cản hiểu
])
def test_bang_anh_xa_muc_sang_dat(muc, dat):
    """⛔ Bảng này là PHÁN QUYẾT của bản sửa V2. Đổi nó = đổi kết luận."""
    d = _doc([{"loai": "lat_nghia", "muc": muc, "doan": "tăng", "ly_do": "x"}])
    assert d["dat"] is dat
    assert d["muc"] == muc


def test_khong_loi_nao_thi_DAT_va_muc_RONG():
    d = _doc([])
    assert d["dat"] is True and d["muc"] == "" and d["loi"] == []


def test_MUC_KHONG_DAT_dung_bang_hai_muc_nang():
    """Chốt hằng số, để không ai lặng lẽ thêm `nhe` vào cho "an toàn"."""
    assert qc_ai.MUC_KHONG_DAT == {"nang", "nghiem_trong"}


# ══════════════════════════════════════════════════════════════════════════════
#  2. ⭐ Lỗi `nhe` phải được GHI LẠI — ⛔ không được vứt
# ══════════════════════════════════════════════════════════════════════════════

def test_loi_NHE_van_duoc_ghi_lai_du_KHONG_sinh_viec_sua():
    """🔴 Đây là chỗ dễ hỏng nhất của bản sửa này.

    Nếu `dat=false` chỉ khi có `nang`, mà `nhe` bị **bỏ đi**, thì ta vừa dựng
    lại đúng bẫy *"hai trạng thái gộp thành một giá trị"*: *"không có lỗi nào"*
    và *"chỉ có lỗi nhẹ"* lại rơi chung một ô — và ta mất đúng khả năng phân
    biệt mà bản sửa này sinh ra để có.
    """
    d = _doc([{"loai": "dien_dat", "muc": "nhe", "doan": "trong năm nay",
               "ly_do": "mất sắc thái"}])
    assert d["dat"] is True                  # ⛔ không sinh việc sửa
    assert d["muc"] == "nhe"                 # ...nhưng KHÔNG phải "sạch"
    assert len(d["loi"]) == 1                # ...và lỗi vẫn còn đó
    assert d["loi"][0]["ly_do"] == "mất sắc thái"


def test_SACH_va_CHI_CO_LOI_NHE_phan_biet_duoc_bang_muc():
    """Hai đoạn cùng `dat=True` nhưng là hai trạng thái khác nhau."""
    sach = _doc([])
    nhe = _doc([{"loai": "dien_dat", "muc": "nhe", "doan": "tăng"}])
    assert sach["dat"] == nhe["dat"] is True
    assert sach["muc"] != nhe["muc"]


def test_muc_nang_nhat_thang_khi_mot_doan_co_nhieu_loi():
    d = _doc([{"loai": "dien_dat", "muc": "nhe", "doan": "tăng"},
              {"loai": "lat_nghia", "muc": "nang", "doan": "hai mươi"}])
    assert d["muc"] == "nang" and d["dat"] is False
    assert len(d["loi"]) == 2, "lỗi nhẹ bị nuốt khi đứng cạnh một lỗi nặng"


# ══════════════════════════════════════════════════════════════════════════════
#  3. ⭐ Lọc CƠ HỌC: lỗi không trích được đoạn ⇒ LOẠI
# ══════════════════════════════════════════════════════════════════════════════

def test_loi_KHONG_trich_doan_bi_LOAI():
    """GEMBA-MQM/ESA đều bắt model chỉ ra đoạn; đó là thứ ghìm lỗi bịa.

    ⛔ Lọc bằng máy, không nhờ lời nhắc *"hãy chính xác"*.
    """
    assert _doc([{"loai": "lat_nghia", "muc": "nang", "doan": ""}])["dat"] is True
    assert _doc([{"loai": "lat_nghia", "muc": "nang"}])["dat"] is True


def test_loi_trich_doan_KHONG_CO_THAT_bi_LOAI():
    """Đoạn không nằm trong nguồn lẫn bản dịch = model bịa ra một đoạn."""
    d = _doc([{"loai": "lat_nghia", "muc": "nghiem_trong",
               "doan": "một câu không hề có trong hai bên"}])
    assert d["dat"] is True and d["loi"] == []


def test_doan_trich_tu_CAU_NGUON_van_duoc_NHAN():
    """⚠️ Lỗi *bỏ sót* trích đoạn ở **câu nguồn**, không ở bản dịch — đúng như ví
    dụ của GEMBA (`accuracy/omission - "the account holder"`).

    ⛔ Chỉ so với bản dịch sẽ loại sạch lỗi bỏ sót, tức đổi một thước quá tay
       lấy một thước MÙ ở đúng loại mà MetricX vốn mạnh (`L_DICH.md` §3).
    """
    d = _doc([{"loai": "bo_sot", "muc": "nang", "doan": "百分之"}])
    assert d["dat"] is False and d["muc"] == "nang"


def test_so_khop_doan_BO_QUA_khoang_trang_va_HOA_THUONG():
    d = _doc([{"loai": "lat_nghia", "muc": "nang", "doan": "  SẢN   lượng  "}])
    assert d["dat"] is False


# ══════════════════════════════════════════════════════════════════════════════
#  4. Mức đọc không được ⇒ `nhe` (mặc định KHÔNG tiêu tiền)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("tho,mong", [
    ("major", "nang"), ("minor", "nhe"), ("critical", "nghiem_trong"),
    ("NANG", "nang"), ("nghiem trong", "nghiem_trong"),
    ("linh tinh", "nhe"), (None, "nhe"), (7, "nhe"),
])
def test_muc_tho_chuan_hoa_va_mac_dinh_la_NHE(tho, mong):
    """⭐ Mặc định `nhe`, ⛔ không phải `nang`.

    Một mức đọc không được là một điều ta KHÔNG biết, và mặc định phải là cái
    **không tiêu tiền**. Mặc định `nang` sẽ biến mỗi lần model gõ sai một chữ
    thành một lần dịch lại có trả tiền — đúng hình dạng lỗi bản V1 mắc phải.
    """
    assert _doc([{"loai": "lat_nghia", "muc": tho, "doan": "tăng"}])["muc"] == mong


def test_loai_la_khac_khi_model_bia_mot_loai_moi():
    d = _doc([{"loai": "mot_loai_khong_co", "muc": "nang", "doan": "tăng"}])
    assert d["loi"][0]["loai"] == "khac" and d["dat"] is False


# ══════════════════════════════════════════════════════════════════════════════
#  5. ⛔ `do_tin` đã RA KHỎI lời nhắc ngữ nghĩa — và đừng thêm lại
# ══════════════════════════════════════════════════════════════════════════════

def test_loi_nhac_KHONG_con_hoi_do_tin():
    """🔴 arXiv 2603.25052: bắt model **vừa lập luận vừa tự khai độ tin** làm
    lệch hiệu chỉnh NẶNG THÊM — lời nhắc cũ đòi đúng hai thứ đó. Cộng 2605.12446
    và số của ta: 98,4% báo động giả có `do_tin >= 0,70`.

    ⛔ Đừng thêm lại "cho chắc".
    """
    he_thong = qc_ai.loi_nhac_ngu_nghia(
        [{"ma": "seg_0001", "goc": GOC, "chu": DICH}])[0]["content"]
    assert "do_tin" not in he_thong
    assert "muc" in he_thong and "doan" in he_thong


def test_phan_quyet_KHONG_con_truong_do_tin():
    assert "do_tin" not in _doc([])


def test_loi_nhac_neu_DU_ba_muc_va_neo_vao_HAU_QUA():
    he_thong = qc_ai.loi_nhac_ngu_nghia(
        [{"ma": "seg_0001", "goc": GOC, "chu": DICH}])[0]["content"]
    for m in qc_ai.MUC:
        assert m in he_thong, f"thiếu mức {m} trong lời nhắc"
    # Neo vao hau qua cho nguoi xem, khong vao mot thang truu tuong.
    assert "hieu SAI" in he_thong or "hiểu SAI" in he_thong


# ══════════════════════════════════════════════════════════════════════════════
#  6. Vòng sửa đọc MỨC, không đọc `do_tin`
# ══════════════════════════════════════════════════════════════════════════════

def test_vong_sua_CHI_dich_lai_khi_co_loi_NANG():
    nang = _doc([{"loai": "lat_nghia", "muc": "nang", "doan": "tăng"}])
    nhe = _doc([{"loai": "dien_dat", "muc": "nhe", "doan": "tăng"}])
    assert sua_chua.tu_qc_ngu_nghia([nang])
    assert sua_chua.tu_qc_ngu_nghia([nhe]) == []


def test_khiem_khuyet_co_MUC_thi_dang_tin_theo_MUC_khong_theo_do_tin():
    """⛔ `do_tin` mặc định của `KhiemKhuyet` là 1.0; nếu `dang_tin` vẫn đọc nó
    thì một khiếm khuyết mức `nhe` sẽ lọt qua cổng mà không ai thấy."""
    k = sua_chua.KhiemKhuyet(sua_chua.DICH_SAI, ma="seg_0001", muc="nhe")
    assert k.do_tin == 1.0 and k.dang_tin is False
    assert sua_chua.KhiemKhuyet(sua_chua.DICH_SAI, ma="x", muc="nang").dang_tin


def test_KHONG_khai_muc_thi_VAN_di_theo_do_tin_cho_lop_HINH():
    """Lớp hình vẫn hỏi `do_tin` ⇒ nhánh cũ phải giữ nguyên hành vi."""
    thap = sua_chua.KhiemKhuyet(sua_chua.CAT_SAI, ma="canh_0001", do_tin=0.5)
    cao = sua_chua.KhiemKhuyet(sua_chua.CAT_SAI, ma="canh_0001", do_tin=0.9)
    assert thap.dang_tin is False and cao.dang_tin is True


def test_loi_NHE_van_vao_bang_chung_cua_khiem_khuyet_NANG():
    d = _doc([{"loai": "dien_dat", "muc": "nhe", "doan": "trong năm nay"},
              {"loai": "lat_nghia", "muc": "nang", "doan": "tăng"}])
    k = sua_chua.tu_qc_ngu_nghia([d])[0]
    assert len(k.bang_chung["loi"]) == 2


def test_ly_do_gop_CHI_tu_cac_loi_da_sinh_ra_phan_quyet():
    d = _doc([{"loai": "dien_dat", "muc": "nhe", "doan": "trong năm nay",
               "ly_do": "chỉ là sắc thái"},
              {"loai": "lat_nghia", "muc": "nang", "doan": "tăng",
               "ly_do": "đảo nghĩa"}])
    assert "đảo nghĩa" in d["ly_do"] and "chỉ là sắc thái" not in d["ly_do"]


# ══════════════════════════════════════════════════════════════════════════════
#  7. V3 — sàn mức cho SAI THỰC THỂ (đo mới thêm, không phải linh cảm)
# ══════════════════════════════════════════════════════════════════════════════

def test_loi_nhac_NEU_SAN_MUC_cho_sai_thuc_the():
    """🔴 V2 (phân mức, chưa có luật này) tụt độ nhạy `sai_thuc_the` 100% → 40%.

    Soi ra: **9/9** ca bỏ sót đều là model **CÓ THẤY** lỗi và **CÓ** gọi đúng
    tên `sai_thuc_the` — rồi chấm `nhe`. ⇒ lỗi **xếp mức**, không phải lỗi phát
    hiện. Một con số hay một cái tên sai không làm câu khó hiểu; nó làm người
    xem **tin chắc một sự việc không có thật**.

    ⛔ Gỡ dòng này ra khỏi lời nhắc là trả bộ chấm về chỗ mù 60% lỗi thực thể.
    """
    he_thong = qc_ai.loi_nhac_ngu_nghia(
        [{"ma": "seg_0001", "goc": GOC, "chu": DICH}])[0]["content"]
    for tu in ("SO", "TEN RIENG", "DON VI", "NGAY THANG"):
        assert tu in he_thong, f"lời nhắc không nêu {tu}"
    assert "`nang`" in he_thong and "`nhe`" in he_thong
