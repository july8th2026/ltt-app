"""Job dieu phoi cua Auto Scan Video.

## Hinh dang: TICK MOT LAN roi TU NOP LAI — khong bao gio cho con

`EXECUTION_GUARDRAILS` muc 1 cam "mot handler cha chay dai giu mot worker chi de
hoi vong job con". Ly do rat cu the trong kho nay: so tien trinh worker mac dinh
**bang so GPU** (`job_worker.py`). Voi hai card, hai run dong thoi ma moi run
giu mot worker de cho la **ca nen tang dung**, va khong loi nao duoc ghi ra.

Nen mot luot `advance` lam dung ba viec roi tra worker ve:
  1. thu ket qua cua job con da xong,
  2. nop nhung giai doan da du phu thuoc,
  3. neu run con song thi **nop lai chinh no** sau vai giay.

Khuon lay tu `apps/agent/jobs.py:19-41`, la duong da chay that trong production.

## Vi sao `advance` an toan khi chay lai

Worker chet giua chung la chuyen binh thuong, va job mo coi se duoc nhat lai
(`jobs.reclaim_orphans`). Nen moi buoc o day phai chiu duoc viec chay hai lan:
- doc trang thai run **duoi khoa** o dau moi luot;
- chi nop giai doan dang `pending`;
- dedupe theo `(run, stage, attempt)` nen nop lai khong tao job thu hai;
- quyet toan idempotent (`features.quyet_toan` tra ve ngay neu da ket thuc).
"""
from __future__ import annotations

import logging

from platform_core.db import get_session
from platform_core.models import JOB_CANCELLED, JOB_DONE, JOB_ERROR, Job

from . import assets, features, pipeline, su_dung, sua_chua, thi_hanh
from .tables import (RUN_DONE, RUN_ERROR, RUN_QUEUED, RUN_RUNNING, RUN_TERMINAL,
                     STAGE_FAILED_RETRYABLE,
                     STAGE_FAILED_TERMINAL, STAGE_PENDING, STAGE_QUEUED,
                     STAGE_RUNNING, STAGE_SUCCEEDED)

log = logging.getLogger(__name__)


def handle(params: dict, ctx=None) -> dict:
    """Cua DUY NHAT nen tang goi cho app nay. Tu phan nhanh theo `job_type`.

    App khach so huu HAI loai job, ca hai deu chi can `api`:
      `advance`         — dieu phoi (tep nay)
      `content_process` — dich, chay qua than thi hanh dung chung
    """
    loai = str(getattr(ctx, "job_type", "") or params.get("_job_type") or "")
    if loai and loai != features.JOB_DIEU_PHOI:
        from .thi_hanh import chay_theo_job_type
        return chay_theo_job_type(loai, params, ctx)

    run_id = str(params.get("run_id") or "")
    owner_id = str(params.get("owner_id") or "")
    if not run_id or not owner_id:
        raise ValueError("thieu run_id/owner_id cho auto_scan_video.advance")

    gen = get_session()
    db = next(gen)
    try:
        ket_qua = _advance(db, run_id=run_id, owner_id=owner_id, ctx=ctx)
        db.commit()
        return ket_qua
    finally:
        db.close()


def _advance(db, *, run_id: str, owner_id: str, ctx=None) -> dict:
    # 🔑 Khoa dong run TRUOC MOI THU. Day la nua thu hai cua I13: mot job con ve
    #    dich muon khong the lam song lai mot run da huy, vi luot advance ke tiep
    #    doc thay `cancelled` va dung ngay.
    run = features.lay_run(db, run_id, owner_id, lock=True)
    if run.status in RUN_TERMINAL:
        return {"run_id": run.id, "status": run.status, "ghi_chu": "da ket thuc"}

    if run.status == RUN_QUEUED:
        run.status = RUN_RUNNING
        run.revision = int(run.revision) + 1

    _thu_ket_qua_job_con(db, run)
    _vo_hieu_giai_doan_da_lech(db, run)

    ds = features.cac_giai_doan(db, run)
    theo_ten = {s.stage: s for s in ds}
    da_xong = {s.stage for s in ds if s.status == STAGE_SUCCEEDED}
    hong = [s for s in ds if s.status == STAGE_FAILED_TERMINAL]

    if hong:
        # Mot giai doan hong han thi ca run hong. Khong co nhanh xu ly loi trong
        # MVP — them mot nhanh nhu vay la bat dau dung mot do thi.
        run.error = f"{hong[0].stage}: {hong[0].error}"[:2000]
        features.quyet_toan(db, run, trang_thai_cuoi=RUN_ERROR)
        return {"run_id": run.id, "status": run.status}

    if len(da_xong) == len(pipeline.CHUOI):
        # 🔑 Cong cuoi cung TRUOC khi giao hang: chuoi da chay het, nhung "chay
        #    het" khong dong nghia "dat". Neu con khiem khuyet sua duoc thi sua,
        #    va chi khi khong con gi de sua moi quyet toan.
        dat_lai = _sua_chua_neu_can(db, run, theo_ten)
        if dat_lai:
            hau_to = getattr(ctx, "job_id", None) or "tay"
            features._nop_dieu_phoi(db, run, ly_do=f"sua:{hau_to}")
            return {"run_id": run.id, "status": run.status,
                    "sua_chua": sorted(set(dat_lai))}
        features.quyet_toan(db, run, trang_thai_cuoi=RUN_DONE)
        return {"run_id": run.id, "status": run.status}

    da_nop = _nop_giai_doan_san_sang(db, run, theo_ten, da_xong)

    # Con viec -> hen luot sau. `ctx.job_id` vao khoa dedupe nen moi luot tao
    # dung mot luot ke tiep, khong bao gio fan-out.
    hau_to = getattr(ctx, "job_id", None) or "tay"
    features._nop_dieu_phoi(db, run, ly_do=f"sau:{hau_to}")

    return {"run_id": run.id, "status": run.status,
            "da_nop": da_nop, "da_xong": sorted(da_xong)}


#: Don vi viec mang so cai cua CHINH vong sua. Khong phai mot doan tieng nao.
#:
#: ⭐ Vong sua duoc dem bang SO DONG SO CAI, khong bang mot bo dem. `su_dung.ghi`
#:    co `UNIQUE(run_id, ma_dispatch)`, nen mot vong khong the duoc dem hai lan
#:    ke ca khi hai luot advance chay chong nhau — va no thanh mot dong nguoi ho
#:    tro doc duoc khi khach hoi "vi sao lan chay nay lau the".
DON_VI_SUA = "__sua_chua__"

#: Hai loai dong cung dung `DON_VI_SUA`, va chung phai phan biet duoc:
#: mot VONG sua da chay, va mot ghi nhan khiem khuyet CON LAI sau khi het
#: vong. Dem lan nhau la an mat mot vong.
NANG_LUC_VONG_SUA = "sua_chua"
NANG_LUC_CON_LAI = "sua_chua_con_lai"


def _cac_nan(db, run) -> list[dict]:
    """Phan quyet NAN cua tung doan tieng, doc tu so cai.

    🔴 **Doc tu so cai chu khong mo kho.** `giai_doan_giong` ghi
       `ghi_chu={"trang_thai_nan": ...}` cho MOI doan ngay luc no tinh tien doan
       do, nen so cai da mang du du lieu. Mo artifact o day se bat dieu phoi vien
       — thu chay o MOI luot advance cua MOI lan chay — phai doc mot tep tu kho
       chi de tra loi mot cau hoi ma CSDL da tra loi duoc.
    """
    ra = []
    for d in su_dung.cac_dong(db, run, stage=pipeline.VOICE_SYNTHESIS):
        gc = dict(getattr(d, "ghi_chu", None) or {})
        tt = str(gc.get("trang_thai_nan") or "")
        if not tt:
            continue
        ra.append({"ma": d.item_key, "trang_thai_nan": tt,
                   "giay": float(getattr(d, "so_luong", 0) or 0),
                   "khe": gc.get("khe")})
    return ra


def _qc_ngu_nghia(theo_ten) -> list[dict]:
    """Phan quyet QC ngu nghia KHONG DAT, doc tu `outputs` cua giai doan.

    ⭐ Doc tu CSDL chu khong mo kho: `_advance` chay o moi luot cua moi lan
       chay, nen bat no mo mot tep de tra loi mot cau ma `stage.outputs` da
       tra loi duoc la mot cai gia phai tra mai mai. Cung ly do voi `_cac_nan`.

    ⚠️ Rong khi QC bang AI TAT — va do la dieu dung: khong soat thi khong co
       phan quyet, va "khong co phan quyet" phai doc thanh "khong co khiem
       khuyet nao DUOC BIET", khong phai "khong co khiem khuyet".
    """
    s = theo_ten.get(pipeline.QC_AI)
    if s is None:
        return []
    return list((getattr(s, "outputs", None) or {}).get("qc_ai_khong_dat")
                or [])


def _sua_chua_neu_can(db, run, theo_ten) -> list[str]:
    """Thi hanh ke hoach sua. Tra ve danh sach giai doan da dat lai.

    🔴 **Day la nua thu hai cua pha 19, va no da nam cho suot tu pha 19 toi
       pha 29 duoi dang ba nang luc mo coi.**

       `sua_chua.py` tinh ra **cai gi** phai lam lai va **o dau**; `qc_ai.py` bo
       sung them nguon khiem khuyet; `assets.vo_hieu_theo_day_chuyen` danh dau
       artifact ha nguon; `ITEM_INVALIDATED` la trang thai danh cho don vi bi bo
       ket qua. Bon thu do deu co test, deu xanh, va **khong thu nao co nguoi
       goi trong ma san pham**. Bao cao pha 19 goi dung ten no: *"The repair
       loop is planned, not yet driven."*

    ⭐ Va khiem khuyet ma no bo sot la mot khiem khuyet THAT, khong phai gia
       dinh: `nan_cho_vua` danh dau `CAN_SUA` cho mot doan khong vua khe **ke ca
       sau khi da het bac thang co gian**, `giai_doan_giong` ghi dau do vao so
       cai — va khong dong ma nao doc no. Tuc san pham BIET mot doan khong vua,
       ghi lai, roi giao hang.

    ⛔ Khong co giai doan moi va khong co bo dieu phoi thu hai. Vong sua dung
       dung co che da co: dat lai giai doan som nhat sua duoc, vo hieu ha nguon,
       roi de `_advance` chay tiep nhu no van chay. Them mot bo dieu phoi rieng
       cho viec sua la tao chu so huu thu hai cho cung mot chuoi.

    🔴 **Va ham nay KHONG lam hong lan chay khi het vong. Ban dau no co lam, va
       do la mot loi thiet ke cua toi ma so lieu that da bac.**

       Luot nghiem thu THAT gan nhat — luot toi vua goi la "xanh hoan toan" —
       giao hang voi `so_can_sua: 3` tren preset giu hinh (mot NUA so doan) va
       `1` tren preset cat. Ban dau nhanh "het vong" cua ham nay dua ca hai luot
       do ve `error`.

    ⭐ Nhung `CAN_SUA` khong dong nghia "video hong", va he thong da biet dieu
       do tu truoc: `thoi_gian` hap thu phan vuot bang **no troi**, co tran
       `TRAN_TROI_SO_DOAN`; va QC do dung hau qua cua no — **T7** (troi cua mot
       doan so voi vi tri da hoach dinh) va **T11** (troi tich luy). Ca hai DAT
       tren chinh ban giao ay.

    ⇒ Hau qua da co cong gac. Them mot cong nua o tang nan la gac hai lan cung
      mot thu, va lan thu hai dung mot nguong ma chinh ma nguon ghi la **chua
      do** (`DUNG_SAI_DAI = 0.08`, "CHUA DO tren du lieu that ... Pha 21 do
      lai" — pha 21 khong do).

    ⚠️ Va cong thoat pha 19 chi doi "bounded terminal failure" cho **QC failures**;
       `CAN_SUA` la phan quyet cua tang NAN, khong phai mot muc QC hong. Toi da
       gop hai thu do lam mot.

    ⇒ Nen: sua mot vong (co gia tri that — doc lai doan do de no vua hon), roi
      neu van con thi GHI LAI va giao hang, de QC lam cong gac nhu no von la.

    🔑 **Tran vong nam o `su_dung.ghi`, khong nam o mot bien.** Mot bien dem
       trong bo nho khong song qua mot lan worker chet; mot cot dem co the bi
       hai luot advance cung tang. Rang buoc `UNIQUE(run_id, ma_dispatch)` thi
       khong — no la mot tran ma CSDL cuong che.
    """
    # ⛔ Loc theo `nang_luc`, KHONG chi theo `item_key`. Hai loai dong dung chung
    #    item_key nay: mot vong sua (`sua_chua`) va mot ghi nhan khiem khuyet CON
    #    LAI (`sua_chua_con_lai`). Dem ca hai thi dong "con lai" tu no an mat mot
    #    vong — vo hai hom nay vi tran la 1, va hong ngay khi ai do nang tran len.
    vong = len([d for d in su_dung.cac_dong(db, run, stage=pipeline.QC,
                                            item_key=DON_VI_SUA)
                if d.nang_luc == NANG_LUC_VONG_SUA])
    ke = sua_chua.lap_ke_hoach(cac_nan=_cac_nan(db, run),
                               qc_ngu_nghia=_qc_ngu_nghia(theo_ten),
                               vong=vong)
    if not ke.can_sua:
        return []

    if not ke.con_vong():
        # 🔑 Het vong: GHI LAI roi di tiep. Khong giet lan chay — xem docstring.
        #
        # ⭐ Ghi vao SO CAI chu khong chi log: mot dong log bien mat sau mot tuan,
        #    va cau hoi "vi sao doan nay nghe hoi don" se duoc hoi sau do lau hon
        #    the. So cai la thu con lai.
        try:
            su_dung.ghi(db, run, stage=pipeline.QC, item_key=DON_VI_SUA,
                        su_dung=su_dung.SuDung(
                            nang_luc=NANG_LUC_CON_LAI,
                            app_chu="auto_scan_video",
                            trang_thai=su_dung.DA_GIAO, don_vi=su_dung.LUOT,
                            so_luong=len(ke.dang_tin), credit=0,
                            ma_dispatch=f"sua-con-lai:{vong}",
                            ghi_chu=ke.sang_dict()))
        except su_dung.DaGhiRoi:
            pass
        log.warning("asv: run %s het vong sua, %d khiem khuyet CON LAI — giao "
                    "hang va de QC lam cong gac", run.id[:8], len(ke.dang_tin))
        return []

    # 🔑 Ghi so TRUOC khi dat lai. Neu dao thu tu, mot lan hong giua chung se de
    #    lai mot chuoi da bi dat lai ma khong co dong nao dem no — tuc tran vong
    #    mat hieu luc dung o lan chay can no nhat.
    try:
        su_dung.ghi(db, run, stage=pipeline.QC, item_key=DON_VI_SUA,
                    su_dung=su_dung.SuDung(
                        nang_luc=NANG_LUC_VONG_SUA,
                        app_chu="auto_scan_video",
                        trang_thai=su_dung.DA_GIAO, don_vi=su_dung.LUOT,
                        so_luong=1, credit=0,
                        ma_dispatch=f"sua:{vong}",
                        ghi_chu=ke.sang_dict()))
    except su_dung.DaGhiRoi:
        # Mot luot advance khac vua lam dung vong nay. Khong lam lai.
        return []

    gon = sua_chua.gon_theo_don_vi(ke)          # {ma: giai_doan som nhat}
    theo_giai_doan: dict[str, list[str]] = {}
    for ma, gd in gon.items():
        theo_giai_doan.setdefault(gd, []).append(ma)

    dat_lai: list[str] = []
    #: 🔴 **Ha nguon giu RIENG, va mot bo do 3 phut da chung minh vi sao.**
    #:
    #:    Ban dau doan duoi truyen ca `dat_lai` — tuc CA giai doan dang duoc sua
    #:    — vao `assets.vo_hieu_theo_day_chuyen`. Hau qua: artifact cua CHINH
    #:    `voice_synthesis` bi danh dau mat, ke ca tieng cua nhung doan con LANH.
    #:    Luot chay lai khong tai dung duoc chung nua, nen `timing_align` phai co
    #:    gian **3,304 lan** va hong han:
    #:
    #:        timing_align failed_terminal
    #:        "He so co gian 3.304 ngoai khoang mot lan `atempo`"
    #:
    #: ⛔ Tuc chinh buoc don dep da pha "pham vi nho nhat an toan" ma ham nay ton
    #:    tai de bao ve. Giai doan duoc sua CAN artifact cua no con nguyen — do
    #:    la thu cho phep no bo qua nhung don vi da xong.
    ha_nguon: list[str] = []
    for gd, cac_ma in sorted(theo_giai_doan.items()):
        for ma in cac_ma:
            try:
                su_dung.mo_lai_don_vi(db, run, stage=gd, item_key=ma)
            except su_dung.XungDotDonVi:
                # ⚠️ Mot tien trinh khac dang cham don vi nay ngay luc nay. Bo
                #    qua **rieng no**, dung giet ca vong sua: nhung don vi khac
                #    van sua duoc, va don vi nay se hien lai o ban ghi "con lai"
                #    neu no van hong.
                log.warning("asv: run %s bo qua don vi %s/%s — dang bi tien "
                            "trinh khac cham", run.id[:8], gd, ma)
        s = theo_ten.get(gd)
        if s is None:
            continue
        try:
            features._dat_lai_giai_doan(db, s)
        except features.XungDot:
            continue
        dat_lai.append(gd)
        moi_ha = features.vo_hieu_ha_nguon(db, run, gd)
        dat_lai += moi_ha
        ha_nguon += moi_ha

    if dat_lai:
        # ⚠️ Chi HA NGUON. Xem ghi chu tren.
        assets.vo_hieu_theo_day_chuyen(db, run.id, sorted(set(ha_nguon)))
        log.warning("asv: run %s vao vong sua %d, dat lai %s (%d don vi)",
                    run.id[:8], vong + 1, ",".join(sorted(set(dat_lai))),
                    len(gon))
    return dat_lai


def _vo_hieu_giai_doan_da_lech(db, run) -> list[str]:
    """Giai doan `succeeded` co van tay khong con khop dau vao -> dat lai (muc 4).

    Chay o **dau moi luot advance**, truoc khi tinh `da_xong`, vi neu tinh
    truoc thi mot giai doan da lech van duoc dem la xong va lan chay co the ket
    thuc ngay o luot nay.

    ⛔ Vo hieu ca HA NGUON cua no, khong chi rieng no: mot giai doan sap chay
       lai se cho ket qua khac, nen moi thu an theo cung phai lam lai. Vo hieu
       thieu la giao mot ban long tieng tron lan hai lan chay.
    """
    lech = thi_hanh.giai_doan_lech_van_tay(db, run)
    if not lech:
        return []

    theo_ten = {s.stage: s for s in features.cac_giai_doan(db, run)}
    da_dat_lai: list[str] = []
    for ten in lech:
        s = theo_ten.get(ten)
        if s is None or s.status != STAGE_SUCCEEDED:
            continue        # mot vong truoc trong chinh luot nay da dat lai roi
        try:
            features._dat_lai_giai_doan(db, s)
        except features.XungDot:
            continue
        da_dat_lai.append(ten)
        da_dat_lai += features.vo_hieu_ha_nguon(db, run, ten)
        theo_ten = {x.stage: x for x in features.cac_giai_doan(db, run)}

    if da_dat_lai:
        # Su kien dang chu y, khong phai binh thuong: no nghia la mot giai doan
        # thuong nguon da chay lai va cho ket qua khac.
        log.warning("asv: run %s dat lai %d giai doan do lech van tay: %s",
                    run.id[:8], len(da_dat_lai), ",".join(sorted(set(da_dat_lai))))
    return da_dat_lai


def _thu_ket_qua_job_con(db, run) -> None:
    """Doi chieu tung giai doan dang chay voi job con cua no.

    ⛔ `Job.status == done` KHONG lam giai doan thanh `succeeded` o day. Handler
       cua giai doan moi la noi hoan tat du nam buoc cua ADR-001 D7 (validate ->
       promote -> ghi tham chieu + van tay) va no tu goi `danh_dau_xong`. Cho nay
       chi lo hai truong hop con lai: job hong, va job bi huy.

    ⭐ Neu cho nay tu suy "job done => stage succeeded" thi mot handler chet ngay
       sau khi engine tra ve — truoc khi promote — se thanh mot giai doan
       "thanh cong" tro toi mot tep khong ton tai. Dung kieu vi pham I8 ma
       `MVP_CONTRACT` va D7 sinh ra de chan.
    """
    for stage in features.cac_giai_doan(db, run):
        if stage.status not in (STAGE_QUEUED, STAGE_RUNNING) or not stage.job_id:
            continue
        job = db.get(Job, stage.job_id)
        if job is None:
            continue

        if job.status == JOB_ERROR:
            try:
                features.danh_dau_hong(db, stage, job.error or "job con that bai")
            except features.XungDot:
                pass    # handler vua kip ghi ket qua that; luot sau doc lai
        elif job.status == JOB_CANCELLED:
            from .tables import STAGE_CANCELLED
            try:
                features.cap_nhat_giai_doan(db, stage, status=STAGE_CANCELLED)
            except features.XungDot:
                pass
        elif job.status == JOB_DONE and stage.status != STAGE_SUCCEEDED:
            # Job xong ma giai doan chua tu danh dau xong => handler chet giua
            # chung sau khi engine tra ve. KHONG suy ra thanh cong: cho no chay
            # lai. Ghi log vi day la mot su kien dang chu y, khong phai binh thuong.
            log.warning("asv: job %s done nhung giai doan %s chua succeeded — "
                        "se chay lai", job.id[:8], stage.stage)
            try:
                features.danh_dau_hong(db, stage, "handler dung giua chung",
                                       cuoi_cung=False)
            except features.XungDot:
                pass


def _nop_giai_doan_san_sang(db, run, theo_ten: dict, da_xong: set[str]) -> list[str]:
    """Nop job con cho moi giai doan da du phu thuoc. Tra ve ten da nop."""
    from platform_core import jobs as hang_doi

    da_nop: list[str] = []
    for g in pipeline.ke_tiep(da_xong):
        stage = theo_ten.get(g.ten)
        # ⭐ `STAGE_FAILED_RETRYABLE` nam o day tu pha 23. Truoc do trang thai
        #    do ton tai nhung **khong ai nop lai** mot giai doan dang mang no —
        #    tuc no la mot ngo cut trong bang trang thai. Khoa dedupe da co
        #    `a{attempt}` chinh vi truong hop nay, va `danh_dau_dang_chay` tang
        #    `attempt` len, nen lan nop lai sinh mot job MOI chu khong dung lai
        #    job cu.
        if stage is None or stage.status not in (STAGE_PENDING,
                                                 STAGE_FAILED_RETRYABLE):
            continue

        # 🔴 **Tran so lan thu phai duoc cuong che O DAY, khong chi o cho bat
        #    loi.** `chay_giai_doan` kiem `con_luot_thu` truoc khi danh dau mot
        #    giai doan la `failed_retryable` — nhung do khong phai duong DUY
        #    NHAT dan toi trang thai do: `_thu_ket_qua_job_con` cung dat no khi
        #    "job xong ma giai doan chua xong" (handler chet giua chung), va
        #    duong do khong hoi tran nao ca.
        #
        # ⇒ Thieu phep kiem nay, mot giai doan roi vao dung cho do se duoc nop
        #   lai **vo han**: moi vong dieu phoi sinh mot job moi, va khong co gi
        #   dung lai. Do la mot vong lap tieu tai nguyen tren mot may dang phuc
        #   vu khach — dung loai su co ma pha 23 ton tai de chan.
        if (stage.status == STAGE_FAILED_RETRYABLE
                and not features.con_luot_thu(stage)):
            try:
                features.danh_dau_hong(
                    db, stage, stage.error or "het luot thu lai",
                    cuoi_cung=True)
            except features.XungDot:
                pass
            continue

        # ⛔ `jobs.submit`, KHONG BAO GIO `submit_with_credit`. Chi run giu tien
        #    (ADR-001 D4). Doi dong nay la tinh tien khach muoi lan cho mot lan
        #    chay, va so credit van can nen khong co gi trong nhu bi hong.
        job = hang_doi.submit(
            db, user_id=run.owner_id, app_slug=g.app_slug, job_type=g.job_type,
            params={"run_id": run.id, "owner_id": run.owner_id, "stage": g.ten},
            # Lineage: nen tang da co san ba cot nay cho quan he cha-con.
            plan_id=run.id, step_id=g.ten,
            dedupe_key=f"asv:{run.id}:{g.ten}:a{int(stage.attempt)}",
            max_attempts=1,
            # Tai nguyen dung chung duoc CHUP luc nop, khong suy lai luc chay:
            # mot lan deploy doi `pipeline` khong duoc doi hang dang cho sang
            # mot pool khac (cung ly do `Job.admission_resource` ton tai —
            # `platform_core/models.py:288`).
            admission_resource=g.tai_nguyen,
            admission_slots=g.tai_nguyen_suat,
        )
        try:
            features.danh_dau_dang_chay(db, stage, job.id)
        except features.XungDot:
            continue
        da_nop.append(g.ten)
    return da_nop
