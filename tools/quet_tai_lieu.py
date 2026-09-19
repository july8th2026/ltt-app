"""Quét tài liệu: tham chiếu chết (tệp/lệnh trong `…` không tồn tại) + thuật ngữ đã bị thay.
Chỉ đọc. Không nối vào gate. Dùng: python tools/quet_tai_lieu.py docs CLAUDE.md --json out.json"""
import argparse, json, re, sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

DUONG = re.compile(r"`([A-Za-z0-9_.\-]+(?:[/\\][A-Za-z0-9_.\-]+)+\.(?:py|ps1|md|mjs|js|ts|rs|json|yml|yaml|toml|bat))`")

def doc_tu_dien(p):
    cap = []
    if p and Path(p).exists():
        for dong in Path(p).read_text(encoding="utf-8").splitlines():
            o = [x.strip() for x in dong.strip().strip("|").split("|")]
            if len(o) >= 2 and o[0] and o[0] not in ("cũ",) and not set(o[0]) <= set("-: "):
                cap.append((o[0], o[1]))
    return cap

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dich", nargs="+")
    ap.add_argument("--goc", default=".")
    ap.add_argument("--tu-dien", default="docs/_luutru/TU_DIEN_DA_THAY.md")
    ap.add_argument("--json")
    a = ap.parse_args()
    goc = Path(a.goc).resolve()
    tu_dien = doc_tu_dien(a.tu_dien if Path(a.tu_dien).is_absolute() else goc / a.tu_dien)
    tep = []
    for d in a.dich:
        p = goc / d
        tep += sorted(p.rglob("*.md")) if p.is_dir() else [p]
    kq = []
    for f in tep:
        if "_luutru" in f.parts:
            continue
        for i, dong in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in DUONG.finditer(dong):
                rel = m.group(1).replace("\\", "/")
                if not (goc / rel).exists():
                    kq.append({"loai": "CHET", "tep": str(f.relative_to(goc)), "dong": i, "mau": rel, "goi_y": ""})
            for cu, moi in tu_dien:
                if cu.lower() in dong.lower():
                    kq.append({"loai": "THAY", "tep": str(f.relative_to(goc)), "dong": i, "mau": cu, "goi_y": moi})
    for r in kq:
        print(f'{r["loai"]} {r["tep"]}:{r["dong"]} {r["mau"]} -> {r["goi_y"]}')
    if a.json:
        Path(a.json).write_text(json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")

if __name__ == "__main__":
    main()
