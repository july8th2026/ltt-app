"""Một kiểu lỗi model duy nhất ở máy A, đọc được envelope B mới và legacy.

Module này cố ý chỉ phụ thuộc standard library và registry thuần dữ liệu của
gateway. Nó được dùng ở cả đường đồng bộ lẫn streaming mà không kéo web stack.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from llm_gateway.error_contract import error_spec
from llm_gateway.error_telemetry import ErrorTelemetry, choose_action


MAX_FAILURE_BODY_BYTES = 64 * 1024
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_SAFE_PROVIDER = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")

_LEGACY_FIELD_TO_CODE = {
    "images": "image_count_exceeded",
    "image_url": "image_url_not_allowed",
    "image_bytes": "image_too_large",
    "max_tokens": "max_output_tokens_exceeded",
    "max_output_tokens": "max_output_tokens_exceeded",
    "input_tokens": "input_tokens_exceeded",
    "context": "context_window_exceeded",
}

_COUNTER_LOCK = threading.Lock()
_COUNTERS = {"v1": 0, "legacy": 0, "unknown": 0, "mismatch": 0}
_TELEMETRY = ErrorTelemetry("A")
log = logging.getLogger("platform_core.llm.model_failure")


@dataclass(frozen=True)
class ModelFailure:
    canonical_code: str
    category: str
    message: str
    http_status: int
    retry: str
    recovery: str
    request_id: str
    field: str | None = None
    limit: int | None = None
    actual: int | None = None
    retry_after_s: int | None = None
    provider_type: str | None = None
    provider_code: str | int | None = None
    upstream_status: int | None = None

    @property
    def is_context_limit(self) -> bool:
        return self.canonical_code in {
            "input_tokens_exceeded",
            "context_window_exceeded",
        }

    @property
    def is_busy(self) -> bool:
        return self.canonical_code in {
            "rate_limited",
            "concurrency_limited",
            "provider_overloaded",
            "model_loading",
        }

    @property
    def is_timeout(self) -> bool:
        return self.canonical_code in {"upstream_timeout", "stream_idle_timeout"}

    @property
    def is_cancelled(self) -> bool:
        return self.canonical_code == "request_cancelled"

    @property
    def penalizes_key(self) -> bool:
        """Chỉ tín hiệu chứng minh endpoint/credential hỏng mới phạt key."""
        return self.canonical_code in {
            "unauthorized",
            "forbidden",
            "upstream_unreachable",
            "provider_oom",
            "stream_truncated",
            "malformed_upstream_response",
            "empty_response",
            "upstream_protocol_error",
            "internal_error",
            "upstream_unknown",
        }

    @property
    def retry_same_generation(self) -> bool:
        """Retry nội bộ duy nhất đã được chứng minh là ngẫu nhiên theo lượt sinh."""
        return self.canonical_code == "tool_call_parse_failed"

    def as_detail(self) -> dict[str, Any]:
        """Dạng an toàn cho lớp tương thích; không chứa prose từ provider."""
        detail: dict[str, Any] = {
            "schema_version": 1,
            "canonical_code": self.canonical_code,
            "category": self.category,
            "message": self.message,
            "retry": self.retry,
            "recovery": self.recovery,
            "request_id": self.request_id,
        }
        optional = {
            "field": self.field,
            "limit": self.limit,
            "actual": self.actual,
            "retry_after_s": self.retry_after_s,
            "provider_type": self.provider_type,
            "provider_code": self.provider_code,
            "upstream_status": self.upstream_status,
        }
        detail.update({key: value for key, value in optional.items() if value is not None})
        if self.field is not None:
            detail.update({"truong": self.field, "tran": self.limit, "thay": self.actual})
        return detail


def failure_decode_counters() -> dict[str, int]:
    with _COUNTER_LOCK:
        return dict(_COUNTERS)


def failure_telemetry_snapshot() -> dict[str, object]:
    """Snapshot counter A; không chứa request ID, message hay dữ liệu request."""
    return _TELEMETRY.snapshot()


def failure_telemetry_reset_for_tests() -> None:
    _TELEMETRY.reset_for_tests()


def observe_model_failure(
    failure: "ModelFailure",
    *,
    gateway_code: str = "",
    protocol_code: str = "",
    protocol: str = "gateway",
    stream_phase: str = "before_headers",
    model: str = "",
    endpoint: str = "gateway",
    elapsed_ms: int | float = 0,
    action: str = "",
    legacy: bool = False,
    contract_mismatch: bool = False,
    model_known: bool = False,
    count: bool = True,
) -> dict[str, object]:
    """Ghi lỗi đã chuẩn hoá; caller không thể truyền raw body/message vào đây."""
    chosen = action or choose_action(
        canonical_code=failure.canonical_code,
        retry=failure.retry,
        legacy=legacy,
        contract_mismatch=contract_mismatch,
    )
    return _TELEMETRY.record(
        logger=log,
        request_id=failure.request_id,
        gateway_code=gateway_code or failure.canonical_code,
        canonical_code=failure.canonical_code,
        protocol_code=protocol_code or failure.canonical_code,
        category=failure.category,
        http_status=failure.http_status,
        upstream_status=failure.upstream_status,
        protocol=protocol,
        stream_phase=stream_phase,
        retry=failure.retry,
        recovery=failure.recovery,
        model=model,
        elapsed_ms=elapsed_ms,
        endpoint=endpoint,
        action=chosen,
        legacy=legacy,
        contract_mismatch=contract_mismatch,
        model_known=model_known,
        count=count,
    )


def _count(name: str) -> None:
    with _COUNTER_LOCK:
        _COUNTERS[name] += 1


def _header(headers: Mapping[str, str], name: str) -> str:
    wanted = name.lower()
    return str(
        next((value for key, value in headers.items() if str(key).lower() == wanted), "") or ""
    )


def _request_id(value: object) -> str:
    text = str(value or "")
    return text if _SAFE_ID.fullmatch(text) else ""


def _integer(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _nonnegative(value: object) -> int | None:
    number = _integer(value)
    return number if number is not None and number >= 0 else None


def _provider_value(value: object) -> str | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and _SAFE_PROVIDER.fullmatch(value):
        return value
    return None


def _json_object(body: bytes) -> dict[str, Any] | None:
    if not body or len(body) > MAX_FAILURE_BODY_BYTES:
        return None
    try:
        decoded = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        return None
    return decoded if isinstance(decoded, dict) else None


def _candidate(root: dict[str, Any] | None) -> dict[str, Any] | None:
    if root is None:
        return None
    detail = root.get("detail")
    if isinstance(detail, dict):
        return detail
    error = root.get("error")
    if isinstance(error, dict):
        return error
    return root


def _retry_after(headers: Mapping[str, str], candidate: Mapping[str, Any]) -> int | None:
    inside = _nonnegative(candidate.get("retry_after_s"))
    if inside is not None:
        return inside
    try:
        seconds = int(_header(headers, "retry-after").strip())
    except ValueError:
        return None
    return seconds if 0 <= seconds <= 86_400 else None


def _build(
    code: str,
    *,
    status: int,
    headers: Mapping[str, str],
    candidate: Mapping[str, Any],
    request_id: str,
) -> ModelFailure:
    spec = error_spec(code)
    provider_type = _provider_value(candidate.get("provider_type"))
    return ModelFailure(
        canonical_code=spec.code,
        category=spec.category,
        message=spec.message,
        http_status=int(status),
        retry=spec.retry,
        recovery=spec.recovery,
        request_id=request_id,
        field=str(candidate.get("field") or "") or None,
        limit=_integer(candidate.get("limit")),
        actual=_integer(candidate.get("actual")),
        retry_after_s=_retry_after(headers, candidate),
        provider_type=provider_type if isinstance(provider_type, str) else None,
        provider_code=_provider_value(candidate.get("provider_code")),
        upstream_status=_integer(candidate.get("upstream_status")),
    )


def model_failure(
    code: str,
    *,
    http_status: int,
    request_id: str = "",
    field: str | None = None,
    limit: int | None = None,
    actual: int | None = None,
    retry_after_s: int | None = None,
) -> ModelFailure:
    """Tạo lỗi nội bộ an toàn khi chưa có body HTTP để decode."""
    candidate: dict[str, Any] = {}
    if field is not None:
        candidate["field"] = field
    if limit is not None:
        candidate["limit"] = limit
    if actual is not None:
        candidate["actual"] = actual
    if retry_after_s is not None:
        candidate["retry_after_s"] = retry_after_s
    return _build(
        code,
        status=http_status,
        headers={},
        candidate=candidate,
        request_id=_request_id(request_id),
    )


def decode_gateway_failure(status: int, headers: Mapping[str, str], body: bytes) -> ModelFailure:
    """Decode v1/legacy có giới hạn; dữ liệu thiếu luôn fail closed unknown."""
    root = _json_object(body)
    candidate = _candidate(root)
    data: Mapping[str, Any] = candidate or {}
    header_id = _request_id(_header(headers, "x-ltt-request-id"))
    body_id = _request_id(data.get("request_id"))
    request_id = body_id or header_id
    contract_mismatch = False

    if data.get("schema_version") == 1:
        code = str(data.get("canonical_code") or "")
        try:
            failure = _build(
                code, status=status, headers=headers, candidate=data, request_id=request_id
            )
        except KeyError:
            _count("mismatch")
            contract_mismatch = True
        else:
            _count("v1")
            observe_model_failure(failure, gateway_code=code)
            return failure

    legacy_value = data.get("legacy")
    legacy: Mapping[str, Any] = legacy_value if isinstance(legacy_value, dict) else data
    field = str(legacy.get("truong") or "")
    legacy_code = _LEGACY_FIELD_TO_CODE.get(field)
    if legacy_code:
        normalized = {
            "field": field,
            "limit": legacy.get("tran"),
            "actual": legacy.get("thay"),
        }
        _count("legacy")
        failure = _build(
            legacy_code,
            status=status,
            headers=headers,
            candidate=normalized,
            request_id=request_id,
        )
        observe_model_failure(
            failure,
            gateway_code=str(data.get("canonical_code") or "legacy"),
            legacy=True,
            contract_mismatch=contract_mismatch,
        )
        return failure

    _count("unknown")
    failure = _build(
        "upstream_unknown", status=status, headers=headers, candidate=data, request_id=request_id
    )
    observe_model_failure(
        failure,
        gateway_code=str(data.get("canonical_code") or "untyped"),
        contract_mismatch=contract_mismatch,
    )
    return failure
