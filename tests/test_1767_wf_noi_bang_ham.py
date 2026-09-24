"""MOI NOI: bang ham §6.3 (`ham_bieu_thuc.BANG_HAM`) × bo tinh §6.1
(`chinh_sach.DAY_DU`).

## Vi sao co tep nay

Hai lan song song da lam hai nua cua cung mot ngon ngu:

    Task 3+5  chinh sach DAY DU, namespace, ep kieu, gioi han  — bang ham GIA
    Task 4    BANG_HAM, 49 ham                                  — khong co bo tinh

Bao cao Task 3+5 tu khai: *"`DAY_DU.ham == {}`; cac ca goi ham dung bang GIA"*,
va liet ke chinh cho nay trong muc "khong phu": *"ngay `BANG_HAM` cam vao, phai
do lai ..."*. ⇒ Truoc tep nay, **khong phep kiem nao** di qua ca hai nua.

⛔ Nen tep nay KHONG kiem lai tung nua. No kiem **cho ghep**:

1. goi duoc **CA 49** ham qua bo tinh (khong chon mau — bang phep kiem so hai
   chieu voi `BANG_HAM`);
2. ten NGOAI bang bi tu choi o **tang bo tinh**, khong chi o tang bang;
3. ham nem loi ⇒ loi **co cho** (cot) va khong ro kieu ngoai le cua tang duoi;
4. sai so tham so ⇒ loi ro, ⛔ khong `TypeError` tho;
5. khong ham nao tra ve mot vat ngoai tap gia tri JSON.

## ⛔ Tep nay KHONG phu

- Khong kiem lai ngu nghia tung ham (do la `test_1765`) — chi kiem rang goi
  duoc va tra ve gia tri JSON.
- Khong phu `{{ }}` (`noi_suy.py`) va khong phu duong dong co.
"""
from __future__ import annotations

import ast
import dataclasses

import pytest

from platform_core.workflow import chinh_sach as CS
from platform_core.workflow import ngon_ngu as NN
from platform_core.workflow.chinh_sach import (
    HANG_SO_TEN,
    NAMESPACE,
    LoiNgonNgu,
    moi_truong_wf,
)
from platform_core.workflow.ham_bieu_thuc import BANG_HAM, LoiHam


def mt(**ns):
    return moi_truong_wf(**ns)


# ═══════════════════════════════════════════════════════════════════════════
#  1. CA 49 HAM goi duoc qua bo tinh
# ═══════════════════════════════════════════════════════════════════════════
#
# ⭐ Mot cap (bieu thuc, ket qua) cho MOI ten trong bang. Khong chon mau: mot
#    ham chi "co trong bang" ma chua ai goi qua bo tinh la mot ham chua ai do.

CA_49: dict[str, tuple[str, object]] = {
    # -- chuoi (12) --
    "len": ('len("abc")', 3),
    "lower": ('lower("AB")', "ab"),
    "upper": ('upper("ab")', "AB"),
    "trim": ('trim("  a  ")', "a"),
    "split": ('split("a,b", ",")', ["a", "b"]),
    "join": ('join(["a", "b"], "-")', "a-b"),
    "replace": ('replace("aXa", "X", "b")', "aba"),
    "contains": ('contains("abc", "b")', True),
    "starts_with": ('starts_with("abc", "a")', True),
    "ends_with": ('ends_with("abc", "c")', True),
    "substring": ('substring("abcdef", 1, 3)', "bc"),
    "slugify": ('slugify("Trang ban hang")', "trang-ban-hang"),
    # -- so (8) --
    "to_number": ('to_number("3")', 3),
    "round": ("round(2.567, 1)", 2.6),
    "floor": ("floor(2.7)", 2),
    "ceil": ("ceil(2.1)", 3),
    "abs": ("abs(-3)", 3),
    "min": ("min(3, 1, 2)", 1),
    "max": ("max(3, 1, 2)", 3),
    "sum": ("sum([1, 2, 3])", 6),
    # -- kieu (7) --
    "to_string": ("to_string(12)", "12"),
    "to_bool": ('to_bool("true")', True),
    "to_int": ('to_int("7")', 7),
    "is_null": ("is_null(null)", True),
    "default": ('default(null, "x")', "x"),
    "coalesce": ('coalesce(null, null, "y")', "y"),
    "type_of": ('type_of("a")', "text"),
    # -- JSON (2) --
    "json_parse": ("json_parse('{\"a\": 1}')", {"a": 1}),
    "json_string": ("json_string([1, 2])", "[1, 2]"),
    # -- danh sach (10) --
    "first": ("first([1, 2])", 1),
    "last": ("last([1, 2])", 2),
    "slice": ("slice([1, 2, 3], 1)", [2, 3]),
    "sort": ("sort([2, 1])", [1, 2]),
    "sort_by": ('sort_by([{"k": 2}, {"k": 1}], "k")', [{"k": 1}, {"k": 2}]),
    "unique": ("unique([1, 1, 2])", [1, 2]),
    "pluck": ('pluck([{"k": 1}], "k")', [1]),
    "flatten": ("flatten([[1], [2]])", [1, 2]),
    "range": ("range(3)", [0, 1, 2]),
    "count": ("count([1, 2])", 2),
    # -- object (6) --
    "keys": ('keys({"a": 1})', ["a"]),
    "values": ('values({"a": 1})', [1]),
    "get": ('get({"a": {"b": 2}}, "a.b", 0)', 2),
    "merge": ('merge({"a": 1}, {"b": 2})', {"a": 1, "b": 2}),
    "pick": ('pick({"a": 1, "b": 2}, "a")', {"a": 1}),
    "omit": ('omit({"a": 1, "b": 2}, "a")', {"b": 2}),
    # -- ngay (4) --
    "date_parse": ('date_parse("2026-09-24T10:00:00", "iso", '
                   '"Asia/Ho_Chi_Minh")', "2026-09-24T10:00:00+07:00"),
    "date_format": ('date_format("2026-09-24T10:00:00+07:00", "%Y", '
                    '"Asia/Ho_Chi_Minh")', "2026"),
    "date_add": ('date_add("2026-09-24T10:00:00+07:00", 1, "day", '
                 '"Asia/Ho_Chi_Minh")', "2026-09-25T10:00:00+07:00"),
    "date_diff": ('date_diff("2026-09-24T11:00:00+07:00", '
                  '"2026-09-24T10:00:00+07:00", "hour")', 1),
}


def test_bang_phep_kiem_khop_BANG_HAM_ca_hai_chieu():
    """⛔ Them mot ham vao bang ma khong goi no qua bo tinh ⇒ ĐỎ o day.

    Day la co so co hoc cua chu "MOI ham": khong phai mot loi hua trong
    docstring ma mot phep so tap hop.
    """
    assert set(CA_49) == set(BANG_HAM), {
        "thieu_ca_kiem": sorted(set(BANG_HAM) - set(CA_49)),
        "thua_ca_kiem": sorted(set(CA_49) - set(BANG_HAM)),
    }
    assert len(CA_49) == 49


@pytest.mark.parametrize("ten", sorted(CA_49))
def test_moi_ham_goi_duoc_QUA_BO_TINH(ten):
    bt, mong = CA_49[ten]
    assert NN.tinh(bt, mt()) == mong


@pytest.mark.parametrize("ten", sorted(CA_49))
def test_moi_ham_tra_ve_GIA_TRI_JSON(ten):
    """⭐ Dieu ma Task 3+5 khai la CHUA DO: tang chinh sach cam **cu phap**
    goi, no khong kiem **gia tri tra ve**. Mot ham tra ve vat goi duoc / mot
    `datetime` la dua be mat Python vao trong ngon ngu.
    """
    ra = NN.tinh(CA_49[ten][0], mt())
    _khong_phai_vat_python(ra)


def _khong_phai_vat_python(gia_tri, sau: int = 0) -> None:
    assert sau < 8
    assert not callable(gia_tri), f"tra ve VAT GOI DUOC: {gia_tri!r}"
    assert gia_tri is None or isinstance(gia_tri, (bool, int, float, str,
                                                   list, dict)), \
        f"kieu ngoai JSON: {type(gia_tri).__name__}"
    if isinstance(gia_tri, list):
        for v in gia_tri:
            _khong_phai_vat_python(v, sau + 1)
    if isinstance(gia_tri, dict):
        for k, v in gia_tri.items():
            assert isinstance(k, str)
            _khong_phai_vat_python(v, sau + 1)


def test_ten_ham_KHONG_dam_len_namespace():
    """Mot ham ten `vars` se che ca namespace §6.2 — kiem lai luc GHEP.

    `kiem_cay` tra ve som cho mot `Name` nam trong bang ham, nen mot ten trung
    se di qua cua kiem roi chet o cua tinh voi mot cau loi noi ve "gia tri".
    """
    assert not set(BANG_HAM) & set(NAMESPACE)
    assert not set(BANG_HAM) & set(HANG_SO_TEN)


def test_bang_ham_that_da_CAM_vao_phuong_ngu():
    """Cua vao cua ngon ngu phai mang CA 49 ten, khong phai bang rong."""
    assert set(NN.NGON_NGU.ham) == set(BANG_HAM)
    assert CS.DAY_DU.ham == {}, "`DAY_DU` van la phuong ngu bang RONG"


# ═══════════════════════════════════════════════════════════════════════════
#  2. Ten NGOAI bang: tu choi o TANG BO TINH
# ═══════════════════════════════════════════════════════════════════════════

NGOAI_BANG = ["eval('1')", "exec('1')", "__import__('os')", "open('x')",
              "getattr(vars, 'x')", "print(1)", "leng('a')", "Len('a')",
              "compile('1', 'x', 'eval')"]


@pytest.mark.parametrize("bt", NGOAI_BANG)
def test_ten_ngoai_bang_bi_tu_choi_o_CUA_KIEM(bt):
    with pytest.raises(LoiNgonNgu) as e:
        NN.tinh(bt, mt(vars={"x": 1}))
    assert "bang" in str(e.value) or "§6.3" in str(e.value)


@pytest.mark.parametrize("bt", NGOAI_BANG)
def test_ten_ngoai_bang_bi_tu_choi_o_TANG_BO_TINH(bt):
    """⭐ Goi THANG `tinh_cay`, bo qua `kiem_cay`.

    Cau hoi: neu mot duong nao do di thang vao bo tinh (hom nay `tinh_ngon_ngu`
    kiem truoc, ngay mai co the co mot duong khac), bo tinh co con canh khong?
    """
    cay = ast.parse(bt, mode="eval")
    with pytest.raises(LoiNgonNgu):
        CS.tinh_cay(cay, NN.NGON_NGU, mt(vars={"x": 1}))


def test_TIEM_LOI_bo_kiem_ten_ham_o_BO_TINH_thi_thoat_duoc():
    """🔑 TIEM LOI vao dung mot cho: cho bang ham nhan MOI ten.

    Neu phep kiem ten trong `tinh_cay` la trang tri thi hai nhanh duoi day cho
    cung ket qua. Chung phai KHAC nhau.
    """
    class _BangToang(dict):
        def __contains__(self, ten):        # moi ten deu "co trong bang"
            return True

        def __missing__(self, ten):
            return lambda *a: "THOAT"

    toang = dataclasses.replace(NN.NGON_NGU, ham=_BangToang(BANG_HAM))
    cay = ast.parse("eval('1')", mode="eval")

    # Voi bang toang: bo tinh KHONG con gi chan ⇒ ham la chay.
    assert CS.tinh_cay(cay, toang, mt()) == "THOAT"
    # Voi bang that: chinh phep kiem ay chan lai.
    with pytest.raises(LoiNgonNgu):
        CS.tinh_cay(cay, NN.NGON_NGU, mt())


def test_goi_phuong_thuc_cua_gia_tri_van_bi_cam():
    """`vars.s.upper()` — mot ham TRONG bang, goi nhu phuong thuc."""
    with pytest.raises(LoiNgonNgu):
        NN.tinh("vars.s.upper()", mt(vars={"s": "a"}))


def test_ham_dung_nhu_TEN_TRAN_khong_co_gia_tri():
    """`upper` tran di qua `kiem_cay` (no nam trong bang) va chet o `tinh_cay`.

    ⚠️ Ghim hanh vi nay vi no la mot **hau qua cua viec ghep**: truoc khi cam
       bang that vao, `upper` la mot ten khong ton tai; nay no la mot ten co
       nhung khong co GIA TRI. Hai cau loi khac nhau.
    """
    with pytest.raises(LoiNgonNgu) as e:
        NN.tinh("upper", mt())
    assert "gia tri" in str(e.value)


# ═══════════════════════════════════════════════════════════════════════════
#  3. Ham nem loi ⇒ loi CO CHO, khong ro kieu cua tang duoi
# ═══════════════════════════════════════════════════════════════════════════

HAM_NEM = [
    ("json_parse('{bad')", "json_parse"),
    ('to_number("khong phai so")', "to_number"),
    ('to_bool("co le")', "to_bool"),
    ("range(100000)", "range"),
    ('date_parse("khong phai ngay")', "date_parse"),
    ('sort_by([{"k": 1}], "thieu")', "sort_by"),
]


@pytest.mark.parametrize("bt,ten", HAM_NEM)
def test_ham_nem_thi_ra_LoiNgonNgu_chu_khong_phai_LoiHam(bt, ten):
    """⛔ `LoiHam` la lop loi cua TANG BANG. No ra toi nguoi goi nghia la
    nguoi goi phai biet ve mot tang khong phai hop dong cua minh.
    """
    with pytest.raises(LoiNgonNgu) as e:
        NN.tinh(bt, mt())
    assert not isinstance(e.value, LoiHam)
    assert ten in str(e.value), "cau loi phai noi ham nao nga"


def test_loi_cua_ham_mang_VI_TRI_va_NGUYEN_VAN():
    """§6.4: loi mang `vi_tri` (cot) + `bieu_thuc`. Loi tu ham cung vay."""
    with pytest.raises(LoiNgonNgu) as e:
        NN.tinh("1 + to_number('x')", mt())
    assert e.value.vi_tri == 4, "cot cua chinh loi goi ham"
    assert e.value.bieu_thuc == "1 + to_number('x')"


def test_loi_cua_ham_KHONG_ro_traceback():
    cau = ""
    try:
        NN.tinh("json_parse('{bad')", mt())
    except LoiNgonNgu as loi:
        cau = str(loi)
    assert cau
    for ro_ri in ("Traceback", "json.decoder", "JSONDecodeError", ".py\",",
                  "File \""):
        assert ro_ri not in cau, f"cau loi ro `{ro_ri}`: {cau}"


def test_TIEM_LOI_ham_hong_bat_thuong_van_khong_thoat_ra_kieu_la():
    """Mot ham trong bang nem mot ngoai le KHONG phai `LoiHam` (loi lap trinh,
    khong phai loi cua nguoi khai) van phai ra `LoiNgonNgu`.
    """
    def _no(_x):
        raise ZeroDivisionError("chi tiet noi bo")

    cs = dataclasses.replace(NN.NGON_NGU, ham={**BANG_HAM, "len": _no})
    with pytest.raises(LoiNgonNgu) as e:
        CS.tinh_ngon_ngu('len("a")', mt(), cs=cs)
    assert "chi tiet noi bo" not in str(e.value), \
        "ngoai le KHONG phai loi nguoi dung thi khong duoc dan nguyen van"
    assert "len" in str(e.value)


# ═══════════════════════════════════════════════════════════════════════════
#  4. Sai so tham so ⇒ loi ro, ⛔ khong `TypeError` tho
# ═══════════════════════════════════════════════════════════════════════════

SAI_THAM_SO = ["upper()", 'upper("a", "b")', "range()",
               'replace("a", "b")', 'get()', 'substring("abc", 1, 2, 3)']


@pytest.mark.parametrize("bt", SAI_THAM_SO)
def test_sai_so_tham_so_ra_loi_ngon_ngu_chu_khong_TypeError(bt):
    with pytest.raises(LoiNgonNgu) as e:
        NN.tinh(bt, mt())
    assert "tham so" in str(e.value)


def test_TypeError_TRONG_THAN_ham_khong_bi_goi_nham_la_sai_tham_so():
    """🔑 Phan biet hai hang loi ma Python goi chung mot ten.

    Neu phep hoi chu ky TRUOC khi goi bi bo di, mot `TypeError` sinh ra trong
    THAN ham se doi lot thanh "goi sai so tham so" — va nguoi khai di sua mot
    cho khong sai. Hai nhanh nay phai noi hai cau khac nhau.
    """
    def _no(_x):
        raise TypeError("loi ben trong than ham")

    cs = dataclasses.replace(NN.NGON_NGU, ham={**BANG_HAM, "len": _no})
    with pytest.raises(LoiNgonNgu) as e:
        CS.tinh_ngon_ngu('len("a")', mt(), cs=cs)
    assert "tham so" not in str(e.value)
    assert "len" in str(e.value)


def test_sai_so_tham_so_van_mang_vi_tri():
    with pytest.raises(LoiNgonNgu) as e:
        NN.tinh("1 + upper()", mt())
    assert e.value.vi_tri == 4


def test_tham_so_CO_TEN_van_bi_cam_voi_bang_that():
    with pytest.raises(LoiNgonNgu) as e:
        NN.tinh('substring("abc", bat_dau=1)', mt())
    assert "ten" in str(e.value)


# ═══════════════════════════════════════════════════════════════════════════
#  5. Ghep KHONG duoc mo rong nhung gi Task 3+5 da khoa
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("bt", [
    'len("a") + 1',            # so hoc tren ket qua ham
    'upper(vars.s)',           # doc namespace roi goi
    'len(nodes["b-2"].output.text)',
])
def test_ham_ghep_voi_namespace_van_chay(bt):
    NN.tinh(bt, mt(vars={"s": "a"},
                   nodes={"b-2": {"status": "SUCCEEDED",
                                  "output": {"text": "abc"}}}))


def test_ep_kieu_6_4_khong_bi_bang_ham_noi_long():
    with pytest.raises(LoiNgonNgu):
        NN.tinh('"1" + 1', mt())
    assert NN.tinh('"a" == 1', mt()) is False


def test_tran_ket_qua_van_ap_cho_gia_tri_DO_HAM_sinh_ra():
    """`range(1000)` qua duoc; mot chuoi khong lo do ham noi ra thi khong."""
    assert len(NN.tinh("range(1000)", mt())) == 1000
    with pytest.raises(LoiNgonNgu):
        NN.tinh('join(range(1000), vars.dai)',
                mt(vars={"dai": "x" * 2000}))


def test_NGHIEM_khong_bi_ghep_lam_ro_ra():
    """Hop dong `timeout_expr` khong thay doi vi mot bang ham o mo-dun khac."""
    from platform_core.workflow.bieu_thuc import LoiBieuThuc, tinh_bieu_thuc

    assert tinh_bieu_thuc("min(a, 10)", {"a": 3}) == 3
    with pytest.raises(LoiBieuThuc):
        tinh_bieu_thuc('upper("a")', {})
    with pytest.raises(LoiBieuThuc):
        tinh_bieu_thuc("len(a)", {"a": 3})


def test_min_sai_tham_so_o_NGHIEM_cung_khong_ra_TypeError():
    """⭐ `NGHIEM` co `ast.Call` va co `min`/`max` — nen no di qua CUNG mot
    doan ma. Mot `TypeError` tho o day la mot loi 500 tren duong `timeout_expr`.
    """
    from platform_core.workflow.bieu_thuc import LoiBieuThuc, tinh_bieu_thuc

    with pytest.raises(LoiBieuThuc):
        tinh_bieu_thuc("min()", {})
    with pytest.raises(LoiBieuThuc):
        tinh_bieu_thuc("min(a)", {"a": 3})


# ═══════════════════════════════════════════════════════════════════════════
#  6. Banh coc: khong ai duoc goi ngon ngu §6 voi bang ham RONG
# ═══════════════════════════════════════════════════════════════════════════

def test_BANH_COC_khong_module_nao_goi_tinh_ngon_ngu_ma_quen_bang_ham():
    """⛔ `tinh_ngon_ngu(bt, mt)` khong `cs=` ⇒ phuong ngu bang RONG: mot ngon
    ngu **im lang** tu choi ca 49 ham. Do la mot cong ma ben goi quen truyen
    la dong — va cho no dong ra thi khong ai nhin.

    Co hoc: doc AST cua ca kho, khong phai mot giao uoc trong docstring.
    """
    import pathlib

    goc = pathlib.Path(CS.__file__).resolve().parents[2]
    cho_phep = {"platform_core/workflow/chinh_sach.py",
                "platform_core/workflow/ngon_ngu.py"}
    vi_pham = []
    for thu_muc in ("platform_core", "apps", "server"):
        for tep in (goc / thu_muc).rglob("*.py"):
            duong = tep.relative_to(goc).as_posix()
            if duong in cho_phep:
                continue
            try:
                cay = ast.parse(tep.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for n in ast.walk(cay):
                if not isinstance(n, ast.Call):
                    continue
                ten = (n.func.id if isinstance(n.func, ast.Name)
                       else n.func.attr if isinstance(n.func, ast.Attribute)
                       else "")
                if ten not in ("tinh_ngon_ngu", "kiem_ngon_ngu"):
                    continue
                if not any(k.arg == "cs" for k in n.keywords):
                    vi_pham.append(f"{duong}:{n.lineno}")
    assert not vi_pham, ("goi ngon ngu §6 voi bang ham RONG: "
                         f"{vi_pham} — dung `ngon_ngu.tinh`/`ngon_ngu.kiem`")


# ═══════════════════════════════════════════════════════════════════════════
#  7. ⭐ CHO GHEP THAT SU VO: ham §6.3 nhan NAMESPACE §6.2
# ═══════════════════════════════════════════════════════════════════════════
#
# 🔴 Bon bai duoi day DO thuc su khi bang ham duoc cam vao bo tinh lan dau
#    (24/09). Hai nua deu dung theo hop dong cua rieng no:
#
#      `chinh_sach.py` (§6.2)  bay ra `Mapping` — doc lazily, cau loi rieng
#      `ham_bieu_thuc.py`      hoi `isinstance(x, dict)`
#
#    `Mapping` khong phai `dict`. Hai hau qua, va cai thu hai TE HON:
#
#      keys(vars)                    ⇒ "keys: can object, gap khong_ho_tro"
#      get(nodes.a.output, "text")   ⇒ **lang le** tra ve mac dinh
#
#    Va mot hau qua thu ba, tu `Mapping.__contains__` mac dinh (no goi
#    `self[khoa]` va chi bat `KeyError`):
#
#      get(nodes.a.output, "khong_co", 0)  ⇒ NEM, thay vi lui ve `0`
#
# ⛔ Khong phep kiem nao cua hai lan nhin thay duoc ba dieu nay: mot ben chi
#    co bang gia (`dict` thuan), ben kia chi co du lieu JSON thuan.

def _mt_nodes():
    return mt(nodes={"b-2": {"status": "SUCCEEDED",
                             "output": {"text": "abc", "so": 2}}},
              vars={"k": 1})


@pytest.mark.parametrize("bt,mong", [
    ('keys(nodes["b-2"].output)', ["text", "so"]),
    ('values(nodes["b-2"].output)', ["abc", 2]),
    ('len(nodes["b-2"].output)', 2),
    ('type_of(nodes["b-2"].output)', "object"),
    ('get(nodes["b-2"].output, "text")', "abc"),
    ('get(nodes["b-2"].output, "khong_co", "md")', "md"),
    ('merge(nodes["b-2"].output, {"them": 1})',
     {"text": "abc", "so": 2, "them": 1}),
    ('pick(nodes["b-2"].output, "so")', {"so": 2}),
    ('omit(nodes["b-2"].output, "so")', {"text": "abc"}),
    ('json_string(nodes["b-2"].output)', '{"text": "abc", "so": 2}'),
    ('to_string(nodes["b-2"].output)', '{"text": "abc", "so": 2}'),
    ('pluck([nodes["b-2"].output], "so")', [2]),
    ('sort_by([nodes["b-2"].output], "so")', [{"text": "abc", "so": 2}]),
    ('count(unique([nodes["b-2"].output, nodes["b-2"].output]))', 1),
    ("keys(vars)", ["k"]),
    ("type_of(vars)", "object"),
])
def test_ham_doc_duoc_NAMESPACE_chu_khong_chi_dict(bt, mong):
    assert NN.tinh(bt, _mt_nodes()) == mong


@pytest.mark.parametrize("bt", [
    'get(nodes["b-2"].output, "khong_co", 0)',
    'get(nodes["b-2"], "khong_co", 0)',
    'get(vars, "khong_co", 0)',
])
def test_get_lui_ve_MAC_DINH_chu_khong_nem_khi_doc_hut_namespace(bt):
    """`get` ton tai de doc du lieu CO THE VANG MAT. Mot `in` ma nem la mot
    cau tra loi bien thanh mot run FAILED.
    """
    assert NN.tinh(bt, _mt_nodes()) == 0


def test_doc_hut_o_cho_KHONG_phai_get_thi_van_NOI_RO():
    """⚠️ Khong duoc "sua" bang cach lam moi phep doc hut thanh im lang."""
    with pytest.raises(LoiNgonNgu) as e:
        NN.tinh('nodes["b-2"].output.khong_co', _mt_nodes())
    assert "khong_co" in str(e.value)


def test_ham_doc_node_CHUA_XONG_thi_cau_loi_cua_namespace_di_ra_nguyen():
    """Namespace §6.2 nem `LoiNgonNgu` voi cau viet cho nguoi khai. Cau do
    phai qua duoc lop boc goi ham, khong bien thanh "ham nga".
    """
    mt_dang_chay = mt(nodes={"b-2": {"status": "RUNNING", "output": {}}})
    with pytest.raises(LoiNgonNgu) as e:
        NN.tinh('keys(nodes["b-2"].output)', mt_dang_chay)
    assert "chua chay xong" in str(e.value)
