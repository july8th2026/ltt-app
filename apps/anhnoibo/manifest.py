"""
App `anhnoibo` — bán model tạo ảnh **nội bộ** (H37, Q102).

⭐ VÌ SAO LÀ MỘT APP MỚI, KHÔNG SỬA `taoanh`/`thumbnail`:

   Model nội bộ là **một provider** (`ltt_image`), không phải một app — điều đó
   không đổi. Nhưng **bán** nó ra `/api/v1` thì cần một `ToolSpec`, mà ToolSpec chỉ
   khai được trong manifest của một app. Thêm nó vào `taoanh`/`thumbnail` là đụng
   vào app đang phục vụ khách; thêm một thư mục vào `apps/` thì không đụng ai.

   Đúng hợp đồng app: **không sửa `platform_core/` hay `server/`** cho việc này.

⛔ BA CỔNG ĐỘC LẬP trước khi khách ngoài gọi được (Q92 fail-closed):
     ① `api_exposed=True` ở đây
     ② `LTT_PUBLIC_API` bật
     ③ tên tool có trong `LTT_PUBLIC_API_TOOLS`
   Quên một cái là tool không ra. Đó là chủ ý.

⚠️ Và một cổng thứ tư của riêng H37: `ModelInfo("hidream-o1").is_active`.
   🔓 **MỞ 24/08** cùng ba cổng trên (G10).

   ⛔ Nhưng đọc cho đúng vì sao nó mở: cổng chất lượng G6b **đã chấm và model nhà
      thua rõ** (D-045). Nó mở vì D-042 + D-046 đã đổi bài toán — không còn định
      tuyến, mỗi model là **một mặt hàng có cổng gọi riêng**, khách gọi `image.ltt`
      là biết trước mình mua gì. Nó **không** mở vì ai đó thấy nó đẹp hơn.

      Hệ quả phải giữ: đừng định vị là "đẹp hơn", và **việc có chữ tiếng Việt thì
      trả lời `image.thumbnail` (Gemini)** — chữ là ngoài phạm vi (D-048).

⛔ GIÁ KHÔNG Ở FILE NÀY. Nó ở `gia.py` — một chỗ duy nhất, có phiên bản, công bố
   ở `/gia-api`. `credit_cost` dưới đây chỉ là **trần ước cao** để giữ chỗ; giá
   cuối do `jobs.handle` báo về theo số ảnh **thật sự sinh ra được** (D-050).
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.llm.residency import THEO_LO
from platform_core.registry import AdmissionModel, AppManifest, ToolSpec

#: ⛔ GIÁ KHÔNG Ở ĐÂY NỮA — nó ở `apps/anhnoibo/gia.py`, một chỗ duy nhất, có
#:    phiên bản, và có `bang_gia()` để trang công khai đọc. Đừng khai lại con số
#:    nào ở đây: hai bảng giá lệch nhau thì bảng nào cũng không đáng tin.
from . import features as _features, gia

# ── Cư trú RTX 3090 (dual-model D01 B, Task 5.5) ─────────────────────────────
#
# Ba app ảnh (`anhnoibo`, `taoanh`, `thumbnail`) bán CÙNG model trên CÙNG card,
# nên cả ba khai cùng một tài nguyên và cùng một nhóm; `apps/ltt_llm` khai nhóm
# ấy cho LTT-3.8 với vai `mac_dinh`. Trọng tài (`platform_core/llm/residency.py`)
# chỉ **đọc** bản khai — nền tảng không được biết tên app (`test_147`) — nên tên
# nhóm không thể sống trong `platform_core`; và ba app không import được nhau
# (`.importlinter`), nên **ba bản khai giống nhau** là hình dạng đúng duy nhất.
# `tests/test_1219_residency_noi.py` chốt cả ba trùng nhau VÀ trùng `NHOM_CU_TRU_38`
# của `apps/ltt_llm/ngan_sach.py` — một chữ lệch là ĐỎ ở cổng, không phải một
# cửa sổ ảnh không bao giờ mở.
#
# ⛔ `vai_tro` lấy từ HẰNG SỐ `residency.THEO_LO`, không gõ chuỗi: `mo_cho` NÉM
#    với vai lạ và nay nó ném **từ trong cửa admission**, nên `"theolo"` gõ sai
#    là lỗi 500 ở mọi lượt trên tài nguyên này — 3 giờ sáng, không phải ở gate.
NHOM_CU_TRU_ANH = "rtx3090"
TAI_NGUYEN_ANH = "anh_3090"
#: Một lượt vẽ tại một thời điểm trên 3090 (D01 B: vẽ **theo lô** trong cửa sổ,
#: không vẽ song song — hai lượt HiDream cùng lúc là OOM trước khi là chậm).
SUAT_ANH = 1
KHAI_CU_TRU_ANH = {"*": AdmissionModel(TAI_NGUYEN_ANH, SUAT_ANH, 0,
                                       NHOM_CU_TRU_ANH, THEO_LO)}


def _gia(params: dict) -> int:
    """TRẦN ƯỚC CAO để giữ chỗ, **không phải giá cuối**.

    Giá cuối do `jobs.handle` báo về qua `credit_cost`, tính theo số ảnh **thật
    sự sinh ra được**. Phần giữ dư được hoàn ngay khi job xong.
    """
    try:
        so = int(params.get("count", 1))
    except (TypeError, ValueError):
        so = 1
    return gia.uoc_tran(so_anh_xin=so, che_do=str(params.get("mode") or "t2i"))


MANIFEST = AppManifest(
    slug="anhnoibo",
    display_name=N_('Ảnh nội bộ (máy nhà)'),
    route_prefix="/anhnoibo",
    summary=N_('Tạo ảnh bằng model chạy trên máy của LTT Studios. Sinh ảnh từ mô '
               'tả, sửa ảnh theo lệnh, giữ nhân vật nhất quán qua nhiều ảnh.'),
    icon="🏠",
    accent="#0F766E",

    # ⛔ KHÔNG có thẻ catalog và KHÔNG có mục nav riêng — app này **chưa có giao
    #    diện**: không `routes.py`, không bundle React. Thiếu khai báo này thì
    #    `/anhnoibo` thành một link 404 trong header của **mọi người đã đăng nhập**
    #    (`visible_on_surface` trả `authenticated or public`, nên `public=False`
    #    một mình KHÔNG đủ), còn `nav=()` thì bị `nav_entries()` tự sinh lại.
    #
    #    `catalog_parent` là cơ chế hợp đồng đã có sẵn cho đúng việc này: *"app con
    #    vẫn giữ route/job/history riêng nhưng không tạo card/nav độc lập… hai
    #    executor cùng nằm dưới một sản phẩm customer-facing"*. Đó chính xác là
    #    quan hệ ở đây: model nhà là một executor ảnh nữa dưới sản phẩm tạo ảnh.
    #
    #    Nó **không** chặn đường API: `app_may_be_public()` chỉ đọc `enabled` +
    #    `lifecycle` + `surface`. Bằng chứng sống: `thumbnail` cũng khai
    #    `catalog_parent="taoanh"` và vẫn đang publish `image.thumbnail`.
    catalog_parent="taoanh",

    job_types=("anhnoibo.generate",),
    # Worker chỉ gọi HTTP sang máy B — không cần GPU trên máy chạy worker.
    requires=("api",),
    credit_cost=_gia,
    #: Trang gia cong khai `/gia-api` doc HAM NAY qua registry, khong
    #: import app nay theo ten. Xem `AppManifest.bang_gia`.
    bang_gia=gia.bang_gia,
    # Suc khoe cho catalog cua san pham khac (H43 Phase 06/10): `GET /live`
    # cua cong render, khong can khoa, timeout ngan. Xem `features.suc_khoe`.
    suc_khoe=_features.suc_khoe,

    tools=(ToolSpec(
        name="image.ltt",
        job_type="anhnoibo.generate",
        description=N_('Tạo ảnh bằng model nội bộ của LTT Studios.'),
        # Xem khối "Cư trú RTX 3090" ở đầu tệp.
        admission_theo_model=KHAI_CU_TRU_ANH,
        params_schema={
            "prompt": {"type": "string", "required": True, "max_length": 4000},
            "mode": {"type": "enum", "values": ["t2i", "edit", "subject"],
                     "default": "t2i"},
            "count": {"type": "int", "min": 1, "max": 4, "default": 1},
            # ⚠️ HAI THAM SỐ, MỘT VIỆC — và đó không phải thừa.
            #    `image_key` (một ảnh) là thứ khách API dùng được: tầng public API
            #    giải **một** phiên tải lên cho **một** tham số
            #    (`invocation.promote_media`, `sessions: dict`), nên kiểu `image[]`
            #    qua API hôm nay là một hợp đồng không thực hiện được.
            #    `image_keys` (tối đa 2) là đường của giao diện web, khai `hidden`.
            #    `taoanh` đã phải làm đúng như vậy — đây là giới hạn của nền tảng,
            #    không phải của model. Model nhận tới 10 ảnh.
            "image_key": {"type": "image", "required": False},
            "image_keys": {"type": "image[]", "required": False},
            # Khai `model_ref` dù hôm nay chỉ có MỘT model: đây là cách bộ chọn
            # model của giao diện và của admin nhìn thấy nó. `default` bắt buộc vì
            # tham số này `hidden` — tham số ẩn mà không có mặc định thì tầng API
            # bỏ trống, và handler tự chọn một thứ khác (đã có tiền lệ: tool
            # storyboard chạy — và tính tiền — sai nhánh vì đúng lỗi này).
            "model": {"type": "model_ref", "category": "image",
                      "providers": ["ltt_image"], "default": "hidream-o1"},
            "negative_prompt": {"type": "string", "max_length": 1000},
        },
        returns={"image_keys": "image[]", "prompt": "text"},

        # Hợp đồng node V2 (spec §4.5). `class="api"`: việc nằm ở provider /
        # máy B — máy A không giữ VRAM nào cho job này.
        side_effect="external",
        resource={"class": "api", "slots": 0},
        idempotency={"key_fields": ("prompt", "negative_prompt", "mode",
                                    "model", "count", "image_key",
                                    "image_keys")},

        api_exposed=True,
        api_contract={
            "scopes": ("jobs:create",),
            "description": (
                "Generate images with LTT Studios' own model. Supports "
                "text-to-image, instruction editing of a reference image, and "
                "keeping the same subject across a new scene."),
            # `model`: hien chi co mot model, va gia tinh theo che do chu khong
            # theo model. Mo ra khi nao ham gia tinh theo tung model.
            # `image_keys`: xem chu thich o params_schema.
            "hidden": ("model", "image_keys"),
            "output_counts": {"image_keys": "count"},
            "params": {
                "prompt": {
                    "description": (
                        "What to draw. Written in any language - the platform "
                        "translates it to English before the model sees it, "
                        "because this model only understands English and "
                        "Chinese. Text you want DRAWN INSIDE the image must be "
                        "in double quotes; it is kept exactly as written."),
                    "example": 'A calico cat sleeping on a windowsill, afternoon light',
                },
                "mode": {
                    "description": (
                        "t2i = from text only. edit = change one reference image "
                        "while keeping the rest. subject = keep the same person "
                        "or object across a new scene. edit and subject both "
                        "need image_key and both cost three times more because "
                        "they take about three times as long; t2i refuses a "
                        "reference image."),
                    "example": "t2i",
                },
                "count": {"description": "How many images to return, 1 to 4.",
                          "example": 1},
                "image_key": {
                    # 🔴 CAU TRUOC NOI SAI HANH VI, va sai theo huong lam khach
                    #    viet ma hong: no ghi "ignored for t2i". May chu KHONG bo
                    #    qua — no TU CHOI:
                    #
                    #        if che_do == "t2i" and refs:
                    #            raise LoiTaoAnh('Che do t2i khong nhan anh tham chieu.')
                    #        (apps/anhnoibo/features.py)
                    #
                    #    Khach doc "ignored" se gui kem cho tien, va nhan mot loi
                    #    ho khong hieu tu dau ra. Do 25/08.
                    "description": (
                        "Reference image, given as the id of an upload you "
                        "confirmed or of an artifact from an earlier job. "
                        "Required for edit and subject. Sending it with t2i is "
                        "REJECTED, not ignored."),
                    "example": "upl_from_POST_/api/v1/uploads",
                    # Khai bang DU LIEU de trang tai lieu loc duoc, thay vi de no
                    # doc cau tieng Anh o tren roi doan.
                    "only_when": {"mode": ["edit", "subject"]},
                },
                "negative_prompt": {
                    "description": "What to avoid. Optional.",
                    "example": "",
                },
            },
        },
    ),),
)
