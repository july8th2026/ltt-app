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

from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry, ToolSpec

# ⛔ GIÁ THEO TỪNG MODEL, không phải một giá phẳng. Sửa 2026-08-23.
#
#    Bản trước tính `count * 5` **bất kể model**, nên một ảnh vẽ bằng model đắt
#    nhất vẫn thu 5 credit. Đo được: giá vốn bậc `pro` là 35,2 credit ⇒ app này
#    lỗ **3.024đ mỗi ảnh**, nặng hơn cả `taoanh` (1.924đ) đúng vì giá phẳng.
#
#    Nguyên tắc chủ dự án chốt (D-042): **dùng model nào trả tiền model đó.**
#    Đây là app cuối cùng vi phạm nó.
#
#    Bảng giá giữ đúng con số của `apps/taoanh` — cùng model thì cùng giá, dù bán
#    qua tool nào. Hai bảng lệch nhau là khách tự tìm ra tool rẻ hơn cho cùng
#    một model, và đó là một lỗ hổng doanh thu chứ không phải một tính năng.
MODEL_CREDIT_PER_IMAGE = {
    "gemini-2.5-flash-image": 5,
    "gemini-3.1-flash-lite-image": 5,
    "gemini-3.1-flash-image": 8,
    "gemini-3.1-flash-image-preview": 8,
    # Bậc `pro` đã đóng ở `providers.py`; giữ giá để job CŨ tra lại vẫn ra đúng số.
    "gemini-3-pro-image": 16,
    "gemini-3-pro-image-preview": 16,
}

#: Đơn giá model mặc định (`jobs._MODEL`). Cũng là giá khi không biết model —
#: đường API ẩn tham số `model` nên nó luôn rơi vào nhánh này.
CREDIT_PER_IMAGE = 5


def unit_credit(model: str) -> int:
    return MODEL_CREDIT_PER_IMAGE.get(str(model or ""), CREDIT_PER_IMAGE)


def _cost(params: dict) -> int:
    """Giá credit = số ảnh × đơn giá CỦA MODEL ĐÓ. LÀ HÀM (giá phụ thuộc tham số)."""
    try:
        count = int(params.get("count", 1))
    except (TypeError, ValueError):
        count = 1
    count = max(1, min(count, 4))
    return count * unit_credit(params.get("model"))


MANIFEST = AppManifest(
    slug="thumbnail",
    display_name=N_('Tạo Thumbnail YouTube'),
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
        description=N_('Sinh thumbnail YouTube có tiêu đề, phong cách và kiểu chữ.'),
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

        # ── Public API (Q92, wave 1) ─────────────────────────────────────────
        api_exposed=True,
        api_contract={
            "scopes": ("jobs:create",),
            "description": ("Generate one to four YouTube thumbnail images from "
                            "a topic, with optional title text, style and "
                            "language."),
            # `model` stays hidden — but the ORIGINAL REASON EXPIRED on
            # 2026-08-23, so here is the current one.
            #
            # The old reason: this tool charged a flat CREDIT_PER_IMAGE whatever
            # the model, so an API caller picking the priciest model would buy a
            # 16-credit render for 5. That comment ended with "expose it the day
            # the cost function prices per model" — that day has come, and the
            # flat price is gone.
            #
            # It stays hidden anyway, for a different and smaller reason:
            # exposing it means publishing an ALIAS BLOCK (`standard`,
            # `enhanced`, ...) the way `image.generate` does, because a public
            # contract must never carry raw vendor model ids. That is a product
            # decision about what this tool sells, not a pricing fix, so it is
            # not smuggled in with one.
            #
            # Charging is now identical on both paths: the API path omits
            # `model`, so `unit_credit(None)` returns the default tier — the
            # exact model `jobs._MODEL` actually calls.
            "hidden": ("model",),
            # `count` decides how many images come back, so test mode returns
            # that many canned files instead of always one (EXT-12).
            "output_counts": {"image_keys": "count"},
            "params": {
                "topic": {
                    "description": ("What the thumbnail is about. The whole "
                                    "image is generated from this, so be "
                                    "specific about subject and mood."),
                    "example": "How to fix a leaking tap in 5 minutes",
                },
                "title": {
                    "description": ("Large text drawn on the image. Leave "
                                    "empty for an image with no text."),
                    "example": "5 MINUTE FIX",
                },
                "subtitle": {
                    "description": "Smaller supporting line under the title.",
                    "example": "no plumber needed",
                },
                "text_style": {
                    "description": ("How the text is drawn. Ignored when both "
                                    "title and subtitle are empty."),
                    "example": "bold_impact",
                },
                "phong_cach": {
                    "description": ("Visual style of the image itself. The "
                                    "name is Vietnamese because it is a stable "
                                    "identifier, not a label; the values are "
                                    "listed in `enum`."),
                    "example": "cinematic",
                },
                "kieu_trend": {
                    "description": ("Composition pattern — what makes the "
                                    "thumbnail work as a thumbnail (a reacting "
                                    "face, a before/after split, a numbered "
                                    "list, and so on)."),
                    "example": "khuon_mat_cam_xuc",
                },
                "ngon_ngu": {
                    "description": "Language of the text drawn on the image.",
                    "example": "english",
                },
                "aspect_ratio": {
                    "description": ("Shape of the output. 16:9 is the YouTube "
                                    "thumbnail shape."),
                    "example": "16:9",
                },
                "count": {
                    "description": ("How many variations to generate. Each one "
                                    "is charged, so a quote for count=4 costs "
                                    "four times a quote for count=1."),
                    "example": 2,
                },
            },
            # Published values are a curated subset of the internal prompt
            # library: the ones with stable, self-explanatory ids. The internal
            # set keeps entries named after people and experiments, which are
            # neither a promise to customers nor safe to freeze into a contract.
            "enums": {
                "text_style": ["bold_impact", "clean_minimal", "dramatic_gold",
                               "neon_glow", "street_art"],
                "phong_cach": ["chuyen_nghiep_toi_gian", "hoat_hinh_cartoon",
                               "cinematic", "flat_design", "3d_render",
                               "collage", "retro_vintage"],
                "kieu_trend": ["khuon_mat_cam_xuc", "so_sanh_truoc_sau",
                               "bi_an_gay_to_mo", "listicle_numbered",
                               "huong_dan_tutorial", "reaction_phan_ung",
                               "storytelling", "mui_ten_chi_dan",
                               "text_heavy_chu_lon"],
                "ngon_ngu": ["tieng_viet", "english", "japanese", "korean",
                             "chinese"],
            },
        },
    ),),

    enabled=True,
    lifecycle="development",
    capabilities=("AI Image",),
    catalog_parent="taoanh",
    group="Ảnh",
    badge="MỚI",
    notes="Cần GEMINI_API_KEY trong secrets/app.env. Tool tính phí đầu tiên (H5).",
)
