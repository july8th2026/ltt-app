"""D5 — GOP KHE nhung ⛔ KHONG VAT QUA CAT CANH.

⭐ Tran khe khong con la mot HANG SO muon cua phu de (7 s = tran DOC, `N-34`).
   Thu that su chan mot khe long tieng dai la **cat canh**: giong chay xuyen qua
   cho chuyen canh la loi khan gia THAY NGAY. ⇒ Chan bang CANH, ⛔ khong bang GIAY.
   Va tran khe dai nhat se do **DU LIEU** quyet, ⛔ khong do ta dat.

Ranh gioi canh lay bang CHINH bo tach cua san pham:
   `apps/auto_scan_video/canh.py` — PySceneDetect ContentDetector(35).
"""
from __future__ import annotations

import json
import pathlib
import statistics as st
import sys

GOC = pathlib.Path(r"D:\LTTSTUDIOSAPP-timeline")
sys.path.insert(0, str(GOC))

import re  # noqa: E402

from apps.auto_scan_video import canh as _canh  # noqa: E402

BC = pathlib.Path(r"D:\LTTSTUDIOSAPP-gop\docs\auto_scan_video_final\bang_chung")
VID = pathlib.Path(r"C:\Users\Thang Tuong\Desktop\TEST VIDEO")
PHIM = {"v1": "\u5ec9\u4ef7\u7684\u725b\u80a0",
        "v2": "\u66b4\u96e8\u5929\u91ce\u5916",
        "v3": "\u6df1\u5ea6\u89e3\u6790"}
RATE = 3.284
TRAN_TANG_TOC = 1.15


def am(s: str) -> int:
    return len([t for t in re.sub(r"[^\w\s]", " ", str(s), flags=re.UNICODE).split() if t])


def vua(a: float, ns: float) -> bool:
    return a / RATE / TRAN_TANG_TOC <= ns


def doc_khe(ma: str) -> list[dict]:
    b1 = {d["ma"]: d for d in json.loads(
        (BC / f"b1_chep_loi_moi/{ma}.json").read_text(encoding="utf-8"))["doan"]}
    seq = sorted(b1.values(), key=lambda d: d["bat"])
    sau = {seq[i]["ma"]: (seq[i + 1]["bat"] if i + 1 < len(seq) else seq[i]["ket"])
           for i in range(len(seq))}
    ra = []
    for t in json.loads((BC / f"b2_dich_nen/{ma}_nen.json")
                        .read_text(encoding="utf-8"))["doan"]:
        s = b1.get(t["ma"])
        vi = str(t.get("chu_dich") or "")
        if not s or not vi or not (s.get("tu") or []):
            continue          # ⛔ bo doan HONG (N-39)
        ra.append({"bat": float(s["bat"]), "sau": float(sau[t["ma"]]), "am": am(vi)})
    return sorted(ra, key=lambda k: k["bat"])


def gop_trong_canh(khe: list[dict], moc_canh: list[float], tran: int | None) -> list[dict]:
    """Gop khe lien ke, ⛔ DUNG lai o moi cat canh. `tran=None` = ⛔ khong gioi han."""
    def cung_canh(t0: float, t1: float) -> bool:
        return not any(t0 < m <= t1 for m in moc_canh)

    ra, i = [], 0
    while i < len(khe):
        a, bat, sau, d = khe[i]["am"], khe[i]["bat"], khe[i]["sau"], 1
        while (tran is None or d < tran) and i + d < len(khe) \
                and not vua(a, sau - bat) and cung_canh(bat, khe[i + d]["sau"]):
            a += khe[i + d]["am"]
            sau = khe[i + d]["sau"]
            d += 1
        ra.append({"am": a, "ns": sau - bat, "bat": bat, "so_gop": d})
        i += d
    return ra


def main() -> None:
    ket: dict = {}
    for ma, mau in PHIM.items():
        tep = next(p for p in VID.glob("*.mp4") if mau in p.name)
        from platform_core import media as _media
        thoi_luong = float(_media.duration_seconds(str(tep)) or 0.0)
        # ⭐ Dung DUNG adapter cua san pham (ContentDetector(35)), roi chinh phep
        #    gop canh ngan cua no — ⛔ khong tu dat nguong nao.
        khoang = _canh.gop_canh_ngan(_canh.tim_moc(str(tep)), thoi_luong)
        moc = sorted({float(b) for b, _ in khoang} | {float(k) for _, k in khoang})
        khe = doc_khe(ma)
        khoi: dict = {"so_canh": len(khoang), "thoi_luong_s": round(thoi_luong, 1),
                      "so_khe_goc": len(khe)}
        # bao nhieu CANH chi co MOT khe => gop ⛔ khong giup gi
        theo_canh: dict[int, int] = {}
        for k in khe:
            j = sum(1 for m in moc if m <= k["bat"])
            theo_canh[j] = theo_canh.get(j, 0) + 1
        khoi["canh_co_khe"] = len(theo_canh)
        khoi["canh_chi_MOT_khe"] = sum(1 for v in theo_canh.values() if v == 1)
        for nhan, tran in (("gop<=2", 2), ("gop<=3", 3), ("gop<=5", 5),
                           ("gop TU DO trong canh", None)):
            g = gop_trong_canh(khe, moc, tran)
            dai = sorted(x["ns"] for x in g)
            khoi[nhan] = {
                "so_khe": len(g),
                "vua": sum(1 for x in g if vua(x["am"], x["ns"])),
                "khe_dai_nhat_s": round(max(dai), 2),
                "khe_trung_vi_s": round(st.median(dai), 2),
                "khe_tren_7s": sum(1 for x in dai if x > 7.0),
            }
        ket[ma] = khoi
    print(json.dumps(ket, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
