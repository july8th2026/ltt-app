"""Vong doi artifact cua Auto Scan Video: dat khoa, promote nguyen tu, toan ven.

Thi hanh ADR-001 D7 (giao thuc hoan tat nam buoc) va D8 (van tay + cache theo
chu so huu).

## Nam buoc, va vi sao THU TU la phan quan trong

    1. engine tra ve
    2. output HOP LE          <- kiem noi dung, khong chi kiem ton tai
    3. `storage.promote`      <- staging -> khoa ben vung
    4. ghi tham chieu + van tay
    5. commit

Doi cho buoc 2 va 3 la mot loi im lang: mot tep hong duoc promote thanh ket qua
chinh thuc roi moi bi phat hien — neu con ai kiem. Bo buoc 2 thi "DONE" chi con
nghia la "engine khong nem", va bat bien I8 mat het noi dung.

## Bon cua so su co, va cach ra khoi tung cai

| Chet giua | Hien trang | Loi ra |
|---|---|---|
| 1→2 | co tep staging, khong co gi trong CSDL | `upload_sessions.sweep` don staging; giai doan chay lai |
| 2→3 | nhu tren | nhu tren |
| 3→4 | tep DA ben vung, khong ai tham chieu | chay lai: van tay tinh lai ra **cung mot khoa**, nen lan ghi thu hai de len chinh no |
| 4→5 | transaction cuon lai | giong 3→4 |

⭐ Cot song cua ca bang tren la mot dieu: **khoa duoc dan xuat tu VAN TAY**, chu
   khong tu dong ho hay bo dem. Nen ghi lai la mot phep toan luy dang (idempotent),
   va mot lan chet chi ton cong tinh, khong bao gio ton tinh dung dan.
   Chot boi `test_401...::test_ghi_lai_cung_mot_van_tay_la_idempotent`.

## Cache: vi sao LUON loc theo chu so huu

Hai khach tai len dung mot tep se ra dung mot van tay. Dung lai ket qua cua
nguoi nay cho nguoi kia se **tiet lo rang nguoi kia dang giu dung tep do** — mot
ro ri khong can doc noi dung cung suy ra duoc. MVP tinh lai cho tung chu so huu
(I19, EXECUTION_GUARDRAILS muc 8). Chia se giua cac chu so huu can mot ADR rieng
ve rieng tu, khong phai mot toi uu.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_core.i18n import _ as _t
from platform_core.storage import Storage, StorageError

from .tables import (ASSET_CORRUPT, ASSET_EXPIRED, ASSET_MISSING, ASSET_OK,
                     KINDS, AsvAsset)

#: Han luu tru mac dinh cua artifact TRUNG GIAN. Ngan hon vong doi mot du an,
#: vi chung la vat lieu chu khong phai san pham; ban giao cho khach la
#: `final.mp4`, va no duoc ghi voi han rieng.
HAN_TRUNG_GIAN = timedelta(days=30)

#: Chi cac ky tu nay duoc phep trong mot doan khoa do ta tu dat.
_DOAN_HOP_LE = re.compile(r"^[A-Za-z0-9._-]+$")


class AssetError(ValueError):
    """Loi vong doi artifact."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(gia_tri: datetime | None) -> datetime | None:
    """Gan UTC cho mot `datetime` khong mang mui gio.

    🔴 BAT BUOC truoc moi phep so sanh thoi gian doc tu CSDL. SQLite **khong**
       giu mui gio: ghi xuong mot `datetime` aware, doc len duoc mot cai naive,
       va `naive <= aware` nem `TypeError`. PostgreSQL cua production giu, nen
       thieu ham nay thi loi chay tot o production va chi no trong bo test —
       tuc no o dung cho lam nguoi ta tuong minh viet sai fixture.

    ⭐ Khong phai phat minh moi: `platform_core/credit.py:541` da co dung ham nay
       vi dung ly do. Mang sang thay vi tu nghi ra mot cach khac.
    """
    if gia_tri is None:
        return None
    return gia_tri if gia_tri.tzinfo else gia_tri.replace(tzinfo=timezone.utc)


# ══════════════════════════════════════════════════════════════════════════════
#  Dat khoa — khong bao gio tin chuoi cua client
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
#  NGAN SACH DO DAI DUONG — do duoc, khong phai chon cho dep
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔴 Da hong that ngay 02/09. Khoa mang van tay sha256 **day du** (64 ky tu hex)
#    lam duong dai **262** tren Windows, va MAX_PATH la **260**:
#
#      ...\popen-gw2\test_MOT_tep_cho_MOI_doan0\kho\asv-staging\uA\
#      asvr_<32 hex>\voice_synthesis\<64 hex>.wav.part20608      <- 262
#
#    ⚠️ Hai cho `<...>` o tren tung la hex THAT khi ghi chu nay moi viet, va bo
#       quet bi mat cua `tests/test_44` bat ngay: mot chuoi 32 ky tu hex tran
#       trui trong ma nguon **khong phan biet duoc** voi mot khoa that. No dung
#       — mot bo quet chi tin duoc khi no khong doan y dinh cua nguoi viet.
#
#    `Storage.put` nem `FileNotFoundError` ngay o `open(tmp,'wb')` — mot thong
#    bao noi ve mot tep khong ton tai, cho mot loi that ra la duong qua dai.
#
# ⭐ Va no hong theo dung kieu te nhat: chay MOT MINH thi **252, xanh**; chay
#    trong gate thi xdist chen them `popen-gwN\` (10 ky tu) va thanh **262, do**.
#    Mot loi that trong ma chi lo ra khi chay song song rat de bi doc nham thanh
#    "test chap chon" roi chay lai cho toi khi tra xanh.
#
# ⛔ Loi KHONG nam o `platform_core/storage.py` — hau to `.part<pid>` chi them 12
#    ky tu. No nam o cho TA dat ba dinh danh day du canh nhau trong mot duong.
#
# 🔑 Va bai hoc dat hon ca lan sua dau: cat rieng van tay xuong 32 van **chua
#    du**. Phep kiem dau tien cua ta dung `owner_id` la `"uA"` — dai 2 ky tu —
#    trong khi `owner_id` that la UUID **36 ky tu**. Tuc ban va dau tien xanh vi
#    du lieu thu qua hien, khong vi loi da het. Chi khi dung dau vao xau nhat
#    THAT SU (`tests/test_412`) moi lo ra la van con 269.
#
# Ngan sach (goc gia dinh 120 = tmpdir cua pytest + xdist; production chi ~28):
#
#      asv-staging/                             12
#      {owner[:16]}/                            17
#      {run[:24]}/                              25
#      {stage}/          (dai nhat content_process)   16
#      {van_tay[:32]}.wav                       36
#                                              ---
#                                              106  + 120 goc + 12 `.part` = 238
#
#: 16 ky tu dau cua UUID chu so huu. Van giu duoc tinh chat o docstring `dat_khoa`
#: (khoa mang chu so huu), va tham quyen phan quyen van la cot CSDL chu khong
#: phai chuoi duong dan.
DAI_OWNER_TRONG_KHOA = 16
#: `asvr_` + 19 hex = 76 bit, dac trong pham vi mot chu so huu.
DAI_RUN_TRONG_KHOA = 24
#: 32 ky tu hex = 128 bit. Thua suc chong dung cho vai nghin artifact mot lan
#: chay. Ban DAY DU van nam nguyen trong `AsvAsset.van_tay` — cat o day chi cat
#: cai TEN, khong cat bang chung.
DAI_VAN_TAY_TRONG_KHOA = 32


def dat_khoa(*, owner_id: str, run_id: str, stage: str, van_tay: str,
             duoi: str) -> str:
    """`asv/{owner}/{run}/{stage}/{van_tay}.{duoi}` — TU DAT, khong nhan tu ngoai.

    Van tay bi cat con `DAI_VAN_TAY_TRONG_KHOA` ky tu trong TEN TEP (xem ghi chu
    o hang so do). Cat mot cach xac dinh nen tra cuu van khop: cung dau vao ra
    cung khoa, va ban day du van nam trong CSDL de doi chieu toan ven.

    🔴 Day la cho de mot he thong luu tru bi bien thanh mot he thong doc tep tuy
       y. `platform_core/storage.py:181 _safe_key` da chan `../`, va no la lop
       phong thu cuoi — nhung lop dau phai la **khong bao gio dung chuoi cua
       client lam khoa**. Ta dung tay tu tung manh da kiem, nen khong co duong
       nao cho mot dau `/` hay `..` di vao.

    ⭐ Chu so huu nam TRONG khoa, khong chi trong mot cot CSDL. Mot phep loc
       quyen dua vao `WHERE owner_id = ...` chi cach mot lan quen viet menh de
       do; mot khoa mang chu so huu thi ro ri doi hoi ai do co y dung ghep mot
       duong dan cua nguoi khac.
    """
    manh = {"owner_id": owner_id, "run_id": run_id, "stage": stage,
            "van_tay": van_tay, "duoi": duoi.lstrip(".")}
    for ten, gia_tri in manh.items():
        if not gia_tri or not _DOAN_HOP_LE.match(str(gia_tri)):
            raise AssetError(f"manh khoa khong hop le: {ten}={gia_tri!r}")
    # ⚠️ Cat SAU khi da kiem tung manh, khong truoc: cat truoc thi mot manh rac
    #    du dai co the bi xen thanh mot manh trong nhin nhu hop le.
    return (f"asv/{manh['owner_id'][:DAI_OWNER_TRONG_KHOA]}"
            f"/{manh['run_id'][:DAI_RUN_TRONG_KHOA]}/{manh['stage']}/"
            f"{manh['van_tay'][:DAI_VAN_TAY_TRONG_KHOA]}.{manh['duoi']}")


def khoa_staging(*, owner_id: str, run_id: str, stage: str, van_tay: str,
                 duoi: str) -> str:
    """Khoa tam, cung khong gian ten nen mot lan don sot lai van tim ra."""
    return "asv-staging/" + dat_khoa(owner_id=owner_id, run_id=run_id,
                                     stage=stage, van_tay=van_tay,
                                     duoi=duoi)[len("asv/"):]


# ══════════════════════════════════════════════════════════════════════════════
#  Buoc 2: kiem HOP LE — khong chi kiem ton tai
# ══════════════════════════════════════════════════════════════════════════════

def _doc_het(kho: Storage, khoa: str) -> bytes:
    f = kho.open(khoa)
    try:
        return f.read()
    finally:
        f.close()


def bam(du_lieu: bytes) -> str:
    return hashlib.sha256(du_lieu).hexdigest()


def kiem_hop_le(kho: Storage, khoa: str, *, kind: str) -> tuple[int, str]:
    """Kiem noi dung theo `kind`. Tra `(co, checksum)`. Nem neu khong dat.

    ⛔ Mot tep 0 byte la KHONG hop le voi moi loai. Do la hinh dang thuong gap
       nhat cua mot lan chet giua chung: tep da duoc tao, chua kip ghi gi.
       De no qua nghia la mot giai doan bao DONE voi mot ket qua rong (I8).
    """
    if kind not in KINDS:
        raise AssetError(f"loai artifact khong biet: {kind!r}")
    try:
        du_lieu = _doc_het(kho, khoa)
    except StorageError as exc:
        raise AssetError(f"khong doc duoc artifact: {khoa}") from exc
    except FileNotFoundError as exc:
        raise AssetError(f"artifact khong ton tai: {khoa}") from exc

    if not du_lieu:
        raise AssetError(f"artifact rong: {khoa}")

    if kind == "json":
        try:
            json.loads(du_lieu.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AssetError(f"artifact JSON hong: {khoa}") from exc

    elif kind in ("video", "audio"):
        # 🔑 Pha 08 tra mon no cua pha 06. Truoc do o day chi kiem "khac rong",
        #    va ly do da ghi ra: chua engine nao sinh ra media that, nen mot phep
        #    kiem ffprobe se chi kiem cac tep gia — mot loi hua rong.
        #
        # ⛔ Voi media, "doc duoc mot byte" khong dinh nghia duoc dieu gi. Mot
        #    tep bi cat ngan giua chung van co header, van mo duoc, va van hong.
        #    Chi ffprobe tra loi duoc cau hoi "trong nay co mot luong that khong".
        _kiem_media(kho, khoa, kind=kind)

    return len(du_lieu), bam(du_lieu)


def _kiem_media(kho: Storage, khoa: str, *, kind: str) -> None:
    """ffprobe tren tep that. Nem `AssetError` neu khong co luong hop le.

    Chi chay duoc khi kho cho ra mot duong dan tren dia (`LocalStorage`). Voi R2
    thi khong tai ve chi de kiem — do la mot lan tai ve cho MOI artifact, va no
    doi mot phep kiem thanh mot khoan chi phi bang thong. Cho do se duoc chot
    bang phep kiem cua chinh giai doan render (pha 15), noi tep von da o tren dia.
    """
    from apps.auto_scan_video import nhap_media

    duong = kho.local_path(khoa) if hasattr(kho, "local_path") else None
    if not duong:
        return      # xem docstring: khong tai ve chi de kiem
    try:
        tt = nhap_media.soi(duong)
    except nhap_media.MediaError as exc:
        raise AssetError(f"artifact {kind} khong doc duoc: {khoa}") from exc

    if kind == "audio" and not tt.get("co_tieng"):
        raise AssetError(f"artifact audio khong co luong tieng: {khoa}")
    if kind == "video" and not tt.get("co_video"):
        raise AssetError(f"artifact video khong co luong hinh: {khoa}")
    if float(tt.get("thoi_luong") or 0) <= 0:
        raise AssetError(f"artifact {kind} co thoi luong 0: {khoa}")


# ══════════════════════════════════════════════════════════════════════════════
#  Buoc 3+4: promote roi ghi tham chieu
# ══════════════════════════════════════════════════════════════════════════════

def promote_va_ghi(db: Session, kho: Storage, *, owner_id: str, run_id: str,
                   stage: str, van_tay: str, kind: str, duoi: str,
                   staging_key: str, parent_keys: list | None = None,
                   schema_version: int = 1,
                   han: timedelta | None = HAN_TRUNG_GIAN) -> AsvAsset:
    """Buoc 2→4 cua giao thuc. Caller commit (buoc 5).

    Thu tu o day la hop dong, khong phai so thich: kiem hop le TRUOC khi promote,
    de mot tep hong khong bao gio den duoc khoa ben vung.
    """
    if not staging_key:
        raise AssetError("thieu staging_key")

    # Buoc 2 — kiem TREN BAN STAGING. Neu hong thi no chet o day, va khoa ben
    # vung chua bao gio bi cham toi.
    co, checksum = kiem_hop_le(kho, staging_key, kind=kind)

    khoa = dat_khoa(owner_id=owner_id, run_id=run_id, stage=stage,
                    van_tay=van_tay, duoi=duoi)

    # Buoc 3 — promote. Khoa dan xuat tu van tay nen ghi lai la luy dang.
    kho.promote(staging_key, khoa)

    # Buoc 4 — ghi tham chieu. Chay lai mot giai doan se gap dong cu; cap nhat
    # tai cho thay vi tao dong thu hai (rang buoc UNIQUE tren `storage_key`
    # bien mot lan tao trung thanh loi, chu khong thanh hai cau tra loi).
    row = db.execute(select(AsvAsset)
                     .where(AsvAsset.storage_key == khoa)).scalars().first()
    if row is None:
        row = AsvAsset(owner_id=owner_id, run_id=run_id, created_by_stage=stage,
                       kind=kind, storage_key=khoa)
        db.add(row)
    row.size = co
    row.checksum = checksum
    row.parent_keys = list(parent_keys or [])
    row.schema_version = int(schema_version)
    row.integrity = ASSET_OK
    row.expires_at = (_now() + han) if han else None
    db.flush()
    return row


# ══════════════════════════════════════════════════════════════════════════════
#  Toan ven va cache
# ══════════════════════════════════════════════════════════════════════════════

def kiem_toan_ven(db: Session, kho: Storage, asset: AsvAsset) -> str:
    """Doi chieu ban ghi voi tep that. Cap nhat va tra ve `integrity`.

    Ba cau tra loi khac nhau, va gop chung lai la mat thong tin can de xu ly:
      `missing` — tham chieu con, tep bien mat  -> phai tinh lai
      `corrupt` — tep con, noi dung da lech     -> phai tinh lai VA dang ngo
      `expired` — chinh sach luu tru, khong phai su co
    """
    han = _aware(asset.expires_at)
    if han is not None and han <= _now():
        asset.integrity = ASSET_EXPIRED
        db.flush()
        return ASSET_EXPIRED
    try:
        if not kho.exists(asset.storage_key):
            asset.integrity = ASSET_MISSING
            db.flush()
            return ASSET_MISSING
        du_lieu = _doc_het(kho, asset.storage_key)
    except (StorageError, FileNotFoundError):
        asset.integrity = ASSET_MISSING
        db.flush()
        return ASSET_MISSING

    if len(du_lieu) != int(asset.size) or bam(du_lieu) != asset.checksum:
        asset.integrity = ASSET_CORRUPT
        db.flush()
        return ASSET_CORRUPT

    asset.integrity = ASSET_OK
    db.flush()
    return ASSET_OK


def cache_dung_duoc(db: Session, kho: Storage, *, owner_id: str, run_id: str,
                    stage: str, van_tay: str) -> list[AsvAsset] | None:
    """Artifact dung lai duoc cho `(chu so huu, giai doan, van tay)`, hoac None.

    Hai dieu kien, ca hai bat buoc (I10):
      1. van tay khop  — dau vao/cau hinh/phien ban engine khong doi;
      2. moi artifact con SONG va con DUNG — kiem tung cai, khong tin ban ghi.

    ⛔ "Co mot tep dung ten" khong phai cache hop le (O13). Mot tep bi xoa, bi
       cat ngan hay het han deu lam luot dung lai thanh mot loi im lang — va no
       se lo ra o cuoi day chuyen, xa cho gay ra no.

    🔑 `owner_id` nam trong menh de WHERE **va** trong khoa. Hai khach cung mot
       van tay van la hai lan tinh (I19).
    """
    hang = list(db.execute(
        select(AsvAsset).where(AsvAsset.owner_id == owner_id,
                               AsvAsset.run_id == run_id,
                               AsvAsset.created_by_stage == stage)).scalars())
    if not hang:
        return None
    # Khoa mang van tay, nen loc bang chinh khoa la du va khong the nham.
    hop = [a for a in hang if f"/{van_tay}." in a.storage_key]
    if not hop:
        return None
    for a in hop:
        if kiem_toan_ven(db, kho, a) != ASSET_OK:
            return None
    return hop


def vo_hieu_theo_day_chuyen(db: Session, run_id: str,
                            tu_giai_doan: list[str]) -> int:
    """Danh dau artifact cua cac giai doan phu thuoc la khong con dung nua.

    Vi sao can mot ham rieng: van tay cua mot giai doan **da chua** van tay cua
    giai doan truoc (`thi_hanh._gom_dau_vao`), nen mot lan tinh lai o thuong
    nguon tu no lam moi van tay ha nguon doi. Nhung ban ghi cu van nam do va van
    noi `ok`; ham nay lam trang thai khop voi su that thay vi doi ai do phat hien.
    """
    if not tu_giai_doan:
        return 0
    hang = list(db.execute(
        select(AsvAsset).where(AsvAsset.run_id == run_id,
                               AsvAsset.created_by_stage.in_(tu_giai_doan))
    ).scalars())
    for a in hang:
        a.integrity = ASSET_MISSING
    db.flush()
    return len(hang)


# ══════════════════════════════════════════════════════════════════════════════
#  Doc co pham vi chu so huu (I6)
# ══════════════════════════════════════════════════════════════════════════════

def asset_cua(db: Session, khoa: str, owner_id: str) -> AsvAsset:
    """Mot artifact CUA CHINH `owner_id`, tra theo khoa. Nem neu khong phai.

    Day la cua duy nhat de doi mot chuoi khoa lay mot artifact. Khong bao gio
    dung thang chuoi client gui len de mo tep: mot khoa doan trung se doc duoc
    artifact cua nguoi khac neu khong co phep loc nay (I6/G4).
    """
    row = db.execute(select(AsvAsset).where(
        AsvAsset.storage_key == khoa,
        AsvAsset.owner_id == owner_id)).scalars().first()
    if row is None:
        # "Khong tim thay" chu khong phai "khong co quyen": phan biet hai cau tra
        # loi do cho phep do xem khoa nao ton tai.
        raise AssetError(_t('Không tìm thấy tài nguyên.'))
    return row


def don_theo_run(db: Session, kho: Storage, run_id: str, owner_id: str) -> int:
    """Xoa artifact cua MOT run cua chinh chu so huu. Tra ve so tep da xoa.

    ⛔ KHONG dung de don du lieu di san. Ham nay chi cham nhung gi chinh Auto
       Scan da ghi, trong pham vi mot run cua mot nguoi (Prompt 06: "no cleanup
       of legacy data").
    """
    hang = list(db.execute(
        select(AsvAsset).where(AsvAsset.run_id == run_id,
                               AsvAsset.owner_id == owner_id)).scalars())
    dem = 0
    for a in hang:
        try:
            kho.delete(a.storage_key)
            dem += 1
        except (StorageError, FileNotFoundError):
            pass    # da bien mat roi thi khong con gi de xoa
        db.delete(a)
    db.flush()
    return dem
