"""
Chọn giọng trong kho chung — bốn luật, và mỗi luật là một cách mất tiền.

🔴 Tính năng này **tiêu tiền của khách** (một lượt hỏi model = 1 credit, giá làm
   tròn lên) và **nói thay khách** (chọn giọng đọc câu trả lời của họ). Hai thứ
   đó cộng lại nghĩa là mọi đường hỏng ở đây đều có hậu quả thật, không có
   đường nào chỉ "hơi khó chịu".

⭐ Bốn luật, viết theo đúng thứ tự thiệt hại giảm dần:

     1. khách đã chọn giọng thì **không ai được đè lên** — mất quyền quyết định;
     2. hỏng thì vẫn phải đọc được — một tiện nghi chặn mất tính năng chính;
     3. model bịa tên giọng thì **không được dùng** — sai engine, không phải
        "một giọng khác";
     4. đã chọn rồi thì **không hỏi lại** — mỗi lần hỏi lại là 1 credit.

⛔ Cả bốn đều đo được mà **không cần model thật và không cần máy B**: đường gọi
   model được thay bằng một hàm giả. Một phép kiểm đòi GPU là một phép kiểm sẽ
   bị tắt.
"""
from __future__ import annotations

import pytest

from apps.chatltt.services import chon_giong as C


KHO = [
    {"value": "Minh Đức", "label": "Minh Đức (Nam · Miền Bắc · Tin tức)"},
    {"value": "Adam", "label": "Adam (Nam · Miền Nam · Tự nhiên)"},
    {"value": "Lan Anh", "label": "Lan Anh (Nữ · Miền Bắc · Kể chuyện)"},
]


@pytest.fixture()
def kho(monkeypatch):
    monkeypatch.setattr(C, "_kho_chung", lambda db, user_id: list(KHO))
    return KHO


def _dat_model(monkeypatch, tra):
    """Thay đường hỏi model bằng một câu trả lời dựng sẵn (hoặc một cú ném)."""
    goi = {"lan": 0}

    def gia(db, *, user_id, alias, trich):
        goi["lan"] += 1
        if isinstance(tra, BaseException):
            raise tra
        return tra

    monkeypatch.setattr(C, "_hoi_model", gia)
    return goi


# ── Luật 1: khách chọn rồi thì không ai đè lên ──────────────────────────────

@pytest.mark.parametrize("params", [
    {"text": "xin chao", "voice_id": "vc_" + "a" * 32},
    {"text": "xin chao", "preset": "Adam"},
])
def test_khach_da_chon_thi_khong_hoi_model(kho, monkeypatch, params):
    """⛔ Đây là luật đắt nhất: đè lên lựa chọn của người trả tiền.

    Và nó cũng là luật dễ vi phạm nhất, vì "tự động cho tiện" nghe như một cải
    tiến cho tới lúc nó đọc giọng nữ cho một khách đã cố ý chọn giọng nam.
    """
    from apps.chatltt.services import tao_media

    goi = _dat_model(monkeypatch, "Lan Anh")
    ra = tao_media._giong_cho_luot(object(), user_id="u1", conv_id="cv1",
                                   params=params)
    assert ra is None
    assert goi["lan"] == 0, "da hoi model du khach tu chon — vua de len vua ton tien"


# ── Luật 2: hỏng thì vẫn đọc được ───────────────────────────────────────────

@pytest.mark.parametrize("hong", [
    RuntimeError("may B sap"),
    None,          # `_hoi_model` tra None: model ban / tu choi / khong doc duoc
])
def test_chon_hong_thi_lui_ve_mac_dinh_chu_khong_nem(kho, monkeypatch, hong):
    """Không đường nào được ném ra ngoài — bên gọi là cửa báo giá của khách."""
    monkeypatch.setattr(C, "giong_da_dung", lambda db, **k: None)
    _dat_model(monkeypatch, hong)
    ra = C.chon(object(), user_id="u1", conv_id="cv1", text="mot cau nao do")
    assert ra["preset"] in {g["value"] for g in KHO}
    assert ra["nguon"] == "mac_dinh"
    assert ra["ton_credit"] == 0, "khong chon duoc thi khong duoc tinh tien"


def test_mac_dinh_lay_phan_tu_dau_cua_kho(kho):
    """Giọng lùi về = phần tử đầu, và **thứ tự do nguồn quyết**.

    🔴 Bản đầu của hạng mục này chốt "ưu tiên phong cách Tự nhiên" bằng cách dò
       chữ `"Tự nhiên"` trong `label`. `tools/check_i18n.py` kêu, và nó kêu đúng
       vào một khuyết tật thật: `label` đi qua `_()`, nên một bản dịch sang
       tiếng Anh sẽ làm phép so chuỗi trượt — giọng mặc định đổi **theo ngôn ngữ
       giao diện**, lặng lẽ.

    ⭐ Nên quyết định nằm ở DỮ LIỆU: `tham_chieu.tuy_chon_preset` xếp giọng
       trung tính lên đầu. `test_636` bên dưới chốt chính thứ tự đó.
    """
    assert C.mac_dinh(object(), "u1") == KHO[0]["value"]
    assert C.mac_dinh(object(), "u1") == "Minh Đức"


def test_kho_chung_xep_giong_trung_tinh_len_dau():
    """Nguồn phải xếp `tu_nhien` trước — đây là nửa kia của mệnh đề trên.

    ⛔ Không có phép kiểm này thì `mac_dinh()` vẫn "đúng" (nó lấy phần tử đầu)
       trong khi phần tử đầu là một giọng **bản tin** trang trọng. Một hàm đúng
       trên một danh sách sai vẫn cho ra một sản phẩm sai.
    """
    from apps.ltt_voice import tham_chieu

    ds = tham_chieu.tuy_chon_preset(None, "")
    assert ds, "kho giong chung rong"
    assert "Tự nhiên" in ds[0]["label"], ds[0]["label"]


# ── Luật 3: tên bịa thì không được dùng ─────────────────────────────────────

def test_model_bia_ten_thi_khong_dung(kho, monkeypatch):
    """Một `preset` không có thật đi thẳng vào `infer(voice=...)` của engine."""
    assert C.hop_le(object(), "u1", "Khong Co Thuc") is False
    assert C.hop_le(object(), "u1", "") is False
    assert C.hop_le(object(), "u1", "Adam") is True


def test_ten_dung_thi_nhan(kho, monkeypatch):
    monkeypatch.setattr(C, "giong_da_dung", lambda db, **k: None)
    _dat_model(monkeypatch, "Lan Anh")
    ra = C.chon(object(), user_id="u1", conv_id="cv1", text="ke mot cau chuyen")
    assert ra == {"preset": "Lan Anh", "nguon": "model", "ton_credit": 1}


# ── Luật 4: đã chọn rồi thì không hỏi lại (mỗi lần hỏi = 1 credit) ──────────

def test_da_co_giong_trong_hoi_thoai_thi_KHONG_hoi_model(kho, monkeypatch):
    """🔴 Đây là luật GIÁ, và nó là lý do tính năng này không nhân đôi hoá đơn.

    Đo 04/09: `gia_token.tinh()` làm tròn lên, nên một lượt hỏi 700 token vào /
    8 token ra vẫn tính tròn **1 credit** — bằng đúng giá một lượt đọc. Hỏi lại
    ở mỗi lần "Đọc to" là biến 1 credit thành 2, mãi mãi.
    """
    monkeypatch.setattr(C, "giong_da_dung", lambda db, **k: "Minh Đức")
    goi = _dat_model(monkeypatch, "Lan Anh")
    ra = C.chon(object(), user_id="u1", conv_id="cv1", text="bat ky")
    assert ra == {"preset": "Minh Đức", "nguon": "nho", "ton_credit": 0}
    assert goi["lan"] == 0, "da hoi model du hoi thoai da co giong — moi lan la 1 credit"


def test_khong_co_van_ban_thi_khong_hoi_model(kho, monkeypatch):
    """Không có gì để đọc thì không có gì để chọn — và không có gì để trả tiền."""
    monkeypatch.setattr(C, "giong_da_dung", lambda db, **k: None)
    goi = _dat_model(monkeypatch, "Lan Anh")
    ra = C.chon(object(), user_id="u1", conv_id="cv1", text="   ")
    assert ra["nguon"] == "mac_dinh" and ra["ton_credit"] == 0
    assert goi["lan"] == 0


def test_trich_bi_cat_truoc_khi_gui_len(kho, monkeypatch):
    """Trần trích là một chốt GIÁ: token vào quyết định tiền, và bài thì dài.

    ⛔ Không có trần này thì một câu trả lời 20.000 ký tự biến lượt "chọn giọng"
       1 credit thành một lượt vài credit — và khách không hề xin điều đó.
    """
    monkeypatch.setattr(C, "giong_da_dung", lambda db, **k: None)
    thay = {}

    def gia(db, *, user_id, alias, trich):
        thay["trich"] = trich
        return "Adam"

    monkeypatch.setattr(C, "_hoi_model", gia)
    C.chon(object(), user_id="u1", conv_id="cv1", text="x" * 5000)
    assert len(thay["trich"]) == C.TRICH_TOI_DA


def test_loi_nhac_mang_du_ca_ba_giong_va_ten_that(kho):
    """Model chỉ chọn được thứ nó nhìn thấy, và chỉ đúng nếu tên là tên thật."""
    nhac = C._loi_nhac(object(), "u1", "mot doan van")
    noi_dung = nhac[0]["content"]
    for g in KHO:
        assert g["value"] in noi_dung
        assert g["label"] in noi_dung
    assert "mot doan van" in noi_dung
