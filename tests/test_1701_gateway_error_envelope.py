"""May B phat ma loi v1 — mot hinh dang duy nhat (Task 13 da go khoa legacy)."""
from __future__ import annotations

import pytest

from llm_gateway import ngan_sach as NS
from llm_gateway.gioi_han import GioiHan
from llm_gateway.upstream import MA_DA_HUY, MA_HET_GIO, MA_KHONG_VOI_TOI
from tests.test_250_llm_gateway import (FakeUpstream, _cfg, _client,
                                        _tt_ban)


def _anh(url: str = "data:image/png;base64,QUJD") -> dict:
    return {"messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": url}},
    ]}]}


BASE = dict(max_input_tokens=10_000, max_output_tokens=100, max_images=4,
            max_image_bytes=1024, max_context=20_000, co_vision=True)


@pytest.mark.parametrize(("body", "overrides", "code", "field"), (
    (_anh(), {"co_vision": False}, "unsupported_modality", "images"),
    (_anh(), {"max_images": 0}, "image_count_exceeded", "images"),
    (_anh("http://127.0.0.1/image.png"), {}, "image_url_not_allowed", "image_url"),
    (_anh("data:image/png;base64," + "A" * 8000), {"max_image_bytes": 10},
     "image_too_large", "image_bytes"),
    ({"max_tokens": 101}, {}, "max_output_tokens_exceeded", "max_tokens"),
    ({"messages": [{"role": "user", "content": "x" * 1000}]},
     {"max_input_tokens": 10}, "input_tokens_exceeded", "input_tokens"),
    ({"messages": []}, {"max_context": 1},
     "context_window_exceeded", "context"),
))
def test_bay_chot_ngan_sach_co_ma_rieng(body, overrides, code, field):
    kwargs = {**BASE, **overrides}
    with pytest.raises(NS.VuotNganSach) as caught:
        NS.kiem_tra(body, **kwargs)
    assert caught.value.code == code
    assert caught.value.truong == field


def _assert_v1(response, code: str, request_id: str) -> dict:
    assert response.headers["X-LTT-Request-Id"] == request_id
    detail = response.json()["detail"]
    assert detail["schema_version"] == 1
    assert detail["canonical_code"] == code
    assert detail["request_id"] == request_id
    assert detail["message"]
    assert detail["retry"]
    assert detail["recovery"]
    return detail


def test_413_anh_chi_con_ma_v1_status_day_giu_nguyen():
    client, _ = _client(_cfg(max_images=0))
    response = client.post(
        "/v1/chat/completions",
        headers={"X-LTT-Request-Id": "rid-image-01"},
        json={"model": "qwen38-api", **_anh()},
    )
    assert response.status_code == 413
    detail = _assert_v1(response, "image_count_exceeded", "rid-image-01")
    assert detail["field"] == "images" and detail["limit"] == 0
    assert detail["actual"] == 1
    for khoa in ("legacy", "ly_do", "truong", "tran", "thay"):
        assert khoa not in detail, detail


def test_B_tu_tao_request_id_khi_client_khong_gui():
    client, _ = _client(_cfg(max_images=0))
    response = client.post(
        "/v1/chat/completions",
        json={"model": "qwen38-api", **_anh()},
    )
    request_id = response.headers["X-LTT-Request-Id"]
    assert request_id and response.json()["detail"]["request_id"] == request_id


def test_model_khong_co_co_typed_code_va_request_id():
    client, _ = _client()
    response = client.post(
        "/v1/chat/completions",
        headers={"X-LTT-Request-Id": "rid-model-404"},
        json={"model": "khong-co", "messages": []},
    )
    assert response.status_code == 404
    _assert_v1(response, "model_not_found", "rid-model-404")


def test_xac_thuc_sai_cung_co_typed_code_va_request_id_an_toan():
    client, _ = _client(_cfg(token="bi-mat"))
    response = client.post(
        "/v1/chat/completions",
        headers={
            "Authorization": "Bearer sai",
            "X-LTT-Request-Id": "rid-auth-01\r\nX-Fake: injected",
        },
        json={"model": "qwen38-api", "messages": []},
    )
    assert response.status_code == 401
    detail = response.json()["detail"]
    assert detail["canonical_code"] == "unauthorized"
    assert "\r" not in detail["request_id"] and "\n" not in detail["request_id"]
    assert response.headers["X-LTT-Request-Id"] == detail["request_id"]


def test_cong_day_va_gpu_ban_la_hai_ma_khac_nhau():
    full = GioiHan(max_dong_thoi=1)
    _phan_xu, held = full.cap_suat()
    assert held is not None
    try:
        client, _ = _client(gh=full)
        response = client.post(
            "/v1/chat/completions",
            headers={"X-LTT-Request-Id": "rid-full"},
            json={"model": "qwen38-api", "messages": []},
        )
        assert response.status_code == 429
        _assert_v1(response, "concurrency_limited", "rid-full")
    finally:
        held.tra()

    client, _ = _client(tt=_tt_ban())
    response = client.post(
        "/v1/chat/completions",
        headers={"X-LTT-Request-Id": "rid-busy"},
        json={"model": "qwen38-api", "messages": []},
    )
    assert response.status_code == 429
    _assert_v1(response, "provider_overloaded", "rid-busy")


@pytest.mark.parametrize(("upstream_code", "status", "canonical"), (
    (MA_DA_HUY, 499, "request_cancelled"),
    (MA_HET_GIO, 504, "upstream_timeout"),
    (MA_KHONG_VOI_TOI, 502, "upstream_unreachable"),
    (500, 502, "upstream_unknown"),
))
def test_loi_van_chuyen_co_ma_va_khong_lo_than_tho(upstream_code, status, canonical):
    raw = b"secret prompt C:/private/path VRAM=12345"
    client, _ = _client(up=FakeUpstream(ma=upstream_code, than=raw))
    response = client.post(
        "/v1/chat/completions",
        headers={"X-LTT-Request-Id": "rid-transport"},
        json={"model": "qwen38-api", "messages": []},
    )
    assert response.status_code == status
    _assert_v1(response, canonical, "rid-transport")
    assert "secret prompt" not in response.text
    assert "private/path" not in response.text
