"""bench_b2_luoc_do.py — 3.5 hay 3.8 co GIU DUOC LUOC DO o co lo THAT khong?

    python tools/bench_b2_luoc_do.py --model ltt-3.8 --lo 12 --temp 0.0

## ⭐ Phep nay co the LAT ca cau hoi 3.5-vs-3.8

Do 24/09: loi nhac DUONG SONG (`long_tieng.loi_nhac`) x `ltt-3.5`, lo **12** doan
⇒ tra ve **1/12** (`ThieuDoan: thieu 11`). ⛔ Khong phai cut — tran token ra
**32 768**. Mot luot khac tra `doan` la mot **MANG**, dung cai docstring cua
`loi_nhac` canh bao (*"khoa phai la MA DOAN, khong phai mot mang"*).

**Ba ket cuc, ba nghia KHAC HAN:**

| ket cuc | nghia | cau hoi ke tiep |
|---|---|---|
| 3.8 du 12 · 3.5 tra 1 | **nang luc MODEL** | 20x la gia cua viec CHAY DUOC ⇒ "ha co lo co cuu duoc 3.5 khong, va ton them bao nhieu luot?" |
| ca hai deu roi doan | ⭐ **LUOC DO**, ⛔ khong phai model | ta dang dinh tra 20x de **che mot khuyet tat thiet ke** |
| 3.8 du · 3.5 du o lo 4 | ca hai chay duoc | so **TONG CHI PHI**: 3.5 x 3 lo vs 3.8 x 1 lo — ⛔ tinh ra so, dung uoc |

⚠️ **`doan` ra MANG ⛔ khong phai chuyen co lo** — do la **bam luoc do khong on
dinh**. Lan khac vua chua dung benh ay bang `temperature 0.0`. ⇒ Thu cung cach
**truoc khi ket toi model**.

## ⛔ Tai nguyen

3.8 **dung chung**, ⛔ **toi da MOT request dong thoi moi lan** (tran chung 2).
⛔ **Khong mot cau nao ve TOC DO** tu cac luot chay trong luc dung chung — so
giay luc nay la so **vo nghia**. Nen ban ghi ⛔ **khong** co truong `giay`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NGUON = GOC / "docs/auto_scan_video_final/bang_chung/b1_chep_loi_moi"


def luoc_do_json(lo: list[dict]) -> dict:
    """`response_format` ep model tra DUNG bang khoa-theo-ma cua lo nay.

    ⭐ **Nguon, ⛔ khong tu suy** — `ggml-org/llama.cpp`, `tools/server/README.md`:

        The `response_format` parameter supports both plain JSON output
        (e.g. `{"type": "json_object"}`) and schema-constrained JSON
        (e.g. `{"type": "json_object", "schema": {...}}` or
        `{"type": "json_schema", "schema": {...}}`)

    ⇒ llama-server dung **grammar-constrained decoding**: ⛔ khong phai mot loi
    nhac manh hon, ma mot **rang buoc luc giai ma** — token khong hop luoc do
    ⛔ khong sinh ra duoc.

    🔑 Va ta biet TRUOC cac ma cua lo, nen luoc do khai duoc **dich danh**:
    `required` = dung cac ma, `additionalProperties: false`. Do chinh la hai che
    do hong da do (`B2_DICH.md` §7.5): `doan` ra **MANG**, va **thieu doan**.
    """
    ma = [str(d["ma"]) for d in lo]
    doan = {
        "type": "object",
        "properties": {m: {
            "type": "object",
            "properties": {
                "chu": {"type": "string"},
                "cam_xuc": {"type": "string"},
                "kieu_noi": {"type": "string"},
                "nhan_manh": {"type": "array", "items": {"type": "string"}},
                "khong_chac": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["chu"],
        } for m in ma},
        "required": ma,
        "additionalProperties": False,
    }
    return {"type": "json_object",
            "schema": {"type": "object", "properties": {"doan": doan},
                       "required": ["doan"], "additionalProperties": False}}


def mot_lo(db, lo: list[dict], tat_ca: list[dict], *, mid: str,
           temp: float | None, ep: bool = False) -> dict:
    """`temp is None` ⇒ ⛔ **khong gui truong `temperature`** — dung nhu DUONG
    SONG lam: `giai_doan_noi_dung.py:217` goi `ai.goi_tinh_tien` ⛔ khong truyen
    `temperature`, `cong_vlm.py:341` chi dat truong khi no khac `None`.
    ⇒ o cau hinh nay model chay bang **mac dinh cua cong may B**, mot so ⛔
    khong khai o dau trong cay nay."""
    from platform_core.llm import dieu_phoi

    from apps.auto_scan_video import ai, long_tieng as L

    msg = L.loi_nhac(lo, tat_ca=tat_ca, ngon_ngu_goc="zh",
                     dac_diem_giong={}, ngon_ngu_dich="vi")
    # 🔴 **Tran token ra va timeout PHAI lay tu `ngan_sach_cho`, ⛔ khong phai
    #    `tran_token_ra()`.** Duong SONG di qua `ai.goi_tinh_tien`, va ham do
    #    lay `tran, cho = ngan_sach_cho(thao_tac)` (`ai.py:774`) ⇒ **16 384**,
    #    ⛔ khong phai 32 768 cua `tran_token_ra()`.
    # ⚠️ Ban dau tep nay xin `tran_token_ra()`, va `B2_DICH.md` §7.3 da suy tu
    #    con so do rang "⛔ khong phai cut, vi tran ra la 32 768". Tran THAT cua
    #    san pham chi bang MOT NUA. Do lo 12 doan: token ra ~2,8-5,0k
    #    (`L_LLM_CONG.md` §3) ⇒ ⛔ ca hai tran deu KHONG cham, nen ket luan
    #    "khong phai cut" van dung — nhung no dung vi so do, ⛔ khong vi 32 768.
    tran, cho = ai.ngan_sach_cho(ai.CHUYEN_LOI_THOAI)
    # ⭐ `them` di thang xuong than request: `CongVlm.chat` lam
    #    `than_gui.update(them)` va cong may B chuyen nguyen than len llama-server
    #    (`llm_gateway/upstream.py:91`). Duong nay da duoc kiem mot lan bang
    #    `seed` (`L_LLM_CONG.md` §4b: cong ⛔ khong tu choi, 5/5 luot tra 200).
    them = {"response_format": luoc_do_json(lo)} if ep else None
    kq = dieu_phoi.goi(db, messages=msg,
                       thu_tu_provider=list(ai.THU_TU_PROVIDER),
                       model_theo_provider={p: mid for p in ai.THU_TU_PROVIDER},
                       temperature=temp, max_tokens=tran, them=them,
                       timeout_s=float(cho or 300.0))
    noi = getattr(kq, "noi_dung", None) or getattr(kq, "content", "")
    ma_lo = {d["ma"] for d in lo}
    try:
        goi = ai.doc_json(str(noi), ai.CHUYEN_LOI_THOAI)
    except Exception as exc:                    # noqa: BLE001
        return {"gui": len(ma_lo), "nhan": 0, "thieu": len(ma_lo),
                "hinh_dang": f"⛔ doc_json nem: {type(exc).__name__}"}
    tho = (goi or {}).get("doan")
    if isinstance(tho, list):
        # ⛔ Vi pham luoc do: vi tri ⛔ khong dung lam dinh danh duoc.
        return {"gui": len(ma_lo), "nhan": 0, "thieu": len(ma_lo),
                "hinh_dang": "⛔ MANG (vi pham luoc do)"}
    if not isinstance(tho, dict):
        return {"gui": len(ma_lo), "nhan": 0, "thieu": len(ma_lo),
                "hinh_dang": f"⛔ {type(tho).__name__}"}
    nhan = {m for m, v in tho.items() if m in ma_lo and isinstance(v, dict)}
    thua = [m for m in tho if m not in ma_lo]
    return {"gui": len(ma_lo), "nhan": len(nhan), "thieu": len(ma_lo - nhan),
            "ma_bia_them": len(thua), "hinh_dang": "bang khoa theo ma ✅"}


def chay(*, model: str, moi_lo: int, temp: float | None, phim: str,
         so_lo: int, ep: bool = False) -> dict:
    import platform_core.db as dbmod
    from platform_core.llm import canonical

    from apps.auto_scan_video import long_tieng as L

    ban = json.loads((NGUON / f"{phim}.json").read_text(encoding="utf-8"))
    doan = [{"ma": d["ma"], "chu": d["chu"], "bat": d["bat"], "ket": d["ket"]}
            for d in ban["doan"]]
    mid = canonical.ALIAS_SANG_ID.get(model, model)
    cac_lo = L.chia_lo(doan, moi_lo=moi_lo)[:so_lo]
    ket = []
    db = next(dbmod.get_session())
    try:
        # ⛔ MOT request mot luc — 3.8 dung chung voi lan khac (luat 24/09).
        for lo in cac_lo:
            ket.append(mot_lo(db, lo, doan, mid=mid, temp=temp, ep=ep))
    finally:
        db.close()
    gui = sum(k["gui"] for k in ket)
    nhan = sum(k["nhan"] for k in ket)
    return {
        "model": model, "model_id": mid, "moi_lo": moi_lo,
        "temperature": ("⛔ KHONG GUI (mac dinh cong may B) — dung nhu duong song"
                        if temp is None else temp),
        "phim": phim, "so_lo": len(ket),
        "ep_luoc_do": ep,
        "⭐ nguon_ep": ("ggml-org/llama.cpp tools/server/README.md — "
                       "response_format {type: json_object, schema: ...} "
                       "= grammar-constrained decoding") if ep else "",
        "tong_gui": gui, "tong_nhan": nhan, "tong_thieu": gui - nhan,
        "ti_le_nhan": round(nhan / max(1, gui), 4),
        "so_lo_vi_pham_luoc_do": sum(1 for k in ket
                                     if "⛔" in k.get("hinh_dang", "")),
        "chi_tiet": ket,
        "⛔ toc_do": "KHONG ghi giay: 3.8 dang DUNG CHUNG, so giay vo nghia.",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default="ltt-3.8")
    ap.add_argument("--lo", type=int, default=12)
    # ⭐ `--temp -1` ⇒ ⛔ KHONG gui truong `temperature`, tuc **dung cau hinh
    #    DUONG SONG**. ⛔ Dung doc `-1` la "nhiet do am".
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--phim", default="v1")
    ap.add_argument("--so-lo", type=int, default=3)
    ap.add_argument("--ra", default="")
    ap.add_argument("--ep-luoc-do", action="store_true",
                    help="gui `response_format` ep bang khoa-theo-ma")
    a = ap.parse_args(argv)
    temp = None if a.temp < 0 else a.temp
    kq = chay(model=a.model, moi_lo=a.lo, temp=temp, phim=a.phim,
              so_lo=a.so_lo, ep=a.ep_luoc_do)
    if a.ra:
        d = Path(a.ra)
        d.mkdir(parents=True, exist_ok=True)
        # 🔴 **`phim` PHAI nam trong ten tep.** Thieu no thi hai luot khac phim
        #    cung cau hinh de len nhau va ban ghi cua luot truoc bien mat —
        #    ⛔ khong mot canh bao nao.
        nhan = ("congmacdinh" if temp is None else f"t{a.temp}") + ("_ep" if a.ep_luoc_do else "")
        (d / f"luocdo_{a.model}_{a.phim}_lo{a.lo}_{nhan}.json").write_text(
            json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{kq['model']} · lo {kq['moi_lo']} · temp {kq['temperature']} · "
          f"{kq['so_lo']} lo")
    print(f"  nhan {kq['tong_nhan']}/{kq['tong_gui']} "
          f"({kq['ti_le_nhan']}) · thieu {kq['tong_thieu']} · "
          f"vi pham luoc do {kq['so_lo_vi_pham_luoc_do']} lo")
    for i, k in enumerate(kq["chi_tiet"], start=1):
        print(f"    lo {i}: nhan {k['nhan']}/{k['gui']} — {k['hinh_dang']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
