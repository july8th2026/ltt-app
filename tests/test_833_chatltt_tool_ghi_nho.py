"""
test_833 — tool `noi_bo.ghi_nho`: cửa thứ tư CÒN ĐÓNG, và đó là chủ ý. (H44 B4 bước 5)

## Phép kiểm quan trọng nhất ở đây chốt một thứ KHÔNG xảy ra

`noi_bo.ghi_nho` thuộc lớp `FREE` — không phiếu duyệt. Điều đó chỉ chấp nhận
được vì người dùng **sửa lại được**; mà *"sửa lại được"* đòi họ **nhìn thấy** nó
đã xảy ra. Khối `tool_call` hiện **chưa được vẽ gì cả** (đo ở P09).

⇒ Mở cửa thứ tư trước P09 là biến một hành động **ghi** thành một hành động
  **vô hình**. Nên `test_CHUA_mo_cua_thu_tu` chốt sự vắng mặt — và nó đi kèm
  một đối chứng dương (`noi_bo.tim_tai_lieu` **có** mặt), vì một phép kiểm chốt
  sự vắng mặt sẽ xanh cả khi `CHO_MODEL_GOI` rỗng sạch.

## Vì sao gọi thẳng handler thay vì qua `thi_hanh`

Chính vì cửa thứ tư đang đóng: `thi_hanh()` chặn ở bước 1 và không bao giờ tới
handler. Hành vi của handler vẫn phải được chốt **bây giờ** — ngày mở cửa,
người mở chỉ sửa một dòng trong `CHO_MODEL_GOI` và sẽ tin rằng phần còn lại đã
được canh.
"""
from __future__ import annotations

import pytest

CHU = "u-chu-that"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "t.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session
    from platform_core.registry import load_app_tables
    load_app_tables()
    Base.metadata.create_all(get_engine())
    gen = get_session()
    s = next(gen)
    yield s
    try:
        next(gen)
    except StopIteration:
        pass
    dbmod.reset_engine()


def _hoi_thoai(db, user_id: str) -> str:
    from apps.chatltt.tables import ChatlttConversation
    c = ChatlttConversation(user_id=user_id, title="t")
    db.add(c)
    db.flush()
    return c.id


def _muc_tool():
    from apps.chatltt.services import tool_noi_bo as T
    return [t for t in T.KHOI if t["function"]["name"] == T.TEN_GHI_NHO][0]


# ── 1. Cửa thứ tư ──────────────────────────────────────────────────────────

def test_CHUA_mo_cua_thu_tu():
    """🔴 Chốt một sự VẮNG MẶT — kèm đối chứng dương ngay dưới."""
    from apps.chatltt.services import chieu_tool, tool_noi_bo as T

    assert T.TEN_GHI_NHO not in chieu_tool.CHO_MODEL_GOI


def test_doi_chung_duong_tim_tai_lieu_VAN_o_trong_cua_bon():
    """Nếu `CHO_MODEL_GOI` rỗng thì phép kiểm trên xanh mà chẳng bảo vệ gì."""
    from apps.chatltt.services import chieu_tool, tool_noi_bo as T

    assert T.TEN_TIM_TAI_LIEU in chieu_tool.CHO_MODEL_GOI


def test_thi_hanh_tu_choi_vi_cua_bon_dong(db):
    """Cửa đóng phải chặn ở `thi_hanh`, không chỉ vắng mặt trong một hằng số."""
    from apps.chatltt.services import thi_hanh, tool_noi_bo as T

    kq = thi_hanh.thi_hanh(db, user_id=CHU, ten=T.TEN_GHI_NHO,
                           doi_so={"noi_dung": "x"},
                           boi_canh={"conversation_id": _hoi_thoai(db, CHU)})
    assert kq.ok is False
    assert kq.ma_loi == thi_hanh.LOI_TEN_LA


# ── 2. Lớp chính sách ──────────────────────────────────────────────────────

def test_lop_la_FREE_chu_khong_phai_READ_ONLY():
    """Nó **ghi**. `READ_ONLY` cho một tool ghi là khai sai bản chất, và lớp là
    thứ điều phối dùng để quyết định có cần phiếu duyệt hay không."""
    from apps.chatltt.services import chieu_tool, tool_noi_bo as T

    assert chieu_tool.lop_chinh_sach(T.TEN_GHI_NHO) == chieu_tool.FREE
    assert T.LOP[T.TEN_GHI_NHO] == "FREE"


def test_FREE_nghia_la_KHONG_can_duyet():
    from apps.chatltt.services import chieu_tool, tool_noi_bo as T

    assert chieu_tool.can_duyet(T.TEN_GHI_NHO) is False


# ── 3. Schema: model không có ĐỊA CHỈ ──────────────────────────────────────

def test_schema_khong_co_truong_dia_chi_nao():
    """⛔ `conversation_id`/`user_id`/`pham_vi`/`muc_tieu_id` **không** được
    xuất hiện. Một tham số do model kiểm soát không thể là ranh giới phạm vi —
    nội dung một tệp đính kèm điều khiển được nó."""
    truong = set(_muc_tool()["function"]["parameters"]["properties"])
    assert truong == {"noi_dung", "lau_dai"}


def test_schema_chi_bat_buoc_noi_dung():
    assert _muc_tool()["function"]["parameters"]["required"] == ["noi_dung"]


# ── 4. Hành vi handler ─────────────────────────────────────────────────────

def test_THIEU_boi_canh_thi_NEM_chu_khong_ghi_bua(db):
    """Fail-closed: mất phạm vi thì **không ghi**, chứ không ghi vào phạm vi rộng."""
    from apps.chatltt.services import tool_noi_bo as T

    with pytest.raises(T.ThieuPhamVi):
        T._h_ghi_nho(db, CHU, {"noi_dung": "abc"}, boi_canh={})


def test_noi_dung_rong_bi_tu_choi(db):
    from apps.chatltt.services import tool_noi_bo as T

    with pytest.raises(T.BieuThucSai):
        T._h_ghi_nho(db, CHU, {"noi_dung": "   "},
                     boi_canh={"conversation_id": _hoi_thoai(db, CHU)})


def test_mac_dinh_ghi_HEP_vao_dung_hoi_thoai_cua_boi_canh(db):
    from apps.chatltt.services import ghi_nho as G, tool_noi_bo as T

    cv = _hoi_thoai(db, CHU)
    khac = _hoi_thoai(db, CHU)
    kq = T._h_ghi_nho(db, CHU, {"noi_dung": "Dang ban ve hop dong 7"},
                      boi_canh={"conversation_id": cv})
    assert kq["pham_vi"] == G.HOI_THOAI
    assert G.liet_ke(db, user_id=CHU)[0].muc_tieu_id == cv
    assert "hop dong 7" not in G.khoi_ngu_canh(db, user_id=CHU, conv_id=khac)


def test_model_xin_lau_dai_ma_boi_canh_KHONG_cho_thi_bi_ha_va_NOI_RA(db):
    """🔴 Kết quả trả về model phải là `pham_vi` **THẬT**.

    Bị hạ trần mà vẫn báo *"đã nhớ lâu dài"* sẽ khiến model khẳng định với khách
    một điều không đúng — và khách chỉ phát hiện ở cuộc trò chuyện sau.
    """
    from apps.chatltt.services import ghi_nho as G, tool_noi_bo as T

    cv = _hoi_thoai(db, CHU)
    kq = T._h_ghi_nho(db, CHU, {"noi_dung": "Ten la Thang", "lau_dai": True},
                      boi_canh={"conversation_id": cv})
    assert kq["pham_vi"] == G.HOI_THOAI


def test_boi_canh_CHO_PHEP_thi_lau_dai_that(db):
    """Đối chứng dương: cùng lời gọi, bên gọi mở trần thì phạm vi rộng ra."""
    from apps.chatltt.services import ghi_nho as G, tool_noi_bo as T

    cv = _hoi_thoai(db, CHU)
    kq = T._h_ghi_nho(db, CHU, {"noi_dung": "Ten la Thang", "lau_dai": True},
                      boi_canh={"conversation_id": cv,
                                "cho_phep_ghi_nho_lau_dai": True})
    assert kq["pham_vi"] == G.NGUOI_DUNG


def test_ghi_lai_cung_dieu_thi_bao_bo_qua_chu_khong_hong(db):
    from apps.chatltt.services import tool_noi_bo as T

    cv = _hoi_thoai(db, CHU)
    doi_so = {"noi_dung": "Thich tra loi ngan gon"}
    a = T._h_ghi_nho(db, CHU, doi_so, boi_canh={"conversation_id": cv})
    b = T._h_ghi_nho(db, CHU, doi_so, boi_canh={"conversation_id": cv})
    assert (a["trang_thai"], b["trang_thai"]) == ("them", "bo_qua")


def test_nguon_luon_la_model_khong_the_gia_danh_nguoi(db):
    """Một mẩu model ghi mà khai là người ghi sẽ **khoá luôn quyền sửa của
    chính model** (xem `ghi_nho.thay`) và nói dối người dùng ở giao diện."""
    from apps.chatltt.services import ghi_nho as G, tool_noi_bo as T

    cv = _hoi_thoai(db, CHU)
    T._h_ghi_nho(db, CHU, {"noi_dung": "abc", "nguon": "nguoi"},
                 boi_canh={"conversation_id": cv})
    assert G.liet_ke(db, user_id=CHU)[0].nguon == G.MODEL


# ── 5. Mô tả gửi cho model ─────────────────────────────────────────────────

def test_mo_ta_noi_KHI_NAO_dung_va_khi_nao_KHONG():
    """P01 đo được model chọn tool rất sát mô tả. Một mô tả chỉ nói *"nó làm
    gì"* sẽ biến mọi lời tâm sự thành một mẩu ghi nhớ, và kho đầy sau ba cuộc
    trò chuyện — đúng ca `KhoDay` mà người dùng không hiểu vì sao."""
    mo_ta = _muc_tool()["function"]["description"]
    assert "CHI dung khi" in mo_ta
    assert "KHONG dung" in mo_ta
