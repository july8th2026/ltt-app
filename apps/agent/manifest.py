"""Manifest for the orchestration UI; execution uses existing app ToolSpecs.

⚠️ `job_types` PHẢI đúng bằng `("agent.advance",)` — không thêm
   `workflow.dong_co` vào đây dù handler thật của nó (`_dong_co`) vẫn sống
   trong `jobs.py` cùng thư mục này. `test_190_public_api_coverage.py::
   test_the_agent_app_is_an_orchestrator_not_a_tool` chốt bất biến "`agent`
   là runtime điều phối, không phải bản thân một job_type động cơ" —
   `apps/agent_dong_co/manifest.py` mới là nơi khai job_type đó (chỉ đăng ký,
   gọi thẳng sang `apps.agent.jobs.handle`). Xem docstring ở đó.
"""
from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry


def _orchestration_cost(_params: dict) -> int:
    return 0


def _luoi_do_dong_co() -> None:
    """Mỗi 60 s: có wakeup tới hạn mà không có job động cơ chờ/chạy ⇒ nộp lại.
    KHÔNG ném (luật `bao_tri`).

    ⭐ Review chốt (final-review.md F1): bản cũ gọi `tao_run.danh_thuc_dong_co`
       VÔ ĐIỀU KIỆN mỗi 60 s — kể cả khi hệ thống không có run nào — nên ổn
       định ở ~1440 job `workflow.dong_co` rỗng/ngày mãi mãi. Docstring luôn
       nói "có wakeup tới hạn MÀ không có job động cơ chờ/chạy", nhưng code
       chỉ kiểm vế sau. Sửa: tự hỏi vế TRƯỚC (có `Wakeup` nào tới hạn, chưa ai
       nhặt) trước khi gọi `danh_thuc_dong_co` — hàm đó tự kiểm vế sau (job
       động cơ chưa kết thúc) như cũ. Lưới đỡ vẫn nguyên vẹn: nó chỉ bớt nộp
       khi THẬT SỰ không có việc gì tới hạn.
    """
    try:
        from datetime import datetime, timezone
        from sqlalchemy import select
        from platform_core.db import get_session
        from platform_core.models import Wakeup
        from platform_core.workflow import tao_run
        gen = get_session(); db = next(gen)
        try:
            bay_gio = datetime.now(timezone.utc).replace(tzinfo=None)
            ke = db.execute(select(Wakeup.id).where(
                Wakeup.claimed_at.is_(None), Wakeup.due_at <= bay_gio)
                .limit(1)).scalar()
            if ke is not None:
                tao_run.danh_thuc_dong_co(db)   # khử trùng job chưa kết thúc
            db.commit()
        finally:
            db.close()
    except Exception:                        # noqa: BLE001
        import logging
        logging.getLogger(__name__).exception("luoi do dong co")


MANIFEST = AppManifest(
    slug="agent",
    display_name="LTT Agent AI",
    route_prefix="/agent",
    summary=N_('Biến mục tiêu thành kế hoạch nhiều bước, báo giá trước và chạy có kiểm soát.'),
    icon="✦",
    accent="#8B5CF6",
    nav=(NavEntry("LTT Agent AI", "/agent", "✦", "agent"),
         NavEntry("Canvas", "/agent/canvas", "◇", "agent_canvas")),
    job_types=("agent.advance",),
    requires=("api",),
    credit_cost=_orchestration_cost,
    enabled=True,
    public=True,
    lifecycle="development",
    capabilities=("Automation",),
    group="AI Studio",
    badge="MỚI",
    notes="Agent/Canvas dùng chung Plan v1 và executor server-side.",
    bao_tri=_luoi_do_dong_co,
    bao_tri_moi_giay=60,
)
