"""`vars` — trang thai workflow theo spec §6.5.

Nguyen van spec §6.5, ca doan:

    Khong co trang thai sua duoc dung chung. `vars` = gop output cua moi
    `core.set` la **to tien** cua node dang tinh, theo thu tu `graph.thu_tu`.
    Hai `core.set` ghi cung khoa ma khong co quan he to tien ⇒ validator tu
    choi (`ghi_bien_xung_dot`). ⇒ Tat dinh, khong khoa, khong can cot trang
    thai run.

⇒ Ba menh de do duoc, va tep nay do tung cai:

1. **gop theo TO TIEN** — mot `core.set` khong phai to tien khong dong gop gi;
2. **theo THU TU `graph.thu_tu`** — hai to tien cung khoa thi nguoi DI SAU
   thang (va ho co quan he to tien nen chuyen do tat dinh);
3. **xung dot chan o PUBLISH** — hai nguoi ghi cung khoa khong co quan he to
   tien la mot do thi ma ket qua phu thuoc thu tu chay ⇒ tu choi.

## ⛔ Tep nay KHONG phu

- **Khong phu node `core.set`** (P3). Hom nay `bien_dich` tu choi moi node
  `core.*` bang `loai_node_chua_ho_tro` — co mot phep kiem BANH COC duoi day
  ghim dung dieu do, de ngay P3 mo node ay ra thi cho nay do neu chua ai noi
  validator vao cong publish.
- Khong phu duong dong co: chua ai goi `gop_vars` luc chay (giong `vars`,
  `nodes`, `trigger` — ca §6.2 van chua duoc dong co nap).
"""
from __future__ import annotations

import pytest

from platform_core.workflow import bien_vars as BV
from platform_core.workflow import ngon_ngu as NN
from platform_core.workflow.bien_dich import LoiBienDich
from platform_core.workflow.chinh_sach import LoiNgonNgu, moi_truong_wf

#  a → b → c ; d roi (khong quan he to tien voi ai)
THU_TU = ["a", "b", "c", "d"]
TO_TIEN = {"a": set(), "b": {"a"}, "c": {"a", "b"}, "d": set()}


def xong(**cong):
    return {"status": "SUCCEEDED", "output": dict(cong)}


ANH_CHUP = {
    "a": xong(x=1, chung="tu_a"),
    "b": xong(y=2, chung="tu_b"),
    "c": xong(z=3),
    "d": xong(w=4),
}


def vars_cua(nid, *, anh_chup=None, thu_tu=None, to_tien=None,
             nguoi_ghi=("a", "b", "d")):
    return BV.gop_vars(anh_chup if anh_chup is not None else ANH_CHUP,
                       nguoi_ghi=nguoi_ghi,
                       to_tien=TO_TIEN[nid] if to_tien is None else to_tien,
                       thu_tu=THU_TU if thu_tu is None else thu_tu)


# ═══════════════════════════════════════════════════════════════════════════
#  1. Gop theo TO TIEN
# ═══════════════════════════════════════════════════════════════════════════

def test_chi_TO_TIEN_moi_dong_gop():
    """`d` ghi `w`, nhung `d` khong phai to tien cua `c` ⇒ `c` khong thay `w`."""
    assert dict(vars_cua("c")) == {"x": 1, "y": 2, "chung": "tu_b"}
    assert "w" not in vars_cua("c")


def test_node_dau_do_thi_thay_vars_RONG():
    assert dict(vars_cua("a")) == {}


def test_node_KHONG_ghi_thi_khong_dong_gop_du_la_to_tien():
    """`c` la to tien cua khong ai o day, va `c` khong nam trong `nguoi_ghi`:
    output cua mot node thuong KHONG duoc chay vao `vars`.
    """
    ra = BV.gop_vars(ANH_CHUP, nguoi_ghi=("a",), to_tien={"a", "b", "c"},
                     thu_tu=THU_TU)
    assert dict(ra) == {"x": 1, "chung": "tu_a"}


def test_TIEM_LOI_bo_loc_TO_TIEN_thi_ket_qua_doi():
    """🔑 Cho `to_tien` = MOI node (tuc bo luat to tien) ⇒ phai khac.

    Neu hai nhanh duoi day bang nhau thi phep loc to tien la trang tri.
    """
    that = dict(vars_cua("c"))
    khong_loc = dict(vars_cua("c", to_tien=set(THU_TU)))
    assert that != khong_loc
    assert khong_loc["w"] == 4 and "w" not in that


# ═══════════════════════════════════════════════════════════════════════════
#  2. Theo THU TU `graph.thu_tu`
# ═══════════════════════════════════════════════════════════════════════════

def test_hai_to_tien_cung_khoa_thi_NGUOI_DI_SAU_thang():
    assert vars_cua("c")["chung"] == "tu_b"


def test_TIEM_LOI_dao_thu_tu_thi_nguoi_thang_doi():
    """Thu tu la NGUON cua ket qua, khong phai trang tri."""
    dao = list(reversed(THU_TU))
    assert vars_cua("c", thu_tu=dao)["chung"] == "tu_a"


def test_nguoi_ghi_ngoai_thu_tu_la_LOI_chu_khong_bi_bo_qua():
    """⛔ Mot nguoi ghi khong co trong `thu_tu` thi khong xep duoc thu tu ⇒
    khong duoc im lang bo qua (bo qua la doi mot gia tri).
    """
    with pytest.raises(LoiNgonNgu):
        BV.gop_vars({**ANH_CHUP, "z9": xong(q=1)},
                    nguoi_ghi=("a", "z9"), to_tien={"a", "z9"},
                    thu_tu=THU_TU)


def test_gop_TAT_DINH():
    lan_1 = dict(vars_cua("c"))
    lan_2 = dict(vars_cua("c", nguoi_ghi=("d", "b", "a")))
    assert lan_1 == lan_2


# ═══════════════════════════════════════════════════════════════════════════
#  3. Nguoi ghi CHUA chay xong
# ═══════════════════════════════════════════════════════════════════════════

def test_nguoi_ghi_chua_SUCCEEDED_khong_dong_gop():
    anh = {**ANH_CHUP, "b": {"status": "RUNNING", "output": {}}}
    ra = vars_cua("c", anh_chup=anh)
    assert dict(ra) == {"x": 1, "chung": "tu_a"}


def test_doc_khoa_thieu_thi_NOI_RO_co_nguoi_ghi_dang_do():
    anh = {**ANH_CHUP, "b": {"status": "FAILED", "output": {}}}
    ra = vars_cua("c", anh_chup=anh)
    with pytest.raises(LoiNgonNgu) as e:
        ra["y"]
    assert "y" in str(e.value)
    assert "b" in str(e.value), "phai chi ra nguoi ghi chua chay xong"


def test_doc_khoa_chua_ai_ghi_thi_ke_ra_khoa_DANG_CO():
    with pytest.raises(LoiNgonNgu) as e:
        vars_cua("c")["khong_co"]
    assert "chung" in str(e.value) and "x" in str(e.value)


def test_khoa_bat_dau_gach_duoi_la_VO_HINH():
    """Cung luat voi `ham_bieu_thuc` va `_doc_khoa`: mot luat, moi cua."""
    anh = {**ANH_CHUP, "a": xong(x=1, _bi_mat="X")}
    ra = vars_cua("c", anh_chup=anh)
    assert "_bi_mat" not in ra
    assert "_bi_mat" not in list(ra)


# ═══════════════════════════════════════════════════════════════════════════
#  4. `vars` doc duoc TU TRONG NGON NGU §6
# ═══════════════════════════════════════════════════════════════════════════

def mt_c():
    return moi_truong_wf(vars=vars_cua("c"))


@pytest.mark.parametrize("bt,mong", [
    ("vars.x", 1),
    ('vars["x"]', 1),
    ("vars.x + 1", 2),
    ("vars.chung", "tu_b"),
    ("keys(vars)", ["x", "chung", "y"]),
    ('get(vars, "x", 0)', 1),
    ('is_null(get(vars, "w"))', True),
])
def test_doc_vars_qua_ngon_ngu(bt, mong):
    assert NN.tinh(bt, mt_c()) == mong


def test_doc_bien_khong_ton_tai_qua_ngon_ngu_mang_COT():
    with pytest.raises(LoiNgonNgu) as e:
        NN.tinh("1 + vars.khong_co", mt_c())
    assert e.value.vi_tri is not None
    assert e.value.bieu_thuc == "1 + vars.khong_co"


def test_KHONG_ghi_duoc_vao_vars_tu_bieu_thuc():
    """§6.5: *"Khong co trang thai sua duoc dung chung"*."""
    for bt in ("vars.x = 2", "vars['x'] = 2"):
        with pytest.raises(LoiNgonNgu):
            NN.tinh(bt, mt_c())
    NN.tinh("vars.x", mt_c())
    assert vars_cua("c")["x"] == 1


# ═══════════════════════════════════════════════════════════════════════════
#  5. XUNG DOT GHI — chan o PUBLISH (`ghi_bien_xung_dot`)
# ═══════════════════════════════════════════════════════════════════════════

def test_hai_nguoi_ghi_CUNG_KHOA_khong_quan_he_to_tien_bi_TU_CHOI():
    with pytest.raises(LoiBienDich) as e:
        BV.kiem_ghi_xung_dot({"b": ["chung"], "d": ["chung"]}, TO_TIEN)
    assert e.value.ma == "ghi_bien_xung_dot"
    assert "chung" in str(e.value)
    assert "b" in str(e.value) and "d" in str(e.value)


def test_hai_nguoi_ghi_cung_khoa_CO_quan_he_to_tien_thi_duoc():
    BV.kiem_ghi_xung_dot({"a": ["chung"], "b": ["chung"]}, TO_TIEN)


def test_khoa_ROI_NHAU_thi_khong_quan_he_cung_duoc():
    BV.kiem_ghi_xung_dot({"b": ["y"], "d": ["w"]}, TO_TIEN)


def test_ba_nguoi_ghi_bat_duoc_dung_CAP_xung_dot():
    with pytest.raises(LoiBienDich) as e:
        BV.kiem_ghi_xung_dot({"a": ["k"], "b": ["k"], "d": ["k"]}, TO_TIEN)
    assert "d" in str(e.value)


def test_TIEM_LOI_bo_hieu_biet_to_tien_thi_cap_HOP_LE_cung_do():
    """🔑 Neu `kiem_ghi_xung_dot` khong THAT SU doc `to_tien` thi cap `a`/`b`
    (co quan he to tien) va cap `b`/`d` (khong) se cho cung ket qua.
    """
    BV.kiem_ghi_xung_dot({"a": ["k"], "b": ["k"]}, TO_TIEN)    # hop le
    with pytest.raises(LoiBienDich):
        BV.kiem_ghi_xung_dot({"a": ["k"], "b": ["k"]}, {"a": set(), "b": set()})


def test_cau_loi_TAT_DINH_khong_phu_thuoc_thu_tu_dict():
    cau = []
    for ghi in ({"d": ["k"], "b": ["k"]}, {"b": ["k"], "d": ["k"]}):
        with pytest.raises(LoiBienDich) as e:
            BV.kiem_ghi_xung_dot(ghi, TO_TIEN)
        cau.append(str(e.value))
    assert cau[0] == cau[1]


# ═══════════════════════════════════════════════════════════════════════════
#  6. BANH COC: ngay `core.set` bien dich duoc thi validator phai duoc NOI VAO
# ═══════════════════════════════════════════════════════════════════════════

def test_BANH_COC_core_set_chua_bien_dich_duoc_va_cong_publish_chua_noi():
    """⚠️ Phep kiem nay dang do mot su VANG MAT, va no noi ra dieu do.

    Hom nay `core.set` la node dieu khien cua P3: `bien_dich` tu choi moi loai
    ngoai `tool`/`app.*`. Nen `kiem_ghi_xung_dot` **chua co duong publish nao
    di qua** — noi no vao `bien_dich` bay gio la dung mot cai cong khong ai di
    qua, va cong do khong ai nhin.

    ⇒ Banh coc: ngay P3 mo `core.set` ra, ve trai thanh sai, va bai nay bat
      nguoi mo phai noi validator vao cong publish.
    """
    import ast
    import pathlib

    from platform_core.workflow import bien_dich as BD

    doc = {"pages": [{"id": "p1", "nodes": [
        {"id": "s1", "type": "core.set", "params": {"x": 1}}], "edges": []}]}
    try:
        BD.bien_dich(doc, cong_cu={})
        core_set_bien_dich_duoc = True
    except LoiBienDich as loi:
        core_set_bien_dich_duoc = loi.ma != "loai_node_chua_ho_tro"

    nguon = pathlib.Path(BD.__file__).read_text(encoding="utf-8")
    da_noi = "kiem_ghi_xung_dot" in {
        n.func.attr if isinstance(n.func, ast.Attribute) else
        n.func.id if isinstance(n.func, ast.Name) else ""
        for n in ast.walk(ast.parse(nguon)) if isinstance(n, ast.Call)}

    if core_set_bien_dich_duoc:
        assert da_noi, ("`core.set` da bien dich duoc ⇒ `bien_dich` PHAI goi "
                        "`bien_vars.kiem_ghi_xung_dot` (spec §6.5), neu khong "
                        "mot do thi co xung dot ghi bien se publish duoc")
    else:
        assert not da_noi, ("`core.set` chua bien dich duoc ma cong publish da "
                            "goi validator — mot cai cong khong ai di qua")
