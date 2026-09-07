r"""Do phu cua DONG MOI — khong do phu ca kho.

    py tools\do_phu_diff.py                    # so voi origin/master
    py tools\do_phu_diff.py --nhanh-goc master
    py tools\do_phu_diff.py --san 80           # do neu dong moi phu < 80%

## Vi sao do phu THEO DIFF chu khong phai phu TOAN KHO

🔴 Mot con so "phu toan kho 62%" khong tra loi duoc cau hoi ma nguoi ta thuc
   su hoi, la: **thu toi vua viet co duoc kiem khong?** Hai luot deu 62% co
   the la mot luot them 300 dong co test va mot luot them 300 dong khong co
   test — con so toan kho gan nhu khong nhuc nhich, vi mau so qua lon.

⭐ `diff-cover` doi cau hoi: chi nhin nhung dong `git diff` cho thay la MOI,
   roi hoi bao nhieu trong so do duoc chay. Mot dong moi khong duoc chay la
   mot dong chua ai kiem — bat ke phan con lai cua kho the nao.

## ⛔ Vi sao KHONG phai mot buoc trong gate

Buoc `bo test (song song)` cua gate mat ~500 giay. Bat `--cov` len no lam moi
luot gate cham them, va gate da la thu chay sau MOI lan sua. Do phu la cau hoi
hoi mot lan truoc khi bao xong, khong phai sau moi lan sua.

⇒ Cong cu nay dung tang voi `tools/test_nhanh.py`: chay tay, xin khoa, va noi
  ro no khong phai cong.

## ⛔ Va vi sao no PHAI xin khoa

No chay ca bo test. Do la lenh NANG theo dung dinh nghia o
`docs/QUY_TAC_CHAY_LENH_NANG.md`. Mot cong cu do ma khong xin khoa la mot cong
cu se chay chong len luot cua phien khac — da xay ra that, xem
`tools/cua_so_yen.py`.
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC / "tools"))

#: Cung pham vi voi `check_mypy.THU_MUC`: do phu cua ma NGUON, khong do phu cua
#: chinh bo test.
DO_PHU = ("apps", "platform_core", "server", "llm_gateway", "render_gateway",
          "sdk", "nexus_agent")


def _ra(*phan: object) -> None:
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    print(*phan)


def _nhanh_goc_mac_dinh() -> str:
    """`origin/master` neu co, khong thi `master`.

    ⛔ Doan mo ta `--compare-branch` cua diff-cover: no chay `git diff
       <nhanh>...HEAD`. Neu nhanh do khong ton tai thi diff rong, va mot diff
       rong cho ra "100% phu" — mot con so DEP vi khong do gi ca.
    """
    for ten in ("origin/master", "master"):
        r = subprocess.run(["git", "rev-parse", "--verify", "--quiet", ten],
                           cwd=GOC, capture_output=True, text=True)
        if r.returncode == 0:
            return ten
    raise SystemExit("khong tim thay `origin/master` lan `master` de so sanh")


def main() -> int:
    p = argparse.ArgumentParser(description="Do phu cua dong MOI so voi mot nhanh goc.")
    p.add_argument("--nhanh-goc", default=None, help="mac dinh: origin/master")
    p.add_argument("--san", type=float, default=None,
                   help="tra ma 1 neu phu duoi muc nay (%%)")
    p.add_argument("--loi", type=int, default=None, help="so worker pytest")
    p.add_argument("--pham-vi", default="tests",
                   help="duong dan test (mac dinh: tests) — de chay thu hep")
    p.add_argument("--khong-khoa", action="store_true",
                   help="bo qua `cua_so_yen` (chi khi da tu biet may ranh)")
    a = p.parse_args()

    goc = a.nhanh_goc or _nhanh_goc_mac_dinh()

    # ⛔ `diff-cover` so `<goc>...HEAD`. Tren mot nhanh song lau nhu
    #    `admin-mvp-v3`, diff voi `origin/master` la TOAN BO do lech cua nhanh
    #    — hang nghin dong cua nhieu phien khac, khong phai "thu toi vua sua".
    #    In ro so tep de nguoi doc biet minh dang doc pham vi nao.
    _dem = subprocess.run(["git", "diff", "--name-only", f"{goc}...HEAD"],
                          cwd=GOC, capture_output=True, text=True)
    _so_tep = len([d for d in _dem.stdout.splitlines() if d.strip()])
    if _so_tep > 60:
        _ra(f"  [!] `{goc}...HEAD` cham {_so_tep} tep — do la do lech CA NHANH,")
        _ra("      khong phai thay doi cua mot lan sua. Dung `--nhanh-goc` tro")
        _ra("      vao diem re that su neu muon doc 'thu toi vua viet'.")
    xml = GOC / "test-results" / "coverage_diff.xml"
    xml.parent.mkdir(parents=True, exist_ok=True)

    from gate import loi_cho_bo_test
    loi = a.loi or loi_cho_bo_test()

    lenh_test = [
        sys.executable, "-m", "pytest", "-q", "-p", "no:randomly", "-n", str(loi),
        *[f"--cov={t}" for t in DO_PHU],
        f"--cov-report=xml:{xml}", "--cov-report=", a.pham_vi,
    ]

    # 🔴 MOT CON SO DEP TU MOT PHAM VI HEP LA MOT CON SO SAI.
    #
    #    `--pham-vi` chi de CHAY THU duong ong. Chay mot tep test roi doc bang
    #    phu ra la doc "dong nao duoc tep AY cham", chu khong phai "dong nao
    #    duoc BO TEST kiem" — va bang do trong y het bang that: cung dinh dang,
    #    cung mau, cung phan tram. Do dung la kieu phep do da lam kho nay tin
    #    nham nhieu lan (xem `docs/BAY_TRONG_CONG_CHAT_LUONG.md`).
    if a.pham_vi != "tests":
        _ra("")
        _ra("  " + "=" * 66)
        _ra(f"  [!] PHAM VI HEP: `{a.pham_vi}` — day KHONG phai mot phep do phu.")
        _ra("      Moi con so duoi day chi noi tep test AY cham vao dau. Mot tep")
        _ra("      khong duoc cham hien `0.0%` vi KHONG AI CHAY NO trong luot")
        _ra("      nay, khong phai vi no thieu test. Chi dung de thu duong ong.")
        _ra("  " + "=" * 66)

    def _chay_do() -> int:
        _ra(f"  [do phu] {len(DO_PHU)} thu muc, -n {loi}, pham vi `{a.pham_vi}`, "
            f"so voi `{goc}`")
        r = subprocess.run(lenh_test, cwd=GOC)
        # ⛔ pytest tra 1 khi CO test do. Do van cho ra mot coverage.xml dung,
        #    nhung mot bao cao phu dung tren mot bo test DANG DO la mot con so
        #    khong dung duoc — no do "dong nao duoc chay", khong do "dong nao
        #    duoc kiem".
        if r.returncode not in (0, 5):
            _ra(f"  [do phu] BO TEST DO (ma {r.returncode}) — sua test truoc.")
            return r.returncode
        return 0

    if a.khong_khoa:
        ma = _chay_do()
    else:
        from cua_so_yen import CuaSoYen
        with CuaSoYen("do-phu-diff", "do phu dong moi",
                      tai_nguyen=("cpu_nhieu", "postgres_test")):
            ma = _chay_do()
    if ma:
        return ma

    lenh_phu = ["diff-cover", str(xml), f"--compare-branch={goc}",
                "--show-uncovered", "--src-roots", *DO_PHU]
    if a.san is not None:
        lenh_phu.append(f"--fail-under={a.san}")
    _ra("")
    return subprocess.run(lenh_phu, cwd=GOC).returncode


if __name__ == "__main__":
    raise SystemExit(main())
