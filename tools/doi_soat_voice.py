"""doi_soat_voice.py — CHI DOC. Commit vung Voice nao chua co dong so cai?

    python tools/doi_soat_voice.py            # bang + ma thoat
    python tools/doi_soat_voice.py --json

INV-CHU-1 (spec 2026-09-11 §5): moi commit cham vung Voice ma chua len trunk
phai co DUNG MOT dong trong docs/LTT_VOICE/HOP_NHAT/SO_CAI.json.

Chay o BA thoi diem: dau phien, truoc ff, truoc deploy. KHONG phai buoc gate:
gate chay o moi cay va khong duoc do vi nhanh cua phien khac.
Khong ghi gi: chi `git for-each-ref` va `git log`.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

GOC = pathlib.Path(__file__).resolve().parents[1]
SO_CAI = GOC / "docs" / "LTT_VOICE" / "HOP_NHAT" / "SO_CAI.json"
KET_CUC = ("KEEP", "DROP", "FIX")
_SHA = re.compile(r"^[0-9a-f]{8,40}$")


def _git(goc: pathlib.Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(goc), *a], check=True,
                          capture_output=True, text=True,
                          encoding="utf-8").stdout


def nap_so_cai(p: pathlib.Path = SO_CAI) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def kiem_hinh_dang(so: dict) -> list:
    loi = []
    for k in ("trunk", "rc", "vung", "nguon", "yeu_cau", "cap_phat_test"):
        if k not in so:
            loi.append(f"thieu khoa `{k}`")
    if not so.get("vung"):
        loi.append("`vung` rong — doi soat se xanh-rong")
    thay = set()
    for i, d in enumerate(so.get("nguon") or ()):
        sha = str(d.get("sha") or "")
        if not _SHA.fullmatch(sha):
            loi.append(f"nguon[{i}].sha khong phai sha hop le: {sha!r}")
        if sha[:8] in thay:
            loi.append(f"nguon[{i}].sha trung: {sha[:8]}")
        thay.add(sha[:8])
        if d.get("ket_cuc") not in KET_CUC:
            loi.append(f"nguon[{i}].ket_cuc phai la {KET_CUC}: {d.get('ket_cuc')!r}")
        if len(str(d.get("ly_do") or "").strip()) < 3:
            loi.append(f"nguon[{i}].ly_do rong — mot ket cuc khong ly do la mot cua bi quen")
    return loi


def commit_chua_doi_soat(so: dict, *, goc: pathlib.Path = GOC,
                         trunk: str = "") -> list:
    trunk = trunk or so["trunk"]
    rc = str((so.get("rc") or {}).get("nhanh") or "")
    co = {str(d["sha"])[:8] for d in so.get("nguon") or ()}
    refs = _git(goc, "for-each-ref", "--format=%(refname:short)",
                "refs/heads", "refs/remotes").split()
    ra, thay = [], set()
    for ref in refs:
        if ref in (trunk, rc, f"origin/{trunk}", f"origin/{rc}") or ref.endswith("/HEAD"):
            continue
        out = _git(goc, "log", "--no-merges", "--format=%H\t%s",
                   f"{trunk}..{ref}", "--", *so["vung"])
        for dong in out.splitlines():
            sha, _, tieu_de = dong.partition("\t")
            if sha[:8] in co or sha in thay:
                continue
            thay.add(sha)
            ra.append({"sha": sha, "nhanh": ref, "tieu_de": tieu_de})
    return ra


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    so = nap_so_cai()
    loi = kiem_hinh_dang(so)
    thieu = [] if loi else commit_chua_doi_soat(so)
    if a.json:
        print(json.dumps({"loi_hinh_dang": loi, "chua_doi_soat": thieu},
                         ensure_ascii=False, indent=2))
    else:
        for s in loi:
            print(f"  LOI  {s}")
        for x in thieu:
            print(f"  THIEU {x['sha'][:8]}  {x['nhanh']:45s} {x['tieu_de'][:70]}")
        print(f"RESULT: {'PASS' if not (loi or thieu) else 'FAIL'} "
              f"({len(thieu)} commit chua doi soat, {len(loi)} loi hinh dang)")
    return 1 if (loi or thieu) else 0


if __name__ == "__main__":
    sys.exit(main())
