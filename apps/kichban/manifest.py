"""
App `kichban` — YouTube Script Generator. Di trú từ BOT GEMINI `youtube_script`
(Đợt A1). Sinh kịch bản có cấu trúc (hook/sections/outro/description/tags) qua
LLM. Đầu ra là VĂN BẢN/JSON (khác app ảnh) — kiểm chứng nhà máy cho app text.

Slug đặt là `kichban` (không phải "script") vì "script" là từ phổ biến trong code
nền tảng (script-src của CSP…) làm test chống hardcode-slug báo nhầm — slug phải
đặc trưng. Prompt ghép từ fragment `apps/kichban/prompts/` (5 độ dài · 6 giọng văn
· 6 đối tượng · 2 ngôn ngữ), KHÔNG hardcode. Key qua APIKEYS (gemini, category chat).
"""
from __future__ import annotations

from platform_core.registry import AppManifest, NavEntry, ToolSpec

CREDIT_PER_SCRIPT = 3


def _cost(params: dict) -> int:
    """Giá cố định mỗi kịch bản (text rẻ). LÀ HÀM theo hợp đồng."""
    return CREDIT_PER_SCRIPT


MANIFEST = AppManifest(
    slug="kichban",
    display_name="Kịch bản YouTube",
    route_prefix="/kichban",
    summary="AI viết kịch bản YouTube đầy đủ: hook, nội dung, outro, description, tags.",
    icon="📝",
    accent="#7C3AED",

    nav=(NavEntry("Kịch bản YouTube", "/kichban", "📝", "kichban"),),

    job_types=("kichban.generate",),
    requires=("api",),
    credit_cost=_cost,
    tools=(ToolSpec(
        name="text.script", job_type="kichban.generate",
        description="Viết kịch bản YouTube có hook, nội dung và metadata từ một chủ đề.",
        params_schema={
            "topic": {"type": "string", "required": True, "max_length": 4000},
            "duration": {"type": "enum", "source": "prompts/do_dai_video"},
            "tone": {"type": "enum", "source": "prompts/giong_van"},
            "audience": {"type": "enum", "source": "prompts/doi_tuong"},
            "language": {"type": "enum", "source": "prompts/ngon_ngu"},
        },
        returns={"script": "json"},
    ),),

    enabled=True,
    group="Kịch bản",
    notes="Di trú A1 từ youtube_script. Đầu ra text/JSON. Key qua APIKEYS (chat).",
)
