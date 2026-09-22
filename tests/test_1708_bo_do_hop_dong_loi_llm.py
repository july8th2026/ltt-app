"""Bộ đo lỗi LLM phải đo contract mà không tự tạo tải production."""
from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from platform_core.llm.model_failure import model_failure


TOOL = Path(__file__).resolve().parents[1] / "tools" / "kiem_hop_dong_loi_llm.py"


def _load():
    spec = importlib.util.spec_from_file_location("kiem_hop_dong_loi_llm", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixture_cli_offline_sinh_json_markdown_va_matrix_day_du(tmp_path, monkeypatch):
    tool = _load()
    monkeypatch.setattr(
        tool.urllib.request,
        "urlopen",
        lambda *_a, **_k: pytest.fail("fixture khong duoc goi network"),
    )
    monkeypatch.setattr(
        tool,
        "_read_live_lines",
        lambda *_a, **_k: pytest.fail("fixture khong duoc doc log may"),
    )

    assert tool.main(["fixture", "--output", str(tmp_path)]) == 0
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "report.md").read_text(encoding="utf-8")

    assert report["mode"] == "fixture" and report["pass"] is True
    assert len(report["matrix"]) >= 33 * 4 * 2
    required = {
        "code",
        "protocol",
        "phase",
        "status",
        "canonical_code",
        "protocol_code",
        "action",
        "pass",
    }
    assert all(required <= row.keys() for row in report["matrix"])
    assert "| code | protocol | phase |" in markdown
    assert report["summary"]["failed"] == 0


def test_fixture_khong_phu_thuoc_tai_may(monkeypatch):
    tool = _load()
    first = tool.build_fixture_report()
    monkeypatch.setenv("LTT_FAKE_CPU_PERCENT", "100")
    monkeypatch.setenv("LTT_FAKE_GPU_PERCENT", "100")
    second = tool.build_fixture_report()
    assert first == second


def test_tiem_decoder_cu_413_thanh_context_lam_report_do():
    tool = _load()

    def old_decoder(_status, _headers, _body):
        return model_failure("context_window_exceeded", http_status=413)

    report = tool.build_fixture_report(decoder=old_decoder)
    assert report["pass"] is False
    mismatches = report["first_two_mismatches"]
    assert mismatches
    assert mismatches[0]["expected_canonical_code"] == "image_count_exceeded"
    assert mismatches[0]["canonical_code"] == "context_window_exceeded"


def test_live_chi_tong_hop_khong_chep_raw_prose_hoac_token():
    tool = _load()
    lines = [
        json.dumps({
            "canonical_code": "image_count_exceeded",
            "request_id": "rid-1",
            "action": "terminal",
            "raw_body": "SECRET RAW BODY",
            "token": "SECRET TOKEN",
        }),
        json.dumps({
            "canonical_code": "upstream_unknown",
            "request_id": "",
            "legacy": True,
            "contract_mismatch": True,
            "action": "unknown",
            "message": "SECRET PROVIDER PROSE",
        }),
    ]
    report = tool.analyze_live(lines, minutes=20)
    encoded = json.dumps(report)
    assert report["summary"] == {
        "events": 2,
        "request_id_present": 1,
        "request_id_coverage": 0.5,
        "unknown": 1,
        "legacy": 1,
        "mismatch": 1,
    }
    assert report["actions"] == {"terminal": 1, "unknown": 1}
    for secret in ("SECRET RAW BODY", "SECRET TOKEN", "SECRET PROVIDER PROSE"):
        assert secret not in encoded


def test_live_chi_doc_event_nam_trong_cua_so(tmp_path):
    tool = _load()
    log = tmp_path / "llm.jsonl"
    log.write_text(
        "\n".join(
            (
                json.dumps({
                    "timestamp": "2026-09-21T11:35:00Z",
                    "canonical_code": "rate_limited",
                    "request_id": "new",
                }),
                json.dumps({
                    "timestamp": "2026-09-21T10:00:00Z",
                    "canonical_code": "upstream_unknown",
                    "request_id": "old",
                }),
                json.dumps({"canonical_code": "internal_error"}),
            )
        ),
        encoding="utf-8",
    )
    now = datetime(2026, 9, 21, 11, 40, tzinfo=timezone.utc)
    lines = tool._read_live_lines([log], minutes=20, now=now)
    report = tool.analyze_live(lines, minutes=20)
    assert report["summary"]["events"] == 1
    assert report["codes"] == {"rate_limited": 1}


def test_live_doc_duoc_snapshot_counter_huu_han():
    tool = _load()
    report = tool.analyze_live(
        [json.dumps({
            "llm_error_total": 10,
            "llm_error_unknown_total": 2,
            "llm_error_legacy_total": 1,
            "llm_error_contract_mismatch_total": 0,
            "llm_error_request_id_missing_total": 1,
        })],
        minutes=20,
    )
    assert report["summary"] == {
        "events": 10,
        "request_id_present": 9,
        "request_id_coverage": 0.9,
        "unknown": 2,
        "legacy": 1,
        "mismatch": 0,
    }
    assert report["pass"] is True


def test_inject_chan_production_truoc_khi_goi_mang():
    tool = _load()
    called = []
    with pytest.raises(ValueError, match="production"):
        tool.run_inject(
            "https://app.lttstudios.com/api",
            token="test-token",
            transport=lambda *_a, **_k: called.append(True),
        )
    assert called == []


def test_inject_chan_ca_loopback_cong_production_may_a():
    tool = _load()
    with pytest.raises(ValueError, match="production"):
        tool.run_inject(
            "http://127.0.0.1:8100/api",
            token="test-token",
            transport=lambda *_a, **_k: pytest.fail("khong duoc goi mang"),
        )


def test_inject_loopback_chi_gui_model_gia_va_khong_lo_token():
    tool = _load()
    calls = []

    def transport(url, *, body, headers):
        calls.append((url, body, headers))
        return 404, {
            "error": {
                "code": "model_not_found",
                "ltt_error": {
                    "canonical_code": "model_not_found",
                    "protocol_code": "model_not_found",
                    "request_id": "rid-inject",
                    "recovery": "choose_model",
                },
            }
        }

    report = tool.run_inject(
        "http://127.0.0.1:18100/api",
        token="test-token",
        transport=transport,
    )
    assert report["mode"] == "inject"
    assert report["pass"] is True
    assert calls and all(call[1]["model"] == "__ltt_contract_missing__" for call in calls)
    assert all(len(json.dumps(call[1])) < 512 for call in calls)
    assert "test-token" not in json.dumps(report)


def test_inject_loi_mang_van_sinh_report_do_khong_lo_chi_tiet():
    tool = _load()

    def failed_transport(*_args, **_kwargs):
        raise OSError("SECRET NETWORK DETAIL")

    report = tool.run_inject(
        "http://127.0.0.1:18100/api",
        token="test-token",
        transport=failed_transport,
    )
    assert report["pass"] is False
    assert report["summary"]["failed"] == 3
    assert "SECRET NETWORK DETAIL" not in json.dumps(report)
