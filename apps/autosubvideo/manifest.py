"""
App `autosubvideo` — Khắc phụ đề vào video (di trú từ BOT GEMINI `auto_sub_video`,
Đợt B). Nhóm `ffmpeg`: burn ASS bằng ffmpeg + libass, có fallback CPU libx264.

Bản chất (người dùng chốt 2026-08-01): **KHÔNG nghe-chép** — người dùng NẠP sẵn
transcript (.srt/.json/.vtt/.ass), app dựng phụ đề theo preset rồi khắc vào video.
(Whisper tự tạo phụ đề để dành fast-follow nếu cần.)

Slug đặt `autosubvideo` (chuỗi riêng, không trùng brand/model) theo bài học slug.
Upload video lớn đi thẳng browser→R2 (presigned PUT, P1) — né trần 100MB Cloudflare.
"""
from __future__ import annotations

from platform_core.registry import AppManifest, NavEntry, ToolSpec


def _cost(params: dict) -> int:
    """Giá GIỮ CHỖ = ước tính theo thời lượng client khai + mức chất lượng.
    Worker đo lại thời lượng THẬT, nâng giữ chỗ nếu thiếu rồi quyết toán đúng giá
    thật (chống khai gian thời lượng để trả rẻ)."""
    from apps.autosubvideo.cost import uoc_luong_credit
    try:
        dur = float(params.get("duration_s", 0) or 0)
    except (TypeError, ValueError):
        dur = 0.0
    quality = str(params.get("quality", "standard"))
    return uoc_luong_credit(dur, quality)


MANIFEST = AppManifest(
    slug="autosubvideo",
    display_name="Khắc phụ đề video",
    route_prefix="/autosubvideo",
    summary="Nạp video + transcript (.srt/.json), chọn kiểu chữ, khắc phụ đề đẹp vào video.",
    icon="💬",
    accent="#0E7C86",

    nav=(NavEntry("Khắc phụ đề video", "/autosubvideo", "💬", "autosubvideo"),),

    job_types=("autosubvideo.render",),
    requires=("ffmpeg",),
    credit_cost=_cost,
    tools=(ToolSpec(
        name="video.subtitle", job_type="autosubvideo.render",
        description="Khắc transcript có sẵn vào video bằng preset phụ đề và FFmpeg.",
        params_schema={
            "video_key": {"type": "video", "required": True},
            "transcript": {"type": "json", "required": True},
            "style_id": {"type": "enum", "values": ["default", "tiktok_bold", "reels_clean", "cinematic", "meme_punch", "kids_color", "punchline", "word_emphasis"], "default": "default"},
            "segment_mode": {"type": "enum", "values": ["sentence", "phrase", "short_form", "punchline", "word_emphasis"], "default": "sentence"},
            "quality": {"type": "enum", "values": ["draft", "standard", "high"], "default": "standard"},
            "output_format": {"type": "enum", "values": ["mp4", "mkv", "webm"], "default": "mp4"},
            "export_srt": {"type": "bool", "default": True},
            "duration_s": {"type": "number", "min": 0},
        },
        returns={"video_key": "video", "srt_key": "text", "ass_key": "text"},
        verifiable=("technical",),
    ),),

    enabled=True,
    group="Video",
    badge="MỚI",
    notes="Di trú Đợt B từ auto_sub_video. Cần transcript nạp sẵn; burn ffmpeg+libass.",
)
