"""
App `upscalevideo` — Nâng cấp video (Real-ESRGAN NCNN ×4), di trú từ BOT GEMINI
`video_upscale` (Đợt C, nhóm GPU). Vendor engine (exe+model ~49MB) copy trong
`apps/upscalevideo/vendor/engine/` (gitignored) — nền tảng cũng chạy Windows nên
dùng thẳng binary Windows.

Bản chất: tách frame → Real-ESRGAN ×4 → encode lại (NVENC, fallback CPU) → giữ
tỉ lệ/FPS/audio. Giá theo phút × độ phân giải × preset (người dùng chốt 2026-08-01).

Slug `upscalevideo` (chuỗi riêng). Upload video lớn đi thẳng browser→R2 (P1).
Dùng chung `platform_core.media` + hạ tầng video của autosubvideo.

**Điểm dùng lại cho seedance**: `apps.upscalevideo.service.submit_upscale_job()` —
taovideo sẽ gọi để "Nâng cấp 4K" video Seedance mà KHÔNG nhân đôi code (theo yêu
cầu người dùng: "upscale cho seedance lấy code từ app upscale").
"""
from __future__ import annotations

from platform_core.registry import AppManifest, NavEntry, ToolSpec


def _cost(params: dict) -> int:
    """Giá GIỮ CHỖ theo thời lượng client khai; worker đo lại thật + nâng giữ chỗ."""
    from apps.upscalevideo.cost import uoc_luong_credit
    try:
        dur = float(params.get("duration_s", 0) or 0)
    except (TypeError, ValueError):
        dur = 0.0
    return uoc_luong_credit(dur, int(params.get("target_height", 1080) or 1080),
                            str(params.get("preset", "fast")),
                            bool(params.get("preview")))


MANIFEST = AppManifest(
    slug="upscalevideo",
    display_name="Nâng cấp video",
    route_prefix="/upscalevideo",
    summary="Nâng nét video lên 1080p/2K/4K bằng AI (Real-ESRGAN). Giữ tỉ lệ, FPS, âm thanh.",
    icon="🔍",
    accent="#B4530A",

    nav=(NavEntry("Nâng cấp video", "/upscalevideo", "🔍", "upscalevideo"),),

    job_types=("upscalevideo.render",),
    requires=("gpu", "ffmpeg"),
    credit_cost=_cost,
    tools=(ToolSpec(
        name="video.upscale", job_type="upscalevideo.render",
        description="Nâng độ nét video lên 1080p, 2K hoặc 4K bằng Real-ESRGAN.",
        params_schema={
            "video_key": {"type": "video", "required": True},
            "preset": {"type": "enum", "values": ["fast", "quality"], "default": "fast"},
            "target_height": {"type": "enum", "values": [1080, 1440, 2160], "default": 1080},
            "codec": {"type": "enum", "values": ["h264", "hevc"], "default": "h264"},
            "preview": {"type": "bool", "default": False},
            "duration_s": {"type": "number", "min": 0},
        },
        returns={"video_key": "video"},
        verifiable=("technical",),
    ),),

    enabled=True,
    group="Video",
    badge="MỚI",
    notes="Di trú Đợt C từ video_upscale. Cần GPU NVIDIA + vendor engine. Job GPU dài.",
)
