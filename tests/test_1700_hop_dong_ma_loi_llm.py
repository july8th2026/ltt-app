"""Hop dong ma loi giua may B va may A.

Day la bang chan doc lap: neu registry bo sot, them thua, hoac doi recovery cua
mot loi thi test phai do. Message khong nam trong phep so sanh hanh vi vi cau chu
co the sua; code/retry/recovery moi la hop dong cua client.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest


EXPECTED = {
    "invalid_request": ("invalid_request", 400, "never", "none"),
    "unsupported_parameter": ("invalid_request", 400, "after_fix", "none"),
    "unsupported_modality": ("invalid_request", 400, "after_fix", "choose_model"),
    "model_not_found": ("model", 404, "after_fix", "choose_model"),
    "model_loading": ("availability", 503, "after_delay", "wait"),
    "request_body_too_large": ("transport", 413, "after_fix", "none"),
    "image_count_exceeded": ("image", 400, "after_fix", "offload_images"),
    "image_too_large": ("image", 400, "after_fix", "offload_images"),
    "image_url_not_allowed": ("image_security", 400, "after_fix", "replace_image"),
    "image_decode_failed": ("image", 400, "after_fix", "replace_image"),
    "input_tokens_exceeded": ("token", 400, "after_fix", "reduce_input"),
    "max_output_tokens_exceeded": ("token", 400, "after_fix", "reduce_output"),
    "context_window_exceeded": ("token", 400, "after_fix", "reduce_input"),
    "tool_call_parse_failed": ("generation", 502, "ambiguous", "none"),
    "structured_output_failed": ("generation", 502, "ambiguous", "none"),
    "unauthorized": ("auth", 401, "never", "reauthenticate"),
    "forbidden": ("auth", 403, "never", "none"),
    "insufficient_credit": ("billing", 409, "after_fix", "top_up"),
    "quota_exceeded": ("billing", 429, "after_fix", "wait"),
    "rate_limited": ("capacity", 429, "after_delay", "wait"),
    "concurrency_limited": ("capacity", 429, "after_delay", "wait"),
    "provider_overloaded": ("capacity", 503, "after_delay", "wait"),
    "upstream_timeout": ("transport", 504, "ambiguous", "report_request_id"),
    "upstream_unreachable": ("transport", 502, "after_delay", "retry_same_request"),
    "provider_oom": ("provider", 503, "after_fix", "report_request_id"),
    "request_cancelled": ("lifecycle", 499, "never", "none"),
    "stream_idle_timeout": ("stream", 504, "ambiguous", "report_request_id"),
    "stream_truncated": ("stream", 502, "ambiguous", "report_request_id"),
    "malformed_upstream_response": ("protocol", 502, "ambiguous", "report_request_id"),
    "empty_response": ("protocol", 502, "ambiguous", "report_request_id"),
    "upstream_protocol_error": ("protocol", 502, "ambiguous", "report_request_id"),
    "internal_error": ("internal", 500, "after_delay", "report_request_id"),
    "upstream_unknown": ("unknown", 502, "ambiguous", "report_request_id"),
}


def test_registry_co_dung_33_ma_va_dung_ngu_nghia():
    from llm_gateway.error_contract import ERROR_SPECS

    actual = {
        code: (spec.category, spec.status, spec.retry, spec.recovery)
        for code, spec in ERROR_SPECS.items()
    }
    assert actual == EXPECTED


def test_envelope_v1_co_du_truong_bat_buoc_va_chi_tiet_tuy_chon():
    from llm_gateway.error_contract import make_error

    body = make_error(
        "image_count_exceeded",
        request_id="req_contract_01",
        field="images",
        limit=4,
        actual=6,
        retry_after_s=7,
        provider_type="invalid_request_error",
        provider_code="image_limit",
        upstream_status=413,
    )
    assert body == {
        "schema_version": 1,
        "canonical_code": "image_count_exceeded",
        "category": "image",
        "message": "Too many images in one request.",
        "retry": "after_fix",
        "recovery": "offload_images",
        "request_id": "req_contract_01",
        "field": "images",
        "limit": 4,
        "actual": 6,
        "retry_after_s": 7,
        "provider_type": "invalid_request_error",
        "provider_code": "image_limit",
        "upstream_status": 413,
    }


def test_envelope_khong_bia_code_la_va_khong_nhap_cac_loi_413():
    from llm_gateway.error_contract import error_spec, make_error

    with pytest.raises(KeyError, match="not registered"):
        error_spec("context_that_co_le")
    with pytest.raises(KeyError, match="not registered"):
        make_error("context_that_co_le", request_id="req_unknown")

    assert error_spec("request_body_too_large").code != "context_window_exceeded"
    assert error_spec("image_count_exceeded").code != "input_tokens_exceeded"
    assert error_spec("max_output_tokens_exceeded").recovery == "reduce_output"


def test_module_hop_dong_chi_dung_thu_vien_chuan():
    path = Path(__file__).resolve().parents[1] / "llm_gateway" / "error_contract.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    assert imports <= {"__future__", "dataclasses", "typing"}
