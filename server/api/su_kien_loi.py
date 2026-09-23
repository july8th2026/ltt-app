"""su_kien_loi.py — MỘT chỗ dựng lỗi đúng khuôn giao thức: sự kiện SSE (sau 200),
thân HTTP "quá dài" (trước 200), và nhịp chờ của từng cửa. (multijob D-06, R-08)

⭐ VÌ SAO CÓ TỆP NÀY: cửa stream nay gửi 200 + mở SSE TRƯỚC khi được nhận vào máy B
   (chờ trong phòng chờ, có nhịp tim). Sau 200 thì không còn mã HTTP — mọi kết cục
   xấu (hết trần chờ, số dư tụt giữa chừng, máy B bận/hỏng) phải thành một SỰ KIỆN
   mà client của ĐÚNG giao thức đó hiểu.

⛔ Không nhét lý do thô của máy B vào thông điệp (bài học `streaming.py:659-667`:
   thân 429 của máy B mang dung lượng VRAM còn lại). Thông điệp ở đây là câu cố định.

## 🔴 "Quá dài" — client nhận ra bằng CÂU CHỮ và KHUÔN, không bằng mã 413 (R-08)

Tra nguồn client thật 18/09/2026 (`tests/test_1480`):

  * Claude Code 2.1.274 (`claude.exe`): lỗi là "prompt too long" khi thông điệp
    chứa ``prompt is too long`` — bất kể mã HTTP — và rút số bằng
    ``/prompt is too long[^0-9]*(\\d+)\\s*tokens?\\s*>\\s*(\\d+)/i``. Đúng câu của
    API Anthropic: ``prompt is too long: N tokens > M maximum``, HTTP 400.
  * Codex CLI (`codex-rs/codex-api/src/sse/responses.rs`, `api_bridge.rs`): CHỈ
    SSE ``response.failed`` + ``error.code == "context_length_exceeded"`` thành
    `ContextWindowExceeded` (⇒ tự nén). HTTP 400/413 thành lỗi chết lượt.

⇒ Trước bản này cả ba cửa trả ``413 problem+json`` với câu "exceeds the model's
  context limit" — không client nào trong hai nhận ra, nên không client nào nén.

## Một renderer duy nhất (Task 13, 22/09/2026)

Cờ ``LTT_PUBLIC_API_STRUCTURED_MODEL_ERRORS`` và renderer cũ (mã nội bộ
``overloaded``/``context_length``/``upstream`` + câu tự do) đã gỡ: mọi lỗi model
đi `render_model_failure` từ một `ModelFailure`. Tín hiệu tự nén ở trên là BẤT
BIẾN của renderer này, không phải của một nhánh riêng: mã quá dài
(`is_context_limit`) luôn mang câu ``prompt is too long: N tokens > M maximum``,
Responses stream trước 200 là 200 + đúng MỘT ``response.failed`` với
``context_length_exceeded``, và thân HTTP giữ ``limit_name``/``limit_value``
(`tests/test_1480`).
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Callable, Literal, Optional, overload

from dataclasses import replace

from starlette.responses import JSONResponse, Response, StreamingResponse

from llm_gateway.error_contract import error_spec
from platform_core.llm.model_failure import (ModelFailure, model_failure,
                                             observe_model_failure)
from platform_core.public_api import errors as api_errors

# canonical_code -> (Anthropic error.type, OpenAI-compatible error.code)
_MODEL_PROTOCOL = {
    "invalid_request": ("invalid_request_error", "invalid_request"),
    "unsupported_parameter": ("invalid_request_error", "unsupported_parameter"),
    "unsupported_modality": ("invalid_request_error", "unsupported_modality"),
    "model_not_found": ("not_found_error", "model_not_found"),
    "model_loading": ("overloaded_error", "server_is_overloaded"),
    "request_body_too_large": ("request_too_large", "request_too_large"),
    "image_count_exceeded": ("invalid_request_error", "image_count_exceeded"),
    "image_too_large": ("invalid_request_error", "image_too_large"),
    "image_url_not_allowed": ("invalid_request_error", "image_url_not_allowed"),
    "image_decode_failed": ("invalid_request_error", "image_decode_failed"),
    "input_tokens_exceeded": ("invalid_request_error", "context_length_exceeded"),
    "max_output_tokens_exceeded": (
        "invalid_request_error",
        "max_output_tokens_exceeded",
    ),
    "context_window_exceeded": ("invalid_request_error", "context_length_exceeded"),
    "tool_call_parse_failed": ("api_error", "tool_call_parse_failed"),
    "structured_output_failed": ("api_error", "structured_output_failed"),
    "unauthorized": ("authentication_error", "invalid_api_key"),
    "forbidden": ("permission_error", "forbidden"),
    "insufficient_credit": ("invalid_request_error", "insufficient_quota"),
    "quota_exceeded": ("rate_limit_error", "rate_limit_exceeded"),
    "rate_limited": ("rate_limit_error", "rate_limit_exceeded"),
    "concurrency_limited": ("rate_limit_error", "rate_limit_exceeded"),
    "provider_overloaded": ("overloaded_error", "server_is_overloaded"),
    "upstream_timeout": ("api_error", "timeout"),
    "upstream_unreachable": ("api_error", "upstream_unreachable"),
    "provider_oom": ("api_error", "server_error"),
    "request_cancelled": ("api_error", "request_cancelled"),
    "stream_idle_timeout": ("api_error", "timeout"),
    "stream_truncated": ("api_error", "stream_truncated"),
    "malformed_upstream_response": ("api_error", "malformed_upstream_response"),
    "empty_response": ("api_error", "empty_response"),
    "upstream_protocol_error": ("api_error", "upstream_protocol_error"),
    "internal_error": ("api_error", "server_error"),
    "upstream_unknown": ("api_error", "upstream_unknown"),
}


#: Mã mà Anthropic stream SAU 200 phải mang `overloaded_error` để Claude Code
#: TỰ THỬ LẠI. Sau 200 không còn status: Claude Code 2.1.275 (`claude.exe`, hàm
#: quyết định retry) chỉ retry lỗi không-status khi thông điệp chứa
#: ``"type":"overloaded_error"``, còn ``if(!e.status)return!1`` với mọi kiểu khác
#: — `rate_limit_error` giữa luồng là lỗi chết lượt. Bận/hết giờ là tạm thời ⇒
#: phải retry được (`test_272`, `test_1534`). `ltt_error.canonical_code` giữ
#: nguyên nghĩa. Codex KHÔNG cần ngoại lệ này: `response.failed` với
#: `rate_limit_exceeded` ⇒ `RateLimitExceeded`, `timeout` ⇒ `Retryable`, còn
#: `server_is_overloaded` ⇒ `ServerOverloaded` KHÔNG retry
#: (openai/codex@286d4ec `codex-api/src/sse/responses.rs` nhánh
#: "response.failed", `api_bridge_tests.rs`
#: `map_api_error_distinguishes_capacity_from_slow_down`).
_ANTHROPIC_SAU_200_QUA_TAI = frozenset({
    "concurrency_limited", "provider_overloaded", "model_loading",
    "upstream_timeout", "stream_idle_timeout",
})


def model_protocol_code(path: str, canonical_code: str, *,
                        phase: str = "before_headers") -> str:
    """Mã giao thức công khai từ cùng bảng renderer, không sao chép mapping."""
    if not (path.endswith("/messages") or path.endswith("/responses")
            or path.endswith("/chat/completions")):
        return canonical_code
    anthropic, openai = _MODEL_PROTOCOL[canonical_code]
    if path.endswith("/messages"):
        if phase == "after_headers" and canonical_code in _ANTHROPIC_SAU_200_QUA_TAI:
            return "overloaded_error"
        return anthropic
    return openai


def render_local_model_failure(
    path: str,
    canonical_code: str,
    *,
    request_id: str,
) -> Response:
    """Render a model error found by A before any request reaches B."""
    spec = error_spec(canonical_code)
    failure = model_failure(
        canonical_code,
        http_status=spec.status,
        request_id=request_id,
    )
    protocol = (
        "messages" if path.endswith("/messages")
        else "responses" if path.endswith("/responses")
        else "chat" if path.endswith("/chat/completions")
        else "rfc9457"
    )
    observe_model_failure(
        failure,
        gateway_code=canonical_code,
        protocol_code=model_protocol_code(path, canonical_code),
        protocol=protocol,
        stream_phase="before_headers",
        endpoint=protocol if protocol != "rfc9457" else "public_api",
        action="terminal",
        model_known=False,
    )
    return render_model_failure(
        path,
        failure,
        phase="before_headers",
        stream=False,
    )

#: Tiền tố Claude Code dò (xem docstring tệp). ⛔ Đừng dịch, đừng viết hoa lại.
CAU_QUA_DAI = "prompt is too long"


def cau_qua_dai(token: Optional[int] = None, tran: Optional[int] = None) -> str:
    """Câu "quá dài" DUY NHẤT: đúng chữ API Anthropic, có số khi biết số."""
    if token is not None and tran is not None:
        return (f"{CAU_QUA_DAI}: {int(token)} tokens > {int(tran)} maximum. "
                f"The input exceeds this model's context window; compact or drop "
                f"older turns and retry.")
    return (f"{CAU_QUA_DAI}: the input exceeds this model's context window; "
            f"compact or drop older turns and retry.")


def _id_response() -> str:
    return "resp_ltt_" + uuid.uuid4().hex[:24]


def _thong_diep(failure: ModelFailure) -> str:
    """Câu công khai: registry, trừ mã quá dài mang câu client dò để TỰ NÉN."""
    if failure.is_context_limit:
        return cau_qua_dai(failure.actual, failure.limit)
    return failure.message


def _model_error(
    failure: ModelFailure,
    *,
    protocol_code: str,
    error_type: str,
    param: Optional[str] = None,
) -> dict:
    return {
        "message": _thong_diep(failure),
        "type": error_type,
        "param": param if param is not None else failure.field,
        "code": protocol_code,
        "ltt_error": api_errors.model_failure_extension(
            failure, protocol_code=protocol_code
        ),
    }


def _openai_type(failure: ModelFailure) -> str:
    if failure.category == "capacity":
        return "rate_limit_error"
    if error_spec(failure.canonical_code).status < 500:
        return "invalid_request_error"
    return "api_error"


def _gioi_han(failure: ModelFailure) -> dict:
    """`limit_name`/`limit_value` ở thân HTTP quá dài (tài liệu `LOI_413`)."""
    if not failure.is_context_limit:
        return {}
    them: dict = {"limit_name": "input_tokens"}
    if failure.limit is not None:
        them["limit_value"] = int(failure.limit)
    return them


def _model_body(path: str, failure: ModelFailure, *, sse: bool) -> dict:
    _anthropic, openai_code = _MODEL_PROTOCOL[failure.canonical_code]
    anthropic_type = model_protocol_code(
        path, failure.canonical_code,
        phase="after_headers" if sse else "before_headers")
    them = {} if sse else _gioi_han(failure)
    if path.endswith("/messages"):
        error = _model_error(
            failure, protocol_code=anthropic_type, error_type=anthropic_type
        )
        error.pop("param")
        error.pop("code")
        return {"type": "error", "error": error, **them}
    if path.endswith("/responses"):
        if not sse:
            # Trước 200: lỗi HTTP khuôn OpenAI (`{"error": {...}}`), như chat.
            param = "input" if failure.is_context_limit else None
            return {"error": _model_error(
                failure, protocol_code=openai_code,
                error_type=_openai_type(failure), param=param,
            ), **them}
        error = _model_error(failure, protocol_code=openai_code, error_type="api_error")
        error.pop("param")
        error.pop("type")
        return {
            "type": "response.failed",
            "response": {
                "id": _id_response(),
                "object": "response",
                "status": "failed",
                "error": error,
            },
        }
    if path.endswith("/chat/completions"):
        param = "messages" if failure.is_context_limit else None
        return {"error": _model_error(
            failure, protocol_code=openai_code,
            error_type=_openai_type(failure), param=param,
        ), **them}
    return api_errors.model_problem(failure, instance=path).to_dict()


def _khoi_sse(path: str, failure: ModelFailure) -> bytes:
    payload = json.dumps(_model_body(path, failure, sse=True)).encode("utf-8")
    if path.endswith("/messages"):
        return b"event: error\ndata: " + payload + b"\n\n"
    if path.endswith("/responses"):
        return b"event: response.failed\ndata: " + payload + b"\n\n"
    return b"data: " + payload + b"\n\n"


@overload
def render_model_failure(
    path: str,
    failure: ModelFailure,
    *,
    phase: Literal["before_headers"],
    stream: Literal[False],
) -> JSONResponse: ...


@overload
def render_model_failure(
    path: str,
    failure: ModelFailure,
    *,
    phase: Literal["before_headers"],
    stream: bool,
) -> Response: ...


@overload
def render_model_failure(
    path: str,
    failure: ModelFailure,
    *,
    phase: Literal["after_headers"],
    stream: bool,
) -> bytes: ...


def render_model_failure(
    path: str,
    failure: ModelFailure,
    *,
    phase: Literal["before_headers", "after_headers"],
    stream: bool,
) -> Response | bytes:
    """Render một lỗi typed mà không đổi canonical semantics của nó.

    ⭐ Responses **stream** + mã quá dài, TRƯỚC 200 ⇒ 200 + đúng MỘT
       ``response.failed`` (``context_length_exceeded``): đường duy nhất Codex
       hiểu là tràn cửa sổ và tự nén (HTTP 400 là lỗi chết lượt với Codex).
    """
    if phase not in {"before_headers", "after_headers"}:
        raise ValueError(f"unsupported model failure phase: {phase}")
    if phase == "after_headers":
        return _khoi_sse(path, failure)

    if stream and path.endswith("/responses") and failure.is_context_limit:
        return StreamingResponse(iter([_khoi_sse(path, failure)]),
                                 media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store",
                                          "X-Accel-Buffering": "no"})

    body = _model_body(path, failure, sse=False)
    spec = error_spec(failure.canonical_code)
    status = 529 if path.endswith("/messages") and failure.canonical_code == (
        "provider_overloaded"
    ) else spec.status
    headers = {"Cache-Control": "no-store"}
    if failure.retry_after_s is not None and failure.retry_after_s > 0:
        headers["Retry-After"] = str(failure.retry_after_s)
    media_type = (
        api_errors.PROBLEM_CONTENT_TYPE
        if not any(path.endswith(suffix) for suffix in (
            "/messages", "/chat/completions", "/responses"
        ))
        else "application/json"
    )
    return JSONResponse(body, status_code=status, media_type=media_type, headers=headers)


def loi_sse(duong: str, failure: ModelFailure) -> bytes:
    """Khối SSE lỗi SAU 200 cho cửa `duong` (`/v1/messages`, `/v1/responses`, còn lại)."""
    return _khoi_sse(duong, failure)


def _qua_dai_typed(failure: ModelFailure | None, *, token: Optional[int],
                   tran: Optional[int], request) -> ModelFailure:
    typed = failure or model_failure(
        "context_window_exceeded",
        http_status=400,
        request_id=_request_id(request),
        field="context",
    )
    # Số cho câu "prompt is too long: N tokens > M maximum" khi lỗi chưa mang.
    if typed.limit is None and tran is not None:
        typed = replace(typed, limit=int(tran))
    if typed.actual is None and token is not None:
        typed = replace(typed, actual=int(token))
    if request is not None:
        # Nhật ký request ghi mã ổn định như mọi `ApiError` (`server/api/errors.py`).
        request.state.api_error_code = model_protocol_code(
            "/v1/chat/completions", typed.canonical_code)
    return typed


def loi_qua_dai(duong: str, *, stream: bool, token: Optional[int] = None,
                tran: Optional[int] = None, request=None,
                failure: ModelFailure | None = None) -> Response:
    """Phản hồi "quá dài" TRƯỚC 200 cho cửa `duong` — 0 khoản giữ, chưa chạm máy B.

    `/v1/messages` ⇒ 400 khuôn Anthropic · `/v1/responses` stream ⇒ 200 + MỘT
    `response.failed` (đường duy nhất Codex hiểu là tràn cửa sổ) · còn lại ⇒ 400
    khuôn OpenAI. `limit_name`/`limit_value` giữ ở thân (tài liệu `LOI_413`).
    """
    typed = _qua_dai_typed(failure, token=token, tran=tran, request=request)
    return render_model_failure(duong, typed, phase="before_headers", stream=stream)


def loi_qua_dai_json(duong: str, *, token: Optional[int] = None,
                     tran: Optional[int] = None, request=None,
                     failure: ModelFailure | None = None) -> JSONResponse:
    """Nhánh HTTP 400 của `loi_qua_dai` (mọi cửa trừ Responses stream)."""
    typed = _qua_dai_typed(failure, token=token, tran=tran, request=request)
    return render_model_failure(duong, typed, phase="before_headers", stream=False)


def _request_id(request) -> str:
    if request is None:
        return ""
    from server.api.context import request_id

    return request_id(request)


def bo_nhip(duong: str) -> Callable[[str], bytes]:
    """Bộ dựng nhịp chờ cho MỘT lượt: `nhip(ly_do) -> bytes`.

    `/v1/responses` ⇒ SỰ KIỆN hợp lệ: lần đầu `response.created` (status
    `queued`), rồi `response.in_progress` — Codex nạp lại đồng hồ im lặng SSE chỉ
    khi có sự kiện (comment bị bộ phân tích nuốt), và `openai-python`
    `responses.stream()` đòi `response.created` là sự kiện đầu. Luồng máy B sau đó
    phát `response.created` của nó: Codex giữ id cuối, `openai-python` bỏ qua bản
    thứ hai. Các cửa khác ⇒ chú thích SSE như cũ (mọi client bỏ qua).
    """
    if not duong.endswith("/responses"):
        def _chu_thich(ly_do: str) -> bytes:
            return f": ltt-cho {ly_do}\n\n".encode("ascii", "replace")
        return _chu_thich

    rid = _id_response()
    tao_luc = int(time.time())
    dem = {"so": 0}

    def _su_kien(ly_do: str) -> bytes:
        so = dem["so"]
        dem["so"] = so + 1
        loai = "response.created" if so == 0 else "response.in_progress"
        than = {"type": loai, "sequence_number": so,
                "response": {"id": rid, "object": "response", "created_at": tao_luc,
                             "status": "queued" if so == 0 else "in_progress",
                             "output": []}}
        khoi = (f"event: {loai}\ndata: ".encode("ascii")
                + json.dumps(than).encode("utf-8") + b"\n\n")
        if so == 0:
            # Lần đầu: created RỒI in_progress ngay, để mọi nhịp đều có in_progress.
            return khoi + _su_kien(ly_do)
        return khoi

    return _su_kien
