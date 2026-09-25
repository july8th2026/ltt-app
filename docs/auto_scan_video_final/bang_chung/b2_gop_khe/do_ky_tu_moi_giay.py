"""B2 — CÁI GIÁ của `gop_khe`: ký tự/giây của PHỤ ĐỀ, trước và sau.

⛔ Chỉ ĐỌC bằng chứng đã có. ⛔ Không TTS, ⛔ không LLM, ⛔ không GPU, ⛔ không một
lượt ASV nào.

Nguồn (chỉ đọc, cây chính):
    b1_chep_loi_moi/v{1,2,3}.json    khe gốc (sau `cat_doan`)
    b2_dich_nen/v{1,2,3}_nen.json    bản dịch tiếng Việt (`chu_dich`)

## Ba dòng của bảng, và vì sao phải có DÒNG BA

Một ô phụ đề của ta dài đúng bằng **thời gian máy đọc chính văn bản của ô đó**
(`phu_de.su_kien_tu_ke_hoach`: `end = dat_tai + dai_ms`, và `dai_ms` là độ dài
tệp tiếng). Nên:

  1. TRƯỚC gộp — mỗi `ma` một ô.
  2. SAU gộp, **thiết kế đã lắp**: `gop_khe` gộp cái ĐỌC (một tệp tiếng cho
     2–4 `ma`) nhưng `no_ban_ke` trả lại một dòng cho MỌI `ma`, nên phụ đề vẫn
     là **một ô cho mỗi `ma`** — ô chỉ dài bằng **phần âm tiết** của nó
     (`nan_thoi_luong.chia_giay`).
  3. SAU gộp, **phản thực**: nếu gộp CẢ Ô (một ô cho cả nhóm). ⛔ KHÔNG lắp —
     dòng này tồn tại để trả lời *"vì sao không"* bằng số, chứ không bằng lời.

⭐ Trần: Netflix 17–20 ký tự/giây (`localize.py:9069-9070`), và trần **bố cục**
   của chính ta: `phu_de.SO_DONG_TOI_DA (2) x KY_TU_MOI_DONG (42)` = 84 ký tự
   một ô.
"""
from __future__ import annotations

import json
import pathlib
import statistics as st
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))

from apps.auto_scan_video import nan_cho_vua as ncv  # noqa: E402
from apps.auto_scan_video import nan_thoi_luong as nt  # noqa: E402
from apps.auto_scan_video import phu_de as pd  # noqa: E402

BC = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else
                  r"D:\LTTSTUDIOSAPP\docs\auto_scan_video_final\bang_chung")
TRAN_NETFLIX = 20.0
TRAN_O = pd.SO_DONG_TOI_DA * pd.KY_TU_MOI_DONG
RATE = nt.AM_TIET_MOI_GIAY
TRAN_CO_GIAN = 1.15            # `thoi_gian.TRAN_TANG_TOC`

#: Khe hẹp hơn mốc này thì `dung_sai_giay` rơi xuống SÀN tuyệt đối — tức đoạn bị
#: phán quyết ở một độ chính xác **nhỏ hơn một âm tiết** (bước 1, `b1-san-dung-sai`).
#: ⛔ Không gõ lại số: dẫn từ chính hai hằng của `nan_cho_vua`.
KHE_DUOI_MOT_AM_TIET_S = ncv.SAN_DUNG_SAI_GIAY / ncv.DUNG_SAI_DAI


def doc(f: str) -> dict:
    return json.loads((BC / f).read_text(encoding="utf-8"))


def khe_cua_phim(ma: str) -> list[nt.Khe]:
    """`Khe` của một phim, `chu` = BẢN DỊCH (thứ máy đọc và thứ hiện ra)."""
    b1 = {d["ma"]: d for d in doc(f"b1_chep_loi_moi/{ma}.json")["doan"]}
    hang = []
    for t in doc(f"b2_dich_nen/{ma}_nen.json")["doan"]:
        s = b1.get(t["ma"])
        vi = str(t.get("chu_dich") or "")
        if not s or not vi.strip():
            continue
        hang.append((float(s["bat"]), float(s["ket"]), str(t["ma"]), vi))
    hang.sort()
    ra = []
    for i, (bat, ket, m, vi) in enumerate(hang):
        moc_sau = hang[i + 1][0] if i + 1 < len(hang) else ket
        ra.append(nt.Khe(ma=m, bat=bat, ket=max(bat, ket),
                         moc_sau=max(moc_sau, ket),
                         am_tiet=nt.am_tiet_cua(vi), chu=vi))
    return ra


def _tt(v: list[float]) -> dict:
    if not v:
        return {"n": 0}
    s = sorted(v)
    return {"n": len(s), "p50": round(st.median(s), 2),
            "p95": round(s[min(len(s) - 1, int(0.95 * len(s)))], 2),
            "max": round(s[-1], 2),
            "so_vuot_20": sum(1 for x in s if x > TRAN_NETFLIX),
            "ti_le_vuot_20": round(sum(1 for x in s if x > TRAN_NETFLIX) / len(s), 3)}


def _o(chu: list[str]) -> dict:
    """Bố cục ô: bao nhiêu ô vượt 2 dòng x 42 ký tự."""
    n = len(chu)
    d = [len(c) for c in chu]
    return {"n": n, "ky_tu_p50": round(st.median(d), 1), "ky_tu_max": max(d),
            "so_vuot_tran_o": sum(1 for x in d if x > TRAN_O),
            "ti_le_vuot_tran_o": round(sum(1 for x in d if x > TRAN_O) / n, 3)}


def _cong(ra: dict, khoa: str) -> dict:
    k = sum(v[khoa]["k"] for v in ra["phim"].values())
    n = sum(v[khoa]["n"] for v in ra["phim"].values())
    return {"k": k, "n": n, "ti_le": round(k / n, 3) if n else None}


def chay() -> dict:
    ra: dict = {
        "tran": {"netflix_ky_tu_moi_giay": TRAN_NETFLIX,
                 "o_phu_de_ky_tu": TRAN_O,
                 "am_tiet_moi_giay": RATE,
                 "luat_gop": {"tran_gop": nt.TRAN_GOP_KHE,
                              "tran_khe_giua_s": nt.TRAN_KHE_GIUA_S,
                              "tran_ky_tu": nt.TRAN_KY_TU_GOP}},
        "phim": {}}
    gom = {"truoc": [], "sau_tach_o": [], "phan_thuc_gop_o": []}
    gom_chu = {"truoc": [], "sau_tach_o": [], "phan_thuc_gop_o": []}
    tong_khe = tong_nhom = tong_da_gop = 0

    for ma in ("v1", "v2", "v3"):
        khes = khe_cua_phim(ma)
        nhom = nt.nhom_chi_so(khes, tran_tang_toc=TRAN_CO_GIAN)
        tong_khe += len(khes)
        tong_nhom += len(nhom)
        da_gop = sum(1 for g in nhom if len(g) > 1)
        tong_da_gop += da_gop

        # 1 — TRƯỚC: mỗi `ma` một ô, ô dài = thời gian đọc chính văn bản của nó.
        truoc = [len(k.chu) / (k.am_tiet / RATE) for k in khes if k.am_tiet]
        # 2 — SAU, thiết kế đã lắp: ô vẫn tách, thời lượng = phần âm tiết của nó
        #     trong tệp gộp (`chia_giay` chia đúng theo âm tiết).
        sau = []
        pt = []
        chu_pt = []
        for g in nhom:
            tv = [khes[k] for k in g]
            giay_tep = sum(k.am_tiet for k in tv) / RATE
            phan = nt.chia_giay(giay_tep, [k.am_tiet for k in tv])
            for k, p in zip(tv, phan, strict=True):
                if p > 0:
                    sau.append(len(k.chu) / p)
            # 3 — phản thực: gộp cả ô
            chu_gop = " ".join(k.chu for k in tv).strip()
            chu_pt.append(chu_gop)
            if giay_tep > 0:
                pt.append(len(chu_gop) / giay_tep)

        # ⭐ CAI LOI: bao nhieu khe con bi phan quyet "khong vua" (bac > 0),
        #    truoc va sau gop. Do la con so `gop_khe` ton tai de ha xuong.
        bac_truoc = sum(1 for k in khes
                        if nt.xep_bac(k, tran_tang_toc=TRAN_CO_GIAN)
                        > nt.BacNan.BINH_THUONG)
        khe_gop = nt.gop_khe(khes, tran_tang_toc=TRAN_CO_GIAN)
        bac_sau = sum(1 for k in khe_gop
                      if nt.xep_bac(k, tran_tang_toc=TRAN_CO_GIAN)
                      > nt.BacNan.BINH_THUONG)

        ra["phim"][ma] = {
            "so_khe": len(khes), "so_nhom": len(nhom), "so_nhom_da_gop": da_gop,
            "khong_vua_truoc": {"k": bac_truoc, "n": len(khes),
                                "ti_le": round(bac_truoc / len(khes), 3)},
            "khong_vua_sau": {"k": bac_sau, "n": len(khe_gop),
                              "ti_le": round(bac_sau / len(khe_gop), 3)},
            # ⭐ Chính phép đo mà brief nêu làm nền (100/106 -> 39/59 trên lượt
            #    `asvr_9fc9cc89`): khe hẹp hơn `KHE_DUOI_MOT_AM_TIET_S` thì dung
            #    sai rơi xuống sàn, tức phán quyết dưới một âm tiết.
            "duoi_mot_am_tiet_truoc": {
                "k": sum(1 for k in khes if k.khe_s < KHE_DUOI_MOT_AM_TIET_S),
                "n": len(khes)},
            "duoi_mot_am_tiet_sau": {
                "k": sum(1 for k in khe_gop if k.khe_s < KHE_DUOI_MOT_AM_TIET_S),
                "n": len(khe_gop)},
            "khe_trung_vi_truoc_s": round(st.median([k.khe_s for k in khes]), 3),
            "khe_trung_vi_sau_s": round(st.median(
                [khes[g[-1]].ket - khes[g[0]].bat for g in nhom]), 3),
            "ky_tu_moi_giay": {"1_truoc": _tt(truoc),
                               "2_sau_o_van_tach": _tt(sau),
                               "3_phan_thuc_gop_ca_o": _tt(pt)},
            "bo_cuc_o": {"1_truoc": _o([k.chu for k in khes]),
                         "3_phan_thuc_gop_ca_o": _o(chu_pt)},
        }
        gom["truoc"] += truoc
        gom["sau_tach_o"] += sau
        gom["phan_thuc_gop_o"] += pt
        gom_chu["truoc"] += [k.chu for k in khes]
        gom_chu["phan_thuc_gop_o"] += chu_pt

    ra["tong"] = {
        "so_khe": tong_khe, "so_nhom": tong_nhom, "so_nhom_da_gop": tong_da_gop,
        "khe_duoi_mot_am_tiet_s": round(KHE_DUOI_MOT_AM_TIET_S, 3),
        "khong_vua_truoc": _cong(ra, "khong_vua_truoc"),
        "khong_vua_sau": _cong(ra, "khong_vua_sau"),
        "duoi_mot_am_tiet_truoc": _cong(ra, "duoi_mot_am_tiet_truoc"),
        "duoi_mot_am_tiet_sau": _cong(ra, "duoi_mot_am_tiet_sau"),
        "ti_le_khe_bi_gop": round(1 - tong_nhom / tong_khe, 3),
        "ky_tu_moi_giay": {"1_truoc": _tt(gom["truoc"]),
                           "2_sau_o_van_tach": _tt(gom["sau_tach_o"]),
                           "3_phan_thuc_gop_ca_o": _tt(gom["phan_thuc_gop_o"])},
        "bo_cuc_o": {"1_truoc": _o(gom_chu["truoc"]),
                     "3_phan_thuc_gop_ca_o": _o(gom_chu["phan_thuc_gop_o"])},
    }
    return ra


if __name__ == "__main__":
    print(json.dumps(chay(), ensure_ascii=False, indent=2))
