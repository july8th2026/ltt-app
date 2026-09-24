"""Ranh gioi cua cong noi bo: khong biet giai doan, khong cong khai, mot duong.

Doc bang AST/van ban — khong import app de tra loi cau hoi ve ma nguon.
"""
from __future__ import annotations

import ast
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
APP = GOC / "apps" / "auto_scan_video"


def _cay(ten: str) -> ast.Module:
    return ast.parse((APP / ten).read_bytes().decode("utf-8"))


def _module_da_import(cay: ast.AST) -> set[str]:
    ra: set[str] = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.ImportFrom):
            goc = ("." * n.level) + (n.module or "")
            if n.level and not n.module:
                ra |= {"." + a.name for a in n.names}
            else:
                ra.add(goc)
        elif isinstance(n, ast.Import):
            ra |= {a.name for a in n.names}
    return ra


#: Dung MOT danh sach nay: cong chi duoc noi voi tang DICH VU.
DUOC_IMPORT = {"__future__", "dataclasses", "typing", "platform_core",
               "platform_core.i18n", "platform_core.storage",
               ".dich_vu_tao", ".features", ".quan_sat", ".pipeline", ".tables"}


def test_cong_KHONG_import_giai_doan_engine_hay_ffmpeg():
    """⛔ Nguoi goi khong goi giai doan/Voice/VLM/FFmpeg — va chinh cong cung khong."""
    dung = _module_da_import(_cay("cong_noi_bo.py"))
    la = dung - DUOC_IMPORT
    assert not la, f"cong_noi_bo import ngoai tang dich vu: {sorted(la)}"


def test_TEN_CONG_ton_tai_va_du_nam_ham():
    import apps.auto_scan_video.cong_noi_bo as cong

    for ten in cong.TEN_CONG:
        assert hasattr(cong, ten), ten
    assert {"submit_run", "get_status", "cancel_run", "retry_run",
            "get_result"} <= set(cong.TEN_CONG)


def test_KHONG_cong_khai_khong_api_v1_khong_toolspec_khong_route():
    van_inv = (GOC / "server" / "api" / "inventory.py").read_bytes().decode("utf-8")
    assert "cong_noi_bo" not in van_inv and "auto_scan_video" not in van_inv
    # Khong ToolSpec, khong ban khai be mat (chua co nguoi goi that).
    for ten in ("manifest.py", "__init__.py"):
        assert "cong_noi_bo" not in (APP / ten).read_bytes().decode("utf-8"), ten
    # Khong route HTTP nao boc cong (route goi dich vu, khong goi cong).
    dung = _module_da_import(_cay("routes.py"))
    assert ".cong_noi_bo" not in dung, dung
    # Khong cua nao ngoai app goi cong ma khong khai (linter chan; day chot lai).
    for f in (GOC / "apps").rglob("*.py"):
        if "__pycache__" in f.parts or f.is_relative_to(APP):
            continue
        assert "auto_scan_video.cong_noi_bo" not in f.read_bytes().decode(
            "utf-8", "replace"), f
    for goc in ("server", "platform_core"):
        for f in (GOC / goc).rglob("*.py"):
            assert "cong_noi_bo" not in f.read_bytes().decode("utf-8", "replace"), f


def test_route_tao_va_cong_goi_CUNG_cua_duyet():
    """Mot duong: route KHONG tu duyet ngon ngu/giong nua; ca hai goi dung_cai_dat."""
    route = _cay("routes.py")
    tao = next(n for n in ast.walk(route)
               if isinstance(n, ast.AsyncFunctionDef) and n.name == "tao")
    goi = {ast.unparse(n.func) for n in ast.walk(tao) if isinstance(n, ast.Call)}
    assert "dich_vu_tao.dung_cai_dat" in goi
    for cam in ("ngon_ngu_mod.kiem_cap", "rang_giong.kiem_o_cua",
                "vung_che.chuan_hoa", "tu_dien_mod.phan_tich",
                "cai_dat_mod.chuan_hoa"):
        assert cam not in goi, f"route van tu duyet: {cam}"

    cong = _cay("cong_noi_bo.py")
    sub = next(n for n in ast.walk(cong)
               if isinstance(n, ast.FunctionDef) and n.name == "submit_run")
    goi_cong = {ast.unparse(n.func) for n in ast.walk(sub) if isinstance(n, ast.Call)}
    assert "dich_vu_tao.dung_cai_dat" in goi_cong
    assert "features.tao_run_tu_ve" in goi_cong


def test_routes_van_duoi_tran_900_dong():
    so = (APP / "routes.py").read_bytes().count(b"\n")
    assert so <= 900, so
