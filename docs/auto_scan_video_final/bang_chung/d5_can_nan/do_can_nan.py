"""D5 — ĐO TRƯỚC KHI XÂY: ba phim có THẬT SỰ cần nắn thời lượng không?

⛔ Chỉ ĐỌC bằng chứng đã có. ⛔ Không chạy TTS, ⛔ không chạy LLM, ⛔ không GPU.

Nguồn (chỉ đọc, cây `LTTSTUDIOSAPP-gop`):
    b1_chep_loi_moi/v{1,2,3}.json    khe + lời gốc (sau `cat_doan`)
    b2_dich_nen/v{1,2,3}_nen.json    bản dịch tiếng Việt (`chu_dich`)
    fix_toc_do/vong_dau_moi_v*.json  TTS THẬT: `am_tiet` + `giay_am`

⭐ Bộ đếm âm tiết được HIỆU CHỈNH với trường `am_tiet` có sẵn: khớp 18/18.
   ⛔ Không tự định nghĩa một đơn vị mới rồi so với số của người khác (N-34).
"""
from __future__ import annotations

import json
import pathlib
import re
import statistics as st
import sys

BC = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else
                  r"D:\LTTSTUDIOSAPP-gop\docs\auto_scan_video_final\bang_chung")


def doc(f: str) -> dict:
    return json.loads((BC / f).read_text(encoding="utf-8"))


def am_tiet(s: str) -> int:
    """Âm tiết tiếng Việt = token phân bởi khoảng trắng, đã bỏ dấu câu."""
    return len([t for t in re.sub(r"[^\w\s]", " ", str(s), flags=re.UNICODE).split() if t])


def toc_do_tts() -> dict:
    """Tốc độ NÓI đo trên giọng TTS THẬT (⛔ không phải tốc độ đọc phụ đề)."""
    rec = [r for f in ("fix_toc_do/vong_dau_moi_v1.json",
                       "fix_toc_do/vong_dau_moi_v2v3.json")
           for r in doc(f)["vong_dau"]]
    lech = [(am_tiet(r["chu"]), int(r["am_tiet"])) for r in rec if r.get("chu")]
    khop = sum(1 for a, b in lech if a == b)
    r = [int(x["am_tiet"]) / float(x["giay_am"]) for x in rec
         if x.get("am_tiet") and float(x.get("giay_am") or 0) > 0]
    return {"n": len(r), "trung_vi": st.median(r), "min": min(r), "max": max(r),
            "hieu_chinh_bo_dem": f"{khop}/{len(lech)}",
            "khe_cua_phep_do_cu_trung_vi_s": st.median(
                [float(x["khe"]) for x in rec if x.get("khe")])}


def chay(rate: float) -> dict:
    ra: dict = {"phim": {}}
    tong = []
    for ma in ("v1", "v2", "v3"):
        b1 = {d["ma"]: d for d in doc(f"b1_chep_loi_moi/{ma}.json")["doan"]}
        seq = sorted(b1.values(), key=lambda d: d["bat"])
        # ⭐ Ngân sách = TỚI LÚC KHE SAU BẮT ĐẦU (`thoi_gian.py:26-31`, mượn Subdub),
        #    ⛔ KHÔNG phải `ket - bat` — lấy `ket - bat` là vứt hết khoảng lặng.
        sau = {seq[i]["ma"]: (seq[i + 1]["bat"] if i + 1 < len(seq) else seq[i]["ket"])
               for i in range(len(seq))}
        rows = []
        for t in doc(f"b2_dich_nen/{ma}_nen.json")["doan"]:
            s = b1.get(t["ma"])
            vi = str(t.get("chu_dich") or "")
            if not s or not vi:
                continue
            han = len(re.sub(r"\s", "", str(s["chu"])))
            if not han:
                continue
            rows.append({
                "ty_am_tiet_tren_ky_tu_han": am_tiet(vi) / han,
                "ty_ky_tu_tren_ky_tu_han": len(vi) / han,
                "giay_can": am_tiet(vi) / rate,
                "khe_s": float(s["ket"]) - float(s["bat"]),
                "ngan_sach_s": float(sau[t["ma"]]) - float(s["bat"]),
            })
        ra["phim"][ma] = _tom(rows)
        tong += rows
    ra["tong"] = _tom(tong)
    return ra


def _tom(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {"n": 0}
    def p(key, q):
        v = sorted(r[key] for r in rows)
        return round(v[min(n - 1, max(0, int(q * n)))], 3)
    kk = sum(1 for r in rows if r["giay_can"] > r["khe_s"])
    kn = sum(1 for r in rows if r["giay_can"] > r["ngan_sach_s"])
    qua = sorted(r["giay_can"] / r["ngan_sach_s"] for r in rows
                 if r["giay_can"] > r["ngan_sach_s"])
    return {
        "n": n,
        "am_tiet_tren_ky_tu_han": {
            "trung_vi": round(st.median(r["ty_am_tiet_tren_ky_tu_han"] for r in rows), 3),
            "p05": p("ty_am_tiet_tren_ky_tu_han", 0.05),
            "p95": p("ty_am_tiet_tren_ky_tu_han", 0.95)},
        "ky_tu_tren_ky_tu_han": {
            "trung_vi": round(st.median(r["ty_ky_tu_tren_ky_tu_han"] for r in rows), 2),
            "p05": p("ty_ky_tu_tren_ky_tu_han", 0.05),
            "p95": p("ty_ky_tu_tren_ky_tu_han", 0.95)},
        "khong_vua_tren_khe": {"k": kk, "n": n, "ti_le": round(kk / n, 3)},
        "khong_vua_tren_ngan_sach": {"k": kn, "n": n, "ti_le": round(kn / n, 3)},
        "he_so_can_nen_trong_so_khong_vua": ({
            "trung_vi": round(st.median(qua), 2),
            "p95": round(qua[int(0.95 * len(qua)) - 1], 2),
            "max": round(max(qua), 2)} if qua else None),
    }


if __name__ == "__main__":
    td = toc_do_tts()
    print(json.dumps({"toc_do_tts": td, **chay(td["trung_vi"])},
                     ensure_ascii=False, indent=2))
