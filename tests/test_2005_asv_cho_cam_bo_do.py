"""Cho cam giua HAI lan: `bo_do._chay_dich` goi `metricx.do_dich`.

🔴 Vi sao tep nay ton tai. Lan `giong` viet cho cam theo mot hop dong GHI TRONG
   DOCSTRING (`do_dich(cap, ngon_ngu_nguon, ngon_ngu_dich, gpu_uuid)`), con lan
   `dich` khai ham that voi `*` sau `cap` — tuc ba tham so kia **chi nhan tu
   khoa**. Hai lan deu xanh o cay rieng; cho noi chi ton tai sau khi GOP, va no
   se nem `TypeError` o dung luot chay THAT dau tien, sau khi khach da tra tien
   cho ASR + dich + giong.

⭐ Nen phep kiem o day khong goi model. No chi hoi mot cau: **loi goi co khop
   chu ky khong** — `inspect.signature().bind()` tra loi dung cau do va khong
   ton mot giay GPU nao.
"""
from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.asv_gpu.do_luong import bo_do, metricx  # noqa: E402


def _loi_goi_do_dich() -> ast.Call:
    """Nut AST cua loi goi `metricx.do_dich(...)` trong `_chay_dich`."""
    cay = ast.parse(inspect.getsource(bo_do._chay_dich))
    for n in ast.walk(cay):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "do_dich"):
            return n
    raise AssertionError("khong thay loi goi `metricx.do_dich` trong `_chay_dich`")


def test_cho_cam_goi_do_dich_KHOP_chu_ky_that():
    """`bind()` nem `TypeError` neu loi goi khong khop — dung dieu can bat."""
    goi = _loi_goi_do_dich()
    vi_tri = ["cap"] * len(goi.args)
    tu_khoa = {kw.arg: None for kw in goi.keywords if kw.arg}

    # Chu ky THAT cua ham, khong phai chu ky chep trong docstring.
    inspect.signature(metricx.do_dich).bind(*vi_tri, **tu_khoa)


def test_ba_tham_so_ngon_ngu_deu_di_bang_TU_KHOA():
    """⛔ Chot rieng: `do_dich` co `*` sau `cap`, nen goi theo vi tri la hong.

    Kiem CA HAI phia — chu ky that va loi goi — de mot lan sau doi ben nay ma
    quen ben kia thi do o day chu khong do o may khach.
    """
    ts = inspect.signature(metricx.do_dich).parameters
    for ten in ("ngon_ngu_nguon", "ngon_ngu_dich", "gpu_uuid"):
        assert ts[ten].kind is inspect.Parameter.KEYWORD_ONLY, ten

    goi = _loi_goi_do_dich()
    assert len(goi.args) == 1, "chi `cap` duoc di theo vi tri"
    assert {kw.arg for kw in goi.keywords} >= {"ngon_ngu_nguon", "ngon_ngu_dich"}


def test_cho_cam_van_bao_khong_kha_dung_khi_THIEU_module(monkeypatch):
    """Thieu bo do ⇒ `KhongKhaDung`, KHONG lui ve mot cong thuc tu che (§21).

    ⚠️ Gia vo "chua co module" bang `sys.modules[...] = None` VA go thuoc tinh
       da gan tren goi: `from . import metricx` doc thuoc tinh cua goi truoc,
       nen chi xoa mot trong hai thi module van vao duoc.
    """
    import apps.asv_gpu.do_luong as goi

    monkeypatch.setitem(sys.modules, "apps.asv_gpu.do_luong.metricx", None)
    monkeypatch.delattr(goi, "metricx", raising=False)
    dv = bo_do.DauVao(cap_dich=[{"ma": "a", "nguon": "x", "dich": "y"}],
                      ngon_ngu_nguon="zh", ngon_ngu_dich="vi")
    try:
        bo_do._chay_dich(dv, gpu_uuid="")
    except bo_do.KhongKhaDung:
        return
    raise AssertionError("thieu module ma khong bao `khong_kha_dung`")
