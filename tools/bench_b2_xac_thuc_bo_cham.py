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
import datetime
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


#: Dau ranh CUM trong mot cau tieng Viet — dung de bo MOT cum.
_RANH_CUM = re.compile(r"\s*[,;:—–]\s*")

#: So am tiet toi thieu cua cum bi bo, va cua phan con lai.
_CUM_TOI_THIEU = 4
_CON_LAI_TOI_THIEU = 5


def lam_hong_bo_sot(cau_vi: str, rng: random.Random) -> str | None:
    """Bo MOT cum — ho loi `bo_sot`. `None` khi cau khong co cum nao bo duoc.

    ⭐ **Dac ta muon tu DEMETR** (`marzenakrp/demetr`, **MIT**, arXiv
       2210.13746): ho `accuracy/omission` gom `major_id5_pp_removed`,
       `critical_id21_adj_adv_removed`, `id22_verb_removed`, `id23_noun_removed`,
       `id24_subj_removed`. ⛔ Ta **khong** dung DU LIEU cua ho: DEMETR chi dich
       **sang tieng Anh**, ma ta la zh→vi — do tren do la do mot he KHAC.

    ⚠️ **Khai dung cai gia:** ta ⛔ khong co bo gan nhan tu loai tieng Viet, nen
       ⛔ khong bo duoc **dung** mot dong tu / chu ngu nhu ho. Ta bo mot **cum
       ngan cach bang dau phay** — tuc mot phep **xap xi** cua ho `omission`.
       ⇒ Phep tiem nay la cua ta, ⛔ **chua duoc ai cong bo kiem chung**; doi lai
       no do **dung he cua minh**.

    ⛔ Bo cum DAU cau se de thanh mot cau cut ro rang (bat bang hinh dang, khong
       phai bang nghia), nen chi bo cum o GIUA hoac CUOI.
    """
    cum = [c for c in _RANH_CUM.split(cau_vi.strip()) if c.strip()]
    if len(cum) < 2:
        return None
    ung = [k for k in range(1, len(cum))
           if len(cum[k].split()) >= _CUM_TOI_THIEU]
    if not ung:
        return None
    k = rng.choice(ung)
    con = cum[:k] + cum[k + 1:]
    if sum(len(c.split()) for c in con) < _CON_LAI_TOI_THIEU:
        return None
    ra = ", ".join(c.strip().rstrip(",;:—–") for c in con).strip()
    if not ra.endswith((".", "!", "?")):
        ra += "."
    return ra if ra != cau_vi else None


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


#: Cac ho loi ta tiem duoc. ⚠️ Taxonomy da cong bo (DEMETR) co **35** ho —
#: xem canh bao dau `B2_XAC_THUC_BO_CHAM.md` va §22.1.
LOAI_TIEM = ("lat_nghia", "sai_thuc_the", "bo_sot")


def dung_cap_tiem(cap: list[tuple[int, str, str]], *, moi_loai: int,
                  rng: random.Random,
                  loai_can: tuple[str, ...] = LOAI_TIEM) -> list[dict]:
    """`moi_loai` cap `lat_nghia` + `moi_loai` cap `sai_thuc_the`.

    ⛔ Hai loai TACH RIENG tu day cho toi bao cao. Gop lai thanh mot ti le "bat
       loi tiem" se giau mat truong hop nguy hiem nhat: bat gan het
       `sai_thuc_the` va bo gan het `lat_nghia` van cho ra mot con so tong
       trong rat dep.
    """
    ra: list[dict] = []
    cac_phep = [(l, h) for l, h in (
        ("lat_nghia", lambda c: lam_hong_lat_nghia(c)),
        ("sai_thuc_the", lambda c: lam_hong_sai_thuc_the(c, rng)),
        ("bo_sot", lambda c: lam_hong_bo_sot(c, rng)),
    ) if l in loai_can]
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

# ══════════════════════════════════════════════════════════════════════════════
#  3b. LOI NHAC DONG BANG — de so V1/V2/V3 tren CUNG mot nen
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔴 **Vi sao ban cu song o `tools/` chu khong o `apps/`.** San pham chi duoc co
#    MOT loi nhac; giu ba ban trong `qc_ai.py` la de hai ban chet nam giua duong
#    chay that. Nhung khong giu thi ta dang so **mot ban do sach voi hai ban do
#    ban** — V1 va V2 deu do o nhiet do mac dinh, va ghim nhiet do da chung minh
#    la no doi ket qua (lo hong 22,2 % -> 0 %).
#
# ⛔ Day la **ban sao dong bang**, chep nguyen van tu lich su git
#    (V1 = truoc `91d921f4`, V2 = `91d921f4`). ⛔ Dung "cap nhat" chung cho khop
#    ban moi — sua mot ban dong bang la xoa chinh cai moc dung de so.

def _loi_nhac_v1(lo: list[dict], ngon_ngu_dich: str = "vi") -> list[dict]:
    """Loi nhac NHI PHAN — ban goc, truoc 24/09. Chep nguyen van tu git."""
    import json as _json

    from apps.auto_scan_video import ngon_ngu
    t = ngon_ngu.cum(ngon_ngu_dich)["tieng"]
    he_thong = (
        f"Ban la nguoi soat ban long tieng {t}. Voi moi cap (cau goc, cau "
        f"{t}), hay noi ban {t} co **giu dung y va thai do** cua cau "
        "goc khong.\n"
        "Quy tac:\n"
        "- `dat=false` CHI khi y nghia bi doi, mat, hoac them.\n"
        "- Cach dien dat khac, dao trat tu, hay rut gon ma giu y => `dat=true`.\n"
        "- `do_tin` la do chac chan cua CHINH BAN, tu 0 den 1.\n"
        "- `ly_do` chi bat buoc khi `dat=false`, va phai noi ro y nao bi lech.\n"
        'Tra ve DUY NHAT: {"doan": {"<ma>": {"dat": true, "do_tin": 0.9, '
        '"ly_do": ""}}}')
    nguoi_dung = _json.dumps({"doan": [
        {"ma": str(d.get("ma") or ""),
         "goc": str(d.get("goc") or "")[:600],
         "tieng_viet": str(d.get("chu") or "")[:600]}
        for d in lo]}, ensure_ascii=False, sort_keys=True)
    return [{"role": "system", "content": he_thong},
            {"role": "user", "content": nguoi_dung}]


def _doc_v1(goi: dict, ma_da_gui: set[str], van_ban) -> list[dict]:
    """Ban doc cua V1: model tu phan `dat`, khong co muc, khong loc doan."""
    from apps.auto_scan_video import qc_ai

    tho = (goi or {}).get("doan")
    if not isinstance(tho, dict):
        raise qc_ai.QcAiError("Model khong tra ve bang phan doan.")
    ra = []
    for ma in sorted(ma_da_gui):
        v = tho.get(ma)
        if isinstance(v, dict):
            ra.append({"ma": ma, "dat": bool(v.get("dat", True)),
                       "muc": "", "loi": [],
                       "ly_do": str(v.get("ly_do") or "")[:300]})
    return ra


def _loi_nhac_v2(lo: list[dict], ngon_ngu_dich: str = "vi") -> list[dict]:
    """Phan muc MQM, CHUA co san muc cho sai thuc the. Chep tu `91d921f4`."""
    import json as _json

    from apps.auto_scan_video import ngon_ngu, qc_ai
    t = ngon_ngu.cum(ngon_ngu_dich)["tieng"]
    he_thong = (
        f"Ban soat ban long tieng {t}. Voi moi cap (cau goc, cau {t}), hay "
        "LIET KE cac loi dich, moi loi mot muc nghiem trong.\n"
        "Ba muc, theo HAU QUA cho nguoi xem clip:\n"
        "- `nghiem_trong`: nguoi xem hieu SAI su viec.\n"
        "- `nang`: pha mach, nhung van hieu duoc dieu cau muon noi.\n"
        "- `nhe`: la loi that, nhung KHONG can tro hieu (sac thai, mot bo ngu "
        "phu, cach dien dat).\n"
        f"Loai loi: {', '.join(qc_ai.LOAI_LOI)}.\n"
        "Quy tac:\n"
        "- `doan` BAT BUOC: trich NGUYEN VAN doan bi loi, lay tu cau goc hoac "
        f"cau {t}. Loi khong trich duoc doan se bi bo.\n"
        "- Cach dien dat khac, dao trat tu, rut gon ma giu y: KHONG phai loi.\n"
        "- Khong tim thay loi nao thi tra danh sach rong.\n"
        'Tra ve DUY NHAT: {"doan": {"<ma>": {"loi": [{"loai": "lat_nghia", '
        '"muc": "nang", "doan": "...", "ly_do": "..."}]}}}')
    nguoi_dung = _json.dumps({"doan": [
        {"ma": str(d.get("ma") or ""),
         "goc": str(d.get("goc") or "")[:600],
         "tieng_viet": str(d.get("chu") or "")[:600]}
        for d in lo]}, ensure_ascii=False, sort_keys=True)
    return [{"role": "system", "content": he_thong},
            {"role": "user", "content": nguoi_dung}]


def _hien_hanh(lo, ngon_ngu_dich="vi"):
    from apps.auto_scan_video import qc_ai
    return qc_ai.loi_nhac_ngu_nghia(lo, ngon_ngu_dich)


def _doc_hien_hanh(goi, ma_da_gui, van_ban):
    from apps.auto_scan_video import qc_ai
    return qc_ai.doc_ngu_nghia(goi, ma_da_gui, van_ban)


#: `{ten: (dung_loi_nhac, doc_phan_hoi)}`. `v3` = ban HIEN HANH cua san pham.
BAN_LOI_NHAC = {
    "v1": (_loi_nhac_v1, _doc_v1),
    "v2": (_loi_nhac_v2, _doc_hien_hanh),
    "v3": (_hien_hanh, _doc_hien_hanh),
}


def cham_mot_luot(db, muc: list[dict], ban: str = "v3") -> dict:
    """Cham `muc` MOT luot qua duong san pham. `{ma: {dat, do_tin, ly_do}}`.

    ⚠️ Lo nao hong / mo ho thi cac ma trong lo do **vang mat** khoi ket qua, ⛔
       khong duoc coi la `dat`. "Khong hoi duoc" khac han "da hoi va khong thay
       gi" — va chinh `doc_ngu_nghia` cung mac dinh `dat=True` cho ma thieu, nen
       tron hai thu o day se lam ti le bao dong gia **dep len** moi lan cong loi.
    """
    from apps.auto_scan_video import ai, qc_ai

    dung_loi_nhac, doc_phan_hoi = BAN_LOI_NHAC[ban]
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
            kq = ai.goi(db, ai.QC_NGU_NGHIA, dung_loi_nhac(lo, "vi"),
                        max_tokens=tran, timeout_s=cho,
                        # ⛔ Cung nhiet do voi duong san pham, va cung nhiet do
                        #    cho CA BA ban — do o hai nhiet do la so hai he
                        #    thong, khong phai so hai loi nhac.
                        temperature=qc_ai.NHIET_DO_NGU_NGHIA)
            for pq in doc_phan_hoi(ai.doc_ket_qua(kq, ai.QC_NGU_NGHIA),
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

def _mat_lo(luot: dict) -> set[str]:
    """Cac ma nam trong mot lo HONG cua luot nay — tuc **chua duoc hoi xong**."""
    return {m for e in luot.get("loi_lo") or [] for m in e.get("ma_lo") or []}


def gop_trung_vi(cac_luot: list[dict], ma: list[str]) -> dict:
    """`{ma: {dat, so_luot, so_bao_sai}}` — `dat` la DA SO tren cac luot tra loi.

    🔴 **HAI cach mot ma vang mat, va chung KHONG cung nghia** (do 24/09):

        lo HONG (`LuocDoSai`)   -> chua duoc hoi xong  => khong dem
        lo CHAY DUOC, model     -> model khong tim thay loi nao => **DAT**
        khong nhac toi ma do

    ⛔ Ban dau ham nay gop ca hai thanh "khong co trong ket qua", va do la mot
       loi that: do 24/09 cho thay model **chi liet ke nhung muc no thay co
       loi** — lo 200-209 tra ve **0/10** ma kem `khong_dat=0`, lo 220-229 tra
       ve 10/10. Coi 10 muc SACH do la "chua tra loi" lam mau so tut tu 30
       xuong 16, va ti le bao dong gia **nhay tu 23 % len 44 %** ma khong mot
       phan quyet nao doi.

    ⭐ Va day dung la bay *"hai trang thai gop thanh mot gia tri"* cua chinh kho
       nay — `doc_ngu_nghia` von ghi ro rang ma thieu la **DAT**. Phep do phai
       dem theo cung hop dong voi san pham, neu khong no do mot he thong khac.
    """
    ra: dict = {}
    for m in ma:
        v = []
        for l in cac_luot:
            if m in l["phan_quyet"]:
                v.append(bool(l["phan_quyet"][m]["dat"]))
            elif m not in _mat_lo(l):
                # Lo chay duoc ma model khong nhac toi ma nay => khong thay loi.
                v.append(True)
        if not v:
            continue
        sai = sum(1 for x in v if not x)
        ra[m] = {"dat": sai * 2 < len(v), "so_luot": len(v), "so_bao_sai": sai}
    return ra


def _tung_luot(cac_luot: list[dict], ma: list[str]) -> list[float]:
    """Ti le "bi cham la dich sai" cua TUNG luot — de bao cao DAI.

    ⛔ Mau so la cac ma DA DUOC HOI XONG trong luot do (tuc khong nam trong mot
       lo hong), ke ca ma model khong nhac toi — xem `gop_trung_vi`.
    """
    ra = []
    for l in cac_luot:
        mat = _mat_lo(l)
        co = [m for m in ma if m not in mat]
        if co:
            ra.append(round(
                sum(1 for m in co
                    if m in l["phan_quyet"] and not l["phan_quyet"][m]["dat"])
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
    # ⛔ Do phu = ma DA DUOC HOI XONG, khong phai ma model co nhac toi. Model
    #    chi liet ke muc no thay co loi (do 24/09), nen dem theo `phan_quyet` se
    #    doc mot lo SACH thanh mot lo MAT.
    do_phu = [round((so_ma - len(_mat_lo(l))) / so_ma, 4) for l in cac_luot]
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

def _bay_gio() -> str:
    """Moc gio UTC, dang ISO — ⛔ khong dung gio may (may nay UTC+7)."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="seconds")


def ti_le_bao_dong_gia(n: int, *, db=None, luot: int = LUOT_MOI_CAP,
                       tu: int = 0, ban: str = "v3",
                       dong: list[int] | None = None,
                       thu_muc: pathlib.Path = FLORES_DIR) -> dict:
    """Ti le bao dong gia cua bo cham tren `n` cap FLORES zh->vi.

    🔑 Moi phan quyet *"dich sai"* o day la mot **bao dong gia theo dinh nghia**:
       ban dich la cua NGUOI, trong mot bo chuan dich chuyen nghiep.

    ⭐ `tu` cho phep chay LAM DOI tren hai tien trinh (moi tien trinh mot nua
       dai cau) roi `gop` lai — tran dong thoi cua CLAUDE.md la 2 request moi
       model, va mot luot tuan tu mat ~1 gio. `ma` mang chi so dong FLORES nen
       hai nua khong the trung ma.
    """
    if dong is not None:
        # ⭐ Cham DUNG nhung dong da duoc soi MU (va phan quyet cua nguoi soi da
        #    COMMIT truoc do). Cho phep mot danh sach roi rac, vi mau ngau nhien
        #    khong lien tuc — ⛔ khong duoc "lam tron" thanh mot dai lien tuc,
        #    lam vay la doi tap do.
        can = set(int(x) for x in dong)
        cap = [c for c in doc_flores(thu_muc) if c[0] in can]
        if len(cap) != len(can):
            raise SystemExit(
                f"chi tim duoc {len(cap)}/{len(can)} dong trong FLORES")
    else:
        cap = doc_flores(thu_muc)[tu:tu + n]
    muc = [{"ma": f"flores_{i:04d}", "goc": zh, "chu": vi} for i, zh, vi in cap]
    ma = [m["ma"] for m in muc]
    bat_dau = _bay_gio()
    cac_luot = []
    for k in range(luot):
        print(f"  [FLORES] {ban} luot {k + 1}/{luot} — {len(muc)} cap NGUOI"
              f" DICH (dong {tu}..{tu + len(muc) - 1})")
        cac_luot.append(cham_mot_luot(db, muc, ban))
    gop = gop_trung_vi(cac_luot, ma)
    # 🔴 **Moc gio la mot phan cua phep do, khong phai trang tri.** Mot luot
    #    vat qua mot su co (deploy, restart, mat dien) cho ra mau so THIEU ma
    #    ⛔ khong bao loi — no chi ra mot ti le KHAC, ⛔ khong phan biet duoc tu
    #    ben ngoai. Khong ghi cua so nay thi khong ai kiem lai duoc.
    return {"n": len(muc), "luot": luot, "tu": tu, "ban": ban, "gop": gop,
            "cua_so_utc": [bat_dau, _bay_gio()],
            "dong": [i for i, _z, _v in cap],
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
        # ⛔ Phan chay voi `--theo-so` cham mot danh sach dong ROI RAC — cap
        #    `tu`/`n` khong ta duoc no (no se sinh ra ma cua nhung dong KHONG
        #    he duoc hoi, roi dem chung nhu "thieu"). Dung `dong` da luu trong
        #    chinh ban ghi khi co.
        ds = p.get("dong")
        if ds is None:
            ds = list(range(p["tu"], p["tu"] + p["n"]))
        ma += [f"flores_{i:04d}" for i in ds]
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
            # ⛔ Giu cua so cua TUNG phan, ⛔ khong gop thanh mot khoang lien
            #    tuc: cac phan chay roi rac, mot khoang gop se nuot cho ho o
            #    giua — dung cho su co co the da xay ra.
            "cua_so_utc_cac_phan": [p.get("cua_so_utc") for p in cac_phan],
            "dong": [int(m.split("_")[1]) for m in ma],
            "cac_luot": cac_luot, **_ti_le(cac_luot, ma, gop)}


def ti_le_bat_loi_tiem(*, db, moi_loai: int, bo_qua: int,
                       luot: int = LUOT_MOI_CAP, ban: str = "v3",
                       loai_can: tuple[str, ...] = LOAI_TIEM,
                       thu_muc: pathlib.Path = FLORES_DIR) -> dict:
    """Doi chung AM: bo cham co bat duoc cac cap DA LAM HONG khong.

    ⚠️ `bo_qua` cac dong da dung cho phep do bao dong gia — ⛔ khong tiem len
       chinh nhung cau da hoi o tren. Hoi lai mot cau da hoi la moi mot lop
       "model da thay cau nay" vao giua phep do, va ta khong tach no ra duoc.
    """
    rng = random.Random(HAT_GIONG)
    muc = dung_cap_tiem(doc_flores(thu_muc)[bo_qua:], moi_loai=moi_loai,
                        rng=rng, loai_can=loai_can)
    ma = [m["ma"] for m in muc]
    bat_dau = _bay_gio()
    cac_luot = []
    for k in range(luot):
        print(f"  [TIEM] {ban} luot {k + 1}/{luot} — {len(muc)} cap DA LAM"
              " HONG")
        cac_luot.append(cham_mot_luot(db, muc, ban))
    gop = gop_trung_vi(cac_luot, ma)
    cua_so = [bat_dau, _bay_gio()]
    theo_loai: dict = {}
    for loai in sorted({m["loai"] for m in muc}):
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
    return {"n": len(muc), "luot": luot, "moi_loai": moi_loai, "ban": ban,
            "theo_loai": theo_loai, "gop": gop, "cac_luot": cac_luot,
            "cua_so_utc": cua_so,
            "dong_flores_da_dung": [m["dong_flores"] for m in muc]}


# ══════════════════════════════════════════════════════════════════════════════
#  6. Bao cao
# ══════════════════════════════════════════════════════════════════════════════

#: Nhung khoa co the mang chu cua FLORES (hoac cua mot tac pham phai sinh).
#: ⛔ Khong khoa nao trong so nay duoc vao tep bang chung commit len kho.
KHOA_CO_CHU = ("cac_luot", "ly_do", "goc", "chu", "nguon", "dich")


# ══════════════════════════════════════════════════════════════════════════════
#  5b. SENTINEL — bo cham dang cham NOI DUNG hay cham bang THIEN LECH BE MAT?
# ══════════════════════════════════════════════════════════════════════════════

#: Canh sentinel: ben nao bi GIAU di.
#:
#: ⭐ Y tuong lay tu `SapienzaNLP/guardians-mt-eval` (ACL 2024, *"Guardians of
#:    the MT Meta-Evaluation: Sentinel Metrics Fall In!"*) — ⚠️ kho do la
#:    **CC BY-NC-SA 4.0**, ⛔ ta KHONG dung ma cua ho; y tuong thi khong co giay
#:    phep. Ho huan luyen metric chi nhin MOT phia; ta lam dung phep do do bang
#:    cach GIAU mot phia khoi chinh loi nhac san pham.
CANH_SENTINEL = ("du", "nguon_mu", "dich_mu")

#: Cong SENTINEL — ⛔ viet TRUOC khi chay.
#:
#: Do bang **KHA NANG PHAN BIET** = (ti le bat tren cap DA LAM HONG) − (ti le
#: gan co tren cap SACH cua nguoi dich). ⛔ Khong do bang "ti le gan co" mot
#: minh: mot bo cham GAN CO TAT CA cung se "bat" 100 % cap hong, va mot bo cham
#: LUON IM cung se "khong bao dong gia" — ca hai deu mu, va chi hieu so moi
#: tach duoc chung ra.
#:
#: ⛔ VE THU BA (canh `du`) LA BAT BUOC: thieu no thi mot bo cham luon im cung
#:    "qua" ca hai canh mu.
NGUONG_PHAN_BIET_DU = 0.30      # canh du PHAI con phan biet duoc
NGUONG_PHAN_BIET_MU = 0.15      # canh mu PHAI mat kha nang phan biet


def _giau(muc: list[dict], canh: str) -> list[dict]:
    """Giau mot phia. ⛔ Truong VAN CON, chi RONG — de loi nhac giu nguyen hinh.

    ⚠️ Giu nguyen `ma`: phan quyet van ghep duoc theo ma.
    """
    if canh == "du":
        return [dict(d) for d in muc]
    khoa = "goc" if canh == "nguon_mu" else "chu"
    return [{**d, khoa: ""} for d in muc]


def do_sentinel(*, db, canh: str, dong_sach: list[int], moi_loai: int,
                bo_qua: int, luot: int = LUOT_MOI_CAP, ban: str = "v3",
                thu_muc: pathlib.Path = FLORES_DIR) -> dict:
    """Chay mot canh sentinel tren CA cap sach LAN cap da lam hong.

    🔴 **Cau hoi co TRUOC moi cau khac.** Neu bo cham van phan duoc khi ta bo
       mot phia, thi no dang cham bang **thien lech be mat** — va ⛔ moi con so
       do nhay/bao dong gia truoc do deu RONG.

    ⚠️ **Mot chi tiet co hoc phai khai:** `doc_ngu_nghia` loai moi loi khong
       trich duoc `doan` trong van ban ĐÃ GUI. O canh `nguon_mu`, mot loi trich
       tu cau nguon ⇒ ⛔ khong khop duoc ⇒ bi loai **bang may**, khong phai vi
       model im. Nen canh mu duoc **tro giup** boi chinh bo loc nay; ⇒ mot canh
       mu VAN phan biet duoc la bang chung **manh hon**, con canh mu mat kha
       nang phan biet thi ⛔ **chua** tach duoc "model mu" khoi "bo loc cat".
    """
    if canh not in CANH_SENTINEL:
        raise SystemExit(f"canh la {CANH_SENTINEL}, khong phai {canh!r}")
    can = set(int(x) for x in dong_sach)
    cap = doc_flores(thu_muc)
    sach = [{"ma": f"flores_{i:04d}", "goc": zh, "chu": vi}
            for i, zh, vi in cap if i in can]
    if len(sach) != len(can):
        raise SystemExit(f"chi tim duoc {len(sach)}/{len(can)} dong sach")
    hong = dung_cap_tiem(cap[bo_qua:], moi_loai=moi_loai,
                         rng=random.Random(HAT_GIONG))
    muc = _giau(sach + hong, canh)
    bat_dau = _bay_gio()
    cac_luot = []
    for k in range(luot):
        print(f"  [SENTINEL {canh}] {ban} luot {k + 1}/{luot} — "
              f"{len(sach)} sach + {len(hong)} hong")
        cac_luot.append(cham_mot_luot(db, muc, ban))
    ma_sach = [d["ma"] for d in sach]
    gop = gop_trung_vi(cac_luot, ma_sach + [d["ma"] for d in hong])

    def _ti(ma_ds):
        co = [m for m in ma_ds if m in gop]
        k = sum(1 for m in co if not gop[m]["dat"])
        return {"n": len(co), "k": k,
                "ti_le": round(k / len(co), 4) if co else None}

    ra_sach = _ti(ma_sach)
    theo_loai = {l: _ti([d["ma"] for d in hong if d["loai"] == l])
                 for l in ("lat_nghia", "sai_thuc_the")}
    tong_hong = _ti([d["ma"] for d in hong])
    pb = (None if tong_hong["ti_le"] is None or ra_sach["ti_le"] is None
          else round(tong_hong["ti_le"] - ra_sach["ti_le"], 4))
    return {
        "canh": canh, "ban": ban, "luot": luot,
        "cua_so_utc": [bat_dau, _bay_gio()],
        "dong_sach": sorted(can), "n_hong": len(hong),
        "gan_co_tren_cap_SACH": ra_sach,
        "bat_tren_cap_HONG": tong_hong,
        "bat_theo_loai": theo_loai,
        # ⭐ Con so quyet dinh: hieu so. ⛔ Khong doc mot ve mot minh.
        "kha_nang_phan_biet": pb,
        "luoc_do": thong_ke_luoc_do(cac_luot, len(muc)),
        "gop": gop, "cac_luot": cac_luot,
    }


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


#: Nguoi soi mu goi la LOI o muc nao thi tinh la loi THAT. ⛔ Viet TRUOC khi
#: doi chieu.
#:
#: ⭐ `ro` la dinh nghia CHINH: "nguoi xem se tin mot su viec sai" — dung cau hoi
#:    bo cham duoc giao. `zh_lech` va `bien` chi de phan tich do nhay cua ket
#:    luan, ⛔ khong de chon cai nao cho ra so dep.
COI_LA_LOI = {
    "chinh": ("ro",),
    "rong": ("ro", "zh_lech"),
    "rong_nhat": ("ro", "zh_lech", "bien"),
}


def doi_chieu(so_soi: dict, cham: dict, *, nguong_luot: int = 2) -> dict:
    """Doi chieu THANG bo cham voi so soi MU — ⛔ khong tru, khong gia dinh.

    🔴 **Vi sao bo phep tru.** `bao dong gia - san loi FLORES` chi dung neu bo
       cham bat duoc **MOI** loi co san cua FLORES, tuc ngam gia dinh do nhay
       100 % tren loi **TU NHIEN**. Ta chi do do nhay tren loi **TA TIEM**, ma
       loi tiem khong cung hinh dang voi `山寨货` -> *"bi ngung kinh doanh"*.
       Bo cham bo sot mot phan loi tu nhien ⇒ ta **tru qua tay** ⇒ so qua dep.

    ⭐ **Phep do nay sach dung o cho ta lo nhat:** phan quyet cua nguoi soi duoc
       ghi **truoc**, **mu**, va **da commit** — ⛔ khong ai chinh duoc sau khi
       thay bo cham noi gi. Do la dieu kien ma viec "soi tap bi gan co" khong co.

    Tra ve bang 2x2 cho tung dinh nghia trong `COI_LA_LOI`:

        gan co & nguoi goi la loi      -> `dung`       (bat trung)
        gan co & nguoi goi khong loi   -> **BAO DONG GIA THAT**
        khong gan co & nguoi goi loi   -> **BO SOT loi TU NHIEN**
        khong gan co & khong loi       -> `dung_am`
    """
    pq = {}
    for m in so_soi["muc"]:
        pq[int(m["dong_flores"])] = str(m["phan_quyet"])
    gop = cham["gop"]
    ra: dict = {"n": 0, "theo_dinh_nghia": {}}
    co_cham = []
    for i in sorted(pq):
        ma = f"flores_{i:04d}"
        if ma in gop:
            co_cham.append(i)
    ra["n"] = len(co_cham)
    ra["dong_khong_cham_duoc"] = [i for i in sorted(pq) if i not in co_cham]
    for ten, nhan in COI_LA_LOI.items():
        dung = bdg = bo_sot = dung_am = 0
        ds_bdg, ds_bo_sot = [], []
        for i in co_cham:
            gan_co = not gop[f"flores_{i:04d}"]["dat"]
            la_loi = pq[i] in nhan
            if gan_co and la_loi:
                dung += 1
            elif gan_co:
                bdg += 1
                ds_bdg.append(i)
            elif la_loi:
                bo_sot += 1
                ds_bo_sot.append(i)
            else:
                dung_am += 1
        gan = dung + bdg
        that = dung + bo_sot
        ra["theo_dinh_nghia"][ten] = {
            "nhan": list(nhan),
            "so_gan_co": gan, "so_loi_that": that,
            "dung": dung, "bao_dong_gia": bdg, "bo_sot": bo_sot,
            "dung_am": dung_am,
            # ⭐ Ti le BAO DONG GIA THAT — do THANG, khong tru.
            "ti_le_bao_dong_gia_that": round(bdg / gan, 4) if gan else None,
            # ⭐ Con so ta CHUA BAO GIO co: do nhay tren loi TU NHIEN.
            "do_nhay_loi_tu_nhien": round(dung / that, 4) if that else None,
            "dong_bao_dong_gia": ds_bdg, "dong_bo_sot": ds_bo_sot,
        }
    return ra


#: Trong so MQM, lay tu giao thuc goc — ⛔ khong phai so ta tu nghi ra.
#:
#: NGUON: `MicrosoftTranslator/GEMBA`, `gemba/gemba_mqm_utils.py`,
#: `parse_mqm_answer` (sha a7a7eff): `final_score += 25 if error_level ==
#: 'critical' else 5 if error_level == 'major' else 1`, chan o **5 loi dau**
#: (`if error_counter < 5`) va tran **25** (`if final_score > 25`).
#:
#: 🔑 ⭐ **Va day la cho ta da bo mat mot BUOC.** Giao thuc goc bien danh sach
#:    loi thanh mot **DIEM** roi moi nguong tren TONG; ta phan `dat=false` ngay
#:    khi co >= 1 loi `nang` — mot co NHI PHAN tren muc cao nhat. ⇒ o giao thuc
#:    goc, MOT loi bi xep qua tay ⛔ khong lat duoc phan quyet; o ta thi co.
TRONG_SO_MQM = {"nghiem_trong": 25, "nang": 5, "nhe": 1}

#: Giao thuc goc chi dem **5 loi dau** va tran diem **25**.
TRAN_SO_LOI_MQM = 5
TRAN_DIEM_MQM = 25


def diem_mqm(muc: list[str]) -> int:
    """Diem MQM co trong so cua MOT luot — theo dung `parse_mqm_answer`."""
    diem = 0
    for m in muc[:TRAN_SO_LOI_MQM]:
        diem += TRONG_SO_MQM.get(m, 0)
    return min(diem, TRAN_DIEM_MQM)


def muc_theo_ma(cac_luot: list[dict], ma: list[str]) -> dict:
    """`{ma: [[muc,...] | None moi luot]}` — ⛔ TACH hai kieu mot ma vang mat.

    ⛔ Ma nam trong lo HONG => `None` (chua hoi xong), ⛔ khong phai danh sach
       rong. Ma khong duoc nhac toi trong mot lo CHAY DUOC => `[]` = khong loi
       nao = DAT, dung hop dong `doc_ngu_nghia`.
    """
    ra: dict = {}
    for m in ma:
        hang = []
        for l in cac_luot:
            if m in l["phan_quyet"]:
                hang.append([str(x.get("muc") or "")
                             for x in (l["phan_quyet"][m].get("loi") or [])])
            elif m in _mat_lo(l):
                hang.append(None)
            else:
                hang.append([])
        ra[m] = hang
    return ra


def gia_theo_ho(hang: list[list[str]], ho: str) -> float:
    """Gia tri gop cua mot ma theo ho luat — TRUNG VI tren cac luot tra loi."""
    if ho == "diem":
        return _trung_vi([diem_mqm(h) for h in hang])
    return _trung_vi([sum(1 for m in h if m in ("nang", "nghiem_trong"))
                      for h in hang])


def quet_nguong_tiem(tiem: dict) -> dict:
    """Do nhay tren loi TA TIEM, theo TUNG LOAI, o moi nguong — offline.

    🔴 **Ve hai cua cong doi dung con so nay**, ⛔ khong phai do nhay tren loi
       tu nhien. Va no la cho phai nghi nhat: luat `diem >= 6` doi **hai** loi
       `nang` (5+5), nen MOT loi thuc the don le bi cham `nhe` (1 diem) se ⛔
       **khong** kich cong — tuc co the dung lai dung cho mu da giet V2.
    """
    ra: dict = {}
    for loai, k in (tiem.get("theo_loai") or {}).items():
        ma = [m for m in tiem["gop"] if m.startswith(f"tiem_{loai}_")]
        muc = muc_theo_ma(tiem["cac_luot"], ma)
        hang_ra = []
        for ho, nguong in (("diem", range(1, TRAN_DIEM_MQM + 1)),
                           ("dem", range(1, 6))):
            for t in nguong:
                n = bat = 0
                for m in ma:
                    co_tra_loi = [h for h in muc[m] if h is not None]
                    if not co_tra_loi:
                        continue
                    n += 1
                    # ⛔ Tren mot cap DA LAM HONG, "gan co" chinh la BAT DUOC.
                    bat += gia_theo_ho(co_tra_loi, ho) >= t
                hang_ra.append({"ho": ho, "nguong": t, "n": n,
                                "bat_duoc": bat,
                                "ti_le": round(bat / n, 4) if n else None})
        ra[loai] = {"n_hoi": k.get("n_hoi"), "duong_cong": hang_ra}
    return ra


def muc_tung_luot(cham: dict) -> dict:
    """`{dong: [[muc,...] moi luot]}` — ⛔ TACH hai kieu mot ma vang mat.

    ⛔ Ma nam trong lo HONG => `None` (chua hoi xong), ⛔ khong phai danh sach
       rong. Ma khong duoc nhac toi trong mot lo CHAY DUOC => `[]` = khong loi
       nao = DAT, dung hop dong `doc_ngu_nghia`.
    """
    ma = [f"flores_{i:04d}" for i in cham["dong"]]
    theo_ma = muc_theo_ma(cham["cac_luot"], ma)
    return {str(i): theo_ma[f"flores_{i:04d}"] for i in cham["dong"]}


def _trung_vi(xs: list[float]) -> float:
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def quet_nguong(muc: dict, pq: dict, nhan: tuple[str, ...],
                dong: list[int] | None = None) -> list[dict]:
    """Duong cong BAO DONG GIA THAT vs DO NHAY TREN LOI TU NHIEN.

    ⭐ **Mien phi:** tinh lai tren dau ra da luu, ⛔ khong goi model lan nao.

    ⛔ Khong thu MOT diem van hanh roi bao "dat/khong dat": ve **ca duong cong**,
       roi hoi mot cau CO/KHONG — *co ton tai diem nao thoa CA HAI cong khong?*
       "Khong co diem nao" ⛔ khong phai that bai, no la mot ket qua QUYET DINH
       ve thiet ke nay.

    Hai ho luat, ca hai deu lay TRUNG VI tren cac luot (cung cach gop voi `gop_trung_vi`):
      `diem`  — gan co khi diem MQM co trong so >= `t`
      `dem`   — gan co khi so loi muc >= `nang` la >= `k`
    """
    ds = [i for i in (dong if dong is not None else
                      sorted(int(x) for x in muc)) if str(i) in muc]
    ra = []
    for ho, nguong in (("diem", range(1, TRAN_DIEM_MQM + 1)),
                       ("dem", range(1, 6))):
        for t in nguong:
            gan = loi_that = trung = bdg = 0
            for i in ds:
                hang = [h for h in muc[str(i)] if h is not None]
                if not hang:
                    continue
                co = gia_theo_ho(hang, ho) >= t
                that = pq.get(i) in nhan
                gan += co
                loi_that += that
                trung += co and that
                bdg += co and not that
            ra.append({
                "ho": ho, "nguong": t, "n": len(ds),
                "so_gan_co": gan, "so_loi_that": loi_that, "bat_trung": trung,
                # ⛔ Mau so la TONG SO DONG — cung dinh nghia voi cong 15 %
                #    ("ti le bao dong gia tren >= 100 cap"), ⛔ khong phai
                #    "tren so dong bi gan co".
                "bao_dong_gia": round(bdg / len(ds), 4) if ds else None,
                "do_nhay_tu_nhien": (round(trung / loi_that, 4)
                                     if loi_that else None),
            })
    return ra


def chon_diem(duong: list[dict]) -> dict | None:
    """Chon diem van hanh — LUAT VIET TRUOC, ⛔ khong chon sau khi thay so.

    Trong cac diem co **do nhay >= `NGUONG_BAT_LOI_TIEM`**, lay diem co **bao
    dong gia thap nhat**; hoa thi do nhay cao hon; van hoa thi nguong LON hon
    (bao thu hon, it gan co hon).
    """
    ung = [d for d in duong
           if d["do_nhay_tu_nhien"] is not None
           and d["do_nhay_tu_nhien"] >= NGUONG_BAT_LOI_TIEM]
    if not ung:
        return None
    return min(ung, key=lambda d: (d["bao_dong_gia"],
                                   -d["do_nhay_tu_nhien"], -d["nguong"]))


def chia_doi(ds: list[int]) -> tuple[list[int], list[int]]:
    """Chia doi theo CHAN/LE cua vi tri trong danh sach da sap xep.

    ⛔ Khong chia theo 500-699 / 700-899: 10 loi ro nam 3/7 giua hai nua do, va
       mot nua 3 loi khong do noi do nhay. Chia xen ke can bang hon **va** giu
       ca hai nua trai deu tren toan dai.
    """
    d = sorted(ds)
    return d[0::2], d[1::2]


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
    d.add_argument("--tiem-loai", default=",".join(LOAI_TIEM),
                   help="cac ho loi can tiem, ngan bang dau phay")
    d.add_argument("--luot", type=int, default=LUOT_MOI_CAP)
    d.add_argument("--ban", choices=tuple(BAN_LOI_NHAC), default="v3",
                   help="ban loi nhac: v1/v2 la ban DONG BANG tu git, "
                        "v3 la ban HIEN HANH cua san pham")
    d.add_argument("--theo-so", default="",
                   help="tep so soi mu: cham DUNG cac `muc[].dong_flores` "
                        "trong do, thay vi mot dai lien tuc")
    d.add_argument("--ra", required=True)
    g = s.add_parser("gop")
    g.add_argument("--fa", nargs="+", required=True,
                   help="cac ban ghi `fa` tung phan, ghep lai")
    g.add_argument("--tiem", default="",
                   help="ban ghi doi chung AM. ⛔ Vang mat thi ban ghi gop "
                        "KHONG mang mot phan quyet — chi de `doi-chieu`")
    g.add_argument("--ra", required=True)
    b = s.add_parser("bao-cao")
    b.add_argument("tep")
    sn = s.add_parser("sentinel")
    sn.add_argument("--canh", choices=CANH_SENTINEL, required=True)
    sn.add_argument("--so-soi", required=True,
                    help="tep so soi mu: lay `dong_flores` lam cap SACH")
    sn.add_argument("--n-sach", type=int, default=30)
    sn.add_argument("--tiem-moi-loai", type=int, default=15)
    sn.add_argument("--tiem-bo-qua", type=int, default=300)
    sn.add_argument("--luot", type=int, default=LUOT_MOI_CAP)
    sn.add_argument("--ban", choices=tuple(BAN_LOI_NHAC), default="v3")
    sn.add_argument("--ra", required=True)
    q = s.add_parser("quet")
    q.add_argument("--cham", required=True,
                   help="ban ghi bo cham co `cac_luot` (dau ra THO)")
    q.add_argument("--so-soi", required=True)
    q.add_argument("--dinh-nghia", choices=tuple(COI_LA_LOI), default="chinh")
    q.add_argument("--tiem", default="",
                   help="ban ghi doi chung AM (co `cac_luot`): them duong cong "
                        "DO NHAY TREN LOI TIEM theo TUNG loai — ve hai cua cong")
    q.add_argument("--ra", required=True)
    dc = s.add_parser("doi-chieu")
    dc.add_argument("--so-soi", required=True,
                    help="so soi MU (phan quyet nguoi doc, da commit TRUOC)")
    dc.add_argument("--cham", required=True, help="ban ghi bo cham tren CUNG dai")
    dc.add_argument("--con", default="", help="danh sach dong cua tap con (JSON)")
    dc.add_argument("--ra", required=True)
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
    if a.lenh == "quet":
        _d = (lambda x: json.loads(
            pathlib.Path(x).read_text(encoding="utf-8")))
        cham = _d(a.cham)["bao_dong_gia"]
        so_soi = _d(a.so_soi)
        pq = {int(m["dong_flores"]): str(m["phan_quyet"])
              for m in so_soi["muc"]}
        muc = muc_tung_luot(cham)
        nhan = COI_LA_LOI[a.dinh_nghia]
        a_nua, b_nua = chia_doi([int(x) for x in muc])
        ra = {"phien_ban": 1, "ban_loi_nhac": cham.get("ban"),
              "dinh_nghia_loi": a.dinh_nghia, "nhan": list(nhan),
              "trong_so_mqm": TRONG_SO_MQM,
              "nguon_trong_so": ("MicrosoftTranslator/GEMBA "
                                 "gemba/gemba_mqm_utils.py::parse_mqm_answer"),
              # ⛔ Duong cong tren CA 100 dong chi de xem HINH DANG — chon
              #    nguong roi bao so tren cung tap la chinh tren bai thi.
              "duong_cong_toan_bo": quet_nguong(muc, pq, nhan),
              # ⛔ Do nhay tren loi TU NHIEN ⛔ KHONG phai ve hai cua cong —
              #    cong doi >= 50 % MOI LOAI TIEM. Hai con so khac nhau.
              "duong_cong_tiem": (quet_nguong_tiem(_d(a.tiem)["bat_loi_tiem"])
                                  if a.tiem else None),
              "chia_doi": {"A": a_nua, "B": b_nua},
              "muc_tung_dong": muc}
        for ten, chon_tren, bao_tren in (("chon_A_bao_B", a_nua, b_nua),
                                         ("chon_B_bao_A", b_nua, a_nua)):
            duong_chon = quet_nguong(muc, pq, nhan, dong=chon_tren)
            diem = chon_diem(duong_chon)
            if diem is None:
                ra[ten] = {"diem": None,
                           "ket_luan": "khong co diem nao dat do nhay tren nua CHON"}
                continue
            bao = [d for d in quet_nguong(muc, pq, nhan, dong=bao_tren)
                   if d["ho"] == diem["ho"] and d["nguong"] == diem["nguong"]][0]
            ra[ten] = {"diem": diem, "bao_tren_nua_kia": bao,
                       "so_loi_that_nua_bao": bao["so_loi_that"]}
        pathlib.Path(a.ra).write_text(
            json.dumps(ra, ensure_ascii=False, indent=1), encoding="utf-8")
        for d in ra["duong_cong_toan_bo"]:
            print(f"[{d['ho']} >= {d['nguong']:>2}] gan co {d['so_gan_co']:>3}"
                  f" | BDG {d['bao_dong_gia']} | do nhay {d['do_nhay_tu_nhien']}")
        for ten in ("chon_A_bao_B", "chon_B_bao_A"):
            print(ten, json.dumps(ra[ten], ensure_ascii=False))
        return 0
    if a.lenh == "doi-chieu":
        _d = (lambda x: json.loads(
            pathlib.Path(x).read_text(encoding="utf-8")))
        so_soi = _d(a.so_soi)
        cham = _d(a.cham)["bao_dong_gia"]
        ra = {"phien_ban": 1, "ban_loi_nhac": cham.get("ban"),
              "toan_bo": doi_chieu(so_soi, cham)}
        if a.con:
            con = set(int(x) for x in _d(a.con))
            ra["tap_con_doi_chung_kep"] = doi_chieu(
                {"muc": [m for m in so_soi["muc"]
                         if int(m["dong_flores"]) in con]}, cham)
        pathlib.Path(a.ra).write_text(
            json.dumps(ra, ensure_ascii=False, indent=1), encoding="utf-8")
        for ten, k in ra["toan_bo"]["theo_dinh_nghia"].items():
            print(f"[{ten}] gan co {k['so_gan_co']} | loi that {k['so_loi_that']}"
                  f" | BAO DONG GIA THAT {k['ti_le_bao_dong_gia_that']}"
                  f" | do nhay loi TU NHIEN {k['do_nhay_loi_tu_nhien']}")
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
              "bat_loi_tiem": _doc(a.tiem)["bat_loi_tiem"] if a.tiem else None}
        pathlib.Path(a.ra).write_text(
            json.dumps(ra, ensure_ascii=False, indent=1), encoding="utf-8")
        # ⛔ Thieu doi chung AM thi KHONG in phan quyet: hai cong phai cung luc,
        #    va mot dong "PHAN QUYET" in ra la mot dong se bi trich.
        if a.tiem:
            print(bao_cao(ra))
        else:
            print(f"da ghi {a.ra} — ⛔ CHUA co doi chung am, khong phan quyet")
        return 0

    from tools import do_llm_cong_asv as mt
    mt._nap_app_env()
    db, so_khoa = mt._mo_db()
    print(f"[MOI TRUONG] {so_khoa} khoa pool")
    t0 = time.monotonic()
    if a.lenh == "sentinel":
        so = json.loads(
            pathlib.Path(a.so_soi).read_text(encoding="utf-8"))
        dong = sorted(int(m["dong_flores"]) for m in so["muc"])[:a.n_sach]
        r = do_sentinel(db=db, canh=a.canh, dong_sach=dong,
                        moi_loai=a.tiem_moi_loai, bo_qua=a.tiem_bo_qua,
                        luot=a.luot, ban=a.ban)
        pathlib.Path(a.ra).write_text(
            json.dumps({"phien_ban": 1, "sentinel": r},
                       ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[SENTINEL {a.canh}] gan co tren cap SACH "
              f"{r['gan_co_tren_cap_SACH']['ti_le']} | bat tren cap HONG "
              f"{r['bat_tren_cap_HONG']['ti_le']} | KHA NANG PHAN BIET "
              f"{r['kha_nang_phan_biet']}")
        return 0
    khoi_fa: dict | None = None
    tiem: dict | None = None
    if a.pha in ("ca", "fa"):
        dong = None
        if a.theo_so:
            so = json.loads(pathlib.Path(a.theo_so).read_text(encoding="utf-8"))
            dong = [int(m["dong_flores"]) for m in so["muc"]]
        khoi_fa = ti_le_bao_dong_gia(a.n, db=db, luot=a.luot, tu=a.tu,
                                    ban=a.ban, dong=dong)
    if a.pha in ("ca", "tiem"):
        loai_can = tuple(x.strip() for x in a.tiem_loai.split(",") if x.strip())
        la = [x for x in loai_can if x not in LOAI_TIEM]
        if la:
            raise SystemExit(f"ho loi la: {la} — chi co {LOAI_TIEM}")
        tiem = ti_le_bat_loi_tiem(db=db, moi_loai=a.tiem_moi_loai,
                                  luot=a.luot, bo_qua=a.tiem_bo_qua,
                                  ban=a.ban, loai_can=loai_can)
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
