"""Manifest for the orchestration UI; execution uses existing app ToolSpecs."""
from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry


def _orchestration_cost(_params: dict) -> int:
    return 0

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
)
