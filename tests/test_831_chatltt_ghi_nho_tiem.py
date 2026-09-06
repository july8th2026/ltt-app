"""
test_831 — tiêm ghi nhớ vào ngữ cảnh: CỜ TẮT phải là KHÔNG ĐỔI MỘT BYTE.
(H44 B4 bước 3)

## Vì sao "cờ tắt" ở đây khắt khe hơn mọi cờ trước nó

`CO_TEP` gác một **cửa**: tắt nó thì một route trả 404 và phần còn lại của sản
phẩm y nguyên. `CO_GHI_NHO` gác **ngữ cảnh của mọi lượt** — kể cả lượt không
đính tệp, không gọi tool, không liên quan gì tới B4.

⇒ Phép kiểm không hỏi *"có tiêm không"* mà hỏi *"danh sách `messages` có **y
  hệt** bản chưa có B4 không"*. Một bản tiêm `{"role":"system","content":""}`
  khi cờ tắt sẽ trượt — và nó phải trượt: khối rỗng vẫn tốn token mỗi lượt và
  vẫn dạy model rằng nó có một kho để viện dẫn.

## Bánh cóc AST: hai nơi gọi, và nơi thứ ba chưa ra đời

`dung_ngu_canh` được gọi ở `luot.chay` và `luot_v3.chay_tiep`. Cả hai đã đi qua
`khoi_ghi_nho_neu_bat()`, tức đi qua cờ. Nơi gọi **thứ ba** sẽ xuất hiện (P09,
B6), và người thêm nó sẽ không đọc tệp này.

⇒ `test_moi_noi_goi_deu_di_qua_cua_co` đọc **AST của `apps/`** chứ không khớp
  chuỗi — cùng bài học đã trả giá ở `test_route_KHONG_chua_nghiep_vu`, nơi một
  bộ dò quét văn bản báo động trên chính đoạn văn giải thích nó.
"""
from __future__ import annotations

import ast
import pathlib

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


class _M:
    def __init__(self, role, blocks):
        self.role, self.blocks = role, blocks


def _duong():
    return [_M("user", [{"type": "text", "text": "chao"}])]


def _hoi_thoai(db, user_id: str) -> str:
    from apps.chatltt.tables import ChatlttConversation
    c = ChatlttConversation(user_id=user_id, title="t")
    db.add(c)
    db.flush()
    return c.id


def _co_mau(db, user_id: str, noi_dung: str = "Khach o Ha Noi"):
    from apps.chatltt.services import ghi_nho as g
    g.them(db, user_id=user_id, pham_vi=g.NGUOI_DUNG, noi_dung=noi_dung)


# ------------------------------------------------------------------ cờ tắt

def test_co_TAT_thi_ngu_canh_khong_doi_mot_byte(db, monkeypatch):
    """🔴 PHÉP KIỂM QUYẾT ĐỊNH của bước 3.

    So **bản dựng có mẩu trong kho** với **bản dựng khi kho trống**. Cờ tắt thì
    hai bản phải bằng nhau tuyệt đối — không phải "khác một khối rỗng".
    """
    from apps.chatltt.services import luot as L
    monkeypatch.delenv("LTT_CHATLTT_V3_MEMORY", raising=False)
    cv = _hoi_thoai(db, CHU)

    khi_trong = L.dung_ngu_canh(
        _duong(), khoi_ghi_nho=L.khoi_ghi_nho_neu_bat(db, user_id=CHU, conv_id=cv))
    _co_mau(db, CHU)
    khi_co_mau = L.dung_ngu_canh(
        _duong(), khoi_ghi_nho=L.khoi_ghi_nho_neu_bat(db, user_id=CHU, conv_id=cv))

    assert khi_co_mau == khi_trong
    assert not [t for t in khi_co_mau if t["role"] == "system"]


def test_co_TAT_thi_khoi_la_chuoi_rong_du_kho_co_mau(db, monkeypatch):
    from apps.chatltt.services import luot as L
    monkeypatch.delenv("LTT_CHATLTT_V3_MEMORY", raising=False)
    cv = _hoi_thoai(db, CHU)
    _co_mau(db, CHU)
    assert L.khoi_ghi_nho_neu_bat(db, user_id=CHU, conv_id=cv) == ""


# ------------------------------------------------------------------ cờ bật

def test_co_BAT_thi_mau_vao_ngu_canh(db, monkeypatch):
    """Đối chứng dương cho phép kiểm trên: cùng dữ liệu, cờ bật thì PHẢI thấy."""
    from apps.chatltt.services import luot as L
    monkeypatch.setenv("LTT_CHATLTT_V3_MEMORY", "1")
    cv = _hoi_thoai(db, CHU)
    _co_mau(db, CHU)

    tin = L.dung_ngu_canh(
        _duong(), khoi_ghi_nho=L.khoi_ghi_nho_neu_bat(db, user_id=CHU, conv_id=cv))
    assert tin[0]["role"] == "system"
    assert "Ha Noi" in tin[0]["content"]


def test_khoi_ghi_nho_dung_DAU_chu_khong_giua_dong(db, monkeypatch):
    """Bối cảnh bền đặt giữa dòng thì model đọc nó như một điều ai đó vừa nói."""
    from apps.chatltt.services import luot as L
    monkeypatch.setenv("LTT_CHATLTT_V3_MEMORY", "1")
    cv = _hoi_thoai(db, CHU)
    _co_mau(db, CHU)
    tin = L.dung_ngu_canh(
        _duong(), khoi_ghi_nho=L.khoi_ghi_nho_neu_bat(db, user_id=CHU, conv_id=cv))
    assert [t["role"] for t in tin] == ["system", "user"]


def test_co_BAT_ma_kho_TRONG_thi_van_khong_co_tin_system(db, monkeypatch):
    """Cờ bật không phải lý do để tiêm một khối rỗng."""
    from apps.chatltt.services import luot as L
    monkeypatch.setenv("LTT_CHATLTT_V3_MEMORY", "1")
    cv = _hoi_thoai(db, CHU)
    tin = L.dung_ngu_canh(
        _duong(), khoi_ghi_nho=L.khoi_ghi_nho_neu_bat(db, user_id=CHU, conv_id=cv))
    assert not [t for t in tin if t["role"] == "system"]


def test_ghi_nho_khong_ro_sang_nguoi_khac_qua_duong_tiem(db, monkeypatch):
    """Cửa quyền phải giữ **ở chính đường tiêm**, không chỉ ở `liet_ke`."""
    from apps.chatltt.services import luot as L
    monkeypatch.setenv("LTT_CHATLTT_V3_MEMORY", "1")
    _co_mau(db, CHU, "Bi mat cua chu")
    cv_ho = _hoi_thoai(db, NGUOI_KHAC)
    assert L.khoi_ghi_nho_neu_bat(db, user_id=NGUOI_KHAC, conv_id=cv_ho) == ""


# ------------------------------------------------------------- bánh cóc AST

def _cac_loi_goi_dung_ngu_canh() -> list:
    """Mọi lời gọi `dung_ngu_canh(...)` trong `apps/` — đọc AST, không khớp chuỗi."""
    ra = []
    for tep in sorted((GOC / "apps").rglob("*.py")):
        cay = ast.parse(tep.read_bytes().decode("utf-8"))
        for nut in ast.walk(cay):
            if not isinstance(nut, ast.Call):
                continue
            f = nut.func
            ten = (f.attr if isinstance(f, ast.Attribute)
                   else f.id if isinstance(f, ast.Name) else "")
            if ten == "dung_ngu_canh":
                ra.append((tep.relative_to(GOC).as_posix(), nut))
    return ra


def test_co_it_nhat_hai_noi_goi():
    """⛔ Đối chứng cho bánh cóc dưới: nếu bộ dò không tìm thấy gì thì phép kiểm
       kia luôn xanh và không bảo vệ gì cả — *"không đối chứng thì số 0 không
       phải phát hiện"*."""
    assert len(_cac_loi_goi_dung_ngu_canh()) >= 2


def test_moi_noi_goi_deu_di_qua_cua_co():
    """🔴 BÁNH CÓC: nơi gọi thứ ba (P09/B6) phải truyền `khoi_ghi_nho`.

    Người thêm nó sẽ không đọc tệp này — nên phép kiểm phải nói ra thay vì một
    chú thích nằm chờ.
    """
    thieu = [t for t, nut in _cac_loi_goi_dung_ngu_canh()
             if "khoi_ghi_nho" not in {k.arg for k in nut.keywords}]
    assert thieu == [], f"noi goi khong truyen `khoi_ghi_nho`: {thieu}"


def test_dung_HAI_cho_doc_co_ghi_nho_va_moi_cho_mot_viec():
    """Cờ được đọc ở **đúng hai** chỗ, và đó là con số đúng — không phải một.

    ⚠️ Bản đầu của phép kiểm này chốt *"đúng MỘT chỗ"* và đỏ ngay ở bước 4. Mệnh
       đề ấy **sai**, không phải mã sai: một tính năng sau cờ có hai bề mặt độc
       lập, và mỗi bề mặt phải tự đóng lấy.

        `luot.khoi_ghi_nho_neu_bat`   nga ba NGU CANH  -> khong tiem gi
        `routes._chung.cong_ghi_nho`  nga ba HTTP      -> 404

    ⛔ Gộp chúng lại thì tắt cờ vẫn để lộ bốn route (chỉ là chúng trả về kho
       rỗng) — tức vẫn khai rằng tính năng tồn tại. Hai chỗ đọc **cùng một
       hằng số** thì không lệch được; thứ nguy hiểm là hai *tên cờ*, và
       `test_co_ghi_nho_co_ten_rieng_khong_dung_chung` chốt việc đó.
    """
    noi = []
    for tep in sorted((GOC / "apps").rglob("*.py")):
        van = tep.read_bytes().decode("utf-8")
        if "ghi_nho_bat()" in van and tep.name != "co_v3.py":
            noi.append(tep.relative_to(GOC).as_posix())
    assert noi == ["apps/chatltt/routes/_chung.py",
                   "apps/chatltt/services/luot.py"], noi


def test_co_ghi_nho_co_ten_rieng_khong_dung_chung():
    from apps.chatltt.services import co_v3
    assert co_v3.CO_GHI_NHO == "LTT_CHATLTT_V3_MEMORY"
    assert len({co_v3.CO_GHI_NHO, co_v3.CO_TEP, co_v3.CO_TOOLS,
                co_v3.CO_TOOL_CO_PHI, co_v3.CO_DU_AN}) == 5


def test_trang_thai_khai_du_MOI_co():
    """`/api/danh-muc` phải nói được cờ nào đang bật — kể cả cờ mới.

    ⚠️ Bánh cóc này làm đúng việc ở B5: nó đỏ khi cờ thứ **năm** (`du_an`) ra
       đời, và bắt tôi quay lại đây khai. Bản viết lại vẫn chốt **TẬP HỢP**, chỉ
       là năm tên thay vì bốn — không nới thành `>=`, vì nới là gỡ chính thứ vừa
       bắt được thay đổi.
    """
    from apps.chatltt.services import co_v3
    assert set(co_v3.trang_thai()) == {"tools", "tool_co_phi", "tep",
                                       "ghi_nho", "du_an"}


def test_danh_muc_CO_khai_co_v3_ra_giao_dien():
    """🔴 `co_v3.trang_thai()` từng là một hàm KHÔNG AI GỌI.

    Docstring của nó khai *"cho `/api/danh-muc` và log"* từ P03, nhưng đo 06/09:
    không nơi nào gọi. Tức `test_co_ghi_nho_...` ở trên đang chốt hình dạng của
    một thứ **không có người tiêu thụ** — đúng hình dạng *"phép kiểm mạnh hơn
    thứ nó đo"*, chỉ khác là ở đây nó mạnh hơn cả sự tồn tại.

    ⭐ Và giao diện thật sự cần nó: nút *"Máy nhớ gì về bạn"* không được hiện
       khi cờ TẮT — hiện một nút dẫn tới 404 là một lời hứa hỏng, và đó chính
       là lý do `cong_ghi_nho` trả 404 chứ không 403.
    """
    import ast

    cay = ast.parse((GOC / "apps" / "chatltt" / "routes" / "_p_trang.py")
                    .read_bytes().decode("utf-8"))
    ham = [n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and n.name == "api_danh_muc"]
    assert len(ham) == 1
    khoa = {k.value for n in ast.walk(ham[0]) if isinstance(n, ast.Dict)
            for k in n.keys if isinstance(k, ast.Constant)}
    assert "co_v3" in khoa
    assert "nang_luc" in khoa, "doi chung: khoa cu phai con nguyen"
