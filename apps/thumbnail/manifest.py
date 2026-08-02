"""
App `thumbnail` — tạo thumbnail YouTube bằng Gemini Image API (H5, Q11).

Tool tính phí ĐẦU TIÊN của nền tảng. Chọn nó vì (KHAO_SAT_BOT_GEMINI mục 3):
API thuần ~5-15 giây (không đụng trần 100 giây của Cloudflare), kết quả là ảnh
vài MB (không đụng trần 100 MB) → chứng minh đủ chuỗi user → job → credit →
tải về mà chưa cần object storage R2.

Viết MỚI theo hợp đồng app (Q3) — chỉ tham chiếu `D:/BOT GEMINI/app/modules/
thumbnail_api`, KHÔNG kéo theo api-pool/cascade/prompt-fragment của họ. Khoá
Gemini đọc từ biến môi trường phía máy chủ (`GEMINI_API_KEY`), KHÔNG BAO GIỜ
xuống trình duyệt.
"""
from __future__ import annotations

from platform_core.registry import AppManifest, NavEntry, ToolSpec

# Số credit cho MỖI ảnh. Tạm cố định; khi cần chính xác theo token thật thì đọc
# `usageMetadata` Gemini trả về rồi quyết toán ở worker (mẫu: cost.py bên BOT
# GEMINI có markup + quy đổi VND). Gemini 2.5 Flash Image ~1290 token/ảnh.
CREDIT_PER_IMAGE = 5


def _cost(params: dict) -> int:
    """Giá credit = số ảnh × CREDIT_PER_IMAGE. LÀ HÀM (giá phụ thuộc tham số)."""
    try:
        count = int(params.get("count", 1))
    except (TypeError, ValueError):
        count = 1
    count = max(1, min(count, 4))
    return count * CREDIT_PER_IMAGE


MANIFEST = AppManifest(
    slug="thumbnail",
    display_name="Tạo Thumbnail YouTube",
    route_prefix="/thumbnail",
    summary="Sinh ảnh thumbnail YouTube từ mô tả bằng Gemini Image. "
            "Nhập chủ đề + tiêu đề, chọn tỉ lệ, nhận ảnh tải về.",
    icon="🖼️",
    accent="#C2410C",

    nav=(NavEntry("Tạo Thumbnail", "/thumbnail", "🖼️", "thumbnail"),),

    job_types=("thumbnail.generate",),
    requires=("api",),          # chỉ gọi API Gemini → chạy được ở cloud
    credit_cost=_cost,
    tools=(ToolSpec(
        name="image.thumbnail", job_type="thumbnail.generate",
        description="Sinh thumbnail YouTube có tiêu đề, phong cách và kiểu chữ.",
        params_schema={
            "topic": {"type": "string", "required": True, "max_length": 2000},
            "title": {"type": "string", "max_length": 200},
            "subtitle": {"type": "string", "max_length": 200},
            "text_style": {"type": "enum", "source": "prompts/text_style"},
            "phong_cach": {"type": "enum", "source": "prompts/phong_cach"},
            "kieu_trend": {"type": "enum", "source": "prompts/kieu_trend"},
            "ngon_ngu": {"type": "enum", "source": "prompts/ngon_ngu"},
            "model": {"type": "model_ref", "category": "image", "providers": ["gemini"]},
            "aspect_ratio": {"type": "enum", "values": ["16:9", "9:16", "1:1", "4:3", "3:4"], "default": "16:9"},
            "count": {"type": "int", "min": 1, "max": 4, "default": 1},
        },
        returns={"image_keys": "image[]", "prompt": "text"},
        verifiable=("vlm_judge",),
    ),),

    enabled=True,
    group="Ảnh",
    badge="MỚI",
    notes="Cần GEMINI_API_KEY trong secrets/app.env. Tool tính phí đầu tiên (H5).",
)
