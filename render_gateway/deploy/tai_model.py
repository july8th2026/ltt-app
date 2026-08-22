"""
tai_model.py - tai trong so model ve MAY B, kem bang ke sha256.

    E:\\AI\\venv\\Scripts\\python.exe tai_model.py --ban-khai models_hidream_o1.json

Chay bang venv CUA COMFYUI vi no da co `huggingface_hub`. Day la dung ho, KHONG
cai them gi vao venv do - quy tac cua CLAUDE.md.

** VI SAO CAN BANG KE: trong so la DU LIEU, khong phai ma. Chung khong nam trong
   git va khong duoc sao luu. Bang ke `(ten, nguon, sha256, ngay, dung luong)` la
   thu duy nhat cho phep dung lai dung y nguyen bo model sau khi cai lai may -
   buoc 17 cua bo build pack doi dieu nay.

** TAI TIEP DUOC: `huggingface_hub` tu noi lai file dang do. Mot lan rot mang giua
   chung khong bat tai lai 16 GB tu dau.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

TEN_BANG_KE = "BANG_KE.json"


def sha256(duong: Path, chunk: int = 8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with duong.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ban-khai", required=True, type=Path)
    ap.add_argument("--goc", type=Path, default=None,
                    help="ghi de thu muc goc trong ban khai")
    ap.add_argument("--chi", type=int, default=None,
                    help="chi tai file co uu_tien nay")
    a = ap.parse_args()

    khai = json.loads(a.ban_khai.read_text(encoding="utf-8"))
    goc = a.goc or Path(khai["goc"])
    goc.mkdir(parents=True, exist_ok=True)

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("KHONG co huggingface_hub. Chay bang E:\\AI\\venv\\Scripts\\python.exe")
        return 2

    bang_ke_duong = goc / TEN_BANG_KE
    bang_ke = {}
    if bang_ke_duong.is_file():
        bang_ke = json.loads(bang_ke_duong.read_text(encoding="utf-8"))
    bang_ke.setdefault("files", {})

    files = sorted(khai["files"], key=lambda x: x.get("uu_tien", 99))
    if a.chi is not None:
        files = [f for f in files if f.get("uu_tien") == a.chi]

    for muc in files:
        ten = Path(muc["file"]).name
        dich_thu_muc = goc / muc["thu_muc"]
        dich_thu_muc.mkdir(parents=True, exist_ok=True)
        dich = dich_thu_muc / ten

        if dich.is_file() and bang_ke["files"].get(ten, {}).get("sha256"):
            print(f"[BO QUA] {ten} da co va da co sha256", flush=True)
            continue

        print(f"[TAI]   {ten}  (~{muc.get('gb_mong_doi', '?')} GB)  {muc.get('vai','')}",
              flush=True)
        t0 = time.time()
        tam = hf_hub_download(repo_id=muc["repo"], filename=muc["file"],
                              local_dir=str(goc / "_hf"))
        dt = time.time() - t0
        # hf_hub_download giu cay thu muc cua repo; ta dua file ra dung cho ComfyUI doc.
        Path(tam).replace(dich)
        cd = dich.stat().st_size
        print(f"        xong {cd / 1024**3:.2f} GB trong {dt/60:.1f} phut "
              f"({cd / 1024**2 / max(dt, 1):.1f} MB/s)", flush=True)

        print("        dang tinh sha256...", flush=True)
        bam = sha256(dich)
        bang_ke["files"][ten] = {
            "repo": muc["repo"],
            "duong_dan_repo": muc["file"],
            "sha256": bam,
            "byte": cd,
            "gb": round(cd / 1024 ** 3, 2),
            "ngay_tai": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "vai": muc.get("vai", ""),
        }
        bang_ke["cap_nhat"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        # UTF-8 KHONG BOM - quy tac 1 cua CLAUDE.md.
        bang_ke_duong.write_text(
            json.dumps(bang_ke, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"        sha256 {bam[:16]}... da ghi vao bang ke", flush=True)

    # Don cay tam cua huggingface_hub neu no rong.
    tam_goc = goc / "_hf"
    if tam_goc.is_dir():
        for p in sorted(tam_goc.rglob("*"), reverse=True):
            try:
                p.rmdir() if p.is_dir() else p.unlink()
            except OSError:
                pass
        try:
            tam_goc.rmdir()
        except OSError:
            pass

    print("\nBANG KE:", bang_ke_duong)
    for ten, m in bang_ke["files"].items():
        print(f"  {ten:52} {m['gb']:6.2f} GB  {m['sha256'][:16]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
