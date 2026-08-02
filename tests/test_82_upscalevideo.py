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
    monkeypatch.setattr(autotune, "query_vram", lambda: (16311, 12000))
    t = autotune.pick(Preset.fast, 1920, 1080)
    assert t.model == "realesr-general-x4v3" and t.fast_path and t.tile in (256, 384)


def test_autotune_quality_thieu_vram_canh_bao(monkeypatch):
    from apps.upscalevideo import autotune
    from apps.upscalevideo.schemas import Preset
    monkeypatch.setattr(autotune, "query_vram", lambda: (16311, 5000))  # budget 2000
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
