"""bench_b2_duong_b_tu_khai.py — DUONG B: model co biet cho no KHONG BIET khong?

    python tools/bench_b2_duong_b_tu_khai.py --ra <thu muc>

## ⭐ Vi sao phep nay dang chay TRUOC khi ai quyet dinh gi

Nam duong cua `B2_DICH.md` §4d dang cho mot quyet dinh san pham. Nhung **duong B
(model tu khai cho no khong chac)** ⛔ khong can cho ai — no la mot **cau hoi
thuc nghiem**:

> **Model co biet nhung cho no khong biet khong?**

⇒ Tra loi duoc bang **ban nen da co** (`ltt-3.5`), ⛔ khong can `ltt-3.8`,
⛔ khong can bo cham.

## ⛔ Thiet ke — ba dieu KHONG duoc chech

1. ⛔ **Khong noi cho model biet ta dang tim gi.** Cau hoi la *"tu/cum nao ban
   khong chac"*, ⛔ khong phai *"tu chuyen nganh nao"*.
2. ⛔ **Khong dua mot vi du nao tu 7 ca da hong.** Hom nay da mat mot luot vi
   dung chuyen nay: **vi du trong loi nhac la mot MENH LENH ngam** — dua
   `掐雷` vao lam vi du thi no se khai `掐雷`, va ta do chinh cai ta vua mach.
3. ⛔ **Khong sua loi nhac SAN PHAM.** Tep nay dung mot ban SAO co them mot
   truong; `dich_thuat._loi_nhac` giu nguyen.

## ⭐ HAI VE, do cung luc — ⛔ dung chi dem ve mot

| ve | cau hoi | vi sao no quyet dinh |
|---|---|---|
| **do nhay** | bat duoc bao nhieu trong **7 ca da biet hong**? | bat it ⇒ duong B **chet** |
| **do on** | khai them bao nhieu tu **ngoai** 7 ca? | ⭐ mot model khai **moi** tu thi bat du 7 ma **VO DUNG**. Khai 200/718 tu ⇒ duong B chet, va **chet bang so** |

**Ba ket cuc, ba hanh dong:** bat gan du + danh sach ngan ⇒ duong B **re va
song**. Bat it ⇒ **chet**, ghi lai. Bat du nhung on ⇒ ghi **ca hai so**, de chu
du an thay **gia that**.

⛔ Van khong khuyen nghi — dieu phoi can **lua chon kem gia**.

## Khoa

⛔ KHONG giu `cpu_nhieu` (goi may B = cho mang). Tran 2 request/model. 3.5 only.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NGUON = GOC / "docs/auto_scan_video_final/bang_chung/b1_chep_loi_moi"

#: 🔴 **BAY ca da biet hong** (`B2_DICH.md` §4d + §4.3). ⛔ Danh sach nay CHI de
#: CHAM SAU KHI CHAY — ⛔ tuyet doi khong duoc di vao loi nhac.
DA_BIET_HONG = {
    "掐雷": "v3", "纯白给": "v3", "补人": "v3",
    "烧酒": "v1", "热胀冷缩": "v1", "师傅": "v1",
    "这才是": "v2",
}


def _loi_nhac_co_tu_khai(lo: list[dict], ngon_ngu_goc: str) -> list[dict]:
    """Ban SAO cua loi nhac san pham + MOT truong. ⛔ Khong sua ban that.

    ⚠️ Cau hoi co y **trung tinh**: *"tu hoac cum nao ban KHONG CHAC"*. ⛔ Khong
       noi "chuyen nganh", ⛔ khong noi "tieng long", ⛔ khong mot vi du nao —
       neu ta mach thi ta do chinh loi mach cua minh.
    """
    from apps.auto_scan_video import dich_thuat as D

    goc = D._loi_nhac(lo, ngon_ngu_goc)          # noqa: SLF001
    he = goc[0]["content"] + (
        "\n\nNGOAI ban dich, hay tra ve them khoa \"khong_chac\": danh sach "
        "nhung tu hoac cum TRONG CAU GOC ma ban khong chac chan ve cach dich. "
        "De danh sach RONG neu ban chac chan het.\n"
        "Dinh dang: {\"doan\": {\"<ma>\": \"<cau tieng Viet>\"}, "
        "\"khong_chac\": [\"<tu goc>\", ...]}")
    return [{"role": "system", "content": he}, goc[1]]


def mot_phim(ten: str) -> dict:
    import platform_core.db as dbmod

    from apps.auto_scan_video import ai, dich_thuat as D

    ban = json.loads((NGUON / f"{ten}.json").read_text(encoding="utf-8"))
    doan = [{"ma": d["ma"], "chu": d["chu"]} for d in ban["doan"]]
    nn = str(ban.get("ngon_ngu") or "zh")
    t0 = time.time()
    khai: list[str] = []
    dich: dict = {}
    loi: list[dict] = []
    db = next(dbmod.get_session())
    try:
        for lo in D.chia_lo(doan):
            try:
                kq = ai.goi(db, ai.DICH_THUAT, _loi_nhac_co_tu_khai(lo, nn),
                            temperature=0.2)
                goi = ai.doc_json(kq["noi_dung"], ai.DICH_THUAT)
                dich.update(goi.get("doan") or {})
                khai.extend(str(x) for x in (goi.get("khong_chac") or []))
            except Exception as exc:            # noqa: BLE001
                loi.append({"kieu": type(exc).__name__, "loi": str(exc)[:200]})
    finally:
        db.close()

    van_goc = "".join(d["chu"] for d in doan)
    can_bat = {k for k, v in DA_BIET_HONG.items() if v == ten}
    bat = {k for k in can_bat if any(k in x or x in k for x in khai)}
    # ⭐ "Ngoai 7 ca" = do ON. ⛔ Phai dem, khong duoc bo qua.
    ngoai = [x for x in khai
             if not any(k in x or x in k for k in DA_BIET_HONG)]
    return {
        "phim": ban.get("phim"), "model": _model(), "so_doan": len(doan),
        "so_ky_tu_goc": len(van_goc), "giay": round(time.time() - t0, 1),
        "lo_hong": loi,
        "do_nhay": {"can_bat": sorted(can_bat), "bat_duoc": sorted(bat),
                    "ti_le": (round(len(bat) / len(can_bat), 4)
                              if can_bat else None)},
        "do_on": {"tong_khai": len(khai), "ngoai_7_ca": len(ngoai),
                  "ti_le_tren_ky_tu_goc": round(len(khai) / max(1, len(van_goc)), 4),
                  "danh_sach": khai},
        "⛔": "Danh sach 7 ca CHI dung de cham SAU khi chay — khong vao loi nhac.",
    }


def _model() -> str:
    from apps.auto_scan_video import ai

    try:
        return ai.model_cho(ai.DICH_THUAT)
    except Exception as e:                      # noqa: BLE001
        print(f"[canh bao] khong doc duoc model dich: {type(e).__name__}")
        return ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--phim", default="")
    ap.add_argument("--ra", default="")
    a = ap.parse_args(argv)
    ra_dir = Path(a.ra) if a.ra else None
    if ra_dir:
        ra_dir.mkdir(parents=True, exist_ok=True)
    for ten in ([a.phim] if a.phim else ["v1", "v2", "v3"]):
        kq = mot_phim(ten)
        if ra_dir:
            (ra_dir / f"{ten}_tukhai.json").write_text(
                json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
        dn, do = kq["do_nhay"], kq["do_on"]
        print(f"{ten}: bat {len(dn['bat_duoc'])}/{len(dn['can_bat'])} "
              f"({dn['bat_duoc']}) · khai TONG {do['tong_khai']} "
              f"(ngoai 7 ca: {do['ngoai_7_ca']}) · {kq['giay']} s "
              f"lo_hong={len(kq['lo_hong'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
