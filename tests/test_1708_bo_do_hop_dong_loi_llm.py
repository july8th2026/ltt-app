"""Bộ đo lỗi LLM phải đo contract mà không tự tạo tải production."""
from __future__ import annotations

import importlib.util
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pytest

from llm_gateway.upstream_errors import observe_upstream_events
from platform_core.llm.model_failure import (
    decode_gateway_failure,
    failure_telemetry_reset_for_tests,
    failure_telemetry_snapshot,
    model_failure,
)


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


def test_help_in_duoc_tren_console_windows_cp1252():
    tool = _load()
    help_text = tool._parser().format_help()
    encoded = help_text.encode("cp1252", errors="strict")
    assert b"fixture" in encoded
    assert b"live" in encoded
    assert b"inject" in encoded


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
            "event": "llm_model_error",
            "canonical_code": "image_count_exceeded",
            "request_id": "rid-1",
            "action": "terminal",
            "raw_body": "SECRET RAW BODY",
            "token": "SECRET TOKEN",
        }),
        json.dumps({
            "event": "llm_model_error",
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


def test_live_bo_qua_jsonl_process_khong_phai_event_model():
    tool = _load()
    lines = [
        json.dumps({"ts": "2026-09-22T01:00:00Z", "message": "server started"}),
        json.dumps({"timestamp": "2026-09-22T01:00:01Z", "status": 200}),
    ]
    report = tool.analyze_live(lines, minutes=20)
    assert report["summary"]["events"] == 0
    assert report["pass"] is False


def test_live_dem_event_tung_process_khong_de_counter_ghi_de():
    tool = _load()
    lines = [
        json.dumps({
            "event": "llm_model_error",
            "source": "A",
            "canonical_code": "rate_limited",
            "request_id": "process-1",
            "llm_error_total": 1,
        }),
        json.dumps({
            "event": "llm_model_error",
            "source": "A",
            "canonical_code": "server_overloaded",
            "request_id": "process-2",
            "llm_error_total": 1,
        }),
    ]
    report = tool.analyze_live(lines, minutes=20)
    assert report["summary"]["events"] == 2
    assert report["summary"]["request_id_coverage"] == 1.0
    assert report["codes"] == {"rate_limited": 1, "server_overloaded": 1}


def test_live_chi_doc_event_nam_trong_cua_so(tmp_path):
    tool = _load()
    log = tmp_path / "llm.jsonl"
    log.write_text(
        "\n".join(
            (
                json.dumps({
                    "event": "llm_model_error",
                    "timestamp": "2026-09-21T11:35:00Z",
                    "canonical_code": "rate_limited",
                    "request_id": "new",
                }),
                json.dumps({
                    "event": "llm_model_error",
                    "timestamp": "2026-09-21T10:00:00Z",
                    "canonical_code": "upstream_unknown",
                    "request_id": "old",
                }),
                json.dumps({
                    "event": "llm_model_error",
                    "canonical_code": "internal_error",
                }),
            )
        ),
        encoding="utf-8",
    )
    now = datetime(2026, 9, 21, 11, 40, tzinfo=timezone.utc)
    lines = tool._read_live_lines([log], minutes=20, now=now)
    report = tool.analyze_live(lines, minutes=20)
    assert report["summary"]["events"] == 1
    assert report["codes"] == {"rate_limited": 1}


def test_live_mac_dinh_doc_dung_thu_muc_log_va_ten_process_a(tmp_path, monkeypatch):
    server = tmp_path / "ltt-server.jsonl"
    worker = tmp_path / "ltt-job-worker-2.jsonl"
    unrelated = tmp_path / "audit.jsonl"
    for path in (server, worker, unrelated):
        path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("LTT_LOGS_DIR", str(tmp_path))
    monkeypatch.delenv("LTT_LLM_CONTRACT_LOGS", raising=False)

    paths = _load()._default_live_paths()

    assert server in paths
    assert worker in paths
    assert unrelated not in paths


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


def test_inject_doc_duoc_envelope_v1_truc_tiep_cua_gateway_b():
    tool = _load()

    def transport(_url, *, body, headers):
        assert body["model"] == "__ltt_contract_missing__"
        assert headers["Authorization"] == "Bearer test-token"
        return 404, {
            "detail": {
                "schema_version": 1,
                "canonical_code": "model_not_found",
                "category": "model",
                "message": "The requested model is not available.",
                "retry": "after_fix",
                "recovery": "choose_model",
                "request_id": "rid-b-direct",
            }
        }

    report = tool.run_inject(
        "http://127.0.0.1:18100",
        token="test-token",
        transport=transport,
    )

    assert report["pass"] is True
    assert {row["canonical_code"] for row in report["matrix"]} == {
        "model_not_found"
    }


def test_http_transport_dung_user_agent_ro_rang_cho_cloudflare(monkeypatch):
    tool = _load()
    requests = []

    class Response:
        status = 404

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        @staticmethod
        def read():
            return b'{"detail":{"canonical_code":"model_not_found"}}'

    def urlopen(request, *, timeout):
        requests.append((request, timeout))
        return Response()

    monkeypatch.setattr(tool.urllib.request, "urlopen", urlopen)
    status, _body = tool._http_transport(
        "https://app.lttstudios.com/api/v1/messages",
        body={"model": "__ltt_contract_missing__"},
        headers={"Authorization": "Bearer test-token"},
    )

    assert status == 404
    assert requests[0][0].get_header("User-agent") == (
        "ltt-llm-contract-monitor/1.0"
    )


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


def _event_records(caplog):
    events = []
    for record in caplog.records:
        try:
            event = json.loads(record.getMessage())
        except ValueError:
            continue
        if event.get("event") == "llm_model_error":
            events.append(event)
    return events


def test_telemetry_a_known_legacy_unknown_mismatch_co_du_truong_va_khong_lo_secret(
    caplog,
):
    failure_telemetry_reset_for_tests()
    caplog.set_level(logging.WARNING)
    secret = "SECRET prompt data:image/png;base64,AAA Authorization=Bearer credential"

    known = {
        "schema_version": 1,
        "canonical_code": "rate_limited",
        "request_id": "rid-known",
        "message": secret,
    }
    legacy = {"detail": {"truong": "images", "tran": 4, "thay": 6,
                           "request_id": "rid-legacy", "raw_body": secret}}
    unknown = {"error": {"message": secret}}
    mismatch = {
        "detail": {
            "schema_version": 1,
            "canonical_code": "future_private_error",
            "token": secret,
        }
    }
    for payload in (known, legacy, unknown, mismatch):
        decode_gateway_failure(502, {}, json.dumps(payload).encode())

    events = _event_records(caplog)
    assert len(events) == 4
    required = {
        "request_id", "gateway_code", "canonical_code", "protocol_code",
        "category", "http_status", "upstream_status", "protocol",
        "stream_phase", "retry", "recovery", "model", "elapsed_ms",
        "action", "source", "legacy", "contract_mismatch",
    }
    assert all(required <= event.keys() for event in events)
    assert [event["action"] for event in events] == [
        "retry", "legacy", "unknown", "unknown",
    ]
    assert events[-1]["contract_mismatch"] is True
    assert events[-1]["llm_error_total"] == 4
    assert events[-1]["llm_error_contract_mismatch_total"] == 1
    assert secret not in caplog.text

    snapshot = failure_telemetry_snapshot()
    assert snapshot["llm_error_total"] == 4
    assert snapshot["llm_error_unknown_total"] == 2
    assert snapshot["llm_error_legacy_total"] == 1
    assert snapshot["llm_error_contract_mismatch_total"] == 1
    assert snapshot["llm_error_request_id_missing_total"] == 2
    assert snapshot["labels"]
    assert all(
        set(row) == {
            "canonical_code", "model", "endpoint", "stream_phase",
            "protocol", "action", "count",
        }
        for row in snapshot["labels"]
    )
    assert "request_id" not in json.dumps(snapshot["labels"])
    assert "message" not in json.dumps(snapshot["labels"])


class _DisconnectingStream:
    def __init__(self):
        self._chunks = iter([b'data: {"choices":[{"delta":{"content":"x"}}]}\n\n'])

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._chunks)

    def close(self):
        return None


def test_client_disconnect_log_only_co_cau_truc_va_khong_bia_loi_provider(caplog):
    caplog.set_level(logging.WARNING)
    stream = observe_upstream_events(
        _DisconnectingStream(),
        request_id="rid-disconnect",
    )
    next(stream)
    stream.close()
    events = _event_records(caplog)
    assert len(events) == 1
    event = events[0]
    assert event["canonical_code"] == "client_disconnected"
    assert event["action"] == "client_disconnected"
    assert event["request_id"] == "rid-disconnect"
    assert event["source"] == "B"
    assert event["counted"] is False
    assert "upstream_unknown" not in caplog.text


def test_live_doc_event_llm_long_trong_process_jsonl():
    tool = _load()
    inner = {
        "event": "llm_model_error",
        "timestamp": "2026-09-22T01:00:00+00:00",
        "source": "A",
        "canonical_code": "rate_limited",
        "request_id": "rid-nested",
        "action": "retry",
        "counted": True,
    }
    outer = {
        "ts": "2026-09-22T01:00:00+00:00",
        "message": json.dumps(inner),
        "token": "SECRET OUTER TOKEN",
    }
    report = tool.analyze_live([json.dumps(outer)], minutes=20)
    assert report["summary"]["events"] == 1
    assert report["codes"] == {"rate_limited": 1}
    assert report["actions"] == {"retry": 1}
    assert "SECRET OUTER TOKEN" not in json.dumps(report)


def test_gateway_b_ghi_loi_typed_voi_label_huu_han_khong_chep_prompt(caplog):
    from llm_gateway.error_telemetry import B_TELEMETRY
    from tests.test_250_llm_gateway import FakeUpstream, _client

    B_TELEMETRY.reset_for_tests()
    caplog.set_level(logging.WARNING)
    secret = "SECRET prompt data:image/png;base64,AAA Authorization=Bearer credential"
    client, _ = _client(up=FakeUpstream())
    response = client.post(
        "/v1/chat/completions",
        headers={"X-LTT-Request-Id": "rid-b-known"},
        json={"model": "untrusted-model-name", "messages": [
            {"role": "user", "content": secret}
        ]},
    )
    assert response.status_code == 404
    events = [event for event in _event_records(caplog) if event["source"] == "B"]
    assert len(events) == 1
    assert events[0]["canonical_code"] == "model_not_found"
    assert events[0]["protocol"] == "chat"
    assert events[0]["model"] == "other"
    assert events[0]["action"] == "terminal"
    assert secret not in caplog.text
    snapshot = B_TELEMETRY.snapshot()
    assert snapshot["llm_error_total"] == 1
    assert snapshot["labels"][0]["model"] == "other"


def test_server_a_ghi_giao_thuc_public_nhung_khong_dem_lap(caplog):
    from server.api import streaming

    failure_telemetry_reset_for_tests()
    caplog.set_level(logging.WARNING)
    failure = model_failure(
        "image_count_exceeded",
        http_status=400,
        request_id="rid-public",
        field="images",
        limit=4,
        actual=6,
    )
    streaming._observe_public_model_failure(
        failure,
        duong="/v1/messages",
        model="ltt-3.8",
        elapsed_ms=17,
    )
    event = _event_records(caplog)[-1]
    assert event["source"] == "A"
    assert event["protocol"] == "messages"
    assert event["endpoint"] == "messages"
    assert event["model"] == "ltt-3.8"
    assert event["protocol_code"] == "invalid_request_error"
    assert event["elapsed_ms"] == 17
    assert failure_telemetry_snapshot()["llm_error_total"] == 0
