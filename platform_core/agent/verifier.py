"""Deterministic verifier pipeline and bounded-failure metadata for P7."""
from __future__ import annotations

import json
import mimetypes
import os
import re
from dataclasses import asdict, dataclass
from typing import Callable, Optional

from platform_core import media

VERIFIER_CREDIT = {"technical": 0, "face_identity": 0, "vlm_judge": 1}
_FAULTS = {"partial", "structural", "policy", "inconclusive"}
_SENSITIVE = re.compile(
    r"(?i)(bearer\s+\S+|(?:api[_ -]?key|token|password|secret)\s*[:=]\s*\S+|"
    r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})"
)


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    score: float
    fault: str
    reason: str
    check: str
    model: str = ""
    key_ref: str = ""
    credit: int = 0

    def public_dict(self) -> dict:
        return asdict(self)


def sanitize_reason(value) -> str:
    text = " ".join(str(value or "").split())[:500]
    return _SENSITIVE.sub("[REDACTED]", text)


def _result(*, passed: bool, score=0, fault="", reason="", check: str,
            model="", key_ref="") -> VerificationResult:
    try:
        score = max(0.0, min(1.0, float(score)))
    except (TypeError, ValueError):
        score = 0.0
    if passed:
        fault = ""
    elif fault not in _FAULTS:
        fault = "inconclusive"
    return VerificationResult(
        bool(passed), score, fault, sanitize_reason(reason), check,
        sanitize_reason(model)[:80], sanitize_reason(key_ref)[:80],
        VERIFIER_CREDIT[check],
    )


def _artifact(outputs: dict, config: dict):
    field = str(config.get("output", "")).strip()
    if field:
        return outputs.get(field)
    for key in ("video", "image", "output", "path", "file"):
        if key in outputs:
            return outputs[key]
    return None


def technical(outputs: dict, config: dict, *,
              probe: Optional[Callable[[str], dict]] = None) -> VerificationResult:
    artifact = _artifact(outputs, config)
    if not isinstance(artifact, str) or not artifact:
        return _result(passed=False, fault="structural", reason="Thiếu artifact.",
                       check="technical")
    if not os.path.isfile(artifact):
        return _result(passed=False, fault="structural", reason="Artifact không tồn tại.",
                       check="technical")
    mime = mimetypes.guess_type(artifact)[0] or ""
    expected = str(config.get("mime", "")).strip()
    if expected and not mime.startswith(expected):
        return _result(passed=False, fault="structural", reason="MIME không hợp lệ.",
                       check="technical")
    metadata = {"file_size_mb": os.path.getsize(artifact) / (1024 * 1024)}
    if mime.startswith("video/") or any(
            key in config for key in ("min_duration", "max_duration", "min_width", "min_height")):
        try:
            metadata.update((probe or media.probe)(artifact))
        except Exception as exc:  # noqa: BLE001 - converted to explicit inconclusive
            return _result(passed=False, fault="inconclusive",
                           reason=f"Không probe được artifact: {type(exc).__name__}",
                           check="technical")
    checks = (
        ("min_duration", "duration", lambda actual, limit: actual >= limit),
        ("max_duration", "duration", lambda actual, limit: actual <= limit),
        ("min_width", "width", lambda actual, limit: actual >= limit),
        ("min_height", "height", lambda actual, limit: actual >= limit),
        ("max_size_mb", "file_size_mb", lambda actual, limit: actual <= limit),
    )
    for option, field, predicate in checks:
        if option in config and not predicate(float(metadata.get(field, 0)),
                                              float(config[option])):
            return _result(passed=False, fault="structural",
                           reason=f"Artifact không đạt {option}.", check="technical")
    return _result(passed=True, score=1, reason="Technical pass.", check="technical")


def vlm_judge(outputs: dict, config: dict, *,
              judge: Optional[Callable[[dict, dict], object]] = None) -> VerificationResult:
    if judge is None:
        return _result(passed=False, fault="inconclusive",
                       reason="VLM verifier chưa được cấu hình.", check="vlm_judge")
    try:
        raw = judge(outputs, config)
        if isinstance(raw, str):
            raw = json.loads(raw)
        if not isinstance(raw, dict) or not isinstance(raw.get("pass"), bool):
            raise ValueError("schema")
        fault = str(raw.get("fault", ""))
        if not raw["pass"] and fault not in {"partial", "structural", "policy"}:
            raise ValueError("fault")
        return _result(
            passed=raw["pass"], score=raw.get("score", 0), fault=fault,
            reason=raw.get("reason", ""), check="vlm_judge",
            model=raw.get("model", ""), key_ref=raw.get("key_ref", ""),
        )
    except Exception as exc:  # noqa: BLE001 - provider/schema failures are explicit
        return _result(passed=False, fault="inconclusive",
                       reason=f"VLM verifier lỗi: {type(exc).__name__}",
                       check="vlm_judge")


def face_identity(outputs: dict, config: dict, *,
                  compare: Optional[Callable[[object, object], float]] = None
                  ) -> VerificationResult:
    if compare is None:
        return _result(passed=False, fault="inconclusive",
                       reason="Face recognition adapter chưa được cấu hình.",
                       check="face_identity")
    try:
        score = float(compare(_artifact(outputs, config), config.get("against")))
        minimum = float(config.get("min_score", 0.75))
        return _result(passed=score >= minimum, score=score,
                       fault="structural" if score < minimum else "",
                       reason="Face identity pass." if score >= minimum
                       else "Khuôn mặt không đạt ngưỡng danh tính.",
                       check="face_identity")
    except Exception as exc:  # noqa: BLE001
        return _result(passed=False, fault="inconclusive",
                       reason=f"Face verifier lỗi: {type(exc).__name__}",
                       check="face_identity")


def verify(outputs: dict, config: dict, *, probe=None, judge=None,
           face_compare=None) -> tuple[VerificationResult, ...]:
    """Run cheap checks first and stop at first non-pass result."""
    requested = config if isinstance(config, list) else [config]
    order = {"technical": 0, "face_identity": 1, "vlm_judge": 2}
    requested = sorted(requested, key=lambda item: order.get(item.get("check", ""), 99))
    results = []
    for item in requested:
        check = item.get("check")
        if check == "technical":
            result = technical(outputs, item, probe=probe)
        elif check == "face_identity":
            result = face_identity(outputs, item, compare=face_compare)
        elif check == "vlm_judge":
            result = vlm_judge(outputs, item, judge=judge)
        else:
            result = _result(passed=False, fault="inconclusive",
                             reason="Verifier không được hỗ trợ.", check="technical")
        results.append(result)
        if not result.passed:
            break
    return tuple(results)


def verifier_cost(config) -> int:
    requested = config if isinstance(config, list) else ([config] if config else [])
    return sum(VERIFIER_CREDIT.get(str(item.get("check", "")), 0)
               for item in requested if isinstance(item, dict))
