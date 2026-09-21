"""Runtime máy A giữ nguyên ModelFailure; policy key đọc code, không đọc cờ/prose."""
from __future__ import annotations

import json

import pytest

from llm_gateway.error_contract import error_spec, make_error
from platform_core.llm.model_failure import ModelFailure, decode_gateway_failure


def _failure(code: str, **optional) -> ModelFailure:
    spec = error_spec(code)
    return decode_gateway_failure(
        spec.status,
        {},
        json.dumps({"error": make_error(code, request_id="rid-runtime", **optional)}).encode(),
    )


def _prepared():
    from platform_core.runtime_noi_bo.luong import ChuanBi

    return ChuanBi(
        db=object(),
        user_id="user-01",
        tool_name="text.chat",
        duong="/v1/messages",
        than_gui={"model": "m"},
        request_id="rid-runtime",
        lease_id="lease-01",
        da_giu=1,
        token_vao_uoc=10,
        xin_ra=20,
        model_alias="m",
        executor=object(),
    )


@pytest.mark.parametrize(
    ("failure", "runtime_exception"),
    (
        (_failure("image_count_exceeded", field="images", limit=4, actual=6),
         "KhongMoDuoc"),
        (_failure("max_output_tokens_exceeded", field="max_output_tokens",
                  limit=4096, actual=8192), "KhongMoDuoc"),
        (_failure("context_window_exceeded", field="context", limit=100,
                  actual=120), "KhongMoDuoc"),
        (_failure("concurrency_limited", retry_after_s=17), "DangBan"),
        (_failure("upstream_timeout"), "KhongMoDuoc"),
        (_failure("upstream_unknown"), "KhongMoDuoc"),
        (_failure("request_cancelled"), "KhongMoDuoc"),
    ),
)
def test_mo_thuong_nguon_giu_nguyen_model_failure(
        monkeypatch, failure, runtime_exception):
    from platform_core.llm import luong_vlm
    from platform_core.public_api import metrics
    from platform_core.runtime_noi_bo import luong

    source = luong_vlm.KhongMoDuocLuong(failure=failure)
    monkeypatch.setattr(luong_vlm, "mo", lambda *args, **kwargs: (_ for _ in ()).throw(source))
    monkeypatch.setattr(luong, "hoan", lambda *args, **kwargs: None)
    monkeypatch.setattr(luong, "_nha_suat", lambda *args, **kwargs: None)
    monkeypatch.setattr(metrics, "increment", lambda *args, **kwargs: None)

    expected = getattr(luong, runtime_exception)
    with pytest.raises(expected) as caught:
        luong.mo_thuong_nguon(_prepared())

    assert caught.value.failure is failure
    assert caught.value.failure.canonical_code == failure.canonical_code
    assert (
        caught.value.failure.field,
        caught.value.failure.limit,
        caught.value.failure.actual,
        caught.value.failure.retry_after_s,
    ) == (failure.field, failure.limit, failure.actual, failure.retry_after_s)
    assert caught.value.__cause__ is source


def test_boolean_legacy_khong_duoc_bien_loi_anh_thanh_context():
    from platform_core.runtime_noi_bo.luong import KhongMoDuoc

    image = _failure("image_count_exceeded", field="images", limit=4, actual=6)
    error = KhongMoDuoc(failure=image)
    assert error.failure is image
    assert not error.qua_dai


@pytest.mark.parametrize(
    ("code", "penalized"),
    (
        ("provider_oom", True),
        ("upstream_unreachable", True),
        ("concurrency_limited", False),
        ("provider_overloaded", False),
        ("upstream_timeout", False),
        ("stream_idle_timeout", False),
        ("request_cancelled", False),
        ("upstream_unknown", True),
    ),
)
def test_policy_phat_khoa_chi_theo_canonical_code(code, penalized):
    failure = _failure(code)
    assert failure.penalizes_key is penalized


@pytest.mark.parametrize(
    "code",
    (
        "provider_oom",
        "invalid_request",
        "image_count_exceeded",
        "max_output_tokens_exceeded",
        "context_window_exceeded",
        "upstream_unknown",
    ),
)
def test_policy_retry_parser_khong_lan_sang_loi_khac(code):
    assert not _failure(code).retry_same_generation


def test_chi_tool_call_parse_failed_duoc_retry_mot_lan_o_tang_provider():
    assert _failure("tool_call_parse_failed").retry_same_generation
