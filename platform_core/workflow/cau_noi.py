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
from sqlalchemy.exc import IntegrityError

from platform_core import jobs, registry
from platform_core.job_scheduler import ORIGIN_WORKFLOW
from platform_core.models import (JOB_CANCELLED, JOB_DONE, Artifact, Job,
                                  Waitpoint, WaitpointSignal, WorkflowRun)
from platform_core.workflow import (cho_doi, danh_thuc, may_trang_thai,
                                    thi_hanh, thu_lai)
from platform_core.workflow import artifact as _artifact
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
        ra = anh.output_ref or {}
        if "_tran" in ra:
            # Output đã tràn ra artifact (§5.8). Node sau phải nhận cả tệp qua
            # một cổng `artifact_ref`, không phải một khoá con — plan 04 thêm
            # node đọc artifact. Nói thẳng ra thay vì báo "khong co cong".
            raise LoiThamSo(
                "dau_ra_tran_artifact",
                f"{nguon} tran ra artifact {ra['_tran']['artifact_ref']}; "
                f"khong tra cung duoc cong {cong!r}")
        if cong not in ra:
            raise LoiThamSo("dau_vao_sai", f"{nguon} khong co cong {cong!r}")
        return ra[cong]
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
    ten_cc = str(node["type"])[4:]
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, nid)
    lan = int(anh.attempt_number if anh else 1)
    cc = cc_all.get(ten_cc)
    if cc is None:
        # ⭐ F5 (final-review.md): tra `cc_all[...]` bằng tay trước đây ném
        # `KeyError` thẳng vào `mot_vong` khi một tool bị gỡ khỏi registry
        # SAU KHI version đã publish (app tắt cờ, tool đổi tên) — nuốt mất
        # theo từng lượt (`except Exception` ở `mot_vong`), node đứng QUEUED
        # mãi, credit vẫn giữ, cho tới khi `TRAN_RUN` (20h) tự hết hạn. Mọi
        # chỗ từ chối node KHÁC trong hàm này đều xử lý văn minh (`LoiThamSo`,
        # vượt trần báo giá) — chỗ này cũng phải vậy: FAILED có mã lỗi rõ, để
        # run kết thúc ngay trong lượt này thay vì quay vòng đến khi hết hạn.
        may_trang_thai.chuyen_node(
            db, run.id, nid, sang="FAILED", mo_ta="cong cu bien mat khoi registry",
            error=f"cong_cu_khong_con: {ten_cc!r}", attempt_number=lan)
        return None
    try:
        params = giai_tham_so(db, run.id, node.get("params") or {})
    except LoiThamSo as loi:
        # `str(loi)` da la "<ma>: <chi tiet>" (LoiThamSo.__init__) - khong lap
        # lai `loi.ma` lan nua o day (review round 1: ma "dau_vao_sai" bi lap
        # ba lan khi ghep them prefix rieng).
        may_trang_thai.chuyen_node(
            db, run.id, nid, sang="FAILED", mo_ta="giai tham so",
            error=str(loi), attempt_number=lan)
        return None
    gia_that = int(cc.tinh_gia(params))
    tran = int(node.get("gia_tran", 0))
    if gia_that > tran:
        may_trang_thai.chuyen_node(
            db, run.id, nid, sang="FAILED", mo_ta="vuot tran bao gia",
            error=f"vuot_tran_bao_gia: {gia_that} > {tran}",
            attempt_number=lan)
        return None
    wp = cho_doi.tao_waitpoint(db, run_id=run.id, owner_id=run.owner_id,
                               kind="JOB", required_successes=1)
    cho_doi.chan_node(db, run_id=run.id, node_id=nid, waitpoint_id=wp.id)
    tham_so = dict(params)
    tham_so["owner_id"] = run.owner_id           # như submit_child (v1)
    khoa = _khoa_idem(run, node, lan, cc, params)
    tham_so["_idem"] = khoa
    # Làn + admission ĐÚNG con đường canonical (`public_api/invocation.py`
    # `submit()`, dòng ~500-560): làn do `ToolSpec.lane_for` chọn (không cứng
    # `cc.job_type`), `Job.admission_resource/slots` ghi LÚC NỘP qua
    # `registry.admission_luc_nop` — thiếu bước này `jobs.claim()` coi mọi
    # job GPU/LLM là "không giành tài nguyên chia sẻ" và có thể nhận quá số
    # thẻ (multijob 2.3, R20; review round 1, controller-found). `cc.spec`
    # rỗng (CongCu giả trong test cũ) ⇒ giữ hành vi cũ y nguyên: làn =
    # `job_type`, không admission — không tự suy diễn logic của registry ở
    # đây, chỉ gọi thẳng hai hàm đã có.
    if cc.spec is not None:
        lane = cc.spec.lane_for(tham_so)
        # `mac_dinh="internal"`: nhánh này chỉ chạy khi tool KHÔNG khai admission
        # nào cả (không `admission_theo_model`, không bộ ba tĩnh) — bản thân
        # `so_suat` vẫn là 0 trong nhánh đó (xem `admission_luc_nop`), nên nhãn
        # chỉ phục vụ quan sát/gom nhóm, không đổi quyền giành suất. Job này
        # đến từ động cơ workflow (không phải Public API, nơi dùng "api"), nên
        # nhãn "internal" khớp `priority_class="internal"` đã dùng ngay dưới
        # thay vì mượn nhãn "api" của một cửa khác.
        tai_nguyen, so_suat = registry.admission_luc_nop(
            cc.spec, tham_so, mac_dinh="internal")
    else:
        lane, tai_nguyen, so_suat = cc.job_type, "", 0
    job = jobs.submit(db, user_id=run.owner_id, app_slug=cc.app_slug,
                      job_type=lane, params=tham_so, dedupe_key=khoa,
                      max_attempts=3, parent_id=wp.id, plan_id=run.id,
                      origin=ORIGIN_WORKFLOW, priority_class="internal",
                      admission_resource=tai_nguyen, admission_slots=so_suat)
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
    except IntegrityError:
        # `UNIQUE(waitpoint_id, seq)` — tín hiệu đã có: gọi lại luỹ đẳng (job
        # runner gọi trùng, retry hạ tầng). MỌI lỗi khác (FK thiếu, mất kết
        # nối, serialization) phải NỔI LÊN — nuốt hết bằng `except Exception`
        # (review round 1, Important #2) từng khiến job đóng "thành công" mà
        # node đứng QUEUED mãi mãi, không wakeup, không log.
        return
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
            bao = du_lieu.get("credit_cost")      # handler báo giá thật (vd theo token)
            chi_phi = int(bao) if bao is not None else gia_that
            do_dai = len(json.dumps(du_lieu, default=str))
            tran_ref = ""
            if do_dai > GIOI_HAN_DAU_RA:
                # ⭐ Spec §5.8: output quá lớn KHÔNG làm hỏng node — nó ra
                #    artifact và output giữ ref. Plan 01a để FAILED
                #    (`dau_ra_qua_lon`) vì chưa có đường lưu; đây là chỗ trả nợ.
                # ⚠️ `credit_cost` đọc TRƯỚC dòng này: sau khi thay `du_lieu`
                #    bằng ref thì handler coi như không báo giá, và mọi node
                #    tràn sẽ bị thu theo `gia_that`.
                khoa = f"workflow/{run.id}/{node_id}/{lan}.json"
                du_lieu = {"_tran": _artifact.luu_json(
                    db, owner_id=run.owner_id, key=khoa, du_lieu=du_lieu)}
                tran_ref = str(du_lieu["_tran"]["artifact_ref"])
            node = _node_cua(db, run, node_id)
            # M2 (final-review.md): mặc định PHẢI khớp `nop_job` (fail-closed,
            # `0`) — bản cũ mặc định `chi_phi` (fail-OPEN, tức "không trần")
            # khi thiếu `gia_tran`. Không sờ được hôm nay (bộ biên dịch luôn
            # ghi `gia_tran` và `_ban_publish` từ chối version chưa biên
            # dịch), nhưng hai mặc định khác nhau cho CÙNG một luật là đúng
            # hình dạng hai bản sao trôi nhau — sửa cả hai về cùng `0`.
            chi_phi = min(chi_phi, int(node.get("gia_tran", 0)))  # không thu quá trần
            may_trang_thai.chuyen_node(
                db, run.id, node_id, sang="SUCCEEDED", mo_ta="job xong",
                output_ref=du_lieu, cost_credit=chi_phi, attempt_number=lan,
                job_id=sig.ref_id)
            if tran_ref:
                # LINEAGE — `created_by_snapshot_id` phải trỏ vào ảnh chụp
                # ĐANG GIỮ ref, để "tệp này từ đâu ra" trả lời được bằng MỘT
                # cột. Ảnh chụp đó là hàng SUCCEEDED vừa ghi ở trên: mô hình C
                # INSERT một hàng MỚI mỗi lần chuyển, nên lúc `luu_json` chạy
                # nó CHƯA tồn tại (`anh` khi đó còn là hàng QUEUED/RUNNING).
                moi = thi_hanh.anh_chup_hien_tai(db, run.id, node_id)
                if moi is not None:
                    db.get(Artifact, tran_ref).created_by_snapshot_id = moi.id
            run.actual_cost = int(run.actual_cost or 0) + chi_phi
            db.flush()
            return "SUCCEEDED"
        mo_ho = (sig.result_ref or {}).get("provider_state") == jobs.PROVIDER_AMBIGUOUS
        cc_all = _nguon.tat_ca() if cong_cu is None else cong_cu
        ten_cc = str(_node_cua(db, run, node_id)["type"])[4:]
        cc = cc_all.get(ten_cc)
        if cc is None:
            # F5 (final-review.md) — cùng lý do với `nop_job`: tool bị gỡ
            # khỏi registry giữa lúc publish và lúc job này kết thúc. Tra
            # `side_effect` bằng tay ném `KeyError` ở đây thì job ĐÃ kết thúc
            # (job runner đã gọi `bao_ket_thuc`) nhưng node không bao giờ
            # chốt trạng thái — cùng cái bẫy 20h, chỉ khác cửa vào. FAILED có
            # mã rõ, không đoán `side_effect` khi không còn ToolSpec nào để
            # đọc nó.
            may_trang_thai.chuyen_node(
                db, run.id, node_id, sang="FAILED", mo_ta="job ket thuc",
                error=f"cong_cu_khong_con: {ten_cc!r}", attempt_number=lan,
                job_id=sig.ref_id)
            return "FAILED"
        sang = "ABANDONED" if (mo_ho and cc.side_effect == "irreversible") else (
            "CANCELLED" if sig.status == "CANCELLED" else "FAILED")
        # Ba mã riêng (spec §5.6 `NodeError.ma`) — review round 1: CANCELLED
        # từng bị gắn nhầm mã `provider_loi` (mã của FAILED).
        ma = {"ABANDONED": "ket_qua_mo_ho", "CANCELLED": "bi_huy"}.get(
            sang, "provider_loi")
        chi_tiet = str((sig.result_ref or {}).get("error", ""))
        # ⭐ Retry CẤP NODE (spec §5.6) — chỉ xảy ra ở ĐÂY, tức khi job đã kết
        #    thúc ERROR và retry của chính job đã cạn. `thu_lai` không có bộ
        #    đếm riêng: nó đọc `settings.retry`, hỏi `jobs.gian_cach_retry` về
        #    giãn cách, và hẹn một wakeup. `KHONG_THU_LAI` (ABANDONED/CANCELLED)
        #    thắng `settings.retry`, không phải ngược lại.
        node = _node_cua(db, run, node_id)
        if thu_lai.quyet_dinh(sang=sang, node=node, lan=lan) == "RETRY_SCHEDULED":
            han = thu_lai.hen(db, run_id=run.id, node=node, lan=lan)
            may_trang_thai.chuyen_node(
                db, run.id, node_id, sang="RETRY_SCHEDULED",
                mo_ta="job ket thuc, con luot thu lai",
                error=f"{ma}: {chi_tiet}"[:2000],
                attempt_number=lan + 1, job_id=sig.ref_id,
                output_ref={thu_lai.KHOA_HAN: han.isoformat()})
            return "RETRY_SCHEDULED"
        may_trang_thai.chuyen_node(
            db, run.id, node_id, sang=sang, mo_ta="job ket thuc",
            error=f"{ma}: {chi_tiet}"[:2000],
            attempt_number=lan, job_id=sig.ref_id)
        return sang
    return None


def _node_cua(db, run: WorkflowRun, node_id: str) -> dict:
    from platform_core.models import WorkflowVersion
    g = db.get(WorkflowVersion, run.version_id).graph
    return next(n for n in g["nodes"] if n["id"] == node_id)


__all__ = ["GIOI_HAN_DAU_RA", "LoiThamSo", "giai_tham_so", "nop_job",
           "bao_ket_thuc", "ap_ket_qua"]
