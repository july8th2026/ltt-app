"""Chuẩn hoá lỗi HTTP llama.cpp bằng typed field, không đoán từ câu chữ."""
from __future__ import annotations

import json

import pytest

from llm_gateway.upstream_errors import decode_upstream_http
from tests.test_250_llm_gateway import FakeUpstream, _client


def _body(error_type: str, code: int | str, message: str = "secret detail") -> bytes:
    return json.dumps({"error": {
        "code": code,
        "message": message,
        "type": error_type,
    }}).encode()


@pytest.mark.parametrize(("provider_type", "provider_code", "status", "canonical"), (
    ("exceed_context_size_error", 400, 400, "context_window_exceeded"),
    ("invalid_request_error", 400, 400, "invalid_request"),
    ("not_found_error", 404, 404, "model_not_found"),
    ("unavailable_error", 503, 503, "model_loading"),
    ("server_error", 500, 500, "upstream_unknown"),
    ("authentication_error", 401, 401, "unauthorized"),
    ("permission_error", 403, 403, "forbidden"),
    ("not_supported_error", 501, 501, "unsupported_parameter"),
))
def test_mapping_huu_han_theo_type_llama_cpp(
        provider_type, provider_code, status, canonical):
    error = decode_upstream_http(
        status,
        {},
        _body(provider_type, provider_code),
        request_id="rid-unit",
    )
    assert error["canonical_code"] == canonical
    assert error["provider_type"] == provider_type
    assert error["provider_code"] == provider_code
    assert error["upstream_status"] == status
    assert error["request_id"] == "rid-unit"
    assert "secret detail" not in json.dumps(error)


@pytest.mark.parametrize("status,body", (
    (400, b""),
    (502, b"<html>proxy says context window exceeded</html>"),
    (422, b'{"error":'),
    (400, _body("future_new_error", "context_window_exceeded")),
    (413, json.dumps({"error": {
        "code": 413,
        "message": "context window exceeded",
    }}).encode()),
))
def test_thieu_typed_bang_chung_thi_fail_closed(status, body):
    error = decode_upstream_http(
        status, {}, body, request_id="rid-unknown",
    )
    assert error["canonical_code"] == "upstream_unknown"
    assert error["upstream_status"] == status
    assert "context window exceeded" not in json.dumps(error)


def test_code_string_chi_duoc_dung_khi_nam_trong_mapping_huu_han():
    error = decode_upstream_http(
        400,
        {},
        json.dumps({"error": {"code": "exceed_context_size_error",
                               "message": "opaque"}}).encode(),
        request_id="rid-code",
    )
    assert error["canonical_code"] == "context_window_exceeded"
    assert error["provider_code"] == "exceed_context_size_error"


def test_retry_after_duoc_loc_va_than_qua_lon_khong_duoc_parse():
    valid = decode_upstream_http(
        503,
        {"Retry-After": "17"},
        _body("unavailable_error", 503),
        request_id="rid-retry",
    )
    assert valid["retry_after_s"] == 17

    huge = b'{"error":{"type":"exceed_context_size_error","message":"' + (
        b"context secret " * 6000) + b'"}}'
    unknown = decode_upstream_http(400, {}, huge, request_id="rid-huge")
    assert unknown["canonical_code"] == "upstream_unknown"
    assert "provider_type" not in unknown


def test_api_khong_chuyen_tiep_raw_loi_4xx_cua_llama_cpp():
    raw = _body("invalid_request_error", 400,
                "secret prompt C:/private/model.gguf")
    client, _ = _client(up=FakeUpstream(ma=400, than=raw))
    response = client.post(
        "/v1/chat/completions",
        headers={"X-LTT-Request-Id": "rid-http-400"},
        json={"model": "qwen38-api", "messages": []},
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["canonical_code"] == "invalid_request"
    assert detail["request_id"] == "rid-http-400"
    assert response.headers["X-LTT-Request-Id"] == "rid-http-400"
    assert "secret prompt" not in response.text
    assert "private/model.gguf" not in response.text


def test_api_stream_that_bai_truoc_header_cung_dung_decoder():
    raw = _body("exceed_context_size_error", 400, "secret context prose")
    client, _ = _client(up=FakeUpstream(ma=400, khoi_stream=[raw]))
    response = client.post(
        "/v1/chat/completions",
        headers={"X-LTT-Request-Id": "rid-stream-http"},
        json={"model": "qwen38-api", "messages": [], "stream": True},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["canonical_code"] == "context_window_exceeded"
    assert "secret context prose" not in response.text


def test_api_giu_http_compat_nhung_khong_mat_nghia_model_loading():
    raw = _body("unavailable_error", 503, "Loading private model path")
    client, _ = _client(up=FakeUpstream(ma=503, than=raw))
    response = client.post(
        "/v1/chat/completions",
        headers={"X-LTT-Request-Id": "rid-loading"},
        json={"model": "qwen38-api", "messages": []},
    )
    # B hiện hành đổi upstream 5xx thành 502; canonical code mới mang ngữ nghĩa
    # riêng. Đổi status là một migration độc lập, không trộn vào task này.
    assert response.status_code == 502
    assert response.json()["detail"]["canonical_code"] == "model_loading"
