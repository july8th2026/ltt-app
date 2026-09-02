"""Than thi hanh dung chung cua mot giai doan — BE MAT CONG KHAI cua app nay.

## Vi sao tep nay ton tai

Ba app, mot san pham (ADR-001 D5). Hai executor an (`asv_media`, `asv_gpu`) phai
chay cung mot vong doi giai doan: doc run co pham vi chu so huu -> tinh van tay
-> lam viec -> kiem tran chi -> ghi checkpoint.

Ban dau `asv_gpu` import thang `_chay_giai_doan` tu `asv_media`.
`tools/lint_app_contract.py` chan lai, va no **dung**: mot cai ten mo dau bang
gach duoi la mot loi hua rieng tu, va mot app voi tay vao ruot app khac de lay
no la dung thu hop dong app sinh ra de chan. Trieu chung se den muon — ngay
`asv_media` doi chu ky ham do vi ly do cua rieng no.

⇒ Than dung chung nam o **app cha**, la noi so huu mo hinh run/stage, va duoc
   khai la be mat cong khai trong `apps/auto_scan_video/__init__.py`. Hai
   executor chi con la lop dinh tuyen mong.

⭐ Ghi lai vi day la mot linter bat duoc mot loi THIET KE chu khong phai mot loi
   danh may.
"""
from __future__ import annotations

import hashlib
import io
import json

from platform_core.db import get_session
from platform_core.storage import get_storage

from . import (assets, features, giai_doan_am_thanh, giai_doan_ban_dung,
               giai_doan_chep_loi, giai_doan_giong, giai_doan_ket_xuat,
               giai_doan_media, giai_doan_noi_dung, giai_doan_thoi_gian,
               pipeline)
from .tables import STAGE_SUCCEEDED

#: Chi phi do duoc gia cua mot giai doan o pha 05. Bang 0 vi khong provider nao
#: bi goi va khong card nao bi dung.
#:
#: ⭐ Duong ghi chi phi van chay THAT (giai doan ghi `credit_actual`, run cong
#:    don, quyet toan doc tong) — chi con so la 0. Nho vay pha 08+ chi phai doi
#:    mot con so, khong phai dung mot duong moi.
CHI_PHI_GIA = 0


#: Phien ban cua ENGINE GIA. Giai doan chua co engine that dung so nay, va no
#: PHAI doi khi engine that thay cho no — neu khong, moi ket qua gia da luu se
#: duoc coi la cache hop le cho engine moi.
PHIEN_BAN_ENGINE_GIA = 0


def phien_ban_engine(stage_ten: str) -> str:
    """Phien ban ENGINE cua mot giai doan — phan da thieu trong van tay tu pha 05.

    🔴 `van_tay` ban pha 05 chi gom `(stage, contract, settings, dau_vao)`, va
       docstring cua chinh no ghi mon no nay: *"Pha 08+ **phai** them chung —
       thieu chung thi nang model len ban moi se dung lai ket qua cu, im lang."*
       Mon no do di qua bay pha ma khong ai tra, vi khong co gi bao no thieu.

    ⭐ Cai lam no lo ra la mot phep kiem cua pha 15
       (`test_415::test_doi_cach_dung_lenh_thi_van_tay_PHAI_doi`): nang
       `PHIEN_BAN_KET_XUAT` roi chay lai, va ket qua **khong doi** — tuc mot ban
       va cho trinh render da duoc giao nhung se khong bao gio chay, vi moi lan
       chay lai deu tra ve tep cu tu cache.

    ⚠️ Import ben trong ham, khong o dau tep: `thi_hanh` duoc ba app vo thi hanh
       nap, va keo ca cay module engine vao luc import se bat mot worker chi
       chay lan `api` phai co du moi thu cua lan `gpu`.
    """
    if stage_ten == pipeline.MEDIA_PREPARE:
        from . import nhap_media
        return f"chuan_hoa/{nhap_media.PHIEN_BAN_CHUAN_HOA}"
    if stage_ten == pipeline.AUDIO_PREPARE:
        from . import tach_tieng
        return f"tach/{tach_tieng.PHIEN_BAN_TACH}"
    if stage_ten == pipeline.TRANSCRIBE:
        from . import giai_doan_chep_loi
        return f"chep_loi/{giai_doan_chep_loi.PHIEN_BAN_MA}"
    if stage_ten == pipeline.CONTENT_PROCESS:
        from . import dich_thuat, van_ban
        # Provider + model nam trong nay: doi model dich la doi san pham, va
        # mot lan doi lang le nghia la khach nhan mot ban dich khac.
        return (f"noi_dung/{van_ban.PHIEN_BAN_LOI_NHAC}"
                f"/{dich_thuat.PROVIDER_CHINH}/{dich_thuat.MODEL_CHINH}")
    if stage_ten == pipeline.VOICE_SYNTHESIS:
        from . import giong_noi
        return f"giong/{giong_noi.PHIEN_BAN_GIONG}"
    if stage_ten == pipeline.TIMING_ALIGN:
        from . import thoi_gian
        return f"thoi_gian/{thoi_gian.PHIEN_BAN_THOI_GIAN}"
    if stage_ten == pipeline.COMPOSE:
        from . import ban_dung
        return f"ban_dung/{ban_dung.PHIEN_BAN_BAN_DUNG}"
    if stage_ten == pipeline.RENDER:
        from . import ket_xuat
        return f"ket_xuat/{ket_xuat.PHIEN_BAN_KET_XUAT}"
    # ⚠️ Giai doan chua co engine that van phai co MOT phien ban, khong duoc tra
    #    chuoi rong. Tra rong nghia la "khong co gi de lam moi cache", va do la
    #    dung mon no ma ham nay sinh ra de tra — chi doi cho.
    #
    #    Khi pha 18 thay engine gia cua QC bang engine that, chuoi nay doi tu
    #    `gia/0` sang mot thu khac, va moi ket qua QC cu bi vo hieu **dung nhu
    #    mong doi**. `tests/test_416` chot TAP HOP giai doan con dung engine gia,
    #    nen luot do khong the quen cap nhat cho nay.
    return f"gia/{PHIEN_BAN_ENGINE_GIA}"


def van_tay(stage_ten: str, run, dau_vao: dict) -> str:
    """Van tay hieu luc cua mot giai doan (ADR-001 D8).

    Gom bon thu cua ban pha 05 **cong** phien ban engine (xem `phien_ban_engine`).
    Thieu manh cuoi thi nang engine len ban moi se dung lai ket qua cu, im lang —
    dung kieu hong ma O13 sinh ra de chan: "co mot tep ten dung" khong phai la
    mot cache hop le.
    """
    goi = json.dumps({
        "stage": stage_ten,
        "contract": run.contract_version,
        "settings": run.settings or {},
        "dau_vao": dau_vao,
        "engine": phien_ban_engine(stage_ten),
    }, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(goi.encode("utf-8")).hexdigest()


def _gom_dau_vao(db, run_id: str, ten: str) -> dict:
    """Tham chieu output cua cac giai doan truoc — phan LINEAGE cua van tay.

    Vi sao dua ca VAN TAY cua giai doan truoc vao chu khong chi ten tep: neu mot
    giai doan thuong nguon chay lai va cho ket qua khac, van tay cua no doi, nen
    van tay cua giai doan nay cung doi va cache cu bi vo hieu **theo day chuyen**
    (I10). Chi so ten tep thi khong bat duoc dieu do.
    """
    g = pipeline.THEO_TEN[ten]
    ra: dict = {}
    for truoc in g.sau:
        s = features.giai_doan_theo_ten(db, run_id, truoc)
        ra[truoc] = {"fingerprint": s.fingerprint if s else "",
                     "outputs": (s.outputs if s else {}) or {}}
    return ra


def _khoa_cha(db, run_id: str, ten: str) -> list[str]:
    """Khoa luu tru cua artifact ma giai doan nay dan xuat tu — LINEAGE that.

    Khac `_gom_dau_vao` (thu vao van tay): day la thu ghi xuong `AsvAsset.parent_keys`
    de mot nguoi doc du lieu sau nay lan nguoc duoc day chuyen ma khong phai
    doc lai ma nguon.
    """
    g = pipeline.THEO_TEN[ten]
    ra: list[str] = []
    for truoc in g.sau:
        s = features.giai_doan_theo_ten(db, run_id, truoc)
        for khoa in ((s.outputs or {}).get("khoa_asset") or []) if s else []:
            ra.append(khoa)
    return ra


def chay_giai_doan(ten: str, params: dict, ctx=None) -> dict:
    """Chay MOT giai doan. Be mat cong khai cho hai executor an.

    Vong doi o day la ban PHA 05: cong viec ben trong la gia. Cai that la doc co
    pham vi chu so huu, van tay + lineage, chot tran chi, va ghi checkpoint.
    """
    run_id = str(params.get("run_id") or "")
    owner_id = str(params.get("owner_id") or "")
    if not run_id or not owner_id:
        raise ValueError("thieu run_id/owner_id")

    gen = get_session()
    db = next(gen)
    try:
        # 🔑 Doc CO PHAM VI CHU SO HUU, ke ca trong worker. `owner_id` den tu
        #    params do chinh dieu phoi ghi ra, khong phai tu client — nhung phep
        #    loc van phai co: mot params bi dung san la duong tan cong duy nhat
        #    con lai o tang nay (I6).
        run = features.lay_run(db, run_id, owner_id)
        stage = features.giai_doan_theo_ten(db, run_id, ten)
        if stage is None:
            raise ValueError(f"run {run_id} khong co giai doan {ten}")
        if stage.status == STAGE_SUCCEEDED:
            # Nhat lai mot job da xong: khong lam lai, khong tinh tien lai.
            return {"stage": ten, "ghi_chu": "da xong tu truoc"}

        # Huy giua chung (I13). Hop tac, khong cuong che.
        if ctx is not None and getattr(ctx, "is_cancelled", None) and ctx.is_cancelled():
            return {"stage": ten, "ghi_chu": "da huy"}

        vt = van_tay(ten, run, _gom_dau_vao(db, run_id, ten))
        kho = get_storage()

        # ── Cache: van tay khop VA artifact con song (I10) ─────────────────
        cu = assets.cache_dung_duoc(db, kho, owner_id=owner_id, run_id=run_id,
                                    stage=ten, van_tay=vt)
        if cu:
            features.danh_dau_xong(
                db, stage, fingerprint=vt, credit_actual=0,
                outputs={"stage": ten, "khoa_asset": [a.storage_key for a in cu],
                         "tu_cache": True})
            db.commit()
            return {"stage": ten, "fingerprint": vt, "credit_cost": 0,
                    "tu_cache": True}

        # Chot BAT BUOC truoc moi lan ton tien (ADR-001 D4).
        features.kiem_tran_chi(db, run, CHI_PHI_GIA)

        # ── Buoc 1: engine ────────────────────────────────────────────────
        if ten == pipeline.MEDIA_PREPARE:
            ra = giai_doan_media.chay(db, kho, run=run, ctx=ctx)
        elif ten == pipeline.AUDIO_PREPARE:
            ra = giai_doan_am_thanh.chay(db, kho, run=run, ctx=ctx)
        elif ten == pipeline.TRANSCRIBE:
            ra = giai_doan_chep_loi.chay(db, kho, run=run, ctx=ctx)
        elif ten == pipeline.CONTENT_PROCESS:
            ra = giai_doan_noi_dung.chay(db, kho, run=run, ctx=ctx)
        elif ten == pipeline.VOICE_SYNTHESIS:
            ra = giai_doan_giong.chay(db, kho, run=run, ctx=ctx)
        elif ten == pipeline.TIMING_ALIGN:
            ra = giai_doan_thoi_gian.chay(db, kho, run=run, ctx=ctx)
        elif ten == pipeline.COMPOSE:
            ra = giai_doan_ban_dung.chay(db, kho, run=run, ctx=ctx)
        elif ten == pipeline.RENDER:
            ra = giai_doan_ket_xuat.chay(db, kho, run=run, ctx=ctx)
        else:
            ra = _engine_gia(kho, run_id=run_id, owner_id=owner_id, ten=ten,
                             van_tay=vt)

        # ── Buoc 2→4: kiem hop le -> promote -> ghi tham chieu + van tay ───
        khoa_ra: list[str] = []
        for phan in ra["phan"]:
            asset = assets.promote_va_ghi(
                db, kho, owner_id=owner_id, run_id=run_id, stage=ten,
                van_tay=phan.get("van_tay") or vt, kind=phan["kind"],
                duoi=phan["duoi"], staging_key=phan["staging_key"],
                parent_keys=_khoa_cha(db, run_id, ten))
            khoa_ra.append(asset.storage_key)

        features.danh_dau_xong(
            db, stage, fingerprint=vt, credit_actual=CHI_PHI_GIA,
            outputs={"stage": ten, "khoa_asset": khoa_ra,
                     **(ra.get("tom_tat") or {})})
        # ── Buoc 5 ────────────────────────────────────────────────────────
        db.commit()
        return {"stage": ten, "fingerprint": vt, "credit_cost": CHI_PHI_GIA,
                "khoa_asset": khoa_ra}
    finally:
        db.close()


def _engine_gia(kho, *, run_id: str, owner_id: str, ten: str, van_tay: str) -> dict:
    """Cong viec gia cho cac giai doan CHUA co engine that (pha 09+ thay dan).

    Van di qua dung duong ma giai doan that di: ghi mot tep staging, roi de
    nguoi goi kiem hop le va promote. Nho vay khi engine that vao, thu doi la
    **noi dung**, khong phai duong di.
    """
    noi_dung = json.dumps({"stage": ten, "run": run_id, "gia": True,
                           "van_tay": van_tay}, sort_keys=True).encode("utf-8")
    khoa_tam = assets.khoa_staging(owner_id=owner_id, run_id=run_id,
                                   stage=ten, van_tay=van_tay, duoi="json")
    kho.put(khoa_tam, io.BytesIO(noi_dung), content_type="application/json")
    return {"phan": [{"staging_key": khoa_tam, "kind": "json", "duoi": "json"}]}


def chay_theo_job_type(job_type: str, params: dict, ctx=None) -> dict:
    """Tra `job_type` -> giai doan roi chay. Cua vao cua ca hai executor."""
    giai_doan = pipeline.THEO_JOB_TYPE.get(str(job_type or ""))
    if giai_doan is None:
        raise ValueError(f"khong giai doan nao nhan job_type {job_type!r}")
    return chay_giai_doan(giai_doan.ten, params, ctx)
