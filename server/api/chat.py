"""``POST /api/v1/chat/completions`` — cửa đồng bộ có thu tiền (Q106, H38 V3).

⭐ VÌ SAO CỬA NÀY TỒN TẠI, DÙ CỬA JOB ĐÃ CHẠY. `ASYNC_JOB` hợp lệ về mọi mặt, nhưng
   nó bắt **mọi** khách viết một vòng lặp hỏi trạng thái trước khi nhận được câu
   "hello" đầu tiên. Đây là API bán ra ngoài để khách cắm SDK vào; dòng lệnh đầu
   tiên trong tài liệu OpenAI phải chạy được.

⭐ VÌ SAO NÓ KHÔNG PHẢI `SYNC`. `SYNC` cấm cả ba thứ một lượt chat cần: cấm thu
   tiền, cấm gọi GPU, cấm chạy quá 5 giây. `check_mode_rules` chặn thẳng, và chốt
   đó **đang làm đúng việc** — lách nó bằng `chargeable=False` sẽ qua được cửa và
   để lại một lượt đốt GPU mà không ai bị tính tiền. Nên Q106 thêm hẳn chế độ thứ
   ba, `SYNC_BILLED`, khai đúng thứ đang xảy ra.

Ba luật của chế độ đó, và cả ba đều thi hành ở file này:

  1. **Bắt buộc `Idempotency-Key`.** Không có quote (giá phụ thuộc token đầu ra,
     thứ chưa tồn tại lúc ký giá), nên khoá này là thứ **duy nhất** chặn một lần
     thử lại vì mạng mua hàng hai lần.
  2. **Giữ chỗ trước khi chạm nhà cung cấp, quyết toán theo số đo thật.** Giữ là
     trần ước cao; hoá đơn là token đã đo. Không đo được thì **hoàn đủ**.
  3. **Không đẩy vào hàng đợi**, và không chạy quá `SYNC_BILLED_MAX_SECONDS`.

⛔ KHÔNG NỚI TRẦN THỜI GIAN Ở ĐÂY. Cloudflare mặc định cắt ở 125 giây nếu không
   nhận được byte; ngân sách nội bộ 90 giây giữ biên cho tunnel và quyết toán.
   Lượt dài hơn đi stream hoặc cửa job.
"""
from __future__ import annotations

import logging
import time

from fastapi import Body, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from platform_core import credit
from platform_core.public_api import (idempotency, limits, metrics, policy,
                                      sandbox)
from platform_core.public_api.catalog import build_catalog, require_tool
from platform_core.public_api.executor import for_tool, for_tool_name
from platform_core.public_api.errors import (THIEU_CREDIT_LOI,
                                             insufficient_credit,
                                             invalid_request,
                                             model_not_found,
                                             service_unavailable,
                                             thieu_credit_chi_tiet,
                                             tran_bi_vuot)
from platform_core.public_api.principal import Principal
from platform_core.public_api.protocol import SYNC_BILLED_MAX_SECONDS
from platform_core.public_api.scopes import SCOPE_JOBS_CREATE
from server.api import su_kien_loi
from server.api.auth import require_scope
from server.api.streaming import HEADER_EFFORT_BO_QUA
from server.deps import get_db

log = logging.getLogger("server.api.chat")

_NO_STORE = {"Cache-Control": "no-store"}
OPERATION_CHAT = "chat.completions"

#: Tool đứng sau cửa này. Nó vẫn phải qua đủ ba cổng của Q92 như mọi tool khác —
#: có route riêng **không** làm nó bỏ qua `LTT_PUBLIC_API_TOOLS`.
TOOL_CHAT = "text.chat"

#: `Retry-After` khi hết trần chờ. Đã chờ tới trần rồi mới trả 429, nên khuyên
#: thử lại sau vài giây là khuyên đúng — không phải 15 giây của cửa "bận ngay".
_THU_LAI_S = 10

#: Khách đã ngắt trước khi có câu trả lời. 499 là mã của nginx cho đúng tình
#: huống này; không client nào đọc nó (họ đi rồi) nhưng **sổ request thì đọc**,
#: và trộn nó vào 5xx là biến một chuyện bình thường thành một báo động giả.
MA_KHACH_NGAT = 499
_KHACH_NGAT = {"code": "client_disconnected",
               "detail": "The client disconnected before the answer was ready."}
#: Lượt bị HUỶ theo yêu cầu (`/v1/huy`, hoặc cổng máy B trả 499).
#:
#: 🔴 VÌ SAO TỒN TẠI. `cong_vlm.HuyError` KHÔNG được bắt ở cửa đồng bộ lẫn cửa
#:    stream — đo 14/09/2026: `grep HuyError server/` trả **0 dòng**. Nên một
#:    lượt khách CHỦ ĐỘNG huỷ rơi vào nhánh bắt-tất-cả và khách nhận
#:    **500 `internal_error`** cho một sự việc mà chính docstring của lớp ấy gọi
#:    là *"KHÔNG PHẢI LỖI — của ai cả"*. Một 500 còn kéo theo cảnh báo trực và
#:    những vòng thử lại không ai muốn.
#:
#: ⭐ Dùng lại đúng **499** và đúng hình dạng của `_KHACH_NGAT` ngay trên: hai
#:    sự việc anh em (khách đi / khách huỷ) phải cùng một khuôn. Khác nhau đúng
#:    một chữ — `code` — vì hai nguyên nhân ấy phân biệt được và nên phân biệt.
#:
#: ⚠️ Cả hai thân 499 này nằm NGOÀI `problem+json` của `/api/v1`. Đó là hiện
#:    trạng có từ trước, không phải thứ bản vá này đẻ ra; đưa chúng vào khuôn
#:    chung là một đổi hợp đồng riêng, cần chốt riêng.
_DA_HUY = {"code": "request_cancelled",
           "detail": "The request was cancelled before it finished."}


def kiem_ten_model(tool, ten) -> None:
    """Tên `model` không có trong danh mục công khai ⇒ `model_not_found` (D02).

    🔑 NGUỒN LÀ `tool.model_aliases` — **đúng dict** mà `GET /api/v1/models`
       chiếu ra. Nên câu trả lời ở đây không bao giờ lệch với danh sách khách
       vừa đọc; một danh sách gõ tay ở cửa là bản chân lý thứ hai.

    🔴 VÌ SAO KHÔNG ĐỂ `executor.validate` LO (dual-model 2.3, Step 2c). Nó có
       bắt, nhưng bắt thành `invalid_request` — câu nói *"yêu cầu của bạn sai
       hình dạng"*. Khách vừa bị cắt tên `ltt_llm` cần nghe *"tên model ấy không
       còn"*, và họ phải nghe **cùng một câu** dù đi đường nào:

         · tên đã cắt (`ltt_llm`, `ltt_llm_vision`)         -> ở đây
         · tên bản khai admission không phủ (`KeyError`)    -> chỗ giải admission

       Hai đường, một mã lỗi, một chỉ dẫn: gọi `GET /api/v1/models`.

    ⛔ Rỗng thì KHÔNG ném: model là tham số **tuỳ chọn** và mặc định do app khai.
    """
    ten = str(ten or "")
    if not ten:
        return
    bi_danh = getattr(tool, "model_aliases", None) or {}
    if bi_danh and ten not in bi_danh:
        raise model_not_found(
            f"`model` {ten!r} is not served here. Call GET /api/v1/models for "
            f"the names in service: {', '.join(sorted(bi_danh))}.")


def _tran_max_tokens(token_vao_uoc: int = 0, executor=None) -> int:
    """Trần `max_tokens` mà một lượt ĐỒNG BỘ được phép xin.

    🔴 CON SỐ NÀY DẪN RA TỪ SỐ ĐO, KHÔNG PHẢI CHỌN CHO TRÒN:

        thời gian = nạp model + hạ tầng + input/prefill + output/decode

        prefill bảo thủ     750 tok/s  (đo 756,49 ở 131K)
        decode bảo thủ       40 tok/s  (đo 41,57)
        nạp model + hạ tầng  30 giây

    ⛔ Xin nhiều hơn thì **từ chối ngay**, đừng nhận rồi để Cloudflare cắt giữa
       chừng. Ta từ chối bằng một cái 400 nói rõ lý do và chỉ sang cửa job; nó
       cắt bằng một cái 524 không ai đọc được.
    """
    executor = executor or for_tool_name(TOOL_CHAT)
    return executor.sync_output_cap(token_vao_uoc, SYNC_BILLED_MAX_SECONDS)


def _than_openapi(config) -> dict:
    """Mô tả thân request cho OpenAPI, **lấy từ chính hợp đồng của tool**.

    🔴 VÌ SAO CẦN. Đo 14/09/2026 trên `GET /api/v1/openapi.json`:

           /chat/completions  requestBody -> {"type":"object",
                                              "additionalProperties":true}

       Tức spec **máy đọc** không nói một chữ nào về `model`, `messages`,
       `max_tokens`, `reasoning_effort` hay sáu tham số mở hôm nay. Ai trỏ một
       bộ sinh client vào đó sẽ nhận một client chỉ biết `dict` — trong khi
       `DEVELOPER_GUIDE.md` (người đọc) thì đầy đủ. Hai bề mặt của **cùng một
       hợp đồng**, một bên rỗng.

       Và ta **quảng cáo** nó: guide ghi *"Spec máy đọc: GET /api/v1/openapi.json"*.

    ⭐ Nguyên nhân là chữ ký `body: dict = Body(...)` — FastAPI không có gì để
       suy ra. Nhưng catalog **đã dựng sẵn** `ToolSpec.input_schema` từ
       `params_schema`, đủ cả enum, mặc định và mô tả. Nên đây chỉ là **nối một
       nguồn đã có vào một bề mặt đang rỗng**, không phải khai lại lần hai.

    ⛔ Trả `{}` khi không dựng được: một spec thiếu mô tả vẫn phải bật được
       server. Đổi chữ ký handler sang model Pydantic thì hợp đồng sẽ bị khai ở
       **hai** nơi và ngày chúng lệch nhau là ngày spec nói dối.
    """
    try:
        from platform_core.public_api.catalog import build_catalog

        for tool in build_catalog(config):
            if tool.name == TOOL_CHAT:
                return {"requestBody": {"required": True, "content": {
                    "application/json": {"schema": dict(tool.input_schema)}}}}
    except Exception:                       # noqa: BLE001
        log.exception("khong dung duoc schema OpenAPI cho %s", TOOL_CHAT)
    return {}


def register_chat_routes(api, config, tag: str) -> None:
    @api.post("/chat/completions", tags=[tag],
              summary="Chat completion, answered in the request",
              openapi_extra=_than_openapi(config),
              description=(
                  "OpenAI-compatible chat completion. Chargeable and answered "
                  "in the same request (execution mode SYNC_BILLED). Requires "
                  "an Idempotency-Key header. Credit is held at a ceiling "
                  "before the model runs and settled from measured tokens."))
    def chat_completions(
        request: Request,
        body: dict = Body(...),
        idempotency_key: str = Header(default="", alias="Idempotency-Key"),
        principal: Principal = Depends(require_scope(SCOPE_JOBS_CREATE)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        from platform_core.llm import ngat, phong_cho, thanh_toan
        from platform_core.runtime_noi_bo import luong as cua_luong

        # Ngân sách thời gian của cửa được tính từ ĐÂY: mọi giây tiêu ở khâu
        # kiểm là một giây lượt gọi model không còn (xem `han_cho_dong_bo`).
        t0 = time.monotonic()

        # ⭐ THÔNG BÁO LỖI LÀ TÀI LIỆU, VÀ LÀ TRANG TÀI LIỆU DUY NHẤT CHẮC CHẮN
        #    ĐƯỢC ĐỌC. Đo thật 23/08 với `openai` 2.30.0: một lượt gọi đúng theo
        #    tài liệu OpenAI **trả 400 ở đây**, vì SDK của OpenAI tự sinh một
        #    khoá idempotency cho mỗi POST nhưng chỉ **gửi** nó khi
        #    `_idempotency_header` được đặt — mà với client OpenAI thì nó là
        #    `None`. Khoá được sinh ra rồi vứt đi.
        #
        #    Câu "endpoint này cần header X" đúng nhưng vô dụng: người đọc đang
        #    dùng SDK và không biết chèn header vào đâu. Nên nói luôn chỗ chèn.
        if not str(idempotency_key or "").strip():
            raise invalid_request(
                "This endpoint requires an Idempotency-Key header, one per "
                "call. The OpenAI SDK does not send it for you: pass "
                'extra_headers={"Idempotency-Key": uuid.uuid4().hex} on the '
                "Python call, or { headers: { \"Idempotency-Key\": "
                "randomUUID() } } as the second argument in TypeScript. Do not "
                "put it in the client's default headers — one key shared by "
                "every call replays the first answer instead of running a new "
                "one.")
        key = idempotency.require_key(idempotency_key)
        payload = dict(body or {})

        # `text.chat` phải qua đủ ba cổng của Q92. Có route riêng KHÔNG cho nó
        # bỏ qua công tắc người vận hành — cửa mới không được là cửa sau.
        tool = require_tool(build_catalog(config), TOOL_CHAT, principal)
        executor = for_tool(tool)

        if payload.pop("stream", False):
            # ⭐ CẬP NHẬT 23/08 (Q107): streaming nay CÓ, chỉ là không ở route
            #    này. Cửa này trả một cục JSON; chỗ streaming là
            #    `/api/v1/messages` (Anthropic) và `/api/v1/responses` (OpenAI
            #    Responses). Nhận `stream: true` rồi trả một cục là nói dối SDK —
            #    nó đang chờ `text/event-stream` và sẽ vỡ ở chỗ khó lần hơn nhiều.
            raise invalid_request(
                "This endpoint returns a single JSON answer. For a stream use "
                "POST /api/v1/messages (Anthropic Messages) or "
                "POST /api/v1/responses (OpenAI Responses) — those are what "
                "Claude Code, Claude Desktop and Codex speak.")

        # Kiểm THAM SỐ trước khi tiền chuyển — cùng câu `jobs.py` đã viết:
        # "a typo must never reach the ledger".
        if "max_tokens" not in payload:
            payload["max_tokens"] = executor.mac_dinh_cho("sync")
        # Tên model TRƯỚC hình dạng: một tên đã cắt phải nghe "model không còn",
        # không phải "yêu cầu sai hình dạng" (D02, Step 2c).
        kiem_ten_model(tool, payload.get("model"))
        try:
            sach = executor.validate(payload)
        except executor.parameter_error as e:
            raise invalid_request(str(e)) from None

        token_vao_uoc = executor.estimate_input(sach["messages"], sach.get("tools"))

        # 🔴 413 TRƯỚC MỌI THỨ KHÁC (spec §6). Quá trần vào của model là chuyện
        #    của **yêu cầu**, không của năng lực — nó sẽ quá dài kể cả khi máy B
        #    rảnh hoàn toàn, nên đừng để nó đi vào phòng chờ rồi chờ 60 giây để
        #    nhận một câu trả lời đã biết trước. Và Codex/Claude Code dựa vào
        #    đúng mã 413 để TỰ NÉN hội thoại.
        _tran_vao = getattr(executor, "input_cap", None)
        if _tran_vao is not None:
            _cap = int(_tran_vao(sach["model"]))
            if token_vao_uoc > _cap:
                # R-08: khuôn OpenAI `context_length_exceeded` + câu "prompt is
                # too long" (`su_kien_loi` — một chỗ dựng cho mọi cửa).
                return su_kien_loi.loi_qua_dai_json(
                    "/v1/chat/completions", token=int(token_vao_uoc), tran=_cap,
                    request=request)

        # ⛔ SAU 413, khong truoc. Mot tran ra thap den muc chac chan tra ve
        #    RONG cung la mot yeu cau hong, nhung no la hong ve NGAN SACH — con
        #    413 la hong ve DO DAI, va Codex/Claude Code dua vao dung ma 413 de
        #    tu nen hoi thoai. Yeu cau vi pham ca hai phai nghe 413 truoc: loi
        #    khuyen "nang max_tokens" vo nghia voi mot hoi thoai du sao cung
        #    qua dai. `features.kiem_san_token_ra` giu ly do day du.
        _san_ra = getattr(executor, "check_output_floor", None)
        if _san_ra is not None:
            try:
                _san_ra(sach)
            except executor.parameter_error as e:
                raise invalid_request(str(e)) from None

        # ── Sức chứa admission CỦA ĐÚNG MODEL NÀY (multijob 2.2) ─────────────
        #
        # 🔴 Giải Ở ĐÂY, trước `idempotency.begin`, và đây là một phép ĐỌC
        #    thuần — không giữ suất, không chạm tiền, nên thứ tự tiền của D04
        #    (413 → 402 → `begin` → `commit` → chờ → giữ tiền → gọi → quyết
        #    toán) không đổi một bước nào. Giải sau `begin` thì một bản khai
        #    lệch sẽ để lại một bản ghi idempotency treo phải đi mở lại.
        #
        # ⛔ Sau 413. Quá trần vào là chuyện của **yêu cầu** và Codex/Claude Code
        #    dựa vào đúng mã 413 để tự nén hội thoại; chen một lỗi khác lên trước
        #    nó là lấy mất đường tự chữa của client.
        try:
            suc = tool.admission_cho(sach["model"])
        except KeyError as e:
            # Bản khai của app nói tool này không phục vụ model ấy. KHÔNG phải
            # 500: ta biết chính xác chuyện gì xảy ra và nói được ra.
            # ⭐ CÙNG MỘT CÂU với tên đã cắt (`kiem_ten_model`) — D02, Step 2c.
            #    Trước 2.3 chỗ này nói `invalid_request`, tức khách nhận hai câu
            #    khác nhau cho cùng một sự thật "model này không phục vụ được".
            log.error("ban khai admission thieu model %r: %s", sach["model"], e)
            raise model_not_found(
                f"`model` {sach['model']!r} is not served here. Call "
                f"GET /api/v1/models for the names in service."
            ) from None

        tran = _tran_max_tokens(token_vao_uoc, executor)
        if sach["max_tokens"] > tran:
            raise invalid_request(
                f"This synchronous request is estimated at {token_vao_uoc} input "
                f"tokens, leaving room for at most {tran} output tokens inside "
                f"its {SYNC_BILLED_MAX_SECONDS}s budget. Reduce the prompt or "
                f"max_tokens, use a streaming endpoint, or submit it to "
                f"POST /api/v1/jobs.")

        # Suy nghĩ do máy chủ quyết (L-26). Model một chế độ (3.5): budget suy
        # nghĩ của lượt đặt theo `max_tokens` đã qua trần thời gian, chừa chỗ
        # trả lời — budget khách gửi đã bị gỡ trong `validate`.
        _budget_fn = getattr(executor, "sync_thinking_budget", None)
        budget_suy_nghi = _budget_fn(sach) if callable(_budget_fn) else None
        _, effort_bo_qua = cua_luong.chuan_hoa_suy_nghi(payload, sach["model"])

        def _gan(tra: JSONResponse) -> JSONResponse:
            if effort_bo_qua:
                tra.headers[HEADER_EFFORT_BO_QUA] = "1"
            return tra

        # 🔴 402 TRƯỚC `idempotency.begin` (spec §6). Chỉ ĐỌC số dư — không giữ
        #    đồng nào ở đây, vì lượt này còn có thể phải chờ, và giữ tiền của
        #    một lượt đang chờ là đúng thứ INV-MJ-1 cấm.
        if not sandbox.is_test(principal.mode) and not thanh_toan.du_so_du(
                db, user_id=principal.user_id, token_vao_uoc=token_vao_uoc,
                max_tokens=sach["max_tokens"], model=sach["model"]):
            metrics.increment(metrics.CREDIT_EXHAUSTED)
            raise insufficient_credit(
                THIEU_CREDIT_LOI)

        request_hash = idempotency.canonical_hash({"tool": TOOL_CHAT, "input": sach})
        record, replay = idempotency.begin(
            db, key_id=principal.key_id, user_id=principal.user_id,
            operation=OPERATION_CHAT, key=key, request_hash=request_hash)
        if replay:
            # Cùng khoá, cùng yêu cầu: trả lại đúng câu trả lời đầu tiên. Không
            # giữ chỗ lần hai, không gọi model lần hai — đó là toàn bộ lý do
            # header này tồn tại, và ở đây nó còn quan trọng hơn ở cửa job vì
            # không có quote nào để đối chiếu.
            metrics.increment(metrics.IDEMPOTENCY_REPLAY)
            return _gan(JSONResponse(
                record.response, status_code=200,
                headers={**_NO_STORE, "Idempotency-Replayed": "true"}))

        resolved = policy.resolve(db, config=config, principal=principal,
                                  tool_name=TOOL_CHAT)
        limits.enforce_create_rate(key_id=principal.key_id, config=config,
                                   limits=resolved, user_id=principal.user_id)

        # ── Chế độ thử: không chạm GPU, không chạm sổ tiền ───────────────────
        # ⛔ ĐỪNG BỎ NHÁNH NÀY. Ở cửa job, một lượt thử vẫn chạy thật vì nó xếp
        #    hàng và chịu mọi hạn mức. Ở đây nó sẽ chiếm GPU ngay lập tức mà
        #    không ai trả tiền — tức là một cách miễn phí để giữ card.
        if sandbox.is_test(principal.mode):
            tra_ve = _dang_openai(sach, noi_dung="[test mode] no model was called.",
                                  token_vao=0, token_ra=0, thu_credit=0,
                                  da_do_duoc=True, che_do_thu=True)
            idempotency.complete(db, record, response=tra_ve)
            db.commit()
            return _gan(JSONResponse(tra_ve, status_code=200, headers=_NO_STORE))

        # ⛔ KHONG `f"chat:{record.id}"`: 5 + 36 = 41 ky tu, vuot VARCHAR(36)
        #    cua `credit_entries.job_id`. PostgreSQL ep, SQLite khong — nen loi
        #    nay chay sach qua ca bo test roi no o luot goi that dau tien.
        request_id = thanh_toan.ma_luot("ch")

        # 🔴 CHỐT GIAO DỊCH TRƯỚC KHI CHỜ, VÀ TRƯỚC KHI GỌI MODEL (D04).
        #
        #   1. **Khoá idempotency.** `idempotency.begin` lấy
        #      `pg_advisory_xact_lock`, và khoá đó sống hết giao dịch. Để giao
        #      dịch trùm lên cả lúc chờ + lượt gọi model thì một yêu cầu trùng
        #      khoá **treo theo** thay vì nhận ngay câu trả lời đúng ("đang xử
        #      lý"). D04 dời điểm chờ xuống **sau** dòng này chính vì thế.
        #   2. **Kết nối CSDL bị giữ suốt lượt gọi.** Pool có N kết nối; N lượt
        #      chat đồng thời là hết pool, và thứ chết trước là **những trang
        #      không liên quan gì** — trang đăng nhập, trang nạp tiền.
        #   3. **Tiến trình chết giữa chừng thì mất cả hai.** Cuộn ngược xoá bản
        #      ghi idempotency, nên lần thử lại chạy lại từ đầu và đốt GPU lần
        #      nữa. Chốt lại thì khoá vẫn giữ lời hứa của nó.
        #
        # ⛔ Từ dòng này trở xuống, **mọi đường ra phải tự chốt giao dịch của nó.**
        db.commit()

        # ── Phòng chờ (D04) — CHƯA giữ đồng nào ──────────────────────────────
        try:
            suat = cua_luong.cho_suat_dong_bo(
                suc=suc,
                user_id=principal.user_id, request_id=request_id, cua="sync",
                token_vao_uoc=int(token_vao_uoc), xin_ra=int(sach["max_tokens"]),
                han_s=cua_luong.han_cho_dong_bo(
                    ngan_sach_s=float(SYNC_BILLED_MAX_SECONDS),
                    da_tieu_s=time.monotonic() - t0),
                # Id model **nội bộ** cho sổ lượt (dual-model 6.3). ⛔ Không ghi
                # bí danh khách: bí danh đổi được mà engine không đổi.
                model=cua_luong.id_model_noi_bo(executor, sach["model"]),
                ngat_chua=ngat.do_ngat(request))
        except phong_cho.HetCho as e:
            # Hết trần chờ: 0 khoản giữ (INV-MJ-2), và **mở lại khoá** — bảo
            # khách thử lại bằng `Retry-After` rồi trả 409 cho lượt thử lại là
            # một lời khuyên không thực hiện được.
            metrics.increment(metrics.CAPACITY_REFUSED)
            _mo_lai_khoa(record, "het_cho:" + str(e.ly_do))
            log.warning("HET CHO dong bo user=%s ly_do=%s",
                        principal.user_id[:8], e.ly_do)
            # ⛔ `reason` — cung ly le voi cua stream: `het_cho` (hang cho cua
            #    TA day) khac han `suat` (GPU het suat) va `thuong_nguon` (may B
            #    tra 429). Cung mot ma HTTP, ba nguyen nhan, ba cach xu.
            raise limits.execution_busy((suc.resource if suc else ""),
                                        retry_after=_THU_LAI_S,
                                        reason="het_cho") from None
        except phong_cho.KhachDi:
            _mo_lai_khoa(record, "khach_di_luc_cho")
            return JSONResponse(_KHACH_NGAT, status_code=MA_KHACH_NGAT,
                                headers=_NO_STORE)
        except cua_luong.KhongMoDuoc as e:
            # Đặt chỗ (vào + ra + đệm + ảnh) vượt cả pool KV — phương án C bất
            # biến 1, không còn kẹp im lặng. Quá dài với model: 400
            # `context_length_exceeded` (R-08), 0 khoản giữ, mở khoá cho lượt đã
            # rút gọn.
            _mo_lai_khoa(record, "qua_dai")
            return su_kien_loi.loi_qua_dai_json(
                "/v1/chat/completions", token=e.token,
                tran=(e.tran if e.tran is not None
                      else int(suc.token_pool if suc else 0)),
                request=request)

        # ── Được nhận ⇒ GIỮ TIỀN (và chỉ từ đây trở đi) ─────────────────────
        try:
            da_giu = thanh_toan.giu_cho_luot(
                db, user_id=principal.user_id, request_id=request_id,
                token_vao_uoc=token_vao_uoc, max_tokens=sach["max_tokens"],
                model=sach["model"])
            db.commit()
        except credit.ThieuCreditError as e:
            # Số dư tụt giữa lúc tiền kiểm và lúc được nhận (khách chạy song song).
            #
            # ⭐ Đếm nó: một khách hết credit là người **muốn dùng mà không dùng
            #    được**. Không đếm thì ta chỉ biết chuyện đó khi họ chịu khó viết
            #    thư — mà phần lớn thì không, họ đi chỗ khác.
            metrics.increment(metrics.CREDIT_EXHAUSTED)
            log.info("khach het credit tai chat/completions: user=%s",
                     principal.user_id[:8])
            db.rollback()
            _nha(suat, "thieu_credit")
            raise insufficient_credit(
                THIEU_CREDIT_LOI, **thieu_credit_chi_tiet(e)) from None
        except BaseException:
            db.rollback()
            _nha(suat, "loi")
            raise

        try:
            # `giu_suat_dong_bo`, không `keep_alive(suat.lease_id)`: máy B 429 ⇒
            # xếp lại ⇒ suất MỚI, và đường nhả phải nhả suất ĐANG giữ.
            with cua_luong.giu_suat_dong_bo(suat):
                return _gan(_finish_chat(
                    db=db, sach=sach, principal=principal, record=record,
                    request_id=request_id, da_giu=da_giu, executor=executor,
                    trang_thai=request.state, request=request,
                    bat_dau_cua=t0, waiter_id=suat.waiter_id, suat=suat,
                    budget_suy_nghi=budget_suy_nghi))
        finally:
            # ⛔ LƯỚI, KHÔNG PHẢI KẾT CỤC. Bản đầu ghi thẳng `"xong"` ở đây —
            #    tức **mọi** đường ra, kể cả lỗi và khách ngắt, vào sổ 30 ngày
            #    dưới một chữ. Một cuốn sổ chỉ biết nói "xong" không phân tích
            #    được gì, mà nó tồn tại chính để phân tích.
            #    `_finish_chat` chốt kết cục thật ở từng nhánh; `ghi_ket_thuc`
            #    chỉ ăn khi dòng còn `nhan`, nên dòng dưới đây chỉ chạy khi
            #    KHÔNG nhánh nào kịp chốt (thoát bất thường).
            if suat.waiter_id:
                phong_cho.ghi_ket_thuc(suat.waiter_id, "loi")


def _mo_lai_khoa(record, ly_do: str) -> None:
    """Đóng bản ghi idempotency ở trạng thái **thử lại được**, phiên mới.

    ⚠️ Phiên của request đã commit và có thể đã được dùng tiếp; mở một phiên
       riêng để việc này không kéo theo bất cứ thứ gì khác vào cùng giao dịch.
    """
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        row = db.get(type(record), record.id)
        if row is not None:
            idempotency.mo_lai(db, row, ly_do=ly_do)
            db.commit()
    except Exception:  # noqa: BLE001 - khong duoc lam hong duong tra loi
        db.rollback()
        log.exception("khong mo lai duoc khoa idempotency %s", record.id[:8])
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _con_lai_s(bat_dau_cua: float, ngan_sach_s: float, san_s: float = 1.0) -> float:
    """Ngân sách thời gian CÒN LẠI cho lời gọi model, tính từ lúc vào cửa.

    🔴 ĐỒNG HỒ PHẢI BẮT ĐẦU TRƯỚC PHÒNG CHỜ. Bản đầu của tôi đặt mốc **sau** khi
       chờ xong, nên phép trừ này luôn ra gần đúng 90 và không kẹp gì cả: một
       lượt chờ 60 giây rồi chạy thêm 90 giây là 150 giây — đúng kịch bản 524
       của Cloudflare mà `han_cho_dong_bo` sinh ra để chặn. Hai hàm phải đo
       **cùng một cái đồng hồ**, nếu không chúng chia nhau một ngân sách tưởng
       tượng.

    ⚠️ Sàn `san_s`: hết sạch ngân sách thì vẫn gửi đi với một giây, để lỗi là
       một cái timeout đọc được chứ không phải một số âm ném từ `httpx`.
    """
    return max(float(san_s), float(ngan_sach_s) - (time.monotonic() - float(bat_dau_cua)))


def _nha(suat, ket_qua: str) -> None:
    """Nhả suất + chốt dòng chờ. Idempotent, và không bao giờ ném."""
    from platform_core.llm import admission, phong_cho

    try:
        if getattr(suat, "lease_id", ""):
            admission.release_by_id(suat.lease_id)
    except Exception:  # noqa: BLE001 - ORPHAN_TIMEOUT la luoi cuoi
        log.exception("khong nha duoc suat cua cua dong bo")
    if getattr(suat, "waiter_id", ""):
        phong_cho.ghi_ket_thuc(suat.waiter_id, ket_qua)


def _finish_chat(*, db, sach: dict, principal, record, request_id: str,
                 trang_thai=None, request=None, bat_dau_cua: float = 0.0,
                 waiter_id: str = "", suat=None,
                 da_giu: int, executor=None,
                 budget_suy_nghi: int | None = None) -> JSONResponse:
    """Chạy model và định đoạt tiền; caller giữ execution lease bằng finally.

    `bat_dau_cua` là `time.monotonic()` lúc **request vào cửa**, không phải lúc
    vào hàm này — xem `_con_lai_s`.
    `waiter_id`: mỗi đường ra tự ghi KẾT CỤC THẬT vào sổ lượt. `ghi_ket_thuc`
    chỉ ăn khi dòng còn ở trạng thái `nhan`, nên lời ghi ĐẦU TIÊN thắng và lưới
    "loi" của bên gọi là no-op khi ở đây đã chốt đúng.
    """
    from platform_core.llm import ngat, phong_cho, thanh_toan
    from platform_core.llm.cong_vlm import (BanError, CongVlmError, HuyError,
                                            SuDung, VuotNganSachError,
                                            YeuCauSaiError)

    bat_dau = time.monotonic()
    try:
        executor = executor or for_tool_name(TOOL_CHAT)
        # ⭐ Spec §16: thăm `is_disconnected` ~1 s **song song** với lời gọi.
        #    Khách đi giữa chừng mà ta không biết là một lượt GPU chạy trọn cho
        #    một người đã đóng cửa sổ — và ở cửa đồng bộ thì không có byte nào
        #    chảy để phát hiện chuyện ấy sớm hơn.
        # ⭐ Máy B 429 cho lượt đã nhận ⇒ xếp lại trong phần còn lại của ngân sách
        #    cửa (phương án C bước 1); mỗi lần gọi mang `X-LTT-Token-Dat` (O-05).
        from platform_core.runtime_noi_bo import luong as cua_luong

        def _goi():
            return ngat.chay_canh_ngat(
                lambda: executor.run(
                    db, sach,
                    timeout_s=_con_lai_s(bat_dau_cua or bat_dau,
                                         float(SYNC_BILLED_MAX_SECONDS)),
                    # 🔴 TRUYỀN MÃ LƯỢT (L-06). Không có nó, đường hủy chỉ đóng
                    #    socket — và `httpx.Client.close()` không cắt một
                    #    request đang bay ở luồng khác. Máy B sinh chữ tới hết,
                    #    ta chờ tới hết, slot bị giữ 15–32 s, khách vẫn bị tính
                    #    tiền.
                    ma_luot=request_id,
                    **({"budget_suy_nghi": budget_suy_nghi}
                       if budget_suy_nghi is not None else {})),
                ngat_chua=ngat.do_ngat(request))

        kq = cua_luong.goi_dong_bo_co_xep_lai(
            _goi, suat,
            han_s=lambda: cua_luong.han_cho_dong_bo(
                ngan_sach_s=float(SYNC_BILLED_MAX_SECONDS),
                da_tieu_s=time.monotonic() - (bat_dau_cua or bat_dau)),
            ngat_chua=ngat.do_ngat(request))
    except ngat.KhachNgat as e:
        # 🔴 HAI KẾT CỤC KHÁC HẲN NHAU, VÀ CHÚNG ĐỊNH ĐOẠT KHOÁ IDEMPOTENCY
        #    THEO HAI CHIỀU NGƯỢC NHAU.
        #
        #    Lời gọi **kịp về** ⇒ model đã chạy, tiền đã thu theo `usage` đo
        #    được. Mở lại khoá ở đây là mời lượt thử lại chạy model **lần hai**
        #    và thu **lần hai** — đúng thứ INV-011/012 và chính chú thích ⛔ của
        #    `idempotency.mo_lai` cấm. Nên: `complete` với câu trả lời. Khách
        #    thử lại cùng khoá sẽ **replay** đúng câu ấy, miễn phí.
        #
        #    Lời gọi **chưa về** ⇒ hoàn trọn, không thu gì ⇒ mới được mở khoá.
        if e.ket_qua is not None:
            thu = thanh_toan.quyet_toan_hoac_hoan(
                db, user_id=principal.user_id, request_id=request_id,
                su_dung=SuDung(token_vao=e.ket_qua.token_vao,
                               token_ra=e.ket_qua.token_ra,
                               token_vao_cache=e.ket_qua.token_vao_cache,
                               dang_tin=e.ket_qua.do_duoc),
                model=sach["model"])
            if trang_thai is not None:
                trang_thai.api_credit_delta = -int(thu.thu_credit)
            tra_ve = _dang_openai(
                sach, noi_dung=e.ket_qua.noi_dung, token_vao=e.ket_qua.token_vao,
                token_ra=e.ket_qua.token_ra, thu_credit=thu.thu_credit,
                da_do_duoc=thu.da_do_duoc,
                token_vao_cache=e.ket_qua.token_vao_cache,
                finish_reason=e.ket_qua.finish_reason,
                tool_calls=list(e.ket_qua.tool_calls), da_giu=da_giu,
                giay=round(time.monotonic() - bat_dau, 2))
            idempotency.complete(db, record, response=tra_ve)
            db.commit()
            phong_cho.ghi_ket_thuc(waiter_id, "khach_ngat")
            # Khách đã đi nên không ai đọc thân này; nó tồn tại để sổ request
            # ghi đúng **một lượt đã chạy và đã thu**, không phải một lượt hỏng.
            return JSONResponse(tra_ve, status_code=MA_KHACH_NGAT,
                                headers=_NO_STORE)
        thanh_toan.hoan_luot(db, user_id=principal.user_id,
                             request_id=request_id)
        db.commit()
        _mo_lai_khoa(record, "khach_ngat")
        phong_cho.ghi_ket_thuc(waiter_id, "khach_ngat")
        return JSONResponse(_KHACH_NGAT, status_code=MA_KHACH_NGAT,
                            headers=_NO_STORE)
    except BanError as e:
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        # Đếm vào `CAPACITY_REFUSED` — lý do đầy đủ ở nhánh bận của
        # `_mot_cuc` trong `server/api/streaming.py`.
        metrics.increment(metrics.CAPACITY_REFUSED)
        log.warning("BAN dong bo: user=%s duong=/chat/completions ly_do=%s",
                    principal.user_id[:8], e)
        # 🔴 KHÔNG nội suy `{e}`. `BanError` mang `detail.chi_tiet` / `ly_do`
        #    của máy B (`platform_core/llm/cong_vlm.py:225`) — mô tả TRẠNG THÁI
        #    BÊN TRONG ta ("3/3 suat dang dung"), thứ khách không hành động
        #    được và không nên đọc. Dòng `log.warning` ngay trên đã giữ nó cho
        #    người trực.
        #
        # ⭐ Cửa ĐỒNG BỘ này bị bỏ sót ở lượt rà đầu: phép quét tìm `ly_do}`
        #    không thấy nó, vì ở đây là `{e}` chứ không `{e.ly_do}`. Chỉ một
        #    phép quét rộng hơn (mọi biểu thức cạnh hàm dựng lỗi HTTP) mới lôi
        #    ra. Ba chỗ rò, không phải hai.
        #
        # ⛔ GIỮ NGUYÊN tiền tố "The model is busy right now" — `test_360` neo
        #    vào đúng chuỗi ấy trên CẢ `chat` lẫn `streaming`. Xem **Bẫy 31**.
        phong_cho.ghi_ket_thuc(waiter_id, "ban")
        raise service_unavailable(
            "The model is busy right now.", retry_after=30) from None
    except VuotNganSachError as e:
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        phong_cho.ghi_ket_thuc(waiter_id, "tham_so_sai")
        # 🔴 NOI RO TRAN NAO, BAO NHIEU, VA KHACH GUI BAO NHIEU.
        #
        #    Do 14/09 tren production: gui 5 anh -> 400 voi detail
        #    "yeu cau vuot tran cua cong". Khach khong sua duoc yeu cau tu mot
        #    cau nhu the — ho khong biet tran la 4, khong biet la tran ANH.
        #
        #    Cong may B da gui san `{truong, tran, thay}`; day la cho dich
        #    chung sang ten cong khai MOT LAN.
        failure = e.failure
        raise invalid_request(
            failure.message if failure is not None else "The request exceeds a model limit.",
            **tran_bi_vuot(failure.as_detail() if failure is not None else e.chi_tiet),
        ) from e
    except YeuCauSaiError as e:
        # 🔴 LOI CUA KHACH, KHONG PHAI CUA MAY. Do duoc 13/09 (L-09): mot anh
        #    hong lam may B tra dung chuan
        #
        #        400 invalid_request_error "Failed to load image or audio file"
        #
        #    nhung may A lam phang thanh 503. Hai cai sai, moi cai mot huong:
        #    khach nhan `retry: after_delay` cho mot yeu cau KHONG BAO GIO thanh
        #    cong, va `danh_dau_loi` phat key nhu mot loi 5xx — nam lan la tat
        #    model nha.
        #
        # Thông điệp công khai lấy từ registry của `ModelFailure`, không lấy
        # `str(e)`: prose thô của thượng nguồn chỉ được giữ trong log nội bộ.
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        phong_cho.ghi_ket_thuc(waiter_id, "tham_so_sai")
        raise invalid_request(
            e.failure.message
            if e.failure is not None
            else "The model rejected this request.",
        ) from e
    except HuyError:
        # ⛔ PHAI dung TRUOC nhanh bat-tat-ca ben duoi. `HuyError` co chu y KHONG
        #    ke thua `CongVlmError`, nen no roi thang vao `except Exception` va
        #    thanh 500 — xem `_DA_HUY`.
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        phong_cho.ghi_ket_thuc(waiter_id, "huy")
        return JSONResponse(_DA_HUY, status_code=MA_KHACH_NGAT,
                            headers=_NO_STORE)
    except (CongVlmError, Exception) as e:                  # noqa: BLE001
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        log.warning("chat.completions that bai user=%s: %s",
                    principal.user_id[:8], e)
        phong_cho.ghi_ket_thuc(waiter_id, "loi")
        raise service_unavailable("The model could not serve this request.") from None
    except BaseException:
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        phong_cho.ghi_ket_thuc(waiter_id, "loi")
        raise

    su_dung = SuDung(token_vao=kq.token_vao, token_ra=kq.token_ra,
                     token_vao_cache=kq.token_vao_cache, dang_tin=kq.do_duoc)
    thu = thanh_toan.quyet_toan_hoac_hoan(
        db, user_id=principal.user_id, request_id=request_id,
        su_dung=su_dung, model=sach["model"])
    # ⛔ P08 F-01: cot `credit_delta` cua so request CHI duoc ghi o cua job, nen
    #    hai cua nay doc ra `+0` bat ke thu bao nhieu — va `anomalies.py` dua vao
    #    no de do bat thuong tien. Mot so 0 co cau truc trong o "da thu bao nhieu"
    #    la thu te hon mot o trong: no doc len nhu mot phep do.
    if trang_thai is not None:
        trang_thai.api_credit_delta = -int(thu.thu_credit)
    tra_ve = _dang_openai(
        sach, noi_dung=kq.noi_dung, token_vao=kq.token_vao,
        token_ra=kq.token_ra, thu_credit=thu.thu_credit,
        da_do_duoc=thu.da_do_duoc, token_vao_cache=kq.token_vao_cache,
        finish_reason=kq.finish_reason, tool_calls=list(kq.tool_calls),
        da_giu=da_giu, giay=round(time.monotonic() - bat_dau, 2))
    idempotency.complete(db, record, response=tra_ve)
    db.commit()
    metrics.increment("chat:completions")
    # T4 P2: token vào sổ lượt; TTFB NULL (không stream, không có byte đầu).
    phong_cho.ghi_ket_thuc(waiter_id, "xong", so_do=phong_cho.SoDo.tu_su_dung(su_dung))
    return JSONResponse(tra_ve, status_code=200, headers=_NO_STORE)


def _dang_openai(sach: dict, *, noi_dung: str, token_vao: int, token_ra: int,
                 thu_credit: int, da_do_duoc: bool, token_vao_cache: int = 0,
                 finish_reason: str = "stop", tool_calls: list | None = None,
                 da_giu: int = 0, giay: float = 0.0,
                 che_do_thu: bool = False) -> dict:
    """Phản hồi hình dạng OpenAI, cộng một khối `x_ltt` cho thứ OpenAI không có.

    ⭐ TIỀN NẰM TRONG `x_ltt`, KHÔNG NHÉT VÀO `usage`. `usage` là hình dạng khách
       đã có mã đọc sẵn; thêm khoá lạ vào đó là mời client nghiêm ngặt vỡ. Tiền là
       thứ **của ta**, nên nó ở chỗ có tiền tố của ta.

    ⭐ `credit_charged` là số THẬT SỰ bị thu, không phải phần đã giữ. Khách nhìn
       thấy hoá đơn ngay trong phản hồi, không phải đợi tới trang usage.
    """
    tin = {"role": "assistant", "content": noi_dung}
    if tool_calls:
        tin["tool_calls"] = tool_calls
    return {
        "object": "chat.completion",
        "model": sach["model"],
        "choices": [{"index": 0, "message": tin, "finish_reason": finish_reason}],
        "usage": {
            "prompt_tokens": token_vao,
            "completion_tokens": token_ra,
            "total_tokens": token_vao + token_ra,
        },
        "x_ltt": {
            "credit_charged": thu_credit,
            "credit_held": da_giu,
            "usage_measured": da_do_duoc,
            "cached_prompt_tokens": token_vao_cache,
            "duration_seconds": giay,
            "test_mode": che_do_thu,
        },
    }
