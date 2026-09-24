import json, pathlib, re, sys
sys.path.insert(0, r"D:\LTTSTUDIOSAPP-timeline")
from apps.auto_scan_video import canh as _canh
from platform_core import media as _media
BC = pathlib.Path(r"D:\LTTSTUDIOSAPP-gop\docs\auto_scan_video_final\bang_chung")
VID = pathlib.Path(r"C:\Users\Thang Tuong\Desktop\TEST VIDEO")
PHIM = {"v1": "\u5ec9\u4ef7\u7684\u725b\u80a0", "v2": "\u66b4\u96e8\u5929\u91ce\u5916",
        "v3": "\u6df1\u5ea6\u89e3\u6790"}
tong_k = tong_n = 0
for ma, mau in PHIM.items():
    tep = next(p for p in VID.glob("*.mp4") if mau in p.name)
    dur = float(_media.duration_seconds(str(tep)) or 0)
    kho = _canh.gop_canh_ngan(_canh.tim_moc(str(tep)), dur)
    moc = sorted({float(b) for b, _ in kho} | {float(k) for _, k in kho})
    doan = sorted(json.loads((BC / f"b1_chep_loi_moi/{ma}.json")
                  .read_text(encoding="utf-8"))["doan"], key=lambda d: d["bat"])
    k = sum(1 for d in doan
            if any(float(d["bat"]) < m < float(d["ket"]) for m in moc))
    cat_trong = [sum(1 for m in moc if float(d["bat"]) < m < float(d["ket"])) for d in doan]
    print(f"{ma}: {len(moc)-1} canh · {len(doan)} khe GOC · "
          f"khe DA vat qua >=1 cat canh: {k}/{len(doan)} = {k/len(doan):.1%} · "
          f"nhieu nhat {max(cat_trong)} cat trong MOT khe")
    tong_k += k; tong_n += len(doan)
print(f"\nTONG: {tong_k}/{tong_n} = {tong_k/tong_n:.1%} khe HIEN NAY da vat qua cat canh")
