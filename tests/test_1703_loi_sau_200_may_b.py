"""Quan sát lỗi terminal trong SSE mà không sửa byte của luồng thành công."""
from __future__ import annotations

import json

import pytest

from tests.test_250_llm_gateway import FakeUpstream, _client
from llm_gateway.upstream_errors import (
    MAX_SSE_FRAME_BYTES,
    UpstreamEventObserver,
    observe_upstream_events,
)


def _run(raw: bytes, chunks: list[bytes]):
    observer = UpstreamEventObserver(request_id="rid-stream")
    frames = []
    for chunk in chunks:
        frames.extend(observer.feed(chunk))
    frames.extend(observer.finish())
    return frames


def _failure(raw: bytes, chunks: list[bytes]) -> dict:
    failures = [frame.failure for frame in _run(raw, chunks) if frame.failure]
    assert len(failures) == 1
    return failures[0]


@pytest.mark.parametrize(("raw", "canonical"), (
    (b'event: error\ndata: {"type":"error","error":'
     b'{"type":"unavailable_error","code":503,"message":"private"}}\n\n',
     "model_loading"),
    (b'data: {"error":{"type":"server_error","code":500,'
     b'"message":"private"}}\n\n', "upstream_unknown"),
    (b'event: response.failed\ndata: {"type":"response.failed",'
     b'"response":{"error":{"code":"server_error",'
     b'"message":"private"}}}\n\n', "upstream_unknown"),
    (b'error: {"message":"private raw llama error"}\n\n',
     "upstream_unknown"),
))
def test_bon_hinh_dang_loi_terminal(raw, canonical):
    # Nguyên body, từng byte, và mọi vị trí chia đôi phải cùng một ngữ nghĩa.
    variants = [[raw], [bytes([byte]) for byte in raw]]
    variants.extend([[raw[:i], raw[i:]] for i in range(1, len(raw))])
    for chunks in variants:
        failure = _failure(raw, chunks)
        assert failure["canonical_code"] == canonical
        assert failure["request_id"] == "rid-stream"
        assert "private" not in json.dumps(failure)


def test_crlf_multiline_data_comment_va_utf8_chia_giua_code_point():
    raw = (
        b": keep-alive\r\n\r\n"
        b"event:error\r\n"
        b'data:{"error":\r\n'
        + 'data:{"type":"invalid_request_error","message":"bí mật"}}\r\n\r\n'.encode()
    )
    failure = _failure(raw, [bytes([byte]) for byte in raw])
    assert failure["canonical_code"] == "invalid_request"


@pytest.mark.parametrize("terminal", (
    b'data: {"choices":[{"delta":{"content":"xin"}}]}\n\n'
    b'data: [DONE]\n\n',
    b'event: message_start\ndata: {"type":"message_start"}\n\n'
    b'event: message_stop\ndata: {"type":"message_stop"}\n\n',
    b'event: response.output_text.delta\n'
    b'data: {"type":"response.output_text.delta","delta":"xin"}\n\n'
    b'event: response.completed\n'
    b'data: {"type":"response.completed","response":{"status":"completed"}}\n\n',
))
def test_luong_thanh_cong_giu_nguyen_tung_byte(terminal):
    frames = _run(terminal, [bytes([byte]) for byte in terminal])
    assert all(frame.failure is None for frame in frames)
    assert b"".join(frame.raw for frame in frames) == terminal


def test_eof_dot_ngot_truoc_terminal_thanh_stream_truncated():
    raw = b'data: {"choices":[{"delta":{"content":"nua cau"}}]}\n\n'
    frames = _run(raw, [raw])
    assert frames[0].raw == raw
    assert frames[-1].failure["canonical_code"] == "stream_truncated"


def test_gioi_han_ap_theo_tung_frame_khong_theo_network_chunk():
    comment = b":" + (b"x" * (MAX_SSE_FRAME_BYTES // 2)) + b"\n\n"
    raw = comment + comment + b"data: [DONE]\n\n"
    frames = _run(raw, [raw])
    assert all(frame.failure is None for frame in frames)
    assert b"".join(frame.raw for frame in frames) == raw

    observer = UpstreamEventObserver(request_id="rid-overflow")
    overflow = observer.feed(b"data: " + b"x" * MAX_SSE_FRAME_BYTES)
    assert overflow[0].failure["canonical_code"] == "upstream_protocol_error"


def test_event_loi_khong_phat_raw_ma_phat_envelope_an_toan():
    raw = b'error: {"message":"secret prompt C:/private/path"}\n\n'
    output = b"".join(observe_upstream_events(iter([raw]),
                                                  request_id="rid-safe"))
    assert output.startswith(b"event: error\ndata: ")
    assert b'"canonical_code":"upstream_unknown"' in output
    assert b'"request_id":"rid-safe"' in output
    assert b"secret prompt" not in output and b"private/path" not in output


def test_api_bat_terminal_error_sau_http_200():
    raw = (b'data: {"error":{"type":"unavailable_error","code":503,'
           b'"message":"secret model path"}}\n\n')
    client, _ = _client(up=FakeUpstream(khoi_stream=[raw]))
    response = client.post(
        "/v1/chat/completions",
        headers={"X-LTT-Request-Id": "rid-api-terminal"},
        json={"model": "qwen38-api", "messages": [], "stream": True},
    )
    assert response.status_code == 200
    assert b'"canonical_code":"model_loading"' in response.content
    assert b'"request_id":"rid-api-terminal"' in response.content
    assert b"secret model path" not in response.content


class _Closable:
    def __init__(self):
        self.close_count = 0
        self._chunks = iter([
            b'data: {"choices":[{"delta":{"content":"xin"}}]}\n\n',
            b'data: [DONE]\n\n',
        ])

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._chunks)

    def close(self):
        self.close_count += 1


def test_client_cancel_chi_dong_nguon_mot_lan_khong_bia_provider_failure(caplog):
    source = _Closable()
    stream = observe_upstream_events(source, request_id="rid-cancel")
    first = next(stream)
    assert b"delta" in first
    stream.close()
    stream.close()
    assert source.close_count == 1
    assert "client_disconnected" in caplog.text
    assert "upstream_unknown" not in caplog.text
