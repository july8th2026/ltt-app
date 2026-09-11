"""INV-02: chỉ `lan_ngon_ngu` được phán về làn — và danh sách làn chỉ có một bản.

Đọc CÂY CÚ PHÁP, không khớp chuỗi — xem [[bo-do-quet-van-ban-trung-phat-viec-giai-thich]]:
một phép quét văn bản sẽ báo động trên chính chú thích giải thích nó.
"""
from __future__ import annotations

import ast
import pathlib

GOC = pathlib.Path(__file__).resolve().parents[1]
APP = GOC / "apps" / "ltt_voice"
THAM_QUYEN = APP / "lan_ngon_ngu.py"

#: Tên của chính sách làn thứ hai (nhánh GUI MVP, SC-1). Bỏ ở RC1; không được mọc lại.
BIA_MO = {"xung_dot", "cau_xung_dot", "_chan_xung_dot_lan", "_MAU_XUNG_DOT"}
MA_LOI = {"voice_language_mismatch", "voice_language_unknown"}


def _cac_tep():
    return [p for p in APP.rglob("*.py") if "__pycache__" not in p.parts]


def _cay(p):
    return ast.parse(p.read_text(encoding="utf-8"))


def test_doi_chung_phep_quet_THAY_duoc_tham_quyen():
    ten = {n.func.id for n in ast.walk(_cay(THAM_QUYEN))
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "PhanQuyet" in ten, "phep quet khong thay chinh tham quyen — no dang xanh-rong"


def test_chi_lan_ngon_ngu_DUNG_PhanQuyet():
    sai = []
    for p in _cac_tep():
        if p == THAM_QUYEN:
            continue
        for n in ast.walk(_cay(p)):
            if (isinstance(n, ast.Call) and getattr(n.func, "id", "") == "PhanQuyet") or (
                    isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "PhanQuyet"):
                sai.append(f"{p.relative_to(GOC)}:{n.lineno}")
    assert not sai, f"phan quyet lan dung ngoai tham quyen: {sai}"


def test_ma_loi_lan_chi_GO_o_tham_quyen():
    sai = []
    for p in _cac_tep():
        if p == THAM_QUYEN:
            continue
        for n in ast.walk(_cay(p)):
            if isinstance(n, ast.Constant) and n.value in MA_LOI:
                sai.append(f"{p.relative_to(GOC)}:{n.lineno} {n.value}")
    assert not sai, f"go lai ma loi lan thay vi dung hang so: {sai}"


def test_chinh_sach_lan_thu_hai_KHONG_moc_lai():
    sai = []
    for p in _cac_tep():
        for n in ast.walk(_cay(p)):
            ten = (getattr(n, "name", None) if isinstance(n, (ast.FunctionDef, ast.ClassDef))
                   else getattr(n, "id", None) if isinstance(n, ast.Name) else None)
            if ten in BIA_MO:
                sai.append(f"{p.relative_to(GOC)}:{n.lineno} {ten}")
    assert not sai, f"SC-1 moc lai: {sai}"


def test_cap_vi_en_KHONG_go_lai_ngoai_tham_quyen():
    sai = []
    for p in _cac_tep():
        if p == THAM_QUYEN:
            continue
        for n in ast.walk(_cay(p)):
            if isinstance(n, (ast.Tuple, ast.List, ast.Set)):
                gt = {e.value for e in n.elts if isinstance(e, ast.Constant)}
                if {"vi", "en"} <= gt:
                    sai.append(f"{p.relative_to(GOC)}:{n.lineno}")
    assert not sai, f"danh sach lan go lai (dung lan_ngon_ngu.LAN_HOP_LE): {sai}"
