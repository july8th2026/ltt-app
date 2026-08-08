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

from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry, ToolSpec

CREDIT_PER_SCRIPT = 3
CREDIT_PER_VISION_TEXT = 4
CREDIT_PER_VIDEO_TEXT = 6


def _cost(params: dict) -> int:
    """Giá theo modality đầu vào; server là nguồn báo giá duy nhất."""
    if params.get("video_key"):
        return CREDIT_PER_VIDEO_TEXT
    if params.get("image_key") or params.get("image_keys"):
        return CREDIT_PER_VISION_TEXT
    return CREDIT_PER_SCRIPT


MANIFEST = AppManifest(
    slug="kichban",
    display_name=N_('Kịch bản YouTube'),
    route_prefix="/kichban",
    summary=N_('AI viết kịch bản YouTube đầy đủ: hook, nội dung, outro, description, tags.'),
    icon="📝",
    accent="#7C3AED",

    nav=(NavEntry("Kịch bản YouTube", "/kichban", "📝", "kichban"),),

    job_types=("kichban.generate",),
    requires=("api",),
    credit_cost=_cost,
    tools=(ToolSpec(
        name="text.script", job_type="kichban.generate",
        description=N_('Viết kịch bản YouTube có hook, nội dung và metadata từ một chủ đề.'),
        params_schema={
            "topic": {"type": "string", "required": True, "max_length": 4000},
            "duration": {"type": "enum", "source": "prompts/do_dai_video"},
            "tone": {"type": "enum", "source": "prompts/giong_van"},
            "audience": {"type": "enum", "source": "prompts/doi_tuong"},
            "language": {"type": "enum", "source": "prompts/ngon_ngu"},
        },
        returns={"script": "json"},
        customer_visible=False,
    ), ToolSpec(
        name="text.generate", job_type="kichban.generate",
        description=N_('Sinh văn bản đa dụng từ chỉ dẫn, có thể chọn định dạng đầu ra.'),
        params_schema={
            "prompt": {"type": "string", "required": True, "max_length": 12000},
            "source_text": {"type": "text", "max_length": 32000},
            "image_key": {"type": "image"},
            "image_keys": {"type": "image[]"},
            "video_key": {"type": "video"},
            "model": {"type": "model_ref", "category": "chat", "providers": ["gemini"]},
            "format": {"type": "enum", "values": ["plain", "markdown", "json"], "default": "markdown"},
        },
        returns={"text": "text"},
    )),

    enabled=True,
    public=False,
    surface="runtime",
    lifecycle="retired",
    group="Kịch bản",
    notes="Di trú A1 từ youtube_script. Đầu ra text/JSON. Key qua APIKEYS (chat).",
)
