"""
App `taovideo` — Tạo video AI (BytePlus ModelArk / Seedance 2.0). Di trú từ BOT
GEMINI `seedance_video` (Đợt A2). App VIDEO đầu tiên: async submit→poll, giá theo
token thật (giữ chỗ ước tính → quyết toán chính xác).

Slug đặt `taovideo` (không phải "seedance") vì "seedance" là brand model xuất hiện
trong `platform_core/providers.py` (byteplus) → test_60 chống hardcode-slug báo
nhầm. Bài học lặp lại: slug app phải là chuỗi RIÊNG, không trùng brand/model.

Pha 1 (bản này): text→video + ảnh tham chiếu inline (≤8MB), đủ model/độ phân giải/
thời lượng/tỉ lệ/audio + giá thật + serve video theo HTTP Range (né trần 100MB CF).
Pha 2 (sau): asset:// (ảnh/video lớn + người thật) + kiểm duyệt mặt tự động.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry, ToolSpec


def _cost(params: dict) -> int:
    """Giá GIỮ CHỖ = ước tính theo model/độ phân giải/thời lượng (token→VND→credit).
    Quyết toán chính xác theo token thật ở handler (worker hoàn phần dư)."""
    from apps.taovideo.cost import customer_charge_cap
    return customer_charge_cap(params)


MANIFEST = AppManifest(
    slug="taovideo",
    display_name=N_('Tạo Video Seedance'),
    route_prefix="/taovideo",
    summary=N_('Tạo video Seedance từ mô tả và tài sản tham chiếu. Tính phí theo token thật.'),
    icon="🎬",
    accent="#6A0DAD",

    nav=(NavEntry("Tạo Video Seedance", "/taovideo", "🎬", "taovideo"),),

    job_types=("taovideo.generate",),
    requires=("api",),
    credit_cost=_cost,
    tools=(ToolSpec(
        name="video.generate", job_type="taovideo.generate",
        description=N_('Sinh video Seedance từ mô tả và các tài sản tham chiếu tùy chọn.'),
        params_schema={
            "prompt": {"type": "string", "required": True, "max_length": 10000},
            "model": {"type": "model_ref", "category": "video", "providers": ["byteplus"]},
            "resolution": {"type": "enum", "depends_on": "model", "field": "resolutions"},
            "duration": {"type": "enum", "depends_on": "model", "field": "durations"},
            "aspect_ratio": {"type": "enum", "depends_on": "model", "field": "aspects"},
            "generate_audio": {"type": "bool", "default": True},
            "camera": {"type": "enum", "values": ["", "static", "dolly_in", "tracking", "orbit", "aerial", "handheld"], "default": ""},
            "motion": {"type": "enum", "values": ["", "subtle", "dynamic", "cinematic"], "default": ""},
            "visual_style": {"type": "enum", "values": ["", "realistic", "cinematic", "anime", "product"], "default": ""},
            "seed": {"type": "number", "min": 0, "max": 2147483647},
            "image_key": {"type": "image"},
            "image_keys": {"type": "image[]"},
            "video_key": {"type": "video"},
            "audio_key": {"type": "audio"},
            "refs": {"type": "json"},
        },
        returns={"video_key": "video"},
        verifiable=("technical", "vlm_judge"),
    ),),

    enabled=True,
    lifecycle="released",
    capabilities=("AI Video",),
    group="Video",
    badge="MỚI",
    notes="Di trú A2 từ seedance_video. Key qua APIKEYS (provider byteplus, category video).",
)
