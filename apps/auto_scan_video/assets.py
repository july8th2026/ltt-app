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
from pathlib import Path
import json
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_core.i18n import _ as _t
from platform_core.storage import CLOUDFLARE_BODY_LIMIT, Storage, StorageError

from .tables import (ASSET_CORRUPT, ASSET_EXPIRED, ASSET_MISSING, ASSET_OK,
                     KINDS, KIND_ANH, KIND_PHU_DE, AsvAsset)

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


#: Doc theo khoi 1 MiB. Du lon de khong ton syscall, du nho de mot tep 4 GB
#: khong bao gio ton hon 1 MiB RAM cua tien trinh.
KHOI_DOC = 1024 * 1024


def bam_tep(duong: str | Path) -> str:
    """sha256 cua MOT TEP, doc theo dong chay. **Dung ham nay cho media.**

    ⛔ `bam(Path(x).read_bytes())` nap TOAN BO tep vao RAM chi de bam no. Voi
       tran 90 MB cua V2 thi con song duoc; voi duong tai len ben vung cua V4
       (toi 2 GiB, `upload_sessions`) thi mot lan chay lam boc hoi 2 GiB RAM cua
       worker — va co N worker.

    ⭐ Va no khong hien ra nhu mot loi: tep van bam dung, van tay van khop, chi
       la may bat dau swap khi hai lan chay trung nhau. Do la ly do
       `V4_RESOURCE_CPU_GPU_POLICY` goi dich danh viec nay ra:
       *"never `Path.read_bytes()` multi-GB solely to hash"*.

    Ket qua **bang het** `bam(duong.read_bytes())` cho cung mot tep — hai duong
    khong the lech, va `tests/test_429` chot dieu do tren nhieu kich thuoc, ke ca
    tep rong va tep lon hon mot khoi.
    """
    h = hashlib.sha256()
    with open(duong, "rb") as f:
        while True:
            khoi = f.read(KHOI_DOC)
            if not khoi:
                break
            h.update(khoi)
    return h.hexdigest()


def nguon_soi_duoc(kho: Storage, khoa: str, *, ttl_s: int = 3600) -> str:
    """Mot thu `ffprobe` doc duoc, **khong tai tep ve**.

    Hai backend, hai cau tra loi, va ca hai deu da co san o `platform_core`:

        LocalStorage -> `local_path()`  duong dan tren dia
        R2Storage    -> `url_for()`     presigned GET; ffprobe doc bang range request

    🔑 `platform_core/media.py:81 is_remote_source` va docstring cua no da ghi ro
       vi sao dieu nay dang lam: *"voi R2, nguon LA mot presigned URL va ffprobe
       chi tai vai khoi dau bang range request. Vong qua no bang cach tai ca tep
       ve la dung thu H10 sinh ra de tranh — mot video 2 GB di qua tunnel chi de
       doc mot con so."*

    ⇒ Day khong phai nang luc moi. Day la mot nang luc da co ma Auto Scan chua
      dung, va `nhap_media.soi` von da truyen thang tham so cho `ffprobe` nen no
      nhan URL ma khong can sua mot dong nao.

    ⛔ Nem neu khong backend nao tra loi duoc. Im lang tai ca tep ve la dung
       hanh vi ma ham nay ton tai de khong lam.
    """
    duong = kho.local_path(khoa) if hasattr(kho, "local_path") else None
    if duong:
        return duong
    url = kho.url_for(khoa, ttl_s=ttl_s) if hasattr(kho, "url_for") else None
    if url:
        return url
    raise AssetError(
        f"kho khong cho ra duong dan lan URL cho {khoa} — khong soi duoc ma "
        f"khong tai ve")


def do_va_bam(kho: Storage, khoa: str) -> tuple[int, str]:
    """`(co, checksum)` cua mot artifact, doc THEO KHOI tu kho.

    ⛔ `_doc_het` nap ca artifact vao RAM. Voi `transcript.json` do la vai chuc
       KB va khong sao; voi `final.mp4` do la ca cuon phim, va no xay ra o MOI
       lan kiem toan ven cua MOI lan chay.

    ⭐ Va cai gia khong hien ra nhu mot loi: phep kiem van dung, van tay van
       khop, chi la worker phinh len bang kich thuoc san pham no vua lam ra.
    """
    h = hashlib.sha256()
    co = 0
    f = kho.open(khoa)
    try:
        while True:
            khoi = f.read(KHOI_DOC)
            if not khoi:
                break
            co += len(khoi)
            h.update(khoi)
    finally:
        f.close()
    return co, h.hexdigest()


def tran_nhac_nen_byte() -> int:
    """Tran mot tep nhac nen (V3, `asv-nhac`) khach tu tai len.

    ⭐ Khuon `features.tran_logo_byte()`: LAY TU chinh sach nen tang, khong go
       tay mot so thu hai — `platform_core.storage.CLOUDFLARE_BODY_LIMIT` la
       tran than HTTP THAT cua Cloudflare Tunnel (100 MB), da dung cho video
       o nhieu app khac (`autosubvideo`/`taoclipngan`/`upscalevideo`/
       `qualitylab`). Mot ban sao rieng o day la mot con so se troi khi
       chinh sach do doi, va troi im lang.

    ⛔ Ham nay KHONG tu no chan duoc tep qua tran — do la viec cua duong upload
       (chua noi day, xem `logo.gan_vao_run`/`doc_tu_bieu_mau` — dung lai DUONG
       do, dung viet mot duong thu hai). No chi la MOT nguon cho cai tran, de
       duong do khoi tu bia mot con so khac.
    """
    return int(CLOUDFLARE_BODY_LIMIT)


def kiem_hop_le(kho: Storage, khoa: str, *, kind: str) -> tuple[int, str]:
    """Kiem noi dung theo `kind`. Tra `(co, checksum)`. Nem neu khong dat.

    ⛔ Mot tep 0 byte la KHONG hop le voi moi loai. Do la hinh dang thuong gap
       nhat cua mot lan chet giua chung: tep da duoc tao, chua kip ghi gi.
       De no qua nghia la mot giai doan bao DONE voi mot ket qua rong (I8).
    """
    if kind not in KINDS:
        raise AssetError(f"loai artifact khong biet: {kind!r}")

    # 🔑 Media di duong DONG CHAY, JSON/text doc het.
    #
    #    Khac biet khong phai tuy tien: phep kiem cua JSON la `json.loads`, va no
    #    can toan bo van ban. Phep kiem cua media la ffprobe tren mot TEP, khong
    #    phai tren mot chuoi bytes — nen nap no vao RAM khong phuc vu phep kiem
    #    nao ca, chi de bam va do do dai.
    if kind in ("video", "audio"):
        try:
            co, checksum = do_va_bam(kho, khoa)
        except StorageError as exc:
            raise AssetError(f"khong doc duoc artifact: {khoa}") from exc
        except FileNotFoundError as exc:
            raise AssetError(f"artifact khong ton tai: {khoa}") from exc
        if not co:
            raise AssetError(f"artifact rong: {khoa}")
        _kiem_media(kho, khoa, kind=kind)
        return co, checksum

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

    if kind == KIND_PHU_DE:
        # ⭐ Dung lai `nguon_loi.doc_srt` — bo doc SRT DUY NHAT cua app (no da
        #    doc phu de nhung o duong dinh tuyen nguon loi). Viet mot bo doc thu
        #    hai o day la mo mot cho cho hai cau tra loi lech nhau ve cung mot
        #    tep.
        from .nguon_loi import doc_srt

        try:
            van = du_lieu.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AssetError(f"artifact phu de khong phai UTF-8: {khoa}") from exc
        if not doc_srt(van):
            # ⛔ KHONG cho qua mot tep `.srt` khong co muc nao. Do la hinh dang
            #    cua "da viet tep, chua kip ghi cue" — dung loai that bai ma I8
            #    ton tai de chan, chi la no khong rong nen `not du_lieu` o tren
            #    khong bat duoc.
            raise AssetError(f"artifact phu de khong co muc nao: {khoa}")

    if kind == KIND_ANH:
        # 🔑 Kiem bang CHU KY + kich thuoc diem anh, khong bang duoi tep hay
        #    `content_type` da luu — ca hai deu do khach dat.
        #    `validate_reference` doc NOI DUNG va tra ve kieu THAT; no nem khi
        #    khong doc duoc.
        #
        # ⭐ Dung lai nen tang thay vi viet mot phep doc PNG/JPEG o day: han muc
        #    (8 MiB, 24 Mpx) la chinh sach cua NEN TANG, va mot ban sao la mot
        #    ban se troi.
        #
        # ⛔ Them mot `kind` moi ma khong them nhanh nay la mo mot loai artifact
        #    **khong ai soi noi dung** — tuc bat bien I8 (*"DONE nghia la co mot
        #    ket qua HOP LE"*) mat hieu luc cho dung loai do, va mat im lang.
        # 🔴 **`validate_reference(du_lieu, "")` TU CHOI MOI ANH — do duoc.**
        #
        #    Ham ay bat dau bang `if mime not in ALLOWED_REFERENCE_MIME: raise`,
        #    va `""` khong bao gio nam trong tap do. Nen nhanh nay khong phai
        #    "mot hang rao chat": no la mot hang rao **dong kin**, va moi logo
        #    khach dan deu chet o day.
        #
        # ⛔ Va no chet KHONG KEU o dung cho te nhat: `AssetError` khong phai
        #    `features.AsvError`, nen ca hai duong tao lan chay khong bat no va
        #    khach nhan mot trang **500**. Tinh nang logo chua tung chay het
        #    duong mot lan nao — "nang luc co, khong ai di tren duong" o dang
        #    nang nhat: duong bi chinh hang rao cua ta chan.
        #
        # ⭐ Sua bang cach SOI kieu tu NOI DUNG roi dua cho nen tang, ⛔ khong
        #    bang cach doc `content_type` da luu hay duoi tep: ca hai deu do
        #    khach dat, va do dung la dieu chu thich tren cam.
        #
        # ⚠️ Moi HAN MUC van thuoc nen tang (tap kieu cho phep, san 64x64, tran
        #    8 MiB / 24 Mpx, va chinh phep `verify()`). O day khong co mot con so
        #    nao — chi mot phep soi kieu.
        import io as _io

        from platform_core import image_input

        try:
            from PIL import Image as _Image

            with _Image.open(_io.BytesIO(du_lieu)) as _anh:
                _kieu = _Image.MIME.get(_anh.format or "", "")
            image_input.validate_reference(du_lieu, _kieu)
        except Exception as exc:            # noqa: BLE001 — dich sang loi cua ta
            raise AssetError(f"artifact anh khong hop le: {khoa}") from exc

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

def _do_toan_ven(kho: Storage, asset: AsvAsset) -> str:
    """DO trang thai toan ven — thuan doc, khong cham CSDL."""
    han = _aware(asset.expires_at)
    if han is not None and han <= _now():
        return ASSET_EXPIRED
    try:
        if not kho.exists(asset.storage_key):
            return ASSET_MISSING
        # Chi can do dai va checksum, khong can noi dung -> doc theo khoi.
        co, checksum = do_va_bam(kho, asset.storage_key)
    except (StorageError, FileNotFoundError):
        return ASSET_MISSING

    if co != int(asset.size) or checksum != asset.checksum:
        return ASSET_CORRUPT
    return ASSET_OK


def kiem_toan_ven(db: Session, kho: Storage, asset: AsvAsset) -> str:
    """Doi chieu ban ghi voi tep that. Cap nhat va tra ve `integrity`.

    Ba cau tra loi khac nhau, va gop chung lai la mat thong tin can de xu ly:
      `missing` — tham chieu con, tep bien mat  -> phai tinh lai
      `corrupt` — tep con, noi dung da lech     -> phai tinh lai VA dang ngo
      `expired` — chinh sach luu tru, khong phai su co

    🔴 **Ham nay la NGUON cua ca M-08 lan M-09, va ly do la mot dong `flush`.**

       No mang ten mot phep DOC (*"kiem"*) nhung no GHI: truoc 23/09 no dat
       `asset.integrity` roi `flush` — tuc mo mot transaction GHI tren phien
       cua worker va **khong dong lai**. Nguoi goi khong co ly do gi de doan
       ra dieu do tu ten ham.

       Cai bay no giang: `JobContext.progress` / `.event` / `.is_cancelled`
       (`platform_core/job_runner.py`) mo mot phien **THU HAI** theo thiet ke.
       Tren SQLite hai phien do gap nhau thanh `database is locked`:

         * M-08 — `COMPOSE`: `_khoa_con_dung` -> `kiem_toan_ven` -> `flush`,
           roi `ctx.progress(60)`;
         * M-09 — `VOICE_SYNTHESIS`: `_doan_con_dung` -> `kiem_toan_ven` ->
           `flush`, roi nhanh `continue` (doan dung lai duoc) **bo qua**
           `db.commit()` cuoi vong, nen lan `ctx.progress` cua vong lap KE TIEP
           dung vao dung khoa do. Vi the no chi lo ra o VONG SUA: chi khi ay
           artifact moi bi `vo_hieu_theo_day_chuyen` dat `missing` va phep do
           nay moi co gi de GHI lai.

       M-08 vá tai MOT trong nam nguoi goi. Nam nguoi goi thi bon cai bay con
       lai van nguyen, va M-09 chinh la cai thu hai no bo xuong.

    ⭐ Nen phep do tach khoi phep ghi, va phep ghi chiu hai rang buoc:

      1. **Khong doi thi khong ghi.** Duong lanh (artifact van `ok`) nay la
         thuan doc — phien cua nguoi goi khong bao gio bi mo transaction ghi vi
         mot cau hoi ma cau tra loi la "khong co gi moi".
      2. **Doi thi COMMIT, khong `flush`.** Day la mot quan sat ve THE GIOI
         ("tep nay bien mat"), khong phai mot manh cua don vi viec nguoi goi
         dang lam: no dung ke ca khi giai doan sau do hong va bi `rollback`.
         Do cung la luat ma `thi_hanh.chay_giai_doan` ghi trong nhanh bat loi
         cua no — *"diem chot da `commit` ... do la ca ly do chung `commit`
         ngay tai cho thay vi `flush`"*.

    ⛔ Khong dung mot phien RIENG cho lan ghi nay. Phien cua nguoi goi vua
       SELECT chinh dong nay nen tren SQLite no dang giu khoa doc; mot phien
       thu hai xin khoa ghi se **doi chinh no** — dung cai bay vua go, dat
       nguoc chieu.
    """
    moi = _do_toan_ven(kho, asset)
    if str(asset.integrity or "") != moi:
        asset.integrity = moi
        db.commit()
    return moi


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

    🔴 **Ham nay tung khong bao gio tra ve mot lan trung nao, va no hong o HAI
       tang chu khong mot (B23-01).**

    Tang mot: no loc bang `f"/{van_tay}." in storage_key` voi mot van tay 64 ky
    tu, trong khi `dat_khoa` cat con `DAI_VAN_TAY_TRONG_KHOA = 32` ky tu khi
    dung ten tep. Mot chuoi 64 ky tu khong the nam trong mot khoa chi chua 32 ky
    tu dau.

    Tang hai — va day moi la tang khong sua duoc bang cach cat cho khop: khoa
    mang van tay cua **TUNG ARTIFACT**, khong phai van tay cua GIAI DOAN. Do
    that: mot lan `media_prepare` ghi **hai** artifact duoi **hai** van tay khac
    nhau (`source_probe.json` va `audio_full.wav`), va `promote_va_ghi` nhan
    `van_tay=phan["van_tay"] or vt` — tuc moi phan tu dat ten khoa cua rieng no.
    Nen **khong** gia tri don nao trong `storage_key` tra loi duoc cau hoi ta
    dang hoi.

    ⇒ Bo han phep so khop chuoi. Cau hoi *"giai doan nay da chay xong voi dung
      van tay nay chua"* da co mot cho tra loi dung: `AsvStage.fingerprint`,
      chinh la thu `features.danh_dau_xong` ghi lai. Va danh sach artifact cua
      no da nam trong `outputs["khoa_asset"]`.

    ⭐ Doi lai, ham nay manh hon truoc theo mot chieu quan trong: no khong con
       doan tu ten tep nua. Mot khoa doi cach dat ten khong lam cache im lang
       chet lan nua.
    """
    from .tables import STAGE_SUCCEEDED, AsvStage

    gd = db.execute(select(AsvStage).where(
        AsvStage.run_id == run_id,
        AsvStage.stage == stage)).scalar_one_or_none()
    if gd is None or gd.status != STAGE_SUCCEEDED:
        return None
    if not van_tay or str(gd.fingerprint or "") != str(van_tay):
        return None

    khoa = [str(k) for k in ((gd.outputs or {}).get("khoa_asset") or [])]
    if not khoa:
        return None

    hang = list(db.execute(
        select(AsvAsset).where(AsvAsset.owner_id == owner_id,
                               AsvAsset.run_id == run_id,
                               AsvAsset.storage_key.in_(khoa))).scalars())
    # ⛔ Thieu MOT artifact la cache khong dung duoc — khong phai "dung phan con
    #    lai". Mot giai doan giao ba tep va ta tra ve hai la mot lan hong o ha
    #    nguon, xa cho gay ra no.
    if len(hang) != len(set(khoa)):
        return None
    for a in hang:
        if kiem_toan_ven(db, kho, a) != ASSET_OK:
            return None
    return hang


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


def quet_het_han(db: Session, kho: Storage, *, moc=None, toi_da: int = 500) -> int:
    """Xoa nhung artifact DA QUA `expires_at`. Tra ve so tep da xoa.

    🔴 **Truoc pha 27 khong ham nao lam viec nay, va `expires_at` chua tung
       duoc mot cau lenh nao doc de xoa.** `HAN_TRUNG_GIAN = 30 ngay` duoc dong
       len moi artifact, `kiem_toan_ven` bao `expired`, va roi khong gi xay ra.
       Mot chinh sach luu tru duoc khai ma khong co bo quet doc len nhu mot loi
       hua — va no con to hon mot loi hua: no lam bao cao kiem toan noi "expired"
       ve nhung tep van dang nam nguyen tren dia va van dang tinh tien luu tru.

    ⛔ **KHONG dung `don_theo_run` cho viec nay.** Ham do xoa MOI artifact cua
       mot lan chay — ke ca ban giao cho khach. Bo quet nay chi cham nhung dong
       co `expires_at` da qua, tuc dung nhung ban trung gian; ban giao duoc
       promote voi `han=None` nen no khong co ngay het han de qua.

    ⚠️ `toi_da` chan tren MOT luot: bo quet chay trong vong bao tri cua worker
       (moi gio), va mot luot xoa hang chuc nghin tep se giu lease `bao_tri`
       qua lau va chan moi viec nen khac. Con lai se duoc don o luot sau.
    """
    moc = _aware(moc) if moc is not None else _now()
    hang = list(db.execute(
        select(AsvAsset)
        .where(AsvAsset.expires_at.is_not(None), AsvAsset.expires_at <= moc)
        .order_by(AsvAsset.expires_at)
        .limit(max(1, int(toi_da)))).scalars())
    dem = 0
    for a in hang:
        try:
            kho.delete(a.storage_key)
            dem += 1
        except (StorageError, FileNotFoundError):
            # Da bien mat roi thi khong con gi de xoa — nhung DONG thi van phai
            # di, neu khong luot sau se lai doc dung no va lai khong xoa duoc gi.
            pass
        db.delete(a)
    db.flush()
    return dem


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
