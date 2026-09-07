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
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess

GOC = pathlib.Path(__file__).resolve().parents[1]
CHAY = pathlib.Path("C:/LTTPlatform/app")
TRUOC = pathlib.Path("C:/LTTPlatform/app.previous")

#: Nam goi ma deploy chep va la thu chay that. `docs/` cung duoc chep nhung
#: khong duoc phuc vu, khong duoc import — de ngoai de phep do noi ve MA.
GOI = ("server", "platform_core", "apps", "alembic", "sdk")


def _bam(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


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
    """`duong/dan.py -> sha1 cua blob`, doc tu chinh commit."""
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
        if loai == "blob" and duong.endswith(".py"):
            ra[duong] = blob
    return ra


def _noi_dung_blob(blob: str) -> bytes:
    r = subprocess.run(["git", "cat-file", "blob", blob],
                       cwd=GOC, capture_output=True)
    return r.stdout if r.returncode == 0 else b"\x00KHONG DOC DUOC"


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

    lech, thieu, thua, vi_du = 0, 0, 0, []
    for duong, blob in trong_commit.items():
        q = CHAY / duong
        if not q.exists():
            thieu += 1
            if len(vi_du) < 6:
                vi_du.append(f"THIEU ben may chu : {duong}")
            continue
        if _bam(q.read_bytes()) != _bam(_noi_dung_blob(blob)):
            lech += 1
            if len(vi_du) < 6:
                vi_du.append(f"LECH noi dung     : {duong}")

    # ⭐ Chieu nguoc lai cung phai hoi: may chu co mang tep KHONG co trong
    #    commit khong? Do la dau hieu deploy di tu mot cay BAN — dung thu
    #    phep do "so voi cay lam viec" khong bao gio thay.
    for g in GOI:
        goc_g = CHAY / g
        if not goc_g.is_dir():
            continue
        for q in goc_g.rglob("*.py"):
            if "__pycache__" in q.parts:
                continue
            duong = q.relative_to(CHAY).as_posix()
            if duong not in trong_commit:
                thua += 1
                if len(vi_du) < 6:
                    vi_du.append(f"THUA (khong co trong commit): {duong}")

    print(f"  doi chieu voi commit : {sha[:12]}")
    print(f"  tep .py trong commit : {len(trong_commit)}")
    print(f"  lech noi dung        : {lech}")
    print(f"  thieu ben may chu    : {thieu}")
    print(f"  thua ben may chu     : {thua}")
    for v in vi_du:
        print(f"    {v}")
    print()

    dat = lech == 0 and thieu == 0 and thua == 0
    print("DAT — ban dang chay khop tuyet doi mot commit xac dinh" if dat
          else "KHONG DAT")
    return 0 if dat else 1


if __name__ == "__main__":
    raise SystemExit(main())
