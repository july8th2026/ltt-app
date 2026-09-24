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
#: Chỉ mục bộ phận `UNIQUE(user_id, dedupe_key) WHERE dedupe_key <> '' AND
#: status IN ('queued','running')` — `platform_core/models.py`, migration
#: `c9d4e1a77b02`. Tên này là thứ DUY NHẤT phân biệt "job động cơ đã có người
#: khác tạo" với mọi vi phạm ràng buộc khác, nên nó là một hằng, không phải
#: một chuỗi gõ lại giữa thân hàm.
UX_JOBS_DEDUPE = "ux_jobs_dedupe_active"
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
            "(xem manifest cua app dang so huu job_type nay duoi apps/)")
    return slug


def _la_trung_khoa_dong_co(exc: IntegrityError) -> bool:
    """`exc` có ĐÚNG là vi phạm `ux_jobs_dedupe_active` hay không.

    ⛔ HẸP có chủ ý. `except IntegrityError` trần ở chỗ gọi sẽ nuốt luôn một vi
       phạm khoá ngoại (`jobs.user_id` → `users.id`), một `NOT NULL`, hay một
       trùng khoá KHÁC — những lỗi đó là lỗi thật và phải nổ.

    PostgreSQL nói thẳng tên ràng buộc trong `Diagnostics.constraint_name`, nên
    ở production phép so là so TÊN, không phải dò chuỗi thông báo — và khi ĐÃ
    có tên thì KHÔNG rơi xuống dò chuỗi nữa (một lỗi khoá ngoại có câu SQL in
    kèm hoàn toàn có thể nhắc tên chỉ mục).

    ⚠️ SQLite (bộ test đơn vị) không có `diag`, và — đo 23/09 trên chính mô
       hình này — nó KHÔNG đọc ra tên chỉ mục bộ phận mà đọc ra các CỘT:
       `UNIQUE constraint failed: jobs.user_id, jobs.dedupe_key`. Nên đường lui
       nhận cả hai dạng, và vẫn hẹp: cặp cột đó chỉ có đúng một ràng buộc duy
       nhất trong mô hình (`ux_jobs_dedupe_active`), còn `jobs.id` hay bất kỳ
       cặp nào khác đều trả `False`.
    """
    orig = getattr(exc, "orig", None)
    ten = getattr(getattr(orig, "diag", None), "constraint_name", None)
    if ten:
        return ten == UX_JOBS_DEDUPE
    txt = str(orig or exc)
    if UX_JOBS_DEDUPE in txt:
        return True
    _, co, cot = txt.partition("UNIQUE constraint failed:")
    if not co:
        return False
    return ({x.strip() for x in cot.split(",") if x.strip()}
            == {"jobs.user_id", "jobs.dedupe_key"})


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
    # ⭐ CUỘC ĐUA GIỮA HAI NGƯỜI DÙNG (đo thật trên PostgreSQL 23/09) — câu
    #    SELECT ở trên và INSERT ở dưới KHÔNG nguyên tử. Hai người dùng KHÁC
    #    NHAU tạo run cùng lúc: phiên A chưa commit nên phiên B (READ
    #    COMMITTED) vẫn thấy "chưa có job động cơ nào" ⇒ cả hai cùng INSERT ⇒
    #    `ux_jobs_dedupe_active` ném `UniqueViolation` vào tay kẻ thua, và
    #    trước bản sửa này nó bay lên tận route ⇒ MỘT NGƯỜI DÙNG NHẬN 500 dù
    #    không làm gì sai.
    #
    # 🔑 VÌ SAO "TRÙNG KHOÁ" Ở ĐÂY LÀ KẾT QUẢ ĐÚNG, KHÔNG PHẢI LỖI:
    #    hàm này không đòi "tôi phải là người tạo job động cơ", nó đòi "có MỘT
    #    job động cơ đang sống". PostgreSQL chỉ ném `UniqueViolation` khi hàng
    #    kia ĐÃ COMMIT — INSERT của kẻ thua bị CHẶN ở chỉ mục cho tới khi phiên
    #    thắng kết thúc, và nếu phiên thắng ROLLBACK thì INSERT này đi tiếp
    #    bình thường. Nghĩa là nhận được lỗi này ⇔ trạng thái đích ĐÃ ĐẠT, do
    #    người khác đạt hộ. Không có gì để sửa, chỉ có việc đi tiếp.
    #
    # ⚠️ SAVEPOINT LỒNG, KHÔNG PHẢI `try` trần: sau khi một câu lệnh vỡ,
    #    transaction PostgreSQL ở trạng thái abort — mọi câu sau đều hỏng cho
    #    tới khi cuộn về một savepoint. Bên gọi (`tao_run`) đang giữ một
    #    savepoint bọc CẢ chuỗi tạo run + khoản giữ chỗ credit; cuộn về savepoint
    #    ĐÓ sẽ xoá luôn khoản giữ của chính kẻ thua. `begin_nested()` ở đây mở
    #    một savepoint RIÊNG chỉ bọc INSERT job, nên `ROLLBACK TO` của nó gỡ
    #    đúng câu vỡ và trả transaction về trạng thái dùng được mà run + hold
    #    của kẻ thua vẫn nguyên.
    #
    # 🔑 Vế "vẫn nguyên" đó dựa vào một hành vi CÓ THẬT, đã đo (SQLAlchemy
    #    2.0.49, 23/09): `begin_nested()` **autoflush TRƯỚC** khi phát
    #    `SAVEPOINT`, nên mọi đối tượng còn treo của chuỗi tạo run (run, khoản
    #    giữ, wakeup, sự kiện) đã nằm NGOÀI savepoint này khi nó mở. Nếu không,
    #    `db.flush()` bên trong `jobs.submit` sẽ kéo chúng vào trong và
    #    `ROLLBACK TO` xoá luôn — đúng thứ bản sửa này phải tránh.
    #
    # ⛔ Bắt HẸP: chỉ đúng `ux_jobs_dedupe_active` (xem `_la_trung_khoa_dong_co`).
    #    Một vi phạm khoá ngoại hay một trùng khoá khác vẫn phải nổ.
    try:
        with db.begin_nested():
            jobs.submit(db, user_id=DONG_CO_USER, app_slug=chu_dong_co(),
                        job_type=DONG_CO_JOB, params={},
                        dedupe_key="workflow:dong_co",
                        max_attempts=3, origin=ORIGIN_WORKFLOW,
                        priority_class="internal")
    except IntegrityError as exc:
        if not _la_trung_khoa_dong_co(exc):
            raise
        # Người khác vừa tạo đúng thứ ta cần. Bất biến "chỉ MỘT job động cơ
        # đang sống" (plan 01a) được giữ CHẶT HƠN, không lỏng đi: chính chỉ mục
        # vừa từ chối hàng thứ hai.


def _tim(db, owner_id: str, khoa: str):
    return db.execute(select(WorkflowRun).where(
        WorkflowRun.owner_id == owner_id,
        WorkflowRun.idempotency_key == khoa)).scalars().first()


def tao_run(db, *, workflow: Workflow, owner_id: str, trigger_kind: str,
            idempotency_key: str, inputs: dict | None = None,
            ghim_version_id: str = "", chay_lai_tu_run_id: str = ""
            ) -> tuple[WorkflowRun, bool]:
    """Cửa tạo run DUY NHẤT (xem docstring đầu tệp).

    `ghim_version_id` — ghim một version **khác** bản publish hiện hành. Chỉ
    một bên gọi dùng: *"chạy lại từ node"* (§14), thứ phải chạy **đúng đồ thị
    của run cũ**. Chạy lại trên một đồ thị đã đổi là sao output của những node
    **có thể không còn tồn tại** sang một đồ thị **có thể không có chúng** —
    và không ai báo.

    ⛔ Version ghim phải thuộc **chính** workflow này. Không kiểm điều đó là mở
       một cửa ghim đồ thị của người khác vào một run của mình: `owner_id` của
       run đúng, `workflow_id` đúng, chỉ `graph` là của người lạ.

    `chay_lai_tu_run_id` — nguồn gốc, ghi thẳng vào cột cùng tên. ⛔ KHÔNG dùng
    `parent_run_id` thay: run con không có `hold_id` riêng, một lượt chạy lại
    **có**. Lượt chạy lại vẫn đi qua **toàn bộ** cửa này, nên nó vẫn giữ tiền
    một lần, vẫn chịu `MAX_RUN_DONG_THOI`, vẫn chống bấm hai lần.
    """
    if workflow.owner_id != owner_id:
        raise KhongCoBanPublish("workflow khong thuoc nguoi goi")
    if not workflow.published_version_id or workflow.archived_at is not None:
        raise KhongCoBanPublish("workflow chua publish hoac da luu tru")
    ver = db.get(WorkflowVersion, str(ghim_version_id or "")
                 or workflow.published_version_id)
    if ver is None:
        raise KhongCoBanPublish("version publish khong ton tai")
    if ver.workflow_id != workflow.id:
        raise KhongCoBanPublish("version khong thuoc workflow nay")

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
                estimated_max=int(ver.estimated_max or 0),
                chay_lai_tu_run_id=chay_lai_tu_run_id)
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
           "UX_JOBS_DEDUPE", "KhongCoBanPublish", "QuaHanMuc",
           "TrungKhoaKhacWorkflow", "chu_dong_co", "danh_thuc_dong_co",
           "tao_run"]
