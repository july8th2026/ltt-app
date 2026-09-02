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
   hoi deploy nham — mot loi im lang, dat, va rat kho phat hien.

   Chot chan that nam trong `setup/2-cai-dat.ps1`: no doi `.git` la mot THU MUC
   (cay chinh) chu khong phai mot TEP (cay rieng), va no `throw` **truoc** moi
   thao tac ghi. Tam bao ve do duoc `tests/test_362_cay_rieng_va_deploy.py` giu
   bang tam chot rieng.

   ⚠️ Doan nay truoc 2026-09-02 ghi rang chot do nam trong mot cong cu kiem
      rieng duoi `tools/` "va no chay trong gate". **Cong cu do khong ton tai.**
      Mot tham chieu chet trong tai lieu an toan la mot lop bao ve TUONG TUONG:
      nguoi doc tin rang co hai lop trong khi chi co mot, nen se khong di kiem
      lop con lai. Nay `test_394` chot rang moi duong `tools/*.py` nhac o day
      phai that su ton tai.

4. ⛔ **Bat cu thu gi con lai trong cay khi ai do deploy deu len production**,
   ke ca tep CHUA THEO DOI. `robocopy` chep ca cay, chi tru danh sach `/XD`
   (`data secrets logs .venv venv __pycache__ .pytest_cache .git dist build
   temp_videos node_modules .playwright-cli .playwright-mcp .claude
   test-results tmp`). Khong co buoc chon loc theo phien — nen "de tam o day
   roi don sau" khong phai mot lua chon an toan tren cay chinh.
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


def _so_voi_origin(nhanh: str) -> str:
    """`nhanh` di truoc/sau `origin/<nhanh>` bao nhieu commit.

    🔴 VI SAO CO COT NAY. Do 2026-09-02: ba phien commit deu dan suot **bon
       ngay** va khong ai hoi `origin` dang o dau. Ket qua: `origin` dung o
       29/08, **nam nhanh chua tung co ban sao nao ngoai may**, va bon commit
       tren `admin-mvp-v3` — trong do co dung ban **da deploy len production**
       — ton tai o **mot cho duy nhat tren doi**.

    ⭐ Gia dinh gay ra chuyen do duoc mot phien noi thang: *"toi coi 'da commit'
       la 'da an toan'"*. Do la mot gia dinh rat de tin va khong bao gio tu keu
       len. Nen no phai duoc IN RA o cho nguoi ta nhin moi ngay, chu khong nam
       trong mot luat ai do phai nho.
    """
    if not nhanh or nhanh.startswith("("):
        return ""
    try:
        r = subprocess.run(
            ["git", "rev-list", "--left-right", "--count",
             f"{nhanh}...origin/{nhanh}"],
            cwd=str(GOC), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=20)
    except (OSError, subprocess.SubprocessError):
        return "  [khong hoi duoc git]"
    if r.returncode != 0:
        # Khong co nhanh tuong ung tren origin — day la truong hop DANG BAO
        # DONG nhat, khong phai truong hop bo qua.
        return "  [!] CHUA CO TREN origin"
    try:
        truoc, sau = (int(x) for x in r.stdout.split())
    except ValueError:
        return ""
    if truoc and sau:
        return f"  [!] truoc {truoc}, sau {sau}"
    if truoc:
        return f"  [!] CHUA DAY {truoc} commit"
    if sau:
        return f"  (sau origin {sau})"
    return "  = origin"


def _chep_thu_khong_o_trong_git(dich: Path) -> None:
    """Chep thu MA GATE CAN nhung git khong giu.

    🔴 VI SAO. `git worktree` chi dung lai thu **trong git**. Nhung mot so thu
       gate doi lai bi `.gitignore` — nen mot cay rieng vua tao **khong bao gio
       xanh duoc**, va no do vi mot ly do khong lien quan gi toi viec dang lam.

    ⛔ Va do la kieu do te nhat. Do 2026-09-02: mot phien mat mot luc de truy
       ba buoc do trong cay rieng cua no truoc khi nhan ra chung von the.
       Nguy hiem that su khong phai thoi gian do — la **mot phep kiem do vi ly
       do sai se day nguoi ta bo qua chinh no**, roi toi luc no do vi ly do
       that thi phan xa da thanh "chac lai chuyen cay rieng".

    ⚠️ CHI chep thu re. `node_modules/` (~700 MB cho ba thu muc) thi khong —
       ba buoc frontend se TU KHAI `BO QUA` va hien o dong RESULT, va do la
       cau tra loi trung thuc hon mot ban sao 700 MB moi lan tao cay.
    """
    nguon_vendor = sorted((GOC / "apps").glob("*/vendor"))
    for nguon in nguon_vendor:
        if not nguon.is_dir():
            continue
        dich_con = dich / nguon.relative_to(GOC)
        if dich_con.exists():
            continue
        mb = sum(f.stat().st_size for f in nguon.rglob("*") if f.is_file()) / 1024 ** 2
        print(f"  chep {nguon.relative_to(GOC).as_posix()} ({mb:.0f} MB) - "
              "git khong giu no, ma gate thi doi")
        shutil.copytree(nguon, dich_con)
    if nguon_vendor:
        print("  (node_modules KHONG chep - ~700 MB; buoc frontend se tu khai BO QUA)")


def _liet_ke() -> int:
    # 🔴 HOI GIT xem dau la cay chinh, dung so voi `GOC`.
    #
    #    `GOC` suy tu `__file__`, tuc no la **cay dang chay**. Chay lenh nay tu
    #    mot cay rieng thi ban cu in "Cay chinh: <cay rieng>" va danh dau `*`
    #    vao chinh no — trong khi `*` co nghia la "CHI cay nay duoc deploy".
    #    Mot dau hieu an toan chi sai o dung noi no can dung nhat.
    #
    # ⭐ Cung mot gia dinh do da gay ba trieu chung trong mot ngay: hai chot o
    #    `test_362` va dong nay. `la_cay_chinh()` ngay ben tren da lam dung —
    #    no hoi git — nen cho nay chi can goi no.
    cac_cay = [d[9:] for d in _git("worktree", "list", "--porcelain").splitlines()
               if d.startswith("worktree ")]
    chinh = cac_cay[0] if cac_cay else str(GOC)
    print(f"Cay chinh: {chinh}\n")
    canh_bao = False
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
            dau = "*" if Path(duong).resolve() == Path(chinh).resolve() else " "
            trang_thai = _so_voi_origin(nhanh)
            canh_bao = canh_bao or "[!]" in trang_thai
            print(f" {dau} {duong:<40} {nhanh:<28}{trang_thai}")
    print("\n  * = cay chinh. CHI cay nay duoc deploy.")
    if canh_bao:
        print("  [!] = co viec CHI TON TAI TREN MAY NAY. `git push origin <nhanh>`.")
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
    _chep_thu_khong_o_trong_git(dich)
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
