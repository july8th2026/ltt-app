"""Versioned, machine-readable failure contract between machine B and A.

This module deliberately uses only the Python standard library.  Machine B is
deployed independently from the platform application, while machine A imports
the same vocabulary as a client of that gateway.  Keeping this boundary pure
prevents either deployment from pulling in the other's web stack.

``message`` is owned by this registry.  Callers cannot pass exception text to
``make_error``: provider bodies can contain prompts, paths, VRAM details, or
configuration and therefore belong only in separately scrubbed operator logs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SCHEMA_VERSION = 1

RETRY_NEVER = "never"
RETRY_AFTER_FIX = "after_fix"
RETRY_AFTER_DELAY = "after_delay"
RETRY_AMBIGUOUS = "ambiguous"
RETRY_VALUES = frozenset({
    RETRY_NEVER,
    RETRY_AFTER_FIX,
    RETRY_AFTER_DELAY,
    RETRY_AMBIGUOUS,
})

RECOVERY_VALUES = frozenset({
    "none",
    "reduce_input",
    "reduce_output",
    "offload_images",
    "replace_image",
    "choose_model",
    "wait",
    "reauthenticate",
    "top_up",
    "retry_same_request",
    "report_request_id",
})

CATEGORY_VALUES = frozenset({
    "invalid_request",
    "model",
    "availability",
    "transport",
    "image",
    "image_security",
    "token",
    "generation",
    "auth",
    "billing",
    "capacity",
    "provider",
    "lifecycle",
    "stream",
    "protocol",
    "internal",
    "unknown",
})


@dataclass(frozen=True)
class GatewayErrorSpec:
    """Stable semantics for one failure code on the B-to-A wire."""

    code: str
    category: str
    status: int
    retry: str
    recovery: str
    message: str


def _spec(code: str, category: str, status: int, retry: str, recovery: str,
          message: str) -> GatewayErrorSpec:
    return GatewayErrorSpec(
        code=code,
        category=category,
        status=status,
        retry=retry,
        recovery=recovery,
        message=message,
    )


_SPECS = (
    _spec("invalid_request", "invalid_request", 400, RETRY_NEVER, "none",
          "The request is invalid."),
    _spec("unsupported_parameter", "invalid_request", 400, RETRY_AFTER_FIX,
          "none", "A request parameter is not supported."),
    _spec("unsupported_modality", "invalid_request", 400, RETRY_AFTER_FIX,
          "choose_model", "This model does not support the requested input type."),
    _spec("model_not_found", "model", 404, RETRY_AFTER_FIX, "choose_model",
          "The requested model is not served."),
    _spec("model_loading", "availability", 503, RETRY_AFTER_DELAY, "wait",
          "The requested model is loading."),
    _spec("request_body_too_large", "transport", 413, RETRY_AFTER_FIX, "none",
          "The HTTP request body is too large."),
    _spec("image_count_exceeded", "image", 400, RETRY_AFTER_FIX,
          "offload_images", "Too many images in one request."),
    _spec("image_too_large", "image", 400, RETRY_AFTER_FIX, "offload_images",
          "An image exceeds the per-image byte limit."),
    _spec("image_url_not_allowed", "image_security", 400, RETRY_AFTER_FIX,
          "replace_image", "Remote image URLs are not allowed."),
    _spec("image_decode_failed", "image", 400, RETRY_AFTER_FIX,
          "replace_image", "An image could not be decoded."),
    _spec("input_tokens_exceeded", "token", 400, RETRY_AFTER_FIX,
          "reduce_input", "The input exceeds this model profile's token limit."),
    _spec("max_output_tokens_exceeded", "token", 400, RETRY_AFTER_FIX,
          "reduce_output", "The requested output token limit is too large."),
    _spec("context_window_exceeded", "token", 400, RETRY_AFTER_FIX,
          "reduce_input", "The input and requested output exceed the context window."),
    _spec("tool_call_parse_failed", "generation", 502, RETRY_AMBIGUOUS, "none",
          "The model output could not be parsed as a tool call."),
    _spec("structured_output_failed", "generation", 502, RETRY_AMBIGUOUS,
          "none", "The model output did not satisfy the requested structure."),
    _spec("unauthorized", "auth", 401, RETRY_NEVER, "reauthenticate",
          "Authentication failed."),
    _spec("forbidden", "auth", 403, RETRY_NEVER, "none",
          "This credential may not perform the requested action."),
    _spec("insufficient_credit", "billing", 409, RETRY_AFTER_FIX, "top_up",
          "The account does not have enough credit for this request."),
    _spec("quota_exceeded", "billing", 429, RETRY_AFTER_FIX, "wait",
          "The account quota is exhausted."),
    _spec("rate_limited", "capacity", 429, RETRY_AFTER_DELAY, "wait",
          "The request rate limit was exceeded."),
    _spec("concurrency_limited", "capacity", 429, RETRY_AFTER_DELAY, "wait",
          "The concurrency limit was reached."),
    _spec("provider_overloaded", "capacity", 503, RETRY_AFTER_DELAY, "wait",
          "The model provider is temporarily overloaded."),
    _spec("upstream_timeout", "transport", 504, RETRY_AMBIGUOUS,
          "report_request_id", "The model provider did not respond in time."),
    _spec("upstream_unreachable", "transport", 502, RETRY_AFTER_DELAY,
          "retry_same_request", "The model provider could not be reached."),
    _spec("provider_oom", "provider", 503, RETRY_AFTER_FIX,
          "report_request_id", "The model provider ran out of GPU memory."),
    _spec("request_cancelled", "lifecycle", 499, RETRY_NEVER, "none",
          "The request was cancelled."),
    _spec("stream_idle_timeout", "stream", 504, RETRY_AMBIGUOUS,
          "report_request_id", "The model stream was idle for too long."),
    _spec("stream_truncated", "stream", 502, RETRY_AMBIGUOUS,
          "report_request_id", "The model stream ended before a terminal event."),
    _spec("malformed_upstream_response", "protocol", 502, RETRY_AMBIGUOUS,
          "report_request_id", "The model provider returned a malformed response."),
    _spec("empty_response", "protocol", 502, RETRY_AMBIGUOUS,
          "report_request_id", "The model provider returned no content."),
    _spec("upstream_protocol_error", "protocol", 502, RETRY_AMBIGUOUS,
          "report_request_id", "The model provider violated the streaming protocol."),
    _spec("internal_error", "internal", 500, RETRY_AFTER_DELAY,
          "report_request_id", "The service could not complete the request."),
    _spec("upstream_unknown", "unknown", 502, RETRY_AMBIGUOUS,
          "report_request_id", "The model provider returned an unclassified error."),
)

ERROR_SPECS = {spec.code: spec for spec in _SPECS}


def _validate_registry() -> None:
    if len(ERROR_SPECS) != len(_SPECS):
        raise RuntimeError("duplicate model error code")
    for code, spec in ERROR_SPECS.items():
        if not code or spec.code != code:
            raise RuntimeError("invalid model error code")
        if spec.category not in CATEGORY_VALUES:
            raise RuntimeError(f"invalid category for {code}")
        if not 400 <= spec.status <= 599:
            raise RuntimeError(f"invalid status for {code}")
        if spec.retry not in RETRY_VALUES:
            raise RuntimeError(f"invalid retry class for {code}")
        if spec.recovery not in RECOVERY_VALUES:
            raise RuntimeError(f"invalid recovery action for {code}")
        if not spec.message.strip():
            raise RuntimeError(f"missing safe message for {code}")


_validate_registry()


def error_spec(code: str) -> GatewayErrorSpec:
    """Return the registered spec; reject unknown codes instead of guessing."""
    try:
        return ERROR_SPECS[str(code)]
    except KeyError as exc:
        raise KeyError(f"model error code {code!r} is not registered") from exc


def make_error(code: str, *, request_id: str, field: str | None = None,
               limit: int | None = None, actual: int | None = None,
               retry_after_s: int | None = None,
               provider_type: str | None = None,
               provider_code: str | int | None = None,
               upstream_status: int | None = None) -> dict[str, Any]:
    """Build one version-1 wire envelope using only registry-owned prose."""
    spec = error_spec(code)
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "canonical_code": spec.code,
        "category": spec.category,
        "message": spec.message,
        "retry": spec.retry,
        "recovery": spec.recovery,
        "request_id": str(request_id),
    }
    optional = {
        "field": field,
        "limit": limit,
        "actual": actual,
        "retry_after_s": retry_after_s,
        "provider_type": provider_type,
        "provider_code": provider_code,
        "upstream_status": upstream_status,
    }
    body.update({key: value for key, value in optional.items() if value is not None})
    return body
