"""Hợp đồng kết quả Quality Lab — ổn định, có version và Honest UI."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from platform_core.i18n import N_

VERDICTS = ("PASS", "WARN", "FAIL", "UNKNOWN", "NOT_APPLICABLE")
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    value: Any
    unit: str = ""
    verdict: str = "UNKNOWN"
    threshold: str = ""
    direction: str = ""
    valid_range: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        if self.verdict not in VERDICTS:
            raise ValueError(N_(f"Verdict không hợp lệ: {self.verdict}"))
        return asdict(self)


@dataclass(frozen=True)
class Dimension:
    key: str
    label: str
    verdict: str
    metrics: tuple[Metric, ...]

    def to_dict(self) -> dict[str, Any]:
        if self.verdict not in VERDICTS:
            raise ValueError(N_(f"Verdict không hợp lệ: {self.verdict}"))
        return {
            "key": self.key,
            "label": self.label,
            "verdict": self.verdict,
            "metrics": [metric.to_dict() for metric in self.metrics],
        }


def build_report(*, evaluation_id: str, pack: str, source_kind: str,
                 evaluator_version: str, dimensions: list[Dimension],
                 runtime: dict[str, Any] | None = None,
                 source_artifact: dict[str, Any] | None = None,
                 evaluators: list[dict[str, Any]] | None = None,
                 environment: dict[str, Any] | None = None) -> dict[str, Any]:
    """Dựng report vector; hard FAIL thắng WARN/PASS, UNKNOWN không thành PASS."""
    verdicts = [item.verdict for item in dimensions]
    if "FAIL" in verdicts:
        overall = "FAIL"
    elif "WARN" in verdicts:
        overall = "WARN"
    elif "UNKNOWN" in verdicts:
        overall = "UNKNOWN"
    elif verdicts and all(value == "NOT_APPLICABLE" for value in verdicts):
        overall = "NOT_APPLICABLE"
    elif verdicts and all(value in {"PASS", "NOT_APPLICABLE"} for value in verdicts):
        overall = "PASS"
    else:
        overall = "UNKNOWN"
    return {
        "schema_version": SCHEMA_VERSION,
        "evaluation_id": evaluation_id,
        "pack": pack,
        "source_kind": source_kind,
        "source_artifact": source_artifact or {},
        "evaluator_version": evaluator_version,
        "evaluators": evaluators or [],
        "calibration_version": "foundation-uncalibrated-v1",
        "release_gate_eligible": False,
        "overall_verdict": overall,
        "dimensions": [item.to_dict() for item in dimensions],
        "runtime": runtime or {},
        "environment": environment or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "notice": N_(
            "Kết quả foundation dùng để chẩn đoán; chưa được hiệu chuẩn với "
            "đánh giá mù của con người và không được dùng làm release gate."),
    }
