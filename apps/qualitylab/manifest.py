"""Manifest của Quality Lab operator-only."""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry


def _cost(_params: dict) -> int:
    """Evaluation nội bộ không trừ credit khách hàng."""
    return 0


MANIFEST = AppManifest(
    slug="qualitylab",
    display_name=N_("Quality Lab"),
    route_prefix="/qualitylab",
    summary=N_("Đo contract và chất lượng đầu ra bằng bằng chứng có phiên bản."),
    icon="📏",
    accent="#0E7C86",
    nav=(NavEntry(N_("Quality Lab"), "/qualitylab", "📏", "qualitylab"),),
    job_types=("qualitylab.evaluate",),
    requires=("ffmpeg",),
    credit_cost=_cost,
    enabled=True,
    public=False,
    surface="admin",
    lifecycle="internal",
    group=N_("Vận hành"),
    badge=N_("NỘI BỘ"),
    notes=N_("Operator-only; foundation evaluator không tải model lúc chạy."),
)
