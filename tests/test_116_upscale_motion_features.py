"""Engine/cost/contract gate cho UP-FEAT-002 motion enhancements."""
from __future__ import annotations

import subprocess
from pathlib import Path


def test_motion_enhancement_credit_multipliers_are_explicit():
    from apps.upscalevideo.cost import uoc_luong_credit

    assert uoc_luong_credit(60, 1080, "fast") == 30
    assert uoc_luong_credit(60, 1080, "fast", stabilize=True) == 36
    assert uoc_luong_credit(60, 1080, "fast", smooth_motion=True) == 66
    assert uoc_luong_credit(60, 1080, "fast", stabilize=True,
                            smooth_motion=True) == 80


def test_service_keeps_motion_flags_in_owner_scoped_job_params():
    from apps.upscalevideo.service import build_params

    defaults = build_params(video_key="upscalevideo/u/a.mp4", owner_id="u")
    enabled = build_params(video_key="upscalevideo/u/a.mp4", owner_id="u",
                           stabilize=True, smooth_motion=True)
    assert defaults["stabilize"] is False and defaults["smooth_motion"] is False
    assert enabled["stabilize"] is True and enabled["smooth_motion"] is True


def test_manifest_hold_cost_includes_motion_features():
    from apps.upscalevideo.manifest import MANIFEST

    assert MANIFEST.credit_cost({"duration_s": 60, "target_height": 1080,
                                 "preset": "fast", "stabilize": True,
                                 "smooth_motion": True}) == 80


def test_fps_rate_multiplier_preserves_rational_rate():
    from apps.upscalevideo.ff import multiply_rate

    assert multiply_rate("24000/1001") == "48000/1001"
    assert multiply_rate("30") == "60"
    assert multiply_rate("invalid") == "60"


def test_stabilization_is_two_pass_relative_transform_on_windows(tmp_path, monkeypatch):
    from apps.upscalevideo import ff

    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        if "vidstabtransform" in " ".join(command):
            Path(command[-1]).write_bytes(b"video")
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(ff, "_run", fake_run)
    out = tmp_path / "stable.mp4"
    ff.stabilize_video(str(tmp_path / "source.mp4"), str(out), max_seconds=8)
    assert out.exists() and len(calls) == 2
    assert "vidstabdetect" in " ".join(calls[0][0])
    assert "result=motion.trf" in " ".join(calls[0][0])
    assert "vidstabtransform" in " ".join(calls[1][0])
    assert calls[0][1]["cwd"] == str(tmp_path)


def test_ui_exposes_real_motion_controls_and_honest_hdr_defer():
    page = Path("apps/upscalevideo/templates/upscalevideo.html").read_text(
        encoding="utf-8")
    assert 'id="stabilize" name="stabilize"' in page
    assert 'id="smooth_motion" name="smooth_motion"' in page
    assert "data.append('stabilize','1')" in page
    assert "data.append('smooth_motion','1')" in page
    assert "không nâng SDR giả thành HDR" in page
