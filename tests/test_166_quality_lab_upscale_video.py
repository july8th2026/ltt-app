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
    vmaf = {item.key: item for item in by_key["full_reference"].metrics}[
        "vmaf_v0_6_1"]
    assert vmaf.verdict == "UNKNOWN"
    assert vmaf.value is not None and vmaf.value > 95
    assert len(vmaf.evidence["ffmpeg_binary_sha256"]) == 64


def test_external_peak_vram_evidence_is_visible_but_never_auto_passes(tmp_path):
    from apps.qualitylab.services.upscale_video import inspect_upscale_video_pair

    candidate = tmp_path / "candidate.mp4"
    reference = tmp_path / "reference.mp4"
    _video(candidate); shutil.copyfile(candidate, reference)
    dimensions, _summary = inspect_upscale_video_pair(
        candidate, reference, None, tmp_path / "work",
        {"processing_seconds": 34.12, "frames": 24, "peak_vram_mb": 11180})
    performance = {item.key: item for item in dimensions[-1].metrics}
    assert performance["peak_vram_mb"].value == 11180
    assert performance["peak_vram_mb"].verdict == "UNKNOWN"


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


def test_vmaf_evaluator_snapshot_pins_binary_and_model():
    from apps.qualitylab.registry import pack_evaluators

    evaluators = {item["key"]: item for item in pack_evaluators(
        "upscale_video_diagnostic")}
    snapshot = evaluators["ffmpeg_libvmaf"]
    assert snapshot["enabled"] is True
    assert len(snapshot["model_sha256"]) == 64
    assert "model=vmaf_v0.6.1" in snapshot["version"]


def _van_tay_moi(monkeypatch):
    """Module vân tay, đã xoá trí nhớ — mọi bài dưới đây phải bắt đầu từ trắng."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg unavailable")
    from apps.qualitylab.services import upscale_video as uv
    monkeypatch.setattr(uv, "_VAN_TAY_DU", None)
    return uv


def test_do_phien_ban_truot_KHONG_duoc_xoa_hash_da_tinh(monkeypatch):
    """🔴 Tật 1 (gate 24/09): một `except` gánh hai tình huống khác loại.

    Bản cũ bọc CẢ việc băm tệp lẫn việc dò `-version` trong một `try`, nên một
    lần dò quá hạn **xoá luôn cái hash đã tính xong** — báo cáo chất lượng mất
    bằng chứng vì một chuyện chẳng liên quan.
    """
    uv = _van_tay_moi(monkeypatch)

    def _qua_han(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="ffmpeg -version", timeout=60)

    monkeypatch.setattr(uv.subprocess, "run", _qua_han)
    van_tay = uv.libvmaf_runtime_fingerprint()
    assert len(van_tay["binary_sha256"]) == 64, "hash bi xoa boi mot loi khac"
    assert van_tay["ffmpeg_version"] == "unavailable"
    assert van_tay["ghi_chu_loi"] == "version:TimeoutExpired"


def test_mot_luot_truot_KHONG_duoc_nho_vao_cache(monkeypatch, tmp_path):
    """🔴 Tật 2: `lru_cache` nhớ cả kết quả THIẾU.

    Đây là lời giải đơn giản nhất cho việc HAI phép cùng đỏ ở cùng worker trong
    lượt gate 24/09: một trục trặc, một cache, mọi lời gọi sau đều rỗng.
    """
    uv = _van_tay_moi(monkeypatch)
    that = uv.media.ffmpeg_bin

    monkeypatch.setattr(uv.media, "ffmpeg_bin",
                        lambda: str(tmp_path / "khong-ton-tai.exe"))
    hong = uv.libvmaf_runtime_fingerprint()
    assert hong["binary_sha256"] == ""
    assert "hash:FileNotFoundError" in hong["ghi_chu_loi"]

    monkeypatch.setattr(uv.media, "ffmpeg_bin", that)
    lai = uv.libvmaf_runtime_fingerprint()
    assert len(lai["binary_sha256"]) == 64, "ket qua THIEU da bi nho lai"


def test_van_tay_DU_thi_duoc_nho(monkeypatch):
    """🔑 Đối chứng cho bài trên: nếu KHÔNG bao giờ nhớ thì nó cũng xanh.

    Băm một tệp 211 MB mỗi lần gọi là thật sự đắt, nên phải chốt rằng đường
    thành công VẪN nhớ — nếu không, bài chống-nhớ-kết-quả-thiếu ở trên sẽ xanh
    vì một lý do sai.
    """
    uv = _van_tay_moi(monkeypatch)
    dau = uv.libvmaf_runtime_fingerprint()
    assert len(dau["binary_sha256"]) == 64
    assert "ghi_chu_loi" not in dau

    def _no_neu_goi_lai(*args, **kwargs):
        raise AssertionError("da bam lai du lan truoc thanh cong")

    monkeypatch.setattr(uv.hashlib, "sha256", _no_neu_goi_lai)
    assert uv.libvmaf_runtime_fingerprint() == dau
