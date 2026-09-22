"""Telemetry hữu hạn cho lỗi model, dùng được ở cả tiến trình A và B.

Module chỉ nhận các trường đã chuẩn hoá. Nó không nhận body, prompt, header
Authorization hay message của provider, nên dữ liệu nhạy cảm không có đường đi
vào log. Request ID chỉ là trường tương quan, tuyệt đối không làm label counter.
"""
from __future__ import annotations

import json
import logging
import re
import threading
from collections import Counter
from datetime import datetime, timezone
from typing import Iterable


_SAFE_VALUE = re.compile(r"^[A-Za-z0-9_.:/-]{1,96}$")
_PROTOCOLS = frozenset({"gateway", "chat", "messages", "responses", "rfc9457"})
_PHASES = frozenset({"before_headers", "after_headers", "decode"})
_ACTIONS = frozenset({"retry", "terminal", "legacy", "unknown", "client_disconnected"})
_ENDPOINTS = frozenset({"gateway", "chat", "messages", "responses", "public_api"})


def _safe(value: object, fallback: str) -> str:
    text = str(value or "")
    return text if _SAFE_VALUE.fullmatch(text) else fallback


def _choice(value: object, allowed: frozenset[str], fallback: str) -> str:
    text = str(value or "")
    return text if text in allowed else fallback


def _request_id(value: object) -> str:
    return _safe(value, "")


class ErrorTelemetry:
    """Counter trong tiến trình và structured event với label bị chặn hữu hạn."""

    def __init__(self, source: str):
        self.source = "B" if str(source).upper() == "B" else "A"
        self._lock = threading.Lock()
        self._totals = {
            "llm_error_total": 0,
            "llm_error_unknown_total": 0,
            "llm_error_legacy_total": 0,
            "llm_error_contract_mismatch_total": 0,
            "llm_error_request_id_missing_total": 0,
        }
        self._labels: Counter[tuple[str, str, str, str, str, str]] = Counter()

    def reset_for_tests(self) -> None:
        with self._lock:
            for name in self._totals:
                self._totals[name] = 0
            self._labels.clear()

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            totals = dict(self._totals)
            labels = [
                {
                    "canonical_code": key[0],
                    "model": key[1],
                    "endpoint": key[2],
                    "stream_phase": key[3],
                    "protocol": key[4],
                    "action": key[5],
                    "count": count,
                }
                for key, count in sorted(self._labels.items())
            ]
        return {"source": self.source, **totals, "labels": labels}

    def record(
        self,
        *,
        logger: logging.Logger,
        request_id: object,
        gateway_code: object,
        canonical_code: object,
        protocol_code: object,
        category: object,
        http_status: int,
        upstream_status: int | None,
        protocol: object,
        stream_phase: object,
        retry: object,
        recovery: object,
        model: object,
        elapsed_ms: int | float,
        endpoint: object,
        action: object,
        legacy: bool = False,
        contract_mismatch: bool = False,
        model_known: bool = False,
        count: bool = True,
    ) -> dict[str, object]:
        """Ghi một event an toàn; chỉ label model đã được caller xác nhận."""
        rid = _request_id(request_id)
        canonical = _safe(canonical_code, "upstream_unknown")
        protocol_value = _choice(protocol, _PROTOCOLS, "gateway")
        phase = _choice(stream_phase, _PHASES, "before_headers")
        action_value = _choice(action, _ACTIONS, "terminal")
        endpoint_value = _choice(endpoint, _ENDPOINTS, "gateway")
        raw_model = _safe(model, "")
        model_label = raw_model if model_known and raw_model else (
            "missing" if not raw_model else "other"
        )
        try:
            elapsed = max(0, int(elapsed_ms))
        except (TypeError, ValueError, OverflowError):
            elapsed = 0
        event: dict[str, object] = {
            "event": "llm_model_error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": self.source,
            "request_id": rid,
            "gateway_code": _safe(gateway_code, canonical),
            "canonical_code": canonical,
            "protocol_code": _safe(protocol_code, canonical),
            "category": _safe(category, "unknown"),
            "http_status": int(http_status),
            "upstream_status": (
                int(upstream_status) if upstream_status is not None else None
            ),
            "protocol": protocol_value,
            "stream_phase": phase,
            "retry": _safe(retry, "ambiguous"),
            "recovery": _safe(recovery, "report_request_id"),
            "model": model_label,
            "elapsed_ms": elapsed,
            "endpoint": endpoint_value,
            "action": action_value,
            "legacy": bool(legacy),
            "contract_mismatch": bool(contract_mismatch),
            "counted": bool(count),
        }
        if count:
            with self._lock:
                self._totals["llm_error_total"] += 1
                self._totals["llm_error_unknown_total"] += canonical == "upstream_unknown"
                self._totals["llm_error_legacy_total"] += bool(legacy)
                self._totals["llm_error_contract_mismatch_total"] += bool(contract_mismatch)
                self._totals["llm_error_request_id_missing_total"] += not bool(rid)
                self._labels[(
                    canonical,
                    model_label,
                    endpoint_value,
                    phase,
                    protocol_value,
                    action_value,
                )] += 1
                event.update(self._totals)
        logger.warning(json.dumps(event, ensure_ascii=True, separators=(",", ":")))
        return event


def choose_action(*, canonical_code: str, retry: str,
                  legacy: bool = False, contract_mismatch: bool = False) -> str:
    if legacy:
        return "legacy"
    if canonical_code == "upstream_unknown" or contract_mismatch:
        return "unknown"
    if retry == "after_delay" or canonical_code == "tool_call_parse_failed":
        return "retry"
    return "terminal"


def finite_values() -> dict[str, Iterable[str]]:
    """Công bố tập label để test/gate chứng minh cardinality bị chặn."""
    return {
        "protocol": tuple(sorted(_PROTOCOLS)),
        "stream_phase": tuple(sorted(_PHASES)),
        "action": tuple(sorted(_ACTIONS)),
        "endpoint": tuple(sorted(_ENDPOINTS)),
    }


# Một tiến trình B dùng chung một bộ đếm cho lỗi trước và sau header. Khi module
# được import trong test của máy A, nó vẫn tách khỏi `_TELEMETRY` phía A.
B_TELEMETRY = ErrorTelemetry("B")
