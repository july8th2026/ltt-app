"""``/api/v1/tools`` — the public catalog endpoints.

The routes are thin on purpose: gating and projection live in
``platform_core.public_api.catalog`` so they can be tested without HTTP, and so
a second caller (the portal, an SDK generator) sees exactly the same answer.
"""
from __future__ import annotations

from fastapi import Depends, Query
from fastapi.responses import JSONResponse

from platform_core.public_api.catalog import (build_catalog, build_models,
                                              capabilities_of, require_model,
                                              require_tool, visible_to)
from platform_core.public_api.pagination import Page, PageRequest
from platform_core.public_api.principal import Principal
from platform_core.public_api.scopes import SCOPE_TOOLS_READ
from server.api.auth import require_scope

_NO_STORE = {"Cache-Control": "no-store"}

#: Cửa sổ ngữ cảnh **CÔNG BỐ** cho client agentic, khi model không tự khai.
#:
#: ⚠️ Đây phải là con số **NHỎ HƠN trần đầu-vào thật của thượng nguồn**, không
#:    phải cửa sổ lý thuyết của model. Máy B nạp `qwen38-api` với `-c 131072`
#:    nhưng cổng của nó chặn ở `LTT_LLM_MAX_INPUT_TOKENS` (65.000 lúc đo 29/08).
#:    Công bố 131072 thì Codex nén quá muộn và đâm thẳng vào 413 của B.
#:
#: ⭐ Đổi trần bên B thì đổi luôn số này — chúng là **một** phép hứa, kể ở hai nơi.
CUA_SO_CONG_BO_MAC_DINH = 60_000

#: Trần token ra, khớp `MAX_TOKENS_TRAN` của app `ltt_llm`.
TOKEN_RA_TOI_DA = 32_768

#: Mức suy luận Codex được phép chọn, khớp enum `reasoning_effort` của app.
_MUC_SUY_LUAN = ({"effort": "low", "description": "Fast, light reasoning"},
                 {"effort": "medium", "description": "Balanced"},
                 {"effort": "xhigh", "description": "Deepest reasoning"})


def _dang_codex(model) -> dict:
    """Một model alias, viết theo **đúng khuôn `codex_models_manager` đọc được**.

    Tên trường lấy từ chính `~/.codex/models_cache.json` của Codex chứ không
    đoán: `slug`, `context_window`, `max_context_window`, `shell_type`,
    `apply_patch_tool_type`, `input_modalities`. Thiếu `slug` là Codex bỏ cả
    mục; sai `context_window` là nó nén sai lúc.
    """
    rang_buoc = dict(getattr(model, "constraints", None) or {})
    cua_so = int(rang_buoc.get("context_window") or CUA_SO_CONG_BO_MAC_DINH)
    ra = int(rang_buoc.get("max_output_tokens") or TOKEN_RA_TOI_DA)
    doc_anh = bool(rang_buoc.get("reads_images")
                   or "vision" in str(model.name).lower())
    # Ngưỡng nén và trần kết quả tool — **suy ra**, không gõ thêm hằng số.
    # Cùng phép suy với hai bộ cài (`tools/cam_cli.py`), nên ba nơi không lệch
    # được: khoảng trống giữa ngưỡng nén và cửa sổ phải chứa trọn một lượt ra.
    nen = cua_so - ra
    d = {
        "slug": model.name,
        "display_name": model.name,
        "description": model.description,
        "context_window": cua_so,
        "max_context_window": cua_so,
        "max_output_tokens": int(rang_buoc.get("max_output_tokens")
                                 or TOKEN_RA_TOI_DA),
        "default_reasoning_level": "medium",
        "supported_reasoning_levels": [dict(m) for m in _MUC_SUY_LUAN],
        "shell_type": "unified_exec",
        "apply_patch_tool_type": "freeform",
        "input_modalities": ["text", "image"] if doc_anh else ["text"],
        "visibility": "list",
        "supported_in_api": True,
        "priority": 1,
        # 🔴 BA TRƯỜNG DƯỚI ĐÂY LÀ **BẮT BUỘC**, và thiếu chúng thì Codex bỏ
        #    **cả mục** — im lặng, rồi rơi về metadata dự phòng của nó
        #    (272.000 ngữ cảnh, KHÔNG nén), tức bảo đảm một `413` giữa phiên.
        #
        # ⛔ Đo 04/09 trên `rust-v0.145.0`: `ModelInfo` có 17 trường không mang
        #    `#[serde(default)]`; endpoint này thiếu **tám**. Năm trong tám là
        #    `Option<T>` — serde tự cho `None`, vô hại. Ba cái còn lại KHÔNG
        #    phải `Option`, và chính ba cái đó giết cả mục:
        #      `support_verbosity: bool`               (openai_models.rs:424)
        #      `truncation_policy: TruncationPolicyConfig`          (:429)
        #      `experimental_supported_tools: Vec<String>`          (:449)
        #
        # ⭐ Phân biệt đó không phải suy luận — nó đến từ một phép thử BÁC BỎ:
        #    catalog của bộ cài cũng thiếu 5 trường mà Codex vẫn chạy thật. Nếu
        #    "thiếu bất kỳ trường bắt buộc nào là hỏng" thì bộ cài đã phải hỏng.
        #    Nó không hỏng ⇒ giả thuyết đầu của tôi sai ⇒ ranh giới thật là
        #    `Option` hay không.
        "support_verbosity": False,
        "truncation_policy": {"mode": "tokens", "limit": max(ra // 2, 1)},
        "experimental_supported_tools": [],
    }
    # ⛔ BỎ HẲN khi không ngưỡng nào giữ được lời hứa (`nen <= 0`), thay vì ghi
    #    một con số trông hợp lệ. Thiếu trường thì Codex dùng mặc định của nó
    #    (90% cửa sổ); một con số bịa thì nó TIN, và cái giá là `413` giữa
    #    phiên. Cùng luật với `tools/cam_cli.py`.
    if nen > 0:
        d["auto_compact_token_limit"] = nen
    return d


def register_tool_routes(api, config, tag: str) -> None:
    """Attach the catalog routes straight onto the public sub-application.

    Directly, not through ``include_router``: this FastAPI version keeps an
    included router as an opaque wrapper without ``.path`` (see
    ``server/api/__init__`` and ``tests/test_152``), which would make the route
    inventory — the thing that stops undeclared routes shipping — blind to
    exactly the routes it exists to check.
    """
    router = api

    @router.get("/tools", tags=[tag],
                summary="List the tools this API key may call",
                description=("Returns the public tool catalog, narrowed to what "
                             "the calling key is allowed to use."))
    def list_tools(
        limit: int = Query(default=None, description="Page size (max 100)."),
        offset: int = Query(default=None, description="Rows to skip."),
        principal: Principal = Depends(require_scope(SCOPE_TOOLS_READ)),
    ) -> JSONResponse:
        page_request = PageRequest.parse(limit, offset)
        catalog = visible_to(build_catalog(config), principal)
        window = catalog[page_request.offset:
                         page_request.offset + page_request.fetch_limit]
        page = Page.of([tool.to_public_dict() for tool in window], page_request)
        return JSONResponse(page.to_dict(), headers=_NO_STORE)

    @router.get("/tools/{tool_name}", tags=[tag], summary="Contract for one tool",
                description=("Returns the input/output contract of a single "
                             "tool. Unknown or unavailable tools answer 404."))
    def get_tool(
        tool_name: str,
        principal: Principal = Depends(require_scope(SCOPE_TOOLS_READ)),
    ) -> JSONResponse:
        tool = require_tool(build_catalog(config), tool_name, principal)
        return JSONResponse(tool.to_public_dict(), headers=_NO_STORE)

    @router.get("/models", tags=[tag],
                summary="List the model aliases this API key may use",
                description=("Returns the public model aliases, what they can "
                             "do, how stable they are and which tools accept "
                             "them. Prices come from POST /quotes, which prices "
                             "a whole call rather than a model."))
    def list_models(
        capability: str = Query(default="", description="Filter by capability."),
        limit: int = Query(default=None, description="Page size (max 100)."),
        offset: int = Query(default=None, description="Rows to skip."),
        principal: Principal = Depends(require_scope(SCOPE_TOOLS_READ)),
    ) -> JSONResponse:
        page_request = PageRequest.parse(limit, offset)
        catalog = visible_to(build_catalog(config), principal)
        models = build_models(catalog)
        if capability:
            models = [model for model in models
                      if model.capability == str(capability)]
        window = models[page_request.offset:
                        page_request.offset + page_request.fetch_limit]
        page = Page.of([model.to_public_dict() for model in window],
                       page_request)
        body = page.to_dict()
        # Capabilities belong with the models rather than on the anonymous
        # `/capabilities` route: which domains a deployment actually sells is
        # commercial information, and V2 already decided the tool list lives
        # behind a key.
        body["capabilities"] = capabilities_of(catalog)
        # 🔴 `models` LÀ CHO CODEX ĐỌC, KHÔNG PHẢI MỘT BẢN SAO CHO ĐẸP.
        #
        #    Codex (`codex_models_manager`) gọi `{base_url}/models` và **đòi**
        #    khoá gốc tên `models`. Thấy `items` nó bỏ qua toàn bộ, in
        #    *"failed to refresh available models: missing field `models`"* rồi
        #    *"Model metadata for `ltt_llm` not found. Defaulting to fallback
        #    metadata"* — và **fallback của nó là `context_window` 272.000**.
        #
        # ⛔ HẬU QUẢ ĐO ĐƯỢC 29/08, và nó chính là lỗi "hội thoại dài thì im":
        #    Codex tưởng còn 272K nên **không nén hội thoại**, gửi ngữ cảnh vượt
        #    trần đầu-vào thật của máy B → B trả 413 → khách thấy im lặng. Con số
        #    ta công bố ở đây là thứ DUY NHẤT dạy Codex nén đúng lúc.
        body["models"] = [_dang_codex(model) for model in window]
        return JSONResponse(body, headers=_NO_STORE)

    @router.get("/models/{model_name}", tags=[tag],
                summary="Details of one model alias",
                description=("Returns one model alias. Unknown or unavailable "
                             "aliases answer 404, exactly like a tool."))
    def get_model(
        model_name: str,
        principal: Principal = Depends(require_scope(SCOPE_TOOLS_READ)),
    ) -> JSONResponse:
        catalog = visible_to(build_catalog(config), principal)
        model = require_model(build_models(catalog), model_name)
        return JSONResponse(model.to_public_dict(), headers=_NO_STORE)
