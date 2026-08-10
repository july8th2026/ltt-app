"""H31.3c — paired video/temporal/performance diagnostic."""
from __future__ import annotations

import io
import shutil
import subprocess

import numpy as np
import pytest


def _video(path, size: str = "64x64"):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg unavailable")
    result = subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
        "-i", f"testsrc=size={size}:rate=4:duration=1", "-c:v", "libx264",
        "-pix_fmt", "yuv420p", str(path),
    ], capture_output=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr.decode(errors="replace")


def test_temporal_proxy_is_zero_for_identical_frame_sequences():
    from apps.qualitylab.services.upscale_video import temporal_scores

    frames = [np.full((8, 8, 3), value, dtype=np.float32)
              for value in (0, 12, 30)]
    scores = temporal_scores(frames, [item.copy() for item in frames])
    assert scores == {"temporal_delta_mae": 0.0, "luma_flicker_residual": 0.0}


def test_video_diagnostic_contract_temporal_and_performance_are_honest(tmp_path):
    from apps.qualitylab.services.upscale_video import inspect_upscale_video_pair

    candidate = tmp_path / "candidate.mp4"
    reference = tmp_path / "reference.mp4"
    _video(candidate); shutil.copyfile(candidate, reference)
    dimensions, summary = inspect_upscale_video_pair(
        candidate, reference, None, tmp_path / "work",
        {"processing_seconds": 2.0, "frames": 4})
    by_key = {item.key: item for item in dimensions}
    assert by_key["video_contract"].verdict == "PASS"
    assert by_key["full_reference"].verdict == "UNKNOWN"
    assert by_key["temporal"].verdict == "UNKNOWN"
    assert by_key["performance"].verdict == "UNKNOWN"
    performance = {item.key: item for item in by_key["performance"].metrics}
    assert performance["throughput_fps"].value == 2.0
    assert performance["throughput_fps"].verdict == "UNKNOWN"
    assert performance["peak_vram_mb"].value is None
    assert summary["candidate_mean"]["psnr_db"] == 99.0
    assert summary["temporal"]["temporal_delta_mae"] == 0.0


def test_video_diagnostic_fails_before_sampling_on_dimension_mismatch(tmp_path):
    from apps.qualitylab.services.upscale_video import inspect_upscale_video_pair

    candidate, reference = tmp_path / "candidate.mp4", tmp_path / "reference.mp4"
    _video(candidate, "64x64"); _video(reference, "32x32")
    dimensions, _summary = inspect_upscale_video_pair(
        candidate, reference, None, tmp_path / "work")
    assert dimensions[0].key == "video_contract"
    assert dimensions[0].verdict == "FAIL"
    assert not (tmp_path / "work" / "candidate-frames").exists()


def test_video_pack_job_hashes_inputs_and_cleans_ephemeral(tmp_path):
    from apps.qualitylab import jobs
    from platform_core.storage import LocalStorage, set_storage

    source = tmp_path / "source.mp4"
    _video(source)
    storage = LocalStorage(str(tmp_path / "storage")); set_storage(storage)
    keys = {"candidate": "qualitylab/u/ephemeral/candidate.mp4",
            "reference": "qualitylab/u/ephemeral/reference.mp4"}
    payload = source.read_bytes()
    for key in keys.values():
        storage.put(key, io.BytesIO(payload), "video/mp4")
    result = jobs.handle({
        "pack": "upscale_video_diagnostic", "source_key": keys["candidate"],
        "source_name": "candidate.mp4", "reference_key": keys["reference"],
        "source_job_performance": {"processing_seconds": 1, "frames": 4},
        "ephemeral_keys": list(keys.values()),
    })
    assert result["overall_verdict"] == "UNKNOWN"
    assert len(result["report"]["source_artifact"]["reference_sha256"]) == 64
    assert all(not storage.exists(key) for key in keys.values())


def test_quality_report_flow_redirects_to_app_owned_report():
    from pathlib import Path

    routes = Path("apps/qualitylab/routes.py").read_text(encoding="utf-8")
    report = Path("apps/qualitylab/templates/qualitylab_report.html").read_text(
        encoding="utf-8")
    assert 'RedirectResponse(f"/qualitylab/reports/{job.id}"' in routes
    assert 'job.status in {"queued", "running"}' in routes
    assert 'response.headers["Refresh"] = "2"' in routes
    assert 'href="/jobs/{{ job.id }}"' in report
