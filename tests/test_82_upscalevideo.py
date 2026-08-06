"""
Đợt C — app `upscalevideo` (nâng video Real-ESRGAN). Kiểm: giá credit, registry nạp
sạch, vendor engine + model có mặt, autotune fallback (không nvidia-smi), service
build_params. Không chạy GPU thật ở đây (smoke riêng trên máy có card).
"""
from __future__ import annotations

import pytest


# ── Giá credit ────────────────────────────────────────────────────────────────

def test_cost_res_va_preset():
    from apps.upscalevideo import cost
    assert cost.uoc_luong_credit(0, 1080, "fast") == cost.MIN_CREDIT
    assert cost.uoc_luong_credit(60, 1080, "fast") == 30            # 1 phút × 30
    assert cost.uoc_luong_credit(60, 1440, "fast") == 54            # ×1.8
    assert cost.uoc_luong_credit(60, 2160, "fast") == 120           # ×4
    assert cost.uoc_luong_credit(60, 1080, "quality") == 75         # ×2.5
    assert cost.uoc_luong_credit(60, 2160, "quality") == 300        # ×4 ×2.5


def test_cost_preview_chi_tinh_8s():
    from apps.upscalevideo import cost
    # preview cắt còn 8s: 8/60 × 30 = 4
    assert cost.uoc_luong_credit(600, 1080, "fast", preview=True) == 4


def test_cost_res_la_ve_1080():
    from apps.upscalevideo import cost
    assert cost.he_so_res(9999) == 1.0


# ── Registry + engine + handler ──────────────────────────────────────────────

def test_app_nap_sach():
    from platform_core.registry import discover, job_type_owners
    a = {x.manifest.slug: x for x in discover()}.get("upscalevideo")
    assert a is not None and a.error == "" and a.router is not None
    assert a.manifest.requires == ("gpu", "ffmpeg")
    assert job_type_owners().get("upscalevideo.render") == "upscalevideo"


def test_vendor_engine_co_mat():
    from apps.upscalevideo import engine
    assert engine.check_engine(), "thiếu vendor/engine (exe + models)"
    assert engine.model_available("realesr-general-x4v3")
    assert engine.model_available("realesrgan-x4plus")


def test_manifest_cost():
    from apps.upscalevideo.manifest import MANIFEST
    assert MANIFEST.credit_cost({"duration_s": 60, "target_height": 2160,
                                 "preset": "quality"}) == 300
    assert MANIFEST.credit_cost({"duration_s": 0}) == 1


# ── autotune: fallback khi không đọc được VRAM ───────────────────────────────

def test_autotune_fast_luon_co_cau_hinh(monkeypatch):
    from apps.upscalevideo import autotune
    from apps.upscalevideo.schemas import Preset
    monkeypatch.setattr(autotune, "query_vram", lambda gpu_uuid="": (16311, 12000))
    t = autotune.pick(Preset.fast, 1920, 1080)
    assert t.model == "realesr-general-x4v3" and t.fast_path and t.tile in (256, 384)


def test_autotune_quality_thieu_vram_canh_bao(monkeypatch):
    from apps.upscalevideo import autotune
    from apps.upscalevideo.schemas import Preset
    monkeypatch.setattr(autotune, "query_vram", lambda gpu_uuid="": (16311, 5000))  # budget 2000
    t = autotune.pick(Preset.quality, 1920, 1080)
    assert t.model == "realesrgan-x4plus" and not t.fast_path and t.warning


def test_autotune_vram_loi_khong_ne(monkeypatch):
    from apps.upscalevideo import autotune
    from apps.upscalevideo.schemas import Preset
    # query_vram tự fallback (4000 free) khi nvidia-smi lỗi → vẫn ra TuneResult
    t = autotune.pick(Preset.fast, 640, 360)
    assert t.tile > 0 and t.threads


# ── service: điểm dùng lại cho seedance ──────────────────────────────────────

def test_service_build_params_chuan_hoa():
    from apps.upscalevideo.service import build_params
    p = build_params(video_key="taovideo/u/j/video.mp4", owner_id="u",
                     preset="xx", target_height=9999, codec="zz", duration_s=12.3)
    assert p["preset"] == "fast" and p["target_height"] == 1080 and p["codec"] == "h264"
    assert p["video_key"] == "taovideo/u/j/video.mp4" and p["duration_s"] == 12.3
    assert p["preserve_fps"] is True and p["preserve_audio"] is True
    changed = build_params(video_key="x", owner_id="u", preserve_fps=False,
                           preserve_audio=False)
    assert changed["preserve_fps"] is False and changed["preserve_audio"] is False


def test_ffmpeg_subprocess_bi_kill_khi_job_cancel(monkeypatch):
    """FFmpeg stage dài phải dừng trong vòng poll, không chạy tiếp sau refund."""
    import subprocess
    from apps.upscalevideo import ff

    class FakeProcess:
        returncode = None
        killed = False
        calls = 0

        def communicate(self, timeout=None):
            self.calls += 1
            if self.killed:
                self.returncode = -9
                return b"", b""
            raise subprocess.TimeoutExpired(["ffmpeg"], timeout or 0)

        def kill(self):
            self.killed = True

    proc = FakeProcess()
    monkeypatch.setattr(ff.subprocess, "Popen", lambda *a, **k: proc)
    checks = iter((False, True))
    with pytest.raises(ff.ProcessingCancelled):
        ff._run(["ffmpeg"], timeout=10, cancel_check=lambda: next(checks))
    assert proc.killed is True


def test_watch_agent_chi_nhan_file_on_dinh_va_toi_da_ba(tmp_path):
    from apps.upscalevideo.watch_agent import stable_candidates

    folder = tmp_path / "watch"; folder.mkdir()
    for i in range(4):
        (folder / f"{i}.mp4").write_bytes(b"video")
    (folder / "ignore.txt").write_text("x", encoding="ascii")
    state = {}
    assert stable_candidates(folder, state) == []
    ready = stable_candidates(folder, state)
    assert len(ready) == 3 and all(path.suffix == ".mp4" for path in ready)
    (folder / "0.mp4").write_bytes(b"partial-write-changed")
    assert folder / "0.mp4" not in stable_candidates(folder, state)


def test_watch_agent_offline_khong_di_chuyen_source(tmp_path, monkeypatch):
    import httpx
    from apps.upscalevideo import watch_agent

    folder = tmp_path / "watch"; folder.mkdir()
    source = folder / "clip.mp4"; source.write_bytes(b"video")
    state_dir = tmp_path / "state"
    # Scan đầu chỉ quan sát; scan hai mới được coi là stable.
    assert watch_agent.run_once(folder, state_dir, "https://invalid", "token") == 0
    monkeypatch.setattr(watch_agent, "submit_batch", lambda *a, **k: (_ for _ in ()).throw(
        httpx.ConnectError("offline")))
    assert watch_agent.run_once(folder, state_dir, "https://invalid", "token") == 2
    assert source.exists() and not (state_dir / "archive").exists()


def test_watch_agent_archive_success_va_pause_khong_quarantine(tmp_path, monkeypatch):
    from apps.upscalevideo import watch_agent

    folder = tmp_path / "watch"; folder.mkdir()
    source = folder / "done.mp4"; source.write_bytes(b"video")
    state_dir = tmp_path / "state"
    watch_agent.run_once(folder, state_dir, "https://server", "token")
    monkeypatch.setattr(watch_agent, "submit_batch", lambda *a, **k: {
        "ok": True, "http_status": 200})
    assert watch_agent.run_once(folder, state_dir, "https://server", "token") == 0
    assert not source.exists() and (state_dir / "archive" / "done.mp4").exists()

    paused = folder / "paused.mp4"; paused.write_bytes(b"video")
    watch_agent.run_once(folder, state_dir, "https://server", "token")
    monkeypatch.setattr(watch_agent, "submit_batch", lambda *a, **k: {
        "ok": False, "http_status": 402})
    assert watch_agent.run_once(folder, state_dir, "https://server", "token") == 3
    assert paused.exists() and not (state_dir / "quarantine" / "paused.mp4").exists()


def test_watch_agent_powershell_thuan_ascii():
    from pathlib import Path
    data = Path("apps/upscalevideo/install_watch_agent.ps1").read_bytes()
    data.decode("ascii")
    assert b"Unregister-ScheduledTask" in data and b"Register-ScheduledTask" in data


def test_admin_gpu_telemetry_parse_du_lieu_khong_chua_ten_file():
    from apps.upscalevideo.telemetry import gpu_snapshot

    class Result:
        returncode = 0
        # HAI card: máy chủ có 2 GPU từ 2026-08-06. Bản cũ đọc dòng đầu nên
        # bảng quản trị chỉ hiện một card — nói dối đúng lúc người vận hành
        # cần biết card nào đang nóng hoặc đầy.
        stdout = ("NVIDIA RTX Test, 42, 67, 16384, 4096\n"
                  "NVIDIA RTX Hai, 7, 40, 16384, 128\n")

    data = gpu_snapshot(run=lambda *a, **k: Result())
    assert data["available"] is True and data["count"] == 2
    assert [g["model"] for g in data["gpus"]] == ["NVIDIA RTX Test", "NVIDIA RTX Hai"]
    assert data["gpus"][1] == {"index": 1, "model": "NVIDIA RTX Hai", "util_percent": 7,
                               "temp_c": 40, "vram_total_mb": 16384, "vram_used_mb": 128}
    # Khoá phẳng giữ lại cho giao diện cũ, trỏ vào card đầu.
    assert data["model"] == "NVIDIA RTX Test" and data["util_percent"] == 42
    assert "filename" not in data and "video_key" not in data


def test_browser_r2_direct_upload_mac_dinh_tat_den_khi_cors_duoc_gate(monkeypatch):
    from apps.upscalevideo.routes import _browser_direct_upload_enabled
    monkeypatch.delenv("LTT_R2_BROWSER_UPLOAD_ENABLED", raising=False)
    assert _browser_direct_upload_enabled() is False
    monkeypatch.setenv("LTT_R2_BROWSER_UPLOAD_ENABLED", "1")
    assert _browser_direct_upload_enabled() is True
