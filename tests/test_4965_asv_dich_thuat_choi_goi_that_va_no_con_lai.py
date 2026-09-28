"""B17 §4.1, lan P0-a3 — CHOT ai la CHO GOI THAT cua `vuot_tran_theo_nguon` /
`tran_do_dai_theo_nguon`, va khai NO CON LAI (§0b: "lan tu khai no -> mo lan
tra no NGAY").

⭐ Day la thuoc cho bay o `test_2018` (doc lai o brief P0-a3): mot bai kiem
xanh tren mot ham KHONG CON AI GOI thi vo nghia. Bai nay quet TOAN BO
`apps/auto_scan_video/*.py` (⛔ khong doan tu tri nho — [[liet-ke-tu-tri-nho-
thay-vi-dem]]) de chung minh `giai_doan_noi_dung.chay` la CHO GOI SAN XUAT
DUY NHAT, roi doc AST ngay tai cho goi do de ghi lai — TRUNG THUC — no da mang
`toc_doc_giong` hay chua.

🔴 **No con lai (khai thang, dung format §0b):** `giai_doan_noi_dung.py:~435`
goi `dich_thuat.vuot_tran_theo_nguon(...)` NHUNG ⛔ chua truyen `toc_doc_giong=
ho_so.get("toc_doc_giong")` du `ho_so` da co san trong pham vi `chay()` (gan o
dong 263, cung bien da dung cho `long_tieng.loi_nhac(ho_so=ho_so)` o P0-a2).
Noi day la MOT dong o `giai_doan_noi_dung.py` — file ⛔ NGOAI pham vi so huu
cua P0-a3 (chi `dich_thuat.py`). Bai `test_khai_no_CHUA_NOI...` duoi day PIN
trang thai nay: no se DO khi ai do noi day (hoac am tham gay lai) — dung y,
vi day la cach duy nhat bat mot thay doi ⛔ khong ai cap nhat lai bao cao lan
nay va cac tai lieu tham chieu no.
"""
from __future__ import annotations

import ast
import pathlib

APPS = pathlib.Path(__file__).resolve().parent.parent / "apps" / "auto_scan_video"


def _cay(tep: pathlib.Path) -> ast.Module:
    return ast.parse(tep.read_text(encoding="utf-8"), filename=str(tep))


def _goi_toi(cay: ast.Module, ten_thuoc_tinh: str) -> list[ast.Call]:
    """Moi `ast.Call` dang `<gi_do>.<ten_thuoc_tinh>(...)` trong `cay`."""
    ra = []
    for node in ast.walk(cay):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == ten_thuoc_tinh):
            ra.append(node)
    return ra


def _ham_bao_quanh(cay: ast.Module, node_muc_tieu: ast.Call) -> str | None:
    """Ten `FunctionDef` gan nhat bao quanh `node_muc_tieu`, hoac None."""
    for ham in ast.walk(cay):
        if not isinstance(ham, ast.FunctionDef):
            continue
        if any(n is node_muc_tieu for n in ast.walk(ham)):
            return ham.name
    return None


def test_giai_doan_noi_dung_la_CHO_GOI_SAN_XUAT_DUY_NHAT_cua_vuot_tran_theo_nguon():
    """Quet CA THU MUC — ⛔ khong chi mot tep doan truoc — de ⛔ khong bo sot
    mot cho goi thu hai da xuat hien tu lan sau."""
    cho_goi = {}  # {ten_tep: [ten_ham_bao_quanh, ...]}
    for tep in sorted(APPS.glob("*.py")):
        if tep.name == "dich_thuat.py":
            continue  # dinh nghia, khong phai cho GOI
        cay = _cay(tep)
        goi = _goi_toi(cay, "vuot_tran_theo_nguon")
        if goi:
            cho_goi[tep.name] = [_ham_bao_quanh(cay, g) for g in goi]

    assert cho_goi == {"giai_doan_noi_dung.py": ["chay"]}, (
        f"tap cho goi vuot_tran_theo_nguon da doi: {cho_goi!r} — cap nhat lai "
        "test nay VA bao cao lan P0-a3 (chot 'ai goi tren duong chay that')")


def test_dich_thuat_py_la_TEP_DUY_NHAT_goi_truc_tiep_tran_do_dai_theo_nguon():
    """Ngoai chinh `dich_thuat.py` (noi bo, `vuot_tran_theo_nguon` goi
    `tran_do_dai_theo_nguon`), ⛔ khong tep san xuat nao khac goi thang ham
    nay — cua PHAT HIEN N5 CHI di qua `vuot_tran_theo_nguon`."""
    for tep in sorted(APPS.glob("*.py")):
        if tep.name == "dich_thuat.py":
            continue
        cay = _cay(tep)
        goi = _goi_toi(cay, "tran_do_dai_theo_nguon")
        assert not goi, (
            f"{tep.name} goi thang tran_do_dai_theo_nguon — vuot_tran_theo_"
            "nguon khong con la cua PHAT HIEN DUY NHAT, chot lai pham vi bai "
            "nay")


def test_khai_no_CHUA_NOI__giai_doan_noi_dung_chua_truyen_toc_doc_giong():
    """🔴 PIN trang thai NO hom nay (28/09, P0-a3). Doc AST DUNG tai cho goi
    that trong `giai_doan_noi_dung.py`.

    ⚠️ Bai nay CO Y do MOT dieu KHONG mong muon (thieu tu khoa) — day KHONG
    phai mot bat bien san pham, ma la mot moc ghi lai NO. Neu bai nay DO vi
    `toc_doc_giong=` da xuat hien o cho goi, do la TIN VUI (no da duoc tra) —
    xoa/sua lai bai nay thanh khang dinh THUAN (co mang tham so) thay vi coi
    do la mot hong hoc.
    """
    tep = APPS / "giai_doan_noi_dung.py"
    cay = _cay(tep)
    cac_goi = _goi_toi(cay, "vuot_tran_theo_nguon")
    assert len(cac_goi) == 1, (
        f"ky vong DUNG MOT cho goi vuot_tran_theo_nguon trong {tep.name}, "
        f"thay {len(cac_goi)} — cap nhat lai bai nay theo hinh dang moi")
    goi = cac_goi[0]
    mang_toc_doc_giong = any(kw.arg == "toc_doc_giong" for kw in goi.keywords)
    assert mang_toc_doc_giong is False, (
        "giai_doan_noi_dung.py GIO DA truyen toc_doc_giong cho "
        "vuot_tran_theo_nguon — NO CON LAI cua P0-a3 da duoc tra! Cap nhat "
        "lai bai nay (doi thanh khang dinh True) va bao cao lan da noi day "
        "chuoi toc_doc_giong HOAN TAT.")
