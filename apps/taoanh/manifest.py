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

#: ⛔ BẢNG NÀY NAY CHỈ ĐỂ **TRA LẠI JOB CŨ**. Từ pha 06.3 app chạy `hidream-o1`
#:    và giá của model đó ở `platform_core.image_gen.gia` — một chỗ duy nhất mà
#:    `anhnoibo` cũng đọc. Thêm `hidream-o1` vào đây sẽ tạo lại đúng cái bảng giá
#:    thứ hai mà chú thích dưới cảnh báo.
MODEL_CREDIT_PER_IMAGE = {
    "gemini-2.5-flash-image": 5,
    "gemini-3.1-flash-lite-image": 5,
    "gemini-3.1-flash-image": 8,
    "gemini-3.1-flash-image-preview": 8,
    # ⛔ Bậc `pro` ĐÓNG 2026-08-23: gia von 35,2 credit, ban 16 => lo 1.924d/anh.
    #    Giữ hai dòng giá này vì job CŨ trong lịch sử vẫn tra giá qua đây; xoá đi
    #    thì một trang lịch sử sẽ hiện giá 5 credit cho việc đã tính 16.
    "gemini-3-pro-image": 16,
    "gemini-3-pro-image-preview": 16,
}
CREDIT_PER_IMAGE = 5  # tương thích code/test cũ: đơn giá model mặc định


def unit_credit(model: str) -> int:
    return MODEL_CREDIT_PER_IMAGE.get(str(model or ""), CREDIT_PER_IMAGE)


def _cost(params: dict) -> int:
    """Trần giữ chỗ. Đọc bảng giá MODEL NHÀ — cùng hàm `anhnoibo` gọi.

    ⛔ Không nhân `unit_credit()` nữa: từ pha 06.3 app chỉ chạy `hidream-o1`, và
       `unit_credit` của bảng trên sẽ trả về **5** cho nó (rơi vào nhánh mặc
       định) trong khi `anhnoibo` bán đúng model ấy **3**. Cùng model hai giá là
       lỗ hổng doanh thu, không phải một chi tiết.

    ⚠️ Ảnh có tham chiếu đắt gấp 3 — nên trần phải biết chế độ, không chỉ số ảnh.
       Giữ chỗ THIẾU thì khách tiêu quá số dư; giữ dư thì hoàn lại.
    """
    from apps.taoanh.features import clean_mode
    from platform_core.image_gen import gia

    try:
        count = int(params.get("count", 1))
    except (TypeError, ValueError):
        count = 1
    che_do = "edit" if clean_mode(
        str(params.get("edit_mode") or "generate")) == "edit" else "t2i"
    return gia.uoc_tran(so_anh_xin=count, che_do=che_do)


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
        description=N_('Sinh từ một đến bốn ảnh từ mô tả tự do, bằng model nội bộ.'),
        admission_theo_model=KHAI_CU_TRU_ANH,      # cư trú 3090 — xem đầu tệp
        params_schema={
            "prompt": {"type": "string", "required": True, "max_length": 4000},
            "image_key": {"type": "image", "required": False},
            "image_keys": {"type": "image[]", "required": False},
            "model": {"type": "model_ref", "category": "image", "providers": ["ltt_image"]},
            "aspect_ratio": {"type": "enum", "values": ["16:9", "9:16", "1:1", "4:3", "3:4"], "default": "16:9"},
            "count": {"type": "int", "min": 1, "max": 4, "default": 1},
        },
        returns={"image_keys": "image[]", "prompt": "text"},
        verifiable=("vlm_judge",),

        # Hợp đồng node V2 (spec §4.5). `class="api"`: việc nằm ở provider /
        # máy B — máy A không giữ VRAM nào cho job này.
        side_effect="external",
        resource={"class": "api", "slots": 0},
        idempotency={"key_fields": ("prompt", "model", "aspect_ratio", "count",
                                    "image_key", "image_keys")},

        # ── Public API (Q92, wave 1) ─────────────────────────────────────────
        api_exposed=True,
        api_contract={
            "scopes": ("jobs:create",),
            "description": ("Generate one to four images from a text prompt, "
                            "optionally guided by one reference image."),
            # 🔴 KHỐI ALIAS BA BẬC ĐÃ GỠ 09/09/2026 (pha 06.3) — BREAKING,
            #    xem `docs/PUBLIC_API/CHANGELOG.md`.
            #
            #    `standard` · `standard-lite` · `enhanced` trỏ tới ba model
            #    Gemini, và chúng tồn tại được là nhờ đúng một điều kiện mà
            #    chú thích cũ nói thẳng: *"quote, charge and choice all move
            #    together"* — tức **giá đi theo model**. Sau di trú, app chỉ
            #    chạy một model và giá không còn phụ thuộc bậc nào.
            #
            # ⛔ Nên giữ ba bậc lại sẽ là bán ba thứ khác nhau, giao cùng một
            #    thứ, ở ba mức giá — đúng cái mà `test_187` gọi tên: *"model
            #    choice is published only where price follows it"*. Nay giá
            #    không đi theo model nữa, nên lựa chọn không được công bố.
            #
            # One reference image is supported through the public upload flow;
            # the multi-image form is a Canvas/UI path that takes a list, and
            # the API media contract handles single references only today.
            "hidden": ("image_keys", "model"),
            # As for the thumbnail tool: `count` multiplies the output.
            "output_counts": {"image_keys": "count"},
            "params": {
                "prompt": {
                    "description": ("What to draw. Everything about the image "
                                    "comes from this text."),
                    "example": "a paper boat on a rain-soaked street at night",
                },
                "image_key": {
                    "description": ("Optional reference image, given as the id "
                                    "of an upload you confirmed or of an "
                                    "artifact from an earlier job. The result "
                                    "follows its subject and composition."),
                    "example": "upl_from_POST_/api/v1/uploads",
                },
                "aspect_ratio": {
                    "description": "Shape of the output image.",
                    "example": "16:9",
                },
                "count": {
                    "description": ("How many images to generate. Each one is "
                                    "charged."),
                    "example": 1,
                },
            },
        },
    ), ToolSpec(
        name="image.batch_generate", job_type="taoanh.generate",
        description=N_('Sinh một lô 2–4 ảnh đồng nhất từ cùng mô tả.'),
        # ⚠️ CẢ HAI tool của app này phải khai, không chỉ tool đầu: hai đường nộp
        #    job đọc `ToolSpec` **của tool được gọi** (`registry.admission_luc_nop`),
        #    nên bỏ sót một tool là bỏ sót một đường vào cùng một card.
        admission_theo_model=KHAI_CU_TRU_ANH,
        params_schema={
            "prompt": {"type": "string", "required": True, "max_length": 4000},
            "image_key": {"type": "image", "required": False},
            "image_keys": {"type": "image[]", "required": False},
            "model": {"type": "model_ref", "category": "image", "providers": ["ltt_image"]},
            "aspect_ratio": {"type": "enum", "values": ["16:9", "9:16", "1:1", "4:3", "3:4"], "default": "16:9"},
            "count": {"type": "int", "min": 2, "max": 4, "default": 4},
        },
        returns={"image_keys": "image[]", "prompt": "text"},
        verifiable=("vlm_judge",),

        side_effect="external",
        resource={"class": "api", "slots": 0},
        idempotency={"key_fields": ("prompt", "model", "aspect_ratio", "count",
                                    "image_key", "image_keys")},
    )),

    enabled=True,
    lifecycle="development",
    capabilities=("AI Image",),
    group="Ảnh",
    notes="Di trú A1 từ gemini_image. Key qua APIKEYS (provider gemini, category image).",
)
