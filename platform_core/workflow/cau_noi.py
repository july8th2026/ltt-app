"""Cầu nối job ↔ node (spec §5.8). Tầng nền gọi đúng MỘT hàm ở đây:
`bao_ket_thuc` từ `jobs.complete/fail/cancel`.

⭐ Một attempt = một job: waitpoint + job + node→QUEUED cùng MỘT transaction.
   `jobs.submit` chỉ khử trùng job CHƯA kết thúc; chốt idempotency sau khi job
   xong là transaction này + việc node đã rời READY.
⭐ Không hold riêng: run đã giữ một lần (`tien.py`, `test_965`). Job không có
   hold ⇒ `job_runner._quyet_toan_credit/_hoan_credit` tự bỏ qua.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from sqlalchemy import select

from platform_core import jobs
from platform_core.job_scheduler import ORIGIN_WORKFLOW
from platform_core.models import (JOB_CANCELLED, JOB_DONE, Job, Waitpoint,
                                  WaitpointSignal, WorkflowRun)
from platform_core.workflow import (cho_doi, danh_thuc, may_trang_thai,
                                    thi_hanh)
from platform_core.workflow import cong_cu as _nguon
from platform_core.workflow.bien_dich import la_tham_chieu
from platform_core.workflow.cong_cu import CongCu

GIOI_HAN_DAU_RA = 256 * 1024


class LoiThamSo(ValueError):
    def __init__(self, ma: str, thong_diep: str):
        super().__init__(f"{ma}: {thong_diep}")
        self.ma = ma


def _bay_gio():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(tzinfo=None)


def giai_tham_so(db, run_id: str, params: dict) -> dict:
    def _giai(v: Any) -> Any:
        if isinstance(v, dict):
            return {k: _giai(x) for k, x in v.items()}
        if isinstance(v, list):
            return [_giai(x) for x in v]
        tc = la_tham_chieu(v)
        if tc is None:
            return v
        nguon, cong = tc
        anh = thi_hanh.anh_chup_hien_tai(db, run_id, nguon)
        if anh is None or anh.execution_status != "SUCCEEDED":
            raise LoiThamSo("dau_vao_sai", f"{nguon} chua SUCCEEDED")
        if cong not in (anh.output_ref or {}):
            raise LoiThamSo("dau_vao_sai", f"{nguon} khong co cong {cong!r}")
        return anh.output_ref[cong]
    return _giai(dict(params))


def _khoa_idem(run: WorkflowRun, node: dict, lan: int, cc: CongCu,
               params: dict) -> str:
    if cc.side_effect == "none" or not cc.idempotency_fields:
        goc = [run.id, node["id"], lan]
    else:
        goc = [run.id, node["id"],
               {k: params.get(k) for k in cc.idempotency_fields}]
    return hashlib.sha256(json.dumps(goc, sort_keys=True, default=str)
                          .encode()).hexdigest()[:64]


def nop_job(db, run: WorkflowRun, node: dict, *,
            cong_cu: Optional[dict[str, CongCu]] = None) -> Optional[str]:
    cc_all = _nguon.tat_ca() if cong_cu is None else cong_cu
    nid = node["id"]
    cc = cc_all[str(node["type"])[4:]]
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, nid)
    lan = int(anh.attempt_number if anh else 1)
    try:
        params = giai_tham_so(db, run.id, node.get("params") or {})
    except LoiThamSo as loi:
        may_trang_thai.chuyen_node(
            db, run.id, nid, sang="FAILED",
            mo_ta=f"dau_vao_sai: {loi.ma}: {loi}", attempt_number=lan)
        return None
    gia_that = int(cc.tinh_gia(params))
    tran = int(node.get("gia_tran", 0))
    if gia_that > tran:
        may_trang_thai.chuyen_node(
            db, run.id, nid, sang="FAILED",
            mo_ta=f"vuot_tran_bao_gia: {gia_that} > {tran}", attempt_number=lan)
        return None
    wp = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id=run.owner_id,
                               kind="JOB", required_successes=1)
    cho_doi.chan_node(db, run_id=run.id, node_id=nid, waitpoint_id=wp.id)
    tham_so = dict(params)
    tham_so["owner_id"] = run.owner_id           # như submit_child (v1)
    khoa = _khoa_idem(run, node, lan, cc, params)
    tham_so["_idem"] = khoa
    job = jobs.submit(db, user_id=run.owner_id, app_slug=cc.app_slug,
                      job_type=cc.job_type, params=tham_so, dedupe_key=khoa,
                      max_attempts=3, parent_id=wp.id, plan_id=run.id,
                      origin=ORIGIN_WORKFLOW, priority_class="internal")
    may_trang_thai.chuyen_node(
        db, run.id, nid, sang="QUEUED", mo_ta="da nop job", job_id=job.id,
        attempt_number=lan, output_ref={"_gia_that": gia_that})
    return job.id


def bao_ket_thuc(db, job: Job) -> None:
    from platform_core.workflow import tao_run
    if job.job_type == tao_run.DONG_CO_JOB:
        return
    if job.origin != ORIGIN_WORKFLOW or not job.parent_id or not job.plan_id:
        return
    trang_thai = {JOB_DONE: "SUCCEEDED", JOB_CANCELLED: "CANCELLED"}.get(
        str(job.status), "FAILED")
    ket_qua = dict(job.result or {}) if trang_thai == "SUCCEEDED" else {
        "error": str(job.error or "")[:2000],
        "provider_state": str(job.provider_state or "")}
    try:
        with db.begin_nested():
            cho_doi.ghi_tin_hieu(db, job.parent_id, seq=1, status=trang_thai,
                                 ref_id=job.id, result_ref=ket_qua)
    except Exception:                                # noqa: BLE001
        return                                       # tín hiệu đã có: luỹ đẳng
    danh_thuc.hen(db, run_id=job.plan_id, kind="job", due_at=_bay_gio(),
                  node_run_id=job.id)
    tao_run.danh_thuc_dong_co(db)


def ap_ket_qua(db, run: WorkflowRun, node_id: str, *,
               cong_cu: Optional[dict[str, CongCu]] = None) -> Optional[str]:
    hien = may_trang_thai.trang_thai_node(db, run.id, node_id)
    if hien not in ("QUEUED", "RUNNING"):
        return None
    for wp_id in cho_doi.waitpoint_cua_node(db, run.id, node_id):
        wp = db.get(Waitpoint, wp_id)
        if wp is None or wp.kind != "JOB" or wp.status != "PENDING":
            continue
        sig = db.execute(select(WaitpointSignal).where(
            WaitpointSignal.waitpoint_id == wp_id)).scalars().first()
        if sig is None:
            continue
        wp.status = "COMPLETED"
        anh = thi_hanh.anh_chup_hien_tai(db, run.id, node_id)
        lan = int(anh.attempt_number if anh else 1)
        gia_that = int((anh.output_ref or {}).get("_gia_that", 0)) if anh else 0
        if sig.status == "SUCCEEDED":
            du_lieu = dict(sig.result_ref or {})
            if len(json.dumps(du_lieu, default=str)) > GIOI_HAN_DAU_RA:
                may_trang_thai.chuyen_node(
                    db, run.id, node_id, sang="FAILED", mo_ta="dau_ra_qua_lon",
                    attempt_number=lan, job_id=sig.ref_id)
                return "FAILED"
            bao = du_lieu.get("credit_cost")      # handler báo giá thật (vd theo token)
            chi_phi = int(bao) if bao is not None else gia_that
            node = _node_cua(db, run, node_id)
            chi_phi = min(chi_phi, int(node.get("gia_tran", chi_phi)))  # không thu quá trần
            may_trang_thai.chuyen_node(
                db, run.id, node_id, sang="SUCCEEDED", mo_ta="job xong",
                output_ref=du_lieu, cost_credit=chi_phi, attempt_number=lan,
                job_id=sig.ref_id)
            run.actual_cost = int(run.actual_cost or 0) + chi_phi
            db.flush()
            return "SUCCEEDED"
        mo_ho = (sig.result_ref or {}).get("provider_state") == jobs.PROVIDER_AMBIGUOUS
        cc_all = _nguon.tat_ca() if cong_cu is None else cong_cu
        se = cc_all[str(_node_cua(db, run, node_id)["type"])[4:]].side_effect
        sang = "ABANDONED" if (mo_ho and se == "irreversible") else (
            "CANCELLED" if sig.status == "CANCELLED" else "FAILED")
        ma = "ket_qua_mo_ho" if sang == "ABANDONED" else "provider_loi"
        mo_ta = f"{ma}: {(sig.result_ref or {}).get('error', '')}"[:2000]
        may_trang_thai.chuyen_node(
            db, run.id, node_id, sang=sang, mo_ta=mo_ta,
            attempt_number=lan, job_id=sig.ref_id)
        return sang
    return None


def _node_cua(db, run: WorkflowRun, node_id: str) -> dict:
    from platform_core.models import WorkflowVersion
    g = db.get(WorkflowVersion, run.version_id).graph
    return next(n for n in g["nodes"] if n["id"] == node_id)


__all__ = ["GIOI_HAN_DAU_RA", "LoiThamSo", "giai_tham_so", "nop_job",
           "bao_ket_thuc", "ap_ket_qua"]
