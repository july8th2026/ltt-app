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

from dataclasses import dataclass, field
from typing import Optional

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
