"""Regression H32.6 for customer Upscale controls and runtime evidence tooling."""
from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_customer_ui_hides_internal_infrastructure_and_fake_entitlement():
    page = _read("apps/upscalevideo/templates/upscalevideo.html")

    assert '<span class="up-pro">PRO</span>' not in page
    assert "R2 CORS" not in page
    assert 'href="/jobs?app=upscalevideo"' in page
    assert 'href="/jobs/{{j.id}}"' in page


def test_mobile_hidden_settings_are_removed_from_keyboard_and_a11y_tree():
    page = _read("apps/upscalevideo/templates/upscalevideo.html")

    assert "form.toggleAttribute('inert',hidden)" in page
    assert "form.setAttribute('aria-hidden','true')" in page
    assert "form.removeAttribute('aria-hidden')" in page
    assert "if(!open)settingsToggle.focus()" in page


def test_file_probe_releases_blob_only_after_detaching_media():
    page = _read("apps/upscalevideo/templates/upscalevideo.html")

    assert "video.removeAttribute('src');video.load()" in page
    assert "setTimeout(()=>URL.revokeObjectURL(url),0)" in page
    assert "window.addEventListener('beforeunload'" in page


def test_option_matrix_covers_customer_visible_compatibility_surface():
    spec = importlib.util.spec_from_file_location(
        "upscale_option_matrix", ROOT / "tools" / "upscale_option_matrix.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cases = module._cases()
    core = {(item["preset"], item["height"], item["codec"])
            for item in cases if not item["flags"]}

    assert core == {(preset, height, codec)
                    for preset in ("fast", "quality")
                    for height in (1080, 1440, 2160)
                    for codec in ("h264", "hevc")}
    flags = {flag for item in cases for flag in item["flags"]}
    assert {"--no-preserve-fps", "--no-preserve-audio", "--preview",
            "--stabilize", "--smooth-motion"} <= flags


def test_gpu_lease_contract_splits_fast_and_quality_from_legacy_lane():
    from apps.upscalevideo.manifest import MANIFEST

    assert MANIFEST.vram_for("upscalevideo.render") == 12000
    assert MANIFEST.vram_for("upscalevideo.render.fast") == 2000
    assert MANIFEST.vram_for("upscalevideo.render.quality") == 12000


def test_motion_smoothing_doubles_source_cadence_instead_of_forcing_60fps():
    from apps.upscalevideo.jobs import _output_fps

    assert _output_fps("24/1", False, True) == "48/1"
    assert _output_fps("24000/1001", False, True) == "48000/1001"
    assert _output_fps("24/1", False, False) == "30"
    assert _output_fps("24/1", True, False) == "24/1"


def test_qualitylab_cli_hashes_artifacts_without_embedding_paths(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "qualitylab_upscale_video_cli",
        ROOT / "tools" / "qualitylab_upscale_video_cli.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    artifact = tmp_path / "sample.bin"
    artifact.write_bytes(b"LTT")

    assert module._sha256(artifact) == (
        "9aa875234c360ed734b9ff8da5ddcc92db8ae5bfdad7dc2afd2c892a99f21dae")
