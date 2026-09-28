"""B17 §4.1, lan P0-a3 — AST: CHOT cho GOI THAT mang `toc_doc_giong`.

⭐ Doc AST thay vi doan tu hanh vi (bai hoc
[[fixture-tu-dung-tien-de-ma-san-pham-khong-co]]): mot bai do HANH VI co the
xanh vi trung con so o mot nhanh khac, ⛔ khong chung minh DAY DA NOI. Bai nay
doc truc tiep cay cu phap cua `apps/auto_scan_video/dich_thuat.py` va chot hai
lien ket GOI:

    tran_do_dai_theo_nguon()  --goi--> ngon_ngu.ngan_sach_do_dai(toc_doc_giong=...)
    vuot_tran_theo_nguon()    --goi--> tran_do_dai_theo_nguon(toc_doc_giong=...)

Day CHINH XAC la hai cho P0-a3 duoc giao noi (xem lai brief: "Con MOT cho goi
nua chua noi: dich_thuat.py:374"). ⛔ Khong AST-chot `giai_doan_noi_dung.py`:
tep do NGOAI pham vi so huu cua lan nay (chi `dich_thuat.py`) va la NO CON LAI
— xem `test_4965`.
"""
from __future__ import annotations

import ast
import inspect

from apps.auto_scan_video import dich_thuat


def _goi_mang_tu_khoa(cay_ham: ast.FunctionDef, ten_ham_goi: str,
                       ten_tu_khoa: str) -> bool:
    """True neu THAN ham `cay_ham` co mot `ast.Call` toi ham co ten cuoi
    (`.attr` hoac `.id`) khop `ten_ham_goi`, va cuoc goi ay mang mot
    `keyword` co `arg == ten_tu_khoa`."""
    for node in ast.walk(cay_ham):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        ten = func.attr if isinstance(func, ast.Attribute) else (
            func.id if isinstance(func, ast.Name) else None)
        if ten != ten_ham_goi:
            continue
        if any(kw.arg == ten_tu_khoa for kw in node.keywords):
            return True
    return False


def _tim_ham(cay: ast.Module, ten: str) -> ast.FunctionDef:
    for node in ast.walk(cay):
        if isinstance(node, ast.FunctionDef) and node.name == ten:
            return node
    raise AssertionError(f"khong tim thay ham {ten!r} trong dich_thuat.py")


def _cay_dich_thuat() -> ast.Module:
    nguon = inspect.getsource(dich_thuat)
    return ast.parse(nguon)


def test_AST_tran_do_dai_theo_nguon_GOI_ngan_sach_do_dai_mang_toc_doc_giong():
    cay = _cay_dich_thuat()
    ham = _tim_ham(cay, "tran_do_dai_theo_nguon")
    assert _goi_mang_tu_khoa(ham, "ngan_sach_do_dai", "toc_doc_giong"), (
        "tran_do_dai_theo_nguon KHONG chuyen tiep toc_doc_giong xuong "
        "ngon_ngu.ngan_sach_do_dai — day la CHINH cho goi P0-a3 duoc giao noi "
        "(dich_thuat.py:374 nguyen ban)")


def test_AST_vuot_tran_theo_nguon_GOI_tran_do_dai_theo_nguon_mang_toc_doc_giong():
    cay = _cay_dich_thuat()
    ham = _tim_ham(cay, "vuot_tran_theo_nguon")
    assert _goi_mang_tu_khoa(ham, "tran_do_dai_theo_nguon", "toc_doc_giong"), (
        "vuot_tran_theo_nguon KHONG chuyen tiep toc_doc_giong xuong "
        "tran_do_dai_theo_nguon — cua PHAT HIEN N5 se KHONG BAO GIO nhan duoc "
        "gia tri giong that du ben goi ngoai co truyen")


def test_AST_chu_ky_ham_co_tham_so_toc_doc_giong_mac_dinh_None():
    """Chu ky, khong chi than ham: `toc_doc_giong` phai la tu-khoa-rieng, mac
    dinh `None` — giu HANH VI HOM NAY khong doi cho MOI ben goi cu chua sua
    (hop dong tuong thich nguoc, ⛔ khong phai tinh co)."""
    for ten in ("tran_do_dai_theo_nguon", "vuot_tran_theo_nguon"):
        chu_ky = inspect.signature(getattr(dich_thuat, ten))
        tham_so = chu_ky.parameters.get("toc_doc_giong")
        assert tham_so is not None, f"{ten} thieu tham so toc_doc_giong"
        assert tham_so.kind == inspect.Parameter.KEYWORD_ONLY, (
            f"{ten}.toc_doc_giong phai la keyword-only (nhat quan voi "
            "ngon_ngu.ngan_sach_do_dai)")
        assert tham_so.default is None, (
            f"{ten}.toc_doc_giong phai mac dinh None de ben goi cu khong doi "
            "hanh vi")
