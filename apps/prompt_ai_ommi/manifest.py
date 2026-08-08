"""Manifest for PROMPT AI OMMI (Q65/H19)."""
from __future__ import annotations

from platform_core.i18n import N_
import math

from platform_core.registry import AppManifest, NavEntry, ToolSpec


def _director_cost(params: dict) -> int:
    try:
        scenes = max(1, min(20, int(params.get("scene_count", 6))))
    except (TypeError, ValueError):
        scenes = 6
    return max(4, min(18, 2 + math.ceil(scenes / 3) * 2))


def _cost(params: dict) -> int:
    kind = str(params.get("operation") or "director")
    if kind == "storyboard":
        try:
            scenes = max(1, min(20, int(params.get("scene_count", 6))))
        except (TypeError, ValueError):
            scenes = 6
        return max(3, min(12, 2 + math.ceil(scenes / 4) * 2))
    if kind == "batch":
        try:
            count = max(1, min(8, int(params.get("batch_count", 1))))
        except (TypeError, ValueError):
            count = 1
        return _director_cost(params) * count
    return _director_cost(params)


MANIFEST = AppManifest(
    slug="prompt_ai_ommi",
    display_name="Prompt AI",
    route_prefix="/prompt-ai-ommi",
    summary=("Studio AI biến brief và tài sản tham chiếu thành prompt nhiều cảnh, "
             "storyboard và gói sản xuất nhất quán."),
    icon="✦",
    accent="#E53935",
    nav=(NavEntry("Prompt AI", "/prompt-ai-ommi", "✦", "prompt_ai_ommi"),),
    job_types=("prompt_ai_ommi.generate",),
    requires=("api",),
    credit_cost=_cost,
    tools=(
        ToolSpec(
            name="text.prompt_package",
            job_type="prompt_ai_ommi.generate",
            description=("Chuyển brief thành gói prompt nhiều cảnh có camera, ánh sáng, "
                         "continuity và negative prompt."),
            params_schema={
                "operation": {"type": "enum", "values": ["director"],
                              "default": "director"},
                "title": {"type": "string", "required": True, "max_length": 160},
                "story": {"type": "text", "required": True, "max_length": 12000},
                "scene_count": {"type": "int", "min": 1, "max": 20, "default": 6},
                "duration_seconds": {"type": "int", "min": 3, "max": 600,
                                     "default": 30},
                "aspect_ratio": {"type": "enum",
                                 "values": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
                                 "default": "16:9"},
                "style": {"type": "string", "max_length": 500},
                "audience": {"type": "string", "max_length": 300},
                "language": {"type": "enum", "values": ["vi", "en"], "default": "vi"},
                "resources": {"type": "json"},
                "model": {"type": "model_ref", "category": "chat",
                          "providers": ["gemini"]},
            },
            returns={"prompt_package": "json", "master_prompt": "text"},
            verifiable=("structural",),
        ),
        ToolSpec(
            name="story.storyboard",
            job_type="prompt_ai_ommi.generate",
            description=("Phân rã câu chuyện thành storyboard shot list có bố cục, "
                         "camera, continuity và prompt hình ảnh."),
            params_schema={
                "operation": {"type": "enum", "values": ["storyboard"],
                              "default": "storyboard"},
                "title": {"type": "string", "required": True, "max_length": 160},
                "story": {"type": "text", "required": True, "max_length": 12000},
                "scene_count": {"type": "int", "min": 1, "max": 20, "default": 6},
                "aspect_ratio": {"type": "enum",
                                 "values": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
                                 "default": "16:9"},
                "style": {"type": "string", "max_length": 500},
                "resources": {"type": "json"},
                "model": {"type": "model_ref", "category": "chat",
                          "providers": ["gemini"]},
            },
            returns={"storyboard": "json", "master_prompt": "text"},
            verifiable=("structural",),
        ),
    ),
    # Kho tài nguyên và thư viện prompt dùng chung giữa nhiều project nên không
    # vừa trong `AppProject` JSON — app sở hữu bảng riêng, xem `tables.py`.
    table_prefix="ommi",
    enabled=True,
    public=True,
    lifecycle="released",
    capabilities=("Chat & Prompt", "Automation"),
    group="AI Studio",
    badge="MỚI",
    notes="H19/Q65: replatform Prompt Seedance Studio trên AppProject/Job/Credit/Storage.",
)

