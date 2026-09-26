"""Cache DUNG CHUNG xuyen lan chay — V6 pha 25.

Cache cu (`assets.cache_dung_duoc`) chi tra loi *"giai doan nay CUA LAN CHAY
NAY da xong voi dung van tay chua"*. Khach nop lai CUNG mot video (doi giong,
doi preset, sua mot chu trong tu dien) thi tach nguon va chep loi — hai thu dat
nhat ma khong phu thuoc gi vao nhung thay doi do — chay lai tu dau.

🔴 **Van tay giai doan KHONG dung lam khoa xuyen lan chay duoc, va dung no la
   tham hoa chu khong phai toi uu kem.** `thi_hanh.van_tay` gom stage + hop dong +
   TOAN BO settings + dau ra thuong nguon + engine — nhung **khong co danh tinh
   noi dung nguon**. Hai video khac nhau, cung settings, se ra cung mot van tay
   o `media_prepare`, va mot tra cuu xuyen lan chay theo van tay do se giao ban
   chep loi cua video A cho video B.

⭐ Nen khoa o day la **dia chi noi dung**: checksum cua DUNG tep ma giai doan doc,
   cong DUNG nhung thiet lap ma giai doan doc — khong hon, khong kem. Thieu mot
   thiet lap thi dung sai; thua mot thiet lap thi mat cache ma khong ai biet.
   `test_478` chot tap thiet lap ay bang AST, nen them mot phep doc `cd.doc(run)`
   vao giai doan ma quen them vao khoa se lam gate do.

🔑 **Chu so huu nam TRONG khoa va trong menh de WHERE** (I19, cung ly do nhu
   `assets.cache_dung_duoc`). Hai khach tai len cung mot video van la hai lan
   tinh: checksum trung la mot su that ve noi dung, khong phai giay phep doc
   artifact cua nguoi khac — va neu tra loi khac nhau theo "co trung hay khong"
   thi chinh thoi gian phan hoi da ro ri rang nguoi kia co tep ay.

🔑 **Dung lai bang cach CHEP, khong bang cach tro.** Artifact duoc chep vao khoa
   staging cua lan chay moi roi di qua `promote_va_ghi` nhu mot ket qua engine
   binh thuong. Hai lan chay giu hai vong doi doc lap: xoa lan chay A
   (`don_theo_run`) khong duoc lam hong lan chay B dang tro vao tep cua A.

⭐ *Mot tinh, cac ben kia cho* (asv-final, `L_CACHE_LEASE.md`): `giu_cho` gianh
   lease NEN TANG (`platform_core.leases`, bang `singleton_leases`) theo
   `khoa_chung`. Ben den sau KHONG ngu trong worker: no nem `jobs.DangBan`, worker
   `defer_resource` job ve hang doi (khong tieu luot thu, khong cham tien), va
   luot sau no tim thay ket qua qua `lay`. Chu lease chet ⇒ het nhip ⇒ lease het
   han sau `TTL_GIU_CHO`; chu bi huy ⇒ thoi dap nhip ⇒ nhu chet.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from datetime import timedelta

from sqlalchemy import select

from platform_core import leases
from platform_core.db import get_session
from platform_core.jobs import DangBan
from platform_core.models import SingletonLease
from platform_core.storage import Storage

from . import assets, features, pipeline

log = logging.getLogger(__name__)

#: Doi so nay la vo hieu MOI khoa dung chung da ghi. Nang khi doi cach dung khoa
#: hoac khi mot giai doan duoc chia se bat dau doc them mot dau vao.
PHIEN_BAN_CACHE_CHUNG = 3      # 2 (22/09): TRANSCRIBE doc them video nguon (dinh tuyen)
                               # 3 (26/09): AUDIO_PREPARE doc them ho so BA LOP
                               #   (`lop`, B2) — xem `dau_vao_noi_dung` ben duoi

#: Giai doan duoc chia se. Chi nhung giai doan (a) dat — GPU/CPU nang — va (b) co
#: dau vao noi dung xac dinh duoc. `media_prepare` re va la cho TINH checksum;
#: tu `edit_plan` tro xuong dau ra phu thuoc settings cua tung lan chay.
GIAI_DOAN_CHUNG = (pipeline.AUDIO_PREPARE, pipeline.TRANSCRIBE)

#: Tran so dong ung vien doc cho mot lan tra cuu — mot khach, mot giai doan.
SO_UNG_VIEN_TOI_DA = 200

#: Khoa cua `outputs` KHONG phai tom tat cua engine: chep chung sang lan chay moi
#: se tro sai (khoa asset cua lan chay khac) hoac tu nhan sai nguon goc.
_KHONG_CHEP = frozenset({"stage", "khoa_asset", "khoa_chung", "tu_cache",
                         "tu_cache_chung"})

_KIEU_NOI_DUNG = {"audio": "audio/wav", "json": "application/json"}


def _checksum_tieng_asr(db, run) -> str:
    """Checksum cua DUNG ban tieng `transcribe` se doc, lay tu `AsvAsset`.

    🔑 Dung tep ma giai doan doc (`_khoa_tieng_asr` — ban 16 kHz cua
       MEDIA_PREPARE), khong phai dau ra cua `audio_prepare` dung truoc no trong
       do thi. Khoa theo mot tep giai doan KHONG doc la khoa theo mot thu co the
       doi ma ket qua khong doi, hoac nguoc lai.
    """
    from .giai_doan_chep_loi import ThieuBanTieng, _khoa_tieng_asr

    try:
        khoa = _khoa_tieng_asr(db, run)
        return str(assets.asset_cua(db, khoa, run.owner_id).checksum or "")
    except (ThieuBanTieng, assets.AssetError):
        return ""


def dau_vao_noi_dung(db, run, ten: str) -> dict | None:
    """Thu THAT SU quyet dinh dau ra cua giai doan, hoac None neu khong chia se."""
    if ten == pipeline.AUDIO_PREPARE:
        # `audio_prepare` doc thang `run.source_key`; checksum cua chinh tep do
        # da duoc MEDIA_PREPARE tinh (`giai_doan_media`) va ghi vao tom tat.
        media = features.giai_doan_theo_ten(db, run.id, pipeline.MEDIA_PREPARE)
        ck = str(((media.outputs if media else None) or {}).get("checksum_nguon") or "")
        if not ck:
            return None
        # 🔴 B2 (25/09) them ho so BA LOP (`lop`): `giai_doan_am_thanh.chay` doc
        #    no de biet gain tung lop luc TRON nen (`tach_tieng.tron_nen`), nen
        #    ban nen (`bed.wav`) ra KHAC nhau theo `lop` du CUNG mot nguon.
        #    Thieu dong nay: hai lan chay cung video, khac gain, se dung chung
        #    MOT bed.wav — cua BAT KY lan nao chay truoc — va lan sau nhan sai
        #    am luong ma khong ai bao. `tu_cai_dat_lop` chuan hoa `None`/ho so
        #    THUA ve DUNG mot dang (khuon `van_tay_tach`), nen hai ho so tuong
        #    duong ve gia tri (vd `None` va ho so MAC_DINH day du) van chia se
        #    duoc, dung nhu tren mot lan chay don (`assets.cache_dung_duoc`).
        from . import cai_dat as cd
        from . import tach_tieng
        return {"nguon": ck, "lop": tach_tieng.tu_cai_dat_lop(cd.doc(run).lop)}
    if ten == pipeline.TRANSCRIBE:
        from . import cai_dat as cd, nguon_loi as nl
        from .giai_doan_chep_loi import MODEL_ASR

        ck = _checksum_tieng_asr(db, run)
        if not ck:
            return None
        cai = cd.doc(run)
        dv = {"tieng_asr": ck, "model": MODEL_ASR,
              "ngon_ngu_nguon": str(cai.ngon_ngu_nguon or ""),
              # TRANSCRIBE chot cap ngon ngu (ngon_ngu.kiem_nguon_da_doan);
              # dung lai cheo dich la bo qua phep chot do.
              "ngon_ngu_dich": cai.ngon_ngu_dich,
              # Dinh tuyen nguon loi (22/09): che do + engine OCR.
              "nguon_loi": nl.chuan_che_do(cai.nguon_loi),
              "dinh_tuyen": nl.PHIEN_BAN_DINH_TUYEN}
        if dv["nguon_loi"] != nl.ASR:
            # 🔑 Dinh tuyen DOC VIDEO (luong phu de, dai hardsub): ban tieng
            #    trung ma hinh khac (vd. cung am thanh, khac phu de dot) la
            #    ban ghi khac. Thieu checksum video ⇒ khong chia se.
            media = features.giai_doan_theo_ten(db, run.id, pipeline.MEDIA_PREPARE)
            ck_v = str(((media.outputs if media else None) or {}).get("checksum_nguon") or "")
            if not ck_v:
                return None
            dv["video"] = ck_v
        return dv
    return None


def khoa(db, run, ten: str, *, engine: str) -> str:
    """Khoa dung chung, hoac `""` khi giai doan khong chia se / thieu dau vao.

    `engine` do `thi_hanh.phien_ban_engine` dua vao: nang engine la vo hieu moi
    ket qua cu, dung nhu voi van tay trong mot lan chay.
    """
    if ten not in GIAI_DOAN_CHUNG:
        return ""
    dv = dau_vao_noi_dung(db, run, ten)
    if dv is None:
        return ""
    goi = json.dumps({"v": PHIEN_BAN_CACHE_CHUNG, "owner": run.owner_id,
                      "stage": ten, "contract": run.contract_version,
                      "engine": engine, "dau_vao": dv},
                     sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()


def _artifact_song(db, kho: Storage, *, owner_id: str, run_id: str,
                   khoa_asset: list[str]) -> list | None:
    """Artifact cua lan chay cho, THEO THU TU da ghi, neu MOI cai con song."""
    from .tables import AsvAsset

    if not khoa_asset:
        return None
    hang = {a.storage_key: a for a in db.execute(select(AsvAsset).where(
        AsvAsset.owner_id == owner_id, AsvAsset.run_id == run_id,
        AsvAsset.storage_key.in_(khoa_asset))).scalars()}
    # ⛔ Thieu MOT artifact la khong dung duoc — khong phai "dung phan con lai".
    if len(hang) != len(set(khoa_asset)):
        return None
    for a in hang.values():
        if assets.kiem_toan_ven(db, kho, a) != assets.ASSET_OK:
            return None
    # Giu THU TU cua `khoa_asset`; ha nguon lay "tep .wav dau tien".
    return [hang[k] for k in khoa_asset]


def lay(db, kho: Storage, *, run, ten: str, khoa_chung: str) -> dict | None:
    """Ket qua cua mot lan chay KHAC cung khach, cung khoa — dang `{"phan","tom_tat"}`.

    Tra ve dung hinh dang dau ra engine, nen `thi_hanh` promote + ghi lineage
    theo DUNG duong cua mot lan tinh that. None khi khong co gi dung lai duoc.
    """
    if not khoa_chung:
        return None
    from .tables import STAGE_SUCCEEDED, AsvStage

    ung_vien = db.execute(select(AsvStage).where(
        AsvStage.owner_id == run.owner_id, AsvStage.stage == ten,
        AsvStage.status == STAGE_SUCCEEDED, AsvStage.run_id != run.id)
        .order_by(AsvStage.finished_at.desc())
        .limit(SO_UNG_VIEN_TOI_DA)).scalars().all()
    for gd in ung_vien:
        ra = gd.outputs or {}
        if ra.get("khoa_chung") != khoa_chung:
            continue
        hang = _artifact_song(db, kho, owner_id=run.owner_id, run_id=gd.run_id,
                              khoa_asset=[str(k) for k in ra.get("khoa_asset") or []])
        if hang is None:
            continue
        phan = []
        for a in hang:
            # Ten tep cua lan cho la `{van_tay[:32]}.{duoi}`, da khac nhau tung
            # cai trong lan cho — giu nguyen nen hai tep cung noi dung (vd hai
            # stem im lang) khong de len nhau o khoa staging moi.
            van_tay, _, duoi = a.storage_key.rsplit("/", 1)[-1].rpartition(".")
            tam = assets.khoa_staging(owner_id=run.owner_id, run_id=run.id,
                                      stage=ten, van_tay=van_tay, duoi=duoi)
            with kho.open(a.storage_key) as f:
                kho.put(tam, f, content_type=_KIEU_NOI_DUNG.get(
                    a.kind, "application/octet-stream"))
            phan.append({"staging_key": tam, "kind": a.kind, "duoi": duoi,
                         "van_tay": van_tay})
        tom_tat = {k: v for k, v in ra.items() if k not in _KHONG_CHEP}
        tom_tat["tu_cache_chung"] = True
        log.info("cache chung: %s dung lai %d artifact", ten, len(phan))
        return {"phan": phan, "tom_tat": tom_tat}
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  Mot tinh, cac ben kia cho — lease NEN TANG theo `khoa_chung`
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔑 Dung lai `platform_core.leases` (bang `singleton_leases`, gianh bang INSERT +
#    UNIQUE, het han theo nhip) — khong co co che khoa thu hai. Chay giong het
#    tren SQLite va PostgreSQL.
# 🔑 Ben den sau KHONG ngu trong worker: nem `jobs.DangBan` ⇒ `job_runner`
#    `defer_resource` (job ve `queued`, `next_run_at` lui, KHONG tang `attempts`,
#    khong cham so tien). Dong `asv_stage` giu `running` + dung `job_id`, nen dieu
#    phoi vien khong nop job moi.
# ⚠️ Lease la TOI UU, khong phai chot dung sai: ket qua van di qua `lay` (chu so
#    huu trong WHERE + kiem toan ven). Mat lease giua chung chi lam hai ben cung
#    tinh — ton cong, khong sai. Vi vay loi ha tang lease ⇒ tinh khong lease.

#: Chu lease im nhip qua moc nay thi ben kia duoc thu hoi (crash/kill/mat dien).
TTL_GIU_CHO = timedelta(minutes=2)
#: Nhip dap cua chu lease — ngan hon TTL nhieu lan.
NHIP_GIU_CHO_S = 30.0
#: Tran thoi gian mot chu duoc giu lease. Handler treo ma tien trinh con song se
#: khong giu ben kia mai mai: qua moc nay thoi dap nhip, ben kia nhan sau TTL.
GIU_CHO_TOI_DA_S = 2 * 3600.0
#: Ben cho quay lai hoi sau bao lau. Re: mot luot hoi = mot claim + vai SELECT.
CHO_LAI_KHI_BAN_S = 15
#: `SingletonLease.name` la String(64).
_TIEN_TO_LEASE = "asvcc:"


def ten_lease(khoa_chung: str) -> str:
    return (_TIEN_TO_LEASE + khoa_chung)[:64]


def _phien():
    gen = get_session()
    db = next(gen)
    try:
        yield db
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


class GiuCho:
    """Lease dang giu + luong dap nhip. `nha()` idempotent."""

    def __init__(self, ten: str, holder: str, con_song=None):
        self.ten = ten
        self.holder = holder
        self._con_song = con_song
        self._dung = threading.Event()
        self._bat_dau = time.monotonic()
        self.luong = threading.Thread(target=self._nhip, daemon=True,
                                      name=f"asvcc-hb-{ten[6:14]}")

    def _lease(self) -> SingletonLease:
        # Doi tuong TAM: `leases.heartbeat/release` chi doc name + holder.
        return SingletonLease(name=self.ten, holder=self.holder)

    def _nhip(self) -> None:
        while not self._dung.wait(NHIP_GIU_CHO_S):
            if time.monotonic() - self._bat_dau > GIU_CHO_TOI_DA_S:
                log.warning("cache chung: %s giu qua %ss — thoi dap nhip",
                            self.ten, GIU_CHO_TOI_DA_S)
                return
            try:
                if self._con_song is not None and not self._con_song():
                    # Job chu da bi huy: thoi dap nhip ⇒ ben cho nhan sau TTL
                    # ke ca khi engine chua chiu dung.
                    log.info("cache chung: chu %s da huy — thoi dap nhip", self.ten)
                    return
                for db in _phien():
                    if not leases.heartbeat(db, self._lease()):
                        log.warning("cache chung: mat lease %s", self.ten)
                        return
            except Exception:                   # noqa: BLE001
                log.exception("cache chung: dap nhip lease %s loi", self.ten)

    def nha(self) -> None:
        if self._dung.is_set():
            return
        self._dung.set()
        if self.luong.is_alive() and self.luong is not threading.current_thread():
            self.luong.join(timeout=5)
        try:
            for db in _phien():
                leases.release(db, self._lease())
        except Exception:                       # noqa: BLE001
            log.exception("cache chung: khong nha duoc lease %s — het han sau TTL",
                          self.ten)


def giu_cho(khoa_chung: str, *, holder: str, con_song=None) -> GiuCho | None:
    """Gianh quyen TINH cho `khoa_chung`.

    Tra `GiuCho` (nguoi goi PHAI `nha()` trong `finally`), hoac None khi khong
    co khoa / ha tang lease loi (tinh khong lease — xem ghi chu dau muc).
    Nem `DangBan` khi lan chay khac dang tinh dung khoa nay.
    """
    if not khoa_chung:
        return None
    ten = ten_lease(khoa_chung)
    holder = str(holder or leases.holder_id())[:160]
    try:
        for db in _phien():
            lease = leases.acquire(db, name=ten, holder=holder, ttl=TTL_GIU_CHO)
    except Exception:                           # noqa: BLE001
        log.exception("cache chung: khong gianh duoc lease %s — tinh khong lease", ten)
        return None
    if lease is None:
        log.info("cache chung: %s dang duoc lan chay khac tinh — hoan job", ten)
        raise DangBan(f"cache chung: dang tinh o lan chay khac ({ten[:18]})",
                      retry_after_s=CHO_LAI_KHI_BAN_S)
    g = GiuCho(ten, holder, con_song)
    g.luong.start()
    return g
