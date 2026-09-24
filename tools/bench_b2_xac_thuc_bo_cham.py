r"""bench_b2_xac_thuc_bo_cham.py — BO CHAM ngu nghia cua ASV co dang tin khong?

    python tools\bench_b2_xac_thuc_bo_cham.py tai
    python tools\bench_b2_xac_thuc_bo_cham.py do --n 100 --luot 3 --ra <ra.json>
    python tools\bench_b2_xac_thuc_bo_cham.py bao-cao <ra.json>

## Cau hoi

Luot chay that cham **44/95 muc (46 %)** la *dich sai*. 46 % do la ban dich te
that, hay bo cham qua tay? Hai cau tra loi dan toi hai viec hoan toan khac nhau
— sua BAN DICH hay sua BO CHAM.

⚠️ Nghi ngo co co so: model CUNG LOAI o lop kiem HINH cho **9/9 bao dong gia**
   khi soi tay (M-10 trong `LOI_TONG.md`), va lop do da bi ha xuong *tu van*.

## Cach do (Q6, chu du an chot)

FLORES-200 co cap `zho_Hans` <-> `vie_Latn` **do NGUOI dich**. Dua cap (nguon zh,
ban dich chuan vi) cho **CHINH** lop cham ngu nghia cua ASV. Moi lan no phan
*"dich sai"* tren mot ban dich cua nguoi => **bao dong gia theo dinh nghia**.

⛔ **DOI CHUNG AM khong duoc bo.** Khong co no thi "bao dong gia 0 %" co the chi
   nghia la bo cham **khong bao gio bao gi** — va ta se ket luan no dang tin
   trong khi no da chet. Nen: >= 30 cap DA LAM HONG co chu y, tach hai loai
   (`lat_nghia` / `sai_thuc_the`), bao ti le bat duoc **cho tung loai**.

⚠️ `L_DICH.md` §3: MetricX co AUC **0,61** cho lat nghia zh->vi — gan nhu tung
   dong xu. Neu lop `qc_ai` cung yeu o lat nghia thi ta **mu o dung cho te
   nhat**, va do la phat hien quan trong hon con so tong.

## ⛔ MOT LUOT DON LE KHONG PHAI MOT PHAN QUYET

Cong dang ap `--temp 1.0` va `seed` **KHONG co hieu luc** (do 24/09: 5 luot cung
dau vao cho 4 ket qua khac nhau; `temperature=0.0` cung van khac). Nen moi cap
cham **>= 3 luot**, lay **trung vi** (da so), va bao cao **kem dai**.

## ⛔ GIAY PHEP: CC-BY-SA-4.0 — ShareAlike

FLORES-200 la CC-BY-SA-4.0 (`README.md` goc cua `facebookresearch/flores`; ⚠️ kho
do con co `LICENSE_CC-BY-NC4.0` nhung dieu khoan NC thuoc **NLLB-MD**, khong phai
FLORES-200). Vi ShareAlike:

  * ⛔ **Khong ghi cau FLORES vao ban ghi ket qua**, va ⛔ khong ghi cac cap da
    lam hong (chung la tac pham PHAI SINH). Ban ghi chi co **chi so dong FLORES**
    + phan quyet + `ly_do` do model sinh ra => du de tai lap, khong phan phoi
    lai mot chu nao.
  * ⛔ Khong dua vao duong san pham. Tep nay la cong cu DO.

Xem `docs/auto_scan_video_final/THIRD_PARTY_METRICS.md` §1 dong 11.

## ⛔ Di dung duong san pham

`qc_ai.loi_nhac_ngu_nghia` -> `ai.goi` -> `qc_ai.doc_ngu_nghia`. Khong viet mot
loi nhac rieng cho phep do: mot loi nhac khac loi nhac san pham se tra loi ve
mot he thong khong phai he thong dang chay.

## ⛔ Khoa may

Tep nay **chi goi may B** (cho mang, khong dot loi may A) => **KHONG** giu
`cpu_nhieu`. Tran dong thoi <= 2 request moi model (CLAUDE.md toan cuc); tep nay
goi TUAN TU, tuc mot request mot luc.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import random
import re
import sys
import tarfile
import time
import urllib.request

GOC = pathlib.Path(__file__).resolve().parent.parent
if str(GOC) not in sys.path:
    sys.path.insert(0, str(GOC))

#: Ban FLORES-200 duoc GHIM. ⛔ Sai sha256 => dung, khong doan.
FLORES_URL = "https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz"
FLORES_SHA256 = "b8b0b76783024b85797e5cc75064eb83fc5288b41e9654dabc7be6ae944011f6"
FLORES_BYTE = 25_585_843

#: Cho cat FLORES. Cung o voi `hf-cache` — mot cho cho moi thu tai ve.
FLORES_DIR = pathlib.Path(
    os.environ.get("LTT_FLORES_DIR")
    or r"C:\LTTPlatform\hf-cache\flores200") / "flores200_dataset"

# ══════════════════════════════════════════════════════════════════════════════
#  NGUONG — ⛔ viet TRUOC khi chay, khong duoc noi sau khi thay so
# ══════════════════════════════════════════════════════════════════════════════

#: Bo cham DANG TIN khi ti le bao dong gia <= muc nay tren >= `N_TOI_THIEU` cap.
NGUONG_BAO_DONG_GIA = 0.15

#: Co mau toi thieu cho phan quyet ve bao dong gia.
N_TOI_THIEU = 100

#: Bo cham con SONG khi bat duoc >= muc nay o MOI loai loi tiem.
#:
#: ⭐ Day khong phai mot nguong chat luong — no la mot phep **do mach**. Duoi
#:    nguong nay o mot loai nghia la ta MU o dung loai do, va moi con so bao dong
#:    gia do tren loai do chi noi "bo cham it noi", khong noi "bo cham dung".
NGUONG_BAT_LOI_TIEM = 0.50

#: So luot cham moi cap. ⛔ Khong ha xuong 1: cong ap `--temp 1.0`, `seed` khong
#: co hieu luc, nen mot luot don le khong phai mot phan quyet.
LUOT_MOI_CAP = 3

#: Hat giong cho phep chon cau + phep lam hong. Tai lap duoc.
HAT_GIONG = 20260924

# ── Cong NEN SACH: phai qua TRUOC khi duoc so hai loi nhac voi nhau ──────────
#
# 🔴 **22 % lo hong JSON khong phai mot khiem khuyet cua phep do — no lam phep
#    do KHONG TON TAI.** Mot lo hong mat tron 10 muc, tuc mat **ca mot cum**,
#    khong phai mot mau ngau nhien. Ti le tinh tren phan con lai khong noi ve
#    tong the nao ca.
#
# ⛔ Muc tran lay dung muc **V1** da do duoc (1/30 lo): ta khong duoc lam nen te
#    hon luc chua dung vao. ⛔ Khong noi hai con so nay de mot ban sua di qua.

#: Tran ti le LO tra JSON hong.
NGUONG_LO_HONG = 0.033

#: San do phu moi luot (so ma co phan quyet / so ma da gui).
NGUONG_DO_PHU = 28 / 30


# ══════════════════════════════════════════════════════════════════════════════
#  1. FLORES — tai, kiem sha256, doc
# ══════════════════════════════════════════════════════════════════════════════

def tai_flores(thu_muc: pathlib.Path = FLORES_DIR) -> dict:
    """Tai + kiem sha256 + giai nen DUNG hai tep ngon ngu ta can.

    ⛔ Kiem bam TRUOC khi giai nen. Mot tep tai ve khac ban ghim la mot bo do
       khac, va moi so do tren no khong so sanh duoc voi so da cong bo.
    """
    thu_muc.parent.mkdir(parents=True, exist_ok=True)
    tar = thu_muc.parent / "flores200_dataset.tar.gz"
    if not tar.exists():
        urllib.request.urlretrieve(FLORES_URL, tar)
    b = tar.read_bytes()
    bam = hashlib.sha256(b).hexdigest()
    if bam != FLORES_SHA256 or len(b) != FLORES_BYTE:
        raise SystemExit(
            f"FLORES tai ve KHONG khop ban ghim: {len(b)} B / {bam}\n"
            f"  cho doi: {FLORES_BYTE} B / {FLORES_SHA256}")
    can = ["./flores200_dataset/dev/zho_Hans.dev",
           "./flores200_dataset/dev/vie_Latn.dev"]
    with tarfile.open(tar, "r:gz") as f:
        for ten in can:
            # `filter="data"` — mac dinh cua Python 3.14, khai som de khong
            # phu thuoc vao mot mac dinh dang doi.
            f.extract(f.getmember(ten), path=thu_muc.parent, filter="data")
    return {"tar": str(tar), "sha256": bam, "byte": len(b),
            "thu_muc": str(thu_muc),
            "tep": [str(thu_muc / "dev" / t)
                    for t in ("zho_Hans.dev", "vie_Latn.dev")]}


def doc_flores(thu_muc: pathlib.Path = FLORES_DIR) -> list[tuple[int, str, str]]:
    """`[(chi_so_dong, cau_zh, cau_vi_NGUOI_DICH)]` — split `dev`, 997 dong.

    ⚠️ Hai tep **cung thu tu** (README cua FLORES noi vay), nen chi so dong la
       khoa ghep. Hai tep lech nhau mot dong se lam MOI cap sai, va moi phan
       quyet "dich sai" sau do la that — tuc phep do tu bien thanh mot phep do
       ve chinh no. Vi vay so dong lech => dung ngay.
    """
    zh = thu_muc / "dev" / "zho_Hans.dev"
    vi = thu_muc / "dev" / "vie_Latn.dev"
    if not zh.exists() or not vi.exists():
        raise SystemExit(f"chua co FLORES o {thu_muc} — chay `... tai` truoc")
    a = zh.read_text(encoding="utf-8").splitlines()
    b = vi.read_text(encoding="utf-8").splitlines()
    if len(a) != len(b):
        raise SystemExit(f"hai tep FLORES lech so dong: {len(a)} vs {len(b)}")
    return [(i, a[i].strip(), b[i].strip()) for i in range(len(a))
            if a[i].strip() and b[i].strip()]


# ══════════════════════════════════════════════════════════════════════════════
#  2. LAM HONG CO CHU Y — doi chung am
# ══════════════════════════════════════════════════════════════════════════════

#: Phep LAT NGHIA: `(tim, thay)` tren ban tieng Viet. ⛔ Chi nhung phep ma cau ra
#: van **troi chay** — mot cau tieng Viet gay se bi bat vi no GAY, khong phai vi
#: nghia bi lat, va ta se doc nham mot phep do ve NGU PHAP thanh mot phep do ve
#: NGHIA.
LAT_NGHIA: tuple[tuple[str, str], ...] = (
    ("tăng", "giảm"), ("giảm", "tăng"),
    ("nhiều hơn", "ít hơn"), ("ít hơn", "nhiều hơn"),
    ("lớn nhất", "nhỏ nhất"), ("nhỏ nhất", "lớn nhất"),
    ("thành công", "thất bại"), ("thất bại", "thành công"),
    ("đồng ý", "phản đối"), ("phản đối", "đồng ý"),
    ("có thể", "không thể"), ("không thể", "có thể"),
    ("sẽ không", "sẽ"), ("sẽ ", "sẽ không "),
    ("không phải là", "là"), (" là ", " không phải là "),
    ("không có", "có"), (" có ", " không có "),
    ("được phép", "bị cấm"), ("bị cấm", "được phép"),
    ("trước khi", "sau khi"), ("sau khi", "trước khi"),
)

#: Ten rieng thay the cho phep SAI THUC THE. ⛔ Phai la ten **co that va khac
#: han** — doi `Stanford` thanh `Stanfrod` la mot loi CHINH TA, khong phai mot
#: loi thuc the, va hai thu do bat bang hai nang luc khac nhau.
TEN_THAY_THE = ("Brazil", "Nga", "Ai Cập", "Canada", "Thổ Nhĩ Kỳ", "Indonesia")

_SO = re.compile(r"\d+")
#: Mot chu HOA KHONG dung dau cau (tuc mot ten rieng, khong phai chu dau cau).
_TEN = re.compile(r"(?<=[^.!?]\s)([A-ZĐÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĨŨƠƯ]\w{2,})")


def lam_hong_lat_nghia(cau_vi: str) -> str | None:
    """Lat nghia MOT cho. `None` khi khong ap duoc phep nao.

    ⭐ Tra `None` chu khong tra cau nguyen ven: mot cau "da lam hong" ma thuc ra
       khong doi gi se di vao cot *"bo cham khong bat duoc"* va keo ti le bat
       xuong — tuc ta se ket toi bo cham mot loi cua chinh bo do.
    """
    for tim, thay in LAT_NGHIA:
        if tim in cau_vi:
            return cau_vi.replace(tim, thay, 1)
    return None


def lam_hong_sai_thuc_the(cau_vi: str, rng: random.Random) -> str | None:
    """Doi MOT con so hoac MOT ten rieng. `None` khi cau khong co gi de doi."""
    m = _SO.search(cau_vi)
    if m:
        cu = m.group(0)
        moi = str(int(cu) + 7)
        if moi != cu:
            return cau_vi[:m.start()] + moi + cau_vi[m.end():]
    m = _TEN.search(cau_vi)
    if m:
        cu = m.group(1)
        khac = next((t for t in rng.sample(TEN_THAY_THE, len(TEN_THAY_THE))
                     if t != cu), None)
        if khac:
            return cau_vi[:m.start(1)] + khac + cau_vi[m.end(1):]
    return None


def dung_cap_tiem(cap: list[tuple[int, str, str]], *, moi_loai: int,
                  rng: random.Random) -> list[dict]:
    """`moi_loai` cap `lat_nghia` + `moi_loai` cap `sai_thuc_the`.

    ⛔ Hai loai TACH RIENG tu day cho toi bao cao. Gop lai thanh mot ti le "bat
       loi tiem" se giau mat truong hop nguy hiem nhat: bat gan het
       `sai_thuc_the` va bo gan het `lat_nghia` van cho ra mot con so tong
       trong rat dep.
    """
    ra: list[dict] = []
    cac_phep = (
        ("lat_nghia", lambda c: lam_hong_lat_nghia(c)),
        ("sai_thuc_the", lambda c: lam_hong_sai_thuc_the(c, rng)),
    )
    for loai, ham in cac_phep:
        n = 0
        for i, zh, vi in cap:
            if n >= moi_loai:
                break
            hong = ham(vi)
            if hong is None or hong == vi:
                continue
            ra.append({"ma": f"tiem_{loai}_{i:04d}", "dong_flores": i,
                       "loai": loai, "goc": zh, "chu": hong})
            n += 1
        if n < moi_loai:
            raise SystemExit(
                f"chi dung duoc {n}/{moi_loai} cap `{loai}` — noi rong bo cau")
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  3. Goi bo cham THAT
# ══════════════════════════════════════════════════════════════════════════════

def cham_mot_luot(db, muc: list[dict]) -> dict:
    """Cham `muc` MOT luot qua duong san pham. `{ma: {dat, do_tin, ly_do}}`.

    ⚠️ Lo nao hong / mo ho thi cac ma trong lo do **vang mat** khoi ket qua, ⛔
       khong duoc coi la `dat`. "Khong hoi duoc" khac han "da hoi va khong thay
       gi" — va chinh `doc_ngu_nghia` cung mac dinh `dat=True` cho ma thieu, nen
       tron hai thu o day se lam ti le bao dong gia **dep len** moi lan cong loi.
    """
    from apps.auto_scan_video import ai, qc_ai

    tran, cho = ai.ngan_sach_cho(ai.QC_NGU_NGHIA)
    ra: dict = {}
    loi: list[dict] = []
    for lo in qc_ai.chia_lo(muc):
        ma_lo = {str(d["ma"]) for d in lo}
        # ⚠️ `doc_ngu_nghia` can van ban de loc doan trich (⛔ loi khong trich
        #    duoc doan thi bi loai). Truyen dung cap da gui di, khong dung lai.
        van_ban = {str(d["ma"]): (str(d["goc"]), str(d["chu"])) for d in lo}
        t0 = time.monotonic()
        try:
            kq = ai.goi(db, ai.QC_NGU_NGHIA,
                        qc_ai.loi_nhac_ngu_nghia(lo, "vi"),
                        max_tokens=tran, timeout_s=cho,
                        # ⛔ Cung nhiet do voi duong san pham. Do o mot nhiet do
                        #    khac la do mot he thong khac.
                        temperature=qc_ai.NHIET_DO_NGU_NGHIA)
            for pq in qc_ai.doc_ngu_nghia(ai.doc_ket_qua(kq, ai.QC_NGU_NGHIA),
                                          ma_lo, van_ban):
                ra[pq["ma"]] = {"dat": bool(pq["dat"]),
                                "muc": pq["muc"],
                                "loi": pq["loi"],
                                "ly_do": pq["ly_do"]}
            xau = sum(1 for m in ma_lo if m in ra and not ra[m]["dat"])
            print(f"    lo {len(lo):>2} muc  {time.monotonic() - t0:>6.1f}s  "
                  f"model={kq.get('model', '-')}  khong_dat={xau}")
        except Exception as exc:                                 # noqa: BLE001
            loi.append({"ma_lo": sorted(ma_lo),
                        "loi": f"{type(exc).__name__}: {str(exc)[:200]}"})
            print(f"    lo {len(lo):>2} muc  {time.monotonic() - t0:>6.1f}s  "
                  f"LOI {type(exc).__name__}: {str(exc)[:120]}")
    return {"phan_quyet": ra, "loi_lo": loi}


# ══════════════════════════════════════════════════════════════════════════════
#  4. Gop nhieu luot — TRUNG VI, khong phai mot luot
# ══════════════════════════════════════════════════════════════════════════════

def gop_trung_vi(cac_luot: list[dict], ma: list[str]) -> dict:
    """`{ma: {dat, so_luot, so_bao_sai}}` — `dat` la DA SO tren cac luot tra loi.

    ⛔ Ma khong luot nao tra loi thi **khong co** trong ket qua. No khong phai
       `dat` va cung khong phai `khong dat`; no la mot cau hoi chua duoc tra loi,
       va mau so cua moi ti le phia sau phai la so cau DA duoc tra loi.
    """
    ra: dict = {}
    for m in ma:
        v = [bool(l["phan_quyet"][m]["dat"]) for l in cac_luot
             if m in l["phan_quyet"]]
        if not v:
            continue
        sai = sum(1 for x in v if not x)
        ra[m] = {"dat": sai * 2 < len(v), "so_luot": len(v), "so_bao_sai": sai}
    return ra


def _tung_luot(cac_luot: list[dict], ma: list[str]) -> list[float]:
    """Ti le "bi cham la dich sai" cua TUNG luot — de bao cao DAI."""
    ra = []
    for l in cac_luot:
        co = [m for m in ma if m in l["phan_quyet"]]
        if co:
            ra.append(round(sum(1 for m in co if not l["phan_quyet"][m]["dat"])
                            / len(co), 4))
    return ra


def thong_ke_luoc_do(cac_luot: list[dict], so_ma: int) -> dict:
    """NEN co sach khong: ti le lo hong + do phu tung luot.

    🔑 **Do nay phai dung truoc moi so sanh loi nhac.** Mat theo LO nghia la mat
       ca mot cum; mot ti le bao dong gia tinh tren phan con lai khong noi ve
       tong the nao ca. ⛔ Nen khong dat cong nay thi con so ben canh no **khong
       duoc doc**, du no dep den may.
    """
    so_lo = sum(len(l["loi_lo"]) for l in cac_luot)
    # Moi luot chia `so_ma` thanh cac lo `DOAN_MOI_LO`; lo hong nam trong
    # `loi_lo`, lo chay duoc thi khong de lai dau — nen tong so lo tinh ra.
    from apps.auto_scan_video import qc_ai
    lo_moi_luot = -(-so_ma // qc_ai.DOAN_MOI_LO)
    tong_lo = lo_moi_luot * len(cac_luot)
    do_phu = [round(len(l["phan_quyet"]) / so_ma, 4) for l in cac_luot]
    ti_le = round(so_lo / tong_lo, 4) if tong_lo else None
    return {
        "tong_lo": tong_lo, "so_lo_hong": so_lo, "ti_le_lo_hong": ti_le,
        "do_phu_tung_luot": do_phu,
        "do_phu_thap_nhat": min(do_phu) if do_phu else None,
        "nguong_lo_hong": NGUONG_LO_HONG, "nguong_do_phu": round(NGUONG_DO_PHU, 4),
        "nen_sach": bool(ti_le is not None and ti_le <= NGUONG_LO_HONG
                         and do_phu and min(do_phu) >= NGUONG_DO_PHU),
    }


def _ti_le(cac_luot: list[dict], ma: list[str], gop: dict) -> dict:
    tung = _tung_luot(cac_luot, ma)
    n = len(gop)
    sai = sum(1 for m in gop if not gop[m]["dat"])
    return {
        "n_hoi": len(ma), "n_co_phan_quyet": n, "so_bi_cham_sai": sai,
        "ti_le_trung_vi": round(sai / n, 4) if n else None,
        "ti_le_tung_luot": tung,
        "dai": [min(tung), max(tung)] if tung else None,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  5. Giao dien cua Task 10
# ══════════════════════════════════════════════════════════════════════════════

def ti_le_bao_dong_gia(n: int, *, db=None, luot: int = LUOT_MOI_CAP,
                       tu: int = 0,
                       thu_muc: pathlib.Path = FLORES_DIR) -> dict:
    """Ti le bao dong gia cua bo cham tren `n` cap FLORES zh->vi.

    🔑 Moi phan quyet *"dich sai"* o day la mot **bao dong gia theo dinh nghia**:
       ban dich la cua NGUOI, trong mot bo chuan dich chuyen nghiep.

    ⭐ `tu` cho phep chay LAM DOI tren hai tien trinh (moi tien trinh mot nua
       dai cau) roi `gop` lai — tran dong thoi cua CLAUDE.md la 2 request moi
       model, va mot luot tuan tu mat ~1 gio. `ma` mang chi so dong FLORES nen
       hai nua khong the trung ma.
    """
    cap = doc_flores(thu_muc)[tu:tu + n]
    muc = [{"ma": f"flores_{i:04d}", "goc": zh, "chu": vi} for i, zh, vi in cap]
    ma = [m["ma"] for m in muc]
    cac_luot = []
    for k in range(luot):
        print(f"  [FLORES] luot {k + 1}/{luot} — {len(muc)} cap NGUOI DICH"
              f" (dong {tu}..{tu + len(muc) - 1})")
        cac_luot.append(cham_mot_luot(db, muc))
    gop = gop_trung_vi(cac_luot, ma)
    return {"n": len(muc), "luot": luot, "tu": tu, "gop": gop,
            "luoc_do": thong_ke_luoc_do(cac_luot, len(muc)),
            "cac_luot": cac_luot, **_ti_le(cac_luot, ma, gop)}


def gop_phan(cac_phan: list[dict]) -> dict:
    """Gop nhieu ban ghi `bao_dong_gia` tung phan thanh MOT, roi tinh lai ti le.

    ⛔ Ghep theo TUNG LUOT (`cac_luot[k]`), khong doi mot phan thanh mot luot
       rieng: moi cau van phai co dung `luot` phan quyet doc lap, neu khong
       "trung vi tren 3 luot" se tro thanh "mot luot" cho mot nua so cau.

    ⛔ Hai phan trung ma la mot loi, khong phai mot chuyen vat: no nghia la hai
       tien trinh da hoi cung mot cau va ta dang dem no hai lan.
    """
    if not cac_phan:
        raise SystemExit("khong co phan nao de gop")
    luot = {p["luot"] for p in cac_phan}
    if len(luot) != 1:
        raise SystemExit(f"cac phan khac so luot: {sorted(luot)}")
    ma: list[str] = []
    for p in cac_phan:
        trung = set(ma) & {m for l in p["cac_luot"] for m in l["phan_quyet"]}
        if trung:
            raise SystemExit(f"hai phan trung ma: {sorted(trung)[:5]}")
        ma += [f"flores_{i:04d}"
               for i in range(p["tu"], p["tu"] + p["n"])]
    cac_luot = []
    for k in range(next(iter(luot))):
        pq: dict = {}
        loi: list[dict] = []
        for p in cac_phan:
            pq.update(p["cac_luot"][k]["phan_quyet"])
            loi += p["cac_luot"][k]["loi_lo"]
        cac_luot.append({"phan_quyet": pq, "loi_lo": loi})
    gop = gop_trung_vi(cac_luot, ma)
    return {"n": len(ma), "luot": next(iter(luot)),
            "tu_cac_phan": [p["tu"] for p in cac_phan], "gop": gop,
            "cac_luot": cac_luot, **_ti_le(cac_luot, ma, gop)}


def ti_le_bat_loi_tiem(*, db, moi_loai: int, bo_qua: int,
                       luot: int = LUOT_MOI_CAP,
                       thu_muc: pathlib.Path = FLORES_DIR) -> dict:
    """Doi chung AM: bo cham co bat duoc cac cap DA LAM HONG khong.

    ⚠️ `bo_qua` cac dong da dung cho phep do bao dong gia — ⛔ khong tiem len
       chinh nhung cau da hoi o tren. Hoi lai mot cau da hoi la moi mot lop
       "model da thay cau nay" vao giua phep do, va ta khong tach no ra duoc.
    """
    rng = random.Random(HAT_GIONG)
    muc = dung_cap_tiem(doc_flores(thu_muc)[bo_qua:], moi_loai=moi_loai, rng=rng)
    ma = [m["ma"] for m in muc]
    cac_luot = []
    for k in range(luot):
        print(f"  [TIEM] luot {k + 1}/{luot} — {len(muc)} cap DA LAM HONG")
        cac_luot.append(cham_mot_luot(db, muc))
    gop = gop_trung_vi(cac_luot, ma)
    theo_loai: dict = {}
    for loai in ("lat_nghia", "sai_thuc_the"):
        ml = [m["ma"] for m in muc if m["loai"] == loai]
        co = [m for m in ml if m in gop]
        bat = sum(1 for m in co if not gop[m]["dat"])
        # 🔴 KHONG dao dau o day. `_tung_luot` dem ti le `khong dat`, va tren
        #    mot cap DA LAM HONG thi `khong dat` chinh la **BAT DUOC**. Mot phep
        #    `1 - x` lac cho se in "bat 100 %" cho mot bo cham bat 0/15 — tuc
        #    dao nguoi mu thanh nguoi tinh (`test_3600::..._CHIEU_DUNG`).
        tung = _tung_luot(cac_luot, ml)
        theo_loai[loai] = {
            "n_hoi": len(ml), "n_co_phan_quyet": len(co), "so_bat_duoc": bat,
            "ti_le_trung_vi": round(bat / len(co), 4) if co else None,
            "ti_le_tung_luot": tung,
            "dai": [min(tung), max(tung)] if tung else None,
            "dat_nguong_mach": (bat / len(co) >= NGUONG_BAT_LOI_TIEM)
                               if co else None,
        }
    return {"n": len(muc), "luot": luot, "moi_loai": moi_loai,
            "theo_loai": theo_loai, "gop": gop, "cac_luot": cac_luot,
            "dong_flores_da_dung": [m["dong_flores"] for m in muc]}


# ══════════════════════════════════════════════════════════════════════════════
#  6. Bao cao
# ══════════════════════════════════════════════════════════════════════════════

#: Nhung khoa co the mang chu cua FLORES (hoac cua mot tac pham phai sinh).
#: ⛔ Khong khoa nao trong so nay duoc vao tep bang chung commit len kho.
KHOA_CO_CHU = ("cac_luot", "ly_do", "goc", "chu", "nguon", "dich")


def ban_ghi_sach(d: dict) -> dict:
    """Ban ghi DU DE TAI LAP ma khong mang mot chu nao cua FLORES.

    🔴 **Day la mot rao co hoc, khong phai mot y dinh tot.** FLORES la
       CC-BY-SA-4.0 (ShareAlike), va `ly_do` cua model **trich thang** doan nguon
       lan ban dich vao trong no. Mot tep bang chung "day du" se la mot ban phan
       phoi lai FLORES nam trong mot kho khong theo giay phep do.

    ⭐ Cai con lai van tra loi duoc moi cau hoi cua Task 10: chi so dong FLORES
       (tai lap bang `tai` + `HAT_GIONG`), phan quyet tung cau, va ti le.
    """
    def loc(o):
        if isinstance(o, dict):
            return {k: loc(v) for k, v in o.items() if k not in KHOA_CO_CHU}
        if isinstance(o, list):
            return [loc(v) for v in o]
        return o

    sach = loc(d)
    con = [k for k in KHOA_CO_CHU
           if f'"{k}"' in json.dumps(sach, ensure_ascii=False)]
    if con:
        raise SystemExit(f"ban ghi van con khoa mang chu: {con}")
    return sach


def bao_cao(d: dict) -> str:
    fa = d.get("bao_dong_gia") or {}
    tiem = d.get("bat_loi_tiem") or {}
    dong = ["| Phep do | Co mau | Ti le (trung vi) | Dai tung luot | Luot/cap |",
            "|---|---|---|---|---|",
            f"| Bao dong gia (FLORES, NGUOI dich) "
            f"| {fa.get('n_co_phan_quyet')}/{fa.get('n_hoi')} "
            f"| **{fa.get('ti_le_trung_vi')}** | {fa.get('dai')} "
            f"| {fa.get('luot')} |"]
    for loai, k in (tiem.get("theo_loai") or {}).items():
        dong.append(f"| Bat loi tiem — `{loai}` "
                    f"| {k.get('n_co_phan_quyet')}/{k.get('n_hoi')} "
                    f"| **{k.get('ti_le_trung_vi')}** | {k.get('dai')} "
                    f"| {tiem.get('luot')} |")
    t = fa.get("ti_le_trung_vi")
    dong.append("")
    if t is None:
        dong.append("PHAN QUYET: **khong do duoc**.")
    elif t <= NGUONG_BAO_DONG_GIA:
        dong.append(f"PHAN QUYET: bao dong gia {t:.1%} <= nguong "
                    f"{NGUONG_BAO_DONG_GIA:.0%} => bo cham DANG TIN.")
    else:
        dong.append(f"PHAN QUYET: bao dong gia {t:.1%} > nguong "
                    f"{NGUONG_BAO_DONG_GIA:.0%} => **44/95 KHONG dung duoc de "
                    f"ket luan ve ban dich**; viec tiep theo la sua BO CHAM.")
    for loai, k in (tiem.get("theo_loai") or {}).items():
        if k.get("dat_nguong_mach") is False:
            dong.append(f"CANH BAO — MU o `{loai}`: bat "
                        f"{k.get('ti_le_trung_vi'):.1%} < "
                        f"{NGUONG_BAT_LOI_TIEM:.0%}.")
    return "\n".join(dong)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Xac thuc bo cham ngu nghia ASV")
    s = p.add_subparsers(dest="lenh", required=True)
    s.add_parser("tai")
    d = s.add_parser("do")
    d.add_argument("--n", type=int, default=N_TOI_THIEU)
    d.add_argument("--tu", type=int, default=0,
                   help="dong FLORES bat dau (de chay lam doi roi `gop`)")
    d.add_argument("--pha", choices=("ca", "fa", "tiem"), default="ca")
    d.add_argument("--tiem-moi-loai", type=int, default=15)
    d.add_argument("--tiem-bo-qua", type=int, default=N_TOI_THIEU)
    d.add_argument("--luot", type=int, default=LUOT_MOI_CAP)
    d.add_argument("--ra", required=True)
    g = s.add_parser("gop")
    g.add_argument("--fa", nargs="+", required=True,
                   help="cac ban ghi `fa` tung phan, ghep lai")
    g.add_argument("--tiem", required=True)
    g.add_argument("--ra", required=True)
    b = s.add_parser("bao-cao")
    b.add_argument("tep")
    bg = s.add_parser("bang-chung")
    bg.add_argument("tep")
    bg.add_argument("--ra", required=True)
    a = p.parse_args(argv)

    if a.lenh == "tai":
        print(json.dumps(tai_flores(), ensure_ascii=False, indent=2))
        return 0
    if a.lenh == "bao-cao":
        print(bao_cao(json.loads(
            pathlib.Path(a.tep).read_text(encoding="utf-8"))))
        return 0
    if a.lenh == "bang-chung":
        sach = ban_ghi_sach(json.loads(
            pathlib.Path(a.tep).read_text(encoding="utf-8")))
        pathlib.Path(a.ra).write_text(
            json.dumps(sach, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"da ghi ban ghi SACH (khong mang chu FLORES): {a.ra}")
        return 0
    if a.lenh == "gop":
        _doc = (lambda t: json.loads(
            pathlib.Path(t).read_text(encoding="utf-8")))
        fa = gop_phan([_doc(t)["bao_dong_gia"] for t in a.fa])
        if fa["n"] < N_TOI_THIEU:
            raise SystemExit(
                f"gop lai chi duoc {fa['n']} cap < {N_TOI_THIEU} — "
                "khong du de ra mot phan quyet")
        ra = {"phien_ban": 1, "hat_giong": HAT_GIONG,
              "nguong_bao_dong_gia": NGUONG_BAO_DONG_GIA,
              "nguong_bat_loi_tiem": NGUONG_BAT_LOI_TIEM,
              "bao_dong_gia": fa,
              "bat_loi_tiem": _doc(a.tiem)["bat_loi_tiem"]}
        pathlib.Path(a.ra).write_text(
            json.dumps(ra, ensure_ascii=False, indent=1), encoding="utf-8")
        print(bao_cao(ra))
        return 0

    from tools import do_llm_cong_asv as mt
    mt._nap_app_env()
    db, so_khoa = mt._mo_db()
    print(f"[MOI TRUONG] {so_khoa} khoa pool")
    t0 = time.monotonic()
    khoi_fa: dict | None = None
    tiem: dict | None = None
    if a.pha in ("ca", "fa"):
        khoi_fa = ti_le_bao_dong_gia(a.n, db=db, luot=a.luot, tu=a.tu)
    if a.pha in ("ca", "tiem"):
        tiem = ti_le_bat_loi_tiem(db=db, moi_loai=a.tiem_moi_loai,
                                  luot=a.luot, bo_qua=a.tiem_bo_qua)
    ra = {
        "phien_ban": 1, "hat_giong": HAT_GIONG,
        "nguong_bao_dong_gia": NGUONG_BAO_DONG_GIA,
        "nguong_bat_loi_tiem": NGUONG_BAT_LOI_TIEM,
        "giay": round(time.monotonic() - t0, 1),
        "bao_dong_gia": khoi_fa, "bat_loi_tiem": tiem,
    }
    pathlib.Path(a.ra).write_text(
        json.dumps(ra, ensure_ascii=False, indent=1), encoding="utf-8")
    # ⛔ Mot PHAN khong duoc in ra mot phan quyet: co mau cua no nho hon
    #    `N_TOI_THIEU`, va mot phan quyet in ra la mot phan quyet se bi trich.
    if a.pha == "ca" and a.n >= N_TOI_THIEU:
        print("\n" + bao_cao(ra))
    else:
        print(f"\n[PHAN] da ghi {a.ra} — chay `gop` roi moi co phan quyet")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
