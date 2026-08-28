"""
Bản khai của `ltt_llm` — model ngôn ngữ chạy trên máy nhà, bán ra ngoài. (H38)

⭐ MỘT KHAI BÁO, HAI CÁNH CỬA.

   Public API của nền tảng (H35/Q92) xây quanh **tool**: `/api/v1/tools` và
   `/api/v1/models` đều **suy ra từ manifest**, không có danh sách trung tâm nào.
   `catalog.build_models` nói rõ vì sao: *"a central list is a second place to
   update, and the day it disagrees with the tools it is the catalog that is
   wrong"*.

   Nên chat **phải** khai như một tool. Đổi lại ta được miễn phí:

     GET  /api/v1/tools              liệt kê `text.chat`
     GET  /api/v1/models             liệt kê `ltt_llm`, `ltt_llm_vision`
     POST /api/v1/jobs               ĐƯỜNG BẤT ĐỒNG BỘ, chạy ngay, không viết gì thêm
     principal.may_use_tool(...)     phân quyền theo khoá khách

   Và cánh cửa thứ hai — `POST /api/v1/chat/completions`, đồng bộ, tương thích
   OpenAI — dùng **chính khai báo này**, không dựng sổ model thứ hai.

⭐ VÌ SAO CẦN CẢ HAI CỬA, KHÔNG PHẢI MỘT:

     đồng bộ (OpenAI)   khách trỏ SDK vào là chạy; nhưng **Cloudflare mặc định
                        cắt ở 125 giây**, nên chỉ hợp prompt vừa phải
     bất đồng bộ (job)  né được trần 125 giây; nhưng khách phải học hình dạng
                        job của ta

   Ngữ cảnh 131K là cửa sổ engine đã đo trên RTX 3090; public API giữ trần
   input 81K theo Q115 để còn biên thời gian cho Cloudflare sau biến thiên
   cold-load. Bản vision vẫn 64K cho tới khi có benchmark riêng. Cửa job vẫn là
   đường lui cho tác vụ dài.

⛔ GIÁ: `credit_cost` ở đây là **TRẦN ƯỚC CAO**, không phải giá cuối. Với LLM,
   số token RA chỉ biết được sau khi sinh xong. Nền tảng giữ chỗ theo trần này rồi
   **quyết toán theo số thật** (`credit.quyet_toan` không bao giờ thu quá phần đã
   giữ). Công thức nằm ở `platform_core/llm/gia_token.py` — **một chỗ duy nhất**,
   dùng chung cho cả hai cửa.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest, ToolSpec

#: Trần token ra mặc định khi khách không khai `max_tokens`. Giữ chỗ theo số này.
MAX_TOKENS_MAC_DINH = 4096

#: Cửa sổ ngữ cảnh của `qwen38-api`, khớp `-c 131072` trong `llama-swap.yaml`.
#: **Vào và ra dùng chung con số này**, nên nó là ràng buộc thật, không phải
#: `MAX_TOKENS_TRAN`.
CUA_SO_NGU_CANH = 131_072

#: Chừa chỗ cho khuôn chat, định nghĩa tool và sai số của phép ước token vào.
#: `uoc_token_vao` là ƯỚC, không phải phép đếm thật — nên phải có biên.
LE_NGU_CANH = 2_048

#: Trần cứng của app. Cổng VLM còn một trần riêng của nó (`LTT_LLM_MAX_*`);
#: cái nào chặt hơn thì cái đó thắng — đúng tinh thần "hai chốt độc lập".
#:
#: ⭐ NÂNG 16.384 → 32.768 ngày 24/08 (chủ sản phẩm quyết), và điều làm nó AN
#:    TOÀN chứ không phải "chắc là được": `llama.cpp` cấp KV cache cho **toàn bộ**
#:    `-c 131072` ngay lúc nạp model. Nên VRAM **không đổi** dù trần token ra là
#:    16K hay 32K — chiều duy nhất có thể nguy hiểm thì không hề động tới.
#:    Đây KHÔNG phải một ngoại lệ của luật "chưa đo thì không chạy" (D-032):
#:    benchmark 131K đã cấp toàn bộ KV trên đúng card 24 GB trước khi chốt Q111.
#:
#: ⛔ VÀ VÌ SAO PHẢI LÀ ≥ 32.000: Claude Code gửi `max_tokens: 32000` mặc định,
#:    và khách gần như **không có cách nào đổi**. Trần 16.384 khiến Claude Code
#:    hoàn toàn không dùng được — phát hiện 24/08 khi cắm thật (H38/L2).
MAX_TOKENS_TRAN = 32_768


def tran_theo_ngu_canh(token_vao_uoc: int) -> int:
    """Trần token ra **thật sự dùng được** cho một lượt, biết ngữ cảnh còn bao nhiêu.

    🔴 VÌ SAO KHÔNG DÙNG THẲNG `MAX_TOKENS_TRAN`. Vào và ra chia nhau **cùng một**
       cửa sổ 131.072. Một lượt có 100.000 token vào mà xin 32.768 token ra thì
       tổng vượt cửa sổ, và thứ hỏng ở đó **không phải một lỗi sạch** — model
       cắt bớt ngữ cảnh hoặc thượng nguồn từ chối, cả hai đều khó truy.

    ⛔ Trả về ít nhất 1: một lượt không còn chỗ để trả lời thì phải hỏng ở chốt
       token VÀO với thông điệp đúng, chứ không phải biến thành `max_tokens=0`.
    """
    con_lai = CUA_SO_NGU_CANH - int(token_vao_uoc or 0) - LE_NGU_CANH
    return max(1, min(MAX_TOKENS_TRAN, con_lai))


def _cost(params: dict) -> int:
    """Trần credit của một lượt gọi. **Ước CAO có chủ ý.**

    Giữ thiếu thì khách tiêu quá số dư; giữ dư thì hoàn lại. Chiều sai thứ nhất
    đắt hơn nhiều.

    ⛔ Không tự nghĩ ra công thức ở đây. Gọi `gia_token` — nó là chỗ duy nhất được
       phép đại diện cho giá, và cả cửa đồng bộ lẫn cửa job đều đọc nó.
    """
    from platform_core.llm import gia_token

    from apps.ltt_llm.features import uoc_token_vao

    token_vao_uoc = uoc_token_vao(params.get("messages"), params.get("tools"))

    xin_ra = params.get("max_tokens")
    xin_ra = int(xin_ra) if isinstance(xin_ra, (int, float)) else MAX_TOKENS_MAC_DINH
    xin_ra = max(1, min(xin_ra, MAX_TOKENS_TRAN))

    tran = gia_token.uoc_tran(token_vao_uoc=token_vao_uoc, max_tokens=xin_ra)
    return max(1, tran.tong_credit_lam_tron_len)


MANIFEST = AppManifest(
    slug="ltt_llm",
    display_name=N_('LTT LLM — model ngôn ngữ của nhà'),
    route_prefix="/ltt-llm",
    summary=N_('Model ngôn ngữ chạy trên máy nhà: coding, chat, agent, '
               'tóm tắt, đọc ảnh. Bán qua API cho khách lập trình.'),
    icon="🧠",
    accent="#3F51B5",

    nav=(),                     # chưa có giao diện web — API trước, UI sau

    # ⛔ SỬA 2026-08-26 — TRƯỚC ĐÓ ĐÂY LÀ MỘT LINK 404 TRONG HEADER CỦA **MỌI**
    #    KHÁCH ĐÃ ĐĂNG NHẬP. Đo được: `GET /ltt-llm` → **404**, mà
    #    `visible_on_surface(authenticated=True)` vẫn trả `True`.
    #
    #    Vì sao: `nav=()` **không** có nghĩa là "không có nav" — `nav_entries()`
    #    tự sinh lại một dòng trỏ vào `route_prefix` khi app không khai gì. Và
    #    app này không có `routes.py`, nên đích của dòng đó không tồn tại.
    #
    # ⭐ `catalog_parent` là cơ chế hợp đồng đã có sẵn cho đúng việc này, và
    #    `anhnoibo` đã dùng nó để tránh **đúng cái bẫy này** — chú thích ở
    #    `apps/anhnoibo/manifest.py` mô tả chính xác kịch bản trên. App này thì
    #    không, nên nó rơi vào.
    #
    #    Chọn `chataistudio` làm cha: đó là sản phẩm văn bản/hội thoại mà khách
    #    thấy được. Model nhà là **một executor nữa** dưới sản phẩm đó — đúng
    #    nghĩa mà hợp đồng đặt ra cho `catalog_parent`.
    #
    # ⛔ KHÔNG đổi `surface` để chữa: Public API chỉ nhận `"customer"`
    #    (`PUBLIC_SURFACES`), nên đổi surface là đóng luôn đường bán API.
    catalog_parent="chataistudio",
    job_types=("ltt_llm.chat",),
    requires=("api",),          # KHÔNG cần GPU của máy A: việc nặng ở máy B
    credit_cost=_cost,

    enabled=True,
    group="AI",
    # ⛔ HAI CỜ KHÁC NHAU, ĐỪNG TRỘN:
    #    `public`  — catalog WEB (H6/Q30). False vì chưa có trang giới thiệu.
    #    `surface` — Public API chỉ nhận `"customer"` (`PUBLIC_SURFACES`), và
    #                đó đúng bản chất: đây là năng lực BÁN CHO KHÁCH.
    #    Cộng thêm cổng thứ ba: `LTT_PUBLIC_API_TOOLS` phải liệt kê `text.chat`.
    #    Ba cổng độc lập — quên một cái thì thiếu tính năng, không phải lộ hàng.
    public=False,
    surface="customer",
    lifecycle="development",
    # ⛔ BẮT BUỘC với mọi app `surface="customer"` không có `catalog_parent`:
    #    `test_60::test_portfolio_surface_and_lifecycle_match_locked_decisions`
    #    đòi mọi thẻ hiện ở catalog phải nói được **nó làm gì** — thẻ trống là
    #    một ô trong cửa hàng không ghi bán gì.
    capabilities=("AI Text",),
    notes=("Model chạy ở máy B qua `llm_gateway` (:8299). Máy B KHÔNG giữ bí mật "
           "nào của nền tảng (Q102). Gọi qua `platform_core/llm/dieu_phoi.py` — "
           "đừng tự dựng HTTP, đó đúng là lỗi mà `dieu_phoi` sinh ra để sửa."),

    tools=(ToolSpec(
        name="text.chat", job_type="ltt_llm.chat",
        description=N_('Sinh văn bản từ hội thoại: coding, chat, agent, tóm tắt.'),
        # Cả job, sync và stream cùng tranh đúng một slot của model nhà. Đây là
        # metadata vận hành, không phải alias công khai và không lộ model id.
        admission_resource="llm_remote", admission_slots=1,
        params_schema={
            "messages": {"type": "json[]", "required": True},
            "model": {"type": "enum",
                      "values": ["ltt_llm", "ltt_llm_vision"],
                      "default": "ltt_llm"},
            "max_tokens": {"type": "int", "min": 1, "max": MAX_TOKENS_TRAN,
                           "default": MAX_TOKENS_MAC_DINH},
            "temperature": {"type": "number", "min": 0.0, "max": 2.0},
            # `json[]`, khong phai `json`: OpenAI khai `tools` la mot MANG.
            "tools": {"type": "json[]"},
            "reasoning_effort": {"type": "enum",
                                 "values": ["low", "medium", "xhigh"],
                                 "default": "medium"},
        },
        returns={"content": "text", "tool_calls": "json[]", "usage": "json"},

        # ── Public API (Q92) ─────────────────────────────────────────────────
        api_exposed=True,
        api_contract={
            "scopes": ("jobs:create",),
            "description": ("Generate text from a conversation. Handles coding, "
                            "chat, agentic tool use, summarisation and image "
                            "reading. OpenAI-compatible message format."),
            # ⭐ ALIAS ≠ ID NỘI BỘ, và khoảng cách đó chính là giá trị của alias:
            #    "Aliases exist so a vendor change is not a breaking change."
            #    Khách ghim vào `ltt_llm`; ngày ta đổi GGUF bên dưới thì mã của họ
            #    không phải sửa một dòng nào.
            #    ⚠️ Bản đầu tôi đặt alias trùng hệt id — `test_212` bắt được.
            "models": {
                "ltt_llm": {
                    "id": "qwen38-api",
                    "description": ("Text only, 131K context. Coding, chat, "
                                    "agentic tool use, summarisation."),
                    "stability": "stable",
                },
                "ltt_llm_vision": {
                    "id": "qwen38-vision",
                    "description": ("Same model plus image reading. 64K context. "
                                    "Send images as OpenAI image_url parts."),
                    "stability": "stable",
                },
            },
            "enums": {
                "model": ["ltt_llm", "ltt_llm_vision"],
                "reasoning_effort": ["low", "medium", "xhigh"],
            },
            "params": {
                "messages": {
                    "description": ("Conversation so far, OpenAI format: a list "
                                    "of {role, content}. `content` may be a "
                                    "string, or a list of parts for images."),
                    "example": [{"role": "user", "content": "Explain HTTP 429."}],
                },
                "model": {
                    "description": ("`ltt_llm` for text (131K context). "
                                    "`ltt_llm_vision` also reads images."),
                    "example": "ltt_llm",
                },
                "max_tokens": {
                    "description": ("Ceiling on generated tokens. Credit is held "
                                    "against this and refunded down to what was "
                                    "actually generated."),
                    "example": 1024,
                },
                "temperature": {"description": "Sampling temperature.", "example": 0.7},
                "tools": {
                    "description": ("Function definitions, OpenAI format. The "
                                    "model may answer with `tool_calls`."),
                    "example": [],
                },
                "reasoning_effort": {
                    "description": ("How much the model thinks before answering. "
                                    "Deeper costs more output tokens."),
                    "example": "medium",
                },
            },
        },
    ),),
)
