"""Manifest for the orchestration UI; execution uses existing app ToolSpecs."""
from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry


def _orchestration_cost(_params: dict) -> int:
    return 0


def _luoi_do_dong_co() -> None:
    """Mỗi 60 s: có wakeup tới hạn mà không có job động cơ chờ/chạy ⇒ nộp lại.
    KHÔNG ném (luật `bao_tri`)."""
    try:
        from platform_core.db import get_session
        from platform_core.workflow import tao_run
        gen = get_session(); db = next(gen)
        try:
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
    job_types=("agent.advance", "workflow.dong_co"),
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
