"""Cửa tạo run DUY NHẤT — API, Canvas, trigger đều đi qua đây (spec §8.1).

Một transaction: ghim version → hold một lần → CREATED→QUEUED → wakeup `start`
→ sự kiện `WorkflowStarted` → đánh thức động cơ. Không commit.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from platform_core import jobs
from platform_core.job_scheduler import ORIGIN_WORKFLOW
from platform_core.models import Workflow, WorkflowRun, WorkflowVersion
from platform_core.workflow import (danh_thuc, may_trang_thai, su_kien,
                                    thi_hanh, tien)

DONG_CO_JOB = "workflow.dong_co"
DONG_CO_USER = "__workflow_dong_co__"
#: Hạn mức (spec §7.3). Đọc từ settings ở plan 06; hằng ở đây là mặc định spec.
MAX_RUN_DONG_THOI = 5
_DANG_SONG = ("CREATED", "QUEUED", "RUNNING", "WAITING")


class KhongCoBanPublish(ValueError):
    pass


class QuaHanMuc(ValueError):
    pass


class TrungKhoaKhacWorkflow(ValueError):
    pass


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def danh_thuc_dong_co(db) -> None:
    """Nộp job động cơ. `jobs.submit` khử trùng job CHƯA kết thúc cùng khoá ⇒
    tối đa một job động cơ chờ trên toàn hệ."""
    jobs.submit(db, user_id=DONG_CO_USER, app_slug="agent",
                job_type=DONG_CO_JOB, params={}, dedupe_key="workflow:dong_co",
                max_attempts=3, origin=ORIGIN_WORKFLOW,
                priority_class="internal")


def _tim(db, owner_id: str, khoa: str):
    return db.execute(select(WorkflowRun).where(
        WorkflowRun.owner_id == owner_id,
        WorkflowRun.idempotency_key == khoa)).scalars().first()


def tao_run(db, *, workflow: Workflow, owner_id: str, trigger_kind: str,
            idempotency_key: str, inputs: dict | None = None
            ) -> tuple[WorkflowRun, bool]:
    if workflow.owner_id != owner_id:
        raise KhongCoBanPublish("workflow khong thuoc nguoi goi")
    if not workflow.published_version_id or workflow.archived_at is not None:
        raise KhongCoBanPublish("workflow chua publish hoac da luu tru")
    ver = db.get(WorkflowVersion, workflow.published_version_id)
    if ver is None:
        raise KhongCoBanPublish("version publish khong ton tai")

    if idempotency_key:
        cu = _tim(db, owner_id, idempotency_key)
        if cu is not None:
            if cu.workflow_id != workflow.id:
                raise TrungKhoaKhacWorkflow(idempotency_key)
            return cu, False

    dang = db.execute(select(func.count()).select_from(WorkflowRun).where(
        WorkflowRun.owner_id == owner_id,
        WorkflowRun.status.in_(_DANG_SONG))).scalar() or 0
    if dang >= MAX_RUN_DONG_THOI:
        raise QuaHanMuc(f"toi da {MAX_RUN_DONG_THOI} run dong thoi")

    # ⚠️ TOÀN BỘ chuỗi (tạo run → giữ tiền → QUEUED → wakeup → sự kiện → đánh
    # thức động cơ) nằm trong CÙNG MỘT savepoint, không chỉ riêng INSERT.
    #
    # 🔴 Lý do không phải gu, mà là một bẫy SQLite đo được: `Session.rollback()`
    #    gọi SAU KHI một `begin_nested()` khác đã thoát êm (savepoint đã
    #    RELEASE) không cuộn lại được các dòng đã ghi — driver `pysqlite` mặc
    #    định của dự án không phát `BEGIN` đúng cách cho SAVEPOINT (bẫy đã biết
    #    của SQLAlchemy). Test trực tiếp: `RELEASE` rồi `db.rollback()` sau đó
    #    ⇒ dòng vẫn còn; nhưng ngoại lệ ném **trong khi savepoint còn mở** thì
    #    `ROLLBACK TO SAVEPOINT` cuộn đúng, kể cả trên driver này.
    #
    # ⇒ Nếu `giu_cho_run` ném `ThieuCreditError` sau khi savepoint tạo run đã
    #    đóng, PostgreSQL (production) cuộn đúng nhưng SQLite (test) để lại một
    #    `WorkflowRun` mồ côi — đúng thứ `test_966::…KHONG_con_run_mo_coi` bắt.
    #    Gộp chung một savepoint là cách né bẫy driver mà không đụng
    #    `platform_core/db.py` (hạ tầng dùng chung, ngoài phạm vi việc này).
    try:
        with db.begin_nested():
            run = thi_hanh.tao_run(
                db, workflow_id=workflow.id, version_id=ver.id,
                owner_id=owner_id, trigger_kind=trigger_kind,
                idempotency_key=idempotency_key,
                estimated_max=int(ver.estimated_max or 0))
            tien.giu_cho_run(db, run)                 # ném ThieuCreditError
            may_trang_thai.chuyen_run(db, run.id, sang="QUEUED")
            danh_thuc.hen(db, run_id=run.id, kind="start", due_at=_bay_gio())
            su_kien.ghi(db, run.id, "WorkflowStarted",
                        du_lieu={"trigger_kind": trigger_kind,
                                 "version_id": ver.id,
                                 "inputs": dict(inputs or {})})
            danh_thuc_dong_co(db)
    except IntegrityError:
        cu = _tim(db, owner_id, idempotency_key)
        if cu is None:
            raise
        if cu.workflow_id != workflow.id:
            raise TrungKhoaKhacWorkflow(idempotency_key) from None
        return cu, False

    return run, True


__all__ = ["DONG_CO_JOB", "DONG_CO_USER", "MAX_RUN_DONG_THOI",
           "KhongCoBanPublish", "QuaHanMuc", "TrungKhoaKhacWorkflow",
           "danh_thuc_dong_co", "tao_run"]
