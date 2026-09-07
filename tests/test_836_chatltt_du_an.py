"""
test_836 — dự án gom hội thoại: LẮP `app_projects`, và XOÁ KHÔNG ĐỐT. (H44 B5)

## Hai mệnh đề quyết định

1. **Xoá một dự án không được xoá hội thoại trong nó.** Người dùng nghĩ mình
   đang dọn một cái *nhãn*; nếu thao tác ấy đốt luôn nội dung thì không có cách
   nào lấy lại, và họ chỉ phát hiện **sau khi đã bấm**.
2. **Không có bộ đếm nào.** `LibreChat/chatProject.ts` mang `conversationCount`
   phi chuẩn hoá; ta cố ý không mượn phần ấy, và một bánh cóc AST giữ cho quyết
   định đó không bị ai lặng lẽ đảo lại vì *"cho nhanh"*.

## Cửa quyền kiểm CẢ HAI CHIỀU

Sở hữu hội thoại **và** sở hữu dự án. Kiểm một chiều là để hở chiều kia — đúng
ca `test_822` đã chốt cho `kho_tep`, và ở đây nó có hai chiều thật sự khác nhau
vì hai bảng có hai chủ được khai riêng.
"""
from __future__ import annotations

import ast
import pathlib
from datetime import datetime, timedelta, timezone

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
CHU = "u-chu-that"
NGUOI_KHAC = "u-nguoi-khac"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", "sqlite:///" + (tmp_path / "t.db").as_posix())
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LTT_CHATLTT_V3_MEMORY", raising=False)
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


def _tran(t: datetime) -> datetime:
    """Bỏ múi giờ để so được.

    ⚠️ SQLite **không giữ** `tzinfo`: ghi vào một `datetime` aware, đọc ra một
       `datetime` naive, và so hai thứ đó ném `TypeError`. Đây là khác biệt của
       ĐƯỜNG CHẠY TEST, không phải của mã — PostgreSQL giữ nguyên múi giờ.

    ⛔ Nên chuẩn hoá ở phép kiểm, **không** sửa mã sản phẩm cho vừa SQLite.
    """
    return t.replace(tzinfo=None) if t.tzinfo else t


def _hoi_thoai(db, user_id: str, tieu_de: str = "t") -> str:
    from apps.chatltt.tables import ChatlttConversation
    c = ChatlttConversation(user_id=user_id, title=tieu_de)
    db.add(c)
    db.flush()
    return c.id


# ── 1. Lược đồ: add-only ───────────────────────────────────────────────────

def test_project_id_NULLABLE_va_khong_co_mac_dinh():
    """🔴 220 hội thoại thật đang sống. Một cột `NOT NULL DEFAULT ''` biến dự án
    thành một tầng mọc thêm trên đầu mọi người — không ai xin điều đó."""
    from apps.chatltt.tables import ChatlttConversation as C

    cot = C.__table__.columns["project_id"]
    assert cot.nullable is True
    assert cot.server_default is None
    assert cot.default is None


def test_KHONG_co_khoa_ngoai_toi_app_projects():
    """⛔ `app_projects` là bảng của **nền tảng**, dùng chung mọi app. Một khoá
    ngoại từ bảng của một app trỏ vào đó buộc lõi phải biết ai đang bám vào nó —
    đúng thứ hợp đồng app sinh ra để tránh. Và `CASCADE` thì đốt nội dung."""
    from apps.chatltt.tables import ChatlttConversation as C

    assert list(C.__table__.columns["project_id"].foreign_keys) == []


# ── 2. Xoá KHÔNG đốt ───────────────────────────────────────────────────────

def test_xoa_du_an_thi_hoi_thoai_CON_NGUYEN(db):
    """🔴 PHÉP KIỂM QUYẾT ĐỊNH.

    Nó đọc lại hội thoại **từ CSDL** sau khi xoá dự án, chứ không chỉ kiểm
    `xoa()` trả `True` — một bản dùng `CASCADE` sẽ trả `True` y hệt.
    """
    from apps.chatltt.services import du_an as D
    from apps.chatltt.tables import ChatlttConversation

    da = D.tao(db, user_id=CHU, ten="Ke toan 2026")
    cv = _hoi_thoai(db, CHU, "hoi ve thue")
    assert D.gan(db, user_id=CHU, conv_id=cv, du_an_id=da.id) is True

    assert D.xoa(db, user_id=CHU, du_an_id=da.id) is True

    con = db.get(ChatlttConversation, cv)
    assert con is not None, "xoa du an da xoa luon hoi thoai"
    assert con.title == "hoi ve thue"
    assert con.project_id is None, "hoi thoai con tro vao mot du an da luu tru"


def test_hoi_thoai_mo_coi_van_liet_ke_duoc_o_danh_sach_chung(db):
    """⭐ Đối chứng cho phép kiểm trên: *"còn hàng trong bảng"* chưa đủ. Một hội
    thoại trỏ vào một dự án đã lưu trữ sẽ **không hiện ở đâu cả** — còn tệ hơn
    bị xoá, vì nó chiếm chỗ mà không ai thấy."""
    from apps.chatltt.services import du_an as D
    from apps.chatltt.services import hoi_thoai as H

    da = D.tao(db, user_id=CHU, ten="tam")
    cv = _hoi_thoai(db, CHU, "van con day")
    D.gan(db, user_id=CHU, conv_id=cv, du_an_id=da.id)
    D.xoa(db, user_id=CHU, du_an_id=da.id)

    ds = H.liet_ke(db, user_id=CHU) if hasattr(H, "liet_ke") else None
    if ds is not None:
        assert cv in [getattr(h, "id", None) for h in ds]


# ── 3. Cửa quyền — CẢ HAI CHIỀU ────────────────────────────────────────────

def test_khong_gan_duoc_vao_du_an_NGUOI_KHAC(db):
    from apps.chatltt.services import du_an as D

    cua_ho = D.tao(db, user_id=NGUOI_KHAC, ten="cua ho")
    cv = _hoi_thoai(db, CHU)
    assert D.gan(db, user_id=CHU, conv_id=cv, du_an_id=cua_ho.id) is False


def test_khong_gan_duoc_HOI_THOAI_cua_nguoi_khac(db):
    """Chiều thứ hai — kiểm một chiều là để hở chiều kia."""
    from apps.chatltt.services import du_an as D

    da = D.tao(db, user_id=CHU, ten="cua toi")
    cua_ho = _hoi_thoai(db, NGUOI_KHAC)
    assert D.gan(db, user_id=CHU, conv_id=cua_ho, du_an_id=da.id) is False


def test_doi_chung_duong_chu_thi_gan_duoc(db):
    """⛔ Thiếu vế này thì một `gan()` luôn trả `False` cũng qua sạch hai phép trên."""
    from apps.chatltt.services import du_an as D

    da = D.tao(db, user_id=CHU, ten="cua toi")
    cv = _hoi_thoai(db, CHU)
    assert D.gan(db, user_id=CHU, conv_id=cv, du_an_id=da.id) is True
    assert [h.id for h in D.hoi_thoai_cua(db, user_id=CHU, du_an_id=da.id)] == [cv]


def test_nguoi_la_KHONG_thay_hoi_thoai_trong_du_an(db):
    from apps.chatltt.services import du_an as D

    da = D.tao(db, user_id=CHU, ten="cua toi")
    D.gan(db, user_id=CHU, conv_id=_hoi_thoai(db, CHU), du_an_id=da.id)
    assert D.hoi_thoai_cua(db, user_id=NGUOI_KHAC, du_an_id=da.id) == []


def test_mot_KHONG_lo_du_an_co_ton_tai_hay_khong(db):
    """`None` cho cả *"không có"* lẫn *"không phải của bạn"* — cùng luật
    `kho_tep.mot` và `ghi_nho.mot`."""
    from apps.chatltt.services import du_an as D

    cua_ho = D.tao(db, user_id=NGUOI_KHAC, ten="x")
    assert D.mot(db, user_id=CHU, du_an_id=cua_ho.id) is None
    assert D.mot(db, user_id=CHU, du_an_id="khong-ton-tai") is None
    assert D.mot(db, user_id=NGUOI_KHAC, du_an_id=cua_ho.id) is not None  # doi chung


# ── 4. `updated_at` là mốc LẦN DÙNG ────────────────────────────────────────

def test_gan_hoi_thoai_CHAM_updated_at_cua_du_an(db):
    """⭐ Nếu chỉ đổi tên mới chạm mốc thì danh sách sắp theo *"lần sửa tên gần
    nhất"* — một thứ không ai quan tâm. Đây là chỗ thay cho `lastConversationAt`
    phi chuẩn hoá của LibreChat, dùng cột đã có."""
    from apps.chatltt.services import du_an as D

    da = D.tao(db, user_id=CHU, ten="x")
    cu = datetime.now(timezone.utc) - timedelta(days=3)
    da.updated_at = cu
    db.flush()

    D.gan(db, user_id=CHU, conv_id=_hoi_thoai(db, CHU), du_an_id=da.id)
    db.refresh(da)
    assert _tran(da.updated_at) > _tran(cu)


def test_go_hoi_thoai_cung_cham_updated_at(db):
    from apps.chatltt.services import du_an as D

    da = D.tao(db, user_id=CHU, ten="x")
    cv = _hoi_thoai(db, CHU)
    D.gan(db, user_id=CHU, conv_id=cv, du_an_id=da.id)
    cu = datetime.now(timezone.utc) - timedelta(days=3)
    da.updated_at = cu
    db.flush()

    assert D.go(db, user_id=CHU, conv_id=cv) is True
    db.refresh(da)
    assert _tran(da.updated_at) > _tran(cu)


def test_liet_ke_sap_theo_GAN_DUNG_NHAT_truoc(db):
    from apps.chatltt.services import du_an as D

    cu = D.tao(db, user_id=CHU, ten="cu")
    D.tao(db, user_id=CHU, ten="moi")
    cu.updated_at = datetime.now(timezone.utc) - timedelta(days=5)
    db.flush()
    assert [d.name for d in D.liet_ke(db, user_id=CHU)] == ["moi", "cu"]

    D.gan(db, user_id=CHU, conv_id=_hoi_thoai(db, CHU), du_an_id=cu.id)
    assert [d.name for d in D.liet_ke(db, user_id=CHU)] == ["cu", "moi"]


# ── 5. Nối vào đường tiêm ghi nhớ (B5 bước 4) ──────────────────────────────

def test_ghi_nho_pham_vi_DU_AN_vao_ngu_canh_khi_hoi_thoai_thuoc_du_an(db, monkeypatch):
    """Tầng `du_an` của `ghi_nho` có từ B4 bước 1 và chưa ai truyền id vào.
    Đây là phép kiểm cho sợi dây ấy."""
    from apps.chatltt.services import du_an as D
    from apps.chatltt.services import ghi_nho as G
    from apps.chatltt.services import luot as L

    monkeypatch.setenv("LTT_CHATLTT_V3_MEMORY", "1")
    da = D.tao(db, user_id=CHU, ten="Ke toan")
    cv = _hoi_thoai(db, CHU)
    D.gan(db, user_id=CHU, conv_id=cv, du_an_id=da.id)
    G.them(db, user_id=CHU, pham_vi=G.DU_AN, muc_tieu_id=da.id,
           noi_dung="Du an nay chi ban ve thue")

    khoi = L.khoi_ghi_nho_neu_bat(db, user_id=CHU, conv_id=cv)
    assert "chi ban ve thue" in khoi


def test_khong_ro_sang_hoi_thoai_o_du_an_KHAC(db, monkeypatch):
    from apps.chatltt.services import du_an as D
    from apps.chatltt.services import ghi_nho as G
    from apps.chatltt.services import luot as L

    monkeypatch.setenv("LTT_CHATLTT_V3_MEMORY", "1")
    a = D.tao(db, user_id=CHU, ten="A")
    b = D.tao(db, user_id=CHU, ten="B")
    cv_b = _hoi_thoai(db, CHU)
    D.gan(db, user_id=CHU, conv_id=cv_b, du_an_id=b.id)
    G.them(db, user_id=CHU, pham_vi=G.DU_AN, muc_tieu_id=a.id,
           noi_dung="Bi mat cua du an A")

    assert "du an A" not in L.khoi_ghi_nho_neu_bat(db, user_id=CHU, conv_id=cv_b)


def test_hoi_thoai_KHONG_thuoc_du_an_nao_van_chay_binh_thuong(db, monkeypatch):
    """Dự án là **tuỳ chọn**. Ca phổ biến nhất phải là ca rẻ nhất."""
    from apps.chatltt.services import ghi_nho as G
    from apps.chatltt.services import luot as L

    monkeypatch.setenv("LTT_CHATLTT_V3_MEMORY", "1")
    cv = _hoi_thoai(db, CHU)
    G.them(db, user_id=CHU, pham_vi=G.NGUOI_DUNG, noi_dung="Toi lam ke toan")
    assert "ke toan" in L.khoi_ghi_nho_neu_bat(db, user_id=CHU, conv_id=cv)


# ── 6. Bánh cóc: KHÔNG có bộ đếm ───────────────────────────────────────────

def test_KHONG_co_bo_dem_hoi_thoai_nao(db):
    """🔴 `LibreChat/chatProject.ts` mang `conversationCount` phi chuẩn hoá. Đó
    là nguồn chân lý **thứ hai** cho thứ `chatltt_conversation` đã biết, và
    `CLAUDE.md` viết thẳng: *"một giá trị chép lại là một giá trị sẽ trôi"* —
    sau khi một bảng chép tay nói sai **năm lần**, cả năm về phía nguy hiểm.

    ⭐ Chốt bằng AST chứ không bằng khớp chuỗi, và chốt trên **tên được gán**:
       một biến `so_hoi_thoai` xuất hiện là đủ để đỏ.
    """
    cay = ast.parse((GOC / "apps" / "chatltt" / "services" / "du_an.py")
                    .read_bytes().decode("utf-8"))
    ten = {n.id for n in ast.walk(cay) if isinstance(n, ast.Name)}
    ten |= {n.attr for n in ast.walk(cay) if isinstance(n, ast.Attribute)}
    for cam in ("so_hoi_thoai", "conversationCount", "dem_hoi_thoai",
                "last_conversation_at"):
        assert cam not in ten, f"bo dem phi chuan hoa da lot vao: {cam!r}"


def test_du_an_KHONG_co_truong_chi_dan_rieng():
    """⛔ Hai cơ chế cùng tiêm chữ vào system prompt là hai cơ chế sẽ lệch nhau,
    và người dùng sẽ có **hai** chỗ để sửa cùng một điều rồi sửa nhầm chỗ.

    ⭐ `chatltt_ghi_nho.pham_vi = "du_an"` đã có từ B4 bước 1. Phép đo đứng sau:
       `LibreChat/chatProject.ts` cũng không cho project một trường chỉ dẫn nào.
    """
    van = (GOC / "apps" / "chatltt" / "services" / "du_an.py"
           ).read_bytes().decode("utf-8")
    cay = ast.parse(van)
    hang = {k.value for n in ast.walk(cay) if isinstance(n, ast.Dict)
            for k in n.keys if isinstance(k, ast.Constant)}
    for cam in ("chi_dan", "instructions", "system_prompt"):
        assert cam not in hang


def test_app_slug_dong_o_MOT_cho(db):
    """Một chuỗi lặp ở mỗi nơi gọi là một chuỗi sẽ có chỗ gõ sai — và gõ sai nó
    nghĩa là đọc dự án của **app khác**."""
    from apps.chatltt.services import du_an as D

    assert D.APP == "chatltt"
    da = D.tao(db, user_id=CHU, ten="x")
    assert da.app_slug == "chatltt"


def test_du_an_cua_hoi_thoai_tra_CHUOI_RONG_khong_phai_None(db):
    """⭐ Nơi gọi là `ghi_nho.ap_dung(du_an_id=…)` và nó đã coi chuỗi rỗng là
    *"không có dự án"*. Một `None` bắt mọi nơi gọi tự quy đổi, và một chỗ quên
    quy đổi là một `WHERE muc_tieu_id = None` không khớp gì mà cũng không báo."""
    from apps.chatltt.services import du_an as D

    assert D.du_an_cua_hoi_thoai(db, user_id=CHU, conv_id=_hoi_thoai(db, CHU)) == ""
    assert D.du_an_cua_hoi_thoai(db, user_id=CHU, conv_id="khong-ton-tai") == ""
