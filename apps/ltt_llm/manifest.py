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

   🔴 SỬA 01/09 — BA CON SỐ Ở ĐOẠN NÀY ĐỀU ĐÃ TRÔI (P08 F-02/F-03).

   Bản cũ viết *"public API giữ trần input 65K theo Q116"*. Trần thật là
   **96.256** (`TOKEN_VAO_TRAN`), và đã là 96.256 từ đợt dọn tham số 30/08.
   Đừng đọc con số ở đây — đọc `ngan_sach.py`, hoặc hỏi máy B:

       tran.input_tokens tu GET /health cua cong may B  ->  169984

   Số đúng tại thời điểm viết:

     * engine `qwen38-api`     `-c 131072`, trần vào 96.256, **công bố 89K**
     * engine `qwen38-vision`  `-c 65536`,  trần vào 30.720, **công bố 28K**

   ⛔ Vision **không** "vẫn 64K" như bản cũ nói — 65.536 là cửa sổ *engine*, còn
      thứ khách nhét vào được nhỏ hơn nhiều vì phải chừa chỗ cho câu trả lời.
      Nói "64K" với khách là đúng lỗi đã bị bắt ngày 01/09.

   Cửa job vẫn là đường lui cho tác vụ dài.

⛔ GIÁ: `credit_cost` ở đây là **TRẦN ƯỚC CAO**, không phải giá cuối. Với LLM,
   số token RA chỉ biết được sau khi sinh xong. Nền tảng giữ chỗ theo trần này rồi
   **quyết toán theo số thật** (`credit.quyet_toan` không bao giờ thu quá phần đã
   giữ). Công thức nằm ở `platform_core/llm/gia_token.py` — **một chỗ duy nhất**,
   dùng chung cho cả hai cửa.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest, ToolSpec

from apps.ltt_llm import features as _features

#: ⛔ CÁC HẰNG DƯỚI ĐÂY LÀ **BÍ DANH**, KHÔNG PHẢI ĐỊNH NGHĨA.
#:
#:    Nguồn chân lý là `apps/ltt_llm/ngan_sach.py`. Giữ tên cũ ở đây để mã đang
#:    gọi không phải sửa, nhưng **đừng gán số vào chúng nữa** — gán ở đây là
#:    dựng lại đúng cái chồng chéo mà `ngan_sach.py` sinh ra để dẹp.
from apps.ltt_llm.ngan_sach import (CONG_BO_CHO_CLIENT,
                                    CUA_SO_MODEL as CUA_SO_NGU_CANH,
                                    LE as LE_NGU_CANH,
                                    POOL_KV_MAY_B, SO_SLOT_MAY_B,
                                    TOKEN_RA_TRAN as MAX_TOKENS_TRAN,
                                    cong_bo_cua, mac_dinh_cho,
                                    tran_theo_ngu_canh)

#: Token ra mặc định của **cửa job** (manifest phục vụ đường job).
MAX_TOKENS_MAC_DINH = mac_dinh_cho("job")


def _cua_so_noi_voi_khach(model_id: str) -> str:
    """Con số ngữ cảnh **đúng với thứ khách thật sự nhét vào được**, theo model.

    🔴 THAM SỐ `model_id` LÀ BẢN VÁ CHO MỘT LỜI HỨA SAI THỨ HAI (01/09, P08 F-02).

       Bản đầu của hàm này **không có tham số** — nó trả một con số cho **mọi**
       alias. Nên `ltt_llm_vision` được quảng cáo *"same 89K usable input
       context"* trong khi máy B chặn nó ở 65.536, và đo thật cho `413`.

       ⭐ Điều đáng học: bản vá 30/08 dưới đây sửa **con số** (131K → 89K) và
          coi như xong. Khuyết tật thật là **một con số cho hai model**, và nó
          sống thêm một ngày sau khi "đã sửa". Sửa giá trị không phải sửa hình
          dạng.

    🔴 TRƯỚC 30/08 CHỖ NÀY GÕ TAY "131K", VÀ ĐÓ LÀ MỘT LỜI HỨA SAI.

       131.072 là cửa sổ của **engine**. Trần đầu vào của Public API là
       `TOKEN_VAO_TRAN` (96.256, vì phải chừa chỗ cho câu trả lời dài nhất và
       cho sai số của phép ước), còn con số ta **công bố** cho client là
       `CONG_BO_CHO_CLIENT` (88.555, chừa thêm 8 %).

       Khách đọc "131K", nhét 120K token vào, và ăn **413**. Không có gì trên
       trang nói cho họ biết vì sao — đúng lớp lỗi "hai nơi nói hai con số" mà
       `ngan_sach.py` sinh ra để dẹp, chỉ là lần này nó rò ra tới **khách hàng**.

    ⛔ Đừng gõ lại số ở đây. `DEVELOPER_GUIDE.md` **sinh ra** từ manifest này
       (`tools/build_public_api_docs.py`), nên một con số gõ tay ở đây sẽ tự
       nhân bản sang tài liệu ta xuất bản.
    """
    return f"{round(cong_bo_cua(model_id) / 1000)}K"




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
    #    Chọn `chatltt` làm cha: đó là sản phẩm văn bản/hội thoại mà khách
    #    thấy được. Model nhà là **một executor nữa** dưới sản phẩm đó — đúng
    #    nghĩa mà hợp đồng đặt ra cho `catalog_parent`.
    #
    # 🔴 Cha CŨ là `chataistudio`, đã **gỡ hẳn** ở pha 07 (AI CLEAN REBUILD V2)
    #    vì nó là bản sao thứ hai của `chatltt` sau khi mất Codex. Một
    #    `catalog_parent` trỏ tới app không tồn tại làm mục này **rơi khỏi**
    #    catalog — mất chứ không báo lỗi.
    #
    # ⛔ KHÔNG đổi `surface` để chữa: Public API chỉ nhận `"customer"`
    #    (`PUBLIC_SURFACES`), nên đổi surface là đóng luôn đường bán API.
    catalog_parent="chatltt",
    job_types=("ltt_llm.chat",),
    requires=("api",),          # KHÔNG cần GPU của máy A: việc nặng ở máy B
    credit_cost=_cost,
    # Sức khoẻ cho catalog của sản phẩm khác (H43 Phase 06): `GET /live` của
    # cổng máy B, không cần khoá, timeout ngắn. Xem `features.suc_khoe`.
    suc_khoe=_features.suc_khoe,

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
        # Cả job, sync và stream cùng tranh MỘT pool slot + MỘT ngân sách KV của
        # model nhà. Metadata vận hành, không phải alias công khai và không lộ
        # model id. Số lấy từ `ngan_sach.py` — đừng gõ số ở đây (test_1201).
        admission_resource="llm_remote", admission_slots=SO_SLOT_MAY_B,
        admission_token_pool=POOL_KV_MAY_B,
        sync_executor="apps.ltt_llm.executor:EXECUTOR",
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
            # ⛔ `constraints.context_window` KHÔNG PHẢI TRANG TRÍ. Thiếu nó thì
            #    `server/api/tools.py:_dang_codex` rơi về hằng số lùi
            #    `CUA_SO_CONG_BO_MAC_DINH` (60.000) — và khách nhận **hai con số
            #    khác nhau trong CÙNG một phản hồi**: phần chữ nói 89K, trường
            #    `context_window` nói 60000 (P08 F-03).
            #
            #    `test_334::TestBanSaoConLai` nay buộc **mọi** alias ở đây phải
            #    tự khai, nên đường lùi không bao giờ áp cho `ltt_llm` nữa.
            "models": {
                "ltt_llm": {
                    "id": "qwen38-api",
                    "description": (f"Text only, {_cua_so_noi_voi_khach('qwen38-api')} "
                                    f"usable input context. Coding, chat, agentic "
                                    f"tool use, summarisation."),
                    "stability": "stable",
                    "constraints": {
                        "context_window": cong_bo_cua("qwen38-api"),
                        "max_output_tokens": MAX_TOKENS_TRAN,
                    },
                },
                "ltt_llm_vision": {
                    "id": "qwen38-vision",
                    "description": (f"Same model plus image reading, but a smaller "
                                    f"{_cua_so_noi_voi_khach('qwen38-vision')} usable "
                                    f"input context. Send images as OpenAI image_url "
                                    f"parts."),
                    "stability": "stable",
                    "constraints": {
                        "context_window": cong_bo_cua("qwen38-vision"),
                        "max_output_tokens": MAX_TOKENS_TRAN,
                        "reads_images": True,
                    },
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
                    "description": (f"`ltt_llm` for text "
                                    f"({_cua_so_noi_voi_khach('qwen38-api')} usable "
                                    f"input context). `ltt_llm_vision` also reads "
                                    f"images, with a smaller "
                                    f"{_cua_so_noi_voi_khach('qwen38-vision')} "
                                    f"input context."),
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
