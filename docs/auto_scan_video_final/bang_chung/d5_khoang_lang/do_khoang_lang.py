"""D5 — DO KHOANG LANG THAT truoc khi quyet dinh co noi `vad.py` hay khong.

Cau hoi DUY NHAT: giua cac khe (sau `cat_doan`) co BAO NHIEU khoang lang THAT?

  co nhieu  => can gat 2 song lai, viec noi `vad.py` duoc bien minh bang so
  ~0        => can gat 2 chet vinh vien, KHONG noi gi, tiet kiem mot mat xich

⛔ Doc am thanh, ⛔ khong goi LLM. Dung DUNG `vad_speech_segments` cua app phien
   am (tham so mac dinh cua san pham).

⚠️ `pad_s = 0.15` cua no NO RONG vung tieng hai dau => khoang lang do duoc bi
   HUT ~0,3 s moi vung. Nen con so nay la CAN DUOI (bi quan). Neu ngay ca can
   duoi da du thi ket luan chac; neu no ~0 thi do thêm ban pad_s=0 de khong
   ket luan oan.
"""
from __future__ import annotations

import json
import pathlib
import statistics as st
import sys

GOC = pathlib.Path(r"D:\LTTSTUDIOSAPP-timeline")
sys.path.insert(0, str(GOC))

from apps.transcript.services.engine.vad import vad_speech_segments  # noqa: E402

BC = pathlib.Path(r"D:\LTTSTUDIOSAPP-gop\docs\auto_scan_video_final\bang_chung")
VID = pathlib.Path(r"C:\Users\Thang Tuong\Desktop\TEST VIDEO")
PHIM = {
    "v1": "\u5ec9\u4ef7\u7684\u725b\u80a0",
    "v2": "\u66b4\u96e8\u5929\u91ce\u5916",
    "v3": "\u6df1\u5ea6\u89e3\u6790",
}


def lang_tu_tieng(vung: list[dict], dau: float, cuoi: float) -> list[tuple[float, float]]:
    """Phan bu cua vung co tieng, trong [dau, cuoi]."""
    ra, t = [], dau
    for v in sorted(vung, key=lambda x: x["start"]):
        a, b = float(v["start"]), float(v["end"])
        if b <= dau or a >= cuoi:
            continue
        a, b = max(a, dau), min(b, cuoi)
        if a > t:
            ra.append((t, a))
        t = max(t, b)
    if t < cuoi:
        ra.append((t, cuoi))
    return ra


def chay(pad: float) -> dict:
    ket = {}
    for ma, mau in PHIM.items():
        tep = next(p for p in VID.glob("*.mp4") if mau in p.name)
        doan = sorted(json.loads((BC / f"b1_chep_loi_moi/{ma}.json").read_text(
            encoding="utf-8"))["doan"], key=lambda d: d["bat"])
        dau, cuoi = float(doan[0]["bat"]), float(doan[-1]["ket"])
        vung = vad_speech_segments(str(tep), pad_s=pad)
        lang = lang_tu_tieng(vung, dau, cuoi)

        # 1. Lang co the MUON cho can gat 2, tinh THEO TUNG RANH GIOI.
        #
        # 🔴 SUA 25/09: ban dau toi cong CA vung lang chua ranh gioi, cho MOI
        #    ranh gioi ⇒ **CONG TRUNG**. Bang chung tu no lo ra: v3 cho
        #    "99,8 s tai ranh gioi" trong khi CA cua so chi co 74,4 s lang —
        #    ⛔ bat kha. Nay:
        #      * moi vung lang chi duoc tinh MOT lan (dedupe theo vung);
        #      * va phan THAT SU muon duoc cho can gat 2 la lang nam **giua**
        #        `ket_i` va `bat_{i+1}` — ⛔ khong phai ca vung chua diem do.
        tai_ranh, vung_da_tinh, giua_khe = [], set(), []
        for i in range(len(doan) - 1):
            t0, t1 = float(doan[i]["ket"]), float(doan[i + 1]["bat"])
            trung = [(a, b) for a, b in lang if a - 1e-6 <= t0 <= b + 1e-6]
            if trung and trung[0] not in vung_da_tinh:
                vung_da_tinh.add(trung[0])
                tai_ranh.append(trung[0][1] - trung[0][0])
            # phan muon duoc THAT: giao cua [t0, t1] voi cac vung lang
            giua_khe.append(sum(max(0.0, min(b, t1) - max(a, t0)) for a, b in lang))
        tong_lang = sum(b - a for a, b in lang)
        ket[ma] = {
            "so_khe": len(doan), "so_ranh": len(doan) - 1,
            "cua_so_s": round(cuoi - dau, 1),
            "tong_lang_s": round(tong_lang, 1),
            "ti_le_lang": round(tong_lang / max(1e-6, cuoi - dau), 3),
            # ⭐ SO QUYET DINH cho can gat 2: lang nam DUNG GIUA hai khe.
            "muon_duoc_giua_hai_khe": {
                "so_ranh_co": sum(1 for x in giua_khe if x > 0.05),
                "tong_s": round(sum(giua_khe), 2),
                "trung_vi_s": round(st.median(giua_khe), 3),
                "lon_nhat_s": round(max(giua_khe), 3),
            },
            # Vung lang RIENG BIET cham toi mot ranh gioi (da dedupe).
            "vung_lang_cham_ranh_gioi": {
                "so_vung": len(tai_ranh),
                "tong_s": round(sum(tai_ranh), 1),
                "lon_nhat_s": round(max(tai_ranh), 2) if tai_ranh else 0.0,
            },
            # So sanh voi HO ma ban ghi khai (do truoc: trung vi 0,000 s)
            "ho_ban_ghi_tong_s": round(sum(
                float(doan[i + 1]["bat"]) - float(doan[i]["ket"])
                for i in range(len(doan) - 1)), 1),
        }
        # 🔴 BAT BIEN: khong phan nao duoc VUOT tong lang cua chinh cua so.
        #    Chinh phep kiem nay bat ra loi CONG TRUNG 25/09.
        r = ket[ma]
        assert r["muon_duoc_giua_hai_khe"]["tong_s"] <= r["tong_lang_s"] + 0.5, (
            f"{ma}: muon duoc {r['muon_duoc_giua_hai_khe']['tong_s']} s > tong lang "
            f"{r['tong_lang_s']} s — CONG TRUNG")
        assert r["vung_lang_cham_ranh_gioi"]["tong_s"] <= r["tong_lang_s"] + 0.5, (
            f"{ma}: vung cham ranh gioi {r['vung_lang_cham_ranh_gioi']['tong_s']} s "
            f"> tong lang {r['tong_lang_s']} s — CONG TRUNG")
    return ket


if __name__ == "__main__":
    # ⭐ NHA KHOA SOM: chay ban CAN DUOI truoc (pad mac dinh cua san pham).
    #    Chi chay them ban `pad_s=0` khi can duoi cho ket qua NHO — luc do ta
    #    can no de ⛔ khong ket oan cho can gat 2. Can duoi da du thi ket luan
    #    da chac, va mot luot quet nua chi ton khoa cua may dung chung.
    can_duoi = chay(0.15)
    tong = sum(v["muon_duoc_giua_hai_khe"]["tong_s"] for v in can_duoi.values())
    ra = {"pad_s_0.15_MAC_DINH_SAN_PHAM": can_duoi,
          "pad_s_0_KHONG_NO": None,
          "ghi_chu": f"tong lang MUON DUOC giua hai khe (can duoi) = {tong:.1f} s"}
    # Nguong quyet dinh: can gat 2 can bu ~1,33x tren 138 khe. Neu can duoi da
    # cho > 30 s tong cong thi da du de ket luan "co that su co khoang lang".
    if tong <= 30.0:
        ra["pad_s_0_KHONG_NO"] = chay(0.0)
        ra["ghi_chu"] += " -> NHO, chay them ban pad_s=0 de khong ket oan"
    else:
        ra["ghi_chu"] += " -> DU, ⛔ khong can ban pad_s=0 (tiet kiem khoa)"
    print(json.dumps(ra, ensure_ascii=False, indent=1))
