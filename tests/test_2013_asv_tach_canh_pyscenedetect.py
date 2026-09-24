"""ASV final (lan ky-thuat) — hop dong adapter tach canh PySceneDetect.

Chan ly nen do ffmpeg lavfi sinh ra voi moc cat BIET TRUOC (cung khuon benchmark
trong `docs/auto_scan_video_final/L_KY_THUAT.md`), thu nho de chay trong vai giay.

🔑 Ca "talking head" la ca ban cu (`select=gt(scene,0.4)`) bo sot 2/2 trong
   benchmark — bai nay chot rang bo tach moi bat duoc no.
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import canh as c, thi_hanh, pipeline  # noqa: E402
from tests.fixtures import asv_media as fx  # noqa: E402

pytest.importorskip("scenedetect")

SZ, R = "320x180", 24


def _dau(mau: str, x: int) -> str:
    return (f"color=c={mau}:s={SZ}:r={R}:d=5,"
            f"drawbox=x={x}+4*sin(2*t):y=50+2*sin(3*t):w=50:h=60:c=0xd0a080:t=fill")


def _tao(dest: Path, fc: str, inputs: list[str]) -> Path:
    ff = fx.require_ffmpeg()
    cmd = [ff, "-hide_banner", "-loglevel", "error", "-y"]
    for i in inputs:
        cmd += ["-f", "lavfi", "-i", f"{i},format=yuv420p,setsar=1"]
    cmd += ["-filter_complex", fc, "-map", "[o]", "-c:v", "libx264",
            "-crf", "23", "-pix_fmt", "yuv420p", str(dest)]
    subprocess.run(cmd, check=True, capture_output=True)
    return dest


def _gan(moc, dung, tol=0.2):
    return all(any(abs(m - d) <= tol for m in moc) for d in dung)


def test_talking_head_va_cat_cung_duoc_bat(tmp_path):
    v = _tao(tmp_path / "th.mp4", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[o]",
             [_dau("0x506070", 130), _dau("0x705040", 110),
              f"testsrc2=s={SZ}:r={R}:d=5"])
    moc = c.tim_moc(str(v))
    assert _gan(moc, [5.0, 10.0]), moc
    assert len(moc) == 2, f"bao du: {moc}"


def test_canh_quay_lia_KHONG_bi_bao_cat(tmp_path):
    v = _tao(tmp_path / "pan.mp4",
             "[0:v]scale=1280:720,crop=320:180:x='t*60':y='t*25'[o]",
             [f"testsrc2=s=640x360:r={R}:d=10"])
    assert c.tim_moc(str(v)) == []


def test_phan_tich_tat_dinh_va_ghi_bo_tach(tmp_path):
    v = _tao(tmp_path / "hc.mp4", "[0:v][1:v]concat=n=2:v=1:a=0[o]",
             [f"testsrc2=s={SZ}:r={R}:d=4", f"mandelbrot=s={SZ}:r={R},trim=duration=4"])
    a, b = c.phan_tich(str(v), thoi_luong=8.0), c.phan_tich(str(v), thoi_luong=8.0)
    assert c.sang_json(a) == c.sang_json(b)
    c.kiem_chi_muc(a)
    assert len(a.canh) == 2 and abs(a.canh[1].bat - 4.0) <= 0.2
    assert a.tom_tat()["bo_tach"] == c.BO_TACH


def test_huy_giua_chung_thi_NEM(tmp_path):
    v = _tao(tmp_path / "d.mp4", "[0:v]null[o]", [f"testsrc2=s={SZ}:r={R}:d=20"])
    with pytest.raises(c.CanhError):
        c.tim_moc(str(v), hoi_huy=lambda: True)


def test_tep_khong_mo_duoc_thi_NEM(tmp_path):
    hong = tmp_path / "hong.mp4"
    hong.write_bytes(b"khong phai video")
    with pytest.raises(c.CanhError):
        c.tim_moc(str(hong))


def test_doi_bo_tach_thi_cache_giai_doan_DOI(monkeypatch):
    a = thi_hanh.phien_ban_engine(pipeline.EDIT_PLAN)
    assert c.PHIEN_BAN_CANH in a
    monkeypatch.setattr(c, "PHIEN_BAN_CANH", c.PHIEN_BAN_CANH + "x")
    assert thi_hanh.phien_ban_engine(pipeline.EDIT_PLAN) != a


def test_KHONG_con_duong_ffmpeg_select_cu():
    """Loai B da thay => xoa het, khong de hai bo tach song song."""
    van = (Path(c.__file__)).read_text(encoding="utf-8")
    assert "select='gt(scene" not in van and "doc_moc_tu_ffmpeg" not in van
    cay = ast.parse(van)
    ten = {n.name for n in ast.walk(cay) if isinstance(n, ast.FunctionDef)}
    assert "tim_moc" in ten and "doc_moc_tu_ffmpeg" not in ten
