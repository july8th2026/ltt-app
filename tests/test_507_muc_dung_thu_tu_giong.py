r"""U-12 — THỨ TỰ GIỌNG ĐẾN TỪ MỨC DÙNG THẬT CỦA TA.

## Vì sao có tệp này

`_p_tao.py` mời khách chọn giọng theo **thứ tự khai báo trong ảnh chụp của
engine** — một thứ tự do người khác quyết, vì một lý do không liên quan tới
khách của ta. `tham_chieu.py` đã xếp lại theo phong cách, nhưng bên trong một
tầng phong cách vẫn còn 6–7 giọng, và giữa chúng thứ tự là **bảng chữ cái**.

Bảng chữ cái không phải một quyết định sản phẩm; nó là sự vắng mặt của một
quyết định — trong khi phần tử **đầu** được dùng làm mặc định.

## ⛔ Ba mệnh đề tệp này chốt, và chúng khác nhau

1. **Ảnh chụp rỗng ⇒ thứ tự CŨ, y nguyên.** Đây là mệnh đề quan trọng nhất, vì
   ảnh chụp rỗng là trạng thái của mọi kho vừa khởi động lại.
2. **Mức dùng ĐỔI được thứ tự** — bên trong một tầng phong cách.
3. **Mức dùng KHÔNG vượt được tầng phong cách.** Vòng phản hồi "hiện trước ⇒
   dùng nhiều ⇒ càng hiện trước" là có thật; ta nhốt nó trong một tầng.

⭐ Mệnh đề 2 và 3 phải đi **cùng nhau**. Chỉ có 2 thì một bản vá "xếp thuần theo
   mức dùng" cũng xanh — và nó sẽ kéo một giọng kể chuyện lên làm mặc định cho
   mọi khách mới. Chỉ có 3 thì một bản vá **bỏ hẳn** mức dùng cũng xanh.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from apps.ltt_voice import giong_mau, muc_dung

GOC = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _sach():
    """⛔ Ảnh chụp là trạng thái **cấp module**. Không dọn thì một phép kiểm đặt
    số liệu sẽ quyết định kết quả của phép kiểm chạy sau nó — và thứ tự chạy
    thì `pytest-randomly` đổi mỗi lượt, nên lỗi ấy hiện ra rồi biến mất."""
    muc_dung.xoa()
    yield
    muc_dung.xoa()


def _ma(ds) -> list:
    return [g.ma for g in ds]


# ── 1. Rỗng là trạng thái hợp lệ, và nó cho thứ tự CŨ ────────────────────────

def test_anh_chup_RONG_cho_dung_thu_tu_co_so():
    """Không có số liệu ⇒ (phong cách, mã) — đúng thứ tự trước 08/09/2026."""
    mong = _ma(sorted(giong_mau.DANH_SACH,
                      key=lambda g: (giong_mau.UU_TIEN_PHONG_CACH.get(
                          g.phong_cach, 9), g.ma)))
    assert _ma(muc_dung.xep(giong_mau.DANH_SACH)) == mong


def test_anh_chup_QUA_HAN_bi_coi_nhu_RONG(monkeypatch):
    """⭐ Vòng bảo trì chết thì thứ tự **lùi về cơ sở**, không đóng băng mãi mãi
    ở một ảnh chụp không ai biết đã cũ bao lâu."""
    ds = list(giong_mau.DANH_SACH)
    muc_dung.dat({ds[-1].ma: 999})
    assert muc_dung.dem(), "moi dat xong ma da rong"
    monkeypatch.setattr(muc_dung, "HAN_DUNG_S", -1)
    assert muc_dung.dem() == {}


def test_xep_KHONG_them_bot_phan_tu():
    """Nó là phép **xếp**, không phải phép lọc. Một giọng chưa ai dùng vẫn hiện
    đủ — chỉ nằm sau."""
    ds = list(giong_mau.DANH_SACH)
    muc_dung.dat({ds[0].ma: 500})
    assert sorted(_ma(muc_dung.xep(ds))) == sorted(_ma(ds))


# ── 2. Mức dùng ĐỔI được thứ tự — trong một tầng ─────────────────────────────

def _theo_tang() -> dict:
    theo: dict = {}
    for g in giong_mau.DANH_SACH:
        theo.setdefault(g.phong_cach, []).append(g)
    return theo


def _cung_tang() -> list:
    """Hai giọng cùng phong cách, để phép so không lẫn với tầng.

    🔴 `assert`, KHÔNG `pytest.skip`. Bản đầu viết `skip` cho "phòng khi kho
       giọng chỉ có một tầng" — và điều kiện ấy **không bao giờ đúng được**:
       ảnh chụp giọng là một tệp trong chính kho này (đo 08/09/2026: ba tầng,
       4 · 8 · 8 giọng), không phải một thứ của môi trường.

    ⛔ Một `skip` không nổ được thì nó không canh gì cả — nó chỉ cộng vào bánh
       cóc `check_bo_qua` và làm bản kiểm kê nói rằng phép kiểm này *có thể*
       vắng mặt một cách hợp lệ. Và nếu ngày nào ảnh chụp **thật sự** mất một
       tầng, thứ ta muốn là một lượt ĐỎ bắt người ta nhìn, không phải một dòng
       `skipped` trôi qua.

    ⭐ `skip` dành cho điều kiện của **môi trường** (thiếu GPU, thiếu cổng).
       Dữ liệu nằm trong kho thì `assert`.
    """
    theo = _theo_tang()
    cac = [v for v in theo.values() if len(v) >= 2]
    assert cac, (
        f"khong tang phong cach nao co >=2 giong — anh chup giong da doi? "
        f"(hien: { {k: len(v) for k, v in theo.items()} })")
    return sorted(cac[0], key=lambda g: g.ma)[:2]


def test_muc_dung_DAY_mot_giong_len_truoc_trong_cung_tang():
    dau, sau = _cung_tang()
    assert _ma(muc_dung.xep([dau, sau])) == [dau.ma, sau.ma], "chua co dem"
    muc_dung.dat({sau.ma: 100})
    assert _ma(muc_dung.xep([dau, sau])) == [sau.ma, dau.ma], (
        "muc dung KHONG doi duoc thu tu — `xep` dang bo qua anh chup")


def test_bang_diem_thi_xep_theo_MA_va_khong_bap_benh():
    """🔴 Thiếu khoá phá hoà thì hai giọng cùng 0 lượt ra thứ tự tuỳ lượt — tức
    trang **đổi mặc định giữa hai lần tải mà không có gì đổi**."""
    dau, sau = _cung_tang()
    muc_dung.dat({dau.ma: 7, sau.ma: 7})
    lan1 = _ma(muc_dung.xep([sau, dau]))
    lan2 = _ma(muc_dung.xep([dau, sau]))
    assert lan1 == lan2 == sorted([dau.ma, sau.ma])


# ── 3. ⛔ Mức dùng KHÔNG vượt được tầng phong cách ────────────────────────────

def test_muc_dung_KHONG_keo_duoc_mot_giong_qua_TANG():
    """⭐ Đây là vế chặn vòng phản hồi, và là vế duy nhất phân biệt bản này với
    một bản "xếp thuần theo mức dùng" — bản ấy cũng xanh ở mọi phép kiểm trên.
    """
    theo_tang = _theo_tang()
    tang = sorted(theo_tang, key=lambda t: giong_mau.UU_TIEN_PHONG_CACH.get(t, 9))
    # 🔴 `assert`, không `skip` — cùng lý do đã ghi ở `_cung_tang`.
    assert len(tang) >= 2, (
        f"kho giong chi con MOT tang phong cach ({tang}) — phep kiem nay mat "
        f"y nghia, va do la mot thay doi dang do chu khong dang bo qua")

    tren = theo_tang[tang[0]][0]
    duoi = theo_tang[tang[-1]][0]
    muc_dung.dat({duoi.ma: 10_000, tren.ma: 0})
    assert _ma(muc_dung.xep([tren, duoi])) == [tren.ma, duoi.ma], (
        f"`{duoi.ma}` (tang `{duoi.phong_cach}`) vuot len tren `{tren.ma}` "
        f"(tang `{tren.phong_cach}`) chi vi duoc dung nhieu — vong phan hoi "
        f"da thoat khoi tang")


# ── 4. Hằng số ưu tiên chỉ có MỘT bản ────────────────────────────────────────

def test_chi_MOT_bang_uu_tien_phong_cach_trong_ca_app():
    """⛔ Hai bảng thứ tự cho cùng một kho giọng là hai màn hình mời cùng một
    khách hai giọng **mặc định** khác nhau.

    Bản trước có đúng hai bản: một trong `giong_mau`, một gõ tại chỗ trong
    `tham_chieu.sap_xep`.
    """
    goc = GOC / "apps/ltt_voice"
    thay = []
    for f in goc.rglob("*.py"):
        if "__pycache__" in f.parts or f.name == "giong_mau.py":
            continue
        cay = ast.parse(f.read_text(encoding="utf-8"))
        for n in ast.walk(cay):
            if not isinstance(n, ast.Dict):
                continue
            khoa = {k.value for k in n.keys
                    if isinstance(k, ast.Constant) and isinstance(k.value, str)}
            if {"tu_nhien", "doc_truyen", "tin_tuc"} <= khoa and all(
                    isinstance(v, ast.Constant) and isinstance(v.value, int)
                    for v in n.values):
                thay.append(f"{f.relative_to(GOC)}:{n.lineno}")
    assert not thay, (
        f"bang uu tien phong cach bi go lai o {thay} — dung "
        f"`giong_mau.UU_TIEN_PHONG_CACH`")


# ── 5. Nối vào SẢN PHẨM, không phải một hàm mồ côi ───────────────────────────

def _goi_ham(f: pathlib.Path, ten: str) -> bool:
    cay = ast.parse(f.read_text(encoding="utf-8"))
    return any(isinstance(n, ast.Call) and ten in ast.unparse(n.func)
               for n in ast.walk(cay))


@pytest.mark.parametrize("tep", [
    "apps/ltt_voice/routes/_p_tao.py",
    "apps/ltt_voice/routes/_p_giong.py",
    "apps/ltt_voice/routes/_p_api.py",
    "apps/ltt_voice/tham_chieu.py",
])
def test_moi_noi_dung_danh_sach_giong_deu_di_qua_xep(tep):
    """⛔ Truyền thẳng `giong_mau.DANH_SACH` là bỏ qua toàn bộ cơ chế — và nó
    hỏng **lặng lẽ**: trang vẫn dựng, chỉ là thứ tự sai."""
    ma = (GOC / tep).read_text(encoding="utf-8")
    assert "muc_dung.xep(" in ma, f"{tep} khong xep truoc khi hien"
    cay = ast.parse(ma)
    tho = [n.lineno for n in ast.walk(cay)
           if isinstance(n, ast.keyword) and n.arg == "giong_mau"
           and isinstance(n.value, ast.Attribute) and n.value.attr == "DANH_SACH"]
    assert not tho, (
        f"{tep}:{tho} truyen thang `giong_mau.DANH_SACH` - phai qua "
        f"`muc_dung.xep(...)`")


def test_bao_tri_CO_dem_muc_dung():
    """Ảnh chụp không tự đầy. Không nối vào `bao_tri` thì `xep()` sẽ mãi mãi
    chạy trên một `dict` rỗng — đúng lớp lỗi DV-010 (`KetQua.canh_bao`)."""
    from apps.ltt_voice import nghe_thu
    assert _goi_ham(GOC / "apps/ltt_voice/nghe_thu.py", "_dem_muc_dung")
    assert hasattr(nghe_thu, "_dem_muc_dung")


def test_dem_muc_dung_DUNG_NGOAI_cong_san_sang():
    """⭐ Thứ tự giọng là chuyện của giao diện; nó phải đúng cả trên máy chưa
    cài engine. Đặt phép đếm **sau** `if not san_sang(): return` là để một kho
    chạy nhiều tháng không engine phục vụ mãi một thứ tự bảng chữ cái."""
    ma = (GOC / "apps/ltt_voice/nghe_thu.py").read_text(encoding="utf-8")
    cay = ast.parse(ma)
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "bao_tri")
    dong_dem = next(n.lineno for n in ast.walk(ham)
                    if isinstance(n, ast.Call) and "_dem_muc_dung" in
                    ast.unparse(n.func))
    dong_cong = next(n.lineno for n in ast.walk(ham)
                     if isinstance(n, ast.Call) and "san_sang" in
                     ast.unparse(n.func))
    assert dong_dem < dong_cong, (
        "`_dem_muc_dung()` nam SAU cong `san_sang()` - may chua cai engine se "
        "khong bao gio dem duoc")


def test_lam_moi_KHONG_NEM_khi_CSDL_hong():
    """Việc nền chạy dưới lease. Một truy vấn hỏng không được làm hỏng lượt
    dựng tệp nghe thử ngay dưới nó."""
    class DbHong:
        def execute(self, *a, **k):
            raise RuntimeError("csdl hong")

    assert muc_dung.lam_moi(DbHong()) == 0
    assert muc_dung.dem() == {}, "loi ma van ghi de anh chup"


def test_lam_moi_dem_PRESET_chu_khong_dem_voice_id():
    """⚠️ Giọng nhân bản là của **riêng một khách**. Xếp thứ tự giọng MẪU theo
    mức dùng của giọng nhân bản là trộn hai tập không giao nhau."""
    ma = (GOC / "apps/ltt_voice/muc_dung.py").read_text(encoding="utf-8")
    cay = ast.parse(ma)
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "lam_moi")
    chuoi = {n.value for n in ast.walk(ham)
             if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert "preset" in chuoi
    assert "voice_id" not in chuoi


def test_lam_moi_CO_TRAN_dong():
    """⛔ Bảng `jobs` của **cả kho**, không của một khách. Một `.all()` không
    trần trên một bảng đang lớn là cách làm chết tiến trình worker vào một ngày
    không ai đoán trước."""
    assert isinstance(muc_dung.GIOI_HAN, int) and muc_dung.GIOI_HAN > 0
    ma = (GOC / "apps/ltt_voice/muc_dung.py").read_text(encoding="utf-8")
    cay = ast.parse(ma)
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "lam_moi")
    assert any(isinstance(n, ast.Call) and ast.unparse(n.func).endswith("limit")
               for n in ast.walk(ham)), "truy van khong co `.limit(...)`"
