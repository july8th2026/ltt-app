"""Golden cho một ModelFailure qua RFC 9457, Anthropic, Chat và Responses."""
from __future__ import annotations

import json

import pytest
from starlette.responses import Response

from llm_gateway.error_contract import ERROR_SPECS
from platform_core.llm.model_failure import model_failure
from platform_core.public_api.config import load_public_api_config
from platform_core.public_api.error_registry import REGISTRY
from server.api import su_kien_loi


# Giá trị adapter công khai, chép rõ từng mã để thêm mã mà quên renderer phải đỏ.
_PROTOCOL = {
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

_PATHS = (
    "/api/v1/jobs",
    "/v1/messages",
    "/v1/chat/completions",
    "/v1/responses",
)


def _failure(code: str):
    return model_failure(
        code,
        http_status=599,  # cố tình khác status public để bắt suy diễn từ transport
        request_id="rid-golden",
        field="messages",
        limit=4,
        actual=6,
        retry_after_s=17,
    )


def _json_response(response: Response) -> dict:
    return json.loads(response.body)


def _sse_payload(block: bytes) -> tuple[str, dict]:
    lines = block.decode("utf-8").strip().splitlines()
    event = next((line[7:] for line in lines if line.startswith("event: ")), "")
    data = next(line[6:] for line in lines if line.startswith("data: "))
    return event, json.loads(data)


def _extension(path: str, body: dict) -> tuple[dict, str]:
    if path.endswith("/messages"):
        return body["error"]["ltt_error"], body["error"]["type"]
    if path.endswith("/responses") and body.get("type") == "response.failed":
        return body["response"]["error"]["ltt_error"], body["response"]["error"]["code"]
    if path.endswith("/chat/completions"):
        return body["error"]["ltt_error"], body["error"]["code"]
    return body["ltt_error"], body["code"]


def test_golden_phu_dung_33_ma_khong_thua_thieu():
    assert set(_PROTOCOL) == set(ERROR_SPECS)


@pytest.mark.parametrize("code", tuple(_PROTOCOL))
@pytest.mark.parametrize("path", _PATHS)
def test_truoc_header_giu_nguyen_nghia_va_status_public(code, path):
    failure = _failure(code)
    response = su_kien_loi.render_model_failure(
        path, failure, phase="before_headers", stream=False
    )
    assert isinstance(response, Response)
    body = _json_response(response)
    extension, protocol_code = _extension(path, body)
    expected = code if path == "/api/v1/jobs" else (
        _PROTOCOL[code][0] if path.endswith("/messages") else _PROTOCOL[code][1]
    )

    assert protocol_code == expected
    assert extension == {
        "schema_version": 1,
        "canonical_code": code,
        "protocol_code": expected,
        "category": failure.category,
        "retry": failure.retry,
        "recovery": failure.recovery,
        "request_id": "rid-golden",
        "field": "messages",
        "limit": 4,
        "actual": 6,
        "retry_after_s": 17,
    }
    expected_status = ERROR_SPECS[code].status
    if path.endswith("/messages") and code == "provider_overloaded":
        expected_status = 529
    assert response.status_code == expected_status
    assert response.status_code == 413 if code == "request_body_too_large" else response.status_code != 413
    if path == "/api/v1/jobs":
        assert response.media_type == "application/problem+json"
        assert body["type"] == f"/errors/{code}"
        assert body["code"] == code


@pytest.mark.parametrize("code", tuple(_PROTOCOL))
@pytest.mark.parametrize("path", _PATHS)
def test_sau_header_la_terminal_sse_nhung_khong_mat_ma(code, path):
    failure = _failure(code)
    block = su_kien_loi.render_model_failure(
        path, failure, phase="after_headers", stream=True
    )
    assert isinstance(block, bytes)
    event, body = _sse_payload(block)
    extension, protocol_code = _extension(path, body)
    expected = code if path == "/api/v1/jobs" else (
        _PROTOCOL[code][0] if path.endswith("/messages") else _PROTOCOL[code][1]
    )
    assert extension["canonical_code"] == code
    assert extension["protocol_code"] == expected
    assert extension["request_id"] == "rid-golden"
    assert protocol_code == expected
    if path.endswith("/messages"):
        assert event == "error"
    elif path.endswith("/responses"):
        assert event == "response.failed"


@pytest.mark.parametrize(
    "code",
    ("image_count_exceeded", "image_too_large", "max_output_tokens_exceeded"),
)
def test_anh_va_output_khong_bao_gio_bi_goi_context(code):
    for path in _PATHS[1:]:
        response = su_kien_loi.render_model_failure(
            path, _failure(code), phase="before_headers", stream=False
        )
        extension, protocol_code = _extension(path, _json_response(response))
        assert protocol_code != "context_length_exceeded"
        assert extension["canonical_code"] == code


def test_chi_hai_ma_token_duoc_adapter_context_tuong_thich():
    mapped = {code for code, (_, openai_code) in _PROTOCOL.items()
              if openai_code == "context_length_exceeded"}
    assert mapped == {"input_tokens_exceeded", "context_window_exceeded"}


def test_co_cau_truc_mac_dinh_tat_va_doc_tu_env_duoc_tiem():
    assert not load_public_api_config({}).structured_model_errors
    assert load_public_api_config(
        {"LTT_PUBLIC_API_STRUCTURED_MODEL_ERRORS": "1"}
    ).structured_model_errors


def test_rollout_khong_viet_de_hop_dong_public_api_cu():
    assert REGISTRY["model_not_found"].status == 400
    assert REGISTRY["quota_exceeded"].retry == "after_delay"


def test_co_tat_giu_nguyen_byte_legacy_co_bat_them_ltt_error():
    off = load_public_api_config({})
    on = load_public_api_config({"LTT_PUBLIC_API_STRUCTURED_MODEL_ERRORS": "1"})
    failure = _failure("context_window_exceeded")
    legacy = su_kien_loi.loi_sse(
        "/v1/chat/completions",
        "context_length",
        "prompt is too long",
        failure=failure,
        structured=off.structured_model_errors,
    )
    assert b'"ltt_error"' not in legacy

    modern = su_kien_loi.loi_sse(
        "/v1/chat/completions",
        "context_length",
        "prompt is too long",
        failure=failure,
        structured=on.structured_model_errors,
    )
    assert b'"ltt_error"' in modern


def test_renderer_tu_choi_phase_la_de_khong_doan():
    with pytest.raises(ValueError):
        su_kien_loi.render_model_failure(
            "/v1/messages", _failure("invalid_request"), phase="during", stream=True
        )
