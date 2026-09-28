"""Huy giua duong: khach tra DUNG phan da giao, ⛔ KHONG duoc mien phi.

## 🔴 Vi sao task nay nguy hiem nhat ca pha

`prompt_ai_ommi` tinh tien o **tang job**: credit duoc GIU luc nop, quyet toan luc
xong. Va nen tang **mac dinh hoan TOAN BO** khi job bi huy
(`job_runner._hoan_credit`).

⇒ Neu ta vua hoan het vua giu lai canh da sinh, khach lay duoc viec **MIEN PHI**, va
  **lap duoc**: nop 20 canh, huy sau lo 1, nhan 5 canh, lam lai. Do la mot duong lam
  dung THAT, ⛔ khong phai mot ca hiem.

## ⭐ Thuoc: quyet toan theo phan DA GIAO roi NEM LAI

    1. khach POST /jobs/{id}/cancel  -> status = JOB_CANCELLED
    2. worker toi ranh lo ke tiep    -> ctx.progress_counter() NEM JobCancelled
    3. `jobs.py` BAT, lam hai viec roi NEM LAI:
         credit.quyet_toan(db, user_id, job_id, actual=gia_phan_da_giao(...))
         raise
    4. runner -> _hoan_credit -> credit.hoan() -> gap `_da_ket_so` True -> KHONG hoan

⚠️ **Chot chiu luc la buoc 4, va no nam o `hoan()`, ⛔ KHONG o `so_da_giu()`.**
   `so_da_giu` chi cong but toan `CREDIT_HOLD` nen no **van > 0** sau quyet toan;
   `_hoan_credit` vi the **van goi** `hoan()`. Thu chan hoan la `_da_ket_so`.

   ⇒ Neu ai bo cai guard ay, khach duoc hoan **ca khoan vua thu** — mat doanh thu,
     ⛔ khong mot dong log nao. Nen bai duoi ghim chinh no, o MA NEN TANG.
"""
from __future__ import annotations

import ast
import inspect

import pytest

from apps.prompt_ai_ommi.project_schema import MAX_SCENES
from apps.prompt_ai_ommi.services import chia_lo


def test_jobs_BAT_JobCancelled_QUYET_TOAN_roi_NEM_LAI():
    """Doc AST: phai co `except` bat `JobCancelled`, trong do goi `quyet_toan`, va
    ket bang mot `raise` TRAN."""
    from apps.prompt_ai_ommi import jobs
    cay = ast.parse(inspect.getsource(jobs))
    thay = False
    for n in ast.walk(cay):
        if not isinstance(n, ast.ExceptHandler) or n.type is None:
            continue
        if "JobCancelled" not in ast.unparse(n.type):
            continue
        than = ast.unparse(n)
        assert "quyet_toan" in than, (
            "bat `JobCancelled` ma KHONG quyet toan: nen tang se hoan TOAN BO va "
            "khach lay duoc phan da giao MIEN PHI")
        assert any(isinstance(x, ast.Raise) and x.exc is None for x in ast.walk(n)), (
            "phai `raise` TRAN de nem lai: khong nem lai thi job ket thuc BINH "
            "THUONG sau khi bi huy, va trang thai bao cho khach se sai")
        thay = True
    assert thay, "khong co `except JobCancelled` nao trong jobs.py"


def test_chan_hoan_tien_nam_o_credit_hoan_CHU_KHONG_o_so_da_giu():
    """⭐ GHIM dung co che ma ca cach huy dua vao — o MA NEN TANG, khong o ma app.

    `so_da_giu` chi cong but toan HOLD nen no VAN > 0 sau quyet toan; thu chan hoan
    la `_da_ket_so` trong `credit.hoan`. Doi cai guard ay thi khach duoc hoan CA
    KHOAN VUA THU — mat doanh thu, khong mot dong log nao.
    """
    from platform_core import credit
    than = inspect.getsource(credit.hoan)
    assert "_da_ket_so" in than or "da_quyet_toan" in than, (
        "`credit.hoan` KHONG con chan theo 'da ket so'. Toan bo cach huy cua pha 6 "
        "dua vao dieu nay — doc lai `jobs.py` truoc khi tin bat cu bai nao khac "
        "trong tep nay.")


@pytest.mark.parametrize("da_giao,thap_hon", [(0, True), (5, True), (10, True),
                                              (15, True), (MAX_SCENES, False)])
def test_gia_huy_THAP_HON_gia_day_du_tru_khi_giao_du(da_giao, thap_hon):
    from apps.prompt_ai_ommi.manifest import _cost
    p = {"operation": "director", "scene_count": MAX_SCENES}
    day_du = _cost(p)
    gia = chia_lo.gia_phan_da_giao(da_giao, p)
    if thap_hon:
        assert gia < day_du, (
            f"giao {da_giao}/{MAX_SCENES} canh ma thu {gia} = gia day du {day_du}: "
            f"khach huy som KHONG duoc tra nhu chay het")
    else:
        assert gia == day_du


def test_DOI_CHUNG_bo_quyet_toan_thi_bai_dau_PHAI_do():
    """Tiem loi: bo loi goi `quyet_toan` khoi nhanh `except`.

    ⭐ Khong co buoc nay thi bai dau co the dang xanh vi mot ly do khong lien quan
       (vd `ast.unparse` doi dinh dang va chuoi `quyet_toan` khop o cho khac).
    """
    from apps.prompt_ai_ommi import jobs
    src = inspect.getsource(jobs)
    assert "quyet_toan" in src
    hong = src.replace("quyet_toan", "KHONG_QUYET_TOAN")
    cay = ast.parse(hong)
    for n in ast.walk(cay):
        if isinstance(n, ast.ExceptHandler) and n.type is not None \
                and "JobCancelled" in ast.unparse(n.type):
            con = ast.unparse(n).replace("KHONG_QUYET_TOAN", "")
            assert "quyet_toan" not in con, (
                "tiem loi khong hieu qua — bai dau khong do duoc dieu gi")
            return
    pytest.fail("khong tim thay nhanh except sau khi tiem loi")


def test_huy_o_lo_dau_thi_khach_KHONG_bi_thu_gi():
    """`0` canh giao -> gia `0`. ⛔ KHONG phai san duoi `4`.

    San 4 la gia cua mot luot CO giao hang. Huy truoc khi lo dau xong thi khach
    ⛔ khong nhan gi, nen ⛔ khong duoc thu gi.
    """
    p = {"operation": "director", "scene_count": MAX_SCENES}
    assert chia_lo.gia_phan_da_giao(0, p) == 0
