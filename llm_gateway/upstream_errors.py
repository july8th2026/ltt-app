"""Bộ giải mã hữu hạn cho lỗi HTTP từ llama.cpp/llama-swap.

Chỉ các field máy đọc được (`type` hoặc string `code`) mới quyết định ngữ nghĩa.
HTTP status và `message` không bao giờ được dùng để đoán context, ảnh hay OOM.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from collections.abc import Generator, Mapping
from typing import Any, Callable, Iterator

from .error_contract import make_error


# Đủ lớn cho object lỗi thông thường nhưng chặn một trang proxy/body bất thường
# khỏi được parse/copy thêm trên đường lỗi.
MAX_ERROR_BODY_BYTES = 64 * 1024
MAX_SSE_FRAME_BYTES = 1024 * 1024

_SAFE_PROVIDER_VALUE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_SSE_BOUNDARY = re.compile(br"\r?\n\r?\n")
log = logging.getLogger("llm_gateway.upstream_errors")

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

_STREAM_TYPE_TO_CANONICAL = {
    "overloaded_error": "provider_overloaded",
    "rate_limit_error": "rate_limited",
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


@dataclass(frozen=True)
class ObservedFrame:
    """Một SSE frame nguyên byte và kết luận terminal (nếu có)."""

    raw: bytes
    failure: dict[str, object] | None = None
    terminal: bool = False


def _json_object(value: str) -> dict[str, Any] | None:
    try:
        decoded = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None
    return decoded if isinstance(decoded, dict) else None


def _decode_stream_error(error: dict[str, Any] | None, *,
                         request_id: str) -> dict[str, object]:
    candidate = error if isinstance(error, dict) else {}
    provider_type = _safe_provider_value(candidate.get("type"))
    provider_code = _safe_provider_value(candidate.get("code"))
    typed_key = provider_type
    if not isinstance(typed_key, str) and isinstance(provider_code, str):
        typed_key = provider_code
    if isinstance(typed_key, str) and typed_key in _STREAM_TYPE_TO_CANONICAL:
        return make_error(
            _STREAM_TYPE_TO_CANONICAL[typed_key],
            request_id=request_id,
            provider_type=provider_type if isinstance(provider_type, str) else None,
            provider_code=provider_code,
            upstream_status=200,
        )
    # Dùng cùng bảng typed của lỗi HTTP. Body được dựng lại chỉ từ object đã
    # parse, nhưng decoder vẫn không bao giờ lấy message làm tín hiệu.
    body = json.dumps({"error": candidate}, separators=(",", ":")).encode()
    return decode_upstream_http(200, {}, body, request_id=request_id)


def _field_value(line: bytes) -> tuple[bytes, bytes]:
    field, separator, value = line.partition(b":")
    if separator and value.startswith(b" "):
        value = value[1:]
    return field, value


class UpstreamEventObserver:
    """Parser SSE tăng dần, giữ nguyên bytes và chỉ giữ tối đa một frame."""

    def __init__(self, *, request_id: str):
        self.request_id = request_id
        self._buffer = bytearray()
        self._terminal_seen = False
        self._finished = False
        self._saw_bytes = False

    def feed(self, chunk: bytes) -> list[ObservedFrame]:
        """Nhận chunk tùy ý; chỉ parse sau khi đã có trọn SSE frame."""
        if self._finished or not chunk:
            return []
        self._saw_bytes = True
        self._buffer.extend(chunk)

        frames: list[ObservedFrame] = []
        while not self._finished:
            match = _SSE_BOUNDARY.search(self._buffer)
            if match is None:
                if len(self._buffer) > MAX_SSE_FRAME_BYTES:
                    frames.append(self._protocol_error())
                break
            end = match.end()
            if end > MAX_SSE_FRAME_BYTES:
                frames.append(self._protocol_error())
                break
            raw = bytes(self._buffer[:end])
            del self._buffer[:end]
            frame = self._classify(raw, match.start())
            frames.append(frame)
            if frame.failure is not None:
                self._finished = True
                self._buffer.clear()
        return frames

    def _protocol_error(self) -> ObservedFrame:
        self._buffer.clear()
        self._finished = True
        return ObservedFrame(
            raw=b"",
            failure=make_error(
                "upstream_protocol_error",
                request_id=self.request_id,
                upstream_status=200,
            ),
        )

    def finish(self) -> list[ObservedFrame]:
        """EOF tự nhiên không có terminal rõ ràng là lỗi, không phải success."""
        if self._finished:
            return []
        self._finished = True
        self._buffer.clear()
        if self._terminal_seen:
            return []
        code = "stream_truncated" if self._saw_bytes else "empty_response"
        return [ObservedFrame(
            raw=b"",
            failure=make_error(
                code,
                request_id=self.request_id,
                upstream_status=200,
            ),
        )]

    def _classify(self, raw: bytes, content_end: int) -> ObservedFrame:
        event = ""
        data_lines: list[bytes] = []
        raw_error: bytes | None = None
        for line in raw[:content_end].splitlines():
            if not line or line.startswith(b":"):
                continue
            field, value = _field_value(line)
            if field == b"event":
                event = value.decode("utf-8", "replace").strip()
            elif field == b"data":
                data_lines.append(value)
            elif field == b"error":
                raw_error = value

        data = b"\n".join(data_lines)
        data_text = data.decode("utf-8", "replace").strip()
        payload = _json_object(data_text) if data_text else None

        error: dict[str, Any] | None = None
        is_failure = False
        if raw_error is not None:
            error = _json_object(raw_error.decode("utf-8", "replace").strip())
            is_failure = True
        elif event == "error":
            is_failure = True
            if payload is not None:
                nested = payload.get("error")
                error = nested if isinstance(nested, dict) else payload
        elif isinstance(payload, dict) and isinstance(payload.get("error"), dict):
            is_failure = True
            error = payload["error"]
        elif event == "response.failed" or (
                isinstance(payload, dict) and payload.get("type") == "response.failed"):
            is_failure = True
            response = payload.get("response") if isinstance(payload, dict) else None
            nested = response.get("error") if isinstance(response, dict) else None
            error = nested if isinstance(nested, dict) else payload

        if is_failure:
            return ObservedFrame(
                raw=b"",
                failure=_decode_stream_error(error, request_id=self.request_id),
            )

        payload_type = payload.get("type") if isinstance(payload, dict) else None
        terminal = (
            data_text == "[DONE]"
            or event in {"message_stop", "response.completed"}
            or payload_type in {"message_stop", "response.completed"}
        )
        if terminal:
            self._terminal_seen = True
        return ObservedFrame(raw=raw, terminal=terminal)


def _encoded_failure(failure: dict[str, object]) -> bytes:
    safe = json.dumps({"error": failure}, ensure_ascii=True,
                      separators=(",", ":")).encode("ascii")
    return b"event: error\ndata: " + safe + b"\n\n"


class _ObservedStream:
    """Iterator có close idempotent để cancellation không thành lỗi model."""

    def __init__(self, source: Iterator[bytes], *, request_id: str,
                 on_failure: Callable[[dict[str, object]], None] | None):
        self._source = source
        self._request_id = request_id
        self._on_failure = on_failure
        self._source_closed = False
        self._iterator = self._run()

    def __iter__(self) -> "_ObservedStream":
        return self

    def __next__(self) -> bytes:
        return next(self._iterator)

    def _close_source(self) -> None:
        if self._source_closed:
            return
        self._source_closed = True
        close = getattr(self._source, "close", None)
        if close is not None:
            close()

    def _emit(self, frame: ObservedFrame) -> Iterator[bytes]:
        if frame.failure is not None:
            if self._on_failure is not None:
                self._on_failure(frame.failure)
            yield _encoded_failure(frame.failure)
        elif frame.raw:
            yield frame.raw

    def _run(self) -> Generator[bytes, None, None]:
        observer = UpstreamEventObserver(request_id=self._request_id)
        try:
            for chunk in self._source:
                for frame in observer.feed(chunk):
                    yield from self._emit(frame)
                    if frame.failure is not None:
                        return
            for frame in observer.finish():
                yield from self._emit(frame)
        except GeneratorExit:
            log.warning("client_disconnected request_id=%s", self._request_id)
            raise
        finally:
            self._close_source()

    def close(self) -> None:
        try:
            self._iterator.close()
        finally:
            self._close_source()


def observe_upstream_events(
        stream: Iterator[bytes], *, request_id: str,
        on_failure: Callable[[dict[str, object]], None] | None = None,
) -> Iterator[bytes]:
    """Ẩn raw terminal error, phát một envelope an toàn; success giữ nguyên."""
    return _ObservedStream(stream, request_id=request_id, on_failure=on_failure)
