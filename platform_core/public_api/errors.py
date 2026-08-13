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


def quote_expired(detail: object = "") -> ApiError:
    return ApiError(400, CODE_QUOTE_EXPIRED, detail)


def quote_invalid(detail: object = "") -> ApiError:
    return ApiError(400, CODE_QUOTE_INVALID, detail)
