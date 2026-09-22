"""Machine-readable error contract for ``/api/v1`` — RFC 9457 problem details.

Why a second error shape at all: Q88 already fixed the JSON contract for
``/health`` and for app-nested APIs (``/<slug>/api/*``) and has a test holding
it (``tests/test_176_api_error_contract.py``). Changing that shape would break
frontends that ship today. A brand-new surface, however, gets to pick the
standard one, so ``/api/v1`` answers with ``application/problem+json``:

    {"type": "/errors/not_found", "title": "Not found", "status": 404,
     "detail": "...", "instance": "/api/v1/jobs/x", "code": "not_found",
     "request_id": "..."}

``type`` is deliberately a **relative** URI reference: RFC 9457 allows it, and a
absolute URL would hard-code a hostname into the payload — exactly what Q92
forbids.

Two rules this module exists to enforce:

* the ``detail`` a caller sees never carries request input, exception context,
  stack traces or configuration — see :func:`scrub_detail`;
* codes are stable strings. They are part of the public contract; titles and
  details may be reworded, ``code`` may not.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from llm_gateway.error_contract import error_spec
from platform_core.llm.model_failure import ModelFailure

PROBLEM_CONTENT_TYPE = "application/problem+json"

# Stable, machine-readable codes. Add here rather than inventing per route.
CODE_INVALID_REQUEST = "invalid_request"
CODE_UNAUTHORIZED = "unauthorized"
CODE_FORBIDDEN = "forbidden"
CODE_NOT_FOUND = "not_found"
CODE_METHOD_NOT_ALLOWED = "method_not_allowed"
CODE_CONFLICT = "conflict"
CODE_PAYLOAD_TOO_LARGE = "payload_too_large"
CODE_UNPROCESSABLE = "unprocessable_request"
CODE_RATE_LIMITED = "rate_limited"
CODE_INTERNAL = "internal_error"
CODE_READ_ONLY = "read_only"
CODE_SERVICE_UNAVAILABLE = "service_unavailable"

# Specific causes (EXT-02). These exist because the generic code above told the
# caller *that* it failed without telling them *what to do*: `conflict` covered
# "top up credit", "request a new quote" and "your client reused a key with a
# different body" — three problems with three different fixes.
#
# Note what is deliberately NOT split: 401. Every credential failure keeps one
# code, because separate codes for "unknown key" and "wrong secret" turn the
# endpoint into an oracle for guessing key ids.
CODE_MISSING_SCOPE = "missing_scope"
CODE_TOOL_NOT_ALLOWED = "tool_not_allowed"
CODE_INSUFFICIENT_CREDIT = "insufficient_credit"
CODE_PRICE_CHANGED = "price_changed"
CODE_IDEMPOTENCY_CONFLICT = "idempotency_conflict"
CODE_IDEMPOTENCY_IN_PROGRESS = "idempotency_in_progress"
CODE_QUOTE_EXPIRED = "quote_expired"
CODE_QUOTE_INVALID = "quote_invalid"
CODE_CONCURRENCY_LIMITED = "concurrency_limited"
CODE_MODEL_NOT_FOUND = "model_not_found"
CODE_QUOTA_EXCEEDED = "quota_exceeded"

_TITLES = {
    CODE_INVALID_REQUEST: "Invalid request",
    CODE_UNAUTHORIZED: "Unauthorized",
    CODE_FORBIDDEN: "Forbidden",
    CODE_NOT_FOUND: "Not found",
    CODE_METHOD_NOT_ALLOWED: "Method not allowed",
    CODE_CONFLICT: "Conflict",
    CODE_PAYLOAD_TOO_LARGE: "Payload too large",
    CODE_UNPROCESSABLE: "Unprocessable request",
    CODE_RATE_LIMITED: "Too many requests",
    CODE_INTERNAL: "Internal error",
    CODE_READ_ONLY: "Read-only mode",
    CODE_SERVICE_UNAVAILABLE: "Service unavailable",
    CODE_MISSING_SCOPE: "Missing scope",
    CODE_TOOL_NOT_ALLOWED: "Tool not allowed",
    CODE_INSUFFICIENT_CREDIT: "Insufficient credit",
    CODE_PRICE_CHANGED: "Price changed",
    CODE_IDEMPOTENCY_CONFLICT: "Idempotency conflict",
    CODE_IDEMPOTENCY_IN_PROGRESS: "Request still in progress",
    CODE_QUOTE_EXPIRED: "Quote expired",
    CODE_QUOTE_INVALID: "Quote invalid",
    CODE_CONCURRENCY_LIMITED: "Too many concurrent jobs",
    CODE_MODEL_NOT_FOUND: "Model not found",
    CODE_QUOTA_EXCEEDED: "Quota exceeded",
}

_STATUS_CODES = {
    400: CODE_INVALID_REQUEST,
    401: CODE_UNAUTHORIZED,
    403: CODE_FORBIDDEN,
    404: CODE_NOT_FOUND,
    405: CODE_METHOD_NOT_ALLOWED,
    409: CODE_CONFLICT,
    413: CODE_PAYLOAD_TOO_LARGE,
    422: CODE_UNPROCESSABLE,
    429: CODE_RATE_LIMITED,
    500: CODE_INTERNAL,
    503: CODE_SERVICE_UNAVAILABLE,
}

# What a caller is told when the server hit something unexpected. Never the
# exception text: provider SDKs put credentials and customer data in there.
GENERIC_INTERNAL_DETAIL = "The server could not complete this request."


def scrub_detail(value):
    """Return ``value`` with unsafe validation fields removed, JSON-safe.

    Pydantic error entries carry the original request under ``input`` and the
    raised exception under ``ctx``. The first can echo customer content back to
    whoever triggered the error; the second is not serializable at all. Both are
    dropped here so no route has to remember to do it.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [scrub_detail(item) for item in value]
    if isinstance(value, dict):
        return {str(key): scrub_detail(item) for key, item in value.items()
                if key not in {"input", "ctx"}}
    return str(value)


@dataclass(frozen=True)
class ApiProblem:
    """One RFC 9457 problem document."""

    status: int
    code: str
    title: str = ""
    detail: object = ""
    instance: str = ""
    request_id: str = ""
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        code = self.code or _STATUS_CODES.get(int(self.status), CODE_INTERNAL)
        body = {
            "type": f"/errors/{code}",
            "title": self.title or _TITLES.get(code, "Error"),
            "status": int(self.status),
            "code": code,
        }
        detail = scrub_detail(self.detail)
        if detail not in (None, ""):
            body["detail"] = detail
        if self.instance:
            body["instance"] = self.instance
        if self.request_id:
            body["request_id"] = self.request_id

        # Phân loại thử-lại đi kèm chính phản hồi, không nằm riêng trong tài
        # liệu. Trước đây `error_registry` biết đủ cả — lỗi này thử lại được
        # không, và thử lại có phải dùng lại `Idempotency-Key` không — nhưng
        # thứ duy nhất khách nhận được là một mã lỗi. Nên mỗi tích hợp phải tự
        # đoán, và đoán sai theo hướng "thử lại đi" là cách một lần gián đoạn
        # biến thành hai lần tính tiền.
        from platform_core.public_api import error_registry

        #  chứ không phải : hàm kia cố tình ném lỗi cho mã chưa
        # khai, và một mã lạ không được phép biến phản hồi lỗi thành lỗi 500.
        spec = error_registry.REGISTRY.get(code)
        if spec is not None:
            body["retry"] = spec.retry
            if spec.reuse_idempotency_key:
                body["reuse_idempotency_key"] = True

        for key, value in (self.extra or {}).items():
            if key not in body:
                body[key] = scrub_detail(value)
        return body


class ApiError(Exception):
    """Raise inside a ``/api/v1`` handler to answer with a problem document."""

    def __init__(self, status: int, code: str, detail: object = "", *,
                 title: str = "", extra: dict | None = None):
        self.status = int(status)
        self.code = str(code)
        self.title = title or _TITLES.get(self.code, "Error")
        self.detail = detail
        self.extra = dict(extra or {})
        super().__init__(f"{self.status} {self.code}")

    def problem(self, *, instance: str = "", request_id: str = "") -> ApiProblem:
        return ApiProblem(
            status=self.status, code=self.code, title=self.title,
            detail=self.detail, instance=instance, request_id=request_id,
            extra=self.extra,
        )


def problem_for_status(status: int, detail: object = "", *, instance: str = "",
                       request_id: str = "") -> ApiProblem:
    """Map a framework status (404 from routing, 405, …) onto the contract."""
    code = _STATUS_CODES.get(int(status), CODE_INTERNAL)
    if int(status) >= 500:
        detail = GENERIC_INTERNAL_DETAIL
    return ApiProblem(status=int(status), code=code, detail=detail,
                      instance=instance, request_id=request_id)


def model_failure_extension(
    failure: ModelFailure, *, protocol_code: str
) -> dict:
    """Extension công khai an toàn; không mang prose hay chi tiết hạ tầng B."""
    extension = {
        "schema_version": 1,
        "canonical_code": failure.canonical_code,
        "protocol_code": protocol_code,
        "category": failure.category,
        "retry": failure.retry,
        "recovery": failure.recovery,
        "request_id": failure.request_id,
    }
    optional = {
        "field": failure.field,
        "limit": failure.limit,
        "actual": failure.actual,
        "retry_after_s": failure.retry_after_s,
    }
    extension.update({key: value for key, value in optional.items() if value is not None})
    return extension


def model_problem(failure: ModelFailure, *, instance: str) -> ApiProblem:
    """RFC 9457 cho lỗi model, lấy status public từ registry chứ không từ B."""
    spec = error_spec(failure.canonical_code)
    return ApiProblem(
        status=spec.status,
        code=failure.canonical_code,
        title=failure.canonical_code.replace("_", " ").title(),
        detail=failure.message,
        instance=instance,
        request_id=failure.request_id,
        extra={
            "retry": failure.retry,
            "recovery": failure.recovery,
            "ltt_error": model_failure_extension(
                failure, protocol_code=failure.canonical_code
            ),
        },
    )


#: Câu DUY NHẤT mọi cửa nói khi hết credit. Một câu ⇒ không có hai bản trôi
#: khỏi nhau, và nó là tiếng Anh vì `/api/v1` là bề mặt tiếng Anh.
THIEU_CREDIT_LOI = (
    "Not enough credit for this call. The balance is checked against the "
    "maximum this request could consume, not its typical cost.")


def thieu_credit_chi_tiet(e: object) -> dict:
    """Dịch `can`/`con` của lỗi credit sang `required_credit`/`balance`.

    🔴 VÌ SAO CÓ HÀM NÀY. Rà 14/09/2026: bốn cửa công khai cùng báo "hết credit"
       bằng **hai hợp đồng khác nhau**.

           jobs.py       -> "Not enough credit for this call."
                            + required_credit + balance          ✅
           chat.py       -> str(e) = "Khong du credit: can 1234, con 56."
           streaming.py  -> str(e) = "so du khong du cho phan giu cho cua luot nay"
           workflows.py  -> str(loi)

       Ba cửa dưới trả cho khách một câu **tiếng Việt không dấu của nội bộ**, và
       khách muốn biết phải nạp bao nhiêu thì chỉ còn cách phân tích chuỗi.

    ⭐ Hai số ấy ĐÃ CÓ SẴN ở chỗ ném (`credit.py` khoá số dư rồi mới so). Hàm này
       chỉ **dịch tên**, một lần, một chỗ. (Bản dịch `{truong, tran, thay}` của
       lỗi model — `tran_bi_vuot` — đã gỡ ở Task 13: lỗi model nay mang
       `field`/`limit`/`actual` trong `ltt_error` của `render_model_failure`.)

    Trả `{}` khi không biết số, để bên gọi cứ `**` vào được: một lỗi thiếu chi
    tiết vẫn phải là một lỗi hợp lệ, chứ không được thành một lỗi khác.
    """
    ra: dict = {}
    can, con = getattr(e, "can", None), getattr(e, "con", None)
    if isinstance(can, int) and not isinstance(can, bool):
        ra["required_credit"] = can
    if isinstance(con, int) and not isinstance(con, bool):
        ra["balance"] = con
    return ra


def invalid_request(detail: object = "", **extra) -> ApiError:
    return ApiError(400, CODE_INVALID_REQUEST, detail, extra=extra or None)


def unauthorized(detail: object = "") -> ApiError:
    return ApiError(401, CODE_UNAUTHORIZED, detail)


def forbidden(detail: object = "") -> ApiError:
    return ApiError(403, CODE_FORBIDDEN, detail)


def not_found(detail: object = "") -> ApiError:
    return ApiError(404, CODE_NOT_FOUND, detail)


def conflict(detail: object = "", **extra) -> ApiError:
    return ApiError(409, CODE_CONFLICT, detail, extra=extra or None)


def payload_too_large(detail: object = "", **extra) -> ApiError:
    return ApiError(413, CODE_PAYLOAD_TOO_LARGE, detail, extra=extra or None)


def rate_limited(detail: object = "", **extra) -> ApiError:
    return ApiError(429, CODE_RATE_LIMITED, detail, extra=extra or None)


def read_only(detail: object = "") -> ApiError:
    """Emergency switch answer: reads keep working, writes stop."""
    return ApiError(503, CODE_READ_ONLY, detail,
                    title=_TITLES[CODE_READ_ONLY])


def service_unavailable(detail: object = "", *, retry_after: int = 0,
                        **extra) -> ApiError:
    """Temporarily cannot serve this — come back. The code already existed in
    the registry; until EXT-14 nothing constructed it, because the only 503 the
    platform could raise was the global read-only switch."""
    if retry_after:
        extra = {**extra, "retry_after": int(retry_after)}
    return ApiError(503, CODE_SERVICE_UNAVAILABLE, detail,
                    title=_TITLES[CODE_SERVICE_UNAVAILABLE],
                    extra=extra or None)


# ── Specific causes (EXT-02) ─────────────────────────────────────────────────
# Same statuses as the generic helpers they replace; only the code and the
# advice change. A caller matching on status keeps working.

def missing_scope(detail: object = "", **extra) -> ApiError:
    return ApiError(403, CODE_MISSING_SCOPE, detail, extra=extra or None)


def tool_not_allowed(detail: object = "", **extra) -> ApiError:
    return ApiError(403, CODE_TOOL_NOT_ALLOWED, detail, extra=extra or None)


def insufficient_credit(detail: object = "", **extra) -> ApiError:
    return ApiError(409, CODE_INSUFFICIENT_CREDIT, detail, extra=extra or None)


def price_changed(detail: object = "", **extra) -> ApiError:
    return ApiError(409, CODE_PRICE_CHANGED, detail, extra=extra or None)


def idempotency_conflict(detail: object = "", **extra) -> ApiError:
    return ApiError(409, CODE_IDEMPOTENCY_CONFLICT, detail, extra=extra or None)


def idempotency_in_progress(detail: object = "", **extra) -> ApiError:
    """The first attempt is still running — the opposite of a permanent error.

    Sharing `conflict` with the different-body case told a client to give up on
    a request that was about to succeed.
    """
    return ApiError(409, CODE_IDEMPOTENCY_IN_PROGRESS, detail,
                    extra=extra or None)


def model_not_found(detail: object = "", **extra) -> ApiError:
    """The `model` asked for is not one this platform serves (D02).

    Two different ways to arrive here must say the **same** sentence, or the
    customer has to guess whether the name is gone or the server is broken:

    * a name that was cut — `ltt_llm`, `ltt_llm_vision` — which integrations
      pinned to before 2026-09-11;
    * a name the admission declaration does not cover, which `suc_chua_admission`
      reports as `KeyError` (fail-closed: never run a model with no lease).

    Both used to come back as the generic `invalid_request`, which reads as "you
    sent malformed JSON" and sends the reader looking in the wrong place.

    ⛔ STATUS STAYS 400, not 404. The rule this module states for every specific
       cause is "same status as the generic helper it replaces; only the code and
       the advice change", so a client matching on status keeps working. A 404 on
       a POST body field would also be indistinguishable from "this route does
       not exist" — the one reading a caller is most likely to act on wrongly.
    """
    return ApiError(400, CODE_MODEL_NOT_FOUND, detail, extra=extra or None)


def quote_expired(detail: object = "") -> ApiError:
    return ApiError(400, CODE_QUOTE_EXPIRED, detail)


def quote_invalid(detail: object = "") -> ApiError:
    return ApiError(400, CODE_QUOTE_INVALID, detail)
