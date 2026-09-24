"""bench_b2_lap_lai.py — o nhiet do DA GHIM, dich lai CUNG dau vao co ra CUNG dau ra?

    python tools/bench_b2_lap_lai.py --phim v3 --lan 3

## ⭐ Vi sao phep nay quyet dinh mot cau hoi lon

Gia thuyet cua dieu phoi (24/09, sau N-23):

> *"O `temperature = 0`, dich lai cung mot dau vao cho cung mot dau ra ⇒ **vong
>  sua thoi xao**. Neu dung thi 85 -> 85 phan lon la **nhiet do**, ⛔ khong phai
>  bo cham."*

Do la mot gia thuyet **kiem duoc truc tiep**, ⛔ khong can bo cham, ⛔ khong can
67 phut: goi CUNG mot lo, `--lan` lan, tren **dung loi nhac duong song**, o
**dung nhiet do san pham dang ghim** (`ai.nhiet_do_cho`), roi dem **bao nhieu
doan DOI giua cac luot**.

    0 doan doi   => vong sua THOI XAO. Gia thuyet DUNG.
    con doi      => vong sua VAN xao, va ghim nhiet do ⛔ KHONG dong duoc N-02.

## ⚠️ Va co mot nguon da tra loi TRUOC — phep nay de KIEM CHUNG, ⛔ khong de xac nhan

`L_LLM_CONG.md` §4b do tren chinh `chuyen_loi_thoai`, loi nhac san pham:
**5 ket qua khac nhau / 5 luot** ngay o `temperature = 0,0`. Co che hop ly:
`-np 3` + continuous batching + `--spec-type draft-mtp` — thu tu ghep lo doi
theo tai, nen cung prompt ⛔ khong cho cung chuoi.

⇒ Ky vong: gia thuyet **SAI**. Nhung no phai duoc **do lai tren dung lo va dung
loi nhac cua B2** truoc khi ta noi the — mot nguon tra loi mot cau hoi **gan
giong** ⛔ khong phai cau tra loi cho cau hoi cua ta.

## ⛔ Tai nguyen

Goi may B = **cho mang** ⇒ ⛔ KHONG giu `cpu_nhieu`. `ltt-3.8` dung chung ⇒
⛔ toi da MOT request dong thoi.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                               # noqa: BLE001
    pass

NGUON = GOC / "docs/auto_scan_video_final/bang_chung/b1_chep_loi_moi"


def _mot_luot(db, lo: list[dict], tat_ca: list[dict], *, mid: str,
              ep: bool = True, seed: int | None = None) -> dict:
    """`{ma: chu}` cho mot lan goi. ⛔ Khong nem khi thieu doan — thieu la DU LIEU."""
    from platform_core.llm import dieu_phoi

    from apps.auto_scan_video import ai, long_tieng as L

    msg = L.loi_nhac(lo, tat_ca=tat_ca, ngon_ngu_goc="zh",
                     dac_diem_giong={}, ngon_ngu_dich="vi")
    tran, cho = ai.ngan_sach_cho(ai.CHUYEN_LOI_THOAI)
    # ⭐ **Cau hinh SAN PHAM hom nay** = ghim nhiet do + EP LUOC DO (N-23).
    #    Luot do dau (11/12 doi) chay TRUOC khi noi `response_format`, nen no
    #    ⛔ khong phai cau hinh dang chay. Mac dinh `ep=True` de bench ⛔ khong
    #    tu troi khoi san pham mot lan nua.
    them: dict = {}
    if ep:
        them["response_format"] = L.luoc_do_phan_hoi(lo)
    # ⚠️ `seed` — `llama.cpp` co `-s, --seed` (tools/server/README.md) va cong
    #    may B ⛔ khong tu choi truong nay (`L_LLM_CONG.md` §4b: 5/5 luot tra 200).
    #    Nhung lan do do KHONG o cau hinh hom nay (chua ghim nhiet do, chua ep
    #    luoc do) ⇒ o day do lai tren dung cau hinh dang chay.
    if seed is not None:
        them["seed"] = int(seed)
    kq = dieu_phoi.goi(db, messages=msg, them=(them or None),
                       thu_tu_provider=list(ai.THU_TU_PROVIDER),
                       model_theo_provider={p: mid for p in ai.THU_TU_PROVIDER},
                       # ⭐ ⛔ Khong go lai so: doc dung nhiet do SAN PHAM ghim.
                       temperature=ai.nhiet_do_cho(ai.CHUYEN_LOI_THOAI),
                       max_tokens=tran, timeout_s=float(cho or 300.0))
    noi = getattr(kq, "noi_dung", None) or getattr(kq, "content", "")
    try:
        tho = (ai.doc_json(str(noi), ai.CHUYEN_LOI_THOAI) or {}).get("doan")
    except Exception:                           # noqa: BLE001
        return {}
    if not isinstance(tho, dict):
        return {}
    ma_lo = {d["ma"] for d in lo}
    return {m: str((v or {}).get("chu") or "")
            for m, v in tho.items() if m in ma_lo and isinstance(v, dict)}


def chay(*, model: str, phim: str, lan: int, so_doan: int,
         ep: bool = True, seed: int | None = None) -> dict:
    import platform_core.db as dbmod
    from platform_core.llm import canonical

    from apps.auto_scan_video import ai

    ban = json.loads((NGUON / f"{phim}.json").read_text(encoding="utf-8"))
    doan = [{"ma": d["ma"], "chu": d["chu"], "bat": d["bat"], "ket": d["ket"]}
            for d in ban["doan"]][:so_doan]
    mid = canonical.ALIAS_SANG_ID.get(model, model)

    luot = []
    db = next(dbmod.get_session())
    try:
        for _ in range(lan):                    # ⛔ MOT request mot luc
            luot.append(_mot_luot(db, doan, doan, mid=mid, ep=ep, seed=seed))
    finally:
        db.close()

    # ⭐ Dem theo DOAN, khong theo luot: mot luot hong ⛔ khong duoc lam ca phep
    #    do mat nghia, va ta can biet **bao nhieu doan** khong on dinh.
    chi_tiet, on_dinh, doi = [], 0, 0
    for d in doan:
        ma = d["ma"]
        ban_ra = [l.get(ma, "") for l in luot]
        co = [x for x in ban_ra if x]
        if len(co) < 2:
            continue                            # ⛔ khong du hai luot de so
        khac = len(set(co))
        (on_dinh, doi) = (on_dinh + 1, doi) if khac == 1 else (on_dinh, doi + 1)
        if khac > 1:
            chi_tiet.append({"ma": ma, "goc": d["chu"],
                             "so_ban_khac_nhau": khac,
                             "cac_ban": sorted(set(co))})
    tong = on_dinh + doi
    return {
        "model": model, "phim": phim, "lan": lan, "so_doan_gui": len(doan),
        "nhiet_do": ai.nhiet_do_cho(ai.CHUYEN_LOI_THOAI),
        "ep_luoc_do": ep, "seed": seed,
        "⚠️ nhiet_do_la_gi": ("doc tu `ai.NHIET_DO_THEO_THAO_TAC` — dung thu "
                             "san pham ghim, ⛔ khong phai mot hang cua bench"),
        "doan_so_duoc": tong,
        "doan_ON_DINH": on_dinh, "doan_DOI": doi,
        "ti_le_doi": round(doi / max(1, tong), 4),
        "so_luot_trong_do_moi_doan_xuat_hien": Counter(
            sum(1 for l in luot if l.get(d["ma"])) for d in doan),
        "chi_tiet_doan_DOI": chi_tiet,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default="ltt-3.5")
    ap.add_argument("--phim", default="v3")
    ap.add_argument("--lan", type=int, default=3)
    ap.add_argument("--so-doan", type=int, default=12)
    ap.add_argument("--ra", default="")
    ap.add_argument("--khong-ep", action="store_true",
                    help="⛔ KHONG gui response_format (⛔ khac san pham)")
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args(argv)
    kq = chay(model=a.model, phim=a.phim, lan=a.lan, so_doan=a.so_doan,
              ep=not a.khong_ep, seed=a.seed)
    if a.ra:
        d = Path(a.ra)
        d.mkdir(parents=True, exist_ok=True)
        _n = ("ep" if not a.khong_ep else "khongep") + (f"_seed{a.seed}" if a.seed is not None else "")
        (d / f"laplai_{a.model}_{a.phim}_lan{a.lan}_{_n}.json").write_text(
            json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{kq['model']} · {kq['phim']} · {kq['lan']} luot · "
          f"nhiet do {kq['nhiet_do']} · ep luoc do {kq['ep_luoc_do']} · seed {kq['seed']}")
    print(f"  doan so duoc {kq['doan_so_duoc']} · ON DINH {kq['doan_ON_DINH']} · "
          f"DOI {kq['doan_DOI']} ({kq['ti_le_doi']:.0%})")
    for c in kq["chi_tiet_doan_DOI"][:6]:
        print(f"    {c['ma']}  {c['so_ban_khac_nhau']} ban khac nhau")
        for b in c["cac_ban"]:
            print(f"        {b[:78]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
