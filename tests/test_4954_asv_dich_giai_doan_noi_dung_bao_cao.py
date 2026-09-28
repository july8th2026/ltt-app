"""B14/V3 — bao cao cua `giai_doan_noi_dung.chay`: khoa `"muc"` (khong phai
`"doan"`) + ba khoa PHAT HIEN moi (N4/N5/N6) that su toi `outputs`.

🔴 **Ban sua mot bug SONG (khong phai gia dinh) tim thay khi lam N4/N5/N6.**
`tai_lieu` (ket qua `long_tieng.dung()`) tra ve khoa `"muc"` (xem
`long_tieng.py:595`, va `van_ban.py`/`long_tieng.kiem`/`long_tieng.tom_tat` deu
doc `"muc"`) — KHONG bao gio co khoa `"doan"`. Truoc ban sua nay,
`giai_doan_noi_dung.chay` doc `tai_lieu.get("doan")`, luon tra `[]`, nen
`so_doan_han_lot`/`ti_le_han_lot`/`doan_han_lot` trong `tom_tat` LUON la
0/None/None du danh dau per-doan (`AsvWorkItem.outputs["han_lot"]`) van dung —
dung hinh dang "so dung nhung gan cho SAI KHOA". Khong bo test nao bat duoc vi
`test_4894` chi kiem `long_tieng.chu_han_lot()` doc lap, chua tung kiem duong
bao cao nay dau-cuoi.

Cac phep kiem duoi neo vao AST (CHO GOI/CHO TRA VE that su), dung quy uoc da co
cua `test_408_asv_dich_thuat.py::_dict_tom_tat_tai_return`/`_khoa_chuoi` —
⛔ khong doan tu van ban ma nguon, va ⛔ khong can chay ca chuoi CSDL/hang doi
(tiet kiem thoi gian, vi ba cua nay la CUA PHAT HIEN thuan tuy, khong dung
so cai/trang thai).
"""
from __future__ import annotations

import ast
import inspect

from apps.auto_scan_video import giai_doan_noi_dung
from tests.test_408_asv_dich_thuat import _dict_tom_tat_tai_return, _khoa_chuoi


def _cac_goi_thuoc_tinh(mo_dun_hoac_ham) -> list[ast.Call]:
    cay = ast.parse(inspect.getsource(mo_dun_hoac_ham))
    return [n for n in ast.walk(cay)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]


def test_KHONG_con_doc_tai_lieu_get_doan__bug_da_sua():
    """Neo dung CHO GOI: khong con loi goi `<gi_do>.get("doan")` nao trong
    `chay` — mau `.get("doan")` la dung hinh dang cua bug (khoa sai)."""
    cac = _cac_goi_thuoc_tinh(giai_doan_noi_dung.chay)
    goi_get_doan = [
        c for c in cac
        if c.func.attr == "get" and c.args
        and isinstance(c.args[0], ast.Constant) and c.args[0].value == "doan"
        # `goc.get("doan")`/`giu.get("doan")` la HOP LE — do la ban ghi/ban
        # long tieng THUONG (khoa "doan" that), khac han `tai_lieu` (khoa
        # "muc"). Chi cam `tai_lieu.get("doan")` cu the.
        and isinstance(c.func.value, ast.Name) and c.func.value.id == "tai_lieu"]
    assert not goi_get_doan, (
        "`giai_doan_noi_dung.chay` van con `tai_lieu.get(\"doan\")` — "
        "`tai_lieu` chi co khoa \"muc\" (xem long_tieng.dung), day la bug")


def test_doc_tai_lieu_muc_de_tinh_han_lot():
    cac = _cac_goi_thuoc_tinh(giai_doan_noi_dung.chay)
    goi_get_muc = [
        c for c in cac
        if c.func.attr == "get" and c.args
        and isinstance(c.args[0], ast.Constant) and c.args[0].value == "muc"
        and isinstance(c.func.value, ast.Name) and c.func.value.id == "tai_lieu"]
    assert goi_get_muc, "khong thay `tai_lieu.get(\"muc\")` — khoa dung phai la 'muc'"


def test_tom_tat_mang_du_ba_khoa_PHAT_HIEN_N4_N5_N6():
    d = _dict_tom_tat_tai_return(giai_doan_noi_dung)
    khoa = _khoa_chuoi(d)
    can = {"so_doan_phinh_bia", "doan_phinh_bia",
           "so_doan_vuot_tran_nguon", "doan_vuot_tran_nguon",
           "so_doan_gop_cau_nghi_ngo", "doan_gop_cau_nghi_ngo"}
    thieu = can - khoa
    assert not thieu, f"tom_tat cua giai_doan_noi_dung.chay thieu khoa {thieu}"
    # Han lot van con nguyen (khong bi dam trong luc them khoa moi).
    assert {"so_doan_han_lot", "ti_le_han_lot", "doan_han_lot"} <= khoa


def _outputs_dict_cua_danh_dau_xong(mo_dun) -> ast.Dict:
    """Dict truyen cho tham so `outputs=` trong loi goi `su_dung.danh_dau_xong`
    O TRONG VONG LAP CHINH (khong phai o cho khac)."""
    cay = ast.parse(inspect.getsource(mo_dun.chay))
    for n in ast.walk(cay):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "danh_dau_xong"):
            continue
        for kw in n.keywords:
            if kw.arg == "outputs" and isinstance(kw.value, ast.Dict):
                return kw.value
    raise AssertionError("khong thay loi goi danh_dau_xong(outputs={...})")


def test_moi_item_danh_dau_xong_mang_ba_co_PHAT_HIEN():
    d = _outputs_dict_cua_danh_dau_xong(giai_doan_noi_dung)
    khoa = _khoa_chuoi(d)
    can = {"phinh_bia", "vuot_tran_nguon", "gop_cau_nghi_ngo", "han_lot"}
    thieu = can - khoa
    assert not thieu, (
        f"outputs cua danh_dau_xong (per-doan) thieu co PHAT HIEN {thieu}")


def test_dich_thuat_duoc_import_va_dung_that_su():
    """Chong "khai bao ma khong dung": `dich_thuat` phai xuat hien trong CHO
    GOI that su (khong chi trong import) cua `chay`."""
    cac = _cac_goi_thuoc_tinh(giai_doan_noi_dung.chay)
    goi_dich_thuat = [
        c for c in cac
        if isinstance(c.func.value, ast.Name) and c.func.value.id == "dich_thuat"]
    ten_ham = {c.func.attr for c in goi_dich_thuat}
    assert {"cau_dich_phinh_bia", "vuot_tran_theo_nguon",
            "danh_dau_gop_cau"} <= ten_ham
