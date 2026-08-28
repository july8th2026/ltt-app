"""``POST /api/v1/messages`` và ``POST /api/v1/responses`` — cửa streaming (Q107).

Hai route, một đường ống. Chúng tồn tại vì **mọi CLI đáng phục vụ đều bắt buộc
streaming**, và mỗi CLI chỉ nói đúng một giao thức:

    /api/v1/messages    Anthropic Messages  <- Claude Code CLI, Claude Desktop
    /api/v1/responses   OpenAI Responses    <- Codex CLI, tiện ích Codex VS Code

⭐ ĐỊA CHỈ KHỚP SẴN, KHÔNG PHẢI THIẾT KẾ RA. Hai CLI ghép đuôi hai kiểu khác nhau,
   và chỗ ta đã mount `/api/v1` từ trước hứng đúng cả hai:

     Codex khai `…/api/v1`  + `/responses`     -> /api/v1/responses
     Claude khai `…/api`    + `/v1/messages`   -> /api/v1/messages

   Nên không cần tên miền mới, không cần proxy thứ hai.

⛔ CỔNG NÀY LÀ ỐNG, KHÔNG PHẢI BỘ DỊCH. Nó kiểm, giữ tiền, rồi **chuyển byte
   nguyên xi**. Việc dịch Responses ⇄ Chat là của `llama-server` ở máy B; việc
   nhìn qua để đếm token là của `dem_token_luong`, và nó cũng chỉ **nhìn**.

⛔ KHÔNG ĐÒI `Idempotency-Key` (Q107). Đo thật 23/08: **không CLI nào gửi nó**.
   Thứ giữ tiền thay nó là **thu theo token đã thật sự sinh ra** — khách ngắt
   giữa chừng thì trả phần đã sinh, không trả trọn phần đã giữ.
"""
from __future__ import annotations

import logging
from typing import Iterator, Optional

from fastapi import Body, Depends, Request
from starlette.background import BackgroundTask
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from platform_core.public_api import limits, metrics, policy, sandbox
from platform_core.public_api.catalog import build_catalog, require_tool
from platform_core.public_api.executor import for_tool, for_tool_name
from platform_core.public_api.errors import (insufficient_credit,
                                             invalid_request,
                                             payload_too_large,
                                             service_unavailable)
from platform_core.public_api.principal import Principal
from platform_core.public_api.protocol import (STREAM, PublicOperationContract)
from platform_core.public_api.scopes import SCOPE_JOBS_CREATE
from server.api import tool_dich
from server.api.auth import require_scope
from server.deps import get_db

log = logging.getLogger("server.api.streaming")

_SSE = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}
_NO_STORE = {"Cache-Control": "no-store"}
TOOL_CHAT = "text.chat"

#: Tên tuyến **tương thích**, chỉ tồn tại vì một ràng buộc phía CLIENT.
#:
#: 🔴 VÌ SAO CÓ MỤC NÀY. Claude Desktop ở chế độ `gateway` **lọc danh sách model
#:    trước khi hiện picker**. Luật đọc được từ chính bản cài (1.34493.1.0, tệp
#:    `ce459c687-CEBp0mVy.js`):
#:
#:        Be = /…|gpt|gemini|glm|llama|minimax|mistral|qwen|…/     # CẤM
#:        qe = ["claude", …tên dòng Claude…, "anthropic"]          # PHẢI chứa
#:        Ke(t) = !Be.test(t) && (Ne.test(t) || qe.some(s => t.includes(s)))
#:
#: ⛔ HẬU QUẢ ĐO ĐƯỢC 24/08: `ltt_llm` không chứa chuỗi nào trong `qe` ⇒ bị **lọc
#:    khỏi mảng** ⇒ picker rỗng ⇒ **nút gửi vô hiệu, không một lời báo lỗi nào**.
#:    Cả Enter lẫn bấm nút đều im lặng: không log, không toast, không banner. Mất
#:    một buổi mới tìm ra, vì triệu chứng không hề chỉ về phía nguyên nhân.
#:    (`qwen` còn nằm trong danh sách CẤM, nên tên trung thực nhất cũng bị chặn.)
#:
#: ⭐ VÌ SAO TÊN NÀY CHỨ KHÔNG PHẢI `claude-sonnet-4-5`. Luật chỉ đòi tên **chứa**
#:    chuỗi `claude`; nó **không** đòi một model Anthropic có thật. Nên ta qua
#:    được cổng mà **không** mượn tên sản phẩm của hãng khác. Đây là **tên tuyến**
#:    của một cổng tương thích, không phải tên sản phẩm: catalog, bảng giá và
#:    `/api/v1/tools` vẫn chỉ nói `ltt_llm`, và model đứng sau vẫn là model nhà.
#:
#: ⚠️ ĐỪNG đưa tên này vào `features.ALIAS_SANG_ID`. Chỗ đó là **từ vựng sản phẩm**
#:    của app; mục này là **chi tiết giao thức của một client**. Trộn hai thứ là
#:    cách một hằng số tạm bợ trở thành thứ ta phải đỡ mãi mãi.
TUYEN_TUONG_THICH = {"ltt-llm-claude-compat": "ltt_llm"}


def _giai_ten_model(ten: str) -> str:
    """Tên tuyến tương thích → alias thật. Tên khác giữ nguyên để lỗi ở chỗ cũ."""
    return TUYEN_TUONG_THICH.get(ten, ten)

#: 🔴 NGÂN SÁCH MỞ LUỒNG — 75 giây, và con số này có lý do.
#:
#:    Nó nằm **dưới** trần mặc định 125 giây của Cloudflare, nên khi máy B chậm quá thì
#:    **ta** trả 503 chứ không để Cloudflare trả 524. Một cái 503 của ta client
#:    đọc được; một cái 524 của Cloudflare thì không phân biệt được "hỏng" với
#:    "xong rồi nhưng mất kết nối".
#:
#:    Đủ rộng cho ca xấu đã đo: `llama-swap` nạp lại model ~25 giây.
#:
#: ⛔ NỚI SỐ NÀY KHÔNG MUA THÊM THỜI GIAN. Nó chỉ đổi 503 của ta lấy 524 của
#:    Cloudflare. Nạp từ đĩa lạnh lâu hơn thì giảm nhẹ bằng `ttl` của llama-swap
#:    (giữ model thường trú), không bằng đồng hồ này.
MO_LUONG_GIAY = 75.0


def _tran_giay() -> int:
    """Trần thời gian cho đường **không streaming**.

    Dùng lại đúng con số của `/chat/completions`: không stream nghĩa là không
    byte nào chảy cho tới khi xong, nên đồng hồ 125 giây của Cloudflare có hiệu
    lực ở cả hai chỗ, và vì cùng một lý do.
    """
    from server.api.chat import SYNC_BILLED_MAX_SECONDS
    return int(SYNC_BILLED_MAX_SECONDS)

#: Hợp đồng của hai route này, **khai ra để bộ kiểm chạy được**.
#:
#: ⭐ Dựng ở cấp module có chủ ý: `check_mode_rules` chạy ngay lúc nạp app, nên
#:    một bản sau lỡ bỏ mất một lời hứa của `STREAM` sẽ làm **app không khởi
#:    động được**, thay vì lặng lẽ phục vụ sai. Trước hôm nay
#:    `PublicOperationContract` chỉ được dựng trong test — hợp đồng có bộ kiểm mà
#:    bộ kiểm không bao giờ chạy trên đường thật.
HOP_DONG = PublicOperationContract(
    name="chat.stream",
    execution_mode=STREAM,
    chargeable=True,
    requires_quote=False,
    requires_idempotency_key=False,          # Q107
    scopes=(SCOPE_JOBS_CREATE,),
    extra={
        "event_types": ("message_start", "content_block_start",
                        "content_block_delta", "content_block_stop",
                        "message_delta", "message_stop",
                        "response.created", "response.output_text.delta",
                        "response.completed"),
        "heartbeat_seconds": 15,
        "usage_event": "message_delta | response.completed",
        "cancel_on_disconnect": True,
        "settles_from_measured_usage": True,
    },
)


def register_streaming_routes(api, config, tag: str) -> None:
    @api.post("/messages", tags=[tag],
              summary="Chat completion as an Anthropic Messages stream",
              description=(
                  "Anthropic Messages API over SSE, for Claude Code and Claude "
                  "Desktop. Point ANTHROPIC_BASE_URL at the /api parent of this "
                  "route. Requires \"stream\": true. Credit is held at a ceiling "
                  "and settled from the tokens actually produced."))
    def messages(request: Request, body: dict = Body(...),
                 principal: Principal = Depends(require_scope(SCOPE_JOBS_CREATE)),
                 db: Session = Depends(get_db)) -> StreamingResponse:
        return _cua("/v1/messages", body or {}, principal, db, config)

    @api.post("/responses", tags=[tag],
              summary="Chat completion as an OpenAI Responses stream",
              description=(
                  "OpenAI Responses API over SSE, for the Codex CLI and its VS "
                  "Code extension. Set base_url to this route's parent and "
                  "wire_api = \"responses\". Requires \"stream\": true."))
    def responses(request: Request, body: dict = Body(...),
                  principal: Principal = Depends(require_scope(SCOPE_JOBS_CREATE)),
                  db: Session = Depends(get_db)) -> StreamingResponse:
        return _cua("/v1/responses", body or {}, principal, db, config)


def _mot_cuc(duong: str, than: dict, tin: list, ten: str,
             principal: Principal, db: Session, config, tool=None) -> JSONResponse:
    """Tra loi **mot cuc** cho `/messages` va `/responses`, dung hinh dang
    Anthropic Messages.

    ⭐ DUNG LAI TOAN BO DUONG TINH TIEN da co (`giu_cho_luot` -> goi ->
       `quyet_toan_hoac_hoan`). Khong dung mot so tien thu hai o day: mot he
       thong hai cho tinh tien la mot he thong se lech, va lech ve tien thi khong
       ai phat hien cho toi khi khach doi soat.

    ⚠️ TRAN THOI GIAN. Khong stream nghia la khong co byte nao chay cho toi khi
       xong, nen dong ho 125 giay cua Cloudflare **co hieu luc** o day - khac han
       duong streaming. Vi vay `max_tokens` bi kep theo tran cua duong dong bo,
       cung con so ma `/chat/completions` dung, va vi cung mot ly do.
    """
    from platform_core import credit
    from platform_core.llm import admission, thanh_toan
    from platform_core.llm.cong_vlm import (BanError, CongVlmError,
                                            SuDung, VuotNganSachError)
    from server.api.chat import _tran_max_tokens

    executor = for_tool(tool) if tool is not None else for_tool_name(TOOL_CHAT)

    if sandbox.is_test(principal.mode):
        return JSONResponse(_thu_mot_cuc(ten), status_code=200, headers=_NO_STORE)

    vao_uoc = executor.estimate_input(tin)
    xin_ra = _max_tokens(than, vao_uoc)
    if not any(ten in than for ten in ("max_tokens", "max_output_tokens")):
        xin_ra = min(xin_ra, executor.default_max_tokens)
    tran = _tran_max_tokens(vao_uoc)
    if xin_ra > tran:
        raise invalid_request(
            f"This non-streaming request is estimated at {vao_uoc} input tokens, "
            f"leaving room for at most {tran} output tokens inside its "
            f"{_tran_giay()}s budget. Reduce the prompt or max_tokens, set "
            f"stream=true, or submit it to POST /api/v1/jobs.")
    request_id = thanh_toan.ma_luot("ms")
    ticket = None
    if tool is not None and tool.admission_resource and tool.admission_slots > 0:
        ticket = admission.acquire(
            db, resource=tool.admission_resource, slots=tool.admission_slots,
            user_id=principal.user_id, mode="sync", holder_id=request_id)
    if tool is not None and tool.admission_resource and ticket is None:
        db.rollback()
        raise limits.execution_busy(tool.admission_resource)

    def _release_ticket() -> None:
        if ticket is not None:
            admission.release_by_id(ticket.id)
    try:
        da_giu = thanh_toan.giu_cho_luot(
            db, user_id=principal.user_id, request_id=request_id,
            token_vao_uoc=vao_uoc, max_tokens=xin_ra)
    except credit.ThieuCreditError as e:
        db.rollback()
        raise insufficient_credit(str(e)) from None
    db.commit()

    # 🔴 LƯỚI AN TOÀN CHO TIỀN — VÀ NÓ ĐÃ PHẢI TRẢ GIÁ MỘT LẦN.
    #
    #    Bản đầu chỉ hoàn tiền cho **ba** loại ngoại lệ có tên. Mọi ngoại lệ khác
    #    thoát thẳng ra ngoài, thành `500` — và **để nguyên tiền trong hold**.
    #
    # ⛔ ĐO ĐƯỢC 25/08, tiền thật của khách: Claude Desktop gọi một lượt, ta ném
    #    một ngoại lệ không có trong danh sách, và sổ credit còn lại đúng một
    #    dòng mồ côi: `23:58:10  -1  hold  ms:84e9b…` — **không settle, không
    #    hoàn**. Đường đồng bộ này KHÔNG có Job row, nên `_hoan_credit` của
    #    worker không bao giờ chạm tới nó. Không ai quét. Khách mất tiền im lặng.
    #
    # ⭐ Nên cờ dưới đây đo đúng một điều: **tiền đã được định đoạt chưa** (quyết
    #    toán HOẶC hoàn). Đừng đổi nó thành "đã hoàn chưa" — hai nhánh except bên
    #    trong đã hoàn rồi mới ném tiếp, và hoàn lần hai là trả tiền thừa.
    try:
        # 🔴 ĐI ĐƯỜNG CHUNG, ĐỪNG TỰ DỰNG CLIENT.
        #
        #    Bản đầu gọi thẳng `CongVlm().chat(...)` và **500 ngay lượt đầu**:
        #    `CongVlm.__init__` đòi một tham số `goi`, nó không phải constructor
        #    rỗng. Nhưng lỗi cú pháp đó chỉ là triệu chứng.
        #
        # ⛔ Cái sai thật là **đi vòng qua `dieu_phoi`** — thứ mà chính tài liệu
        #    của nó gọi là *"MỘT đường gọi model ngôn ngữ cho toàn nền tảng"*.
        #    Đi vòng là mất: chọn khoá theo pool, bỏ qua provider đang bận, ánh
        #    xạ tên model theo từng provider, và cách đếm token thống nhất.
        #    Một client dựng tay sẽ **chạy được** trong ca sạch rồi lệch dần ở
        #    đúng những ca mà `dieu_phoi` sinh ra để xử.
        #
        #    `features.chay` là đúng cửa mà `/chat/completions` đã dùng.
        # ⚠️ `_tin_that`, KHÔNG phải `tin`. `tin` là danh sách **ước token** và
        #    các phần tử của nó cố ý không có `role` — xem `_tin_that`.
        #
        # ⭐ Rồi dịch sang giao thức OpenAI: máy B nói OpenAI, khách nói Anthropic.
        #    `sang_openai_messages` là thứ giữ được **vòng gọi tool** — khối
        #    `tool_use` thành `tool_calls`, khối `tool_result` thành các tin
        #    `role="tool"` riêng, đúng thứ tự.
        sach = {"model": ten, "max_tokens": xin_ra,
                "messages": tool_dich.sang_openai_messages(_tin_that(than))}
        cong_cu = tool_dich.sang_openai_tools(than.get("tools"))
        if cong_cu:
            sach["tools"] = cong_cu
        kq = executor.run(db, sach, timeout_s=float(_tran_giay()))
    except executor.parameter_error as e:
        # Tham số sai là lỗi của **yêu cầu**, không phải của máy chủ: 400, không
        # phải 500. Hoàn tiền trước, vì hold đã đặt rồi.
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        _release_ticket()
        raise invalid_request(str(e)) from None
    except BanError as e:
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        _release_ticket()
        # ⛔ BAN != HONG (D-005). 429/503 + Retry-After, va khach KHONG bi thu tien.
        raise service_unavailable(f"The model is busy right now: {e}",
                                  retry_after=getattr(e, "thu_lai_sau_s", 30)) from None
    except (VuotNganSachError, CongVlmError) as e:
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        _release_ticket()
        log.warning("mot cuc that bai user=%s: %s", principal.user_id[:8], e)
        raise service_unavailable("The model could not serve this request.") from None
    except BaseException:
        # ⛔ ĐO ĐƯỢC 25/08, TIỀN THẬT CỦA KHÁCH. Ba nhánh trên chỉ bắt ngoại lệ
        #    **có tên**. Một ngoại lệ ngoài danh sách thoát thẳng ra thành `500`
        #    và **để nguyên tiền trong hold**: sổ credit còn đúng một dòng mồ côi
        #    `23:58:10  -1  hold  ms:84e9b…` — không quyết toán, không hoàn.
        #
        # ⚠️ Và KHÔNG AI QUÉT NÓ. Đường đồng bộ này không tạo `Job`, nên
        #    `_hoan_credit` của worker không bao giờ nhìn thấy. Khách mất tiền
        #    lặng lẽ, và không có báo cáo nào chỉ ra điều đó.
        #
        # ⭐ Vì sao `BaseException` chứ không phải `Exception`: khách ngắt kết nối
        #    giữa chừng có thể tới dưới dạng `CancelledError` — thứ **không** kế
        #    thừa `Exception`. Đó chính là ca hay xảy ra nhất ở một cửa đồng bộ.
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        _release_ticket()
        raise

    # `quyet_toan_hoac_hoan` nhan chinh doi tuong `SuDung` do cong tra ve - dung
    # tu boc token roi truyen so le: chinh no biet cach xu khi KHONG DO DUOC
    # (hoan du va ghi canh bao), va do la luat tien cua ca he thong.
    # ⚠️ `features.chay` tra ve `KetQua` cua app (token phang), khong phai
    #    `KetQuaChat` cua cong (co `.su_dung`). Boc y het `/chat/completions`,
    #    ke ca `dang_tin=kq.do_duoc` - do la co bao "co do duoc token khong", va
    #    `quyet_toan_hoac_hoan` dua vao no de HOAN DU khi khong do duoc.
    try:
        thanh_toan.quyet_toan_hoac_hoan(
            db, user_id=principal.user_id, request_id=request_id,
            su_dung=SuDung(token_vao=kq.token_vao, token_ra=kq.token_ra,
                           token_vao_cache=kq.token_vao_cache,
                           dang_tin=kq.do_duoc))
    except BaseException:
        # Cùng một lý do với lưới ở trên: hold đã đặt rồi, nên đường thoát nào
        # cũng phải trả nó lại. Hỏng ở bước quyết toán mà bỏ chạy thì tiền kẹt.
        db.rollback()
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        _release_ticket()
        raise
    db.commit()
    _release_ticket()
    metrics.increment("chat:mot_cuc")
    return JSONResponse(_dang_anthropic(kq, ten, request_id),
                        status_code=200, headers=_NO_STORE)


#: Ánh xạ lý do dừng: **kiểu OpenAI → kiểu Anthropic**.
#:
#: 🔴 KHÔNG ĐƯỢC TRUYỀN THẲNG. Máy B nói giao thức OpenAI nên trả `stop` /
#:    `length` / `tool_calls`; hợp đồng Anthropic Messages khai một tập **khác
#:    hẳn**: `end_turn`, `max_tokens`, `stop_sequence`, `tool_use`, `pause_turn`,
#:    `refusal`.
#:
#: ⛔ Bản đầu của tôi viết `kq.finish_reason or "end_turn"` — tức đưa thẳng chữ
#:    `stop` của OpenAI vào một trường mà client Anthropic đọc theo bảng trên.
#:    Client không vỡ ngay: nó chỉ **không nhận ra** giá trị, rồi xử lý sai ở chỗ
#:    quan trọng nhất — `length` (bị cắt vì hết token) trông y hệt một câu trả
#:    lời hoàn chỉnh, nên client sẽ không biết mà xin tiếp.
LY_DO_DUNG = {
    "stop": "end_turn",
    "length": "max_tokens",
    "tool_calls": "tool_use",
    "content_filter": "refusal",
}


def _dang_anthropic(kq, ten: str, request_id: str) -> dict:
    """Bọc kết quả thành hình dạng `message` của Anthropic Messages API.

    Trường bắt buộc, theo tài liệu chính thức: `id`, `type`, `role`, `model`,
    `content`, `stop_reason`, `stop_sequence`, `usage`.

    ⛔ `model` trả về là **alias của khách** (`ltt_llm`), không phải id nội bộ của
       máy B. Khách không bao giờ được nhìn thấy `qwen38-*` — `test_212` chốt.

    ⚠️ `stop_details` phải **có mặt và bằng `null`** khi không phải từ chối. Tài
       liệu nói nó chỉ được điền khi `stop_reason == "refusal"`, nhưng client đọc
       nó vô điều kiện; thiếu khoá và có khoá `null` là hai chuyện khác nhau với
       một bộ giải mã chặt.
    """
    ly_do = LY_DO_DUNG.get(kq.finish_reason or "", "end_turn")

    khoi = tool_dich.sang_anthropic_content(kq.noi_dung,
                                            getattr(kq, "tool_calls", ()))

    # 🔴 KHÔNG ĐƯỢC KHAI `tool_use` KHI KHÔNG CÓ KHỐI `tool_use` NÀO.
    #
    #    Hợp đồng Anthropic: `stop_reason: "tool_use"` là lời hứa rằng trong
    #    `content` có ít nhất một khối `{"type": "tool_use", …}`. Client đọc
    #    `stop_reason`, đi tìm khối đó để chạy tool — không thấy thì nó **treo**,
    #    chứ không báo lỗi.
    #
    # ⚠️ Và hôm nay ta **chưa** dựng được khối đó: `_mot_cuc` không truyền `tools`
    #    lên model, nên model không có gì để gọi. Hỗ trợ tool cho đúng cần dịch
    #    HAI CHIỀU (`tools`/`tool_use`/`tool_result` của Anthropic ↔ `tools`/
    #    `tool_calls`/tin `tool` của OpenAI) — một việc riêng, có test riêng.
    #
    # ⭐ Cho tới lúc đó, thà nói `end_turn` còn hơn hứa một thứ không có. Một câu
    #    trả lời thiếu tool là chuyện khách thấy ngay; một client treo thì không.
    if ly_do == "tool_use" and not any(k.get("type") == "tool_use" for k in khoi):
        log.warning("upstream bao tool_calls nhung khong dung duoc khoi tool_use; "
                    "ha ve end_turn de client khong treo")
        ly_do = "end_turn"
    # Và chiều ngược lại: có khối `tool_use` thì `stop_reason` PHẢI nói `tool_use`,
    # dù thượng nguồn báo `stop`. Client dừng vòng lặp theo `stop_reason`; nói
    # `end_turn` trong khi vừa đưa ra một lời gọi tool là bảo nó **đừng chạy**.
    elif any(k.get("type") == "tool_use" for k in khoi):
        ly_do = "tool_use"

    return {
        "id": "msg_" + request_id,
        "type": "message",
        "role": "assistant",
        "model": ten,
        "content": khoi,
        "stop_reason": ly_do,
        "stop_sequence": None,
        "stop_details": None,
        "usage": {"input_tokens": kq.token_vao,
                  "output_tokens": kq.token_ra},
    }


def _thu_mot_cuc(ten: str) -> dict:
    """Che do thu: dung hinh dang, khong cham GPU, khong cham so tien."""
    return {
        "id": "msg_sandbox", "type": "message", "role": "assistant",
        "model": ten,
        "content": [{"type": "text", "text": "sandbox: khong goi model that"}],
        "stop_reason": "end_turn", "stop_sequence": None, "stop_details": None,
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }


def _bao_400(detail: str, than: dict):
    """Ghi lại LÝ DO + HÌNH DẠNG request mỗi khi ta trả 400 — để soi vì sao Codex
    bị vứt lượt. (Tạm; gỡ khi đã chẩn xong.) KHÔNG log nội dung nhạy cảm, chỉ
    khoá/kiểu."""
    tc = than.get("tool_choice")
    vao = than.get("input")
    log.warning(
        "400 /v1/responses: %s | stream=%s model=%r tc=%r input=%s(len=%s) "
        "tools=%s keys=%s",
        detail, than.get("stream"), than.get("model"),
        (tc.get("type") if isinstance(tc, dict) else tc),
        type(vao).__name__, (len(vao) if isinstance(vao, (list, str)) else "-"),
        len(than.get("tools") or []), sorted(than.keys()))
    return invalid_request(detail)


def _cua(duong: str, than: dict, principal: Principal, db: Session,
         config) -> StreamingResponse:
    from platform_core import credit
    from platform_core.llm import admission, thanh_toan

    # `text.chat` phải qua đủ ba cổng của Q92. Có route riêng KHÔNG cho nó đi
    # vòng qua công tắc người vận hành — cửa mới không được là cửa sau.
    tool = require_tool(build_catalog(config), TOOL_CHAT, principal)
    executor = for_tool(tool)


    ten = _giai_ten_model(str(than.get("model") or ""))
    aliases = executor.aliases()
    if ten not in aliases:
        raise _bao_400(
            f"`model` must be one of {list(aliases)}"
            f"{' or ' + str(list(TUYEN_TUONG_THICH)) if TUYEN_TUONG_THICH else ''}. "
            f"Claude Code sends whatever ANTHROPIC_MODEL is set to, and Codex "
            f"sends `model` from its profile — set them to one of these.", than)

    tin = _tin_nhan(than)
    if not tin:
        raise _bao_400("the request carries no input to answer", than)

    # 🔴 `tool_choice` — CHỈ TỪ CHỐI Ở ĐƯỜNG KHÔNG-STREAM.
    #
    #    Đường **không stream** đi qua `features.chay` → `dieu_phoi.goi`, nơi
    #    **không** nhận `tool_choice`; nuốt im lặng ở đó là để model trả lời bằng
    #    chữ khi khách **ép** gọi tool — nên phải từ chối, không bỏ qua.
    #
    #    Đường **stream** thì KHÁC: `gui = dict(than)` được chuyển **nguyên xi**
    #    tới máy B (llama-server, tương thích OpenAI, CÓ hỗ trợ `tool_choice`).
    #    Từ chối ở đây là bug thật đã chặn Codex: tiện ích Codex **ép** một tool
    #    (`tool_choice: {"type":"function","name":"..."}`) ở nhiều lượt agentic;
    #    ta trả 400 → lượt đó chết lặng (model đã chạy trên GPU nhưng bị vứt), và
    #    khách thấy "GPU dừng mà không có gì xảy ra". (Đo 2026-08-27.)
    #
    # ⭐ `auto` bỏ qua được ở cả hai vì nó **đã là** mặc định của thượng nguồn.
    _chon = than.get("tool_choice")
    if _chon is not None and not than.get("stream"):
        _loai = _chon if isinstance(_chon, str) else (_chon or {}).get("type")
        if _loai != "auto":
            raise _bao_400(
                f"`tool_choice` {_loai!r} is not supported on non-streaming "
                f"requests; only \"auto\" (the default) is honoured there. "
                f"Use streaming, or omit the field.", than)

    # Dịch alias -> id nội bộ NGAY TRƯỚC KHI ra khỏi nền tảng. Khách không bao
    # giờ nhìn thấy `qwen38-*`, và mã của khách không ghim vào nó (test_212).
    gui = dict(than)
    gui["model"] = executor.model_id(ten)


    # 🔴 KHONG STREAM CUNG PHAI PHUC VU DUOC, va day la mot lo hong THAT.
    #
    #    Ban dau route nay tu choi thang moi request khong co `stream: true`, voi
    #    ly do "nhan roi tra mot cuc la noi doi client". Ly do do dung cho mot
    #    client DA XIN streaming - nhung sai voi hop dong Anthropic Messages,
    #    thu ma **cho phep ca hai**.
    #
    # ⛔ HAU QUA DO DUOC 24/08: Claude Desktop **tham do model** bang mot request
    #    KHONG streaming toi `/v1/messages`. Ta tra 400, ung dung ket luan
    #    *"Gateway rejected model ltt_llm"* va **CHAN LUON o chat** - khong phai
    #    mot canh bao trang tri, ma la mot cua dong.
    #
    #    Tuc mot dong `if` giu cho hop dong "sach" da lam ca mot ung dung khach
    #    khong dung duoc, va trieu chung ma khach nhin thay ("model khong kha
    #    dung") **khong he chi ve phia nguyen nhan**.
    if not than.get("stream"):
        return _mot_cuc(duong, than, tin, ten, principal, db, config, tool)

    resolved = policy.resolve(db, config=config, principal=principal,
                              tool_name=TOOL_CHAT)
    limits.enforce_create_rate(key_id=principal.key_id, config=config,
                               limits=resolved, user_id=principal.user_id)

    # ── Chế độ thử: không chạm GPU, không chạm sổ tiền ───────────────────────
    # ⛔ ĐỪNG BỎ NHÁNH NÀY. Một khoá thử ai đăng ký cũng có; để nó chiếm GPU thật
    #    là mở một cách miễn phí để giữ card của máy B.
    if sandbox.is_test(principal.mode):
        return StreamingResponse(_luong_thu(duong), media_type="text/event-stream",
                                 headers=_SSE)

    # ⛔ KHONG tu ghep chuoi o day: `credit_entries.job_id` la VARCHAR(36) va
    #    PostgreSQL ep do dai trong khi SQLite thi khong. Xem `thanh_toan.ma_luot`.
    request_id = thanh_toan.ma_luot("st")
    ticket = admission.acquire(
        db, resource=tool.admission_resource, slots=tool.admission_slots,
        user_id=principal.user_id, mode="stream", holder_id=request_id)
    if ticket is None:
        db.rollback()
        raise limits.execution_busy(tool.admission_resource)
    vao_uoc = executor.estimate_input(tin)
    xin_ra = _max_tokens(than, vao_uoc)

    # 🔴 GHI GIÁ TRỊ ĐÃ KẸP TRỞ LẠI THÂN GỬI LÊN. Thiếu dòng này là lỗi thật, tìm
    #    ra 24/08 khi cắm Claude Code lần đầu (H38/L2).
    #
    #    `_max_tokens()` kẹp về `MAX_TOKENS_TRAN`, nhưng kết quả chỉ dùng cho
    #    phần **giữ tiền**. Thân `gui` vẫn mang con số thô của khách. Nên ta kẹp
    #    cái mình **thu tiền** mà không kẹp cái mình **gửi đi**, và máy B trả 413.
    #
    #    Claude Code gửi `max_tokens: 32000` mặc định — con số khách gần như
    #    không có cách nào đổi. Nên trước khi sửa, Claude Code **hoàn toàn không
    #    dùng được**, và triệu chứng là một 503 "thử lại sau" cho một thứ thử lại
    #    bao nhiêu lần cũng hỏng.
    #
    # ⭐ VÌ SAO KẸP CHỨ KHÔNG TỪ CHỐI, khác hẳn `chat.py`. `max_tokens` là một
    #    **trần**, không phải một lượng đặt hàng: kẹp nó xuống chỉ giới hạn câu
    #    trả lời có thể dài tới đâu, và tiền vẫn tính theo token **thật sự sinh
    #    ra** nên khách không trả thêm đồng nào. Còn `chat.py` từ chối là đúng ở
    #    đó, vì lý do của nó là **thời gian** (trần 125 giây của Cloudflare) —
    #    kẹp `max_tokens` không cứu được một lượt chạy quá lâu.
    #
    # ⛔ Giữ nguyên TÊN TRƯỜNG khách đã dùng: `/responses` của Codex đọc
    #    `max_output_tokens`, hai cửa kia đọc `max_tokens`. Ghi nhầm tên là thêm
    #    một trường lạ mà thượng nguồn bỏ qua — tức lại gửi đi con số thô.
    for _ten in ("max_tokens", "max_output_tokens"):
        if _ten in gui:
            gui[_ten] = xin_ra
            break
    else:
        gui["max_tokens"] = xin_ra
    try:
        da_giu = thanh_toan.giu_cho_luot(
            db, user_id=principal.user_id, request_id=request_id,
            token_vao_uoc=vao_uoc, max_tokens=xin_ra)
    except credit.ThieuCreditError as e:
        # Không đủ tiền thì không đốt GPU. Chốt trước, không phải sau.
        #
        # ⭐ Đếm nó — xem ghi chú cùng chỗ ở `chat.py`.
        metrics.increment(metrics.CREDIT_EXHAUSTED)
        log.info("khach het credit tai %s: user=%s", duong, principal.user_id[:8])
        db.rollback()
        raise insufficient_credit(str(e)) from None

    # 🔴 CHỐT GIAO DỊCH TRƯỚC KHI CHẠM MODEL. Cùng bài học đã học ở
    #    `server/api/chat.py`: giữ giao dịch mở suốt lượt gọi thì giữ luôn một
    #    kết nối CSDL, và tiến trình chết giữa chừng sẽ cuộn mất phần giữ chỗ.
    #    Với streaming còn nặng hơn: generator chạy **sau khi** phản hồi đã bắt
    #    đầu, lúc đó `get_db` đã đóng phiên rồi.
    db.commit()

    from platform_core.llm import luong_vlm

    try:
        mo = luong_vlm.mo(db, duong=duong, than=gui, timeout_s=MO_LUONG_GIAY)
    except luong_vlm.KhongMoDuocLuong as e:
        _hoan(principal.user_id, request_id)
        admission.release_by_id(ticket.id)
        if e.ban:
            # ⛔ BẬN ≠ HỎNG. 503 + Retry-After, và khách KHÔNG bị thu tiền.
            raise service_unavailable(f"The model is busy right now: {e.ly_do}",
                                      retry_after=e.thu_lai_sau_s) from None
        if getattr(e, "qua_dai", False):
            # 413 context_length_exceeded: ngữ cảnh vượt trần đầu-vào của máy B.
            # KHÔNG phải hỏng tạm — client PHẢI nén/bỏ lượt cũ rồi thử lại; retry
            # nguyên si chỉ tạo bão (đúng cái Codex đã dính: hội thoại/phản hồi
            # dài → 413 bị dịch nhầm 503 → "im lặng"). Trả 413 để Codex/Claude
            # tự tóm tắt hội thoại.
            log.warning("ngu canh qua dai user=%s: %s",
                        principal.user_id[:8], e.ly_do)
            raise payload_too_large(
                "The input exceeds the model's context limit. Drop or summarise "
                "older turns and retry with a shorter conversation. "
                f"[{e.ly_do}]") from None
        log.warning("khong mo duoc luong cho user=%s: %s",
                    principal.user_id[:8], e.ly_do)
        raise service_unavailable("The model could not serve this request.") from None
    except BaseException:
        _hoan(principal.user_id, request_id)
        admission.release_by_id(ticket.id)
        raise

    metrics.increment("chat:stream")
    return StreamingResponse(
        _phat(mo, user_id=principal.user_id, request_id=request_id,
              da_giu=da_giu, lease_id=ticket.id),
        media_type=mo.content_type, headers=_SSE,
        background=BackgroundTask(admission.release_by_id, ticket.id))


def _phat(mo, *, user_id: str, request_id: str, da_giu: int,
          lease_id: str = "") -> Iterator[bytes]:
    """Chuyển byte nguyên xi, đếm token dọc đường, quyết toán khi hết.

    ⛔ `finally` chứ không phải "sau vòng lặp". Khách đóng kết nối thì Starlette
       ném `GeneratorExit` vào ngay chỗ `yield`, và nhánh sau vòng lặp **không
       bao giờ chạy** — nghĩa là một lượt đã đốt GPU sẽ không bao giờ được quyết
       toán, và phần giữ chỗ nằm lại đó mãi.
    """
    from platform_core.llm.dem_token_luong import DemToken
    import time as _time

    dem = DemToken()
    vo: Optional[BaseException] = None
    khach_ngat = False
    _t0 = _time.monotonic()
    _n_khoi = 0
    _t_byte_dau: Optional[float] = None
    from contextlib import nullcontext
    from platform_core.llm import admission
    keeper = admission.keep_alive(lease_id) if lease_id else nullcontext()
    with keeper:
        try:
            for khoi in mo.luong:
                if _t_byte_dau is None:
                    _t_byte_dau = _time.monotonic() - _t0
                _n_khoi += 1
                dem.nhin(khoi)
                yield khoi
        except GeneratorExit:
            khach_ngat = True
            raise
        except BaseException as e:                              # noqa: BLE001
            vo = e
            raise
        finally:
            _dt = _time.monotonic() - _t0
            log.warning(
                "STREAM %s rid=%s dur=%.1fs ttfb=%s khoi=%s token_ra=%s",
                "KHACH-NGAT" if khach_ngat else ("LOI" if vo else "XONG"),
                request_id[-8:], _dt,
                (f"{_t_byte_dau:.1f}s" if _t_byte_dau is not None else "-"),
                _n_khoi, dem.token_ra)
            _quyet_toan(user_id, request_id, dem, da_giu)
            if vo is not None:
                mo.hong(vo)
            else:
                mo.xong(tokens=dem.token_ra)


def _quyet_toan(user_id: str, request_id: str, dem, da_giu: int) -> None:
    """Chốt tiền, trong một phiên CSDL **mới**.

    ⚠️ Phiên của request đã đóng từ lúc phản hồi bắt đầu — generator này chạy sau
       đó. Dùng lại phiên cũ là `DetachedInstanceError` hoặc tệ hơn: một giao
       dịch không bao giờ được commit.
    """
    from platform_core.db import get_session
    from platform_core.llm import thanh_toan

    gen = get_session()
    db = next(gen)
    try:
        thu = thanh_toan.quyet_toan_hoac_hoan(
            db, user_id=user_id, request_id=request_id, su_dung=dem.su_dung())
        db.commit()
        log.info("stream %s: giu=%s thu=%s token_ra=%s do_duoc=%s",
                 request_id[-8:], da_giu, thu.thu_credit, dem.token_ra,
                 dem.do_duoc)
    except Exception:                                           # noqa: BLE001
        db.rollback()
        # 🔴 Ồn ào có chủ ý. Không quyết toán được nghĩa là phần giữ chỗ nằm lại
        #    trên tài khoản khách — tiền của họ bị treo, và không có gì khác báo.
        log.exception("KHONG QUYET TOAN DUOC stream %s user=%s",
                      request_id[-8:], user_id[:8])
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _hoan(user_id: str, request_id: str) -> None:
    from platform_core.db import get_session
    from platform_core.llm import thanh_toan

    gen = get_session()
    db = next(gen)
    try:
        thanh_toan.hoan_luot(db, user_id=user_id, request_id=request_id)
        db.commit()
    except Exception:                                           # noqa: BLE001
        db.rollback()
        log.exception("khong hoan duoc phan giu cho cua %s", request_id[-8:])
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── Đọc yêu cầu của hai giao thức ────────────────────────────────────────────

def _tin_nhan(than: dict) -> list:
    """Rút phần văn bản đầu vào, dù client nói giao thức nào.

    Chỉ dùng để **ước** token đầu vào cho phần giữ chỗ, nên không cần chính xác
    tuyệt đối — nhưng phải ước **CAO**, vì giữ thiếu thì khách tiêu quá số dư.
    """
    ra: list = []
    he_thong = than.get("system")
    if isinstance(he_thong, str):
        ra.append({"content": he_thong})
    elif isinstance(he_thong, list):
        ra.extend({"content": (m or {}).get("text", "")} for m in he_thong
                  if isinstance(m, dict))

    tin = than.get("messages")
    if isinstance(tin, list):
        ra.extend(m for m in tin if isinstance(m, dict))

    # Responses gọi nó là `input`, và nó có thể là chuỗi trần.
    vao = than.get("input")
    if isinstance(vao, str):
        ra.append({"content": vao})
    elif isinstance(vao, list):
        ra.extend(m for m in vao if isinstance(m, dict))

    # Định nghĩa tool đi kèm mỗi lượt và **không hề nhỏ**: đo thật 23/08, prompt
    # hệ thống của Codex là ~21.936 token. Bỏ qua nó là ước thiếu rất nhiều.
    cong_cu = than.get("tools")
    if isinstance(cong_cu, list) and cong_cu:
        import json
        ra.append({"content": json.dumps(cong_cu, ensure_ascii=False)})
    return ra


def _chu_trong(khoi) -> str:
    """Văn bản trong một trường có thể là chuỗi **hoặc** danh sách khối Anthropic."""
    if isinstance(khoi, str):
        return khoi
    if isinstance(khoi, list):
        return "\n".join(str((m or {}).get("text", "")) for m in khoi
                         if isinstance(m, dict))
    return ""


def _tin_that(than: dict) -> list:
    """`messages` **THẬT** để gửi cho model — khác hẳn `_tin_nhan`.

    🔴 HAI HÀM NÀY TRÔNG GIỐNG NHAU VÀ KHÔNG THỂ THAY NHAU. `_tin_nhan` chỉ để
       **ước token**, nên nó cố ý sinh ra những phần tử **không có `role`**:
       prompt hệ thống thành `{"content": …}`, và cả khối JSON của `tools` cũng
       được nhét vào như một "tin nhắn" để cộng token.

    ⛔ ĐO ĐƯỢC 25/08, TRÊN PRODUCTION. Bản đầu của `_mot_cuc` đem thẳng danh sách
       ước ấy đi gọi model. Hai hậu quả, và cái thứ hai tệ hơn:

       1. Request nào có `system` hoặc `tools` thì `kiem_tham_so` ném
          `ThamSoSai: moi phan tu cua messages phai co role` → **500**.
       2. Request nào **không** vỡ thì model nhận một hội thoại đã bị bóp méo:
          prompt hệ thống mất vai trò, và định nghĩa tool trở thành một lượt nói
          của người dùng. Nó **vẫn trả lời**, nên lỗi này không tự lộ ra — phép
          thử `8x7` vẫn đúng, và điều đó che mất chuyện ngữ cảnh đã sai.

    ⭐ Nên đường gọi model phải có hàm riêng, và `_tin_nhan` ở lại đúng việc của
       nó. Ước token được phép cẩu thả; thứ gửi cho model thì không.
    """
    ra: list = []
    he = _chu_trong(than.get("system"))
    if he.strip():
        ra.append({"role": "system", "content": he})

    for m in than.get("messages") or []:
        if isinstance(m, dict) and m.get("role"):
            ra.append(m)

    # `/responses` gọi nó là `input`, và nó có thể là chuỗi trần.
    vao = than.get("input")
    if isinstance(vao, str) and vao.strip():
        ra.append({"role": "user", "content": vao})
    elif isinstance(vao, list):
        ra.extend(m for m in vao if isinstance(m, dict) and m.get("role"))
    return ra


def _max_tokens(than: dict, token_vao_uoc: int = 0, executor=None) -> int:
    """Trần token ra cho lượt này, đã kẹp theo **chỗ còn lại trong ngữ cảnh**.

    ⚠️ `token_vao_uoc` mặc định 0 chỉ để không phá lời gọi cũ; đường thật luôn
       truyền số vào. Vào và ra chia nhau cùng một cửa sổ 65.536.
    """
    executor = executor or for_tool_name(TOOL_CHAT)
    tran = executor.context_output_cap(token_vao_uoc)
    for ten in ("max_tokens", "max_output_tokens"):
        gt = than.get(ten)
        if isinstance(gt, (int, float)) and not isinstance(gt, bool):
            return max(1, min(int(gt), tran))
    return min(executor.default_max_tokens, tran)


def _luong_thu(duong: str) -> Iterator[bytes]:
    """Luồng của chế độ thử: đúng hình dạng, không model, không tiền."""
    import json

    def sk(ten: str, goi: dict) -> bytes:
        return (f"event: {ten}\n".encode()
                + b"data: " + json.dumps(goi).encode() + b"\n\n")

    chu = "[test mode] no model was called and no credit moved."
    if duong.endswith("/responses"):
        yield sk("response.created", {"type": "response.created",
                                      "response": {"id": "resp_test",
                                                   "status": "in_progress"}})
        yield sk("response.output_text.delta",
                 {"type": "response.output_text.delta", "delta": chu})
        yield sk("response.completed", {
            "type": "response.completed",
            "response": {"id": "resp_test", "status": "completed",
                         "usage": {"input_tokens": 0, "output_tokens": 0}}})
        return
    yield sk("message_start", {"type": "message_start", "message": {
        "id": "msg_test", "type": "message", "role": "assistant", "content": [],
        "usage": {"input_tokens": 0, "output_tokens": 0}}})
    yield sk("content_block_start", {"type": "content_block_start", "index": 0,
                                     "content_block": {"type": "text", "text": ""}})
    yield sk("content_block_delta", {"type": "content_block_delta", "index": 0,
                                     "delta": {"type": "text_delta", "text": chu}})
    yield sk("content_block_stop", {"type": "content_block_stop", "index": 0})
    yield sk("message_delta", {"type": "message_delta",
                               "delta": {"stop_reason": "end_turn"},
                               "usage": {"output_tokens": 0}})
    yield sk("message_stop", {"type": "message_stop"})
