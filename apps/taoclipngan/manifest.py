"""
App `taoclipngan` — Tạo Clip ngắn. Di trú engine `cutclipshort` từ D:\\FULL AUTO
VIDEO (kho chỉ đọc, NGOÀI BOT GEMINI). Video dài → nhiều clip ngắn dọc (highlight
+ reframe bám người + phụ đề). Nhóm GPU: whisper + YOLO + ffmpeg NVENC.

Chỉ lấy tính năng LÀM FILE TRỰC TIẾP (bỏ tự-động-từ-sheet, GUI, license). Engine
copy nguyên `cutclipshort/` ở gốc repo; worker gọi 3 hàm lõi. Slug là chuỗi riêng.
"""
from __future__ import annotations

from platform_core.registry import AppManifest, NavEntry, ToolSpec


def _cost(params: dict) -> int:
    from apps.taoclipngan.cost import uoc_luong_credit
    try:
        dur = float(params.get("duration_s", 0) or 0)
    except (TypeError, ValueError):
        dur = 0.0
    try:
        n = int(params.get("target_clip_count", 3) or 3)
    except (TypeError, ValueError):
        n = 3
    return uoc_luong_credit(dur, str(params.get("tier", "high_quality")), n)


MANIFEST = AppManifest(
    slug="taoclipngan",
    display_name="Tạo Clip ngắn",
    route_prefix="/taoclipngan",
    summary="Biến video dài thành nhiều clip ngắn dọc (TikTok/Shorts/Reels) — AI chọn highlight, reframe, phụ đề.",
    icon="✂️",
    accent="#C2185B",

    nav=(NavEntry("Tạo Clip ngắn", "/taoclipngan", "✂️", "taoclipngan"),),

    job_types=("taoclipngan.render",),
    requires=("gpu", "ffmpeg"),
    # whisper + YOLO nạp cùng lúc trong một lượt render.
    gpu_vram_mb={"taoclipngan.render": 6000},
    credit_cost=_cost,
    tools=(ToolSpec(
        name="video.short_clips", job_type="taoclipngan.render",
        description="Phân tích video dài và xuất nhiều clip ngắn có reframe, phụ đề.",
        params_schema={
            "video_key": {"type": "video", "required": True},
            "tier": {"type": "enum", "values": ["fast", "balanced", "high_quality"], "default": "high_quality"},
            "genre": {"type": "enum", "values": ["talking_head", "podcast", "interview", "storytelling", "comedy", "education", "news_commentary", "review", "history", "kids_music"], "default": "talking_head"},
            "aspect_ratio": {"type": "enum", "values": ["9:16", "1:1", "16:9", "4:5"], "default": "9:16"},
            "language": {"type": "enum", "values": ["", "vi", "en"], "default": ""},
            "target_clip_count": {"type": "int", "min": 1, "max": 10, "default": 3},
            "min_clip_duration_sec": {"type": "number", "min": 5, "max": 180, "default": 15},
            "max_clip_duration_sec": {"type": "number", "min": 5, "max": 300, "default": 60},
            "duration_s": {"type": "number", "min": 0},
            "brand_preset": {"type": "enum", "values": ["auto", "ltt_red", "creator_clean", "cinematic"], "default": "auto"},
            "platforms": {"type": "json", "default": ["tiktok", "youtube_shorts", "instagram_reels"]},
        },
        # Handler trả metadata từng clip ({video_key,title,score,duration_s}).
        returns={"clips": "json"},
        verifiable=("technical", "vlm_judge"),
    ),),

    enabled=True,
    group="Video",
    badge="MỚI",
    notes="Di trú engine cutclipshort (D:/FULL AUTO VIDEO). GPU: whisper+YOLO. Job dài.",
)
