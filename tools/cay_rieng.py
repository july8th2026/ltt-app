"""cay_rieng.py — mot cay lam viec rieng cho moi phien Claude.

    python tools/cay_rieng.py liet-ke
    python tools/cay_rieng.py tao e7
    python tools/cay_rieng.py go  e7

## Van de no giai

Ba phien cung ghi MOT cay. Mot luot `gate.py` mat 5-6 phut, va trong 6 phut do
phien khac sua vai tep — nen ket qua noi ve mot cay khong con ton tai. Ngay
31/08 ca hai luot gate chay gan nhau deu cho **do gia** vi dung ly do do.

`git worktree` cho moi phien mot cay THAT, chung mot `.git`. Phien khac ghi gi
cung khong lot vao phep do cua ta.

⭐ Kho nay **da** dung co che nay (`D:/LTTGateQ6`, `D:/LTTSTUDIOSAPP_RELEASE_H42`),
   nen day khong phai mot thu nghiem — chi la lam cho no thanh mot buoc co ten.

## Ba dieu phai biet truoc khi dung

1. 🔴 **Thay doi CHUA COMMIT khong di theo.** `git worktree` phan nhanh tu mot
   commit. Moi thu dang do trong cay chinh o lai cay chinh. Do la ly do lenh
   `tao` bat buoc in ra so tep dang do, thay vi im lang tao mot cay thieu viec.

2. 🔴 **Mot nhanh khong the checkout o hai cay.** Nen moi cay rieng phai co
   nhanh rieng (`phien/<ten>`), va cuoi viec phai **gop lai**. Neu ban khong
   dinh gop, dung tao.

3. ⛔ **KHONG BAO GIO DEPLOY TU CAY RIENG.** May nay LA production, va deploy
   chep **ca cay** sang `C:\\LTTPlatform`. Ba cay trong giong het nhau la ba co
   hoi deploy nham — mot loi im lang, dat, va rat kho phat hien. Xem
   `tools/check_cay_chinh.py`; no chan chuyen do, va no chay trong gate.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent

#: Duoi ngan nay thi mot cay rieng nua la lieu. Mot cay ~1,5 GB ke ca `.git`
#: chung khong nhan doi, nhung `__pycache__` + thu muc tam pytest thi co.
TRONG_TOI_THIEU_GB = 20.0


def _git(*a: str, cay: Path | None = None) -> str:
    r = subprocess.run(["git", *a], cwd=str(cay or GOC), capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(a)} that bai:\n{r.stderr.strip()}")
    return r.stdout.strip()


def la_cay_chinh(cay: Path | None = None) -> bool:
    """Cay chinh la cay co `--git-dir` trung `--git-common-dir`.

    Cay lien ket co `--git-dir` tro toi `<chung>/worktrees/<ten>`, nen phep so
    nay dung ma khong phai doan theo duong dan.
    """
    rieng = Path(_git("rev-parse", "--absolute-git-dir", cay=cay)).resolve()
    chung = _git("rev-parse", "--path-format=absolute", "--git-common-dir",
                 cay=cay)
    return rieng == Path(chung).resolve()


def _dang_do() -> list[str]:
    ra = _git("status", "--porcelain")
    return [d for d in ra.splitlines() if d.strip()]


def _liet_ke() -> int:
    print(f"Cay chinh: {GOC}")
    for khoi in _git("worktree", "list", "--porcelain").split("\n\n"):
        duong = nhanh = ""
        for d in khoi.splitlines():
            if d.startswith("worktree "):
                duong = d[9:]
            elif d.startswith("branch "):
                nhanh = d[7:].replace("refs/heads/", "")
            elif d.strip() == "detached":
                nhanh = "(khong nhanh)"
        if duong:
            dau = "*" if Path(duong).resolve() == GOC else " "
            print(f" {dau} {duong:<44} {nhanh}")
    print("\n  * = cay chinh. CHI cay nay duoc deploy.")
    return 0


def _tao(ten: str) -> int:
    if not la_cay_chinh():
        raise SystemExit("Dang o mot cay rieng roi. Chay lenh nay tu cay chinh.")

    dich = GOC.parent / f"{GOC.name}-{ten}"
    nhanh = f"phien/{ten}"
    if dich.exists():
        raise SystemExit(f"{dich} da ton tai.")

    trong_gb = shutil.disk_usage(GOC.parent).free / 1024 ** 3
    if trong_gb < TRONG_TOI_THIEU_GB:
        raise SystemExit(f"O dia chi con {trong_gb:.1f} GB "
                         f"(can it nhat {TRONG_TOI_THIEU_GB:.0f} GB).")

    do = _dang_do()
    if do:
        # 🔴 Khong tu dong mang theo, va cung khong im lang bo lai. Chep tay
        #    thay doi cua nguoi khac la dam vao viec dang do cua ho.
        print(f"CANH BAO: cay chinh dang co {len(do)} tep chua commit.")
        print("  Chung O LAI cay chinh, KHONG di theo sang cay moi:")
        for d in do[:10]:
            print(f"    {d}")
        if len(do) > 10:
            print(f"    ... con {len(do) - 10} tep nua")
        print("  Commit truoc neu ban muon mang chung sang.\n")

    print(_git("worktree", "add", str(dich), "-b", nhanh))
    print(f"\nDa tao cay rieng:\n  {dich}\n  nhanh: {nhanh}\n")
    print("Buoc tiep:")
    print(f"  cd {dich}")
    print(f"  python tools/gate.py --phien {ten}")
    print("\nXong viec thi gop lai roi go cay:")
    print(f"  git -C \"{GOC}\" merge {nhanh}")
    print(f"  python tools/cay_rieng.py go {ten}")
    print("\nKHONG deploy tu cay nay. Deploy chi chay tu cay chinh.")
    return 0


def _go(ten: str) -> int:
    dich = GOC.parent / f"{GOC.name}-{ten}"
    if not dich.exists():
        raise SystemExit(f"{dich} khong ton tai.")
    # ⛔ Khong dung `--force`: git tu choi khi cay con viec chua commit, va do
    #    chinh la thu can duoc tu choi. Ep go la mat viec, im lang.
    print(_git("worktree", "remove", str(dich)) or f"Da go {dich}")
    print(f"Nhanh `phien/{ten}` VAN CON. Xoa khi da gop:")
    print(f"  git branch -d phien/{ten}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Cay lam viec rieng cho moi phien.")
    p.add_argument("lenh", choices=["liet-ke", "tao", "go"])
    p.add_argument("ten", nargs="?", default="",
                   help="ten phien, vd `e7` -> cay `...-e7`, nhanh `phien/e7`")
    a = p.parse_args()

    if a.lenh == "liet-ke":
        return _liet_ke()
    if not a.ten:
        raise SystemExit(f"lenh `{a.lenh}` can mot ten phien.")
    if not a.ten.replace("-", "").replace("_", "").isalnum():
        raise SystemExit("ten phien chi duoc chua chu, so, `-` va `_`.")
    return _tao(a.ten) if a.lenh == "tao" else _go(a.ten)


if __name__ == "__main__":
    sys.exit(main())
