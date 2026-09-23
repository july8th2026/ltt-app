"""409 insufficient_credit phai mang theo can/con - V-22.

Hoi quy nay da tim ra mot lan o cua job ngay 14/09/2026; 23/09 no quay lai o cua
stream va lam mot phien chan doan di sai 20 phut vi khong doc duoc "can bao nhieu,
con bao nhieu".

Tra mã thật truoc khi viet (khong doan chu ky): `ModelFailure` (platform_core/llm/
model_failure.py) la mot dataclass co THANG cac thuoc tinh `limit`/`actual`, va
phuong thuc `as_detail()` la thu dung than v1 (khong phai `than_v1()`/`ltt_error`
nhu ban nhap dau tien cua ke hoach).
"""
from __future__ import annotations

import ast
import pathlib

from platform_core.llm.model_failure import model_failure

_LUONG = pathlib.Path("platform_core/runtime_noi_bo/luong.py")


def test_model_failure_mang_can_va_con():
    f = model_failure("insufficient_credit", http_status=409,
                       request_id="r1", limit=17, actual=13)
    than = f.as_detail()
    assert than["limit"] == 17
    assert than["actual"] == 13


def test_doi_chung_am_khong_truyen_thi_khong_co_hai_truong():
    f = model_failure("insufficient_credit", http_status=409, request_id="r1")
    than = f.as_detail()
    assert "limit" not in than
    assert "actual" not in than


def test_cua_stream_khong_duoc_danh_roi_can_con():
    """Doc AST cua luong.py: nhanh bat ThieuCredit phai GIU ngoai le va truyen so."""
    cay = ast.parse(_LUONG.read_text(encoding="utf-8"))
    tim_thay = False
    for nut in ast.walk(cay):
        if not isinstance(nut, ast.ExceptHandler):
            continue
        ten = getattr(nut.type, "id", None)
        if ten != "ThieuCredit":
            continue
        tim_thay = True
        assert nut.name is not None, "bat ThieuCredit ma khong giu ngoai le - can/con bi danh roi"
        goi = [n for n in ast.walk(nut) if isinstance(n, ast.Call)
               and getattr(n.func, "id", "") == "model_failure"]
        assert goi, "nhanh ThieuCredit phai dung model_failure"
        kw = {k.arg for g in goi for k in g.keywords}
        assert {"limit", "actual"} <= kw, f"thieu limit/actual, dang co: {sorted(kw)}"
    assert tim_thay, "khong con nhanh 'except ThieuCredit' nao trong luong.py - phep kiem da lac chua"
