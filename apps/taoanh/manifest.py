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

from platform_core.registry import AppManifest, NavEntry

CREDIT_PER_IMAGE = 5


def _cost(params: dict) -> int:
    try:
        count = int(params.get("count", 1))
    except (TypeError, ValueError):
        count = 1
    count = max(1, min(count, 4))
    return count * CREDIT_PER_IMAGE


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

    enabled=True,
    group="Ảnh",
    notes="Di trú A1 từ gemini_image. Key qua APIKEYS (provider gemini, category image).",
)
