"""Đo contract lỗi model bằng fixture, log thụ động hoặc request lỗi rẻ."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable, Literal
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_gateway.error_contract import ERROR_SPECS
from platform_core.llm.model_failure import (ModelFailure,
                                             decode_gateway_failure,
                                             model_failure)
from server.api.su_kien_loi import render_model_failure


PROTOCOL_PATHS = {
    "rfc9457": "/api/v1/jobs",
    "anthropic": "/v1/messages",
    "chat": "/v1/chat/completions",
    "responses": "/v1/responses",
}
PHASES: tuple[Literal["before_headers", "after_headers"], ...] = (
    "before_headers",
    "after_headers",
)
OPERATOR_USER_AGENT = "ltt-llm-contract-monitor/1.0"

# Golden adapter chép rõ từ spec, độc lập với `_MODEL_PROTOCOL` của renderer.
EXPECTED_PROTOCOL = {
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


def _fixture_failure(code: str) -> ModelFailure:
    return model_failure(
        code,
        http_status=599,
        request_id="fixture-request-id",
        field="fixture-field",
        limit=4,
        actual=6,
        retry_after_s=17,
    )


def _body_from_rendered(rendered) -> tuple[int, dict]:
    if isinstance(rendered, bytes):
        data = next(
            line[6:]
            for line in rendered.decode("utf-8").splitlines()
            if line.startswith("data: ")
        )
        return 200, json.loads(data)
    return int(rendered.status_code), json.loads(rendered.body)


def _find_extension(value) -> dict:
    if isinstance(value, dict):
        extension = value.get("ltt_error")
        if isinstance(extension, dict):
            return extension
        if (
            value.get("schema_version") == 1
            and isinstance(value.get("canonical_code"), str)
            and value["canonical_code"].strip()
        ):
            return value
        for child in value.values():
            found = _find_extension(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_extension(child)
            if found:
                return found
    return {}


#: Anthropic SAU 200: bận/hết giờ mang `overloaded_error` để Claude Code tự
#: retry (lý do + nguồn: `server/api/su_kien_loi._ANTHROPIC_SAU_200_QUA_TAI`).
#: Gõ lại ở đây CÓ CHỦ Ý — golden độc lập với renderer.
ANTHROPIC_SAU_200_QUA_TAI = frozenset({
    "concurrency_limited", "provider_overloaded", "model_loading",
    "upstream_timeout", "stream_idle_timeout",
})


def _expected_protocol(code: str, protocol: str,
                       phase: str = "before_headers") -> str:
    if protocol == "rfc9457":
        return code
    if (protocol == "anthropic" and phase == "after_headers"
            and code in ANTHROPIC_SAU_200_QUA_TAI):
        return "overloaded_error"
    return EXPECTED_PROTOCOL[code][0 if protocol == "anthropic" else 1]


def _renderer_row(
    code: str,
    protocol: str,
    phase: Literal["before_headers", "after_headers"],
) -> dict:
    path = PROTOCOL_PATHS[protocol]
    failure = _fixture_failure(code)
    rendered = render_model_failure(
        path,
        failure,
        phase=phase,
        stream=phase == "after_headers",
    )
    status, body = _body_from_rendered(rendered)
    extension = _find_extension(body)
    expected_protocol = _expected_protocol(code, protocol, phase)
    expected_status = 200 if phase == "after_headers" else ERROR_SPECS[code].status
    if phase == "before_headers" and protocol == "anthropic" and code == (
        "provider_overloaded"
    ):
        expected_status = 529
    actual_code = str(extension.get("canonical_code") or "")
    protocol_code = str(extension.get("protocol_code") or "")
    passed = (
        status == expected_status
        and actual_code == code
        and protocol_code == expected_protocol
    )
    return {
        "code": code,
        "protocol": protocol,
        "phase": phase,
        "status": status,
        "expected_status": expected_status,
        "canonical_code": actual_code,
        "expected_canonical_code": code,
        "protocol_code": protocol_code,
        "expected_protocol_code": expected_protocol,
        "action": ERROR_SPECS[code].recovery,
        "pass": passed,
    }


def _decoder_row(decoder: Callable) -> dict:
    """Thân HÌNH DẠNG legacy ở 413 phải fail-closed `upstream_unknown` (Task 13).

    Đây cũng là phép đột biến: decoder nào còn suy "413 ⇒ context" hay đọc
    `{truong, tran, thay}` thành mã cụ thể sẽ làm dòng này đỏ.
    """
    body = json.dumps(
        {
            "detail": {
                "ly_do": "fixture only",
                "truong": "images",
                "tran": 4,
                "thay": 6,
            }
        }
    ).encode("utf-8")
    failure = decoder(413, {"X-LTT-Request-Id": "fixture-request-id"}, body)
    expected = "upstream_unknown"
    return {
        "code": expected,
        "protocol": "gateway_legacy_fail_closed",
        "phase": "decode",
        "status": 413,
        "expected_status": 413,
        "canonical_code": failure.canonical_code,
        "expected_canonical_code": expected,
        "protocol_code": failure.canonical_code,
        "expected_protocol_code": expected,
        "action": failure.recovery,
        "pass": failure.canonical_code == expected,
    }


def build_fixture_report(*, decoder: Callable = decode_gateway_failure) -> dict:
    """Replay corpus tổng hợp; không đọc log, network hoặc trạng thái máy."""
    if set(EXPECTED_PROTOCOL) != set(ERROR_SPECS):
        missing = sorted(set(ERROR_SPECS) - set(EXPECTED_PROTOCOL))
        extra = sorted(set(EXPECTED_PROTOCOL) - set(ERROR_SPECS))
        raise RuntimeError(f"protocol golden drift: missing={missing}, extra={extra}")
    matrix = [
        _renderer_row(code, protocol, phase)
        for code in ERROR_SPECS
        for protocol in PROTOCOL_PATHS
        for phase in PHASES
    ]
    matrix.append(_decoder_row(decoder))
    failed = [row for row in matrix if not row["pass"]]
    return {
        "mode": "fixture",
        "pass": not failed,
        "summary": {"rows": len(matrix), "passed": len(matrix) - len(failed),
                    "failed": len(failed)},
        "first_two_mismatches": failed[:2],
        "matrix": matrix,
    }


def _event_from_line(line: str) -> dict | None:
    """Đọc JSONL của A, JSON message của B, không trả phần vỏ có thể chứa secret."""
    try:
        outer = json.loads(line)
    except (TypeError, ValueError):
        start = str(line).find("{")
        if start < 0:
            return None
        try:
            outer = json.loads(str(line)[start:])
        except ValueError:
            return None
    if not isinstance(outer, dict):
        return None
    message = outer.get("message")
    if isinstance(message, str):
        start = message.find("{")
        if start >= 0:
            try:
                nested = json.loads(message[start:])
            except ValueError:
                nested = None
            if isinstance(nested, dict) and (
                nested.get("event") == "llm_model_error"
                or "llm_error_total" in nested
            ):
                if not any(key in nested for key in ("timestamp", "time", "ts")):
                    for key in ("timestamp", "time", "ts"):
                        if key in outer:
                            nested[key] = outer[key]
                            break
                return nested
    if outer.get("event") == "llm_model_error" or "llm_error_total" in outer:
        return outer
    return None


def analyze_live(lines: Iterable[str], *, minutes: int) -> dict:
    """Chỉ giữ counter hữu hạn; tuyệt đối không trả raw line/message/token."""
    codes: Counter[str] = Counter()
    actions: Counter[str] = Counter()
    snapshots: dict[str, dict] = {}
    events = request_ids = unknown = legacy = mismatch = 0
    for line in lines:
        event = _event_from_line(line)
        if event is None:
            continue
        is_error_event = event.get("event") == "llm_model_error"
        if "llm_error_total" in event and not is_error_event:
            source = str(event.get("source") or "default")
            snapshots[source] = event
            continue
        action = str(event.get("action") or "")
        if not bool(event.get("counted", True)):
            if action == "client_disconnected":
                actions[action] += 1
            continue
        events += 1
        code = str(event.get("canonical_code") or "")
        if code:
            codes[code] += 1
        if action:
            actions[action] += 1
        request_ids += bool(event.get("request_id"))
        unknown += code == "upstream_unknown"
        legacy += bool(event.get("legacy"))
        mismatch += bool(event.get("contract_mismatch"))
    # A normal telemetry event also carries a cumulative counter snapshot.  Do
    # not replace event counts with that value: machine A has multiple worker
    # processes whose counters all start at zero.  Counter-only records are a
    # fallback for exporters that do not retain individual events.
    if snapshots and events == 0:
        def total(key: str) -> int:
            values = []
            for snapshot in snapshots.values():
                value = snapshot.get(key, 0)
                values.append(
                    int(value)
                    if isinstance(value, (int, float)) and not isinstance(value, bool)
                    else 0
                )
            return sum(max(0, value) for value in values)

        events = total("llm_error_total")
        unknown = total("llm_error_unknown_total")
        legacy = total("llm_error_legacy_total")
        mismatch = total("llm_error_contract_mismatch_total")
        missing_request_id = total("llm_error_request_id_missing_total")
        request_ids = max(0, events - missing_request_id)
    coverage = request_ids / events if events else 0.0
    summary = {
        "events": events,
        "request_id_present": request_ids,
        "request_id_coverage": coverage,
        "unknown": unknown,
        "legacy": legacy,
        "mismatch": mismatch,
    }
    return {
        "mode": "live",
        "minutes": int(minutes),
        "pass": events > 0 and mismatch == 0,
        "summary": summary,
        "codes": dict(sorted(codes.items())),
        "actions": dict(sorted(actions.items())),
        "first_two_mismatches": [],
        "matrix": [],
    }


def _production_host(hostname: str) -> bool:
    host = (hostname or "").lower().rstrip(".")
    return host == "lttstudios.com" or host.endswith(".lttstudios.com")


def _production_target(parsed) -> bool:
    host = (parsed.hostname or "").lower()
    if _production_host(host):
        return True
    if host in {"127.0.0.1", "localhost", "::1"} and parsed.port == 8100:
        return True
    return host == "192.168.2.66" and parsed.port == 8299


def _http_transport(url: str, *, body: dict, headers: dict) -> tuple[int, dict]:
    data = json.dumps(body, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            **headers,
            "Content-Type": "application/json",
            "User-Agent": OPERATOR_USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return int(response.status), json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return int(exc.code), json.loads(exc.read())


def run_inject(
    base_url: str,
    *,
    token: str,
    allow_production: bool = False,
    transport: Callable = _http_transport,
) -> dict:
    """Gửi ba request model giả, nhỏ và dừng trước GPU/model lookup."""
    parsed = urlparse(base_url)
    if _production_target(parsed) and not allow_production:
        raise ValueError("production is blocked; see runbook before explicit override")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base URL must be an absolute HTTP(S) URL")
    if not token:
        raise ValueError("inject requires LTT_LLM_CONTRACT_TOKEN")

    cases = (
        ("anthropic", "/v1/messages", {"messages": [], "max_tokens": 1}),
        ("chat", "/v1/chat/completions", {"messages": [], "max_tokens": 1}),
        ("responses", "/v1/responses", {"input": [], "max_output_tokens": 1}),
    )
    matrix = []
    for protocol, path, payload in cases:
        body = {"model": "__ltt_contract_missing__", **payload}
        request_headers = {"Authorization": f"Bearer {token}"}
        if protocol == "chat":
            request_headers["Idempotency-Key"] = uuid.uuid4().hex
        transport_failed = False
        try:
            status, response = transport(
                base_url.rstrip("/") + path,
                body=body,
                headers=request_headers,
            )
        except (OSError, TimeoutError, ValueError, urllib.error.URLError):
            # Không chép exception: URL/proxy stack có thể mang credential hoặc
            # chi tiết hạ tầng. Hình dạng report vẫn đầy đủ và đỏ rõ ràng.
            status, response, transport_failed = 0, {}, True
        extension = _find_extension(response)
        canonical = str(extension.get("canonical_code") or "")
        protocol_code = str(extension.get("protocol_code") or "")
        row = {
            "code": "model_not_found",
            "protocol": protocol,
            "phase": "before_headers",
            "status": int(status),
            "expected_status": 404,
            "canonical_code": canonical,
            "expected_canonical_code": "model_not_found",
            "protocol_code": protocol_code,
            "expected_protocol_code": _expected_protocol("model_not_found", protocol),
            "action": (
                "transport_error"
                if transport_failed
                else str(extension.get("recovery") or "")
            ),
            "pass": (
                not transport_failed
                and status == 404
                and canonical == "model_not_found"
            ),
        }
        matrix.append(row)
    failed = [row for row in matrix if not row["pass"]]
    return {
        "mode": "inject",
        "pass": not failed,
        "summary": {"rows": len(matrix), "passed": len(matrix) - len(failed),
                    "failed": len(failed)},
        "first_two_mismatches": failed[:2],
        "matrix": matrix,
    }


def _default_live_paths() -> list[Path]:
    configured = [
        Path(value)
        for value in (os.environ.get("LTT_LLM_CONTRACT_LOGS") or "").split(os.pathsep)
        if value.strip()
    ]
    explicit_logs = (os.environ.get("LTT_LOGS_DIR") or "").strip()
    roots = [
        Path(explicit_logs or (r"C:\LTTPlatform\logs" if os.name == "nt" else ROOT / "logs")),
        # Compatibility with the short-lived Task 9 default.  Production A
        # never used this directory, but an operator may have exported logs
        # there before the correction.
        Path(os.environ.get("LTT_DATA_DIR") or r"C:\LTTPlatform\data") / "logs",
    ]
    patterns = ("ltt-server*.jsonl", "ltt-job-worker*.jsonl", "*llm*.jsonl")
    discovered: list[Path] = []
    for root in roots:
        for pattern in patterns:
            for path in sorted(root.glob(pattern)):
                if path not in configured and path not in discovered:
                    discovered.append(path)
    return configured + discovered


def _timestamp(value) -> datetime | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _read_live_lines(
    paths: Iterable[Path], *, minutes: int, now: datetime | None = None
) -> list[str]:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cutoff = current - timedelta(minutes=max(1, int(minutes)))
    lines: list[str] = []
    for path in paths:
        try:
            candidates = path.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
        except OSError:
            continue
        for line in candidates:
            event = _event_from_line(line)
            if event is None:
                continue
            event_time = _timestamp(
                event.get("timestamp", event.get("time", event.get("ts")))
            )
            if event_time is not None and cutoff <= event_time <= current:
                lines.append(json.dumps(event, ensure_ascii=True, separators=(",", ":")))
    return lines


def _markdown(report: dict) -> str:
    lines = [
        "# LLM error contract report",
        "",
        f"- mode: `{report['mode']}`",
        f"- pass: `{str(bool(report['pass'])).lower()}`",
        f"- summary: `{json.dumps(report['summary'], sort_keys=True)}`",
        "",
    ]
    if report.get("matrix"):
        lines.extend([
            "| code | protocol | phase | status | canonical | protocol code | action | pass |",
            "|---|---|---|---:|---|---|---|---|",
        ])
        for row in report["matrix"]:
            lines.append(
                "| {code} | {protocol} | {phase} | {status} | {canonical_code} | "
                "{protocol_code} | {action} | {pass} |".format(**row)
            )
    if report.get("first_two_mismatches"):
        lines.extend(["", "## First two mismatches", ""])
        for row in report["first_two_mismatches"]:
            lines.append(f"- `{json.dumps(row, sort_keys=True)}`")
    return "\n".join(lines) + "\n"


def _write_report(output: Path, report: dict) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output / "report.md").write_text(
        _markdown(report), encoding="utf-8", newline="\n"
    )


def _parser() -> argparse.ArgumentParser:
    # Keep help text ASCII: production operators commonly run this command from
    # Windows PowerShell 5.1, whose stdout can still be strict cp1252.  The
    # Vietnamese module docstring made ``--help`` fail before parsing any mode.
    parser = argparse.ArgumentParser(
        description="Check the LLM error contract with fixtures, logs, or probes."
    )
    sub = parser.add_subparsers(dest="mode", required=True)
    fixture = sub.add_parser("fixture", help="offline deterministic corpus")
    fixture.add_argument("--output", type=Path, required=True)
    live = sub.add_parser("live", help="passive structured-log aggregation")
    live.add_argument("--minutes", type=int, default=20)
    live.add_argument("--output", type=Path, required=True)
    live.add_argument("--log", type=Path, action="append", default=[])
    inject = sub.add_parser("inject", help="cheap failures against a test URL")
    inject.add_argument("--base-url", required=True)
    inject.add_argument("--output", type=Path, required=True)
    inject.add_argument("--allow-production", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.mode == "fixture":
        report = build_fixture_report()
    elif args.mode == "live":
        paths = args.log or _default_live_paths()
        report = analyze_live(
            _read_live_lines(paths, minutes=args.minutes), minutes=args.minutes
        )
        report["sources_read"] = len(paths)
    else:
        report = run_inject(
            args.base_url,
            token=os.environ.get("LTT_LLM_CONTRACT_TOKEN", ""),
            allow_production=args.allow_production,
        )
    _write_report(args.output, report)
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
