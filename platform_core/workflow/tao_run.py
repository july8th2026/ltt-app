"""Cửa tạo run DUY NHẤT — API, Canvas, trigger đều đi qua đây (spec §8.1).

Một transaction: ghim version → hold một lần → CREATED→QUEUED → wakeup `start`
→ sự kiện `WorkflowStarted` → đánh thức động cơ. Không commit.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from platform_core import jobs, registry
from platform_core.job_scheduler import ORIGIN_WORKFLOW
from platform_core.models import (JOB_QUEUED, JOB_RUNNING, Job, Workflow,
                                  WorkflowRun, WorkflowVersion)
from platform_core.registry import RegistryError
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


def chu_dong_co() -> str:
    """slug app sở hữu `DONG_CO_JOB`, tra qua registry — KHÔNG hardcode.

    ⭐ F2 (final-review.md): bản cũ viết thẳng slug app = "agent" ở đây,
       phạm Global Constraint "không hardcode tên app/tool trong
       `platform_core/`" — mà `test_967` (bánh cóc cho luật đó) chỉ quét
       `frontend/agent-canvas/src` nên không bắt được. `apps/agent_dong_co`
       mới là app khai `job_types=("workflow.dong_co",)` (tách khỏi
       `apps/agent` để giữ bất biến orchestrator-không-phải-tool,
       `test_190`); tra registry cho `job.app_slug` khớp đúng app thật sự sở
       hữu job_type này, giống hệt cách `jobs.resolve_handler` tra handler.
       Ném `RegistryError` nếu registry đứt tay (không app nào khai job_type
       này) — vỡ ngay lúc nộp còn hơn ghi một `app_slug` sai lặng lẽ.
    """
    slug = registry.job_type_owners().get(DONG_CO_JOB)
    if not slug:
        raise RegistryError(
            f"khong app nao khai job_type {DONG_CO_JOB!r} trong job_types "
            "(xem apps/agent_dong_co/manifest.py)")
    return slug


def danh_thuc_dong_co(db) -> None:
    """Nộp job động cơ — TỐI ĐA MỘT job động cơ chờ/chạy trên toàn hệ.

    ⛔ Review round 1 (Critical #1): `jobs.submit` chỉ khử trùng theo ĐÚNG
       `dedupe_key`, không theo `job_type`. Job kế tiếp mà `_dong_co` tự nộp
       (`apps/agent/jobs.py`) dùng một khoá RIÊNG cho từng chuỗi
       (`workflow:dong_co:sau:<job_id>`, chủ ý — một job đang chạy không tự
       dedupe được với chính nó qua khoá cố định). Nếu hàm này chỉ gọi thẳng
       `jobs.submit(..., dedupe_key="workflow:dong_co")` như trước, từ lượt
       thứ hai trở đi nó không thấy job nào khớp ĐÚNG khoá cố định nữa và nộp
       thêm một job động cơ MỚI — job đó lại tự nộp chuỗi `:sau:` của riêng
       nó, nhân bản không giới hạn.

    ⇒ Tự hỏi bằng Ý NGHĨA ("có job động cơ nào CHƯA kết thúc không", bất kể
       khoá dedupe nào) thay vì dựa vào khớp khoá — rồi mới nộp dưới khoá cố
       định khi thật sự không có job nào đang sống.
    """
    dang_song = db.execute(select(Job.id).where(
        Job.job_type == DONG_CO_JOB,
        Job.status.in_((JOB_QUEUED, JOB_RUNNING))).limit(1)).scalar()
    if dang_song is not None:
        return
    jobs.submit(db, user_id=DONG_CO_USER, app_slug=chu_dong_co(),
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
        # ⚠️ Chỉ tra "run cũ" khi CÓ khoá — savepoint bọc CẢ chuỗi (không chỉ
        # INSERT), nên `IntegrityError` ở đây có thể đến từ BẤT KỲ bước nào
        # trong chuỗi, không chỉ chỉ mục bộ phận `ux_workflow_run_idem`. Với
        # `idempotency_key == ""`, `_tim(owner_id, "")` khớp MỌI run trước đó
        # của owner này tạo bằng khoá rỗng (trigger_kind khác "api" không đòi
        # khoá) — trả nhầm một run KHÔNG LIÊN QUAN thay vì ném lỗi thật, nuốt
        # mất một lỗi ở `su_kien.ghi`/`danh_thuc_dong_co`/… mà không ai biết.
        if not idempotency_key:
            raise
        cu = _tim(db, owner_id, idempotency_key)
        if cu is None:
            raise
        if cu.workflow_id != workflow.id:
            raise TrungKhoaKhacWorkflow(idempotency_key) from None
        return cu, False

    return run, True


__all__ = ["DONG_CO_JOB", "DONG_CO_USER", "MAX_RUN_DONG_THOI",
           "KhongCoBanPublish", "QuaHanMuc", "TrungKhoaKhacWorkflow",
           "chu_dong_co", "danh_thuc_dong_co", "tao_run"]
