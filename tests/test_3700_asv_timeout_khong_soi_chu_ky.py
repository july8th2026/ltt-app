"""test_3700 — `timeout_xau_nhat` KHONG duoc soi chu ky ham bang `inspect`.

🔴 VI SAO TEP NAY TON TAI (N-52, 25/09). `ai.timeout_xau_nhat()` tung doc
   timeout mac dinh cua `dieu_phoi.goi` bang
   `inspect.signature(dieu_phoi.goi).parameters["timeout_s"].default` — dung Y
   "mot so, mot cho khai" nhung SAI CHO: chu ky ham la thu fixture/wrapper/mock
   THAY duoc. Mot fixture E2E that (`tests/fixtures/asv_e2e.py::dat_cua_model`)
   da thay `dieu_phoi.goi` bang mot ham THIEU tham so `timeout_s` -> `KeyError`
   giua luot chay THAT, chan ca dây chuyen o giai doan dau tien goi AI.

   Ban sua: ha hang so ra `dieu_phoi.TIMEOUT_GOI_MAC_DINH`, doc THANG, bo hoan
   toan `inspect`. Sau ban sua, thay `dieu_phoi.goi` bao nhieu lan cung khong
   con anh huong toi `timeout_xau_nhat` — khong con gi de soi.

⭐ Hai tang, co y: mot phep kiem HANH VI (`test_434` da co, goi ham that voi
   `dieu_phoi.goi` bi thay, kiem khong nem) va mot BANH COC AST o day (dong
   `inspect.signature`/`inspect.getfullargspec` khong con nam trong ham). Tang
   hanh vi bat duoc "gia tri sai"; tang AST bat duoc "ai do them lai `inspect`
   theo mot duong khac roi vay quanh no bang try/except" — mot phep kiem CHAY
   DUOC khong chung minh duoc dieu do, vi mot ban vai co the vo tinh khong
   nem loi trong MOT lan chay ma van con giòn ve nguyen tac.
"""
from __future__ import annotations

import ast
import inspect
import pathlib

from apps.auto_scan_video import ai

NGUON = pathlib.Path(ai.__file__)


def _dinh_nghia_ham(cay: ast.Module, ten: str) -> ast.FunctionDef:
    for node in ast.walk(cay):
        if isinstance(node, ast.FunctionDef) and node.name == ten:
            return node
    raise AssertionError(f"khong tim thay dinh nghia ham {ten!r} trong {NGUON}")


def _goi_ten_day_du(node: ast.Call) -> str:
    """`a.b.c(...)` -> `"a.b.c"`. Rong neu khong doc duoc (vd goi qua bien)."""
    phan = []
    hien = node.func
    while isinstance(hien, ast.Attribute):
        phan.append(hien.attr)
        hien = hien.value
    if isinstance(hien, ast.Name):
        phan.append(hien.id)
    else:
        return ""
    return ".".join(reversed(phan))


def test_timeout_xau_nhat_KHONG_soi_chu_ky_bang_inspect():
    """`inspect.signature`/`inspect.getfullargspec` khong duoc xuat hien
    trong than ham `timeout_xau_nhat` — banh coc AST, doc ma khong chay ham."""
    cay = ast.parse(NGUON.read_text(encoding="utf-8"), filename=str(NGUON))
    ham = _dinh_nghia_ham(cay, "timeout_xau_nhat")

    cac_goi_soi_chu_ky = []
    for node in ast.walk(ham):
        if not isinstance(node, ast.Call):
            continue
        ten = _goi_ten_day_du(node)
        if ten in {"inspect.signature", "inspect.getfullargspec",
                   "inspect.getargspec"}:
            cac_goi_soi_chu_ky.append(ten)

    assert not cac_goi_soi_chu_ky, (
        f"timeout_xau_nhat van soi chu ky ham ({cac_goi_soi_chu_ky}) — dung "
        "`dieu_phoi.TIMEOUT_GOI_MAC_DINH` truc tiep, dung soi chu ky ham (N-52): "
        "chu ky la thu fixture/wrapper/mock thay duoc, hang so thi khong.")


def test_dieu_phoi_co_hang_so_TIMEOUT_GOI_MAC_DINH_va_goi_dung_no():
    """Hang so ton tai va la MAC DINH thuc su cua `goi(timeout_s=...)` —
    doi xung voi phep AST o tren: co cho de doc THAT, khong chi la thieu inspect."""
    from platform_core.llm import dieu_phoi

    assert hasattr(dieu_phoi, "TIMEOUT_GOI_MAC_DINH")
    moi = inspect.signature(dieu_phoi.goi).parameters["timeout_s"].default
    assert moi == dieu_phoi.TIMEOUT_GOI_MAC_DINH, (
        "default cua tham so timeout_s lech khoi hang so cong khai — hai cho "
        "khai mot dieu (N-24 family)")


def test_ai_py_KHONG_con_import_inspect_o_muc_module_cho_viec_nay():
    """`timeout_xau_nhat` tu import `inspect` cuc bo (khong con dung) —
    banh coc phu: dam bao `inspect` khong bi keo len muc module chi de dung lai."""
    cay = ast.parse(NGUON.read_text(encoding="utf-8"), filename=str(NGUON))
    ham = _dinh_nghia_ham(cay, "timeout_xau_nhat")
    import_trong_ham = [n for n in ast.walk(ham) if isinstance(n, ast.Import)]
    ten_import = {a.name for node in import_trong_ham for a in node.names}
    assert "inspect" not in ten_import, (
        "timeout_xau_nhat khong con can `import inspect` — con dong do la dau "
        "hieu ban sua chua don sach het")
