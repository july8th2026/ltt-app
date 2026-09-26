"""Cong ky thuat Upscale chay tren TEP THAT — mat xich runtime, khong mock.

⭐ VI SAO CAN TEP NAY

`tests/test_4904_upscale_correction.py` khoa hanh vi cong bang cach **mock**
`ff.probe_video`. Mock chung minh duoc logic phan nhanh, nhung KHONG chung minh
duoc ba thu chi lo ra khi cham tep that:

  1. phep toan ti le + lam tron cua `scale=-2:H` (chieu rong ra so LE thi sao?);
  2. `ffprobe` doc ten codec THAT (`hevc` vs `h264`) co dung nhu ta gia dinh;
  3. dung sai thoi luong co bi lech vi lam tron GOP khong.

Ma cong nay co quyen **danh do job cua khach**. Mot cong chua tung chay that ma
duoc phep lam do job la dung loai "tinh nang tren giay" ma dot sua nay di don.

⛔ KHONG dung video trong `Desktop\\TEST VIDEO`: mot phep kiem phu thuoc thu muc
   ca nhan thi may khac chay se do oan. Ta TU SINH nguon bang `testsrc` cua
   ffmpeg, nen no chay o dau cung duoc.

Phai chung minh CA HAI chieu: dau ra dung thi cong IM (khong bao dong gia), dau
ra sai thi cong BAT (khong phai cong giay).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="can ffmpeg+ffprobe that de kiem mat xich runtime")

# Nguon 836x576: ti le LE co y — 1568/1080 khong phai so tron, nen no kiem luon
# duong lam tron `-2` cua `scale`. Mot nguon 16:9 se giau mat loi lam tron.
SRC_W, SRC_H = 836, 576
TARGET_H = 1080


def _ffmpeg(args: list[str]) -> None:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + args,
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        pytest.fail(f"ffmpeg loi: {r.stderr[-400:]}")


def _tao_nguon(p: Path) -> None:
    _ffmpeg(["-f", "lavfi", "-i", f"testsrc=size={SRC_W}x{SRC_H}:rate=30:duration=2",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
             "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30",
             "-c:a", "aac", "-shortest", str(p)])


def _tao_dau_ra(src: Path, out: Path, cao: int, enc: str, co_tieng: bool = True) -> None:
    args = ["-i", str(src), "-vf", f"scale=-2:{cao}", "-c:v", enc]
    if enc in ("libx264", "libx265"):
        args += ["-preset", "ultrafast", "-crf", "30"]
    args += (["-c:a", "aac"] if co_tieng else ["-an"]) + [str(out)]
    _ffmpeg(args)


@pytest.fixture(scope="module")
def nguon(tmp_path_factory) -> Path:
    p = tmp_path_factory.mktemp("cong_that") / "src.mp4"
    _tao_nguon(p)
    return p


def _soi(out: Path, *, encoder: str = "libx264", audio: bool = True,
         duration: float = 2.0) -> dict:
    from apps.upscalevideo import quality_gate
    return quality_gate.kiem_tra_dau_ra(
        str(out), target_h=TARGET_H, src_w=SRC_W, src_h=SRC_H,
        expect_encoder=encoder, expect_audio=audio, expect_duration_s=duration)


def test_dau_ra_dung_thi_cong_IM_khong_bao_dong_gia(nguon, tmp_path):
    """Ti le LE (836x576 -> 1568x1080) van phai DAT.

    Ngan hoi quy: neu phep toan ti le sai hoac dung sai lam tron qua chat, cong
    se danh do job TOT cua khach. Bao dong gia con te hon khong co cong — no lam
    nguoi ta TAT cong di.
    """
    out = tmp_path / "dung.mp4"
    _tao_dau_ra(nguon, out, TARGET_H, "libx264")
    k = _soi(out)
    assert k["ok"] is True, k["loi"]
    assert k["loi"] == []
    assert k["do"]["h"] == TARGET_H
    # `-2` lam tron chieu rong ve so chan gan nhat; ta chi doi sai so <= 2 px.
    assert abs(k["do"]["w"] - round(SRC_W * TARGET_H / SRC_H)) <= 2


def test_sai_chieu_cao_thi_cong_DANH_DO(nguon, tmp_path):
    """Hua 1080 ma giao 720 => DO. Day la ISSUE M (truoc chi kiem `isfile()`)."""
    out = tmp_path / "sai_cao.mp4"
    _tao_dau_ra(nguon, out, 720, "libx264")
    k = _soi(out)
    assert k["ok"] is False
    assert any("chiều cao" in x for x in k["loi"]), k["loi"]


def test_codec_THAT_khac_encoder_khai_thi_DANH_DO(nguon, tmp_path):
    """ISSUE J bat o RUNTIME: khai libx264 ma luong ra `hevc` => DO.

    Day la luoi cuoi cho ca "xin HEVC nhan H.264": du chuoi chon encoder co
    lech, cong van doc codec THAT tu tep chu khong tin loi khai.
    """
    out = tmp_path / "hevc.mp4"
    _tao_dau_ra(nguon, out, TARGET_H, "libx265")
    k = _soi(out, encoder="libx264")
    assert k["ok"] is False
    assert any("codec" in x for x in k["loi"]), k["loi"]
    assert k["do"]["vcodec"] == "hevc"


def test_thieu_tieng_chi_CANH_BAO_chu_khong_lam_do_job(nguon, tmp_path):
    """Lech MEM khong duoc lam do mot job co hinh anh tot.

    Khach van nhan duoc video; ta bao "thieu tieng" chu khong vut ca job.
    """
    out = tmp_path / "khong_tieng.mp4"
    _tao_dau_ra(nguon, out, TARGET_H, "libx264", co_tieng=False)
    k = _soi(out, audio=True)
    assert k["ok"] is True
    assert any("audio" in x for x in k["canh_bao"]), k["canh_bao"]


def test_tep_hong_bi_bat_truoc_khi_goi_ffprobe(nguon, tmp_path):
    """Tep cut ngang => DO ngay o buoc kich thuoc, khong ton mot lan ffprobe."""
    tot = tmp_path / "tot.mp4"
    _tao_dau_ra(nguon, tot, TARGET_H, "libx264")
    hong = tmp_path / "hong.mp4"
    hong.write_bytes(tot.read_bytes()[:5000])
    k = _soi(hong)
    assert k["ok"] is False
    assert "vcodec" not in k["do"]          # chua he goi ffprobe
