"""bench_b2_ab_y_canh.py — `y_canh` CO giup khong? Sinh TAP MU cho nguoi cham.

    python tools/bench_b2_ab_y_canh.py --lan 3 --ra <thu muc>

## ⭐ Vi sao phep nay MOI co nghia

Phep A/B cu (`§4f`) la **RONG**: "dich lai tron" va "dich lai qua vong sua" la
**CUNG MOT DONG MA**, vi ⛔ khong ai truyen `y_canh` (`B2_DICH.md` §7.10).
Sau khi noi `y_canh` (§7.11), hai nhanh **khac that**:

    nhanh A   dich lai KHONG `y_canh`   <- dung san pham HOM QUA
    nhanh B   dich lai CO  `y_canh`     <- san pham sau ban va

## 🔴 `y_canh` o day la LY DO DUNG (nguoi xac minh), ⛔ KHONG phai dau ra bo cham

⚠️ **Phai khai to, vi no doi PHAM VI cua ket luan.** Ta chi co **2** phan quyet
that cua bo cham (`b2_vong_sua/v3_cham.json`) — ⛔ khong du cho mot tap 12 doan,
va sinh them doi hoi `ltt-3.8` (da nhuong han lan bo cham).

⇒ Bay ca con lai lay tu **7 ca hong DA XAC MINH BANG NGUOI** (`B2_DICH.md` §4d).
⇒ Phep nay tra loi: ⭐ **"Neu ly do la DUNG, model co sua duoc khong?"** — tuc
   **tran tren** cua duong `y_canh`.
⛔ No ⛔ **khong** tra loi *"vong sua that co giup khong"*: bo cham that co bao
   dong gia **43 %**, nen `y_canh` that se **on hon** han o day.
⭐ Va do la thu tu dung: **neu `y_canh` ⛔ khong giup ngay ca khi ly do DUNG,
   thi no se ⛔ khong bao gio giup.**

## ⛔ TAP MU — bon duong ro ri phai chan

1. ⛔ `ma` **ngau nhien**, ⛔ khong ma hoa nhanh;
2. ⛔ **xao** thu tu muc;
3. ⛔ trong MOI cap, thu tu `ban_1`/`ban_2` **xao doc lap**;
4. ⭐ **cham theo CAP mot cach CONG KHAI**: cung mot cau nguon xuat hien o ca hai
   nhanh, nen neu de roi ra thi nguoi cham **se nhan ra cap** va cham tuong doi
   — mot **ro ri**. Cho no thanh cap **co y** thi phep so la **co chu dich**.

⛔ **Khoa nam o tep RIENG.** Nguoi cham commit phan quyet TRUOC khi xem khoa.

## ⚠️ Do dai co the to cao nhanh

Neu `y_canh` lam ban dich dai hon mot cach he thong thi nguoi cham doan duoc.
⇒ Tep nay **tu do** ti le do dai hai nhanh va in ra; ⛔ khong de nguoi cham
tu phat hien.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import statistics
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                               # noqa: BLE001
    pass

NGUON = GOC / "docs/auto_scan_video_final/bang_chung/b1_chep_loi_moi"
CHAM = GOC / "docs/auto_scan_video_final/bang_chung/b2_vong_sua/v3_cham.json"

#: 🔴 **BAY ca hong DA XAC MINH BANG NGUOI** (`B2_DICH.md` §4d, §4.3).
#: `(phim, tu_goc, nghi_ngo, ban_cu_sai)` — `ban_cu_sai` la thu ban NEN da ra,
#: chep nguyen van tu bang §4d.
#: ⛔ Day la ly do DUNG, ⛔ khong phai dau ra bo cham — xem docstring dau tep.
CA_NGUOI: tuple[tuple[str, str, str, str], ...] = (
    ("v3", "掐雷", "`雷` o day la LUU DAN, khong phai min; `掐雷` = nau luu dan "
     "(giu vai giay roi nem)", "nem min"),
    ("v3", "纯白给", "tieng long game: chet vo ich / nap mang — khong phai nghia "
     "mat chu", "bi cho trang tay"),
    ("v3", "补人", "thuat ngu game: ket lieu dich DA GUC; phai dung MOT cach goi "
     "nhat quan", "tieu diet / xu ly"),
    ("v1", "烧酒", "phim Han: day la SOJU, khong phai shochu (ten Nhat)",
     "ruou shochu"),
    ("v1", "热胀冷缩", "khai niem GIAN NO VI NHIET, khong phai 'do nong lanh'",
     "do nong lanh"),
    ("v1", "师傅", "sai chinh ta 'thay' va KHONG nhat quan giua cac lan",
     "thay bep / nguoi lam bep"),
    ("v2", "这才是", "'这才是' = 'DAY moi la', khong phai 'Moi day' (= gan day)",
     "Moi day moi la"),
)


def _doan_cua(phim: str, chua: str) -> dict | None:
    ban = json.loads((NGUON / f"{phim}.json").read_text(encoding="utf-8"))
    for d in ban["doan"]:
        if chua in d["chu"]:
            return {"phim": phim, "ma": d["ma"], "chu": d["chu"],
                    "bat": d["bat"], "ket": d["ket"]}
    return None


def tap_thu() -> list[dict]:
    """Cac doan thu + `y_canh` cua chung. ⛔ Moi doan mang nguon cua `y_canh`."""
    ra: list[dict] = []
    for phim, tu, ly, cu in CA_NGUOI:
        d = _doan_cua(phim, tu)
        if d is None:
            continue
        d["y_canh"] = {"nghi_ngo": ly, "trich_nguon": tu, "trich_ban_cu": cu}
        d["nguon_y_canh"] = "NGUOI xac minh (B2_DICH §4d)"
        ra.append(d)
    # ⭐ Hai phan quyet THAT cua bo cham — giu rieng nhan de nguoi doc sau biet
    #    hai ca nay thuoc mot LOAI KHAC (co the mang bao dong gia).
    if CHAM.exists():
        c = json.loads(CHAM.read_text(encoding="utf-8"))
        ban = json.loads((NGUON / "v3.json").read_text(encoding="utf-8"))
        theo_ma = {d["ma"]: d for d in ban["doan"]}
        for k in c.get("bi_gan_co") or []:
            d = theo_ma.get(k["ma"])
            if d is None:
                continue
            ra.append({
                "phim": "v3", "ma": d["ma"], "chu": d["chu"],
                "bat": d["bat"], "ket": d["ket"],
                "y_canh": {"nghi_ngo": " ".join(str(k.get("ly_do") or "").split()),
                           "trich_nguon": str(k.get("goc") or "")[:160],
                           "trich_ban_cu": str(k.get("dich_nen") or "")[:160]},
                "nguon_y_canh": "BO CHAM that (v3_cham.json)",
            })
    return ra


def _dich(db, doan: list[dict], *, mid: str, co_y_canh: bool) -> dict:
    from platform_core.llm import dieu_phoi

    from apps.auto_scan_video import ai, long_tieng as L

    lo = [{"ma": d["ma"], "chu": d["chu"], "bat": d["bat"], "ket": d["ket"]}
          for d in doan]
    yc = {d["ma"]: d["y_canh"] for d in doan} if co_y_canh else None
    msg = L.loi_nhac(lo, tat_ca=lo, ngon_ngu_goc="zh", dac_diem_giong={},
                     ngon_ngu_dich="vi", y_canh=yc)
    tran, cho = ai.ngan_sach_cho(ai.CHUYEN_LOI_THOAI)
    kq = dieu_phoi.goi(
        db, messages=msg, thu_tu_provider=list(ai.THU_TU_PROVIDER),
        model_theo_provider={p: mid for p in ai.THU_TU_PROVIDER},
        temperature=ai.nhiet_do_cho(ai.CHUYEN_LOI_THOAI),
        max_tokens=tran, them={"response_format": L.luoc_do_phan_hoi(lo)},
        timeout_s=float(cho or 300.0))
    noi = getattr(kq, "noi_dung", None) or getattr(kq, "content", "")
    try:
        tho = (ai.doc_json(str(noi), ai.CHUYEN_LOI_THOAI) or {}).get("doan")
    except Exception:                           # noqa: BLE001
        return {}
    if not isinstance(tho, dict):
        return {}
    ma = {d["ma"] for d in lo}
    return {m: str((v or {}).get("chu") or "")
            for m, v in tho.items() if m in ma and isinstance(v, dict)}


def chay(*, model: str, lan: int, hat: int) -> tuple[dict, dict]:
    import platform_core.db as dbmod
    from platform_core.llm import canonical

    from apps.auto_scan_video import ai

    rnd = random.Random(hat)
    doan = tap_thu()
    mid = canonical.ALIAS_SANG_ID.get(model, model)

    db = next(dbmod.get_session())
    try:
        A = [_dich(db, doan, mid=mid, co_y_canh=False) for _ in range(lan)]
        B = [_dich(db, doan, mid=mid, co_y_canh=True) for _ in range(lan)]
    finally:
        db.close()

    muc, khoa = [], []
    for d in doan:
        for i in range(lan):
            a, b = A[i].get(d["ma"], ""), B[i].get(d["ma"], "")
            if not a or not b:
                continue                        # ⛔ thieu mot ve thi bo CA CAP
            ma_mu = hashlib.sha256(
                f"{d['ma']}|{i}|{hat}".encode()).hexdigest()[:10]
            # ⛔ Xao thu tu TRONG cap, doc lap moi cap.
            dao = rnd.random() < 0.5
            muc.append({"ma": ma_mu, "zh": d["chu"],
                        "ban_1": b if dao else a,
                        "ban_2": a if dao else b})
            khoa.append({"ma": ma_mu, "doan": d["ma"], "phim": d["phim"],
                         "luot": i + 1,
                         "ban_1": "B" if dao else "A",
                         "ban_2": "A" if dao else "B",
                         "nguon_y_canh": d["nguon_y_canh"],
                         "y_canh": d["y_canh"]})
    rnd.shuffle(muc)                            # ⛔ xao thu tu MUC

    # ⚠️ Do dai co to cao nhanh khong? Do TRUOC, ⛔ dung de nguoi cham tu thay.
    la = [len(x.split()) for r in A for x in r.values() if x]
    lb = [len(x.split()) for r in B for x in r.values() if x]
    do_dai = {
        "A_trung_vi_tu": statistics.median(la) if la else 0,
        "B_trung_vi_tu": statistics.median(lb) if lb else 0,
        "ti_le_B_tren_A": (round(statistics.median(lb) / statistics.median(la), 3)
                           if la and lb and statistics.median(la) else None),
        "⚠️": ("Neu ti le lech nhieu khoi 1,00 thi DO DAI to cao nhanh va tap "
              "MU khong con mu. Bao cho nguoi cham TRUOC."),
    }
    mu = {
        "⭐ huong_dan": (
            "Moi muc co MOT cau nguon `zh` va HAI ban dich. Voi tung muc: ban "
            "nao TOT HON, hay NGANG NHAU? Kem DOAN TRICH + ly do. Khong trich "
            "duoc => khong tinh la loi. Nghi ngo => ghi 'bien'."),
        "⛔ khong_co_gi_trong_day_noi_ve_nhanh": True,
        "so_muc": len(muc), "muc": muc,
    }
    k = {
        "⛔ KHOA — ⛔ dung mo truoc khi commit phan quyet": True,
        "hat_xao": hat, "so_luot_moi_nhanh": lan, "model": model,
        "nhiet_do": ai.nhiet_do_cho(ai.CHUYEN_LOI_THOAI), "ep_luoc_do": True,
        "⚠️ pham_vi": ("`y_canh` o day la LY DO DUNG (7 ca NGUOI xac minh + 2 "
                      "phan quyet THAT cua bo cham). => Phep do TRAN TREN cua "
                      "duong `y_canh`, ⛔ KHONG phai 'vong sua that co giup "
                      "khong' (bo cham that co bao dong gia 43 %)."),
        "do_dai": do_dai, "cap": khoa,
    }
    return mu, k


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default="ltt-3.5")
    ap.add_argument("--lan", type=int, default=3)
    ap.add_argument("--hat", type=int, default=20260925)
    ap.add_argument("--ra", default="")
    a = ap.parse_args(argv)
    mu, khoa = chay(model=a.model, lan=a.lan, hat=a.hat)
    dd = khoa["do_dai"]
    print(f"tap mu: {mu['so_muc']} muc ({a.lan} luot moi nhanh)")
    print(f"  do dai  A {dd['A_trung_vi_tu']} tu · B {dd['B_trung_vi_tu']} tu "
          f"· ti le B/A {dd['ti_le_B_tren_A']}")
    if a.ra:
        d = pathlib.Path(a.ra)
        d.mkdir(parents=True, exist_ok=True)
        (d / "ab_y_canh_TAP_MU.json").write_text(
            json.dumps(mu, ensure_ascii=False, indent=1), encoding="utf-8")
        (d / "ab_y_canh_KHOA.json").write_text(
            json.dumps(khoa, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  -> {d / 'ab_y_canh_TAP_MU.json'}")
        print(f"  -> {d / 'ab_y_canh_KHOA.json'}  (⛔ khoa)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
