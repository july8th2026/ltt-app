"""Máy A đọc một hợp đồng lỗi cho cả sync và stream, không đoán từ status/prose."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from llm_gateway.error_contract import make_error
from platform_core.llm.cong_vlm import CongVlm, VuotNganSachError
from platform_core.llm.luong_vlm import KhongMoDuocLuong
from platform_core.llm.model_failure import (
    ModelFailure,
    decode_gateway_failure,
    failure_decode_counters,
)


V1 = {
    "schema_version": 1,
    "canonical_code": "image_count_exceeded",
    "category": "image",
    "message": "untrusted provider prose",
    "retry": "after_fix",
    "recovery": "offload_images",
    "request_id": "rid-body-01",
    "field": "images",
    "limit": 4,
    "actual": 6,
}


def _decode(payload, *, status=413, headers=None) -> ModelFailure:
    return decode_gateway_failure(
        status,
        headers or {},
        json.dumps(payload).encode(),
    )


def test_v1_sync_detail_va_stream_error_tao_cung_model_failure():
    sync = _decode({"detail": V1})
    stream = _decode({"error": V1})
    direct = _decode(V1)
    assert sync == stream == direct
    assert sync.canonical_code == "image_count_exceeded"
    assert (sync.field, sync.limit, sync.actual) == ("images", 4, 6)
    assert sync.message == "Too many images in one request."
    assert "untrusted provider prose" not in str(sync)


@pytest.mark.parametrize(
    ("detail", "canonical"),
    (
        ({"truong": "images", "tran": 4, "thay": 6}, "image_count_exceeded"),
        ({"truong": "image_url", "tran": 0, "thay": 1}, "image_url_not_allowed"),
        ({"truong": "image_bytes", "tran": 10, "thay": 11}, "image_too_large"),
        ({"truong": "max_tokens", "tran": 100, "thay": 101}, "max_output_tokens_exceeded"),
        ({"truong": "input_tokens", "tran": 100, "thay": 101}, "input_tokens_exceeded"),
        ({"truong": "context", "tran": 100, "thay": 101}, "context_window_exceeded"),
    ),
)
def test_legacy_chi_anh_xa_theo_field_chinh_xac(detail, canonical):
    failure = _decode({"detail": detail})
    assert failure.canonical_code == canonical
    assert failure.field == detail["truong"]
    assert failure.limit == detail["tran"]
    assert failure.actual == detail["thay"]


@pytest.mark.parametrize(
    "payload",
    (
        {"detail": "context window exceeded"},
        {"error": {"message": "context length and images exceeded"}},
        {"detail": {"schema_version": 1, "canonical_code": "future_error", "message": "context"}},
        b"<html>context window exceeded</html>",
    ),
)
def test_413_khong_bang_chung_typed_thi_unknown(payload):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    failure = decode_gateway_failure(413, {}, body)
    assert failure.canonical_code == "upstream_unknown"
    assert not failure.is_context_limit


def test_retry_after_va_request_id_uu_tien_body_da_validate_roi_header():
    failure = _decode(
        V1,
        status=429,
        headers={"Retry-After": "17", "X-LTT-Request-Id": "rid-header"},
    )
    assert failure.request_id == "rid-body-01"
    assert failure.retry_after_s == 17

    invalid_body_id = {**V1, "request_id": "bad\r\nid"}
    fallback = _decode(
        invalid_body_id,
        headers={"x-ltt-request-id": "rid-header"},
    )
    assert fallback.request_id == "rid-header"


def test_import_decoder_khong_keo_web_stack():
    code = (
        "import sys; import platform_core.llm.model_failure; "
        "assert 'fastapi' not in sys.modules; assert 'httpx' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_legacy_counter_tang_nhung_v1_khong_tang():
    before = failure_decode_counters()["legacy"]
    _decode({"detail": {"truong": "images", "tran": 4, "thay": 6}})
    _decode(V1)
    assert failure_decode_counters()["legacy"] == before + 1


def _stream_http_failure(
    monkeypatch,
    *,
    status: int,
    payload: dict,
    headers: dict | None = None,
    calls: list | None = None,
) -> KhongMoDuocLuong:
    """Đi qua đúng cửa `luong_vlm.mo`, không chỉ gọi decoder trực tiếp."""
    import httpx

    from platform_core import api_keys, api_pool, providers
    from platform_core.llm import luong_vlm

    body = json.dumps(payload).encode()
    response_headers = dict(headers or {})
    monkeypatch.setattr(
        api_pool,
        "chon_key",
        lambda db, **kwargs: type("K", (), {"base_url": "http://b"})(),
    )
    monkeypatch.setattr(api_pool, "danh_dau_loi", lambda *args, **kwargs: None)
    monkeypatch.setattr(api_keys, "lay_credential", lambda db, key: "secret")
    monkeypatch.setattr(providers, "get", lambda provider: None)

    class Response:
        status_code = status
        headers = response_headers

        @staticmethod
        def iter_raw():
            yield body

    class Context:
        def __enter__(self):
            return Response()

        def __exit__(self, *args):
            return False

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def stream(self, *args, **kwargs):
            if calls is not None:
                calls.append((args, kwargs))
            return Context()

        def close(self):
            pass

    monkeypatch.setattr(httpx, "Client", Client)
    with pytest.raises(KhongMoDuocLuong) as caught:
        luong_vlm.mo(None, duong="/v1/messages", than={"model": "m"})
    return caught.value


def test_sync_va_stream_dung_cung_decoder_typed(monkeypatch):
    envelope = make_error(
        "image_count_exceeded",
        request_id="rid-shared",
        field="images",
        limit=4,
        actual=6,
    )
    payload = {"error": envelope}
    headers = {"X-LTT-Request-Id": "rid-shared"}

    client = CongVlm(goi=lambda *args, **kwargs: (413, payload, headers))
    with pytest.raises(VuotNganSachError) as sync:
        client.chat(model="m", messages=[])
    stream = _stream_http_failure(monkeypatch, status=413, payload=payload, headers=headers)

    assert sync.value.failure == stream.failure
    assert stream.failure.canonical_code == "image_count_exceeded"
    assert not stream.qua_dai


def test_stream_413_khong_typed_khong_duoc_bien_thanh_context(monkeypatch):
    error = _stream_http_failure(
        monkeypatch,
        status=413,
        payload={"detail": "context window exceeded"},
    )
    assert error.failure.canonical_code == "upstream_unknown"
    assert not error.failure.is_context_limit
    assert not error.qua_dai


def test_chi_tool_call_parse_failed_typed_moi_duoc_retry_mot_lan(monkeypatch):
    calls: list = []
    error = _stream_http_failure(
        monkeypatch,
        status=502,
        payload={"error": make_error("tool_call_parse_failed", request_id="rid-parser")},
        calls=calls,
    )
    assert error.failure.canonical_code == "tool_call_parse_failed"
    assert len(calls) == 2


def test_prose_parser_legacy_chi_telemetry_khong_duoc_retry(monkeypatch):
    calls: list = []
    error = _stream_http_failure(
        monkeypatch,
        status=502,
        payload={"error": {"message": "Failed to parse tool call arguments as JSON"}},
        calls=calls,
    )
    assert error.failure.canonical_code == "upstream_unknown"
    assert len(calls) == 1
