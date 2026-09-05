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
        dat_lai, het_vong = _sua_chua_neu_can(db, run, theo_ten)
        if het_vong:
            features.quyet_toan(db, run, trang_thai_cuoi=RUN_ERROR)
            return {"run_id": run.id, "status": run.status}
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


def _sua_chua_neu_can(db, run, theo_ten) -> tuple[list[str], bool]:
    """Thi hanh ke hoach sua. Tra ve `(giai_doan da dat lai, het vong)`.

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

    🔑 **Tran vong nam o `su_dung.ghi`, khong nam o mot bien.** Mot bien dem
       trong bo nho khong song qua mot lan worker chet; mot cot dem co the bi
       hai luot advance cung tang. Rang buoc `UNIQUE(run_id, ma_dispatch)` thi
       khong — no la mot tran ma CSDL cuong che.
    """
    vong = len(su_dung.cac_dong(db, run, stage=pipeline.QC,
                                item_key=DON_VI_SUA))
    ke = sua_chua.lap_ke_hoach(cac_nan=_cac_nan(db, run), vong=vong)
    if not ke.can_sua:
        return [], False

    if not ke.con_vong():
        # ⚠️ That bai CO BIEN, dung nhu cong thoat pha 19 doi: "until pass or
        #    bounded terminal failure". Va no phai NOI RA doan nao, vi khach se
        #    hoi — mot lan chay hong ma khong noi hong o dau la mot lan chay
        #    hong hai lan.
        ma = ", ".join(sorted(k.ma for k in ke.dang_tin if k.ma)[:5])
        run.error = (f"sua_chua: het {sua_chua.VONG_SUA_TOI_DA} vong ma "
                     f"{len(ke.dang_tin)} doan van khong dat ({ma})")[:2000]
        log.warning("asv: run %s het vong sua, %d khiem khuyet con lai",
                    run.id[:8], len(ke.dang_tin))
        return [], True

    # 🔑 Ghi so TRUOC khi dat lai. Neu dao thu tu, mot lan hong giua chung se de
    #    lai mot chuoi da bi dat lai ma khong co dong nao dem no — tuc tran vong
    #    mat hieu luc dung o lan chay can no nhat.
    try:
        su_dung.ghi(db, run, stage=pipeline.QC, item_key=DON_VI_SUA,
                    su_dung=su_dung.SuDung(
                        nang_luc="sua_chua", app_chu="auto_scan_video",
                        trang_thai=su_dung.DA_GIAO, don_vi=su_dung.LUOT,
                        so_luong=1, credit=0,
                        ma_dispatch=f"sua:{vong}",
                        ghi_chu=ke.sang_dict()))
    except su_dung.DaGhiRoi:
        # Mot luot advance khac vua lam dung vong nay. Khong lam lai.
        return [], False

    gon = sua_chua.gon_theo_don_vi(ke)          # {ma: giai_doan som nhat}
    theo_giai_doan: dict[str, list[str]] = {}
    for ma, gd in gon.items():
        theo_giai_doan.setdefault(gd, []).append(ma)

    dat_lai: list[str] = []
    for gd, cac_ma in sorted(theo_giai_doan.items()):
        for ma in cac_ma:
            su_dung.mo_lai_don_vi(db, run, stage=gd, item_key=ma)
        s = theo_ten.get(gd)
        if s is None:
            continue
        try:
            features._dat_lai_giai_doan(db, s)
        except features.XungDot:
            continue
        dat_lai.append(gd)
        dat_lai += features.vo_hieu_ha_nguon(db, run, gd)

    if dat_lai:
        assets.vo_hieu_theo_day_chuyen(db, run.id, sorted(set(dat_lai)))
        log.warning("asv: run %s vao vong sua %d, dat lai %s (%d don vi)",
                    run.id[:8], vong + 1, ",".join(sorted(set(dat_lai))),
                    len(gon))
    return dat_lai, False


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
