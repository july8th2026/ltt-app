"""Job cua app Agent.

Sau cat chuyen §17 chi con MOT job: vong dong co Workflow V2. `agent.advance`
(vong tick cua Plan v1) da chet cung `platform_core/agent/executor.py`.

⚠️ `job_types` cua `workflow.dong_co` duoc khai o `apps/agent_dong_co/manifest.py`,
   KHONG o day — xem docstring tep do (bat bien `test_190`
   orchestrator-khong-phai-tool). Handler that van o day vi no dung chung than
   thi hanh voi phan con lai cua app.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def handle(params: dict, ctx=None) -> dict:
    # ⚠️ Phan nhanh theo `ctx.job_type`, KHONG theo `params` — `params` la tham
    #    so cua job (do ben nop dat), `ctx` la thu hang doi gan vao. Ban cu
    #    cung doc `ctx.job_type`; doi sang `params` o day se lam moi job dong
    #    co roi vao nhanh tu choi ma test don vi khong thay.
    job_type = str(getattr(ctx, "job_type", "") or "")
    if job_type == "workflow.dong_co":
        return _dong_co(ctx)
    raise ValueError(f"job_type khong thuoc app agent: {job_type!r}")


def _dong_co(ctx=None) -> dict:
    """Handler của `workflow.dong_co`: một vòng động cơ, rồi tự nộp lại nếu
    `mot_vong` báo còn việc (spec §5.1 — MỘT job động cơ chạy vòng, không phải
    một job mỗi run)."""
    from platform_core.db import get_session
    from platform_core.workflow import dong_co, tao_run

    def _mo():
        return next(get_session())
    kq = dong_co.mot_vong(_mo)
    if kq["con_viec"]:
        gen = get_session(); db = next(gen)
        try:
            tao_run.danh_thuc_dong_co(db)
            # Job hiện tại CHƯA kết thúc lúc này ⇒ dedupe của `danh_thuc_dong_co`
            # (khoá cố định `workflow:dong_co`) trả lại CHÍNH job đang chạy —
            # nên hẹn job KẾ TIẾP bằng một khoá riêng theo job hiện tại (khuôn
            # `agent.advance` ở trên).
            from platform_core import jobs as job_queue
            from platform_core.job_scheduler import ORIGIN_WORKFLOW
            job_next = job_queue.submit(
                db, user_id=tao_run.DONG_CO_USER,
                app_slug=tao_run.chu_dong_co(),
                job_type=tao_run.DONG_CO_JOB, params={},
                dedupe_key=f"workflow:dong_co:sau:{getattr(ctx, 'job_id', 'x')}",
                max_attempts=3, origin=ORIGIN_WORKFLOW, priority_class="internal")
            bay_gio = datetime.now(timezone.utc)
            han = kq["han_ke_tiep"]
            cho = timedelta(seconds=2)
            if han is not None:
                han = han.replace(tzinfo=timezone.utc)
                cho = max(timedelta(0), min(cho, han - bay_gio))
            job_next.next_run_at = bay_gio + cho
            db.commit()
        finally:
            db.close()
    return {"run_da_xu_ly": kq["run_da_xu_ly"], "con_viec": kq["con_viec"]}
