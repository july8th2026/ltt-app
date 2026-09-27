"""
App `thumbnail` — tạo thumbnail YouTube bằng **LTT_IMAGE** (H5, Q11).

🔴 DI TRÚ 09/09/2026 (AI CLEAN REBUILD V2 pha 06.3). Động cơ đổi từ Gemini
   Image sang model nhà, và **tính năng chữ-trong-ảnh bị gỡ** cùng lúc —
   model nhà không vẽ được chữ. Xem khối đầu `jobs.py` và
   `docs/AI_CLEAN_REBUILD/PHA06_THUMBNAIL_CHU.md`.

Tool tính phí ĐẦU TIÊN của nền tảng. Chọn nó vì (KHAO_SAT_BOT_GEMINI mục 3):
API thuần ~5-15 giây (không đụng trần 100 giây của Cloudflare), kết quả là ảnh
vài MB (không đụng trần 100 MB) → chứng minh đủ chuỗi user → job → credit →
tải về mà chưa cần object storage R2.

Viết MỚI theo hợp đồng app (Q3) — chỉ tham chiếu `D:/BOT GEMINI/app/modules/
thumbnail_api`, KHÔNG kéo theo api-pool/cascade/prompt-fragment của họ. Nay
app **không giữ khoá nào**: máy B nhận vé presigned do nền tảng cấp (Q102).
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.llm.residency import THEO_LO
from platform_core.registry import (AdmissionModel, AppManifest, NavEntry,
                                    ToolSpec)

# ── Cư trú RTX 3090 (dual-model D01 B, Task 5.5) ─────────────────────────────
#
# Ba bản khai giống nhau ở ba app ảnh là **hình dạng đúng duy nhất**, không phải
# một chỗ chép: nền tảng không được biết tên app (`test_147`) nên tên nhóm không
# sống được ở `platform_core`, và ba app không import được nhau (`.importlinter`).
# Lý do đầy đủ ở `apps/anhnoibo/manifest.py`; `tests/test_1219_residency_noi.py`
# chốt cả ba trùng nhau và trùng `NHOM_CU_TRU_38` của `apps/ltt_llm/ngan_sach.py`.
#
# ⛔ `vai_tro` lấy từ hằng số `residency.THEO_LO`, không gõ chuỗi — `mo_cho` NÉM
#    với vai lạ, và nay nó ném từ trong cửa admission.
NHOM_CU_TRU_ANH = "rtx3090"
TAI_NGUYEN_ANH = "anh_3090"
SUAT_ANH = 1
KHAI_CU_TRU_ANH = {"*": AdmissionModel(TAI_NGUYEN_ANH, SUAT_ANH, 0,
                                       NHOM_CU_TRU_ANH, THEO_LO)}

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
#: ⛔ BẢNG NÀY NAY CHỈ ĐỂ **TRA LẠI JOB CŨ**. Từ pha 06.3 app chạy
#:    `hidream-o1`, và giá của model đó ở `platform_core.image_gen.gia` —
#:    một chỗ duy nhất mà `anhnoibo` và `taoanh` cũng đọc. Thêm `hidream-o1`
#:    vào đây là dựng lại đúng cái bảng giá thứ hai mà chú thích dưới cảnh báo.
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
    """Trần giữ chỗ. Đọc bảng giá MODEL NHÀ — cùng hàm `anhnoibo`/`taoanh` gọi.

    ⚠️ Ảnh có tham chiếu (remix) đắt gấp 3 vì máy vẽ lâu gấp ~3,3 lần, nên
       trần phải biết có tham chiếu hay không, không chỉ biết số ảnh.
    """
    from platform_core.image_gen import gia

    try:
        count = int(params.get("count", 1))
    except (TypeError, ValueError):
        count = 1
    che_do = "edit" if str(params.get("reference_key") or "") else "t2i"
    return gia.uoc_tran(so_anh_xin=count, che_do=che_do)


MANIFEST = AppManifest(
    slug="thumbnail",
    display_name=N_('Tạo Thumbnail YouTube'),
    route_prefix="/thumbnail",
    summary="Sinh ảnh nền thumbnail YouTube từ mô tả, bằng model nội bộ. "
            "Ảnh KHÔNG có chữ — chữ thêm bằng công cụ chỉnh sửa của bạn.",
    icon="🖼️",
    accent="#C2410C",

    nav=(NavEntry("Tạo Thumbnail", "/thumbnail", "🖼️", "thumbnail"),),

    job_types=("thumbnail.generate",),
    requires=("api",),          # chỉ gọi HTTP tới cổng render → chạy được ở cloud
    credit_cost=_cost,
    tools=(ToolSpec(
        name="image.thumbnail", job_type="thumbnail.generate",
        description=N_('Sinh ảnh nền thumbnail YouTube theo phong cách và bố cục.'),
        ten_ngan=N_('Sinh ảnh nền Thumbnail'),
        admission_theo_model=KHAI_CU_TRU_ANH,      # cư trú 3090 — xem đầu tệp
        # 🔴 BỐN THAM SỐ ĐÃ GỠ Ở PHA 06.3: `title`, `subtitle`, `text_style`,
        #    `ngon_ngu`. Cả bốn chỉ phục vụ chữ vẽ trong ảnh — thứ model nhà
        #    không làm được (`capabilities["canh_bao"]` + D-048). Giữ chúng
        #    lại trong hợp đồng là bán một năng lực không còn.
        params_schema={
            "topic": {"type": "string", "required": True, "max_length": 2000},
            "phong_cach": {"type": "enum", "source": "prompts/phong_cach"},
            "kieu_trend": {"type": "enum", "source": "prompts/kieu_trend"},
            "model": {"type": "model_ref", "category": "image", "providers": ["ltt_image"]},
            "aspect_ratio": {"type": "enum", "values": ["16:9", "9:16", "1:1", "4:3", "3:4"], "default": "16:9"},
            "count": {"type": "int", "min": 1, "max": 4, "default": 1},
        },
        returns={"image_keys": "image[]", "prompt": "text"},
        verifiable=("vlm_judge",),

        # Hợp đồng node V2 (spec §4.5).
        #
        # `class="api"`: việc VẼ nằm ở máy B, máy A không giữ VRAM.
        #   `RESOURCE_CLASS` (`workflow/nut.py`) chỉ có cpu|gpu|api — không có
        #   mức "GPU của máy khác", nên `vram_min_mb` bỏ trống là ĐÚNG.
        # `slots=SUAT_ANH`: hằng số dòng 37 của chính tệp này, cũng là con số
        #   `KHAI_CU_TRU_ANH` (dòng 38) đưa vào `admission_theo_model` (dòng
        #   109). ⛔ Không ghi 0: ba app ảnh giành CHUNG một suất `anh_3090`.
        side_effect="external",
        resource={"class": "api", "slots": SUAT_ANH},
        idempotency={"key_fields": ("topic", "model", "phong_cach",
                                    "kieu_trend", "aspect_ratio", "count")},

        # ── Public API (Q92, wave 1) ─────────────────────────────────────────
        api_exposed=True,
        api_contract={
            "scopes": ("jobs:create",),
            "description": ("Generate one to four YouTube thumbnail background "
                            "images from a topic. The images carry NO text: "
                            "the internal model cannot render legible "
                            "lettering, so add your own title afterwards."),
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
                                    "face, a before/after split, a mystery "
                                    "crop, and so on)."),
                    "example": "khuon_mat_cam_xuc",
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
                "phong_cach": ["chuyen_nghiep_toi_gian", "hoat_hinh_cartoon",
                               "cinematic", "flat_design", "3d_render",
                               "collage", "retro_vintage"],
                # `listicle_numbered` và `text_heavy_chu_lon` đã gỡ: cả hai
                # bố cục ấy ĐÒI chữ vẽ ra (một con số lớn, một khối chữ
                # chiếm 60–70 % khung) nên chúng mâu thuẫn với chính
                # `base_prompt` nay cấm chữ.
                "kieu_trend": ["khuon_mat_cam_xuc", "so_sanh_truoc_sau",
                               "bi_an_gay_to_mo", "huong_dan_tutorial",
                               "reaction_phan_ung", "storytelling",
                               "mui_ten_chi_dan"],
            },
        },
    ),),

    enabled=True,
    lifecycle="development",
    capabilities=("AI Image",),
    catalog_parent="taoanh",
    group="Ảnh",
    badge="MỚI",
    notes="Chạy model nhà qua cổng render (LTT_RENDER_BASE_URL). Ảnh không có chữ.",
)
