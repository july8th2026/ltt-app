"""Manifest for the orchestration UI; execution uses existing app ToolSpecs."""
from platform_core.registry import AppManifest, NavEntry

MANIFEST = AppManifest(
    slug="agent",
    display_name="LTT Agent AI",
    route_prefix="/agent",
    summary="Biến mục tiêu thành kế hoạch nhiều bước, báo giá trước và chạy có kiểm soát.",
    icon="✦",
    accent="#8B5CF6",
    nav=(NavEntry("LTT Agent AI", "/agent", "✦", "agent"),
         NavEntry("Canvas", "/agent/canvas", "◇", "agent_canvas")),
    enabled=True,
    public=True,
    group="AI Studio",
    badge="MỚI",
    notes="Agent/Canvas dùng chung Plan v1 và executor server-side.",
)
