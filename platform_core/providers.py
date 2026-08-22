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


# ── Seed 5 provider hiện có trong BOT GEMINI (chỉ key CHÍNH THỨC) ──────────────
REGISTRY: dict[str, Provider] = {
    "gemini": Provider(
        id="gemini", display_name="Google Gemini (API key)",
        auth_style=AUTH_QUERY_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta",
        categories=(APIKEY_CAT_MODEL, APIKEY_CAT_CHAT, APIKEY_CAT_IMAGE),
        models=(
            ModelInfo("gemini-2.5-flash-image", (APIKEY_CAT_IMAGE,),
                      display_name="Gemini 2.5 Flash"),
            ModelInfo("gemini-3.1-flash-lite-image", (APIKEY_CAT_IMAGE,),
                      display_name="Gemini 3.1 Flash Lite"),
            ModelInfo("gemini-3.1-flash-image", (APIKEY_CAT_IMAGE,),
                      display_name="Gemini 3.1 Flash"),
            ModelInfo("gemini-3-pro-image", (APIKEY_CAT_IMAGE,),
                      display_name="Gemini 3 Pro"),
            # Alias bất hoạt: job/draft cũ vẫn gọi đúng model ổn định, nhưng UI
            # không tiếp tục tạo dữ liệu mới với tên preview đã lỗi thời.
            ModelInfo("gemini-3.1-flash-image-preview", (APIKEY_CAT_IMAGE,),
                      provider_model_id="gemini-3.1-flash-image", is_active=False),
            ModelInfo("gemini-3-pro-image-preview", (APIKEY_CAT_IMAGE,),
                      provider_model_id="gemini-3-pro-image", is_active=False),
            ModelInfo("gemini-2.5-flash", (APIKEY_CAT_CHAT,),
                      display_name="Gemini 2.5 Flash (chat)"),
            ModelInfo("gemini-2.5-flash-preview-tts", ("audio",),
                      display_name="Gemini 2.5 Flash TTS (Preview)", capabilities={
                          "voices": ["Kore", "Puck", "Charon", "Zephyr", "Fenrir",
                                     "Leda", "Orus", "Aoede"],
                          "sample_rate": 24000, "preview": True,
                      }),
        ),
        list_models_path="/models",   # kèm ?key= khi gọi
        notes="Key dạng AIza...; ảnh generateContent đồng bộ; ảnh: responseModalities+imageConfig.",
    ),
    "apiai": Provider(
        id="apiai", display_name="apiai.vn (OpenAI-compat gateway)",
        auth_style=AUTH_BEARER, base_url="https://api.apiai.vn/api/v1",
        categories=(APIKEY_CAT_CHAT, APIKEY_CAT_IMAGE),
        models=(), list_models_path="/models",
        notes="Gateway OpenAI-compat; /chat/completions, /images/generations.",
    ),
    "cheapkeyai": Provider(
        id="cheapkeyai", display_name="cheapkeyai.shop (OpenAI-compat gateway)",
        auth_style=AUTH_BEARER, base_url="https://cheapkeyai.shop/v1",
        categories=(APIKEY_CAT_CHAT, APIKEY_CAT_IMAGE),
        models=(), list_models_path="/models",
        notes="Gateway OpenAI-compat.",
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
                is_active=False,          # mở ở G10, sau cổng G6b
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
                    "context_window": 65_536,
                    "vision": False,
                    "tool_calling": True,
                    "license": "Apache-2.0",
                    "do_duoc": {
                        "decode_tok_s": 68.1,        # trung vị 3 lượt, MTP n-max 2
                        "decode_khong_mtp_tok_s": 40.0,
                        "prefill_tok_s": 1100,       # 1.050–1.190 ở 4 kích cỡ
                        "vram_dinh_mb": 20_339,
                        "nap_model_s": 18,
                    },
                    # ⚠️ Giới hạn phải nói ra, không giấu sau giao diện (D-027).
                    "canh_bao": [
                        N_("máy B dùng chung GPU với việc ảnh và video — bận thì trả 429, không phải lỗi"),
                        N_("cửa sổ 64K là trần Cloudflare, không phải trần model: prompt lấp đầy tốn ~62 giây prefill"),
                    ],
                },
            ),
            ModelInfo(
                "qwen38-vision", (APIKEY_CAT_CHAT,),
                display_name=N_("LTT LLM — đọc ảnh"),
                is_active=True,
                capabilities={
                    "context_window": 65_536,
                    "vision": True,
                    "tool_calling": True,
                    "license": "Apache-2.0",
                    "do_duoc": {"decode_tok_s": 58.5, "vram_dinh_mb": 21_451},
                    "canh_bao": [
                        N_("nạp thêm bộ chiếu ảnh nên tốn hơn ~1,1 GB VRAM so với bản không ảnh"),
                    ],
                },
            ),
            # `qwen38-ops` (200K) CÓ trong llama-swap nhưng KHÔNG khai ở đây:
            # cửa sổ 200K cần ~195 giây prefill khi lấp đầy ⇒ Cloudflare cắt ở 100
            # giây. Nó chỉ dùng được trong LAN, và nền tảng đi qua Cloudflare.
        ),
        list_models_path="/v1/models",
        notes=("Cổng VLM trên máy B (:8299, bearer token), tương thích OpenAI. "
               "Máy B KHÔNG giữ bí mật nào của nền tảng. "
               "429 = BẬN, không phải lỗi — đánh dấu lỗi cho key ở đây sẽ tự tắt "
               "model nhà sau 5 lần (D-005). Gọi qua platform_core/llm/dieu_phoi.py."),
    ),
    "plenx": Provider(
        id="plenx", display_name="PLENX (Seedance/Kling video)",
        auth_style=AUTH_X_API_KEY,
        base_url="https://api.plenxai.com/api/v1/developer",
        categories=(APIKEY_CAT_VIDEO,), async_poll=True,
        models=(
            ModelInfo("seedance-2.0", (APIKEY_CAT_VIDEO,)),
            ModelInfo("seedance-2.0-pro", (APIKEY_CAT_VIDEO,)),
            ModelInfo("kling-3.0", (APIKEY_CAT_VIDEO,)),
        ),
        notes="Key dạng pk_...; video async: POST /generate/video -> GET /status/{id}.",
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
