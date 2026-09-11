"""Nghiem thu mot luot deploy — doi chieu bam voi COMMIT, khong voi cay lam viec.

    python tools\\nghiem_thu_deploy.py

⛔ `EXITCODE=0` KHONG phai bang chung. `docs/16_CAP_NHAT_VA_DEPLOY.md` noi
   thang: doi chieu bam. Cong cu nay lam viec do, va lam dung mot chuyen ma
   hai phien deu tung lam sai trong cung mot ngay.

## 🔴 Vi sao so voi COMMIT chu khong so voi cay lam viec

Ban dau ca hai phien deu viet phep do dang:

    for p in (NGUON / "server").rglob("*.py"):        # NGUON = D:\\LTTSTUDIOSAPP
        so_sanh(p, CHAY / p.relative_to(NGUON))

Do 07/09/2026: no bao **2 tep LECH** ngay sau mot luot deploy thanh cong.
Deploy khong hong. Cay lam viec da doi **sau** luc chep — mot phien khac vua
commit vao do.

⇒ Trong mot kho co nhieu phien, **cay lam viec khong phai mot moc**. No la mot
  moc DANG CHUYEN DONG. Thu duy nhat dung yen la mot commit.

🔴 Va chieu nguy hiem khong phai bao dong gia. La chieu nguoc lai: neu ai do
   deploy tu mot cay BAN, phep do "so voi cay" se bao **0 lech** — trong khi
   ban tren may chu khac han commit ma `dau_van_tay.json` dang khai. Mot loi
   **bao an toan gia**, va no pha dung menh de ma ca `dau_van_tay.json`,
   `/health/version` lan phep doi chieu nay cung dung len:

       ban dang chay = MOT COMMIT XAC DINH

⭐ Nen cong cu nay doc `dau_van_tay.json` cua ban DANG CHAY de biet no khai
   minh la commit nao, roi so tung tep voi `git show <sha>:<duong dan>`. Neu
   may chu mang thu khong co trong commit ay, no noi ra.

RC1 11/09: so moi tep, khong chi .py trong GOI -- mot deploy lech JS/CSS/HTML
truoc day van tra DAT vi phep do cu chi soi .py.

Fix round 1 (11/09): mot deploy DUNG van "thua" 9 tep vendor binary gitignored
co chu dich (`apps/upscalevideo/vendor/...`) vi chung duoc `setup/2-cai-dat.ps1`
chep RIENG qua $VAN_CHUYEN, khong qua `git archive`. Doc lai danh sach nay TU
CHINH tep .ps1 do (khong go lai) va xep rieng thanh nhom `van_chuyen` -- KHONG
tinh la loi. Mot `thua` KHONG nam trong $VAN_CHUYEN thi van la loi that.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess

GOC = pathlib.Path(__file__).resolve().parents[1]
CHAY = pathlib.Path("C:/LTTPlatform/app")
TRUOC = pathlib.Path("C:/LTTPlatform/app.previous")

#: Nam goi ma deploy chep va la thu chay that. `docs/` cung duoc chep nhung
#: khong duoc phuc vu, khong duoc import — de ngoai de phep do noi ve MA.
GOI = ("server", "platform_core", "apps", "alembic", "sdk")


def bam_git(b: bytes) -> str:
    """Sha1 cua mot git blob - de so truc tiep voi blob-sha tu `ls-tree`,
    khong can `git cat-file` doc lai tung tep tren may chu."""
    tieu_de = ("blob %d" % len(b)) + chr(0)
    return hashlib.sha1(tieu_de.encode() + b).hexdigest()


def so_sanh(trong_commit: dict[str, str], tren_may: dict[str, bytes],
            van_chuyen: list[str] | None = None) -> dict:
    """Ham thuan, khong I/O: so blob-sha cua commit voi noi dung tren may.

    `tren_may` la duong -> bytes (chua bam) — ham nay tu bam bang `bam_git`
    de so truc tiep voi gia tri co san trong `trong_commit`.

    `van_chuyen` la danh sach mau duong kieu `$VAN_CHUYEN` (vd dang Windows `apps\\*\\vendor`)
    — tai san gitignored ma deploy VAN chep rieng (`docs/16...`,
    `tests/test_505_nguon_ban_giao.py`). Mot tep `thua` roi vao mot mau trong do
    la TAI SAN DA KHAI, xep rieng vao `van_chuyen`, KHONG tinh la loi. Mot tep
    `thua` khong khop mau nao van la loi that."""
    lech: list[str] = []
    thieu: list[str] = []
    for duong, blob in trong_commit.items():
        if duong not in tren_may:
            thieu.append(duong)
        elif bam_git(tren_may[duong]) != blob:
            lech.append(duong)
    mau_khai = van_chuyen or []
    thua: list[str] = []
    da_khai: list[str] = []
    for d in tren_may:
        if d in trong_commit:
            continue
        if any(_phu_boi(m, d) for m in mau_khai):
            da_khai.append(d)
        else:
            thua.append(d)
    return {"lech": sorted(lech), "thieu": sorted(thieu), "thua": sorted(thua),
            "van_chuyen": sorted(da_khai)}


def _phu_boi(mau: str, duong: str) -> bool:
    """Mau kieu Windows (co the co `*`), co the phu `duong` (posix) khong —
    giong het `tests/test_505_nguon_ban_giao.py::_phu_boi`."""
    m = mau.replace("\\", "/")
    if "*" not in m:
        return duong == m or duong.startswith(m.rstrip("/") + "/")
    dau, sau = m.split("*", 1)
    return duong.startswith(dau) and sau.strip("/") in duong


def doc_van_chuyen(setup_ps1: pathlib.Path | None = None) -> list[str]:
    """Doc `$VAN_CHUYEN` tu `setup/2-cai-dat.ps1` — NGUON DUY NHAT cho danh
    sach tai san gitignored ma deploy van chep rieng, dung chung voi
    `tests/test_505_nguon_ban_giao.py::_van_chuyen`. Khong go lai danh sach
    o day."""
    tep = setup_ps1 or (GOC / "setup" / "2-cai-dat.ps1")
    if not tep.exists():
        return []
    van_ban = tep.read_text(encoding="ascii", errors="replace")
    m = re.search(r"\$VAN_CHUYEN = @\((.*?)\)", van_ban, re.S)
    if not m:
        return []
    return re.findall(r"'([^']+)'", m.group(1))


def _doc_marker(thu_muc: pathlib.Path) -> tuple[str, str]:
    tep = thu_muc / "dau_van_tay.json"
    if not tep.exists():
        return "", ""
    try:
        d = json.loads(tep.read_text(encoding="utf-8"))
    except ValueError:
        return "", ""
    return str(d.get("commit") or ""), str(d.get("luc") or "")


def _tep_trong_commit(sha: str) -> dict[str, str]:
    """`duong/dan -> sha1 cua blob`, MOI tep trong GOI (khong chi .py), doc tu chinh commit."""
    r = subprocess.run(["git", "ls-tree", "-r", sha, "--"] + list(GOI),
                       cwd=GOC, capture_output=True, text=True)
    if r.returncode != 0:
        return {}
    ra = {}
    for dong in r.stdout.splitlines():
        try:
            meta, duong = dong.split("\t", 1)
            _mode, loai, blob = meta.split()
        except ValueError:
            continue
        if loai == "blob":
            ra[duong] = blob
    return ra


def _tep_tren_may(goc: pathlib.Path) -> dict[str, bytes]:
    """`duong/dan -> noi dung`, quet toan bo GOI tren may (bo __pycache__/.pyc)."""
    ra: dict[str, bytes] = {}
    for g in GOI:
        goc_g = goc / g
        if not goc_g.is_dir():
            continue
        for q in goc_g.rglob("*"):
            if not q.is_file():
                continue
            if "__pycache__" in q.parts or q.suffix == ".pyc":
                continue
            duong = q.relative_to(goc).as_posix()
            ra[duong] = q.read_bytes()
    return ra


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--sha", default="",
                   help="commit de doi chieu (mac dinh: doc dau_van_tay.json)")
    a = p.parse_args()

    sha_chay, luc_chay = _doc_marker(CHAY)
    sha_truoc, luc_truoc = _doc_marker(TRUOC)

    print(f"  dang chay : {sha_chay[:12] or '(khong co marker)'}  {luc_chay}")
    print(f"  duong lui : {sha_truoc[:12] or '(khong co)'}  {luc_truoc}")
    print()

    sha = a.sha or sha_chay
    if not sha:
        print("  KHONG BIET doi chieu voi commit nao — thieu dau_van_tay.json")
        print("  (mot may chu chay thang tu cay nguon se khong co tep nay)")
        return 1

    trong_commit = _tep_trong_commit(sha)
    if not trong_commit:
        print(f"  khong doc duoc commit {sha[:12]} trong kho nay.")
        print("  Co the may chu dang chay mot commit CHUA duoc day/fetch ve day.")
        return 1

    tren_may = _tep_tren_may(CHAY)
    van_chuyen = doc_van_chuyen()
    ket_qua = so_sanh(trong_commit, tren_may, van_chuyen)
    so_khong_py = sum(1 for d in trong_commit if not d.endswith(".py"))
    so_van_chuyen = len(ket_qua["van_chuyen"])

    vi_du: list[str] = []
    for duong in ket_qua["lech"]:
        if len(vi_du) < 6:
            vi_du.append(f"LECH noi dung     : {duong}")
    for duong in ket_qua["thieu"]:
        if len(vi_du) < 6:
            vi_du.append(f"THIEU ben may chu : {duong}")
    for duong in ket_qua["thua"]:
        if len(vi_du) < 6:
            vi_du.append(f"THUA (khong co trong commit): {duong}")

    lech, thieu, thua = len(ket_qua["lech"]), len(ket_qua["thieu"]), len(ket_qua["thua"])

    print(f"  doi chieu voi commit       : {sha[:12]}")
    print(f"  tep trong commit           : {len(trong_commit)}")
    print(f"  tep khong .py trong commit : {so_khong_py}")
    print(f"  lech noi dung              : {lech}")
    print(f"  thieu ben may chu          : {thieu}")
    print(f"  thua ben may chu           : {thua}")
    print(f"  tai san ngoai commit DA KHAI (van_chuyen) : {so_van_chuyen}")
    for v in vi_du:
        print(f"    {v}")
    print()

    dat = lech == 0 and thieu == 0 and thua == 0
    print("DAT — ban dang chay khop tuyet doi mot commit xac dinh" if dat
          else "KHONG DAT")
    return 0 if dat else 1


if __name__ == "__main__":
    raise SystemExit(main())
