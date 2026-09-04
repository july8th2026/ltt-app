"""
test_802 — `apps/chatltt/services/chieu_tool.py`: cổng thứ TƯ. (H44 P03)

Ba cổng đã có (`customer_visible` · `api_exposed` · `chinh_sach`) trả lời câu
*"ChatLTT MỜI người dùng năng lực nào"*. Cổng thứ tư trả lời câu khác hẳn:
**model được phép TỰ GỌI năng lực nào**.

⛔ Người dùng bấm nút tạo ảnh là một chuyện; model tự quyết tiêu 3–12 credit
   của họ là chuyện khác. Tệp này chốt rằng hai cổng đó **không được lẫn**.
"""
from __future__ import annotations

import pytest

from apps.chatltt.services import chieu_tool as C


class _NangLucGia:
    def __init__(self, ten, nhan="mo ta cho khach", schema=None,
                 san_sang="san_sang"):
        self.ten = ten
        self.nhan = nhan
        self.san_sang = san_sang
        self.hop_dong = {"input_schema": schema if schema is not None else {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"]}}


def _dat_danh_muc(monkeypatch, ds):
    from apps.chatltt.services import chinh_sach
    monkeypatch.setattr(chinh_sach, "danh_muc",
                        lambda db, *, user_id, apps=None: list(ds))


def _cho_phep(monkeypatch, *ten):
    monkeypatch.setattr(C, "CHO_MODEL_GOI", tuple(ten))


# ── Cổng thứ tư hẹp hơn cổng thứ ba ────────────────────────────────────────

def test_mac_dinh_MODEL_KHONG_duoc_tu_goi_gi(monkeypatch):
    """⭐ Làn A của P03 chạy tool giả/miễn phí trước (gói prompt nói vậy), nên
    mặc định rỗng là đúng — không phải thiếu sót."""
    _dat_danh_muc(monkeypatch, [_NangLucGia("image.ltt")])
    assert C.chieu(None, user_id="u1") == []


def test_nang_luc_duoc_MOI_nhung_khong_duoc_MODEL_GOI_thi_khong_chieu(monkeypatch):
    """🔴 Đây là mệnh đề trung tâm của tệp này."""
    _dat_danh_muc(monkeypatch, [_NangLucGia("image.ltt"), _NangLucGia("calculator")])
    _cho_phep(monkeypatch, "calculator")
    ten = [t["function"]["name"] for t in C.chieu(None, user_id="u1")]
    assert ten == ["calculator"], "image.ltt duoc MOI nhung KHONG cho model tu goi"


def test_kiem_cho_model_goi_nem_voi_ten_la(monkeypatch):
    _cho_phep(monkeypatch, "calculator")
    assert C.kiem_cho_model_goi("calculator") == "calculator"
    with pytest.raises(C.KhongChoModelGoi):
        C.kiem_cho_model_goi("destructive_action_fake")


# ── Lớp chính sách: mặc định NGẶT NHẤT ─────────────────────────────────────

def test_khong_khai_lop_thi_mac_dinh_DESTRUCTIVE():
    """🔴 Mặc định lỏng thì hậu quả là "tiêu tiền khách mà không hỏi" — và cái
    đó không sửa lại được sau khi đã xảy ra. Mặc định ngặt thì hậu quả là "đòi
    duyệt trong khi lẽ ra không cần" — phiền, sửa trong một dòng."""
    assert C.lop_chinh_sach("mot_tool_chua_ai_khai") == C.DESTRUCTIVE
    assert C.can_duyet("mot_tool_chua_ai_khai") is True


def test_lop_khai_tay_KHONG_suy_tu_ten():
    assert C.lop_chinh_sach("image.ltt") == C.PAID
    # Ten co chu "image" nhung chua khai => van la DESTRUCTIVE, khong phai PAID.
    assert C.lop_chinh_sach("image.xoa_het") == C.DESTRUCTIVE


def test_lop_mien_phi_khong_can_duyet():
    C.LOP_CUA["calculator"] = C.READ_ONLY
    try:
        assert C.can_duyet("calculator") is False
    finally:
        C.LOP_CUA.pop("calculator", None)


# ── Fail-closed ở từng lý do riêng ─────────────────────────────────────────

def test_khong_co_mo_ta_thi_KHONG_chieu(monkeypatch):
    """Model chọn tool bằng MÔ TẢ — P01 nhóm N3 cho thấy nó đọc rất sát.
    Một tool không mô tả là một tool sẽ bị chọn sai."""
    _dat_danh_muc(monkeypatch, [_NangLucGia("calculator", nhan="")])
    _cho_phep(monkeypatch, "calculator")
    assert C.chieu(None, user_id="u1") == []


def test_schema_khong_phai_object_thi_KHONG_chieu(monkeypatch):
    _dat_danh_muc(monkeypatch, [_NangLucGia("calculator", schema={"type": "string"})])
    _cho_phep(monkeypatch, "calculator")
    assert C.chieu(None, user_id="u1") == []


def test_nang_luc_KHONG_san_sang_thi_khong_chieu(monkeypatch):
    """Mời model gọi một thứ đang bận là tự tạo một lỗi lẽ ra không cần tồn tại."""
    _dat_danh_muc(monkeypatch, [_NangLucGia("calculator", san_sang="ban")])
    _cho_phep(monkeypatch, "calculator")
    assert C.chieu(None, user_id="u1") == []


# ── Hình dạng khối `tools` ─────────────────────────────────────────────────

def test_khuon_dung_openai(monkeypatch):
    _dat_danh_muc(monkeypatch, [_NangLucGia("calculator", nhan="Tinh bieu thuc.")])
    _cho_phep(monkeypatch, "calculator")
    t = C.chieu(None, user_id="u1")[0]
    assert t["type"] == "function"
    assert t["function"]["name"] == "calculator"
    assert t["function"]["description"] == "Tinh bieu thuc."
    assert t["function"]["parameters"]["type"] == "object"
    assert "expression" in t["function"]["parameters"]["properties"]


def test_lop_theo_ten_tra_dung_lop(monkeypatch):
    _dat_danh_muc(monkeypatch, [_NangLucGia("image.ltt"), _NangLucGia("la_hoac")])
    _cho_phep(monkeypatch, "image.ltt", "la_hoac")
    m = C.lop_theo_ten(C.chieu(None, user_id="u1"))
    assert m == {"image.ltt": C.PAID, "la_hoac": C.DESTRUCTIVE}


def test_rong_tra_ve_LIST_RONG_de_ben_goi_biet_dung_gui_khoa(monkeypatch):
    """⭐ Rỗng khác `[]` gửi lên: có khoá `tools` là **bật** cưỡng chế sinh bằng
    văn phạm GBNF (`01_M1_NATIVE_HAY_GENERIC.md` §5b). Bên gọi phải kiểm rỗng
    rồi mới đính — nên hàm này trả list rỗng chứ không trả `[{}]`."""
    _dat_danh_muc(monkeypatch, [])
    assert C.chieu(None, user_id="u1") == []
