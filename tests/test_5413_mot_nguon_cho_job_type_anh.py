"""`IMAGE_JOB_TYPE` khai DUNG MOT lan, va `raise` trong `except` dung hinh.

## ⛔ Vi sao phep kiem nay doc AST chu khong so hai gia tri

    from ...routes._shared import _IMAGE_JOB_TYPE as a
    from ...services.composite import _IMAGE_JOB_TYPE as b
    assert a is b          # ⛔ VO NGHIA

CPython **noi suy** chuoi hang, nen hai `"taoanh.generate"` khai o hai tep khac
nhau van cho `a is b` dung. Mot phep kiem nhu the se xanh **y nguyen** trong ca
hai the gioi — truoc va sau khi gop — nen no ⛔ khong do gi. Phai dem **cho
KHAI**, va cho khai chi doc duoc tu cay cu phap.

⭐ Cung ho voi bai hoc `banh-coc-do-cach-go-thay-vi-do-tinh-chat`: mot phep kiem
   co the dung ve ket qua ma sai ve **dieu no chung minh**.
"""
from __future__ import annotations

import ast
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
APP = GOC / "apps" / "prompt_ai_ommi"

#: Gia tri that. Doc tu nguon, ⛔ khong go lai o day.
def _gia_tri_khai() -> tuple[str, list[str]]:
    from apps.prompt_ai_ommi.project_schema import IMAGE_JOB_TYPE
    cho: list[str] = []
    for p in sorted(APP.rglob("*.py")):
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if not isinstance(n, ast.Assign):
                continue
            if not (isinstance(n.value, ast.Constant)
                    and n.value.value == IMAGE_JOB_TYPE):
                continue
            cho.append(f"{p.relative_to(GOC)}:{n.lineno}")
    return IMAGE_JOB_TYPE, cho


def test_job_type_anh_khai_dung_MOT_cho():
    gia_tri, cho = _gia_tri_khai()
    assert len(cho) == 1, (
        f'"{gia_tri}" duoc khai o {len(cho)} cho: {cho}. Doi mot ben ma quen ben '
        f'kia tung lam mot job tinh tien DUNG roi bi cua doc TU CHOI vi so sanh '
        f'job_type khong khop.')
    assert cho[0].endswith("project_schema.py:" + cho[0].split(":")[-1]), \
        f"nguon chan ly phai o project_schema.py (la, ca routes/ va services/ " \
        f"deu duoc import), dang o {cho[0]}"


def test_ca_hai_mien_deu_TRO_VE_cung_hang_so():
    """Hai ten cuc bo phai la con tro, khong phai ban sao."""
    from apps.prompt_ai_ommi.project_schema import IMAGE_JOB_TYPE
    from apps.prompt_ai_ommi.routes._shared import _IMAGE_JOB_TYPE as tu_routes
    from apps.prompt_ai_ommi.services.composite import _IMAGE_JOB_TYPE as tu_svc
    assert tu_routes == tu_svc == IMAGE_JOB_TYPE


def test_khong_con_raise_trong_except_thieu_nguyen_nhan():
    """`raise X` trong `except` phai co `from` — hoac la `raise` TRAN.

    ⭐ Quet AST 28/09 tim ra `chia_se.py:149` ma mot phep grep theo `from None`
       ⛔ khong thay: do la ca thu ba — khong thieu `from`, ma `raise exc` (gan
       ten roi nem lai) **cat truy vet** o chinh dong do.
    """
    xau: list[str] = []
    for p in sorted(APP.rglob("*.py")):
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(n, ast.ExceptHandler):
                for m in ast.walk(n):
                    if isinstance(m, ast.Raise) and m.exc is not None \
                            and m.cause is None:
                        xau.append(f"{p.relative_to(GOC)}:{m.lineno}")
    assert not xau, (
        f"{len(xau)} cho nem lai ma khong khai nguyen nhan: {xau}. Dung "
        f"`raise ... from exc` (co nguyen nhan), `from None` (co y giau) hoac "
        f"`raise` tran (nem lai nguyen ven).")
