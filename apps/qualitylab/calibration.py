"""Blind human A/B calibration contract; no synthetic human judgements."""
from __future__ import annotations

import hashlib
import hmac
import json
import math
from typing import Any

from apps.qualitylab.datasets import (
    ALLOWED_DEGRADATIONS,
    ALLOWED_MEDIA_KINDS,
    _safe_key,
)
from platform_core.i18n import N_

ALLOWED_SELECTIONS = {"left", "right", "tie", "insufficient"}
REQUIRED_SLICES = {"face", "text", "nature", "animation", "low-light", "motion"}
MIN_CASES = {"image": 30, "video": 12}
MIN_RATERS = 3
MAX_CASES = 500


def _token(secret: str, value: str) -> str:
    if len(secret) < 16:
        raise ValueError(N_("Blind secret phải có ít nhất 16 ký tự."))
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"),
                    hashlib.sha256).hexdigest()


def validate_calibration_suite(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != 1:
        raise ValueError(N_("Calibration suite phải dùng schema_version=1."))
    version = str(payload.get("calibration_version") or "").strip()[:80]
    dataset_hash = str(payload.get("dataset_manifest_sha256") or "").lower().strip()
    if not version or len(dataset_hash) != 64 or any(
            char not in "0123456789abcdef" for char in dataset_hash):
        raise ValueError(N_("Thiếu calibration version hoặc dataset manifest hash."))
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not 1 <= len(raw_cases) <= MAX_CASES:
        raise ValueError(N_("Calibration suite phải có từ 1 đến 500 case."))
    seen: set[str] = set()
    cases: list[dict[str, Any]] = []
    for raw in raw_cases:
        if not isinstance(raw, dict):
            raise ValueError(N_("Calibration case phải là object."))
        case_id = str(raw.get("id") or "").strip()
        if not case_id or case_id in seen:
            raise ValueError(N_("Calibration case id rỗng hoặc trùng."))
        seen.add(case_id)
        media_kind = str(raw.get("media_kind") or "")
        degradation = str(raw.get("degradation") or "")
        if media_kind not in ALLOWED_MEDIA_KINDS:
            raise ValueError(N_("Calibration media_kind không hợp lệ."))
        if degradation not in ALLOWED_DEGRADATIONS:
            raise ValueError(N_("Calibration degradation không hợp lệ."))
        slice_name = str(raw.get("slice") or "").strip().lower()
        if not slice_name or len(slice_name) > 80:
            raise ValueError(N_("Calibration slice rỗng hoặc quá dài."))
        metric = raw.get("metric_value")
        if metric is not None:
            metric = float(metric)
            if not math.isfinite(metric):
                raise ValueError(N_("metric_value phải hữu hạn."))
        cases.append({
            "id": case_id,
            "dataset_sample_id": str(raw.get("dataset_sample_id") or "")[:120],
            "media_kind": media_kind,
            "degradation": degradation,
            "slice": slice_name,
            "candidate_key": _safe_key(raw.get("candidate_key"), "candidate_key"),
            "baseline_key": _safe_key(raw.get("baseline_key"), "baseline_key"),
            "metric_value": metric,
        })
    normalized = {
        "schema_version": 1,
        "calibration_version": version,
        "dataset_manifest_sha256": dataset_hash,
        "cases": cases,
    }
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False).encode("utf-8")
    normalized["suite_sha256"] = hashlib.sha256(canonical).hexdigest()
    return normalized


def _candidate_is_left(case: dict[str, Any], rater_id: str, secret: str) -> bool:
    assignment_id = _token(secret, f"assignment:{case['id']}:{rater_id}")
    return int(assignment_id[-2:], 16) % 2 == 0


def blind_assignment(case: dict[str, Any], rater_id: str, secret: str) -> dict[str, str]:
    rater = str(rater_id or "").strip()
    if not rater:
        raise ValueError(N_("Thiếu rater id."))
    assignment_id = _token(secret, f"assignment:{case['id']}:{rater}")
    return {
        "case_id": case["id"],
        "assignment_id": assignment_id,
        "left_artifact_token": _token(secret, f"artifact:{case['id']}:{rater}:left"),
        "right_artifact_token": _token(secret, f"artifact:{case['id']}:{rater}:right"),
    }


def resolve_artifact_token(case: dict[str, Any], rater_id: str, token: str,
                           secret: str) -> str:
    """Resolve inside the trusted backend; never serialize the returned key."""
    assignment = blind_assignment(case, rater_id, secret)
    if hmac.compare_digest(token, assignment["left_artifact_token"]):
        side = "left"
    elif hmac.compare_digest(token, assignment["right_artifact_token"]):
        side = "right"
    else:
        raise ValueError(N_("Artifact token không hợp lệ."))
    candidate_left = _candidate_is_left(case, rater_id, secret)
    is_candidate = candidate_left if side == "left" else not candidate_left
    return case["candidate_key"] if is_candidate else case["baseline_key"]


def normalize_vote(case: dict[str, Any], rater_id: str, selection: str,
                   secret: str, rubric: dict[str, Any] | None = None) -> dict[str, Any]:
    choice = str(selection or "").strip().lower()
    if choice not in ALLOWED_SELECTIONS:
        raise ValueError(N_("Lựa chọn A/B không hợp lệ."))
    assignment = blind_assignment(case, rater_id, secret)
    if choice in {"tie", "insufficient"}:
        canonical_choice = choice
    else:
        candidate_left = _candidate_is_left(case, rater_id, secret)
        canonical_choice = ("candidate" if ((choice == "left") == candidate_left)
                            else "baseline")
    scores: dict[str, int] = {}
    for key in ("technical", "semantic", "aesthetic"):
        raw = (rubric or {}).get(key)
        if raw is None:
            continue
        score = int(raw)
        if not 1 <= score <= 5:
            raise ValueError(N_("Điểm rubric phải nằm trong 1..5."))
        scores[key] = score
    vote = {
        "case_id": case["id"],
        "rater_hash": _token(secret, f"rater:{rater_id}"),
        "assignment_id": assignment["assignment_id"],
        "preference": canonical_choice,
        "rubric": scores,
    }
    vote["vote_signature"] = _token(
        secret, "vote:" + json.dumps(vote, sort_keys=True, separators=(",", ":")))
    return vote


def _average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + 1 + end) / 2.0
        for index in order[start:end]:
            ranks[index] = rank
        start = end
    return ranks


def _pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) < 3 or len(left) != len(right):
        return None
    left_mean, right_mean = sum(left) / len(left), sum(right) / len(right)
    numerator = sum((x - left_mean) * (y - right_mean)
                    for x, y in zip(left, right))
    left_var = sum((x - left_mean) ** 2 for x in left)
    right_var = sum((y - right_mean) ** 2 for y in right)
    if left_var == 0 or right_var == 0:
        return None
    return numerator / math.sqrt(left_var * right_var)


def _fleiss_kappa(counts: list[dict[str, int]]) -> float | None:
    usable = [item for item in counts if sum(item.values()) >= MIN_RATERS]
    if len(usable) < 2:
        return None
    agreements = []
    totals = {key: 0 for key in ("candidate", "baseline", "tie")}
    total_votes = 0
    for item in usable:
        n = sum(item.values())
        agreements.append((sum(value * value for value in item.values()) - n) /
                          (n * (n - 1)))
        for key in totals:
            totals[key] += item.get(key, 0)
        total_votes += n
    expected = sum((value / total_votes) ** 2 for value in totals.values())
    if expected == 1:
        return 1.0
    return (sum(agreements) / len(agreements) - expected) / (1 - expected)


def aggregate_reviews(suite: dict[str, Any], votes: list[dict[str, Any]],
                      secret: str) -> dict[str, Any]:
    cases = {case["id"]: case for case in suite["cases"]}
    by_case: dict[str, list[dict[str, Any]]] = {case_id: [] for case_id in cases}
    seen: set[tuple[str, str]] = set()
    for vote in votes:
        unsigned = {key: vote.get(key) for key in (
            "case_id", "rater_hash", "assignment_id", "preference", "rubric")}
        expected_signature = _token(
            secret, "vote:" + json.dumps(unsigned, sort_keys=True,
                                          separators=(",", ":")))
        if not hmac.compare_digest(str(vote.get("vote_signature") or ""),
                                   expected_signature):
            raise ValueError(N_("Chữ ký vote không hợp lệ."))
        case_id = str(vote.get("case_id") or "")
        rater_hash = str(vote.get("rater_hash") or "")
        preference = str(vote.get("preference") or "")
        if case_id not in cases or preference not in {
                "candidate", "baseline", "tie", "insufficient"} or len(rater_hash) != 64:
            raise ValueError(N_("Vote không hợp lệ."))
        identity = (case_id, rater_hash)
        if identity in seen:
            raise ValueError(N_("Một rater chỉ được chấm một lần mỗi case."))
        seen.add(identity)
        by_case[case_id].append(vote)

    case_rows = []
    agreement_counts = []
    metric_values, human_scores = [], []
    for case_id, case in cases.items():
        preferences = [vote["preference"] for vote in by_case[case_id]]
        counts = {key: preferences.count(key) for key in (
            "candidate", "baseline", "tie", "insufficient")}
        valid = counts["candidate"] + counts["baseline"] + counts["tie"]
        score = ((counts["candidate"] + 0.5 * counts["tie"]) / valid
                 if valid else None)
        complete = valid >= MIN_RATERS
        case_rows.append({"case_id": case_id, "valid_raters": valid,
                          "counts": counts, "candidate_preference": score,
                          "complete": complete})
        agreement_counts.append({key: counts[key] for key in (
            "candidate", "baseline", "tie")})
        if complete and score is not None and case["metric_value"] is not None:
            metric_values.append(float(case["metric_value"]))
            human_scores.append(float(score))

    kind_counts = {kind: sum(case["media_kind"] == kind for case in cases.values())
                   for kind in ALLOWED_MEDIA_KINDS}
    missing_slices = sorted(REQUIRED_SLICES - {
        case["slice"] for case in cases.values()})
    missing_degradations = sorted(ALLOWED_DEGRADATIONS - {
        case["degradation"] for case in cases.values()})
    incomplete = sorted(row["case_id"] for row in case_rows if not row["complete"])
    reasons = []
    for kind, minimum in MIN_CASES.items():
        if kind_counts[kind] < minimum:
            reasons.append(f"{kind}_cases<{minimum}")
    if missing_slices:
        reasons.append("missing_slices")
    if missing_degradations:
        reasons.append("missing_degradations")
    if incomplete:
        reasons.append("cases_below_3_raters")
    spearman = _pearson(_average_ranks(metric_values),
                        _average_ranks(human_scores)) if metric_values else None
    return {
        "schema_version": 1,
        "calibration_version": suite["calibration_version"],
        "suite_sha256": suite["suite_sha256"],
        "case_counts": kind_counts,
        "case_results": case_rows,
        "complete_case_count": len(case_rows) - len(incomplete),
        "missing_slices": missing_slices,
        "missing_degradations": missing_degradations,
        "incomplete_case_ids": incomplete,
        "fleiss_kappa": (round(value, 6) if (
            value := _fleiss_kappa(agreement_counts)) is not None else None),
        "spearman_metric_vs_human": (round(spearman, 6)
                                      if spearman is not None else None),
        "ready_for_threshold_review": not reasons,
        "readiness_reasons": reasons,
        "release_gate_eligible": False,
        "notice": N_("Ready chỉ cho phép review threshold; không tự bật release gate."),
    }
