"""Bộ giải mã hữu hạn cho lỗi HTTP từ llama.cpp/llama-swap.

Chỉ các field máy đọc được (`type` hoặc string `code`) mới quyết định ngữ nghĩa.
HTTP status và `message` không bao giờ được dùng để đoán context, ảnh hay OOM.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from .error_contract import make_error


# Đủ lớn cho object lỗi thông thường nhưng chặn một trang proxy/body bất thường
# khỏi được parse/copy thêm trên đường lỗi.
MAX_ERROR_BODY_BYTES = 64 * 1024

_SAFE_PROVIDER_VALUE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")

# Nguồn: llama.cpp tools/server/server-common.cpp::format_error_response.
# `server_error` cố ý không được đổi thành internal/provider_oom: type ấy quá
# rộng, nên chỉ có thể fail closed thành upstream_unknown.
_LLAMA_TYPE_TO_CANONICAL = {
    "exceed_context_size_error": "context_window_exceeded",
    "invalid_request_error": "invalid_request",
    "not_found_error": "model_not_found",
    "unavailable_error": "model_loading",
    "server_error": "upstream_unknown",
    "authentication_error": "unauthorized",
    "permission_error": "forbidden",
    "not_supported_error": "unsupported_parameter",
}


def _safe_provider_value(value: object) -> str | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and _SAFE_PROVIDER_VALUE.fullmatch(value):
        return value
    return None


def _retry_after(headers: Mapping[str, str]) -> int | None:
    raw = next((value for key, value in headers.items()
                if str(key).lower() == "retry-after"), None)
    try:
        seconds = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return seconds if 0 <= seconds <= 86_400 else None


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _error_object(body: bytes) -> dict[str, Any] | None:
    if not body or len(body) > MAX_ERROR_BODY_BYTES:
        return None
    try:
        decoded = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        return None
    if not isinstance(decoded, dict):
        return None
    candidate = decoded.get("error", decoded)
    return candidate if isinstance(candidate, dict) else None


def decode_upstream_http(status: int, headers: Mapping[str, str], body: bytes,
                         *, request_id: str) -> dict[str, object]:
    """Trả envelope v1 đã lọc; không bao giờ phân loại bằng prose/status."""
    error = _error_object(body)
    provider_type = _safe_provider_value(error.get("type")) if error else None
    provider_code = _safe_provider_value(error.get("code")) if error else None

    typed_key = provider_type
    if typed_key not in _LLAMA_TYPE_TO_CANONICAL and isinstance(provider_code, str):
        typed_key = provider_code
    canonical = _LLAMA_TYPE_TO_CANONICAL.get(
        typed_key if isinstance(typed_key, str) else "",
        "upstream_unknown",
    )

    limit = actual = None
    if canonical == "context_window_exceeded" and error is not None:
        limit = _positive_int(error.get("n_ctx"))
        actual = _positive_int(error.get("n_prompt_tokens"))

    return make_error(
        canonical,
        request_id=request_id,
        limit=limit,
        actual=actual,
        retry_after_s=_retry_after(headers),
        provider_type=provider_type if isinstance(provider_type, str) else None,
        provider_code=provider_code,
        upstream_status=int(status),
    )
