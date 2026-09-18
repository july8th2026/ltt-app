"""
providers.py — Provider Registry (H8): MỘT chỗ khai mọi nhà cung cấp API mà nền
tảng biết kết nối. Học từ D:\\BOT GEMINI nhưng GOM lại (BOT GEMINI có 3 registry
model rời + config tĩnh + engine stub — chính là "đừng làm thế").

Thêm loại API mới về sau = thêm MỘT dòng ở REGISTRY (+ tuỳ 1 adapter gọi HTTP),
KHÔNG sửa app, KHÔNG sửa nơi khác.

Tách 3 ID cho model (bài học ModelArk/VideoModelInfo):
- `id`               : id catalog (hiện trên UI, app tham chiếu)
- `provider_model_id`: id thật provider dùng trong body (mặc định = id)
- `endpoint_id`      : id endpoint/deployment theo tài khoản (ModelArk ep-...), nếu có
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from platform_core.i18n import N_

from platform_core.models import (APIKEY_CAT_CHAT, APIKEY_CAT_IMAGE,
                                  APIKEY_CAT_MODEL, APIKEY_CAT_VIDEO)

# Kiểu xác thực — quyết định cách gắn credential vào request.
AUTH_QUERY_KEY = "query_key"    # ?key=<KEY>        (Gemini)
AUTH_BEARER = "bearer"          # Authorization: Bearer <KEY>   (OpenAI-compat, ModelArk)
AUTH_X_API_KEY = "x_api_key"    # X-API-Key: <KEY>  (PLENX)


@dataclass(frozen=True)
class ModelInfo:
    id: str
    categories: tuple = ()
    provider_model_id: str = ""     # mặc định = id
    endpoint: str = ""              # override đường endpoint nếu khác chuẩn provider
    endpoint_id: str = ""           # account endpoint (ModelArk), gửi làm field "model"
    is_active: bool = True
    display_name: str = ""          # nhãn hiển thị UI (rỗng = dùng id)
    # Schema nghiệp vụ theo model, vd resolutions/durations/aspects. Additive;
    # provider/app chưa khai vẫn hoạt động như trước.
    capabilities: dict = field(default_factory=dict)

    def real_model_id(self) -> str:
        return self.provider_model_id or self.id

    def label(self) -> str:
        return self.display_name or self.id


@dataclass(frozen=True)
class Provider:
    id: str
    display_name: str
    auth_style: str
    base_url: str
    categories: tuple
    models: tuple = ()
    list_models_path: Optional[str] = None   # endpoint liệt kê model (nếu có), vd /v1/models
    async_poll: bool = False                 # True = submit->poll (video)
    notes: str = ""
    #: ⛔ `False` = **ĐÃ NGỪNG**. Không tạo được lượt gọi mới và không hiện ở bộ
    #: chọn nào — nhưng `get()` · `resolve_model_id()` · `model_capabilities()`
    #: **vẫn trả về**, để một job cũ trong DB còn đọc được tên model của nó.
    #:
    #: ⭐ Đây là mức PROVIDER của `ModelInfo.is_active` đã có sẵn, **không phải**
    #:    một cơ chế mới. Ranh giới *"chặn tạo mới / giữ đọc lịch sử"* vốn đã nằm
    #:    trong chính tệp này: `model_options()` và `model_catalog()` **lọc**
    #:    theo `is_active`, còn `get()` và `resolve_model_id()` thì **không**.
    is_active: bool = True


class ProviderDaNgung(RuntimeError):
    """Có người cố tạo một lượt gọi MỚI tới provider đã ngừng.

    ⛔ **Đây là fail-closed, và nó KHÔNG có đường lui.** Bắt được lỗi này rồi
    thử một provider khác chính là cái `HARD_DELETE_POLICY` cấm — rollback đi
    bằng Git SHA, không bằng một nhánh `except`.

    ⚠️ Nó **không** phải `BanError`. `BanError` nghĩa *"bận, đi tiếp provider
    sau"*; lỗi này nghĩa *"provider này không còn tồn tại với tư cách đường
    chạy"*. Lẫn hai cái là dựng lại đúng đường lui vừa gỡ.
    """


def da_ngung(provider_id: str) -> bool:
    """Provider này đã ngừng chưa? Đọc THẲNG `REGISTRY`, đúng một nguồn.

    🔴 **Cố ý không đi qua `get()`.** `get()` bị monkeypatch trong nhiều phép
    kiểm (chúng trả `SimpleNamespace` giả không có trường `is_active`), nên một
    cổng đọc qua nó vừa **nổ nhầm** ở test, vừa **im lặng hỏng** nếu ai đó thay
    `get()` bằng thứ luôn báo "còn sống". Sự thật về việc retire nằm ở
    `REGISTRY`, nên cổng phải hỏi đúng chỗ đó.

    Provider **không có trong registry** ⇒ `False`: id lạ không phải việc của
    hàm này, và biến nó thành lỗi ở đây sẽ chặn nhầm các đường hợp lệ khác.
    """
    p = REGISTRY.get((provider_id or "").strip().lower())
    return p is not None and not p.is_active


def chan_neu_da_ngung(provider_id: str) -> None:
    """Cổng fail-closed — gọi NGAY TRƯỚC mỗi lượt ra mạng.

    Đặt ở đây chứ không ở tầng HTTP vì tám nơi tự dựng HTTP riêng: một cổng
    trong `httpx` không tồn tại, còn một cổng theo **danh tính provider** thì
    mọi nơi đều gọi được.
    """
    if da_ngung(provider_id):
        # 🔴 CHUỖI NÀY HIỆN RA VỚI KHÁCH — đo được, không phải phỏng đoán:
        #      platform_core/models.py:297                Job.error  (cot Text)
        #      apps/autosubvideo/templates/…:97           {{ j.error }}
        #    Một job hỏng vì cổng này lưu thông điệp vào `Job.error`, và trang
        #    danh sách job render thẳng nó. Nên nó phải được **dịch**, không
        #    phải một chuỗi kỹ thuật.
        #
        # ⚠️ Cám dỗ ở đây là xếp nó vào *"lỗi nội bộ, không cần dịch"*. Hai
        #    đường gọi trên bác điều đó bằng mã, không bằng ý kiến.
        from platform_core.i18n import _ as _t
        raise ProviderDaNgung(
            _t('Nhà cung cấp này đã ngừng phục vụ. Nội dung cũ vẫn xem được, '
               'nhưng không tạo lượt mới được nữa.'))


# ── Seed 5 provider hiện có trong BOT GEMINI (chỉ key CHÍNH THỨC) ──────────────
REGISTRY: dict[str, Provider] = {
    # ─────────────────────────────────────────────────────────────────────
    # ⛔ BA NHÀ CUNG CẤP ĐÃ XOÁ — AI CLEAN REBUILD V2, 10/09/2026
    #
    # Chủ dự án chốt: *"Codex, gemini, apikey, shopapi các api ngoài hệ thống
    # trừ api byteplus thì ta cần dọn và xoá hết."*
    #
    # 🔴 THỨ ĐÃ XOÁ là toàn bộ phần **GỌI THẾ NÀO**: `base_url` (ba host thật),
    #    `auth_style`, `list_models_path`, và mọi `ModelInfo`. Sau đây không còn
    #    một mẩu công thức nào để dựng lại một lượt gọi ra ba nhà cung cấp này —
    #    kể cả khi ai đó có sẵn khoá API.
    #
    # ⭐ THỨ CỐ Ý GIỮ là đúng ba dòng khai `is_active=False`, và lý do là CƠ HỌC
    #    chứ không phải tình cảm: `da_ngung()` trả `False` cho một id **không có
    #    trong registry**. Xoá hẳn ba dòng này ⇒ `chan_neu_da_ngung("gemini")`
    #    thôi ném, tức cổng fail-closed của pha 04 **im lặng mở ra**.
    #
    #    Nói cách khác: ở đây, xoá nốt dòng cuối không làm hệ thống sạch hơn —
    #    nó gỡ mất lời từ chối. Cái còn lại không phải một đường chạy; nó là một
    #    tấm biển "đường này đã đóng" mà cổng đọc được.
    #
    # ⚠️ Hệ quả đã cân: `resolve_model_id`/`model_capabilities` không còn tra
    #    được tên hiển thị của model Gemini cũ. Job cũ vẫn đọc được **id thô**
    #    đã lưu trong hàng của nó; thứ mất là nhãn đẹp, không phải dữ liệu.
    # ─────────────────────────────────────────────────────────────────────
    "gemini": Provider(
        id="gemini", display_name="Google Gemini (da xoa)",
        auth_style="", base_url="", categories=(), models=(),
        list_models_path=None,
        notes="XOA 2026-09-10 (AI CLEAN REBUILD V2). Giu bia mo de cong "
              "`chan_neu_da_ngung` con no. Khong con base_url/auth/model.",
        is_active=False,
    ),
    "apiai": Provider(
        id="apiai", display_name="apiai gateway (da xoa)",
        auth_style="", base_url="", categories=(), models=(),
        list_models_path=None,
        notes="XOA 2026-09-10 (AI CLEAN REBUILD V2). Nhu tren.",
        is_active=False,
    ),
    "cheapkeyai": Provider(
        id="cheapkeyai", display_name="cheapkeyai gateway (da xoa)",
        auth_style="", base_url="", categories=(), models=(),
        list_models_path=None,
        notes="XOA 2026-09-10 (AI CLEAN REBUILD V2). Nhu tren.",
        is_active=False,
    ),
    "byteplus": Provider(
        id="byteplus", display_name="BytePlus ModelArk (Seedance video)",
        auth_style=AUTH_BEARER,
        base_url="https://ark.ap-southeast.bytepluses.com/api/v3",
        categories=(APIKEY_CAT_VIDEO,), async_poll=True,
        models=(
            ModelInfo("seedance-2.0", (APIKEY_CAT_VIDEO,), capabilities={
                "resolutions": ["480p", "720p", "1080p", "4k"],
                "durations": [4, 5, 6, 8, 10, 12, 15],
                "aspects": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
            }),
            ModelInfo("seedance-2.0-fast", (APIKEY_CAT_VIDEO,), capabilities={
                "resolutions": ["480p", "720p"],
                "durations": [4, 5, 6, 8, 10, 12, 15],
                "aspects": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
            }),
            ModelInfo("seedance-2.0-mini", (APIKEY_CAT_VIDEO,), capabilities={
                "resolutions": ["480p", "720p"],
                "durations": [4, 5, 6, 8, 10, 12, 15],
                "aspects": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
            }),
        ),
        notes="Video async: POST /contents/generations/tasks -> poll GET .../{id}. endpoint_id theo tài khoản.",
    ),
    # ── H37: model ảnh NỘI BỘ chạy trên máy B (Q102) ──────────────────────────
    #
    # ⭐ Nó là MỘT PROVIDER, không phải một app. Toàn bộ phần thêm vào nền tảng cho
    #    H37 là mục này + adapter `platform_core/image_gen/`.
    #
    # ⛔ `base_url` LẤY TỪ MÔI TRƯỜNG, không viết cứng địa chỉ LAN vào mã nguồn:
    #    thư mục này vừa là mã nguồn vừa là BỘ CÀI được chép sang máy khác, và một
    #    IP nội bộ viết cứng sẽ đi theo sang máy không có nó. Chưa đặt biến ⇒ rỗng
    #    ⇒ adapter từ chối chạy (fail-closed, đúng tinh thần Q92).
    #
    # ⛔ MODEL ĐỂ `is_active=False`. Nó chỉ được bật ở G10 sau khi qua cổng G6b (so
    #    mù với Gemini 3 Pro Image). Khai một model chưa qua cổng chất lượng là mở
    #    bán trước khi biết nó có đáng bán không.
    #
    # ⚠️ 429 CỦA CỔNG NÀY LÀ "BẬN", KHÔNG PHẢI LỖI. Máy B dùng chung GPU với dự án
    #    video. Xem `platform_core/image_gen/cong_render.py` — gọi
    #    `api_pool.danh_dau_loi()` cho key này khi gặp 429 sẽ tự tắt model nhà sau
    #    5 lần hàng xóm bận.
    "ltt_image": Provider(
        id="ltt_image", display_name=N_("LTT Studios — máy nhà (RTX 3090)"),
        auth_style=AUTH_BEARER,
        base_url=(os.environ.get("LTT_RENDER_BASE_URL") or "").rstrip("/"),
        categories=(APIKEY_CAT_IMAGE,), async_poll=True,
        models=(
            ModelInfo(
                "hidream-o1", (APIKEY_CAT_IMAGE,),
                display_name=N_("LTT nội bộ (HiDream-O1)"),
                # 🔓 MỞ 24/08 (G10). Cổng G6b đã chấm và **model nhà thua rõ**
                #    (D-045: Gemini 24 – nhà 4). Mở **không phải** vì nó đẹp hơn.
                #
                #    D-042 + D-046 đã đổi bài toán: không còn định tuyến, mỗi model
                #    là **một mặt hàng có cổng gọi riêng**. Khách gọi `image.ltt` là
                #    biết trước mình mua HiDream chạy trên máy nhà — rẻ hơn, và
                #    không bị chính sách nội dung của một hãng khác chi phối.
                #
                # ⛔ ĐỪNG ĐỊNH VỊ NÓ LÀ "ĐẸP HƠN", và đừng đưa việc **có chữ** sang
                #    nó — chữ tiếng Việt là ngoài phạm vi (D-048), việc đó là của
                #    `image.thumbnail` chạy Gemini. Ba chỗ nhà ngang bằng:
                #    anime/fantasy/kiến trúc.
                is_active=True,
                capabilities={
                    # CHỈ khai thứ ĐÃ ĐO THẬT. `edit`/`subject` đã đo xong 22/08
                    # (D-032): VRAM đỉnh 19,8–20,0 GB, giữ được nhân dạng. Trước đó
                    # chúng KHÔNG được khai vì chưa đo — đó là thứ tự đúng.
                    "modes": ["t2i", "edit", "subject"],
                    "buckets": [[2560, 1440], [2048, 2048], [1920, 1080]],
                    "steps": {"min": 30, "max": 90, "default": 30},
                    "license": "MIT",
                    # Số đo 22/08, bf16, `--reserve-vram 3`, lô 10 ảnh liên tiếp.
                    "do_duoc": {"giay_moi_anh_s30": 57.8, "giay_moi_anh_s90": 168.4,
                                "vram_dinh_mb": 17946,
                                # Chế độ tham chiếu ĐẮT GẤP 3,3 LẦN, cùng số bước.
                                "giay_moi_anh_tham_chieu_s30": 190.0,
                                "vram_dinh_tham_chieu_mb": 20047},
                    "max_refs": 2,
                    # ⚠️ Giới hạn phải nói ra, không giấu sau giao diện (D-027).
                    "canh_bao": [N_("prompt phải là tiếng Anh — nền tảng tự dịch"),
                                 N_("chữ tiếng Việt CÓ DẤU vẽ trong ảnh bị sai dấu")],
                },
            ),
        ),
        list_models_path="/v1/models",
        notes=("Cổng render trên máy B (:8199, bearer token). Máy B KHÔNG giữ bí mật "
               "nào của nền tảng: ảnh vào bằng presigned GET, ra bằng presigned PUT. "
               "429 = BẬN, không phải lỗi."),
    ),
    # ── Model ngôn ngữ chạy tại nhà, máy B (H38) ──────────────────────────────
    # Anh em với `ltt_image` ở trên: cùng máy B, cùng nguyên tắc Q102 (máy B KHÔNG
    # giữ bí mật nào của nền tảng), nhưng **cổng khác** (8299, không phải 8199) và
    # **đồng bộ** chứ không async_poll.
    "ltt_llm": Provider(
        id="ltt_llm", display_name=N_("LTT Studios — model ngôn ngữ tại nhà"),
        auth_style=AUTH_BEARER,
        base_url=(os.environ.get("LTT_LLM_BASE_URL") or "").rstrip("/"),
        categories=(APIKEY_CAT_CHAT,), async_poll=False,
        models=(
            ModelInfo(
                "qwen38-api", (APIKEY_CAT_CHAT,),
                display_name=N_("LTT LLM (coding · chat · agent)"),
                # ✅ MỞ. Khác `ltt_image` (còn False): hạng mục này đã qua cổng
                #    nghiệm thu 19/19 trên phần cứng thật ngày 22/08 — sinh thật,
                #    tool calling, prefix cache, và trọng tài VRAM.
                is_active=True,
                capabilities={
                    # CHỈ khai thứ ĐÃ ĐO THẬT trên máy B (SO_DO_P2_P6.md).
                    # 📈 12/09: 204.800 → 221.184 (L-14, 10_BENCHMARK_P3 §G1b —
                    #    mốc cao nhất còn sạch ở `-np 3` + mmproj trên GPU).
                    #    ⛔ Nguồn chân lý `apps/ltt_llm/ngan_sach.CUA_SO_THEO_MODEL`;
                    #    `platform_core` không import `apps/` nên `test_334` là
                    #    thứ buộc hai đầu lại.
                    "context_window": 221_184,
                    # ✅ 18/09 (plan v2 Task 5): False → True. Máy B nạp
                    #    `--mmproj mmproj-F16.gguf` cho hồ sơ này
                    #    (`llm_gateway/deploy/llama-swap.yaml`), và LTTCODE live
                    #    L7 (ảnh, `ltt-3.8`) PASS trên production 17/09
                    #    (`LTTCODEAPP/docs/LTTCODE/reports/P03-live-20260917-*`).
                    #    Cờ này là LỜI KHAI, không phải bộ định tuyến: app nào
                    #    muốn việc ảnh ở 3.5 thì tự chỉ định (xem
                    #    `apps/auto_scan_video/ai.MODEL_THI_GIAC_NOI_BO`).
                    #    `test_334` đối chiếu cửa sổ + vision với `HO_SO` từng model.
                    "vision": True,
                    "tool_calling": True,
                    "license": "Apache-2.0",
                    "do_duoc": {
                        "decode_tok_s": 68.1,        # trung vị 3 lượt, MTP n-max 2
                        "decode_khong_mtp_tok_s": 40.0,
                        "prefill_tok_s": 1100,       # 1.050–1.190 ở 4 kích cỡ
                        "vram_dinh_mb": 20_339,
                        # Bản sao của `ngan_sach.NAP_KHO_AM_S` (kho ấm, §G4);
                        # `platform_core` không import `apps/` ⇒ `test_334` buộc.
                        "nap_model_s": 16.3,
                    },
                    # ⚠️ Giới hạn phải nói ra, không giấu sau giao diện (D-027).
                    "canh_bao": [
                        N_("máy B dùng chung GPU với việc ảnh và video — bận thì trả 429, không phải lỗi"),
                        # 🔴 O-13 (phương án C, 17/09/2026): ĐÃ GỠ cảnh báo
                        #    *"engine có cửa sổ 131K; API public giới hạn input
                        #    96.256"* (`9359d723`, 01/09) — cả hai số đã sai từ
                        #    03/09. Cửa sổ/trần vào công bố THEO MODEL qua
                        #    `/api/v1/models`; đừng gõ lại số vào chuỗi hiển thị
                        #    (`test_334` chặn).
                    ],
                },
            ),
            # 🔴 `qwen38-vision` ĐÃ GỠ 11/09/2026 (D02, dual-model 2.3). Nó là
            #    hồ sơ **thứ hai của cùng một model** trên cùng một card, tồn
            #    tại chỉ vì mmproj; llama-swap phải giết lượt đang chạy để hoán
            #    hồ sơ. Nay `qwen38-api` tự nạp mmproj, và model thứ hai bán ra
            #    là một model KHÁC trên một CARD khác — đó là `qwen35-api`.
            ModelInfo(
                "qwen35-api", (APIKEY_CAT_CHAT,),
                display_name=N_("LTT LLM 3.5 (nhanh · rẻ · đọc ảnh)"),
                is_active=True,
                capabilities={
                    # ✅ SỐ ĐO của hồ sơ 5060 Ti, chốt ở dual-model 2.6:
                    #    `10_BENCHMARK_P3.md` §G3 — `-c 262144 -kvu` KV q8_0 +
                    #    mmproj, VRAM 13.423 MiB, biên 2.888 MiB, không tràn.
                    #    ⛔ KHÁC `qwen38-api` (221.184) và đó là phép đo nói thế:
                    #    model 9B chỉ tốn ~7,3 GiB trọng số nên dù card nhỏ hơn
                    #    8 GB, phần còn lại cho KV vẫn rộng hơn 3090 + 27B.
                    "context_window": 262_144,
                    "vision": True,
                    "tool_calling": True,
                    "license": "Apache-2.0",
                    "canh_bao": [
                        N_("chạy trên card thứ hai của máy B — bận thì trả 429, không phải lỗi"),
                    ],
                },
            ),
            # `qwen38-ops` ĐÃ GỠ 03/09. Nó từng bị giữ trong LAN vì lập luận
            # "200K cần ~195 giây prefill ⇒ vượt timeout 125 giây của Cloudflare" —
            # đúng cho cửa ĐỒNG BỘ, sai cho cửa STREAM, vì `nhip_tim.py` chèn chú
            # thích SSE mỗi 15 giây trong lúc prefill nên đồng hồ im-lặng không
            # bao giờ chạm. Nay `qwen38-api` CHÍNH LÀ hồ sơ 200K, và chỉ có MỘT
            # hồ sơ text: llama-swap giết một lượt đang chạy để nạp hồ sơ khác.
        ),
        list_models_path="/v1/models",
        notes=("Cổng VLM trên máy B (:8299, bearer token), tương thích OpenAI. "
               "Máy B KHÔNG giữ bí mật nào của nền tảng. "
               "429 = BẬN, không phải lỗi — đánh dấu lỗi cho key ở đây sẽ tự tắt "
               "model nhà sau 5 lần (D-005). Gọi qua platform_core/llm/dieu_phoi.py."),
    ),
    # ⛔ PLENX ĐÃ XOÁ — AI CLEAN REBUILD V2, 10/09/2026. Cùng không gian với ba
    #    mục trên: *"các api ngoài hệ thống trừ api byteplus thì ta cần dọn và
    #    xoá hết."* PLENX là một cổng ngoài, không phải BytePlus.
    #
    # 📊 Số liệu đứng sau quyết định, không phải suy đoán — đếm trên CSDL
    #    production 10/09: **1 khoá, 4 lượt gọi từ trước tới nay, im từ 08/09**.
    #    Đường video đang sống là WanGP (LTT VIDEO V2.1), không phải cổng này.
    #
    # ⚠️ **CÁI MẤT, nói thẳng để đảo lại được bằng MỘT commit:** `kling-3.0` và
    #    `seedance-2.0-pro` rời khỏi catalog video. BytePlus vẫn phục vụ
    #    `seedance-2.0`, `-fast`, `-mini`, nên nhóm video **không chết**; thứ
    #    mất là hai bậc model, và đó là một quyết định **sản phẩm** đã được
    #    chủ dự án ra, không phải một hệ quả kỹ thuật tôi tự chọn.
    #
    # ⭐ Giữ `is_active=False` vì cùng lý do cơ học ở khối trên: `da_ngung()` trả
    #    `False` cho một id **vắng mặt**, nên xoá hẳn dòng này sẽ **tắt** cổng
    #    fail-closed thay vì siết nó.
    "plenx": Provider(
        id="plenx", display_name="PLENX video (da xoa)",
        auth_style="", base_url="", categories=(), models=(),
        async_poll=False,
        notes="XOA 2026-09-10 (AI CLEAN REBUILD V2). Cong video ngoai, khong "
              "phai BytePlus. Do 10/09: 1 khoa, 4 luot, im tu 08/09.",
        is_active=False,
    ),
}


def get(provider_id: str) -> Optional[Provider]:
    return REGISTRY.get((provider_id or "").strip().lower())


def list_all() -> list:
    return list(REGISTRY.values())


def provider_ids() -> list:
    return list(REGISTRY.keys())


def models_for(provider_id: str, category: Optional[str] = None) -> list:
    """Danh sách ModelInfo của provider, lọc theo category nếu truyền."""
    p = get(provider_id)
    if p is None:
        return []
    out = list(p.models)
    if category:
        out = [m for m in out if not m.categories or category in m.categories]
    return out


def model_capabilities(model_id: str) -> dict:
    """Trả capability tĩnh của model, không gọi mạng và không lộ credential."""
    for provider in REGISTRY.values():
        for model in provider.models:
            if model.id == model_id:
                return dict(model.capabilities)
    return {}


def resolve_model_id(model_id: str) -> str:
    """Catalog/legacy id -> id thật gửi provider; id lạ được giữ nguyên."""
    value = (model_id or "").strip()
    for provider in REGISTRY.values():
        for model in provider.models:
            if model.id == value:
                return model.real_model_id()
    return value


def model_options(category: str, provider_ids_filter: Optional[tuple] = None) -> list:
    """Danh sách model active theo category/provider, khử trùng nhưng giữ thứ tự."""
    allowed = set(provider_ids_filter or ())
    out: list = []
    seen: set = set()
    for provider in REGISTRY.values():
        if allowed and provider.id not in allowed:
            continue
        if not provider.is_active:
            continue          # ⛔ provider đã ngừng: không hiện ở bộ chọn nào
        for model in provider.models:
            if (model.is_active and category in model.categories
                    and model.id not in seen):
                out.append({"value": model.id, "label": model.label()})
                seen.add(model.id)
    return out


def model_catalog() -> list[dict]:
    """Public capability catalog for schema-driven UIs; never exposes keys/endpoints."""
    indexed: dict[str, dict] = {}
    for provider in REGISTRY.values():
        if not provider.is_active:
            continue          # ⛔ provider đã ngừng: không lên catalog công khai
        for model in provider.models:
            if not model.is_active:
                continue
            item = indexed.setdefault(model.id, {
                "id": model.id, "label": model.label(), "categories": [],
                "providers": [], "capabilities": {},
            })
            item["providers"].append({"id": provider.id, "label": provider.display_name})
            item["categories"] = sorted(set(item["categories"]) | set(model.categories))
            if model.capabilities:
                item["capabilities"].update(model.capabilities)
    return sorted(indexed.values(), key=lambda item: (item["categories"], item["label"]))
