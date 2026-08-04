"""
App `taoanh` — Tạo ảnh AI từ mô tả (Gemini Image). Di trú từ BOT GEMINI
`app/modules/gemini_image` (Đợt A1, xem CONG_THUC_DI_TRU_APP.md).

Slug đặt là `taoanh` (không phải "image") vì slug phải là chuỗi RIÊNG — "image"
là từ phổ biến trong code nền tảng (image/png, category image…) làm test chống
hardcode-slug (`test_60`) báo nhầm. Bài học: slug app phải đặc trưng.

Gốc: prompt tự do (không catalog), chọn model + tỉ lệ + số ảnh. Giữ trung thành
UI/tính năng, chỉ đổi vỏ + hạ tầng (key qua APIKEYS, lưu qua storage, tính credit).
"""
from __future__ import annotations

from platform_core.registry import AppManifest, NavEntry, ToolSpec

MODEL_CREDIT_PER_IMAGE = {
    "gemini-2.5-flash-image": 5,
    "gemini-3.1-flash-lite-image": 5,
    "gemini-3.1-flash-image": 8,
    "gemini-3.1-flash-image-preview": 8,
    "gemini-3-pro-image": 16,
    "gemini-3-pro-image-preview": 16,
}
CREDIT_PER_IMAGE = 5  # tương thích code/test cũ: đơn giá model mặc định


def unit_credit(model: str) -> int:
    return MODEL_CREDIT_PER_IMAGE.get(str(model or ""), CREDIT_PER_IMAGE)


def _cost(params: dict) -> int:
    try:
        count = int(params.get("count", 1))
    except (TypeError, ValueError):
        count = 1
    count = max(1, min(count, 4))
    return count * unit_credit(str(params.get("model") or ""))


MANIFEST = AppManifest(
    slug="taoanh",
    display_name="Tạo ảnh AI",
    route_prefix="/taoanh",
    summary="Sinh ảnh từ mô tả tự do bằng Gemini Image. Chọn model, tỉ lệ, số ảnh.",
    icon="🎨",
    accent="#0EA5E9",

    nav=(NavEntry("Tạo ảnh AI", "/taoanh", "🎨", "taoanh"),),

    job_types=("taoanh.generate",),
    requires=("api",),
    credit_cost=_cost,
    tools=(ToolSpec(
        name="image.generate", job_type="taoanh.generate",
        description="Sinh từ một đến bốn ảnh bằng Gemini Image từ mô tả tự do.",
        params_schema={
            "prompt": {"type": "string", "required": True, "max_length": 4000},
            "image_key": {"type": "image", "required": False},
            "image_keys": {"type": "image[]", "required": False},
            "model": {"type": "model_ref", "category": "image", "providers": ["gemini"]},
            "aspect_ratio": {"type": "enum", "values": ["16:9", "9:16", "1:1", "4:3", "3:4"], "default": "16:9"},
            "count": {"type": "int", "min": 1, "max": 4, "default": 1},
        },
        returns={"image_keys": "image[]", "prompt": "text"},
        verifiable=("vlm_judge",),
    ), ToolSpec(
        name="image.batch_generate", job_type="taoanh.generate",
        description="Sinh một lô 2–4 ảnh đồng nhất từ cùng mô tả và model.",
        params_schema={
            "prompt": {"type": "string", "required": True, "max_length": 4000},
            "image_key": {"type": "image", "required": False},
            "image_keys": {"type": "image[]", "required": False},
            "model": {"type": "model_ref", "category": "image", "providers": ["gemini"]},
            "aspect_ratio": {"type": "enum", "values": ["16:9", "9:16", "1:1", "4:3", "3:4"], "default": "16:9"},
            "count": {"type": "int", "min": 2, "max": 4, "default": 4},
        },
        returns={"image_keys": "image[]", "prompt": "text"},
        verifiable=("vlm_judge",),
    )),

    enabled=True,
    group="Ảnh",
    notes="Di trú A1 từ gemini_image. Key qua APIKEYS (provider gemini, category image).",
)
