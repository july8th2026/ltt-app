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

from . import features, pipeline
from .tables import (RUN_DONE, RUN_ERROR, RUN_QUEUED, RUN_RUNNING, RUN_TERMINAL,
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
        features.quyet_toan(db, run, trang_thai_cuoi=RUN_DONE)
        return {"run_id": run.id, "status": run.status}

    da_nop = _nop_giai_doan_san_sang(db, run, theo_ten, da_xong)

    # Con viec -> hen luot sau. `ctx.job_id` vao khoa dedupe nen moi luot tao
    # dung mot luot ke tiep, khong bao gio fan-out.
    hau_to = getattr(ctx, "job_id", None) or "tay"
    features._nop_dieu_phoi(db, run, ly_do=f"sau:{hau_to}")

    return {"run_id": run.id, "status": run.status,
            "da_nop": da_nop, "da_xong": sorted(da_xong)}


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
        if stage is None or stage.status != STAGE_PENDING:
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
