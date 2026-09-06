r"""Chot RANH GIOI IMPORT giua cac tang -- vo mong quanh `import-linter`.

    py tools\check_ranh_gioi.py

Cau hinh o `.importlinter` (goc kho). Do 06/09: 3 hop dong, 0 gay, ~0,3 giay.

## 🔴 VI SAO CAN MOT VO, THAY VI GOI THANG `python -m importlinter.cli`

Do 06/09/2026, va no suyt thanh mot buoc gate XANH VINH VIEN:

    lint-imports                        rc=1   4.675 ky tu bao cao
    python -m importlinter.cli          rc=0   0 ky tu

Ca hai chay tren CUNG mot cay DANG CO MOT VI PHAM duoc tiem vao. `-m
importlinter.cli` chi NAP module (no dinh nghia mot nhom `click`) chu khong
GOI lenh nao -- nen no thoat 0, im lang, mai mai.

⛔ Mot buoc gate tro thi khong bao gio do, va ba hop dong trong `.importlinter`
   se thanh do trang tri. Toi chi bat duoc vi da hoi "no CO DO duoc khong?"
   truoc khi tin -- xem `AGENTS.md` muc 4d lop C.

⇒ Vo nay goi `lint_imports()` -- dung ham ma console script `lint-imports` goi
  -- roi tu quyet ma thoat. Va no CHUNG MINH duoc minh khong tro: xem
  `tests/test_306` cum "ranh gioi".

## ⛔ KHONG thay `tools/lint_app_contract.py`

Hai cong cu giai hai bai toan khac nhau:

    lint_app_contract   CO HOC hop dong app -- manifest, CSRF, co route,
                        cho dat logic nghiep vu
    check_ranh_gioi     AI DUOC IMPORT AI

Plan ban dau ghi "import-linter thay lint_app_contract". Do la SAI, do duoc
bang cach doc chinh hai cong cu. Bo cai nao cung mat mot lop bao ve.
"""
from __future__ import annotations

import pathlib
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass

    try:
        from importlinter.cli import EXIT_STATUS_SUCCESS, lint_imports
    except ImportError:
        print("[ranh gioi] THIEU `import-linter`. Xem requirements-dev.txt.")
        return 1

    # ⛔ `lint_imports` doc `.importlinter` theo THU MUC LAM VIEC, nen phai dung
    #    o goc kho. Mot lenh chay tu cho khac se khong tim thay cau hinh va
    #    "khong co hop dong nao" doc y het "moi hop dong deu dat".
    import os
    cu = os.getcwd()
    os.chdir(GOC)
    try:
        dat = lint_imports(config_filename=str(GOC / ".importlinter"))
    finally:
        os.chdir(cu)

    # ⛔ `lint_imports` tra ve MA THOAT (int), KHONG phai bool. `0` la thanh
    #    cong, ma `0` thi falsy -- ban dau toi viet `if not dat` va no bao
    #    "CO HOP DONG BI GAY" ngay tren mot bao cao "3 kept, 0 broken". Doan
    #    hinh dang API thay vi doc no: dung lop A cua `AGENTS.md` muc 4d.
    if dat != EXIT_STATUS_SUCCESS:
        print("\n[ranh gioi] CO HOP DONG BI GAY -- doc bao cao o tren.")
        return 1
    print("[ranh gioi] moi hop dong import deu dat")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
