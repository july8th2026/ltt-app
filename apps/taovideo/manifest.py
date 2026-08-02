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

from platform_core.registry import AppManifest, NavEntry, ToolSpec


def _cost(params: dict) -> int:
    """Giá GIỮ CHỖ = ước tính theo model/độ phân giải/thời lượng (token→VND→credit).
    Quyết toán chính xác theo token thật ở handler (worker hoàn phần dư)."""
    from apps.taovideo.cost import uoc_luong_credit
    from apps.taovideo.models import DEFAULT_MODEL
    model = params.get("model") or DEFAULT_MODEL
    resolution = params.get("resolution", "480p")
    try:
        duration = int(params.get("duration", 5))
    except (TypeError, ValueError):
        duration = 5
    # GIỮ CHỖ bảo thủ ×1.25: ước tính token calib 1 điểm; token THẬT có thể vượt →
    # nếu giữ chỗ sát quá, quyết toán (token thật) đẩy số dư ÂM. Đệm 25% để held ≥ thật
    # trong hầu hết trường hợp; quyết toán vẫn theo token thật (hoàn phần dư).
    import math
    est = uoc_luong_credit(model, resolution, duration,
                           bool(params.get("has_video_input")))
    return max(1, math.ceil(est * 1.25))


MANIFEST = AppManifest(
    slug="taovideo",
    display_name="Tạo video AI",
    route_prefix="/taovideo",
    summary="Sinh video từ mô tả (+ảnh tham chiếu) bằng Seedance 2.0. Tính phí theo token thật.",
    icon="🎬",
    accent="#6A0DAD",

    nav=(NavEntry("Tạo video AI", "/taovideo", "🎬", "taovideo"),),

    job_types=("taovideo.generate",),
    requires=("api",),
    credit_cost=_cost,
    tools=(ToolSpec(
        name="video.generate", job_type="taovideo.generate",
        description="Sinh video Seedance từ mô tả và các tài sản tham chiếu tùy chọn.",
        params_schema={
            "prompt": {"type": "string", "required": True, "max_length": 10000},
            "model": {"type": "model_ref", "category": "video", "providers": ["byteplus"]},
            "resolution": {"type": "enum", "depends_on": "model", "field": "resolutions"},
            "duration": {"type": "enum", "depends_on": "model", "field": "durations"},
            "aspect_ratio": {"type": "enum", "depends_on": "model", "field": "aspects"},
            "generate_audio": {"type": "bool", "default": True},
            "refs": {"type": "json"},
        },
        returns={"video_key": "video"},
        verifiable=("technical", "vlm_judge"),
    ),),

    enabled=True,
    group="Video",
    badge="MỚI",
    notes="Di trú A2 từ seedance_video. Key qua APIKEYS (provider byteplus, category video).",
)
