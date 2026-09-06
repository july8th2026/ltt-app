"""
test_820 — ĐIỀU KHOẢN CÔNG BỐ phải theo chính sách ĐANG CHẠY. (H44 R2b)

🔴 Vì sao tệp này tồn tại: ngày 06/09, C3 lên production và trang giá công khai
`/gia-api` **vẫn hứa điều cũ** trong quãng giữa hai lần deploy:

    gia_token.bang_gia()["toi_thieu_moi_luot_credit"]  =  0     (may doc: DUNG)
    /gia-api:  "toi thieu 1 credit. Nen mot luot rat nho tra
                nhieu hon gia niem yet"                        (NGUOI doc: SAI)

⛔ Và mục `lam_tron` trong `dieu_khoan.py` **tự khai** `do_bang:
   "gia_token.bang_gia toi_thieu_moi_luot_credit"` — tức nó nói mình là **dẫn
   xuất** trong khi nó là một **bản chép**. Đúng cơ chế đã hỏng năm lần ở bảng
   trong `CLAUDE.md`: *một giá trị chép lại là một giá trị sẽ trôi.*

⭐ Công bố một lời hứa không còn đúng **tệ hơn thu thừa**: thu thừa thì hoàn
   được, còn một lời hứa sai thì khách đã đọc và đã quyết định theo nó.

Ba nhóm mệnh đề:

  1. Điều khoản **đổi theo** chính sách — cả hai chiều, trong cùng một tiến trình.
  2. `MUC_DA_DO` **sống**, không đóng băng lúc import — vì đường lùi được thiết
     kế để bật giữa chừng, và nó phải kéo theo điều khoản.
  3. Hình dạng không đổi: mọi mục vẫn đủ khoá, vẫn có `do_bang`.
"""
from __future__ import annotations

import pytest

from platform_core.llm import gia_token, thanh_toan
from platform_core.public_api import dieu_khoan as dk


def _muc(khoa: str = "lam_tron") -> dict:
    ds = [m for m in dk.MUC_DA_DO if m["khoa"] == khoa]
    assert len(ds) == 1, f"phai co DUNG mot muc {khoa!r}, thay {len(ds)}"
    return ds[0]


@pytest.fixture()
def c1(monkeypatch):
    monkeypatch.setenv(thanh_toan.CO_SAN_MOI_LUOT, "1")


@pytest.fixture()
def c3(monkeypatch):
    monkeypatch.delenv(thanh_toan.CO_SAN_MOI_LUOT, raising=False)
    monkeypatch.delenv(thanh_toan.CO_TICH_LUY, raising=False)


# ── 1. Điều khoản đổi theo chính sách ──────────────────────────────────────

def test_C3_thi_dieu_khoan_KHONG_hua_san_1_credit(c3):
    """🔴 Mệnh đề trung tâm. Dưới C3 không có sàn, nên không được hứa có sàn."""
    m = _muc()
    assert gia_token.bang_gia()["toi_thieu_moi_luot_credit"] == 0
    assert "tối thiểu 1 credit" not in m["noi_dung"], (
        "dang cong bo mot loi hua khong con dung")
    assert "cộng dồn" in m["noi_dung"] or "giữ lại" in m["noi_dung"]


def test_C1_thi_dieu_khoan_VAN_hua_san_1_credit(c1):
    """Đường lùi phải kéo theo điều khoản, không chỉ kéo theo cách thu."""
    m = _muc()
    assert gia_token.bang_gia()["toi_thieu_moi_luot_credit"] == 1
    assert "tối thiểu 1 credit" in m["noi_dung"]


def test_HAI_CHINH_SACH_cho_HAI_cau_khac_nhau(c3, monkeypatch):
    """⭐ Đối chứng: nếu mục ấy là chuỗi cứng thì hai lần đọc giống hệt nhau, và
    phép kiểm trên vẫn xanh ở **một** trong hai chiều. Chỉ khi so **cả hai** mới
    phân biệt được *"dẫn xuất"* với *"tình cờ đúng"*."""
    a = _muc()["noi_dung"]
    monkeypatch.setenv(thanh_toan.CO_SAN_MOI_LUOT, "1")
    b = _muc()["noi_dung"]
    assert a != b, "dieu khoan KHONG doi theo chinh sach — no dang la ban CHEP"


# ── 2. `MUC_DA_DO` phải SỐNG ───────────────────────────────────────────────

def test_MUC_DA_DO_doc_lai_moi_lan_khong_dong_bang_luc_import(c3, monkeypatch):
    """⛔ Một tuple dựng lúc import giữ câu chữ của chính sách **lúc tiến trình
    khởi động**. Đường lùi `LTT_TINH_TIEN_SAN_MOI_LUOT` tồn tại đúng để bật
    giữa chừng trong một phút — nếu điều khoản không đi theo thì ta vừa mở lại
    khe vừa vá, chỉ khác chiều."""
    truoc = _muc()["tieu_de"]
    monkeypatch.setenv(thanh_toan.CO_SAN_MOI_LUOT, "1")
    assert _muc()["tieu_de"] != truoc, "MUC_DA_DO dong bang luc import"
    monkeypatch.delenv(thanh_toan.CO_SAN_MOI_LUOT)
    assert _muc()["tieu_de"] == truoc, "khong tro lai duoc trang thai ban dau"


def test_muc_lam_tron_van_tu_khai_phep_do_sinh_ra_no(c3):
    """`do_bang` là lời hứa *"tôi dẫn xuất từ đây"*. Giữ nó, và nay nó ĐÚNG."""
    assert _muc()["do_bang"] == "gia_token.bang_gia toi_thieu_moi_luot_credit"


# ── 3. Hình dạng không đổi ─────────────────────────────────────────────────

def test_moi_muc_van_du_khoa(c3):
    for m in dk.MUC_DA_DO:
        assert set(m) >= {"khoa", "tieu_de", "noi_dung", "do_bang"}, m.get("khoa")
        assert isinstance(m["noi_dung"], str) and m["noi_dung"].strip()


def test_khoa_khong_trung(c3):
    khoa = [m["khoa"] for m in dk.MUC_DA_DO]
    assert len(khoa) == len(set(khoa)), khoa


def test_thuoc_tinh_LA_van_nem_AttributeError():
    """`__getattr__` của module không được nuốt tên sai thành `None`."""
    with pytest.raises(AttributeError):
        dk.KHONG_CO_THUOC_TINH_NAY
