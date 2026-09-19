"""Quét tài liệu: tham chiếu chết (tệp/lệnh trong `…` không tồn tại) + thuật ngữ đã bị thay.
Chỉ đọc. Không nối vào gate. Dùng: python tools/quet_tai_lieu.py docs CLAUDE.md --json out.json
Ngoại lệ đã kiểm tay: bảng `| tệp | mẫu | lý do |` trong docs/_luutru/NGOAI_LE_QUET.md (glob, mặc định bật
khi tệp tồn tại; `--ngoai-le ""` để tắt) - dòng khớp cả tệp lẫn mẫu bị bỏ khỏi kết quả."""
import argparse, fnmatch, json, re, subprocess, sys
from pathlib import Path

_reconf = getattr(sys.stdout, "reconfigure", None)
if _reconf:
    _reconf(encoding="utf-8", errors="replace")

DUONG = re.compile(r"`([A-Za-z0-9_.\-]+(?:[/\\][A-Za-z0-9_.\-]+)+\.(?:py|ps1|md|mjs|js|ts|rs|json|yml|yaml|toml|bat))`")

def doc_tu_dien(p):
    cap = []
    if p and Path(p).exists():
        for dong in Path(p).read_text(encoding="utf-8").splitlines():
            o = [x.strip() for x in dong.strip().strip("|").split("|")]
            if len(o) >= 2 and o[0] and o[0] not in ("cũ",) and not set(o[0]) <= set("-: "):
                cap.append((o[0], o[1]))
    return cap

def doc_ngoai_le(p):
    """Chỉ đọc các bảng có tiêu đề đúng `| tệp | mẫu | lý do |` (bảng máy); bảng/đoạn văn khác bỏ qua."""
    luat, trong_bang = [], False
    if not p or not Path(p).is_file():
        return luat
    for dong in Path(p).read_text(encoding="utf-8").splitlines():
        s = dong.strip()
        if not s.startswith("|"):
            trong_bang = False
            continue
        o = [x.strip().strip("`") for x in s.strip("|").split("|")]
        if [x.lower() for x in o[:3]] == ["tệp", "mẫu", "lý do"]:
            trong_bang = True
            continue
        if trong_bang and len(o) >= 2 and o[0] and not set(o[0]) <= set("-: "):
            luat.append((o[0].replace("\\", "/"), o[1]))
    return luat


def la_ngoai_le(luat, tep, mau):
    tep = tep.replace("\\", "/")
    return any(fnmatch.fnmatchcase(tep, t) and fnmatch.fnmatchcase(mau, m) for t, m in luat)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dich", nargs="+")
    ap.add_argument("--goc", default=".")
    ap.add_argument("--tu-dien", default="docs/_luutru/TU_DIEN_DA_THAY.md")
    ap.add_argument("--ngoai-le", default="docs/_luutru/NGOAI_LE_QUET.md")
    ap.add_argument("--json")
    a = ap.parse_args()
    goc = Path(a.goc).resolve()
    tu_dien = doc_tu_dien(a.tu_dien if Path(a.tu_dien).is_absolute() else goc / a.tu_dien)
    ngoai_le = doc_ngoai_le(a.ngoai_le and (a.ngoai_le if Path(a.ngoai_le).is_absolute() else goc / a.ngoai_le))
    tep = []
    for d in a.dich:
        p = goc / d
        tep += sorted(p.rglob("*.md")) if p.is_dir() else [p]
    # Tham chieu hop le neu: ton tai tu goc kho, tu thu muc cua tep .md, hoac la DUOI cua mot tep git dang theo doi
    # (tai lieu hay viet `ltt_llm/ngan_sach.py` thay vi `apps/ltt_llm/ngan_sach.py`) - giam bao chet gia.
    try:
        theo_doi = subprocess.run(["git", "-C", str(goc), "ls-files"], capture_output=True, text=True,
                                  encoding="utf-8", errors="replace").stdout.splitlines()
    except OSError:
        theo_doi = []
    duoi = set()
    for t in theo_doi:
        phan = t.split("/")
        for k in range(len(phan)):
            duoi.add("/".join(phan[k:]))

    def song(rel, f):
        return (goc / rel).exists() or (f.parent / rel).exists() or rel in duoi

    kq = []
    for f in tep:
        if "_luutru" in f.parts:
            continue
        for i, dong in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in DUONG.finditer(dong):
                rel = m.group(1).replace("\\", "/")
                if not song(rel, f):
                    kq.append({"loai": "CHET", "tep": str(f.relative_to(goc)), "dong": i, "mau": rel, "goi_y": ""})
            for cu, moi in tu_dien:
                if cu.lower() in dong.lower():
                    kq.append({"loai": "THAY", "tep": str(f.relative_to(goc)), "dong": i, "mau": cu, "goi_y": moi})
    kq = [r for r in kq if not la_ngoai_le(ngoai_le, r["tep"], r["mau"])]
    for r in kq:
        print(f'{r["loai"]} {r["tep"]}:{r["dong"]} {r["mau"]} -> {r["goi_y"]}')
    if a.json:
        Path(a.json).write_text(json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")

if __name__ == "__main__":
    main()
