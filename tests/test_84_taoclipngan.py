"""
TAO CLIP NGAN (app `taoclipngan` + engine vendored `cutclipshort`). Kiem phan KHONG
can torch/GPU (test suite chay python he thong, khong co torch): gia credit, registry
nap sach, manifest cost, engine vendored co mat tren dia (khong import — can torch),
requirements co ML dep. Nghiem thu chay THAT = smoke GPU + browser.
"""
from __future__ import annotations

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_cost_theo_phut_tier_clip():
    from apps.taoclipngan import cost
    # 300s(5phut) fast 3clip = 5*1.0*5 + 3*5 = 25+15 = 40
    assert cost.uoc_luong_credit(300, "fast", 3) == 40
    # balanced = 5*1.6*5 + 15 = 40+15 = 55
    assert cost.uoc_luong_credit(300, "balanced", 3) == 55
    # high_quality = 5*2.2*5 + 15 = 55+15 = 70
    assert cost.uoc_luong_credit(300, "high_quality", 3) == 70
    assert cost.uoc_luong_credit(0, "fast", 0) == cost.MIN_CREDIT


def test_cost_them_clip_tang_gia():
    from apps.taoclipngan import cost
    a = cost.uoc_luong_credit(120, "balanced", 2)
    b = cost.uoc_luong_credit(120, "balanced", 5)
    assert b == a + 3 * cost.DON_GIA_CLIP


def test_app_nap_sach():
    from platform_core.registry import discover, job_type_owners
    a = {x.manifest.slug: x for x in discover()}.get("taoclipngan")
    assert a is not None and a.error == "" and a.router is not None
    assert a.manifest.requires == ("gpu", "ffmpeg")
    assert job_type_owners().get("taoclipngan.render") == "taoclipngan"


def test_manifest_cost():
    from apps.taoclipngan.manifest import MANIFEST
    assert MANIFEST.credit_cost({"duration_s": 300, "tier": "high_quality",
                                 "target_clip_count": 3}) == 70
    # duration_s=0 nhung mac dinh 3 clip -> 3*5 = 15
    assert MANIFEST.credit_cost({"duration_s": 0}) == 15


def test_engine_vendored_co_mat():
    """Engine cutclipshort da vendor vao repo (khong import — can torch/GPU)."""
    eng = ROOT / "cutclipshort"
    assert eng.is_dir()
    for sub in ("core", "analysis", "editorial", "render", "adapters", "types"):
        assert (eng / sub).is_dir(), f"thieu cutclipshort/{sub}"
    # 3 ham loi ton tai (file check)
    assert (eng / "core" / "analysis_runner.py").is_file()
    assert (eng / "editorial" / "brain.py").is_file()
    assert (eng / "render" / "segment_renderer.py").is_file()
    # da bo GUI/license (khong can server)
    assert not (eng / "gui").exists()
    assert not (eng / "license").exists()


def test_requirements_co_ml_dep():
    txt = (ROOT / "requirements-server.txt").read_text(encoding="utf-8")
    for pkg in ("faster-whisper", "ultralytics", "scenedetect", "demucs"):
        assert pkg in txt, f"thieu {pkg} trong requirements-server.txt"


def test_jobs_aspect_map_day_du():
    """jobs khai du 4 aspect (khong import handle — no torch; doc bang _ASPECT qua AST)."""
    src = (ROOT / "apps" / "taoclipngan" / "jobs.py").read_text(encoding="utf-8")
    for a in ("9:16", "1:1", "16:9", "4:5"):
        assert a in src


def test_nvenc_probe_uses_supported_frame_size(monkeypatch):
    """Không dò NVENC bằng 64x64: RTX 50xx trả âm giả rồi render CPU."""
    from cutclipshort.adapters.ffmpeg_hw import FFmpegHWAdapter

    commands = []

    def fake_run(args, **_kwargs):
        commands.append(args)
        pathlib.Path(args[-1]).write_bytes(b"encoded")

    monkeypatch.setattr("cutclipshort.adapters.ffmpeg_hw.subprocess.run", fake_run)
    adapter = FFmpegHWAdapter("ffmpeg")
    # executable_path không tồn tại sẽ dò PATH; không liên quan lệnh fake.
    monkeypatch.setattr(adapter, "_find_executable", lambda: "ffmpeg")
    assert adapter._test_encoder("h264_nvenc") is True
    assert "color=black:s=256x256:d=0.1" in commands[0]
    assert "yuv420p" in commands[0]


def test_render_resolution_preserves_every_customer_aspect_with_square_pixels():
    from cutclipshort.render.segment_renderer import _resolve_target_resolution
    from cutclipshort.types import ClipSpec, RenderSettings, TimeRange

    expected = {(1080, 1920): (1080, 1920), (1080, 1080): (1080, 1080),
                (1920, 1080): (1920, 1080), (1080, 1350): (1080, 1350)}
    settings = RenderSettings(target_resolution="1080p")
    for (width, height), output in expected.items():
        clip = ClipSpec(clip_id="aspect", source_range=TimeRange(0, 10),
                        target_width=width, target_height=height)
        assert _resolve_target_resolution(settings, clip, 10_000) == output
