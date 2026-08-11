"""H31.3d1 — dataset split and honest blind A/B calibration readiness."""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

SECRET = "fixture-blind-secret-at-least-16"
SLICES = ("face", "text", "nature", "animation", "low-light", "motion")
DEGRADATIONS = ("bicubic", "blur", "noise", "compression", "mixed")


def _case(index: int, kind: str = "image") -> dict:
    return {
        "id": f"case-{kind}-{index}", "dataset_sample_id": f"sample-{index}",
        "media_kind": kind, "degradation": DEGRADATIONS[index % 5],
        "slice": SLICES[index % 6],
        "candidate_key": f"quality-datasets/candidate/{kind}-{index}.png",
        "baseline_key": f"quality-datasets/baseline/{kind}-{index}.png",
        "metric_value": float(index),
    }


def _suite(cases: list[dict]) -> dict:
    from apps.qualitylab.calibration import validate_calibration_suite

    return validate_calibration_suite({
        "schema_version": 1, "calibration_version": "upscale-human-v1",
        "dataset_manifest_sha256": "a" * 64, "cases": cases,
    })


def test_dataset_contract_preserves_split_kind_tags_and_hashes():
    from apps.qualitylab.datasets import validate_manifest

    manifest = validate_manifest({
        "schema_version": 1, "app_slug": "upscalevideo", "dataset_version": "v2",
        "items": [{
            "id": "one", "reference_key": "quality/hr.png",
            "degraded_key": "quality/lr.png", "degradation": "noise",
            "media_kind": "video", "split": "blind-regression",
            "slice": "motion", "tags": ["fast-motion", "low-light"],
            "reference_sha256": "b" * 64, "degraded_sha256": "c" * 64,
            "license": "LTT synthetic", "owned_or_licensed": True,
            "production_data": False,
        }],
    })
    item = manifest["items"][0]
    assert item["media_kind"] == "video"
    assert item["split"] == "blind-regression"
    assert item["tags"] == ["fast-motion", "low-light"]
    assert item["reference_sha256"] == "b" * 64


def test_blind_assignment_is_stable_and_vote_hides_rater_and_model_role():
    from apps.qualitylab.calibration import (
        blind_assignment, normalize_vote, resolve_artifact_token,
    )

    case = _suite([_case(0)])["cases"][0]
    first = blind_assignment(case, "reviewer@example.test", SECRET)
    second = blind_assignment(case, "reviewer@example.test", SECRET)
    assert first == second
    assert set(first) == {"case_id", "assignment_id", "left_artifact_token",
                          "right_artifact_token"}
    assert "candidate" not in str(first) and "baseline" not in str(first)
    resolved = resolve_artifact_token(
        case, "reviewer@example.test", first["left_artifact_token"], SECRET)
    assert resolved in {case["candidate_key"], case["baseline_key"]}
    vote = normalize_vote(case, "reviewer@example.test", "left", SECRET,
                          {"technical": 4, "aesthetic": 3})
    assert "reviewer@example.test" not in str(vote)
    assert len(vote["rater_hash"]) == 64
    assert vote["preference"] in {"candidate", "baseline"}
    assert vote["rubric"] == {"technical": 4, "aesthetic": 3}


def test_partial_suite_never_becomes_release_gate():
    from apps.qualitylab.calibration import aggregate_reviews, normalize_vote

    suite = _suite([_case(0)])
    case = suite["cases"][0]
    votes = [normalize_vote(case, f"rater-{index}", "tie", SECRET)
             for index in range(3)]
    result = aggregate_reviews(suite, votes, SECRET)
    assert result["ready_for_threshold_review"] is False
    assert result["release_gate_eligible"] is False
    assert "image_cases<30" in result["readiness_reasons"]
    assert "video_cases<12" in result["readiness_reasons"]


def test_full_minimum_suite_reports_agreement_and_correlation_but_not_gate():
    from apps.qualitylab.calibration import (
        aggregate_reviews, blind_assignment, normalize_vote, resolve_artifact_token,
    )

    suite = _suite([_case(index, "image") for index in range(30)] +
                   [_case(index + 30, "video") for index in range(12)])
    votes = []
    for case_index, case in enumerate(suite["cases"]):
        wanted = "candidate" if case_index >= 21 else "baseline"
        for rater_index in range(3):
            rater = f"rater-{rater_index}"
            assignment = blind_assignment(case, rater, SECRET)
            left_key = resolve_artifact_token(
                case, rater, assignment["left_artifact_token"], SECRET)
            selected_key = case[f"{wanted}_key"]
            side = "left" if left_key == selected_key else "right"
            votes.append(normalize_vote(case, rater, side, SECRET))
    result = aggregate_reviews(suite, votes, SECRET)
    assert result["case_counts"] == {"image": 30, "video": 12}
    assert result["complete_case_count"] == 42
    assert result["missing_slices"] == []
    assert result["missing_degradations"] == []
    assert result["fleiss_kappa"] == 1.0
    assert result["spearman_metric_vs_human"] > 0.8
    assert result["ready_for_threshold_review"] is True
    assert result["release_gate_eligible"] is False


def test_duplicate_vote_from_same_rater_is_rejected():
    from apps.qualitylab.calibration import aggregate_reviews, normalize_vote

    suite = _suite([_case(0)])
    vote = normalize_vote(suite["cases"][0], "same-rater", "tie", SECRET)
    with pytest.raises(ValueError, match="một lần"):
        aggregate_reviews(suite, [vote, vote], SECRET)


def test_tampered_vote_is_rejected_by_hmac_signature():
    from apps.qualitylab.calibration import aggregate_reviews, normalize_vote

    suite = _suite([_case(0)])
    vote = normalize_vote(suite["cases"][0], "rater", "left", SECRET)
    vote["preference"] = "tie"
    with pytest.raises(ValueError, match="Chữ ký"):
        aggregate_reviews(suite, [vote], SECRET)


def test_calibration_cli_validate_emits_only_safe_suite_metadata():
    result = subprocess.run([
        sys.executable, "tools/qualitylab_calibration.py", "validate", "--suite",
        "tests/fixtures/qualitylab_calibration_suite.json",
    ], capture_output=True, text=True, timeout=20, check=False)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["case_count"] == 1
    assert len(payload["suite_sha256"]) == 64
    assert "candidate_key" not in payload and "baseline_key" not in payload
