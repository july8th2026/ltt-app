"""Phan THUAN cua `tools/asv_chay_tai_cho.py` — L5, B13 §7.6 F1.

⛔ KHONG chay day chuyen that o day (chu du an dan khong chay lenh nang 28/09).
Chi kiem PHAN THUAN: thu tu giai doan, phan giai `--tu`/`--den`, dung `params`,
va van ban `--thu-kho`. Khong DB, khong GPU, khong tien trinh con.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from apps.auto_scan_video import pipeline
from tools.asv_chay_tai_cho import (dong_ke_hoach, khoang_giai_doan,
                                    tham_so_giai_doan, vram_can_cho_khoang)

GOC = Path(__file__).resolve().parent.parent
TEP = GOC / "tools" / "asv_chay_tai_cho.py"


def test_khong_tu_khong_den_la_ca_chuoi():
    """Rong ca hai dau = toan bo `pipeline.CHUOI`, DUNG THU TU."""
    kq = khoang_giai_doan("", "")
    assert kq == pipeline.CHUOI
    assert [g.ten for g in kq] == list(pipeline.TEN_GIAI_DOAN)


def test_khoang_giua_bao_gom_ca_hai_dau():
    kq = khoang_giai_doan(pipeline.VOICE_SYNTHESIS, pipeline.COMPOSE)
    assert [g.ten for g in kq] == [
        pipeline.VOICE_SYNTHESIS, pipeline.TIMING_ALIGN, pipeline.COMPOSE]


def test_chi_tu_thi_toi_cuoi_chuoi():
    kq = khoang_giai_doan(pipeline.QC, "")
    assert kq[-1].ten == pipeline.QC_AI
    assert kq[0].ten == pipeline.QC


def test_chi_den_thi_tu_dau_chuoi():
    kq = khoang_giai_doan("", pipeline.AUDIO_PREPARE)
    assert [g.ten for g in kq] == [pipeline.MEDIA_PREPARE, pipeline.AUDIO_PREPARE]


def test_mot_giai_doan_duy_nhat():
    kq = khoang_giai_doan(pipeline.RENDER, pipeline.RENDER)
    assert [g.ten for g in kq] == [pipeline.RENDER]


def test_ten_khong_ton_tai_nem_loi_ro_rang():
    try:
        khoang_giai_doan("khong_co_that", "")
    except SystemExit as exc:
        assert "khong_co_that" in str(exc)
        assert pipeline.MEDIA_PREPARE in str(exc)     # goi y danh sach hop le
    else:
        raise AssertionError("phai nem SystemExit")


def test_tu_dung_sau_den_nem_loi_ro_rang():
    try:
        khoang_giai_doan(pipeline.RENDER, pipeline.MEDIA_PREPARE)
    except SystemExit as exc:
        assert "dung SAU" in str(exc)
    else:
        raise AssertionError("phai nem SystemExit")


def test_tham_so_giai_doan_chi_co_dung_hai_khoa():
    """Neo `apps/auto_scan_video/thi_hanh.py:442-445`: `chay_giai_doan` chi doc
    `run_id`/`owner_id` tu `params` — cong cu KHONG duoc nhoi them gi khac."""
    kq = tham_so_giai_doan("r1", "o1")
    assert kq == {"run_id": "r1", "owner_id": "o1"}


def test_tham_so_giai_doan_ep_thanh_chuoi():
    kq = tham_so_giai_doan(123, 456)
    assert kq == {"run_id": "123", "owner_id": "456"}


def test_vram_can_khoang_khong_gpu_la_khong():
    """`content_process`/`edit_plan` (app `auto_scan_video`) khong khai VRAM."""
    kq = khoang_giai_doan(pipeline.CONTENT_PROCESS, pipeline.CONTENT_PROCESS)
    assert vram_can_cho_khoang(kq) == 0


def test_vram_can_khoang_co_gpu_lay_max_khong_tong():
    """Khoang co ca `audio_prepare` (2200) va `transcribe` (7600, lon hon) —
    MOT lease chung phai bang MAX, khong phai TONG hai con so."""
    kq = khoang_giai_doan(pipeline.AUDIO_PREPARE, pipeline.TRANSCRIBE)
    vram = vram_can_cho_khoang(kq)
    assert vram > 0
    assert vram == max(
        vram_can_cho_khoang([g]) for g in kq)


def test_ca_chuoi_can_vram_lon_nhat_toan_pipeline():
    """B13 §1.3/§5: transcribe la giai doan GPU nang nhat (whisperx, 7600 MB) —
    xin lease cho ca 13 giai doan phai bang DUNG con so nay, khong it hon."""
    kq = khoang_giai_doan("", "")
    vram_ca_chuoi = vram_can_cho_khoang(kq)
    only_transcribe = khoang_giai_doan(pipeline.TRANSCRIBE, pipeline.TRANSCRIBE)
    assert vram_ca_chuoi == vram_can_cho_khoang(only_transcribe)


def test_dong_ke_hoach_liet_ke_dung_ten_giai_doan_theo_thu_tu():
    kq = khoang_giai_doan(pipeline.COMPOSE, pipeline.RENDER)
    van_ban = dong_ke_hoach(kq, run_id="r1", owner_id="o1", vram_mb=0)
    vi_tri_compose = van_ban.index(pipeline.COMPOSE)
    vi_tri_render = van_ban.index(pipeline.RENDER)
    assert vi_tri_compose < vi_tri_render
    assert "r1" in van_ban and "o1" in van_ban


def test_dong_ke_hoach_khong_gpu_noi_ro_khong_can():
    van_ban = dong_ke_hoach(
        khoang_giai_doan(pipeline.CONTENT_PROCESS, pipeline.CONTENT_PROCESS),
        run_id="r1", owner_id="o1", vram_mb=0)
    assert "khong giai doan nao trong khoang nay can GPU" in van_ban


def test_dong_ke_hoach_co_gpu_in_so_mb():
    van_ban = dong_ke_hoach(
        khoang_giai_doan(pipeline.TRANSCRIBE, pipeline.TRANSCRIBE),
        run_id="r1", owner_id="o1", vram_mb=7600)
    assert "7600 MB" in van_ban


# ══════════════════════════════════════════════════════════════════════════════
#  `--thu-kho` qua CLI THAT — subprocess, khong DB/GPU (chinh diem cua co nay).
# ══════════════════════════════════════════════════════════════════════════════

def _chay_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TEP), "chay", "--thu-kho", *args],
        cwd=str(GOC), capture_output=True, text=True, encoding="utf-8",
        timeout=60)


def test_cli_thu_kho_voi_video_in_ke_hoach_va_thoat_0():
    kq = _chay_cli("--video", "khong-ton-tai.mp4")
    assert kq.returncode == 0, kq.stderr
    assert "KE HOACH" in kq.stdout
    assert pipeline.MEDIA_PREPARE in kq.stdout
    assert pipeline.QC_AI in kq.stdout


def test_cli_thu_kho_voi_run_id_khong_can_video():
    kq = _chay_cli("--run-id", "abc123")
    assert kq.returncode == 0, kq.stderr
    assert "abc123" in kq.stdout


def test_cli_thieu_video_va_run_id_bao_loi_ro():
    kq = subprocess.run(
        [sys.executable, str(TEP), "chay"],
        cwd=str(GOC), capture_output=True, text=True, encoding="utf-8",
        timeout=60)
    assert kq.returncode != 0
    assert "--video" in kq.stderr and "--run-id" in kq.stderr


def test_cli_thu_kho_ton_trong_khoang_tu_den():
    kq = _chay_cli("--run-id", "abc123", "--tu", pipeline.VOICE_SYNTHESIS,
                   "--den", pipeline.COMPOSE)
    assert kq.returncode == 0, kq.stderr
    assert pipeline.MEDIA_PREPARE not in kq.stdout
    assert pipeline.VOICE_SYNTHESIS in kq.stdout
    assert pipeline.COMPOSE in kq.stdout
