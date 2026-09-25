"""bench_b2_flores_dich.py — sinh ban dich FLORES zh->vi de lan do tinh chrF++.

    python tools/bench_b2_flores_dich.py --so-dong 100 --lan 3 --ra <thu muc>

## ⭐ Vi sao tep nay ton tai, va vi sao no phai la FLORES

Moi ban dich B2 da sinh deu la **doan PHIM cua khach** ⇒ ⛔ **khong co ban tham
chieu** ⇒ **chrF++ ⛔ khong do duoc**.

⭐ Va `chrF++` la **tin hieu DUY NHAT hien KHONG dinh vong tron LLM**: no so voi
**ban dich NGUOI** cua FLORES, ⛔ khong qua mot model nao cham. Moi so con lai
(MetricX, bo cham V3) deu treo tren canh bao *"chan ly nen do LLM tao"*.
⇒ Mat no la mat that.

## ⛔ Ba rang buoc cua phep sinh nay

1. ⛔ **CHI cot `zh` lam dau vao.** Cot `vi` la **DAP AN** — de no lot vao loi
   nhac la ta **tu cham bai minh**. Tep nay ⛔ khong bao gio dua `vi` vao
   `messages`; no chi **chep lai** `vi` sang ban ghi de lan do co tham chieu.
2. **Dung DUONG SAN PHAM da ghim**: `ltt-3.5` · `temperature` doc tu
   `ai.nhiet_do_cho` · **ep luoc do** (`long_tieng.luoc_do_phan_hoi`).
   ⛔ Khong cau hinh rieng — mot bench go lai hang so la mot bench do mot thu
   khac voi thu khach nhan.
3. **>= 3 luot.** Duong dich ⛔ **khong tai lap duoc** (`B2_DICH.md` §7.8c:
   `seed` duoc chuyen VA duoc kiem, van doi 12/12 doan) ⇒ **mot luot ⛔ khong
   phai mot con so**.

## ⭐ NHAN CAU HINH NAM TRONG TEP

Mot lan kia vua mat mot luot vi **ba tep bi hieu nham la ba LUOT** trong khi
chung la **ba PHIM**. ⇒ Ban ghi mang `model` · `nhiet_do` · `ep_luoc_do` ·
`so_luot` · `dai_dong_flores` ngay trong than tep, ⛔ khong nam o ten tep.

## ⛔ Tai nguyen

Goi may B = **cho mang** ⇒ ⛔ KHONG giu `cpu_nhieu`.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
from typing import cast

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: ⛔ **Dung CHUNG mot cho cat voi `bench_b2_xac_thuc_bo_cham`** — hai duong doc
#: se lech nhau o mot ban tai lai nao do.
FLORES_DIR = pathlib.Path(
    os.environ.get("LTT_FLORES_DIR")
    or r"C:\LTTPlatform\hf-cache\flores200") / "flores200_dataset"


def doc_flores(thu_muc: pathlib.Path = FLORES_DIR) -> list[tuple[int, str, str]]:
    """`[(chi_so_dong, cau_zh, cau_vi_NGUOI_DICH)]` — split `dev`.

    ⚠️ **Ban SAO nguyen van cua `bench_b2_xac_thuc_bo_cham.doc_flores`**, va do
       la mot **mon no da khai**: tep kia nam o mot nhanh CHUA gop, nen ⛔ khong
       import duoc tu day. ⇒ Khi hai nhanh gop lai, **xoa ban nay** va import
       ban kia — hai bo doc cho cung mot tep la hai co hoi de chung lech nhau.

    ⚠️ Hai tep **cung thu tu** (README cua FLORES), nen chi so dong la khoa ghep.
       Lech mot dong => MOI cap sai => phep do tu bien thanh mot phep do ve chinh
       no. Vi vay so dong lech => **dung ngay**.
    """
    zh = thu_muc / "dev" / "zho_Hans.dev"
    vi = thu_muc / "dev" / "vie_Latn.dev"
    if not zh.exists() or not vi.exists():
        raise SystemExit(f"chua co FLORES o {thu_muc}")
    a = zh.read_text(encoding="utf-8").splitlines()
    b = vi.read_text(encoding="utf-8").splitlines()
    if len(a) != len(b):
        raise SystemExit(f"hai tep FLORES lech so dong: {len(a)} vs {len(b)}")
    return [(i, a[i].strip(), b[i].strip()) for i in range(len(a))
            if a[i].strip() and b[i].strip()]


def _mot_lo(db, lo: list[dict], mid: str, y_canh: dict | None = None) -> dict:
    """`{ma: chu}` cho mot lo, qua DUNG duong san pham (ep luoc do + nhiet do ghim)."""
    from platform_core.llm import dieu_phoi

    from apps.auto_scan_video import ai, long_tieng as L

    # ⛔ `tat_ca=lo`: FLORES la nhung cau ROI RAC, ⛔ khong phai mot mach hoi
    #    thoai. Dua ca tap lam `ke_ben` se bia ra mot ngu canh KHONG ton tai.
    msg = L.loi_nhac(lo, tat_ca=lo, ngon_ngu_goc="zh",
                     dac_diem_giong={}, ngon_ngu_dich="vi", y_canh=y_canh)
    tran, cho = ai.ngan_sach_cho(ai.CHUYEN_LOI_THOAI)
    kq = dieu_phoi.goi(
        db, messages=msg, thu_tu_provider=list(ai.THU_TU_PROVIDER),
        model_theo_provider={p: mid for p in ai.THU_TU_PROVIDER},
        temperature=ai.nhiet_do_cho(ai.CHUYEN_LOI_THOAI),
        max_tokens=tran, them={"response_format": L.luoc_do_phan_hoi(lo)},
        timeout_s=float(cho or 300.0))
    noi = getattr(kq, "noi_dung", None) or getattr(kq, "content", "")
    ma_lo = {d["ma"] for d in lo}
    try:
        tho = (ai.doc_json(str(noi), ai.CHUYEN_LOI_THOAI) or {}).get("doan")
    except Exception as e:                      # noqa: BLE001
        print(f"[canh bao] VUT ca mot lo ({len(lo)} doan) - doc_json nem "
              f"{type(e).__name__}")
        return {}
    if not isinstance(tho, dict):
        return {}
    return {m: str((v or {}).get("chu") or "")
            for m, v in tho.items() if m in ma_lo and isinstance(v, dict)}


def chay(*, model: str, so_dong: int, lan: int, moi_lo: int,
         lan_b: int = 0) -> dict:
    import platform_core.db as dbmod
    from platform_core.llm import canonical

    from apps.auto_scan_video import ai, long_tieng as L, van_ban

    cap = doc_flores()[:so_dong]
    mid = canonical.ALIAS_SANG_ID.get(model, model)
    # 🔴 **`ket` phai lam `do_dai_toi_da` KHONG RANG BUOC — va day la mot
    #    ban SUA, khong phai mot tien nghi.**
    #
    #    Ban dau cho nay dat `ket = 6.0` cho MOI dong. `ngan_sach_do_dai(6,0)`
    #    = **18 am tiet**, trong khi tham chieu NGUOI cua FLORES co trung vi
    #    **29 tu** (max 75). => Ban ta sinh ra **ngan hon 2,4 lan** tham chieu.
    #
    # ⛔ chrF++ tren mot tep nhu vay do **DO NEN**, ⛔ khong do chat luong
    #    dich — va se cho ra mot diem THAP GIA, roi ai do se doc no thanh
    #    *"ltt-3.5 dich te"*. Dung ho loi "pham vi phep do hep hon loi tuyen bo".
    #
    # ⭐ FLORES ⛔ **khong co thoi luong** (no la cau van, khong phai doan
    #    phim), nen mot tran do dai o day la mot **quy uoc cua bench**. => Dat
    #    no **du rong de khong bao gio cham**, va suy tu **do dai NGUON** ( ⛔
    #    khong tu ban tham chieu — do la dap an).
    doan = [{"ma": f"flores_{i:04d}", "chu": zh, "bat": 0.0,
             "ket": max(6.0, len(zh) / 1.5)}
            for i, zh, _vi in cap]
    tham_chieu = {f"flores_{i:04d}": vi for i, _zh, vi in cap}

    db = next(dbmod.get_session())
    cac_luot: list[dict] = []
    cac_luot_b: list[dict] = []
    t0 = time.time()
    try:
        for _ in range(lan):
            ra: dict = {}
            for lo in L.chia_lo(doan, moi_lo=moi_lo):
                ra.update(_mot_lo(db, lo, mid))
            cac_luot.append(ra)
        # ⭐ **Nhanh B: dich LAI dung nhung dong ay, CO `y_canh`** — mo phong
        #    DUNG vong sua that: ly do + trich nguon + BAN CU (chinh ket qua
        #    nhanh A). Muc dich: do xem LUAT `y_canh` (v4) co lam tut chrF++
        #    khong, tren mot tap CO tham chieu nguoi dich.
        # ⚠️ `y_canh` o day la mot nghi ngo TRUNG TINH ("kiem lai nghia") —
        #    ⛔ khong khang dinh mot khuyet tat cu the, vi FLORES ⛔ khong co
        #    phan quyet nao. => No do TAC DUNG PHU cua luat, ⛔ khong do "ly do
        #    dung co giup khong".
        for i in range(lan_b):
            goc_a = cac_luot[min(i, len(cac_luot) - 1)]
            ra = {}
            for lo in L.chia_lo(doan, moi_lo=moi_lo):
                yc = {d["ma"]: {"nghi_ngo": "kiem lai nghia cua cau",
                                "trich_nguon": d["chu"][:160],
                                "trich_ban_cu": goc_a.get(d["ma"], "")[:160]}
                      for d in lo if goc_a.get(d["ma"])}
                ra.update(_mot_lo(db, lo, mid, y_canh=yc or None))
            cac_luot_b.append(ra)
    finally:
        db.close()

    muc = []
    for i, zh, vi in cap:
        ma = f"flores_{i:04d}"
        muc.append({
            "ma": ma, "dong_flores": i, "nguon_zh": zh,
            # ⭐ Tham chieu NGUOI DICH — ⛔ no ⛔ KHONG di vao loi nhac, xem
            #    docstring dau tep. No o day de lan do co cai ma so voi.
            "tham_chieu_vi": vi,
            "cac_luot": [l.get(ma, "") for l in cac_luot],
            "cac_luot_CO_y_canh": [l.get(ma, "") for l in cac_luot_b],
        })
    thieu = sum(1 for m in muc
                for x in cast("list[str]", m["cac_luot"]) if not x)
    return {
        "⭐ nhan_cau_hinh": {
            "model": model, "model_id": mid,
            "nhiet_do": ai.nhiet_do_cho(ai.CHUYEN_LOI_THOAI),
            "ep_luoc_do": True,
            "so_luot": lan, "so_luot_CO_y_canh": lan_b,
            "doan_moi_lo": moi_lo,
            "so_dong": len(cap),
            "dai_dong_flores": [cap[0][0], cap[-1][0]] if cap else [],
            "split_flores": "dev",
            "⚠️ rang_buoc_do_dai": (
                "KHONG RANG BUOC — co y. `ket` suy tu do dai NGUON (len(zh)/1.5) "
                "de `do_dai_toi_da` khong bao gio cham. FLORES khong co thoi "
                "luong; mot tran do dai o day se bien chrF++ thanh phep do DO NEN. "
                "(Ban dau dat ket=6.0 => tran 18 am tiet => ban ra ngan hon tham "
                "chieu 2,4 lan.)"),
            "loi_nhac": van_ban.PHIEN_BAN_LOI_NHAC_LONG_TIENG,
            "⚠️": ("MOI phan tu cua `cac_luot` la MOT LUOT KHAC NHAU tren CUNG "
                  "mot dong FLORES — ⛔ khong phai ba phim, ⛔ khong phai ba "
                  "cau hinh. Duong dich KHONG tai lap duoc (B2_DICH §7.8c)."),
            "⛔ dap_an": ("`tham_chieu_vi` la ban dich NGUOI cua FLORES. No ⛔ "
                         "KHONG di vao loi nhac — chi cot `zh` duoc gui."),
        },
        "so_o_rong": thieu,
        "giay": round(time.time() - t0, 1),
        "muc": muc,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default="ltt-3.5")
    ap.add_argument("--so-dong", type=int, default=100)
    ap.add_argument("--lan", type=int, default=3)
    ap.add_argument("--moi-lo", type=int, default=12)
    ap.add_argument("--lan-b", type=int, default=0,
                    help="so luot dich LAI CO `y_canh` (nhanh B)")
    ap.add_argument("--ra", default="")
    a = ap.parse_args(argv)
    kq = chay(model=a.model, so_dong=a.so_dong, lan=a.lan,
              moi_lo=a.moi_lo, lan_b=a.lan_b)
    n = kq["⭐ nhan_cau_hinh"]
    print(f"FLORES dev zh->vi · {n['so_dong']} dong · {n['model']} · "
          f"t={n['nhiet_do']} · ep luoc do={n['ep_luoc_do']} · {n['so_luot']} luot")
    print(f"  o rong: {kq['so_o_rong']} / {n['so_dong'] * n['so_luot']}"
          f" · {kq['giay']} s")
    if a.ra:
        d = pathlib.Path(a.ra)
        d.mkdir(parents=True, exist_ok=True)
        t = d / f"flores_dich_{a.model}_{n['so_dong']}dong_{a.lan}luot.json"
        t.write_text(json.dumps(kq, ensure_ascii=False, indent=1),
                     encoding="utf-8")
        print(f"  -> {t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
