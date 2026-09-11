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
import logging

from platform_core.db import get_session
from platform_core.i18n import _ as _t
from platform_core.storage import get_storage

from . import (assets, cache_chung, features, giai_doan_am_thanh, giai_doan_ban_dung,
               giai_doan_ban_bien_tap,
               giai_doan_chep_loi, giai_doan_giong, giai_doan_ket_xuat,
               giai_doan_media, giai_doan_noi_dung, giai_doan_qc, giai_doan_qc_ai,
               giai_doan_thoi_gian, loi, pipeline)
from .tables import STAGE_QUEUED, STAGE_RUNNING, STAGE_SUCCEEDED

log = logging.getLogger(__name__)

#: Chi phi do duoc gia cua mot giai doan o pha 05. Bang 0 vi khong provider nao
#: bi goi va khong card nao bi dung.
#:
#: ⭐ Duong ghi chi phi van chay THAT (giai doan ghi `credit_actual`, run cong
#:    don, quyet toan doc tong) — chi con so la 0. Nho vay pha 08+ chi phai doi
#:    mot con so, khong phai dung mot duong moi.
CHI_PHI_GIA = 0


class QcChan(ValueError):
    """Ban ra khong qua cong chat luong.

    ⛔ Loi cua **ket qua**, khong phai truot thoang qua: chay lai cung mot ban
       render cho cung mot phep do. `loi.py` xep no vao `NGUOI_DUNG` de nen tang
       khong thu lai ba lan mot phep do tat dinh.
    """


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
    if stage_ten == pipeline.QC_AI:
        # 🔑 Hai con so, hai thu doi doc lap: ma cua giai doan va loi
        #    nhac/luoc do o `qc_ai`. Doi loi nhac ma van tay khong doi thi
        #    lan chay lai dung y phan quyet cu — tuc mot ban va cho cach hoi
        #    model da duoc giao nhung se khong bao gio chay.
        from . import giai_doan_qc_ai, qc_ai
        return (f"qc_ai/{giai_doan_qc_ai.PHIEN_BAN_QC_AI_GD}"
                f"+loi_nhac/{qc_ai.PHIEN_BAN_QC_AI}")
    if stage_ten == pipeline.MEDIA_PREPARE:
        from . import nhap_media
        return f"chuan_hoa/{nhap_media.PHIEN_BAN_CHUAN_HOA}"
    if stage_ten == pipeline.AUDIO_PREPARE:
        from . import tach_tieng
        return f"tach/{tach_tieng.PHIEN_BAN_TACH}"
    if stage_ten == pipeline.TRANSCRIBE:
        from . import giai_doan_chep_loi
        return f"chep_loi/{giai_doan_chep_loi.PHIEN_BAN_MA}"
    if stage_ten == pipeline.EDIT_PLAN:
        from . import ban_bien_tap, canh, giai_doan_ban_bien_tap
        # 🔑 Ba con so, ba thu doi doc lap: ma cua giai doan, chinh sach cat, va
        #    nguong tach canh. Thieu bat ky cai nao thi doi no xong cache van
        #    khop, va lan chay dung lai mot ban bien tap sinh boi luat CU.
        return (f"ban_bien_tap/{giai_doan_ban_bien_tap.PHIEN_BAN_MA}"
                f"/{ban_bien_tap.PHIEN_BAN_BAN}/{canh.NGUONG_DOI_CANH}")
    if stage_ten == pipeline.CONTENT_PROCESS:
        from . import ai, van_ban
        # 🔴 **Hai dong nay tung doc mot module DA CHET, va hang so chung doc
        #    thi RONG.**
        #
        #    Chung doc `dich_thuat.PROVIDER_CHINH` / `MODEL_CHINH`, nhung pha 14
        #    da chuyen giai doan nay sang `ai.goi_tinh_tien`, va
        #    `dich_thuat.dich_ban_ghi` khong con nguoi goi nao tu do.
        #    `MODEL_CHINH` la chuoi rong — nen van tay cua **giai doan duy nhat
        #    tra tien cho mot model** khong chua danh tinh model nao.
        #
        # ⛔ Hau qua dung bang thu pha 08 them engine version de ngan: nang model
        #    len ban moi thi van tay khong doi, `_vo_hieu_giai_doan_da_lech`
        #    khong vo hieu gi, va cache tra lai ban dich sinh boi model CU — im
        #    lang. Va nguoc lai, sua cai hang so chet kia thi **lai** vo hieu
        #    ca cache ma khong co gi that su doi.
        #
        # 🔑 Hoi BAN DO SONG. `ai.ban_do_model` la thu that su duoc truyen cho
        #    `dieu_phoi.goi`, nen van tay va cu goi khong the lech nhau — chung
        #    doc cung mot nguon.
        ban_do = ai.ban_do_model(ai.CHUYEN_LOI_THOAI)
        # Sap xep de hai lan goi cho ra cung mot chuoi; mot dict khong on dinh
        # thu tu se lam van tay nhay va cache truot vo co.
        model = ",".join(f"{p}:{m}" for p, m in sorted(ban_do.items()))
        return f"noi_dung/{van_ban.PHIEN_BAN_LOI_NHAC}/{model}"
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
    if stage_ten == pipeline.QC:
        from . import qc
        return f"qc/{qc.PHIEN_BAN_QC}"
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


def giai_doan_lech_van_tay(db, run) -> list[str]:
    """Giai doan `succeeded` ma van tay da luu KHONG con khop dau vao hien tai.

    🔑 Prompt 16 muc 4 doi vo hieu theo phu thuoc, va day la nua **tu dong** cua
       no. Nua kia — `features.thu_lai_giai_doan` — la khi nguoi dung chu dong
       yeu cau. Nua nay bat truong hop khong ai yeu cau gi ca:

       mot giai doan thuong nguon chay lai (vd sau mot lan hong tam thoi) va cho
       ket qua **khac**. Van tay ha nguon doi theo, nen cache truot va no khong
       dung lai ket qua sai — nhung dong `asv_stage` cua no van ghi `succeeded`,
       va dieu phoi vien chi nop nhung giai doan CHUA succeeded. Ket qua: no
       khong bao gio chay lai, va lan chay ket thuc bang mot ban long tieng
       tron lan hai lan chay khac nhau.

    ⚠️ Doc, khong ghi. Nguoi goi quyet dinh lam gi — de phep kiem quan sat duoc
       "lech" tach roi khoi "da xu ly".
    """
    ra: list[str] = []
    for s in features.cac_giai_doan(db, run):
        if s.status != STAGE_SUCCEEDED or not s.fingerprint:
            continue
        if van_tay(s.stage, run, _gom_dau_vao(db, run.id, s.stage)) != s.fingerprint:
            ra.append(s.stage)
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

        # ── Cache DUNG CHUNG xuyen lan chay (V6 pha 25) ─────────────────────
        # 🔑 Khoa la DIA CHI NOI DUNG, khong phai `vt`: `vt` khong mang danh tinh
        #    nguon, nen hai video khac nhau cung settings trung `vt`. Xem
        #    `cache_chung.py`. Ket qua di qua DUNG duong promote ben duoi.
        # ⚠️ Chi o lan thu DAU. `attempt > 1` la khach bam "thu lai" (hoac mot lan
        #    engine vua hong): tra lai dung ket qua cu la lam ngo cau hoi. Lech ve
        #    phia TINH LAI, khong ve phia dung sai.
        kc = cache_chung.khoa(db, run, ten, engine=phien_ban_engine(ten))
        ra = (cache_chung.lay(db, kho, run=run, ten=ten, khoa_chung=kc)
              if int(stage.attempt or 0) <= 1 else None)

        # ── Buoc 1: engine ────────────────────────────────────────────────
        if ra is not None:
            pass    # da co tu cache dung chung — di thang toi promote
        elif ten == pipeline.MEDIA_PREPARE:
            ra = giai_doan_media.chay(db, kho, run=run, ctx=ctx)
        elif ten == pipeline.AUDIO_PREPARE:
            ra = giai_doan_am_thanh.chay(db, kho, run=run, ctx=ctx)
        elif ten == pipeline.TRANSCRIBE:
            ra = giai_doan_chep_loi.chay(db, kho, run=run, ctx=ctx)
        elif ten == pipeline.EDIT_PLAN:
            ra = giai_doan_ban_bien_tap.chay(db, kho, run=run, ctx=ctx)
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
        elif ten == pipeline.QC:
            ra = giai_doan_qc.chay(db, kho, run=run, ctx=ctx)
        elif ten == pipeline.QC_AI:
            ra = giai_doan_qc_ai.chay(db, kho, run=run, ctx=ctx)
        else:
            ra = _engine_gia(kho, run_id=run_id, owner_id=owner_id, ten=ten,
                             van_tay=vt)

        # ── Buoc 2→4: kiem hop le -> promote -> ghi tham chieu + van tay ───
        # 🔴 **BAN GIAO KHONG CO HAN; ban trung gian thi co.**
        #
        #    `promote_va_ghi` mac dinh dong `HAN_TRUNG_GIAN = 30 ngay` len MOI
        #    thu, ke ca tep khach tai ve. Truoc pha 27 dieu do vo hai theo mot
        #    cach rat xau: khong bo quet nao ton tai, nen `expires_at` chi la mot
        #    nhan. Pha 27 vua noi bo quet vao (`features.bao_tri`) — va ngay
        #    khoanh khac do, cai nhan vo hai kia tro thanh mot lenh **xoa video
        #    cua khach sau 30 ngay**.
        #
        # ⇒ Hai thay doi nay PHAI di cung nhau. Mot bo quet dung khong kem dong
        #   nay la mot bo quet dung ap dung sai chinh sach — va no im lang cho
        #   30 ngay truoc khi ai do phat hien.
        khoa_ra: list[str] = []
        la_ban_giao = ten == pipeline.RENDER
        for phan in ra["phan"]:
            asset = assets.promote_va_ghi(
                db, kho, owner_id=owner_id, run_id=run_id, stage=ten,
                van_tay=phan.get("van_tay") or vt, kind=phan["kind"],
                duoi=phan["duoi"], staging_key=phan["staging_key"],
                parent_keys=_khoa_cha(db, run_id, ten),
                han=None if la_ban_giao else assets.HAN_TRUNG_GIAN)
            khoa_ra.append(asset.storage_key)

        ket_qua = {"stage": ten, "khoa_asset": khoa_ra,
                   **(ra.get("tom_tat") or {})}
        # Ghi khoa ca khi TINH THAT — do chinh la cach mot ket qua duoc cong bo
        # cho lan chay sau cua cung khach tim thay.
        if kc:
            ket_qua["khoa_chung"] = kc

        # 🔑 QC la mot CONG, va mot cong phai CHAN duoc (Prompt 18 muc 2).
        #
        # 🔴 Ban dau cho nay goi `danh_dau_xong` roi moi nem. Ket qua: dong
        #    `asv_stage` ghi `succeeded`, `_advance` dem du chin giai doan, va
        #    lan chay ve `done` — **du bao cao QC noi `dat: False`**. Tuc cong
        #    van do va van cho qua. Mot cong khong chan thi khong phai cong, va
        #    no con te hon khong co cong vi no trong nhu co.
        #
        # ⭐ Nhung artifact van duoc promote TRUOC (ngay ben tren), va thu tu do
        #    la co y: mot lan chay hong phai de lai **bang chung ve vi sao**.
        #    Nguoi can cau tra loi do nhat la nguoi ho tro, khong phai khach.
        hong_qc = ra.get("_qc_hong") or []
        if hong_qc:
            thong_bao = _t(
                'Bản kết xuất không đạt {n} mục kiểm chất lượng: {ds}.').format(
                n=len(hong_qc), ds=", ".join(hong_qc))
            features.danh_dau_hong(db, stage, thong_bao, cuoi_cung=True)
            stage.outputs = ket_qua
            db.commit()
            raise QcChan(thong_bao)

        features.danh_dau_xong(
            db, stage, fingerprint=vt, credit_actual=CHI_PHI_GIA,
            outputs=ket_qua)
        # ── Buoc 5 ────────────────────────────────────────────────────────
        db.commit()

        return {"stage": ten, "fingerprint": vt, "credit_cost": CHI_PHI_GIA,
                "khoa_asset": khoa_ra}
    except Exception as exc:
        # 🔑 BIEN. Day la cho duy nhat biet ca ngon ngu loi cua engine lan phan
        #    loai cua nen tang, nen phep dich thuoc ve day (xem `loi.py`).
        #
        # ⛔ Khong dich la de moi loai loi cua Auto Scan roi xuong nhanh mac
        #    dinh `"retry"` cua `job_runner._provider_failure_kind` — tuc thu
        #    lai ba lan mot tep nguon khong co tieng, va thu lai mot lan sinh
        #    tieng CO THE DA TINH TIEN.
        # 🔑 **Phan loai di vao TRANG THAI GIAI DOAN, khong chi vao ngoai le.**
        #
        #    Truoc pha 23, phep phan loai nay chi phuc vu hang doi nen tang; con
        #    dong `asv_stage` thi `_thu_ket_qua_job_con` danh dau `failed_terminal`
        #    cho MOI job con hong. Ket qua: `loi.TAM_THOI` khong lam gi ca, va
        #    mot truot thoang qua ket thuc ca lan chay.
        #
        # ⛔ `rollback` truoc khi ghi: phien nay vua nem giua chung nen no dang
        #    o trang thai khong xac dinh. Nhung diem chot da `commit` (tung doan
        #    tieng, tung lo dich) khong bi anh huong — do la ca ly do chung
        #    `commit` ngay tai cho thay vi `flush`.
        try:
            tam_thoi = loi.phan_loai(exc) == loi.TAM_THOI
            db.rollback()
            stage_hong = features.giai_doan_theo_ten(db, run_id, ten)
            if stage_hong is not None and stage_hong.status in (
                    STAGE_QUEUED, STAGE_RUNNING):
                features.danh_dau_hong(
                    db, stage_hong, str(exc)[:2000],
                    cuoi_cung=not (tam_thoi and features.con_luot_thu(stage_hong)))
                db.commit()
        except Exception:                   # noqa: BLE001
            # ⚠️ Ghi trang thai la viec PHU. No hong thi loi goc van phai noi
            #    len — nuot loi goc de bao mot loi ghi so la doi mot cau tra loi
            #    dung lay mot cau tra loi lac de.
            log.warning("khong ghi duoc trang thai hong cua giai doan %s", ten)

        moi = loi.dich_sang_loi_nen_tang(exc)
        if moi is not exc:
            raise moi from exc
        raise
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
