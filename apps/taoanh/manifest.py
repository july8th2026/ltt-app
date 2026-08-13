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

from platform_core.i18n import N_
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
    display_name=N_('Tạo ảnh AI'),
    route_prefix="/taoanh",
    summary=N_('Sinh ảnh từ mô tả tự do bằng Gemini Image. Chọn model, tỉ lệ, số ảnh.'),
    icon="🎨",
    accent="#0EA5E9",

    nav=(NavEntry("Tạo ảnh AI", "/taoanh", "🎨", "taoanh"),),

    job_types=("taoanh.generate",),
    requires=("api",),
    credit_cost=_cost,
    tools=(ToolSpec(
        name="image.generate", job_type="taoanh.generate",
        description=N_('Sinh từ một đến bốn ảnh bằng Gemini Image từ mô tả tự do.'),
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

        # ── Public API (Q92, wave 1) ─────────────────────────────────────────
        api_exposed=True,
        api_contract={
            "scopes": ("jobs:create",),
            "description": ("Generate one to four images from a text prompt, "
                            "optionally guided by one reference image."),
            # Aliases, never provider model ids: the public contract must not
            # name the vendor, and it must survive the day a model id changes.
            # The alias names describe what a caller is buying (quality tier),
            # which is also what `_cost` prices — so quote, charge and choice
            # all move together.
            # An alias may be a bare internal id or carry the metadata a caller
            # needs to choose between aliases. What it must never carry is
            # anything a customer could use to identify or reach the vendor
            # directly — the descriptions below say what you get, not who makes
            # it.
            "models": {
                "standard": {
                    "id": "gemini-2.5-flash-image",
                    "description": "Balanced quality and cost. Start here.",
                    "stability": "stable",
                },
                "standard-lite": {
                    "id": "gemini-3.1-flash-lite-image",
                    "description": ("Same price as standard, tuned for speed "
                                    "over detail."),
                    "stability": "stable",
                },
                "enhanced": {
                    "id": "gemini-3.1-flash-image",
                    "description": ("Better prompt adherence and fine detail "
                                    "than standard."),
                    "stability": "stable",
                },
                "pro": {
                    "id": "gemini-3-pro-image",
                    "description": ("Highest fidelity; use when the result is "
                                    "the deliverable."),
                    "stability": "stable",
                },
            },
            # One reference image is supported through the public upload flow;
            # the multi-image form is a Canvas/UI path that takes a list, and
            # the API media contract handles single references only today.
            "hidden": ("image_keys",),
        },
    ), ToolSpec(
        name="image.batch_generate", job_type="taoanh.generate",
        description=N_('Sinh một lô 2–4 ảnh đồng nhất từ cùng mô tả và model.'),
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
    lifecycle="development",
    capabilities=("AI Image",),
    group="Ảnh",
    notes="Di trú A1 từ gemini_image. Key qua APIKEYS (provider gemini, category image).",
)
