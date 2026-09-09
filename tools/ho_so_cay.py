"""ho_so_cay.py - HO SO VAN HANH cua CAY nay: NORMAL hay FAST_BUILD.

    python tools/ho_so_cay.py trang-thai
    python tools/ho_so_cay.py bat --pham-vi "migration 4 bot -> app"
    python tools/ho_so_cay.py chuyen FEATURE_COMPLETE
    python tools/ho_so_cay.py no-kiem
    python tools/ho_so_cay.py tat

================================================================================
NO GIAI CAI GI

`docs/00_LTT_OPERATING_CONTRACT.md` muc 4.10 dinh nghia HAI ho so van hanh.
Tep nay khong dinh nghia them luat nao ca - no chi tra loi ba cau hoi ma hop
dong do khong tu tra loi duoc, vi ca ba cau deu phu thuoc vao CAY dang dung:

    1. cay nay dang o ho so nao, va o buoc nao cua may trang thai
    2. governance cua cay nay con khop trunk khong
    3. tu MOC baseline toi gio, phai chung nhan nhung gi

⛔ Khong chep bang anh xa test/gate vao day. Cau 3 goi thang `thanh_phan.py`,
   la nguon chan ly ma `gate.py --doi` cung goi. Hai ban sao cua mot anh xa la
   hai ban sao se lech nhau - kho nay da tra gia cho dung co che do (xem
   `docs/QUY_TRINH_WORKTREE.md`: ba ban `gate.py` khac nhau song song).

================================================================================
VI SAO TRANG THAI KHONG NAM TRONG CAY LAM VIEC

Tep trang thai nam trong THU MUC GIT RIENG cua worktree
(`.git/worktrees/<ten>/ltt_ho_so.json`), khong nam trong cay. Ba ly do, ca ba
deu la loi da xay ra that trong kho nay:

    - `gate._anh_chup_cay()` chup `tools/ tests/ apps/ ...` luc bat dau va doi
      chieu luc ket thuc. Mot tep trang thai ghi giua luot chay se lam gate
      tu vut bo phep do cua chinh no.
    - deploy chep CA CAY (`robocopy`), ke ca tep chua theo doi. Trang thai cua
      mot phien khong duoc phep di len may chu.
    - trang thai la cua MOT cay. Commit no vao nhanh la phat no cho moi cay
      khac checkout cung nhanh.

⭐ `git rev-parse --absolute-git-dir` tra dung thu muc rieng cho tung worktree,
   nen khong can `extensions.worktreeConfig` va khong dung toi `.git/config`
   dung chung.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent

#: Nhanh trunk canonical. Ghi de bang `LTT_TRUNK` khi trunk doi ten.
TRUNK = os.environ.get("LTT_TRUNK", "admin-mvp-v3")

TEN_TEP = "ltt_ho_so.json"

HO_SO = ("NORMAL", "FAST_BUILD")

#: May trang thai cua FAST_BUILD - muc 4.10 cua hop dong van hanh.
TRANG_THAI = ("RESEARCH", "BUILDING", "FEATURE_COMPLETE",
              "CERTIFYING", "READY_TO_MERGE")

#: Chuyen duoc di TOI dau. Chi mot chieu, tru duong lui tu CERTIFYING ve
#: BUILDING - va duong do co gia: no vut bo FEATURE_COMPLETE, tuc thua nhan
#: rang feature set chua dong bang that.
CHUYEN_DUOC: dict[str, tuple[str, ...]] = {
    "RESEARCH": ("BUILDING",),
    "BUILDING": ("FEATURE_COMPLETE",),
    "FEATURE_COMPLETE": ("CERTIFYING", "BUILDING"),
    "CERTIFYING": ("READY_TO_MERGE", "BUILDING"),
    "READY_TO_MERGE": ("BUILDING",),
}

#: Tep quyet dinh "cay nay co hieu luat hien hanh khong".
#:
#: 🔴 So bang BLOB SHA voi trunk, khong bang mot chuoi phien ban go tay. Mot
#:    chuoi go tay chi dung cho toi lan dau co nguoi quen tang no, va luc do
#:    no bao XANH cho mot cay da cu - dung chieu nguy hiem.
TEP_GOVERNANCE = (
    "docs/00_LTT_OPERATING_CONTRACT.md",
    "docs/QUY_TRINH_WORKTREE.md",
    "tools/gate.py",
    "tools/thanh_phan.py",
    "tools/ho_so_cay.py",
)

#: Duong dan cham toi giao dien => phai kiem tren trinh duyet (hop dong muc 9).
DUOI_GIAO_DIEN = (".css", ".js", ".jsx", ".ts", ".tsx", ".html", ".vue")
THU_MUC_GIAO_DIEN = ("frontend/", "templates/", "static/")

#: Duong dan NGHIEM TRONG - hop dong muc 4.5 doi L3 o checkpoint.
DUONG_NGHIEM_TRONG = (
    "platform_core/credit.py", "platform_core/billing.py",
    "platform_core/job_runner.py", "platform_core/leases.py",
    "platform_core/auth", "server/auth", "alembic/",
)


def _git(*a: str, cay: Path | None = None) -> str:
    r = subprocess.run(["git", *a], cwd=str(cay or GOC), capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(a)} that bai:\n{r.stderr.strip()}")
    return r.stdout.strip()


def _git_thu(*a: str) -> str | None:
    """Nhu `_git` nhung tra `None` khi git tu choi - dung cho phep DO, khong
    dung cho phep GHI. Mot ref khong ton tai la mot cau tra loi, khong phai loi."""
    r = subprocess.run(["git", *a], cwd=str(GOC), capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip() if r.returncode == 0 else None


def tep_trang_thai() -> Path:
    return Path(_git("rev-parse", "--absolute-git-dir")) / TEN_TEP


def la_cay_chinh() -> bool:
    """Cay chinh la cay co `--git-dir` trung `--git-common-dir`.

    Cung phep do ma `tools/cay_rieng.py::la_cay_chinh` dung, va cung ly do:
    doan theo duong dan thi sai ngay khi ai do doi ten thu muc.
    """
    rieng = Path(_git("rev-parse", "--absolute-git-dir")).resolve()
    chung = _git("rev-parse", "--path-format=absolute", "--git-common-dir")
    return rieng == Path(chung).resolve()


def doc() -> dict:
    tep = tep_trang_thai()
    if not tep.is_file():
        return {"ho_so": "NORMAL"}
    try:
        du_lieu = json.loads(tep.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SystemExit(f"{tep} hong ({e}). Xoa no de ve NORMAL.") from e
    if not isinstance(du_lieu, dict):
        raise SystemExit(f"{tep} khong phai mot doi tuong JSON.")
    return du_lieu


def ghi(du_lieu: dict) -> None:
    tep = tep_trang_thai()
    tep.write_bytes(
        (json.dumps(du_lieu, ensure_ascii=False, indent=2, sort_keys=True)
         + "\n").encode("utf-8"))


def _nhanh() -> str:
    return _git("rev-parse", "--abbrev-ref", "HEAD")


def _lag() -> str:
    """Bao nhieu commit cua trunk chua co o cay nay."""
    ra = _git_thu("rev-list", "--count", f"HEAD..{TRUNK}")
    return ra if ra is not None else "?"


def governance_lech() -> tuple[list[str], list[str]]:
    """`(cu, di_truoc)` - tep governance da CU, va tep cay nay DI TRUOC trunk.

    🔴 **Phep so hai chieu la SAI, va no sai ve phia HANH DONG THUA.**

       Ban dau ham nay chi so `HEAD:<tep>` voi `TRUNK:<tep>` roi bao "lech".
       Do 09/09, ngay tren chinh cay viet ra no: cay di TRUOC trunk 3 commit,
       va cong cu bao *"LECH trunk o 3 tep -> `git merge admin-mvp-v3` truoc
       khi tin mot luot gate"*. Loi khuyen ay khong sai vo hai — no bao nguoi
       ta lam mot viec KHONG lam gi ca, va lam the giua mot chien dich dang do.

    ⭐ Thu phan biet duoc hai chieu la **diem hoa** (`merge-base`), khong phai
       hai dau mut. Voi moi tep, so ba blob:

           HEAD == goc  va  TRUNK != goc   ->  trunk doi, ta CU     (phai gop)
           HEAD != goc  va  TRUNK == goc   ->  ta doi, ta DI TRUOC  (binh thuong)
           ca hai != goc                   ->  PHAN KY             (phai gop, se co xung dot)

    So blob SHA chu khong so noi dung: git da bam san, va phep so nay dung ke
    ca khi mot ben thieu han tep do.
    """
    goc = _git_thu("merge-base", "HEAD", TRUNK)
    cu: list[str] = []
    di_truoc: list[str] = []
    for t in TEP_GOVERNANCE:
        cua_ta = _git_thu("rev-parse", f"HEAD:{t}")
        cua_trunk = _git_thu("rev-parse", f"{TRUNK}:{t}")
        if cua_trunk is None:
            continue          # trunk chua co tep nay - khong ket luan gi
        if cua_ta == cua_trunk:
            continue
        cua_goc = _git_thu("rev-parse", f"{goc}:{t}") if goc else None
        if cua_goc is not None and cua_ta == cua_goc:
            cu.append(t)                      # chi trunk doi
        elif cua_goc is not None and cua_trunk == cua_goc:
            di_truoc.append(t)                # chi ta doi
        else:
            cu.append(t)                      # phan ky - van phai gop
    return cu, di_truoc


def _bay_gio() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# ────────────────────────────────────────────────────────────────────────────
# Lenh
# ────────────────────────────────────────────────────────────────────────────

def _trang_thai() -> int:
    tt = doc()
    ho_so = str(tt.get("ho_so", "NORMAL"))
    cu, di_truoc = governance_lech()
    print(f"Cay        : {GOC}")
    print(f"Nhanh      : {_nhanh()}   HEAD {_git('rev-parse', '--short', 'HEAD')}")
    print(f"Trunk      : {TRUNK}   (cay nay thieu {_lag()} commit cua trunk)")
    print(f"Cay chinh  : {'CO' if la_cay_chinh() else 'khong (cay lien ket)'}")
    print(f"HO SO      : {ho_so}")
    if ho_so == "FAST_BUILD":
        print(f"  trang thai : {tt.get('trang_thai', '?')}")
        print(f"  baseline   : {tt.get('baseline_sha', '?')}")
        print(f"  pham vi    : {tt.get('pham_vi', '?')}")
        print(f"  bat luc    : {tt.get('bat_dau', '?')}")
    if cu:
        print(f"GOVERNANCE : CU o {len(cu)} tep (trunk da di tiep):")
        for t in cu:
            print(f"  - {t}")
        print(f"  -> `git merge {TRUNK}` truoc khi tin mot luot gate o cay nay.")
    elif di_truoc:
        print(f"GOVERNANCE : cay nay DI TRUOC trunk o {len(di_truoc)} tep "
              "- khong phai loi:")
        for t in di_truoc:
            print(f"  - {t}")
    else:
        print("GOVERNANCE : khop trunk")
    print("\nLuat: docs/00_LTT_OPERATING_CONTRACT.md muc 4.10")
    return 0


def _bat(pham_vi: str) -> int:
    if not pham_vi.strip():
        raise SystemExit("`bat` can `--pham-vi \"<mo ta ngan>\"`. Mot ho so "
                         "FAST_BUILD khong co pham vi thi khong dong bang duoc "
                         "feature set o buoc FEATURE_COMPLETE.")
    if la_cay_chinh():
        raise SystemExit(
            "Day la CAY CHINH. FAST_BUILD chi hop le trong mot cay tinh nang "
            "rieng biet (hop dong muc 4.10). Tao cay rieng truoc:\n"
            "  python tools/cay_rieng.py tao <ten>")
    nhanh = _nhanh()
    if nhanh in (TRUNK, "master") or "release" in nhanh or "phat-hanh" in nhanh:
        raise SystemExit(f"Nhanh `{nhanh}` la trunk/phat hanh - luon NORMAL.")

    tt = doc()
    if tt.get("ho_so") == "FAST_BUILD":
        raise SystemExit(f"Cay nay DA o FAST_BUILD tu {tt.get('bat_dau', '?')}. "
                         "`trang-thai` de xem, `tat` de tro ve NORMAL.")

    baseline = _git("rev-parse", "HEAD")
    ghi({"ho_so": "FAST_BUILD", "baseline_sha": baseline, "pham_vi": pham_vi,
         "trang_thai": "RESEARCH", "bat_dau": _bay_gio()})
    print(f"FAST_BUILD BAT cho {GOC}")
    print(f"  baseline : {baseline}")
    print(f"  pham vi  : {pham_vi}")
    print("  trang thai: RESEARCH")
    print(f"\nTep trang thai: {tep_trang_thai()}  (ngoai cay lam viec)")
    print("Buoc tiep: `python tools/ho_so_cay.py chuyen BUILDING`")
    return 0


def _tat() -> int:
    tep = tep_trang_thai()
    if not tep.is_file():
        print("Cay nay von da o NORMAL.")
        return 0
    tep.unlink()
    print(f"Da tro ve NORMAL. Da xoa {tep}")
    return 0


def _chuyen(dich: str) -> int:
    tt = doc()
    if tt.get("ho_so") != "FAST_BUILD":
        raise SystemExit("Cay nay dang o NORMAL - khong co may trang thai. "
                         "`bat --pham-vi \"...\"` truoc.")
    dich = dich.upper()
    if dich not in TRANG_THAI:
        raise SystemExit(f"Trang thai khong co: {dich}. "
                         f"Chon: {', '.join(TRANG_THAI)}")
    hien = str(tt.get("trang_thai", "RESEARCH"))
    if dich not in CHUYEN_DUOC.get(hien, ()):
        raise SystemExit(
            f"Khong chuyen thang {hien} -> {dich}. Tu {hien} chi di duoc toi: "
            f"{', '.join(CHUYEN_DUOC.get(hien, ())) or '(khong dau ca)'}")
    tt["trang_thai"] = dich
    tt.setdefault("lich_su", []).append({"tu": hien, "toi": dich,
                                         "luc": _bay_gio()})
    ghi(tt)
    print(f"{hien} -> {dich}")
    if dich == "CERTIFYING":
        print("\nKe hoach chung nhan:")
        return _no_kiem()
    return 0


def _phan_loai(duong: set[str]) -> dict[str, list[str]]:
    """Xep duong dan da doi thanh cac nhom QUYET DINH mot buoc chung nhan."""
    giao_dien = sorted(
        d for d in duong
        if d.endswith(DUOI_GIAO_DIEN) or any(t in d for t in THU_MUC_GIAO_DIEN))
    app = sorted({d.split("/")[1] for d in duong
                  if d.startswith("apps/") and len(d.split("/")) > 2})
    nghiem_trong = sorted(d for d in duong
                          if any(d.startswith(n) for n in DUONG_NGHIEM_TRONG))
    return {"giao_dien": giao_dien, "app": app, "nghiem_trong": nghiem_trong}


def _no_kiem() -> int:
    tt = doc()
    if tt.get("ho_so") != "FAST_BUILD":
        raise SystemExit("`no-kiem` chi co nghia trong FAST_BUILD: no do TU "
                         "baseline. O NORMAL, `gate.py --doi` da la cau tra loi.")
    baseline = str(tt.get("baseline_sha", ""))
    if not baseline:
        raise SystemExit("Trang thai thieu `baseline_sha`. `tat` roi `bat` lai.")

    sys.path.insert(0, str(GOC / "tools"))
    import thanh_phan as tp

    try:
        duong = tp.duong_da_doi(GOC, goc_so=baseline)
    except tp.KhongBiet as e:
        raise SystemExit(f"Khong doc duoc cay ({e}).") from e

    print(f"Baseline   : {baseline[:12]}")
    print(f"Pham vi    : {tt.get('pham_vi', '?')}")
    print(f"Trang thai : {tt.get('trang_thai', '?')}")
    print(f"\n{len(duong)} duong dan doi ke tu baseline.")
    if not duong:
        print("Chua co gi de chung nhan.")
        return 0

    phan = tp.bi_anh_huong(duong, GOC)
    nhom = _phan_loai(duong)

    if phan is None:
        print("Thanh phan : KHONG suy duoc (cham tep dung chung, hoac mot "
              "duong khong thanh phan nao so huu).")
        print("  -> buoc 2 duoi day TU HA CAP xuong gate DAY DU. Do la thiet "
              "ke, khong phai loi.")
        tep_test: set[str] = set()
    else:
        tep_test = tp.test_can_chay(phan, GOC)
        tep_test |= {t for t in tp.tep_test_da_doi(duong) if (GOC / t).is_file()}
        print(f"Thanh phan : {len(phan)} - {', '.join(sorted(phan))}")
        print(f"Tep test   : {len(tep_test)} (da dedupe)")

    if nhom["app"]:
        print(f"App cham   : {', '.join(nhom['app'])}")
    if nhom["giao_dien"]:
        print(f"Giao dien  : {len(nhom['giao_dien'])} tep -> DOI kiem trinh duyet")
    if nhom["nghiem_trong"]:
        print(f"NGHIEM TRONG: {', '.join(nhom['nghiem_trong'])}")

    print("\n--- KE HOACH CHUNG NHAN (thu tu theo gia, re truoc) ---")
    print("1. tinh/micro      python tools/gate.py --quick")
    print(f"2. gom targeted    python tools/gate.py --doi --tu {baseline[:12]}")
    print("3. tich hop        test tich hop cua cac app o tren")
    print("4. doi chieu legacy phep do parity da dong bang trong ban audit")
    print("5. Workflow E2E    E2E cua node + workflow run")
    if nhom["giao_dien"]:
        print("6. trinh duyet     https://app.lttstudios.com (URL CONG KHAI)")
    else:
        print("6. trinh duyet     KHONG CAN - khong tep giao dien nao doi")
    print("7. L3 mot lan      python tools/gate.py")
    if nhom["nghiem_trong"]:
        print("\n[!] Co duong NGHIEM TRONG trong dien thay doi: hop dong muc 7 "
              "doi L3 o checkpoint, khong chi o cuoi.")
    print("\nGia tri o buoc 3-5 khong suy duoc tu git; chung phu thuoc ban "
          "audit cua chinh chien dich nay.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Ho so van hanh cua cay nay (NORMAL / FAST_BUILD).")
    p.add_argument("lenh", choices=["trang-thai", "bat", "tat", "chuyen",
                                    "no-kiem"])
    p.add_argument("dich", nargs="?", default="",
                   help="voi `chuyen`: trang thai dich")
    p.add_argument("--pham-vi", default="",
                   help="voi `bat`: mo ta ngan pham vi chien dich")
    a = p.parse_args(argv)

    if a.lenh == "trang-thai":
        return _trang_thai()
    if a.lenh == "bat":
        return _bat(a.pham_vi)
    if a.lenh == "tat":
        return _tat()
    if a.lenh == "no-kiem":
        return _no_kiem()
    if not a.dich:
        raise SystemExit(f"`chuyen` can mot trang thai dich: "
                         f"{', '.join(TRANG_THAI)}")
    return _chuyen(a.dich)


if __name__ == "__main__":
    sys.exit(main())
