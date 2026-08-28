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
from platform_core.public_api.errors import (insufficient_credit,
                                             invalid_request,
                                             service_unavailable)
from platform_core.public_api.principal import Principal
from platform_core.public_api.protocol import SYNC_BILLED_MAX_SECONDS
from platform_core.public_api.scopes import SCOPE_JOBS_CREATE
from server.api.auth import require_scope
from server.deps import get_db

log = logging.getLogger("server.api.chat")

_NO_STORE = {"Cache-Control": "no-store"}
OPERATION_CHAT = "chat.completions"

#: Tool đứng sau cửa này. Nó vẫn phải qua đủ ba cổng của Q92 như mọi tool khác —
#: có route riêng **không** làm nó bỏ qua `LTT_PUBLIC_API_TOOLS`.
TOOL_CHAT = "text.chat"


def _tran_max_tokens(token_vao_uoc: int = 0) -> int:
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
    from apps.ltt_llm.features import tran_token_ra_dong_bo

    return tran_token_ra_dong_bo(token_vao_uoc, SYNC_BILLED_MAX_SECONDS)


def register_chat_routes(api, config, tag: str) -> None:
    @api.post("/chat/completions", tags=[tag],
              summary="Chat completion, answered in the request",
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
        from apps.ltt_llm import features
        from platform_core.llm import admission, thanh_toan

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
            payload["max_tokens"] = features.SYNC_MAX_TOKENS_MAC_DINH
        try:
            sach = features.kiem_tham_so(payload)
        except features.ThamSoSai as e:
            raise invalid_request(str(e)) from None

        token_vao_uoc = features.uoc_token_vao(sach["messages"], sach.get("tools"))
        tran = _tran_max_tokens(token_vao_uoc)
        if sach["max_tokens"] > tran:
            raise invalid_request(
                f"This synchronous request is estimated at {token_vao_uoc} input "
                f"tokens, leaving room for at most {tran} output tokens inside "
                f"its {SYNC_BILLED_MAX_SECONDS}s budget. Reduce the prompt or "
                f"max_tokens, use a streaming endpoint, or submit it to "
                f"POST /api/v1/jobs.")

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
            return JSONResponse(record.response, status_code=200,
                                headers={**_NO_STORE, "Idempotency-Replayed": "true"})

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
            return JSONResponse(tra_ve, status_code=200, headers=_NO_STORE)

        # ⛔ KHONG `f"chat:{record.id}"`: 5 + 36 = 41 ky tu, vuot VARCHAR(36)
        #    cua `credit_entries.job_id`. PostgreSQL ep, SQLite khong — nen loi
        #    nay chay sach qua ca bo test roi no o luot goi that dau tien.
        request_id = thanh_toan.ma_luot("ch")
        ticket = admission.acquire(
            db, resource=tool.admission_resource, slots=tool.admission_slots,
            user_id=principal.user_id, mode="sync", holder_id=record.id)
        if ticket is None:
            db.rollback()
            raise limits.execution_busy(tool.admission_resource)
        try:
            da_giu = thanh_toan.giu_cho_luot(
                db, user_id=principal.user_id, request_id=request_id,
                token_vao_uoc=token_vao_uoc, max_tokens=sach["max_tokens"])
        except credit.ThieuCreditError as e:
            # Không đủ tiền thì không đốt GPU. Chốt đúng chỗ, và trước GPU.
            #
            # ⭐ Đếm nó: một khách hết credit là người **muốn dùng mà không dùng
            #    được**. Không đếm thì ta chỉ biết chuyện đó khi họ chịu khó viết
            #    thư — mà phần lớn thì không, họ đi chỗ khác.
            metrics.increment(metrics.CREDIT_EXHAUSTED)
            log.info("khach het credit tai chat/completions: user=%s",
                     principal.user_id[:8])
            db.rollback()
            raise insufficient_credit(str(e)) from None

        # 🔴 CHỐT GIAO DỊCH TRƯỚC KHI GỌI MODEL. Ba thứ hỏng nếu không:
        #
        #   1. **Khoá idempotency giữ suốt 90 giây.** `idempotency.begin` lấy
        #      `pg_advisory_xact_lock`, và khoá đó sống hết giao dịch. Để giao
        #      dịch trùm lên cả lượt gọi model thì một yêu cầu trùng khoá sẽ
        #      **treo 90 giây** thay vì nhận ngay câu trả lời đúng ("đang xử lý").
        #   2. **Kết nối CSDL bị giữ suốt lượt gọi.** Pool có N kết nối; N lượt
        #      chat đồng thời là hết pool, và thứ chết trước là **những trang
        #      không liên quan gì** — trang đăng nhập, trang nạp tiền.
        #   3. **Tiến trình chết giữa chừng thì mất cả hai.** Cuộn ngược xoá phần
        #      giữ chỗ (nghe có vẻ an toàn) **và** xoá luôn bản ghi idempotency —
        #      nên lần thử lại chạy lại từ đầu và đốt GPU lần nữa. Chốt lại thì
        #      phần giữ chỗ còn đó để đối soát, và khoá vẫn giữ lời hứa của nó.
        #
        # ⛔ Từ dòng này trở xuống, **mọi đường ra phải tự chốt giao dịch của nó.**
        #    Không còn một giao dịch bao trùm nào để dựa vào nữa.
        db.commit()
        with admission.keep_alive(ticket.id):
            return _finish_chat(
                db=db, sach=sach, principal=principal, record=record,
                request_id=request_id, da_giu=da_giu)


def _finish_chat(*, db, sach: dict, principal, record, request_id: str,
                 da_giu: int) -> JSONResponse:
    """Chạy model và định đoạt tiền; caller giữ execution lease bằng finally."""
    from apps.ltt_llm import features
    from platform_core.llm import thanh_toan
    from platform_core.llm.cong_vlm import (BanError, CongVlmError, SuDung,
                                            VuotNganSachError)

    bat_dau = time.monotonic()
    try:
        kq = features.chay(db, sach, timeout_s=float(SYNC_BILLED_MAX_SECONDS))
    except BanError as e:
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        raise service_unavailable(
            f"The model is busy right now: {e}", retry_after=30) from None
    except VuotNganSachError as e:
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        raise invalid_request(str(e)) from None
    except (CongVlmError, Exception) as e:                  # noqa: BLE001
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        log.warning("chat.completions that bai user=%s: %s",
                    principal.user_id[:8], e)
        raise service_unavailable("The model could not serve this request.") from None
    except BaseException:
        thanh_toan.hoan_luot(db, user_id=principal.user_id, request_id=request_id)
        db.commit()
        raise

    thu = thanh_toan.quyet_toan_hoac_hoan(
        db, user_id=principal.user_id, request_id=request_id,
        su_dung=SuDung(token_vao=kq.token_vao, token_ra=kq.token_ra,
                       token_vao_cache=kq.token_vao_cache,
                       dang_tin=kq.do_duoc))
    tra_ve = _dang_openai(
        sach, noi_dung=kq.noi_dung, token_vao=kq.token_vao,
        token_ra=kq.token_ra, thu_credit=thu.thu_credit,
        da_do_duoc=thu.da_do_duoc, token_vao_cache=kq.token_vao_cache,
        finish_reason=kq.finish_reason, tool_calls=list(kq.tool_calls),
        da_giu=da_giu, giay=round(time.monotonic() - bat_dau, 2))
    idempotency.complete(db, record, response=tra_ve)
    db.commit()
    metrics.increment("chat:completions")
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
