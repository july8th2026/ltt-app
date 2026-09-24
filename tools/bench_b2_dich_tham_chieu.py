"""Bo do dich CO THAM CHIEU (FLORES-200 zh->vi) — va phep XAC THUC chinh no.

    # 1. buoc TINH (nang — trong khoa `cpu_nhieu`), ca hai che do MetricX
    python tools\\bench_b2_dich_tham_chieu.py cham-tho --nhan <soi_mu.json> --ra tho.json
    # 2. phan tich (nhe — NGOAI khoa)
    python tools\\bench_b2_dich_tham_chieu.py xac-thuc --tho tho.json
    python tools\\bench_b2_dich_tham_chieu.py doi --tho tho.json --nhan <soi_mu.json>

## Vi sao co tep nay

Ta da mat gan mot ngay vi dung mot bo cham **chua duoc xac thuc** (bo cham ngu
nghia QE: bao dong gia 33%, cong <= 15% ⇒ TRUOT). Bo do o day khac o mot diem:
no **co ban dich nguoi de so** (FLORES-200 co ban tieng Viet tham chieu), nen
xac thuc no re hon nhieu — khong can ai gan nhan tay.

⭐ Luat: ⛔ KHONG do ban dich cua ta bang bo do nay truoc khi lenh `xac-thuc`
   xanh. Mot bo do chua tung **do** thi ta chua biet no bat duoc gi.

## Lop TINH vs lop NOI — ⛔ khong tu viet lop tinh

| Lop | Ai lam |
|---|---|
| Diem MetricX-24-Hybrid (tham chieu) | `google-research/metricx` (Apache-2.0), ban GHIM o `apps/asv_gpu/do_luong/_metricx/` |
| chrF / chrF++ / BLEU | `sacrebleu` (Apache-2.0) — **tuy chon**, bo qua neu chua cai |
| Khoang tin cay | `scipy.stats.bootstrap` (BSD-3-Clause) |
| Doc FLORES | `doc_flores()` cua `tools/bench_b2_xac_thuc_bo_cham.py` (lan khac so huu) |
| Lam hong "nang" | `lam_hong_lat_nghia` / `lam_hong_sai_thuc_the` cua cung tep do |

Thu ta viet o day chi la phan **NOI**: chon cau, lam hong "nhe", ghep muc "san",
goi runner, xep bang.

## Bon muc cua phep xac thuc

| Muc | Ung vien la gi | Ky vong |
|---|---|---|
| `tran` | chinh ban dich NGUOI cua FLORES | diem tot nhat |
| `nhe` | hoan vi hai tu ke nhau / bo mot tu | thap hon RO |
| `nang` | lat nghia hoac thay the thuc the | thap hon NHIEU |
| `san` | ban dich cua mot dong KHAC (khong lien quan) | te nhat |

⛔ Bon muc khong xep dung thu tu ⇒ bo do KHONG DUNG DUOC. Do la ket qua quan
   trong, phai bao ngay — ⛔ khong chua chay.

⚠️ `tran` la phep **dong nhat** (ung vien == tham chieu). Voi mot bo do co tham
   chieu day la moc TREN TUYET DOI, khong phai "mot ban dich tot". Khoang cach
   `tran`–`nhe` do duoc vi the la **rong hon** khoang cach thuc te giua mot ban
   dich tot that va cung ban dich ay bi lam hong nhe. Doc bang voi canh bao do.

⚠️ FLORES ⛔ khong hoan hao: do mu 24/09 thay 10/100 dong co loi ro (KTC
   [5,5 ; 17,4]). "Khop FLORES" ⛔ khong bang "hoan hao".
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import random
import re
import statistics
import sys
import time

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

RUNNER = GOC / "tools" / "_metricx_tham_chieu_runner.py"

#: Hat giong cho chon cau + phep lam hong. Tai lap duoc.
HAT_GIONG = 20260924

#: Co mau toi thieu cho mot phan quyet ve thu tu bon muc.
N_TOI_THIEU = 100

#: So lan boc lai cho khoang tin cay bootstrap.
LAN_BOOTSTRAP = 10_000

#: Ten bon muc, theo thu tu KY VONG (tot -> te).
MUC = ("tran", "nhe", "nang", "san")


# ══════════════════════════════════════════════════════════════════════════════
#  0. DUNG LAI — doc FLORES + phep lam hong "nang" cua lan `xac-thuc`
# ══════════════════════════════════════════════════════════════════════════════

def _nap_xac_thuc():
    """Module `bench_b2_xac_thuc_bo_cham` (lan khac so huu). ⛔ Khong chep lai no.

    Duong tim: `tools/` cua cay nay, roi `LTT_XAC_THUC_DIR` (de chay duoc khi tep
    ay chua len `main`).
    """
    for thu_muc in (GOC / "tools", pathlib.Path(os.environ.get("LTT_XAC_THUC_DIR", ""))):
        p = thu_muc / "bench_b2_xac_thuc_bo_cham.py"
        if p.is_file():
            spec = importlib.util.spec_from_file_location("_bench_xac_thuc", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise SystemExit(
        "khong thay bench_b2_xac_thuc_bo_cham.py (doc_flores + phep lam hong).\n"
        "Tep do thuoc lan `xac-thuc`, chua len `main`. Dat LTT_XAC_THUC_DIR tro "
        "vao thu muc chua no, hoac doi no len `main`.")


# ══════════════════════════════════════════════════════════════════════════════
#  1. LAM HONG "NHE" — phan ta tu viet (lan kia chi co phep "nang")
# ══════════════════════════════════════════════════════════════════════════════

#: Tu chuc nang: bo mot tu nay gan nhu khong doi nghia => ⛔ khong dung lam phep
#: "bo mot bo ngu". Ta muon bo mot tu MANG NGHIA.
_TU_CHUC_NANG = frozenset(
    "và của là các những một với cho từ đã sẽ được ở về khi thì mà nhưng "
    "hay hoặc trong ra vào lên xuống này đó nó họ có".split())

_DAU_CUOI = re.compile(r"[.!?,;:\"')\]]+$")


def lam_hong_nhe(cau_vi: str, rng: random.Random) -> tuple[str, str] | None:
    """Nhieu NHE: hoan vi hai tu ke nhau, hoac bo mot tu mang nghia.

    Tra `(cau_hong, ten_phep)`, hoac `None` khi khong ap duoc phep nao.

    ⭐ Tra `None` chu khong tra cau nguyen ven: mot cau "da lam hong" ma thuc ra
       khong doi gi se di vao cot `nhe` va keo diem muc `nhe` len bang muc `tran`
       — tuc ta se ket toi bo do mot loi cua chinh phep lam hong.
    """
    tu = cau_vi.split()
    if len(tu) < 6:
        return None
    phep = ["hoan_vi", "bo_tu"]
    rng.shuffle(phep)
    for ten in phep:
        if ten == "hoan_vi":
            # ⛔ Khong dung o dau/cuoi cau: doi cho tu dau lam hong VIET HOA va
            #    doi cho tu cuoi lam hong DAU CAU — ca hai la loi hinh thuc, se
            #    bi bat vi hinh thuc chu khong vi nghia.
            chon = [i for i in range(1, len(tu) - 2) if tu[i] != tu[i + 1]]
            if chon:
                i = rng.choice(chon)
                moi = list(tu)
                moi[i], moi[i + 1] = moi[i + 1], moi[i]
                return " ".join(moi), "hoan_vi"
        else:
            chon = [i for i in range(1, len(tu) - 1)
                    if _DAU_CUOI.sub("", tu[i]).lower() not in _TU_CHUC_NANG
                    and len(_DAU_CUOI.sub("", tu[i])) >= 2]
            if chon:
                i = rng.choice(chon)
                return " ".join(tu[:i] + tu[i + 1:]), "bo_tu"
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  2. DUNG BON MUC
# ══════════════════════════════════════════════════════════════════════════════

def dung_bon_muc(dong: list[tuple[int, str, str]], n: int, hat: int = HAT_GIONG) -> list[dict]:
    """`[{chi_so, nguon, tham_chieu, ung_vien: {muc: cau}, phep: {...}}]`.

    ⛔ Chi giu dong nao dung duoc CA BON muc. Mot dong thieu mot muc se lam bon
       cot co co mau khac nhau, va so sanh giua cac cot khong con la so sanh tren
       cung tap dong.
    """
    rng = random.Random(hat)
    xt = _nap_xac_thuc()
    thu_tu = list(dong)
    rng.shuffle(thu_tu)

    ra: list[dict] = []
    for chi_so, zh, vi in thu_tu:
        if len(ra) >= n:
            break
        nhe = lam_hong_nhe(vi, rng)
        if nhe is None:
            continue
        # "nang": uu tien lat nghia, khong duoc thi thay the thuc the.
        nang, ten_nang = None, ""
        c = xt.lam_hong_lat_nghia(vi)
        if c and c != vi:
            nang, ten_nang = c, "lat_nghia"
        else:
            c = xt.lam_hong_sai_thuc_the(vi, rng)
            if c and c != vi:
                nang, ten_nang = c, "sai_thuc_the"
        if nang is None:
            continue
        ra.append({
            "chi_so": chi_so, "nguon": zh, "tham_chieu": vi,
            "ung_vien": {"tran": vi, "nhe": nhe[0], "nang": nang, "san": None},
            "phep": {"nhe": nhe[1], "nang": ten_nang},
        })

    # "san": ban dich cua mot dong KHAC. Xoay vong 1 tren chinh tap da chon =>
    # moi dong nhan dung mot ban dich khong lien quan, khong dong nao trung minh.
    for i, m in enumerate(ra):
        m["ung_vien"]["san"] = ra[(i + 1) % len(ra)]["tham_chieu"]
    if len(ra) >= 2 and any(m["ung_vien"]["san"] == m["tham_chieu"] for m in ra):
        raise SystemExit("muc `san` trung tham chieu — phep xoay vong hong")
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  3. CHAM THO — buoc TINH. ⛔ Tach khoi phan tich de giu khoa `cpu_nhieu` ngan
# ══════════════════════════════════════════════════════════════════════════════

#: Hai che do cua MetricX-24-**hybrid** (mot checkpoint, hai cach ghep dau vao).
#: ⭐ `qe` la che do DUNG DUOC THAT: phim khach ⛔ khong co ban dich doi chieu.
#: `tham_chieu` chi chay duoc o noi co san ban dich nguoi (FLORES).
CHE_DO = ("qe", "tham_chieu")


def _cham_mot_che_do(cap: list[dict], che_do: str, *, thiet_bi: str, lo: int,
                     timeout_s: int) -> dict[str, float]:
    """`{ma: diem}` — MQM [0,25], THAP LA TOT. ⛔ Khong tu viet lop tinh."""
    if che_do == "qe":
        # Duong SAN PHAM dang chay (`apps/asv_gpu/do_luong/metricx.py`). Dung lai
        # nguyen ven => con so o day la con so production se thay, khong phai mot
        # ban sao gan giong.
        from apps.asv_gpu.do_luong import metricx
        return metricx.do_dich(
            [{"ma": c["ma"], "nguon": c["nguon"], "dich": c["dich"]} for c in cap],
            ngon_ngu_nguon="zh", ngon_ngu_dich="vi",
            thiet_bi=thiet_bi, lo=lo, timeout_s=timeout_s)
    from apps.asv_gpu.do_luong import venv
    ra = venv.chay(RUNNER, {"cap": cap, "thiet_bi": thiet_bi, "lo": int(lo)},
                   timeout_s=timeout_s)
    diem = ra.get("diem") or {}
    thieu = {c["ma"] for c in cap} - set(diem)
    if thieu:
        raise SystemExit(f"runner thieu diem cho {len(thieu)}/{len(cap)} cap")
    print(f"    {che_do}: {ra.get('thong_tin')}", file=sys.stderr)
    return {k: float(v) for k, v in diem.items()}


def cham_tho(mau: list[dict], dau: list[tuple[int, str, str]] = (), *,
             che_do: tuple[str, ...] = CHE_DO, thiet_bi: str = "auto",
             lo: int = 16, timeout_s: int = 7200,
             ) -> dict[str, dict[str, dict[int, float]]]:
    """`{che_do: {muc: {chi_so: diem}, "dau": {chi_so: diem}}}`.

    `mau`  — bo BON MUC cua phep xac thuc (moi dong du ca bon).
    `dau`  — `(chi_so, zh, vi)` cua san dau: ung vien la chinh ban dich NGUOI.
             ⭐ Tach khoi `mau` vi san dau phai la **DUNG 100 dong da soi mu**,
             con `mau` chi giu duoc dong nao ap duoc ca hai phep lam hong (16/100
             dong soi mu ⛔ khong ap duoc phep "nang"). Ep chung lam mot thi hoac
             san dau thung mat 16 dong, hoac bon cot lech co mau.

    ⭐ MOT luot goi cho tat ca trong moi che do: cung mot lan nap model, moi cap
       di qua **dung mot** trang thai may. Chia nho se them mot nguon lech ma ta
       khong do duoc.
    """
    ra: dict[str, dict[str, dict[int, float]]] = {}
    for cd in che_do:
        cap = [{"ma": f"{muc}|{m['chi_so']}", "nguon": m["nguon"],
                "dich": m["ung_vien"][muc], "tham_chieu": m["tham_chieu"]}
               for m in mau for muc in MUC]
        cap += [{"ma": f"dau|{i}", "nguon": zh, "dich": vi, "tham_chieu": vi}
                for i, zh, vi in dau]
        t0 = time.perf_counter()
        diem = _cham_mot_che_do(cap, cd, thiet_bi=thiet_bi, lo=lo, timeout_s=timeout_s)
        print(f"  {cd}: {len(cap)} cap trong {time.perf_counter() - t0:.0f} s",
              file=sys.stderr)
        bang: dict[str, dict[int, float]] = {muc: {} for muc in (*MUC, "dau")}
        for ma, d in diem.items():
            muc, chi_so = ma.split("|", 1)
            bang[muc][int(chi_so)] = float(d)
        ra[cd] = bang
    return ra


def cham_chrf(mau: list[dict]) -> dict[str, dict[int, float]] | None:
    """`{muc: {chi_so: chrF++}}` — CAO LA TOT. `None` khi chua cai `sacrebleu`.

    ⛔ Khong tu tinh chrF: cong thuc co nhieu bien the (n-gram toi da, beta, cach
       xu ly khoang trang) va mot ban tu viet se khong so duoc voi bat ky so nao
       cong bo o ngoai. `sacrebleu` la ban tham chieu cua cong dong (WMT).
    """
    try:
        from sacrebleu.metrics import CHRF
    except ImportError:
        return None
    do = CHRF(word_order=2)  # chrF++ — them n-gram TU
    return {muc: {m["chi_so"]: do.sentence_score(m["ung_vien"][muc],
                                                 [m["tham_chieu"]]).score
                  for m in mau} for muc in MUC}


# ══════════════════════════════════════════════════════════════════════════════
#  4. KHOANG TIN CAY — ⛔ so tran khong duoc nhan
# ══════════════════════════════════════════════════════════════════════════════

def ktc_trung_binh(x: list[float], muc: float = 0.95) -> tuple[float, float]:
    """KTC bootstrap (BCa) cho trung binh — `scipy.stats.bootstrap`."""
    import numpy as np
    from scipy.stats import bootstrap
    if len(set(x)) <= 1:  # mau suy bien: bootstrap khong co gi de boc
        return (float(x[0]), float(x[0])) if x else (float("nan"),) * 2
    r = bootstrap((np.asarray(x, dtype=float),), np.mean, confidence_level=muc,
                  n_resamples=LAN_BOOTSTRAP, method="BCa",
                  random_state=np.random.default_rng(HAT_GIONG))
    return float(r.confidence_interval.low), float(r.confidence_interval.high)


def ktc_hieu_cap(a: list[float], b: list[float], muc: float = 0.95) -> tuple[float, float]:
    """KTC bootstrap cho trung binh HIEU THEO CAP `b[i] - a[i]`.

    ⭐ Theo CAP, khong phai hai mau doc lap: bon muc do tren **cung mot tap dong**,
       nen do kho cua tung dong la nhieu CHUNG. Boc theo cap khu duoc nhieu do va
       cho khoang hep hon (dung hon) so voi boc hai mau roi tru trung binh.
    """
    return ktc_trung_binh([y - x for x, y in zip(a, b, strict=True)], muc)


def _tom_tat(ten: str, diem: dict[int, float], khoa: list[int], thap_la_tot: bool) -> dict:
    x = [diem[k] for k in khoa]
    lo, hi = ktc_trung_binh(x)
    return {"muc": ten, "n": len(x), "trung_binh": statistics.fmean(x),
            "trung_vi": statistics.median(x), "ktc": (lo, hi),
            "thap_la_tot": thap_la_tot}


def phan_tich(bang: dict[str, dict[int, float]], khoa: list[int], *, ten: str,
              thap_la_tot: bool) -> dict:
    """Bang bon muc + phan quyet thu tu + tach `tran` vs `nhe`."""
    hang = [_tom_tat(m, bang[m], khoa, thap_la_tot) for m in MUC]
    tb = [h["trung_binh"] for h in hang]
    dung_thu_tu = all(
        (tb[i] < tb[i + 1]) if thap_la_tot else (tb[i] > tb[i + 1])
        for i in range(len(tb) - 1))

    cap_ke: dict[str, dict] = {}
    for i in range(len(MUC) - 1):
        a, b = MUC[i], MUC[i + 1]
        x = [bang[a][k] for k in khoa]
        y = [bang[b][k] for k in khoa]
        lo, hi = ktc_hieu_cap(x, y)
        tach = (lo > 0) if thap_la_tot else (hi < 0)  # huong dung = sau TE hon truoc
        cap_ke[f"{a}->{b}"] = {
            "hieu_trung_binh": statistics.fmean([q - p for p, q in zip(x, y, strict=True)]),
            "ktc": (lo, hi), "tach_duoc": tach,
            "ti_le_dong_dung_huong": statistics.fmean(
                [1.0 if ((q > p) if thap_la_tot else (q < p)) else 0.0
                 for p, q in zip(x, y, strict=True)]),
        }
    return {"ten": ten, "thap_la_tot": thap_la_tot, "hang": hang,
            "dung_thu_tu": dung_thu_tu, "cap_ke": cap_ke}


# ══════════════════════════════════════════════════════════════════════════════
#  5. CUOC DAU — MetricX vs bo cham tu nan, tren 100 dong SOI MU
# ══════════════════════════════════════════════════════════════════════════════

#: Tran ti le bao dong gia. ⛔ Khong duoc noi cho ben nao.
NGUONG_BAO_DONG_GIA = 0.15
#: San do nhay tren loi tu nhien. ⛔ Khong duoc ha.
NGUONG_DO_NHAY = 0.50

#: Ba dinh nghia "loi that" cua san dau — LAY Y NGUYEN cua lan `xac-thuc` de hai
#: ben duoc cham bang cung mot thuoc. ⛔ Khong tu dinh nghia lai.
DINH_NGHIA = {"chinh": ("ro",), "rong": ("ro", "zh_lech"),
              "rong_nhat": ("ro", "zh_lech", "bien")}


def doc_nhan_soi_mu(tep: pathlib.Path) -> dict[int, str]:
    """`{dong_flores: phan_quyet}` tu `b2_san_loi_flores.json` (da COMMIT, MU)."""
    d = json.loads(tep.read_text(encoding="utf-8"))
    return {int(m["dong_flores"]): str(m["phan_quyet"]) for m in d["muc"]}


def bang_2x2(gan_co: dict[int, bool], that: dict[int, bool]) -> dict:
    """2x2 + hai ti le cua cong — lop dem/KTC di qua `tools/do_luong.py`.

    ⚠️ HAI mau so, va chung tra loi HAI cau khac nhau. Phai in ca hai, vi mot so
       23% va mot so 77% cua cung mot bang tung lam hai nguoi cai nhau ca buoi:
      - `bao_dong_gia` = FP / **n**        ⇒ so cua CONG (nguong 15%)
      - `bao_dong_gia_tren_gan_co` = FP/FP+TP ⇒ "gan co xong thi sai bao nhieu"
    """
    khoa = sorted(set(gan_co) & set(that))
    tp = sum(1 for k in khoa if gan_co[k] and that[k])
    fp = sum(1 for k in khoa if gan_co[k] and not that[k])
    fn = sum(1 for k in khoa if not gan_co[k] and that[k])
    tn = sum(1 for k in khoa if not gan_co[k] and not that[k])
    n, gan, loi = len(khoa), tp + fp, tp + fn
    from do_luong import ti_le_kem_ktc
    return {
        "n": n, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "so_gan_co": gan, "so_loi_that": loi,
        "bao_dong_gia": ti_le_kem_ktc(fp, n) if n else None,
        "bao_dong_gia_tren_gan_co": ti_le_kem_ktc(fp, gan) if gan else None,
        "do_nhay": ti_le_kem_ktc(tp, loi) if loi else None,
    }


def quet_nguong(diem: dict[int, float], that: dict[int, bool]) -> list[dict]:
    """CA DUONG CONG nguong, ⛔ khong chi diem tot nhat.

    ⭐ MetricX cho diem LIEN TUC ⇒ no co mot duong cong. So "MetricX o diem tot
       nhat" voi "V3 o mot diem" la so lech san; ta in ca duong de doi thu duoc
       so voi duong cua ho.
    """
    moc = sorted({round(v, 3) for v in diem.values()})
    ra = []
    for t in moc:
        b = bang_2x2({k: v <= t for k, v in diem.items()}, that)
        b["nguong"] = t
        ra.append(b)
    return ra


def _qua_cong(b: dict) -> bool:
    return (b["bao_dong_gia"] is not None and b["do_nhay"] is not None
            and b["bao_dong_gia"]["ti_le"] <= NGUONG_BAO_DONG_GIA
            and b["do_nhay"]["ti_le"] >= NGUONG_DO_NHAY)


def chon_nguong(diem: dict[int, float], that: dict[int, bool]) -> dict | None:
    """Nguong TOT NHAT tren tap DUA RA. ⛔ Khong bao so tren chinh tap nay.

    Uu tien: qua cong truoc; trong so do lay do nhay cao nhat, roi BDG thap nhat.
    """
    ung = [b for b in quet_nguong(diem, that) if _qua_cong(b)]
    if not ung:
        return None
    return max(ung, key=lambda b: (b["do_nhay"]["ti_le"], -b["bao_dong_gia"]["ti_le"]))


def nua_va_nua(diem: dict[int, float], that: dict[int, bool],
               hat: int = HAT_GIONG) -> dict:
    """Chon nguong tren NUA A, bao so tren NUA B — chong chinh-tren-bai-thi.

    ⚠️ Moi nua chi con ~5 loi that. ⛔ Day la mot phep RAT MONG; no chi loai duoc
       ca "nguong vua khit bai thi", ⛔ khong cho mot uoc luong chac chan.
    ⭐ Chia PHAN TANG theo nhan: neu boc ngau nhien thuan, mot nua co the trung 2
       loi con nua kia 8, va chenh lech ay se bi doc nham thanh chenh lech nang luc.
    """
    rng = random.Random(hat)
    duong = [k for k in sorted(diem) if that.get(k)]
    am = [k for k in sorted(diem) if not that.get(k)]
    rng.shuffle(duong)
    rng.shuffle(am)
    a = set(duong[::2]) | set(am[::2])
    b = set(duong[1::2]) | set(am[1::2])
    ra = {}
    for ten, dua, bao in (("A->B", a, b), ("B->A", b, a)):
        n_dua = chon_nguong({k: diem[k] for k in dua}, {k: that[k] for k in dua})
        if n_dua is None:
            ra[ten] = {"nguong": None, "ghi_chu": "khong nguong nao qua cong o nua dua ra"}
            continue
        t = n_dua["nguong"]
        kq = bang_2x2({k: diem[k] <= t for k in bao}, {k: that[k] for k in bao})
        kq["nguong"] = t
        kq["so_loi_that_nua_dua_ra"] = n_dua["so_loi_that"]
        ra[ten] = kq
    return ra


def cuoc_dau(diem: dict[int, float], nhan: dict[int, str], *, dinh_nghia: str) -> dict:
    that = {k: (v in DINH_NGHIA[dinh_nghia]) for k, v in nhan.items()}
    that = {k: v for k, v in that.items() if k in diem}
    return {
        "dinh_nghia": dinh_nghia, "nhan_tinh_la_loi": list(DINH_NGHIA[dinh_nghia]),
        "duong_cong": quet_nguong(diem, that),
        "nguong_tot_nhat_tren_chinh_no": chon_nguong(diem, that),
        "nua_va_nua": nua_va_nua(diem, that),
    }


def doc_co_v3(tep: pathlib.Path) -> dict[int, bool]:
    """`{dong_flores: da_gan_co}` cua bo cham V3 (tu nan), tu ban ghi DA COMMIT."""
    g = json.loads(tep.read_text(encoding="utf-8"))["bao_dong_gia"]["gop"]
    return {int(k.split("_")[1]): (not v["dat"]) for k, v in g.items()}


def ghep(diem: dict[int, float], co_v3: dict[int, bool], nhan: dict[int, str], *,
         dinh_nghia: str = "chinh", nguong: float = 6.0) -> dict:
    """Do phep GHEP: MetricX loc truoc o `nguong`, V3 xu phan du.

    ⭐ Hai cach ghep, va chung ⛔ KHONG giong nhau — phai do ca hai:

    - `hop` (thac nuoc that): co = MetricX ∪ V3. Day la thu mot thac nuoc THUC SU
      tra ve — V3 chi duoc GOI tren phan MetricX bo qua, nhung dong nao MetricX
      da gan co thi van la co. ⇒ Cai loi la **CHI PHI** (bot loi goi V3),
      ⛔ khong phai do chinh xac: hop chi co the LAM TANG so bao dong gia.
    - `giao`: co = MetricX ∩ V3 (MetricX dung de **phu quyet**). Ha bao dong gia,
      nhung ha ca do nhay.

    ⚠️ San nay ⛔ KHONG kiem duoc cai loi that su cua phep ghep: no toan loi TU
       NHIEN, TINH VI trong mot ban dich NGUOI — ⛔ khong co mot dong `san` nao
       (khong dich / dich nham ca cau), tuc ⛔ khong co dung cai loai hong ma
       MetricX bat gioi (99 %). Con so duoi day vi the do phep ghep o **dung cho
       no yeu nhat**. ⛔ Doc nhu mot can duoi, ⛔ khong phai mot phan quyet.
    """
    khoa = sorted(set(diem) & set(co_v3) & set(nhan))
    that = {k: (nhan[k] in DINH_NGHIA[dinh_nghia]) for k in khoa}
    co_mx = {k: diem[k] > nguong for k in khoa}  # diem CAO = te => HONG
    ra = {
        "nguong_metricx": nguong, "dinh_nghia": dinh_nghia, "n": len(khoa),
        "metricx_mot_minh": bang_2x2(co_mx, that),
        "v3_mot_minh": bang_2x2({k: co_v3[k] for k in khoa}, that),
        "ghep_hop": bang_2x2({k: co_mx[k] or co_v3[k] for k in khoa}, that),
        "ghep_giao": bang_2x2({k: co_mx[k] and co_v3[k] for k in khoa}, that),
        # Cai loi CHI PHI: bao nhieu dong khong phai goi V3 nua.
        "dong_metricx_da_chot": sum(1 for k in khoa if co_mx[k]),
        "ti_le_loi_goi_v3_tiet_kiem": sum(1 for k in khoa if co_mx[k]) / len(khoa),
        "so_dong_muc_san_tren_san_nay": 0,
    }
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  6. IN
# ══════════════════════════════════════════════════════════════════════════════

def _in_xac_thuc(kq: dict) -> bool:
    huong = "THAP LA TOT" if kq["thap_la_tot"] else "CAO LA TOT"
    print(f"\n╔═ {kq['ten']} ({huong}) ═╗")
    print(f"  {'muc':<6} {'n':>4} {'trung binh':>11} {'trung vi':>10}  KTC95")
    for h in kq["hang"]:
        print(f"  {h['muc']:<6} {h['n']:>4} {h['trung_binh']:>11.3f} "
              f"{h['trung_vi']:>10.3f}  [{h['ktc'][0]:.3f} ; {h['ktc'][1]:.3f}]")
    print(f"\n  Thu tu bon muc: {'✅ DUNG' if kq['dung_thu_tu'] else '⛔ SAI'}")
    print(f"  {'buoc':<14} {'hieu tb':>9}  {'KTC95 (theo cap)':<22} tach?  dong dung huong")
    for ten, c in kq["cap_ke"].items():
        print(f"  {ten:<14} {c['hieu_trung_binh']:>9.3f}  "
              f"[{c['ktc'][0]:>7.3f} ; {c['ktc'][1]:>7.3f}]  "
              f"{'✅' if c['tach_duoc'] else '⛔':<6} {c['ti_le_dong_dung_huong']:>6.1%}")
    c = kq["cap_ke"]["tran->nhe"]
    print(f"\n  ⭐ CAU QUYET DINH — `tran` vs `nhe` tach duoc? "
          f"{'✅ CO' if c['tach_duoc'] else '⛔ KHONG'}  "
          f"(hieu {c['hieu_trung_binh']:.3f}, KTC [{c['ktc'][0]:.3f} ; {c['ktc'][1]:.3f}])")
    return kq["dung_thu_tu"] and c["tach_duoc"]


def _p(d: dict | None) -> str:
    if not d:
        return "—"
    return (f"{d['ti_le']:>6.1%} [{d['ktc'][0]:.1%} ; {d['ktc'][1]:.1%}]"
            if isinstance(d.get("ktc"), (list, tuple)) else f"{d['ti_le']:>6.1%}")


def _in_bang(b: dict, nhan: str = "") -> None:
    print(f"  {nhan:<10} n={b['n']:<4} gan co {b['so_gan_co']:<3} "
          f"loi that {b['so_loi_that']:<3} TP {b['tp']:<3} FP {b['fp']:<3} FN {b['fn']:<3}")
    print(f"  {'':<10} BDG (FP/n) {_p(b['bao_dong_gia'])}  "
          f"| BDG tren gan co {_p(b['bao_dong_gia_tren_gan_co'])}  "
          f"| do nhay {_p(b['do_nhay'])}  "
          f"=> {'✅ QUA CONG' if _qua_cong(b) else '⛔ TRUOT'}")


def _in_dau(d: dict, che_do: str) -> None:
    print(f"\n╔═ CUOC DAU — MetricX ({che_do}) · dinh nghia `{d['dinh_nghia']}` "
          f"({'+'.join(d['nhan_tinh_la_loi'])}) ═╗")
    dc = [b for b in d["duong_cong"] if b["so_gan_co"]]
    print(f"  Duong cong nguong ({len(dc)} moc) — vai moc tieu bieu:")
    print(f"  {'nguong':>8} {'gan co':>7} {'TP':>3} {'FP':>3} {'BDG(FP/n)':>10} {'do nhay':>9}  cong")
    buoc = max(1, len(dc) // 12)
    for b in dc[::buoc]:
        print(f"  {b['nguong']:>8.3f} {b['so_gan_co']:>7} {b['tp']:>3} {b['fp']:>3} "
              f"{b['bao_dong_gia']['ti_le']:>10.1%} {b['do_nhay']['ti_le']:>9.1%}  "
              f"{'✅' if _qua_cong(b) else ''}")
    t = d["nguong_tot_nhat_tren_chinh_no"]
    if t is None:
        print("\n  ⛔ KHONG mot nguong nao qua duoc CA HAI cong tren chinh tap nay.")
    else:
        print(f"\n  Nguong tot nhat tren CHINH tap nay (nguong={t['nguong']:.3f}) "
              f"— ⚠️ so nay CHINH TREN BAI THI, khong dung de phan quyet:")
        _in_bang(t)
    print("\n  ⭐ Chong chinh-tren-bai-thi — chon nguong tren mot nua, bao so tren nua kia:")
    for ten, b in d["nua_va_nua"].items():
        if b.get("nguong") is None:
            print(f"  {ten:<10} ⛔ {b['ghi_chu']}")
        else:
            _in_bang(b, ten)


# ══════════════════════════════════════════════════════════════════════════════
#  7. LENH
# ══════════════════════════════════════════════════════════════════════════════

def lenh_cham_tho(a: argparse.Namespace) -> int:
    """Buoc TINH. ⭐ Chay trong khoa `cpu_nhieu`; phan tich lam NGOAI khoa."""
    xt = _nap_xac_thuc()
    dong = xt.doc_flores()
    print(f"FLORES dev: {len(dong)} dong dung duoc", file=sys.stderr)

    # Bo XAC THUC: lay tu CA dai FLORES — can 100 dong du ca bon muc.
    mau = dung_bon_muc(dong, a.n)
    if len(mau) < N_TOI_THIEU:
        raise SystemExit(f"chi dung duoc {len(mau)} dong, can >= {N_TOI_THIEU}")

    # San DAU: DUNG nhung dong da soi mu, khong bot mot dong nao.
    dau: list[tuple[int, str, str]] = []
    if a.nhan:
        giu = set(doc_nhan_soi_mu(pathlib.Path(a.nhan)))
        dau = [d for d in dong if d[0] in giu]
        if len(dau) != len(giu):
            raise SystemExit(
                f"san dau thung: {len(dau)}/{len(giu)} dong soi mu tim thay trong FLORES")
    print(f"Xac thuc: {len(mau)} dong x {len(MUC)} muc · San dau: {len(dau)} dong",
          file=sys.stderr)

    tho = cham_tho(mau, dau, che_do=tuple(a.che_do.split(",")),
                   thiet_bi=a.thiet_bi, lo=a.lo)
    chrf = cham_chrf(mau)
    if chrf is None:
        print("⚠️  chua cai `sacrebleu` — bo qua chrF++", file=sys.stderr)
    pathlib.Path(a.ra).write_text(json.dumps({
        "hat_giong": HAT_GIONG, "n": len(mau), "n_dau": len(dau),
        "mau": [{"chi_so": m["chi_so"], "phep": m["phep"]} for m in mau],
        "metricx": tho, "chrf": chrf,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"-> {a.ra}", file=sys.stderr)
    return 0


def _doc_tho(tep: str) -> dict:
    d = json.loads(pathlib.Path(tep).read_text(encoding="utf-8"))
    for cd, bang in d["metricx"].items():
        d["metricx"][cd] = {m: {int(k): float(v) for k, v in b.items()}
                            for m, b in bang.items()}
    if d.get("chrf"):
        d["chrf"] = {m: {int(k): float(v) for k, v in b.items()}
                     for m, b in d["chrf"].items()}
    return d


def lenh_xac_thuc(a: argparse.Namespace) -> int:
    d = _doc_tho(a.tho)
    khoa = sorted(d["metricx"][next(iter(d["metricx"]))]["tran"])
    ket = []
    for cd, bang in d["metricx"].items():
        ket.append(phan_tich(bang, khoa, ten=f"MetricX-24-Hybrid ({cd})",
                             thap_la_tot=True))
    if d.get("chrf"):
        ket.append(phan_tich(d["chrf"], khoa, ten="chrF++ (sacrebleu)",
                             thap_la_tot=False))
    dat = all(_in_xac_thuc(k) for k in ket)
    print(f"\n{'✅ BO DO PHAN BIET DUOC' if dat else '⛔ BO DO KHONG DUNG DUOC — bao dieu phoi, KHONG chua chay'}")
    return 0 if dat else 1


def lenh_doi(a: argparse.Namespace) -> int:
    d = _doc_tho(a.tho)
    nhan = doc_nhan_soi_mu(pathlib.Path(a.nhan))
    for cd, bang in d["metricx"].items():
        # ⭐ Ung vien la chinh ban dich NGUOI cua FLORES — dung thu ma nguoi soi mu
        #    da phan quyet. ⛔ Khong phai mot ban lam hong.
        diem = bang.get("dau") or {}
        if not diem:
            raise SystemExit("tep tho khong co bo `dau` — chay lai `cham-tho --nhan ...`")
        if cd == "tham_chieu":
            print("\n⚠️  Che do `tham_chieu` tren san nay la phep DONG NHAT (ung vien"
                  " == tham chieu): FLORES ⛔ khong co ban dich thu hai de doi chieu."
                  " Con so duoi day do MOT HANG SO, khong do nang luc — no co mat de"
                  " CHUNG MINH dieu do, ⛔ khong de phan quyet.", file=sys.stderr)
        for dn in a.dinh_nghia.split(","):
            _in_dau(cuoc_dau(diem, nhan, dinh_nghia=dn), cd)
    if a.ra:
        pathlib.Path(a.ra).write_text(json.dumps(
            {cd: {dn: cuoc_dau(b["dau"], nhan, dinh_nghia=dn)
                  for dn in a.dinh_nghia.split(",")}
             for cd, b in d["metricx"].items() if b.get("dau")},
            ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


def lenh_ghep(a: argparse.Namespace) -> int:
    d = _doc_tho(a.tho)
    diem = d["metricx"][a.che_do]["dau"]
    r = ghep(diem, doc_co_v3(pathlib.Path(a.v3)),
             doc_nhan_soi_mu(pathlib.Path(a.nhan)),
             dinh_nghia=a.dinh_nghia, nguong=a.nguong)
    print(f"\n╔═ PHEP GHEP — MetricX ({a.che_do}) @ {r['nguong_metricx']} loc truoc, "
          f"V3 xu phan du · n={r['n']} ═╗")
    print("  ⚠️ CACH MOI (doi chieu nguoi soi MU). ⛔ Khong so voi bang 'cach cu' "
          "(V1 43,3% · V2 16,7% · V3 23,3%) — khac THUOC.\n")
    for ten in ("metricx_mot_minh", "v3_mot_minh", "ghep_hop", "ghep_giao"):
        _in_bang(r[ten], ten)
    print(f"\n  Cai loi CHI PHI: MetricX chot san {r['dong_metricx_da_chot']}/{r['n']} dong "
          f"({r['ti_le_loi_goi_v3_tiet_kiem']:.1%} loi goi V3 tiet kiem duoc)")
    print(f"\n  ⚠️ San nay co {r['so_dong_muc_san_tren_san_nay']} dong muc `san` "
          "(khong dich / dich nham ca cau) — tuc ⛔ KHONG co dung loai hong ma\n"
          "     MetricX bat gioi (99%). Bang tren do phep ghep o dung cho no YEU\n"
          "     nhat ⇒ doc nhu mot CAN DUOI, ⛔ khong phai mot phan quyet.")
    if a.ra:
        pathlib.Path(a.ra).write_text(json.dumps(r, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    return 0


def lenh_bench(a: argparse.Namespace) -> int:
    """Cham ban dich THAT cua ta tren FLORES. ⛔ Chi chay sau khi `xac-thuc` xanh.

    Moi `--dich` la MOT LUOT: JSON `{chi_so_dong: "cau da dich"}` (chi so FLORES
    dev). ⛔ Tep nay khong goi model dich — no chi cham.

    🔴 **BAT BUOC >= 3 LUOT.** Duong dich ⛔ KHONG TAI LAP DUOC: temp 0,0 + ep
       luoc do + seed van cho ba ban khac nhau o MOI doan (0 on dinh / 12 doi).
       ⇒ mot luot ⛔ khong phai mot con so. Bao **trung vi + khoang**, ⛔ khong
       bao mot so tran.
    ⚠️ FLORES co ~10 % dong loi ro ⇒ "khop FLORES" ⛔ khong bang "dung".
    """
    if len(a.dich) < 3:
        raise SystemExit(
            f"chi co {len(a.dich)} luot, can >= 3 — duong dich khong tai lap duoc,\n"
            "mot luot khong phai mot con so (xem docstring)")
    xt = _nap_xac_thuc()
    dong = {i: (zh, vi) for i, zh, vi in xt.doc_flores()}

    luot: list[dict] = []
    for k, tep in enumerate(a.dich, 1):
        ban = {int(i): str(c) for i, c in
               json.loads(pathlib.Path(tep).read_text(encoding="utf-8")).items()}
        thieu = set(ban) - set(dong)
        if thieu:
            raise SystemExit(f"luot {k}: {len(thieu)} chi so khong co trong FLORES dev")
        if len(ban) < N_TOI_THIEU:
            raise SystemExit(f"luot {k}: chi co {len(ban)} cau, can >= {N_TOI_THIEU}")
        khoa = sorted(ban)
        r: dict[str, object] = {"tep": tep, "n": len(khoa)}

        # chrF++ — NHE, ⛔ khong can khoa. Diem CUM (corpus) la cach cong bo chuan.
        try:
            from sacrebleu.metrics import CHRF
            r["chrf"] = CHRF(word_order=2).corpus_score(
                [ban[i] for i in khoa], [[dong[i][1] for i in khoa]]).score
        except ImportError:
            print("⚠️  chua cai `sacrebleu` — bo qua chrF++", file=sys.stderr)

        if not a.bo_metricx:  # NANG — di qua chay_nang.py
            from apps.asv_gpu.do_luong import metricx
            diem = metricx.do_dich(
                [{"ma": str(i), "nguon": dong[i][0], "dich": ban[i]} for i in khoa],
                ngon_ngu_nguon="zh", ngon_ngu_dich="vi",
                thiet_bi=a.thiet_bi, lo=a.lo, timeout_s=7200)
            v = [float(diem[str(i)]) for i in khoa]
            r["metricx_trung_vi"] = statistics.median(v)
            r["metricx_trung_binh"] = statistics.fmean(v)
            r["metricx_ktc"] = ktc_trung_binh(v)
            r["metricx_qua_nguong_san_pham"] = sum(
                1 for x in v if x > metricx.NGUONG_DO[("zh", "vi")])
        luot.append(r)

    print(f"\n╔═ BAN DICH CUA TA tren FLORES zh->vi · {len(luot)} LUOT ═╗")
    print("  ⚠️ Duong dich KHONG tai lap duoc ⇒ doc TRUNG VI + KHOANG, ⛔ khong doc mot luot.")
    for ten, khoa_r, cao_tot in (("chrF++ (cum)", "chrf", True),
                                 ("MetricX QE (trung vi)", "metricx_trung_vi", False)):
        v = [r[khoa_r] for r in luot if khoa_r in r]
        if not v:
            continue
        print(f"\n  {ten}  ({'cao la tot' if cao_tot else 'THAP la tot'})")
        for k, x in enumerate(v, 1):
            print(f"    luot {k}: {x:.3f}")
        print(f"    ⭐ trung vi {statistics.median(v):.3f}  "
              f"khoang [{min(v):.3f} ; {max(v):.3f}]  (bien do {max(v) - min(v):.3f})")
    print("\n  ⚠️ FLORES co ~10 % dong loi ro ⇒ 'khop FLORES' ⛔ khong bang 'dung'.")
    if a.ra:
        pathlib.Path(a.ra).write_text(json.dumps({"luot": luot}, ensure_ascii=False,
                                                 indent=1), encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    con = p.add_subparsers(dest="lenh", required=True)

    c = con.add_parser("cham-tho", help="buoc TINH — cham 4 muc, ghi diem tho")
    c.add_argument("--n", type=int, default=N_TOI_THIEU)
    c.add_argument("--nhan", help="b2_san_loi_flores.json — chi lay dong da soi mu")
    c.add_argument("--che-do", default=",".join(CHE_DO))
    c.add_argument("--thiet-bi", default="auto", choices=("auto", "cpu", "cuda"))
    c.add_argument("--lo", type=int, default=16)
    c.add_argument("--ra", required=True)
    c.set_defaults(fn=lenh_cham_tho)

    x = con.add_parser("xac-thuc", help="bang bon muc + KTC (ngoai khoa)")
    x.add_argument("--tho", required=True)
    x.set_defaults(fn=lenh_xac_thuc)

    b = con.add_parser("bench", help="cham ban dich THAT cua ta (>= 3 luot)")
    b.add_argument("--dich", required=True, nargs="+", metavar="LUOT.json",
                   help='>= 3 tep, moi tep MOT luot: {chi_so: "cau da dich"}')
    b.add_argument("--thiet-bi", default="auto", choices=("auto", "cpu", "cuda"))
    b.add_argument("--lo", type=int, default=16)
    b.add_argument("--bo-metricx", action="store_true", help="chi chrF (nhe)")
    b.add_argument("--ra")
    b.set_defaults(fn=lenh_bench)

    g = con.add_parser("ghep", help="MetricX loc truoc + V3 xu phan du (ngoai khoa)")
    g.add_argument("--tho", required=True)
    g.add_argument("--nhan", required=True, help="b2_san_loi_flores.json (soi mu)")
    g.add_argument("--v3", required=True, help="b2_cham_v3_tren_100_dong_soi_mu.json")
    g.add_argument("--nguong", type=float, default=6.0, help="nguong san pham MetricX")
    g.add_argument("--che-do", default="qe")
    g.add_argument("--dinh-nghia", default="chinh")
    g.add_argument("--ra")
    g.set_defaults(fn=lenh_ghep)

    d = con.add_parser("doi", help="cuoc dau 2x2 vs bo cham tu nan (ngoai khoa)")
    d.add_argument("--tho", required=True)
    d.add_argument("--nhan", required=True)
    d.add_argument("--dinh-nghia", default="chinh,rong,rong_nhat")
    d.add_argument("--ra")
    d.set_defaults(fn=lenh_doi)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
