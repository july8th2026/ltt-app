"""
test_804 — `apps/chatltt/services/thi_hanh.py`. (H44 P03)

Mệnh đề trung tâm: **lỗi là kết quả, không phải ngoại lệ.** `02_HOP_DONG.md` §1
có hai chuyển đổi `… -> TOOL_RESULT_READY` cho đúng các ca hỏng, và P01 nhóm N8
đã đo model xử lý được lỗi/từ chối đúng cách.
"""
from __future__ import annotations

import pytest

from apps.chatltt.services import chieu_tool as C
from apps.chatltt.services import thi_hanh as T

SCHEMA = {"type": "object",
          "properties": {"expression": {"type": "string"},
                         "so_luong": {"type": "integer"},
                         "don_vi": {"type": "string", "enum": ["c", "f"]}},
          "required": ["expression"]}


@pytest.fixture()
def cho_calc(monkeypatch):
    monkeypatch.setattr(C, "CHO_MODEL_GOI", ("calc_thu", "no_thu", "co_phi_thu"))
    monkeypatch.setitem(C.LOP_CUA, "calc_thu", C.READ_ONLY)
    monkeypatch.setitem(C.LOP_CUA, "no_thu", C.READ_ONLY)
    monkeypatch.setitem(C.LOP_CUA, "co_phi_thu", C.PAID)
    monkeypatch.setitem(T._SO_HANDLER, "calc_thu",
                        lambda db, u, ds: {"ket_qua": 36317933})
    monkeypatch.setitem(T._SO_HANDLER, "no_thu",
                        lambda db, u, ds: (_ for _ in ()).throw(ZeroDivisionError("chia 0")))
    monkeypatch.setitem(T._SO_HANDLER, "co_phi_thu", lambda db, u, ds: "khong duoc chay")
    yield


# ── Đường thành công ───────────────────────────────────────────────────────

def test_chay_duoc_thi_tra_ok(cho_calc):
    kq = T.thi_hanh(None, user_id="u1", ten="calc_thu",
                    doi_so={"expression": "8123*4471"}, schema=SCHEMA)
    assert kq.ok and kq.lop == C.READ_ONLY
    assert "36317933" in kq.cho_model()


# ── Bốn đường hỏng — TẤT CẢ đều trả KetQua, KHÔNG ném ──────────────────────

def test_ten_la_tra_ket_qua_chu_khong_nem(cho_calc):
    kq = T.thi_hanh(None, user_id="u1", ten="khong_ton_tai", doi_so={})
    assert kq.ok is False and kq.ma_loi == T.LOI_TEN_LA
    assert "khong_ton_tai" in kq.thong_diep


def test_thieu_tham_so_bat_buoc(cho_calc):
    kq = T.thi_hanh(None, user_id="u1", ten="calc_thu", doi_so={}, schema=SCHEMA)
    assert kq.ma_loi == T.LOI_DOI_SO
    assert "expression" in kq.thong_diep, "thong diep phai NOI RO thieu cai gi"


def test_handler_nem_thi_bat_va_tra_ket_qua(cho_calc):
    """⛔ Bắt rộng có chủ ý — nhưng KHÔNG nuốt: kiểu ngoại lệ phải đi vào thông điệp."""
    kq = T.thi_hanh(None, user_id="u1", ten="no_thu",
                    doi_so={"expression": "1/0"}, schema=SCHEMA)
    assert kq.ok is False and kq.ma_loi == T.LOI_HANDLER
    assert "ZeroDivisionError" in kq.thong_diep


def test_tool_co_phi_KHONG_chay_o_P03(cho_calc):
    """P03 chỉ tool miễn phí. Chạm `PAID` là dừng, không chạy handler."""
    kq = T.thi_hanh(None, user_id="u1", ten="co_phi_thu", doi_so={})
    assert kq.ok is False and kq.ma_loi == T.LOI_CAN_DUYET
    assert kq.lop == C.PAID


def test_co_phi_chay_duoc_khi_DA_DUYET(cho_calc):
    kq = T.thi_hanh(None, user_id="u1", ten="co_phi_thu", doi_so={},
                    cho_chay_co_phi=True)
    assert kq.ok is True


# ── Schema: kiểm theo hợp đồng ĐÃ ĐƯA cho model ────────────────────────────

def test_tham_so_ngoai_hop_dong_bi_tu_choi_VA_liet_ke_cai_duoc_phep(cho_calc):
    kq = T.thi_hanh(None, user_id="u1", ten="calc_thu",
                    doi_so={"expression": "1+1", "bia_ra": 1}, schema=SCHEMA)
    assert kq.ma_loi == T.LOI_DOI_SO
    assert "bia_ra" in kq.thong_diep and "expression" in kq.thong_diep


def test_enum_sai_thi_noi_ro_gia_tri_duoc_phep(cho_calc):
    kq = T.thi_hanh(None, user_id="u1", ten="calc_thu",
                    doi_so={"expression": "1", "don_vi": "k"}, schema=SCHEMA)
    assert kq.ma_loi == T.LOI_DOI_SO and "'c'" in kq.thong_diep


def test_kieu_sai_thi_noi_ro_kieu(cho_calc):
    kq = T.thi_hanh(None, user_id="u1", ten="calc_thu",
                    doi_so={"expression": "1", "so_luong": "ba"}, schema=SCHEMA)
    assert kq.ma_loi == T.LOI_DOI_SO and "so nguyen" in kq.thong_diep


def test_khong_co_schema_thi_khong_kiem(cho_calc):
    """Không schema ⇒ không bịa ra ràng buộc. Bịa là bắt lỗi model vì lỗi của ta."""
    kq = T.thi_hanh(None, user_id="u1", ten="calc_thu", doi_so={"gi_cung_duoc": 1})
    assert kq.ok is True


# ── Cắt bớt phải THẤY ĐƯỢC ─────────────────────────────────────────────────

def test_ket_qua_dai_bi_cat_VA_NOI_RA(monkeypatch, cho_calc):
    """⛔ `CLAUDE.md`: không cắt xén âm thầm. Cắt lặng lẽ thì model kết luận
    trên dữ liệu thiếu mà tưởng là đủ."""
    monkeypatch.setitem(T._SO_HANDLER, "calc_thu", lambda db, u, ds: "x" * 50_000)
    kq = T.thi_hanh(None, user_id="u1", ten="calc_thu",
                    doi_so={"expression": "1"}, schema=SCHEMA)
    chu = kq.cho_model()
    assert kq.ok is True
    assert len(chu) < 50_000
    assert "DA CAT" in chu, "phai noi ra viec cat, TRONG chuoi model doc"
    assert str(T.TRAN_KY_TU_KET_QUA) in chu


def test_ket_qua_ngan_khong_bi_dong_gi_them(cho_calc):
    kq = T.thi_hanh(None, user_id="u1", ten="calc_thu",
                    doi_so={"expression": "1"}, schema=SCHEMA)
    assert "DA CAT" not in kq.cho_model()


# ── Hình dạng chuỗi trả về model ───────────────────────────────────────────

def test_loi_mang_MA_de_model_quyet_dinh_bang_ma_khong_bang_cau_chu(cho_calc):
    kq = T.thi_hanh(None, user_id="u1", ten="khong_ton_tai", doi_so={})
    assert kq.cho_model().startswith(f"LOI[{T.LOI_TEN_LA}]")


def test_tom_tat_ngan_va_mot_dong(monkeypatch, cho_calc):
    """⚠️ `monkeypatch.setitem`, KHÔNG gán thẳng vào `T._SO_HANDLER`.

    Gán thẳng thì handler giả sống sót sang test sau — và triệu chứng sẽ là
    "chạy riêng xanh mà gate đỏ", đúng lớp lỗi kho này đã trả giá một lần
    (`test_631` ra đời vì `importlib.reload` trong `test_630` làm 16 phép kiểm
    đỏ ở **bảy tệp khác**).
    """
    dai = "d" * 500
    monkeypatch.setitem(T._SO_HANDLER, "calc_thu",
                        lambda db, u, ds: dai + "\n" + dai)
    kq = T.thi_hanh(None, user_id="u1", ten="calc_thu",
                    doi_so={"expression": "1"}, schema=SCHEMA)
    t = kq.tom_tat()
    assert len(t) <= 161 and "\n" not in t


def test_so_handler_KHONG_ro_ra_ngoai_test():
    """Chốt chính chuyện trên: sau mọi test ở tệp này, sổ handler phải sạch.

    ⭐ Đặt cuối tệp là có chủ ý — nó đọc trạng thái mà các test trên để lại.
       Với `-p no:randomly` nó chạy cuối; với thứ tự ngẫu nhiên nó vẫn đúng, vì
       `monkeypatch` dọn sau **từng** test chứ không phải cuối tệp.
    """
    assert "calc_thu" not in T._SO_HANDLER
    assert "co_phi_thu" not in T._SO_HANDLER
