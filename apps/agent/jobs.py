"""App-owned orchestration jobs over the shared Agent executor.

`_dong_co` here handles `workflow.dong_co`, but that job_type is declared in
`apps/agent_dong_co/manifest.py`, NOT in this app's manifest — `apps/agent`
must keep `job_types == ("agent.advance",)` (see manifest.py docstring). The
handler stays in this module because it shares the executor plumbing with
`agent.advance`; `apps.agent_dong_co.jobs.handle` just calls this file's
`handle()`.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from platform_core.agent import executor
from platform_core.db import get_session
from platform_core.models import AGENT_RUNNING


def advance(db: Session, *, run_id: str, user_id: str):
    """Advance one orchestration tick; called by the CSRF-protected progress POST."""
    return executor.tick(db, run_id=run_id, user_id=user_id)


def handle(params: dict, ctx=None) -> dict:
    """Advance once, then durably enqueue the next tick while the run is active."""
    if str(getattr(ctx, "job_type", "") or "") == "workflow.dong_co":
        return _dong_co(ctx)
    run_id, user_id = str(params.get("run_id", "")), str(params.get("user_id", ""))
    if not run_id or not user_id:
        raise ValueError(_t('Thiếu run_id/user_id cho agent.advance.'))
    gen = get_session(); db = next(gen)
    try:
        from platform_core import jobs as job_queue
        from platform_core.agent import runs
        run = runs.get_owned(db, run_id, user_id, lock=True)
        if run.status == AGENT_RUNNING:
            run = advance(db, run_id=run.id, user_id=user_id)
        if run.status == AGENT_RUNNING:
            suffix = getattr(ctx, "job_id", "manual")
            followup = job_queue.submit(
                db, user_id=user_id, app_slug="agent", job_type="agent.advance",
                params={"run_id": run_id, "user_id": user_id},
                dedupe_key=f"agent:advance:{run_id}:after:{suffix}", max_attempts=3,
            )
            followup.next_run_at = datetime.now(timezone.utc) + timedelta(seconds=2)
        db.commit()
        return {"run_id": run.id, "status": run.status}
    finally:
        db.close()


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
