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
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from platform_core.public_api import limits, metrics, policy, sandbox
from platform_core.public_api.catalog import build_catalog, require_tool
from platform_core.public_api.errors import (insufficient_credit,
                                             invalid_request,
                                             service_unavailable)
from platform_core.public_api.principal import Principal
from platform_core.public_api.protocol import (STREAM, PublicOperationContract)
from platform_core.public_api.scopes import SCOPE_JOBS_CREATE
from server.api.auth import require_scope
from server.deps import get_db

log = logging.getLogger("server.api.streaming")

_SSE = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}
TOOL_CHAT = "text.chat"

#: 🔴 NGÂN SÁCH MỞ LUỒNG — 75 giây, và con số này có lý do.
#:
#:    Nó nằm **dưới** trần 100 giây của Cloudflare, nên khi máy B chậm quá thì
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


def _cua(duong: str, than: dict, principal: Principal, db: Session,
         config) -> StreamingResponse:
    from apps.ltt_llm import features
    from platform_core import credit
    from platform_core.llm import thanh_toan

    # `text.chat` phải qua đủ ba cổng của Q92. Có route riêng KHÔNG cho nó đi
    # vòng qua công tắc người vận hành — cửa mới không được là cửa sau.
    require_tool(build_catalog(config), TOOL_CHAT, principal)

    if not than.get("stream"):
        # Nhận rồi trả một cục là nói dối client: nó đang chờ `text/event-stream`
        # và sẽ vỡ ở chỗ khó lần hơn nhiều.
        raise invalid_request(
            'This endpoint streams: send "stream": true. For a single '
            "non-streaming answer use POST /api/v1/chat/completions.")

    ten = str(than.get("model") or "")
    if ten not in features.ALIAS_SANG_ID:
        raise invalid_request(
            f"`model` must be one of {list(features.ALIAS_SANG_ID)}. Claude Code "
            f"sends whatever ANTHROPIC_MODEL is set to, and Codex sends `model` "
            f"from its profile — set them to one of these.")

    tin = _tin_nhan(than)
    if not tin:
        raise invalid_request("the request carries no input to answer")

    # Dịch alias -> id nội bộ NGAY TRƯỚC KHI ra khỏi nền tảng. Khách không bao
    # giờ nhìn thấy `qwen38-*`, và mã của khách không ghim vào nó (test_212).
    gui = dict(than)
    gui["model"] = features.ALIAS_SANG_ID[ten]

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
    xin_ra = _max_tokens(than)
    try:
        da_giu = thanh_toan.giu_cho_luot(
            db, user_id=principal.user_id, request_id=request_id,
            token_vao_uoc=features.uoc_token_vao(tin), max_tokens=xin_ra)
    except credit.ThieuCreditError as e:
        # Không đủ tiền thì không đốt GPU. Chốt trước, không phải sau.
        #
        # ⭐ Đếm nó — xem ghi chú cùng chỗ ở `chat.py`.
        metrics.increment(metrics.CREDIT_EXHAUSTED)
        log.info("khach het credit tai %s: user=%s", duong, principal.user_id[:8])
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
        if e.ban:
            # ⛔ BẬN ≠ HỎNG. 503 + Retry-After, và khách KHÔNG bị thu tiền.
            raise service_unavailable(f"The model is busy right now: {e.ly_do}",
                                      retry_after=e.thu_lai_sau_s) from None
        log.warning("khong mo duoc luong cho user=%s: %s",
                    principal.user_id[:8], e.ly_do)
        raise service_unavailable("The model could not serve this request.") from None

    metrics.increment("chat:stream")
    return StreamingResponse(
        _phat(mo, user_id=principal.user_id, request_id=request_id,
              da_giu=da_giu),
        media_type=mo.content_type, headers=_SSE)


def _phat(mo, *, user_id: str, request_id: str, da_giu: int) -> Iterator[bytes]:
    """Chuyển byte nguyên xi, đếm token dọc đường, quyết toán khi hết.

    ⛔ `finally` chứ không phải "sau vòng lặp". Khách đóng kết nối thì Starlette
       ném `GeneratorExit` vào ngay chỗ `yield`, và nhánh sau vòng lặp **không
       bao giờ chạy** — nghĩa là một lượt đã đốt GPU sẽ không bao giờ được quyết
       toán, và phần giữ chỗ nằm lại đó mãi.
    """
    from platform_core.llm.dem_token_luong import DemToken

    dem = DemToken()
    vo: Optional[BaseException] = None
    try:
        for khoi in mo.luong:
            dem.nhin(khoi)
            yield khoi
    except GeneratorExit:
        # Khách bỏ đi. KHÔNG phải lỗi của khoá — đánh dấu lỗi ở đây là đường
        # thẳng tới D-005 (khoá model nhà tự tắt sau 5 lần).
        raise
    except BaseException as e:                                  # noqa: BLE001
        vo = e
        raise
    finally:
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


def _max_tokens(than: dict) -> int:
    from apps.ltt_llm.manifest import MAX_TOKENS_MAC_DINH, MAX_TOKENS_TRAN

    for ten in ("max_tokens", "max_output_tokens"):
        gt = than.get(ten)
        if isinstance(gt, (int, float)) and not isinstance(gt, bool):
            return max(1, min(int(gt), MAX_TOKENS_TRAN))
    return MAX_TOKENS_MAC_DINH


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
