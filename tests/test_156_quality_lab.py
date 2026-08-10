"""H31.1–H31.2 — contract và foundation evaluator của Quality Lab."""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image


class _Context:
    job_id = "eval-001"

    def __init__(self):
        self.progress_values = []
        self.stages = []

    def progress(self, value, message=""):
        self.progress_values.append((value, message))

    def stage(self, name, message="", **kwargs):
        self.stages.append((name, message, kwargs))


def test_manifest_is_operator_only_and_free_internal_job():
    from apps.qualitylab.manifest import MANIFEST

    assert MANIFEST.slug == "qualitylab"
    assert MANIFEST.surface == "admin"
    assert MANIFEST.public is False
    assert MANIFEST.lifecycle == "internal"
    assert MANIFEST.job_types == ("qualitylab.evaluate",)
    assert MANIFEST.credit_cost({}) == 0


def test_registry_refuses_unapproved_evaluator_instead_of_fallback():
    from apps.qualitylab.registry import EVALUATORS, PACKS, enabled_pack

    assert enabled_pack("media_contract") is PACKS["media_contract"]
    assert EVALUATORS["lpips"].enabled is False
    assert EVALUATORS["lpips"].model_sha256 == ""
    assert all(EVALUATORS[name].enabled
               for name in PACKS["autosub_foundation"]["evaluators"])


def test_report_is_vector_and_unknown_never_becomes_pass():
    from apps.qualitylab.contracts import Dimension, Metric, build_report

    report = build_report(
        evaluation_id="e1", pack="p", source_kind="video", evaluator_version="v1",
        dimensions=[
            Dimension("technical", "Kỹ thuật", "PASS", (
                Metric("decode", "Decode", True, verdict="PASS"),)),
            Dimension("semantic", "Ngữ nghĩa", "UNKNOWN", (
                Metric("alignment", "Alignment", None, verdict="UNKNOWN"),)),
        ],
    )
    assert report["overall_verdict"] == "UNKNOWN"
    assert report["release_gate_eligible"] is False
    assert "score" not in report
    assert len(report["dimensions"]) == 2
    assert "source_artifact" in report
    assert "evaluators" in report
    assert "environment" in report


def test_hard_fail_wins_over_good_dimensions():
    from apps.qualitylab.contracts import Dimension, Metric, build_report

    report = build_report(
        evaluation_id="e2", pack="p", source_kind="video", evaluator_version="v1",
        dimensions=[
            Dimension("technical", "Kỹ thuật", "FAIL", (
                Metric("audio", "Audio", False, verdict="FAIL"),)),
            Dimension("quality", "Chất lượng", "PASS", (
                Metric("proxy", "Proxy", 99, verdict="PASS"),)),
        ],
    )
    assert report["overall_verdict"] == "FAIL"


def test_not_applicable_dimensions_do_not_become_pass():
    from apps.qualitylab.contracts import Dimension, Metric, build_report

    report = build_report(
        evaluation_id="e3", pack="p", source_kind="audio", evaluator_version="v1",
        dimensions=[Dimension("visual", "Hình ảnh", "NOT_APPLICABLE", (
            Metric("frames", "Khung hình", None, verdict="NOT_APPLICABLE"),))],
    )
    assert report["overall_verdict"] == "NOT_APPLICABLE"


def test_subtitle_parser_measures_timing_readability_and_wer():
    from apps.qualitylab.services.subtitle import inspect_subtitle

    srt = """1
00:00:00,000 --> 00:00:02,000
Xin chào mọi người

2
00:00:02,200 --> 00:00:04,000
Đây là LTT Studios
"""
    dimensions, summary = inspect_subtitle(
        srt, "Xin chào mọi người Đây là LTT Studios")
    by_key = {item.key: item for item in dimensions}
    assert by_key["technical"].verdict == "PASS"
    assert by_key["readability"].verdict == "PASS"
    assert by_key["content"].metrics[0].value == 0.0
    assert by_key["content"].verdict == "UNKNOWN"
    assert summary["cue_count"] == 2


def test_subtitle_parser_exposes_overlap_and_long_line():
    from apps.qualitylab.services.subtitle import inspect_subtitle

    srt = """1
00:00:00,000 --> 00:00:02,000
Một dòng phụ đề rất dài vượt quá bốn mươi hai ký tự để kiểm tra

2
00:00:01,800 --> 00:00:03,000
Chồng nhau
"""
    dimensions, summary = inspect_subtitle(srt)
    by_key = {item.key: item for item in dimensions}
    assert by_key["technical"].verdict == "WARN"
    assert by_key["readability"].verdict == "WARN"
    assert by_key["content"].verdict == "UNKNOWN"
    assert summary["overlaps"] == 1


def test_malformed_subtitle_is_hard_fail():
    from apps.qualitylab.services.subtitle import inspect_subtitle

    dimensions, summary = inspect_subtitle("không có timestamp")
    assert dimensions[0].verdict == "FAIL"
    assert dimensions[0].metrics[0].key == "parseable"
    assert summary == {}


def test_image_job_builds_durable_report_and_deletes_ephemeral(tmp_path, monkeypatch):
    from platform_core.storage import LocalStorage, set_storage
    from apps.qualitylab import jobs

    storage = LocalStorage(str(tmp_path / "storage"))
    set_storage(storage)
    image = Image.new("RGB", (64, 48), color=(20, 30, 40))
    payload = io.BytesIO(); image.save(payload, "PNG"); payload.seek(0)
    key = "qualitylab/u1/ephemeral/input.png"
    storage.put(key, payload, "image/png")
    context = _Context()

    result = jobs.handle({
        "pack": "upscale_foundation", "source_key": key,
        "source_name": "input.png", "ephemeral_keys": [key],
        "expectations": {"expected_width": 64, "expected_height": 48},
    }, context)

    assert result["overall_verdict"] == "PASS"
    assert result["report"]["runtime"]["source_bytes"] > 0
    assert len(result["report"]["source_artifact"]["sha256"]) == 64
    assert result["report"]["environment"]["device"] == "cpu"
    assert result["report"]["evaluators"][0]["version"]
    assert result["report"]["release_gate_eligible"] is False
    assert not storage.exists(key)
    assert context.progress_values[-1][0] == 100
    assert context.stages[-1][0] == "evaluation_complete"


def test_direct_subtitle_key_is_retained_after_job(tmp_path):
    from platform_core.storage import LocalStorage, set_storage
    from apps.qualitylab import jobs

    storage = LocalStorage(str(tmp_path / "storage"))
    set_storage(storage)
    key = "autosubvideo/u1/output.srt"
    truth_key = "qualitylab/u1/ephemeral/truth.txt"
    storage.put(key, io.BytesIO(
        b"1\n00:00:00,000 --> 00:00:01,500\nhello world\n"),
        "application/x-subrip")
    storage.put(truth_key, io.BytesIO(b"hello world"), "text/plain")
    result = jobs.handle({
        "pack": "autosub_foundation", "source_key": key,
        "source_name": "output.srt", "expected_text_key": truth_key,
        "ephemeral_keys": [truth_key],
    }, _Context())
    assert result["report"]["runtime"]["summary"]["wer"] == 0.0
    assert storage.exists(key)
    assert not storage.exists(truth_key)


def test_routes_and_templates_lock_operator_honest_ui_contract():
    root = Path(__file__).resolve().parents[1]
    routes = (root / "apps/qualitylab/routes.py").read_text(encoding="utf-8")
    page = (root / "apps/qualitylab/templates/qualitylab.html").read_text(
        encoding="utf-8")
    report = (root / "apps/qualitylab/templates/qualitylab_report.html").read_text(
        encoding="utf-8")

    assert routes.count("Depends(require_operator)") == 4
    assert "Depends(require_login)" not in routes
    assert "Foundation chưa calibrated" in page
    assert "CHƯA DUYỆT" in page
    assert "release gate" in report
    assert 'role="alert"' in page and 'role="status"' in report


def test_browser_fixture_wrapper_is_ascii_and_isolated():
    root = Path(__file__).resolve().parents[1]
    wrapper = (root / "tools/run_qualitylab_fixture.ps1").read_bytes()
    assert not wrapper.startswith(b"\xef\xbb\xbf")
    text = wrapper.decode("ascii")
    assert "qualitylab-browser" in text
    assert "LTT_QUALITYLAB_BROWSER_TEST" in text
    assert "-WindowStyle Hidden" in text
