"""Bảng hàm ĐÓNG của ngôn ngữ biểu thức §6.3 — `ham_bieu_thuc.py`.

⭐ VÌ SAO TỆP NÀY TỒN TẠI, VÀ NÓ CANH CÁI GÌ

Spec §6.3 gọi bảng hàm là **ĐÓNG**. Một bảng "đóng" mà không ai đếm lại thì chỉ
là một bảng. Nên tệp này đóng CẢ HAI chiều, bằng một phép so TẬP HỢP:

    không tên nào NGOÀI spec lọt vào   (mở cửa cho một hàm không ai duyệt)
    không tên nào TRONG spec bị thiếu  (một node publish được rồi chết lúc chạy)

Và chiều thứ ba, cái mà bài học *"hai chỗ khai cùng một điều, không ai bắt khớp"*
nói: danh sách tên trong tệp này **đọc từ chính văn bản spec**, không chép tay.
Chép tay thì tệp test và spec trôi ra xa nhau mà vẫn xanh.

⛔ PHÉP ĐO NÀY KHÔNG PHỦ:
   - Chính sách duyệt AST của ngôn ngữ §6 (`chinh_sach.py`, task 1) — ở đây chỉ
     kiểm các hàm khi GỌI THẲNG bằng Python, không qua máy duyệt. Một hàm an
     toàn vẫn có thể bị gọi sai từ một phương ngữ khai sai.
   - Giới hạn §6.4 (10.000 nút, 1 MB, sâu 32) — trừ trần `range` vì §6.3 khai nó.
   - Nhóm regex: §6.3 HOÃN có chủ đích. Xem `test_bang_chua_mo_nhom_regex`.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re

import pytest

from platform_core.workflow import ham_bieu_thuc as H
from platform_core.workflow.ham_bieu_thuc import BANG_HAM, LoiHam

GOC = pathlib.Path(__file__).resolve().parent.parent
SPEC = GOC / "docs/superpowers/specs/2026-09-22-ltt-workflow-platform-v2-design.md"

#: Tên đếm tay từ §6.3 ngày 24/09 — 49 hàm, bảy nhóm. Giữ ở đây để NGƯỜI đọc
#: được; phép kiểm dưới đây chứng minh nó khớp cả với module lẫn với spec.
TEN_THEO_SPEC = frozenset({
    # chuỗi (12)
    "len", "lower", "upper", "trim", "split", "join", "replace", "contains",
    "starts_with", "ends_with", "substring", "slugify",
    # số (8)
    "to_number", "round", "floor", "ceil", "abs", "min", "max", "sum",
    # kiểu (7)
    "to_string", "to_bool", "to_int", "is_null", "default", "coalesce",
    "type_of",
    # json (2)
    "json_parse", "json_string",
    # danh sách (10)
    "first", "last", "slice", "sort", "sort_by", "unique", "pluck", "flatten",
    "range", "count",
    # object (6)
    "keys", "values", "get", "merge", "pick", "omit",
    # ngày (4)
    "date_parse", "date_format", "date_add", "date_diff",
})

VN = "Asia/Ho_Chi_Minh"
NY = "America/New_York"


def _ten_trong_spec() -> set[str]:
    """Đọc §6.3 và rút ra tên hàm. Không chép tay — spec là nguồn."""
    van = SPEC.read_text(encoding="utf-8")
    m = re.search(r"^### 6\.3 .*?$(.*?)^### ", van, re.M | re.S)
    assert m, "khong tim thay muc 6.3 trong spec"
    than = m.group(1)
    # Bỏ mọi cặp ngoặc: nó nuốt cả danh sách tham số (`sort_by(list, "khoa")`)
    # lẫn đoạn văn xuôi nói vì sao hoãn nhóm regex (trong đó có một `re`).
    than = re.sub(r"\([^()]*\)", " ", than, flags=re.S)
    ten = set()
    for doan in re.findall(r"`([^`]*)`", than, flags=re.S):
        for tu in doan.split():
            if re.fullmatch(r"[a-z_][a-z0-9_]*", tu):
                ten.add(tu)
    return ten


# ── Bảng ĐÓNG: hai chiều, và khớp với spec ────────────────────────────────

def test_bang_la_dict_tra_duoc():
    assert isinstance(BANG_HAM, dict)
    assert all(callable(v) for v in BANG_HAM.values())


def test_spec_van_khai_dung_49_ham():
    """Nếu spec đổi, phép kiểm này đỏ TRƯỚC — không im lặng chạy theo."""
    assert len(_ten_trong_spec()) == 49


def test_bang_khop_spec_hai_chieu():
    trong_spec = _ten_trong_spec()
    assert TEN_THEO_SPEC == trong_spec, "ban dem tay lech voi van ban spec"
    thua = set(BANG_HAM) - trong_spec
    thieu = trong_spec - set(BANG_HAM)
    assert not thua, f"ten NGOAI spec lot vao bang dong: {sorted(thua)}"
    assert not thieu, f"ten trong spec chua cai: {sorted(thieu)}"


def test_khong_ten_rieng_tu():
    assert not [t for t in BANG_HAM if t.startswith("_")]


def test_bang_chua_mo_nhom_regex():
    """§6.3 HOÃN nhóm regex có chủ đích. Mở lại là một quyết định, không phải
    một lần thêm hàm — phép kiểm này bắt ai đó thêm lặng lẽ."""
    assert not [t for t in BANG_HAM if "regex" in t or "match" in t]


def test_module_khong_co_cua_thi_hanh():
    """Cơ học, không giao ước: đọc AST của chính tệp cài đặt."""
    cay = ast.parse((GOC / "platform_core/workflow/ham_bieu_thuc.py")
                    .read_text(encoding="utf-8"))
    cam = {"getattr", "setattr", "eval", "exec", "compile", "__import__",
           "globals", "vars", "locals", "open"}
    goi = {n.func.id for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert not (goi & cam), f"module goi ham nguy hiem: {sorted(goi & cam)}"
    dunder = {n.attr for n in ast.walk(cay)
              if isinstance(n, ast.Attribute) and n.attr.startswith("__")}
    assert not dunder, f"module cham thuoc tinh dunder: {sorted(dunder)}"


# ── `get()`: chỗ dễ mở cửa nhất. Thoát sandbox phải ĐỎ ĐÚNG ───────────────

class _CoThuocTinh:
    bi_mat = "khong duoc thay"

    def phuong_thuc(self):
        return "khong duoc goi"


@pytest.mark.parametrize("duong", [
    "__class__",
    "__class__.__init__",
    "__class__.__init__.__globals__",
    "__dict__",
    "__dict__.bi_mat",
    "__builtins__",
    "__globals__",
    "__subclasses__",
    "a.__class__",
    "a.__class__.__mro__",
])
def test_get_khong_voi_toi_thuoc_tinh_python(duong):
    """⭐ Điều kiện ra của phase: phép thoát sandbox phải ĐỎ ĐÚNG.

    `get` đi sâu theo chuỗi khoá. Nếu nó lui về `getattr` dù chỉ một bước, cả
    ngôn ngữ biểu thức mở ra — `__class__.__init__.__globals__` là đường đi
    kinh điển ra `os.system`.
    """
    obj = {"a": {"b": 1}}
    assert BANG_HAM["get"](obj, duong, "MAC_DINH") == "MAC_DINH"


def test_get_luon_tra_ve_mot_gia_tri_JSON_du_duong_di_the_nao():
    """⚠️ Phép kiểm tham số hoá ở trên chỉ đỏ khi thứ rò ra KHÁC mặc định.

    Đo bằng tiêm lỗi ngày 24/09: một `get` lùi về `getattr` vẫn XANH ở
    `__class__.__init__.__globals__` và `__builtins__` — không phải vì nó an
    toàn, mà vì `getattr` tình cờ ném ở bước thứ hai. Hai ca đỏ thật là
    `__class__` và `a.__class__`, và chúng là bước ĐẦU của mọi chuỗi thoát.

    Phép kiểm này không so với mặc định nữa — nó khẳng định một **tính chất**:
    thứ `get` trả về luôn là một giá trị JSON. Một vật gọi được, một lớp, một
    module lọt ra là đỏ, bất kể đi tới nó bằng đường nào."""
    g = BANG_HAM["get"]
    obj = {"a": {"b": [1, {"c": "x"}]}, "keys": {"d": 2}}
    duong_thu = [
        "__class__", "__class__.__bases__", "__class__.__mro__",
        "__class__.__init__.__globals__", "__builtins__", "__reduce__",
        "a.__class__", "a.b.__class__", "a.b.0.__class__", "keys.__class__",
        "a.items", "a.b.append", "a.b.0.real", "a.b.1.c.upper",
        "a.get", "a.b.count", "keys.d.__class__",
    ]
    for duong in duong_thu:
        ra = g(obj, duong, None)
        assert ra is None or isinstance(ra, (bool, int, float, str, list, dict)), \
            f"{duong!r} lam ro ra mot {ra!r}"


def test_get_khong_cham_doi_tuong_python():
    o = _CoThuocTinh()
    for duong in ("bi_mat", "phuong_thuc", "__class__"):
        assert BANG_HAM["get"](o, duong, None) is None


def test_get_khong_tra_ve_phuong_thuc_cua_dict():
    """`get(obj, "keys")` trên dict phải là MẶC ĐỊNH, không phải `dict.keys`.

    Trả về một hàm là đưa một vật gọi được vào trong ngôn ngữ — bước kế tiếp
    của kẻ tấn công là tìm chỗ gọi nó."""
    assert BANG_HAM["get"]({"x": 1}, "keys", "MAC_DINH") == "MAC_DINH"
    assert BANG_HAM["get"]({"x": 1}, "items", "MAC_DINH") == "MAC_DINH"


def test_get_khoa_gach_duoi_bi_tu_choi_ke_ca_khi_co_that():
    """Dict THẬT sự chứa khoá `_rieng` vẫn không đọc được: §6.1 cấm thuộc tính
    bắt đầu `_`, và `get` không được là cửa hậu cho luật đó."""
    assert BANG_HAM["get"]({"_rieng": 1}, "_rieng", "MAC_DINH") == "MAC_DINH"
    assert BANG_HAM["get"]({"a": {"__x": 1}}, "a.__x", None) is None


def test_get_di_duoc_trong_dict_va_list():
    obj = {"a": {"b": [10, {"c": 3}]}}
    g = BANG_HAM["get"]
    assert g(obj, "a.b.0", None) == 10
    assert g(obj, "a.b.1.c", None) == 3
    assert g(obj, "a.b.9", "HET") == "HET"
    assert g(obj, "a.khong_co", "HET") == "HET"


@pytest.mark.parametrize("duong", ["", ".", "a..b", "a.", ".a", "a.-1"])
def test_get_duong_di_di_dang(duong):
    assert BANG_HAM["get"]({"a": {"b": 1}}, duong, "MAC_DINH") == "MAC_DINH"


def test_get_tren_gia_tri_khong_phai_thung_chua():
    g = BANG_HAM["get"]
    for v in ("chuoi", 5, None, True):
        assert g(v, "a", "MAC_DINH") == "MAC_DINH"


# ── Chuỗi: ca biên trước ca thuận ─────────────────────────────────────────

def test_len_va_count_tren_rong_va_none():
    assert BANG_HAM["len"]("") == 0
    assert BANG_HAM["len"]([]) == 0
    assert BANG_HAM["count"]([]) == 0
    with pytest.raises(LoiHam):
        BANG_HAM["len"](None)
    with pytest.raises(LoiHam):
        BANG_HAM["len"](5)


def test_chuoi_tu_choi_none_thay_vi_bien_thanh_chu_none():
    """`lower(null)` trả `"none"` là cả lớp lỗi im lặng: một ô trống biến thành
    một chuỗi bốn ký tự rồi đi tiếp."""
    for ten in ("lower", "upper", "trim"):
        with pytest.raises(LoiHam):
            BANG_HAM[ten](None)


def test_substring_bien():
    s = BANG_HAM["substring"]
    assert s("abcdef", 1, 3) == "bc"
    assert s("abcdef", 0, 0) == ""
    assert s("abc", 10, 20) == ""
    assert s("abcdef", 4) == "ef"
    with pytest.raises(LoiHam):
        s("abc", -1, 2)
    with pytest.raises(LoiHam):
        s("abc", 3, 1)


def test_split_join_vong_tron():
    sp, jo = BANG_HAM["split"], BANG_HAM["join"]
    assert sp("a,b,,c", ",") == ["a", "b", "", "c"]
    assert sp("", ",") == [""]
    assert jo(["a", "b"], "-") == "a-b"
    assert jo([], "-") == ""
    with pytest.raises(LoiHam):
        jo(["a", 1], "-")          # không ép ngầm số thành chuỗi (§6.4)
    with pytest.raises(LoiHam):
        sp("abc", "")              # sep rỗng: Python ném ValueError thô


def test_contains_starts_ends():
    assert BANG_HAM["contains"]("abc", "b") is True
    assert BANG_HAM["contains"]([1, 2], 2) is True
    assert BANG_HAM["contains"]([1, 2], 9) is False
    assert BANG_HAM["starts_with"]("abc", "") is True
    assert BANG_HAM["ends_with"]("abc", "bc") is True
    with pytest.raises(LoiHam):
        BANG_HAM["contains"](None, "a")


def test_replace_khong_dung_regex():
    """`replace` phải là thay CHỮ, không phải thay MẪU — nếu nó lui về `re`
    thì `.` thành ký tự đại diện và người khai không hề biết."""
    assert BANG_HAM["replace"]("a.b.c", ".", "-") == "a-b-c"
    assert BANG_HAM["replace"]("aaa", "", "-") == "aaa"


# ── slugify: DÙNG LẠI, không viết lại ─────────────────────────────────────

def test_slugify_khong_de_ra_ban_thu_hai():
    """Hai hàm slug trong một kho = hai kết quả cho cùng một chuỗi.

    Phép kiểm này không so hành vi bằng mắt — nó so bằng **danh tính**: cùng
    một đoạn mã chuẩn hoá."""
    from platform_core.public_api import projects
    assert H.nguon_slug() is projects.chuan_hoa_slug


def test_slugify_giu_dau_tieng_viet():
    sl = BANG_HAM["slugify"]
    assert sl("Trang bán hàng") == "trang-ban-hang"
    assert sl("Đường dẫn") == "duong-dan"


def test_slugify_rong_tra_chuoi_rong_khong_phai_default_cua_du_an():
    """⚠️ `projects.slugify("")` trả `"default"` — một mặc định đúng cho BẢNG
    dự án, sai cho một hàm biểu thức: nó bịa ra giá trị người ta không nhập."""
    assert BANG_HAM["slugify"]("") == ""
    assert BANG_HAM["slugify"]("!!!") == ""


def test_slugify_khong_cat_64_ky_tu():
    """Trần 64 là ràng buộc của cột `slug` trong CSDL, không phải của ngôn ngữ."""
    assert len(BANG_HAM["slugify"]("a" * 200)) == 200


# ── Số: hành vi biên CỦA PYTHON, ghim lại thay vì đoán ────────────────────

def test_round_la_lam_tron_ngan_hang_va_ta_ghim_no():
    """docs.python.org/3/library/functions.html#round:
    *"if two multiples are equally close, rounding is done toward the even
    choice"*.

    Đo ngày 24/09 trên CPython 3.13.12: round(0.5)=0, round(2.5)=2.
    Ghim lại vì người khai workflow sẽ đọc con số này trong một hoá đơn."""
    r = BANG_HAM["round"]
    assert r(0.5) == 0
    assert r(1.5) == 2
    assert r(2.5) == 2
    assert r(-1.5) == -2
    assert r(2.675, 2) == 2.67     # nhị phân, không phải 2.68
    assert isinstance(r(1.2), int)


def test_floor_ceil_am():
    assert BANG_HAM["floor"](-1.5) == -2
    assert BANG_HAM["ceil"](-1.5) == -1
    assert isinstance(BANG_HAM["floor"](1.5), int)


def test_to_number_bien():
    tn = BANG_HAM["to_number"]
    assert tn("3") == 3 and isinstance(tn("3"), int)
    assert tn(" 3.5 ") == 3.5
    assert tn(True) == 1
    for xau in ("", "abc", None, "1_0", "0x10", "inf", "nan", [1]):
        with pytest.raises(LoiHam):
            tn(xau)


def test_min_max_sum_tren_rong():
    with pytest.raises(LoiHam):
        BANG_HAM["min"]([])
    with pytest.raises(LoiHam):
        BANG_HAM["max"]([])
    assert BANG_HAM["sum"]([]) == 0
    assert BANG_HAM["min"](3, 1, 2) == 1
    assert BANG_HAM["min"]([3, 1, 2]) == 1
    assert BANG_HAM["max"]([3, 1, 2]) == 3


def test_min_max_sum_tu_choi_tron_kieu():
    """`min(["a", 1])` trên Python ném TypeError thô; §6.4 đòi lỗi nói rõ."""
    with pytest.raises(LoiHam):
        BANG_HAM["min"](["a", 1])
    with pytest.raises(LoiHam):
        BANG_HAM["sum"]([1, "a"])
    with pytest.raises(LoiHam):
        BANG_HAM["sum"]([1, True])   # bool không phải số trong ngôn ngữ này


# ── Kiểu ──────────────────────────────────────────────────────────────────

def test_type_of():
    t = BANG_HAM["type_of"]
    assert t(None) == "null"
    assert t(True) == "boolean"      # ⚠️ bool trước int: bool LÀ int trong Python
    assert t(1) == "integer"
    assert t(1.0) == "number"
    assert t("x") == "text"
    assert t([]) == "list"
    assert t({}) == "object"


def test_to_bool_khong_doan_mo():
    tb = BANG_HAM["to_bool"]
    assert tb("true") is True and tb("FALSE") is False
    assert tb(0) is False and tb(1) is True
    assert tb(None) is False
    for xau in ("yes", "1x", [], {}, 2):
        with pytest.raises(LoiHam):
            tb(xau)


def test_default_va_coalesce_chi_bat_null():
    d, c = BANG_HAM["default"], BANG_HAM["coalesce"]
    assert d(None, 5) == 5
    assert d("", 5) == ""            # chuỗi rỗng KHÔNG phải null
    assert d(0, 5) == 0 and d(False, 5) is False
    assert c(None, None, 3) == 3
    assert c(None, None) is None
    assert BANG_HAM["is_null"](None) is True
    assert BANG_HAM["is_null"]("") is False


def test_to_int_cat_hay_lam_tron():
    ti = BANG_HAM["to_int"]
    assert ti("7") == 7
    assert ti(7.9) == 7 and ti(-7.9) == -7      # cắt về 0, không làm tròn
    with pytest.raises(LoiHam):
        ti("7.9")


def test_to_string():
    ts = BANG_HAM["to_string"]
    assert ts(1) == "1"
    assert ts(True) == "true" and ts(False) == "false"   # JSON, không Python
    assert ts(None) == ""
    assert ts([1, 2]) == "[1, 2]"


# ── JSON ──────────────────────────────────────────────────────────────────

def test_json_parse_loi_va_vong_tron():
    jp, js = BANG_HAM["json_parse"], BANG_HAM["json_string"]
    assert jp('{"a":1}') == {"a": 1}
    assert js({"a": 1}) == '{"a": 1}'
    for xau in ("", "{", "NaN", "Infinity", None, "{'a':1}"):
        with pytest.raises(LoiHam):
            jp(xau)


def test_json_string_tu_choi_nan_va_vat_la():
    with pytest.raises(LoiHam):
        BANG_HAM["json_string"](float("nan"))
    with pytest.raises(LoiHam):
        BANG_HAM["json_string"](object())


# ── Danh sách ─────────────────────────────────────────────────────────────

def test_first_last_tren_rong():
    assert BANG_HAM["first"]([]) is None
    assert BANG_HAM["last"]([]) is None
    assert BANG_HAM["last"]([1, 2]) == 2
    with pytest.raises(LoiHam):
        BANG_HAM["first"]("abc")   # chuỗi không phải danh sách ở đây


def test_slice_am_va_lech():
    sl = BANG_HAM["slice"]
    assert sl([1, 2, 3, 4], 1, 3) == [2, 3]
    assert sl([1, 2], 5, 9) == []
    assert sl([1, 2, 3], 1) == [2, 3]
    with pytest.raises(LoiHam):
        sl([1, 2, 3], -1, 2)


def test_sort_on_dinh_va_tu_choi_tron_kieu():
    """docs.python.org/3/library/stdtypes.html#list.sort:
    *"sorts are guaranteed to be stable"*. Ghim vì `sort_by` dùng đặc tính đó."""
    assert BANG_HAM["sort"]([3, 1, 2]) == [1, 2, 3]
    assert BANG_HAM["sort"]([]) == []
    assert BANG_HAM["sort"](["b", "a"]) == ["a", "b"]
    with pytest.raises(LoiHam):
        BANG_HAM["sort"]([1, "a"])


def test_sort_by_on_dinh_va_thieu_khoa():
    sb = BANG_HAM["sort_by"]
    ds = [{"k": 2, "i": 0}, {"k": 1, "i": 1}, {"k": 2, "i": 2}]
    assert [x["i"] for x in sb(ds, "k")] == [1, 0, 2]   # ổn định: 0 trước 2
    with pytest.raises(LoiHam):
        sb([{"k": 1}, {}], "k")                        # thiếu khoá: nói rõ
    with pytest.raises(LoiHam):
        sb([1, 2], "k")


def test_unique_giu_thu_tu_va_chiu_vat_khong_bam_duoc():
    u = BANG_HAM["unique"]
    assert u([3, 1, 3, 2, 1]) == [3, 1, 2]
    assert u([{"a": 1}, {"a": 1}, {"a": 2}]) == [{"a": 1}, {"a": 2}]
    assert u([0, False]) == [0, False]     # ⚠️ 0 == False nhưng khác kiểu
    assert u([]) == []


def test_pluck_va_flatten():
    assert BANG_HAM["pluck"]([{"a": 1}, {"b": 2}, {"a": 3}], "a") == [1, 3]
    assert BANG_HAM["flatten"]([[1, 2], [], [3]]) == [1, 2, 3]
    assert BANG_HAM["flatten"]([[1, [2]]]) == [1, [2]]   # MỘT tầng, không đệ quy
    with pytest.raises(LoiHam):
        BANG_HAM["flatten"]([1, 2])


def test_range_co_tran_1000():
    rg = BANG_HAM["range"]
    assert rg(0) == []
    assert rg(3) == [0, 1, 2]
    assert len(rg(1000)) == 1000
    for xau in (1001, -1, 1.5, "3", None):
        with pytest.raises(LoiHam):
            rg(xau)


# ── Object ────────────────────────────────────────────────────────────────

def test_keys_values_merge_pick_omit():
    assert BANG_HAM["keys"]({"b": 1, "a": 2}) == ["b", "a"]   # thứ tự chèn
    assert BANG_HAM["values"]({"b": 1, "a": 2}) == [1, 2]
    assert BANG_HAM["merge"]({"a": 1}, {"a": 2, "b": 3}) == {"a": 2, "b": 3}
    assert BANG_HAM["pick"]({"a": 1, "b": 2}, "a", "z") == {"a": 1}
    assert BANG_HAM["omit"]({"a": 1, "b": 2}, "a") == {"b": 2}
    with pytest.raises(LoiHam):
        BANG_HAM["keys"]([1, 2])


def test_merge_khong_sua_dau_vao():
    a = {"x": 1}
    BANG_HAM["merge"](a, {"y": 2})
    assert a == {"x": 1}


def test_khoa_gach_duoi_vo_hinh_o_moi_cua():
    """Một luật, không phải bốn ngoại lệ: khoá bắt đầu `_` không tồn tại đối
    với ngôn ngữ biểu thức — ở `get`, `keys`, `values`, `pick`, `omit`."""
    o = {"_a": 1, "b": 2}
    assert BANG_HAM["keys"](o) == ["b"]
    assert BANG_HAM["values"](o) == [2]
    assert BANG_HAM["pick"](o, "_a", "b") == {"b": 2}
    assert BANG_HAM["omit"](o, "b") == {}


# ── Ngày: múi giờ TƯỜNG MINH, và DST là chỗ thư viện sai ──────────────────

def test_date_parse_mac_dinh_la_gio_viet_nam():
    d = BANG_HAM["date_parse"]("2026-03-01 08:00", "%Y-%m-%d %H:%M")
    assert d == "2026-03-01T08:00:00+07:00"


def test_date_parse_tra_ve_CHUOI_json_duoc():
    """§6.4: tham số đã tính lưu vào snapshot RUNNING. Một `datetime` không
    JSON hoá được, và nó còn mang thuộc tính Python vào trong ngôn ngữ."""
    d = BANG_HAM["date_parse"]("2026-03-01T08:00:00", "iso", VN)
    assert isinstance(d, str)
    json.dumps(d)


def test_date_parse_doi_mui_gio_tuong_minh_khi_chuoi_khong_co():
    d = BANG_HAM["date_parse"]("2026-01-01T00:00:00", "iso", NY)
    assert d == "2026-01-01T00:00:00-05:00"


def test_date_parse_giu_offset_co_san_trong_chuoi():
    d = BANG_HAM["date_parse"]("2026-01-01T00:00:00+09:00", "iso", NY)
    assert d == "2026-01-01T00:00:00+09:00"


def test_date_parse_loi():
    for s, f in [("", "iso"), ("khong-phai-ngay", "iso"),
                 ("2026-13-01", "%Y-%m-%d"), (None, "iso")]:
        with pytest.raises(LoiHam):
            BANG_HAM["date_parse"](s, f, VN)
    with pytest.raises(LoiHam):
        BANG_HAM["date_parse"]("2026-01-01", "iso", "Mars/Olympus")


def test_viet_nam_khong_phai_mot_offset_co_dinh():
    """⚠️ `Asia/Ho_Chi_Minh` đổi từ +08:00 sang +07:00 giữa năm 1975 (tzdata
    2026.1, đo 24/09). Ai thay múi giờ bằng một hằng số sẽ sai ở đây."""
    assert BANG_HAM["date_parse"]("1975-06-01T12:00:00", "iso", VN) \
        == "1975-06-01T12:00:00+08:00"
    assert BANG_HAM["date_parse"]("1975-07-01T12:00:00", "iso", VN) \
        == "1975-07-01T12:00:00+07:00"


def test_date_add_ngay_la_gio_TUONG_va_gio_la_gio_THAT():
    """⭐ Bẫy DST, cùng hạng với croniter #258.

    Đo 24/09 trên CPython 3.13.12 + tzdata 2026.1: từ 2026-03-07 12:00 NY,
    `+1 day` ra 2026-03-08 12:00−04:00 (23 giờ THẬT trôi qua), còn `+24 hour`
    ra 13:00−04:00. Hai kết quả KHÁC NHAU, và cả hai đều đúng — "ngày" là đơn
    vị lịch, "giờ" là đơn vị thời lượng. Gộp chung làm một là sai một bên."""
    a = "2026-03-07T12:00:00-05:00"
    assert BANG_HAM["date_add"](a, 1, "day", NY) == "2026-03-08T12:00:00-04:00"
    assert BANG_HAM["date_add"](a, 24, "hour", NY) == "2026-03-08T13:00:00-04:00"
    assert BANG_HAM["date_add"](a, 1440, "minute", NY) == "2026-03-08T13:00:00-04:00"


def test_date_add_khong_co_tz_thi_offset_DUNG_YEN_va_do_la_gioi_han():
    """⚠️ Một chuỗi ISO mang OFFSET, không mang TÊN VÙNG. `-05:00` không nói
    được nó là New York hay Bogotá, nên không có `tz` thì `date_add` chỉ làm
    số học trên offset cố định đó — kết quả dưới đây **lệch một giờ** so với
    giờ tường New York thật.

    Ghim ca này thay vì giấu nó: người khai workflow cần biết rằng cộng theo
    LỊCH qua ranh giới DST đòi phải khai múi giờ."""
    a = "2026-03-07T12:00:00-05:00"
    assert BANG_HAM["date_add"](a, 1, "day") == "2026-03-08T12:00:00-05:00"


def test_date_add_am_va_don_vi_sai():
    a = "2026-03-08T12:00:00-04:00"
    assert BANG_HAM["date_add"](a, -1, "day", NY) == "2026-03-07T12:00:00-05:00"
    assert BANG_HAM["date_add"](a, 0, "day", NY) == a
    for dv in ("week", "month", "year", "second", "", None):
        with pytest.raises(LoiHam):
            BANG_HAM["date_add"](a, 1, dv)
    with pytest.raises(LoiHam):
        BANG_HAM["date_add"](a, 1.5, "day")


def test_gio_KHONG_TON_TAI_thi_noi_ra_chu_khong_lang_le_troi():
    """02:30 ngày 2026-03-08 ở New York không tồn tại. CPython **không** báo
    lỗi — nó lặng lẽ giữ offset cũ rồi quy về 03:30 UTC-tương-đương. Một trần
    thời gian lệch một tiếng mà không ai biết là đúng hạng lỗi phải chặn."""
    with pytest.raises(LoiHam):
        BANG_HAM["date_parse"]("2026-03-08T02:30:00", "iso", NY)
    with pytest.raises(LoiHam):
        BANG_HAM["date_add"]("2026-03-07T02:30:00-05:00", 1, "day", NY)


def test_date_diff_tinh_theo_UTC_nen_khong_bi_fold_nuot():
    """⭐ 01:30 ngày 2026-11-01 ở New York xảy ra HAI lần. PEP 495: trừ hai mốc
    CÙNG múi giờ **bỏ qua** `fold`, nên phép trừ ngây thơ ra `0`. Đo 24/09:
    `f1 - f0 = 0:00:00` nhưng qua UTC là `1:00:00`. Chuỗi ISO mang offset nên
    hai mốc đó khác nhau tường minh — và `date_diff` phải thấy điều đó."""
    som = "2026-11-01T01:30:00-04:00"
    muon = "2026-11-01T01:30:00-05:00"
    assert BANG_HAM["date_diff"](muon, som, "hour") == 1
    assert BANG_HAM["date_diff"](som, muon, "hour") == -1
    assert BANG_HAM["date_diff"](som, som, "hour") == 0


def test_date_diff_qua_mui_gio_khac_nhau():
    assert BANG_HAM["date_diff"]("2026-01-01T07:00:00+07:00",
                                 "2026-01-01T00:00:00+00:00", "minute") == 0


def test_date_diff_cat_ve_0_khong_lam_tron():
    a = "2026-01-01T00:00:00+07:00"
    assert BANG_HAM["date_diff"]("2026-01-01T01:59:00+07:00", a, "hour") == 1
    assert BANG_HAM["date_diff"]("2025-12-31T22:01:00+07:00", a, "hour") == -1
    with pytest.raises(LoiHam):
        BANG_HAM["date_diff"](a, a, "week")


def test_date_format_doi_mui_gio():
    d = "2026-01-01T00:00:00+00:00"
    assert BANG_HAM["date_format"](d, "%Y-%m-%d %H:%M", VN) == "2026-01-01 07:00"
    assert BANG_HAM["date_format"](d, "%Y-%m-%d %H:%M") == "2026-01-01 07:00"
    assert BANG_HAM["date_format"](d, "iso", NY) == "2025-12-31T19:00:00-05:00"


def test_date_format_tu_choi_dinh_dang_mo_cua():
    for f in ("", None, "%Y" * 200):
        with pytest.raises(LoiHam):
            BANG_HAM["date_format"]("2026-01-01T00:00:00+00:00", f, VN)
