"""ASV final (lan ky-thuat) — T13 `blackdetect`/`freezedetect` + T17 giai ma ca tep.

Hop dong cua adapter `qc.do_hinh`: tham so = mac dinh tai lieu ffmpeg, mot luot
giai ma, so voi NGUON. Chan ly nen o day do CHINH ffmpeg lavfi sinh ra, nen moi
bai biet chinh xac khoang den / dong bang nam o dau.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import che_do_render as cdr, qc  # noqa: E402
from tests.fixtures import asv_media as fx  # noqa: E402


def _tao(dest: Path, video: str, *, dai: float = 6.0) -> Path:
    ff = fx.require_ffmpeg()
    subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", video,
                    "-f", "lavfi", "-i", f"sine=frequency=440:duration={dai}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-shortest", str(dest)], check=True, capture_output=True)
    return dest


# ── Ham thuan: doc stderr ──────────────────────────────────────────────────────

def test_doc_do_hinh_cong_khoang_va_dem_loi():
    err = ("[blackdetect @ 0] [info] black_start:0 black_end:2.5 black_duration:2.5\n"
           "[blackdetect @ 0] [info] black_start:7 black_end:10 black_duration:3\n"
           "[freezedetect @ 0] [info] lavfi.freezedetect.freeze_start: 1\n"
           "[freezedetect @ 0] [info] lavfi.freezedetect.freeze_end: 4\n"
           "[h264 @ 0] [error] Invalid NAL unit size\n")
    r = qc.doc_do_hinh(err, thoi_luong=10.0)
    assert r["den_s"] == 5.5 and r["dong_s"] == 3.0
    assert r["so_loi_giai_ma"] == 1


def test_dong_bang_toi_HET_tep_khong_co_freeze_end_van_duoc_tinh():
    """⚠️ freezedetect khong in `freeze_end` cho khoang keo toi het tep."""
    err = "[freezedetect @ 0] [info] lavfi.freezedetect.freeze_start: 6\n"
    assert qc.doc_do_hinh(err, thoi_luong=10.0)["dong_s"] == 4.0


def test_tham_so_la_MAC_DINH_tai_lieu_ffmpeg():
    """Chot rang tham so khong bi ai lang le chinh (moi doi phai qua bang do)."""
    assert qc.BLACKDETECT == "blackdetect=d=2.0:pic_th=0.98:pix_th=0.10"
    assert qc.FREEZEDETECT == "freezedetect=n=-60dB:d=2"
    cmd = qc.lenh_do_hinh("x.mp4")
    assert "-map" not in cmd, "T17 phai giai ma CA hinh lan tieng"
    assert cmd[cmd.index("-loglevel") + 1] == "level+info"


# ── ffmpeg that ────────────────────────────────────────────────────────────────

def test_video_binh_thuong_khong_den_khong_dong_khong_loi(tmp_path):
    r = qc.do_hinh(str(_tao(tmp_path / "a.mp4", "testsrc2=s=320x240:r=24:d=6")),
                   thoi_luong=6.0)
    assert r["den_s"] == 0 and r["dong_s"] == 0
    assert r["so_loi_giai_ma"] == 0 and r["ma_thoat"] == 0


def test_bat_duoc_khoang_DEN_va_DONG_BANG_that(tmp_path):
    den = _tao(tmp_path / "den.mp4",
               "testsrc2=s=320x240:r=24:d=3[a];color=black:s=320x240:r=24:d=4[b];"
               "[a][b]concat=n=2:v=1:a=0", dai=7.0)
    r = qc.do_hinh(str(den), thoi_luong=7.0)
    assert 3.5 <= r["den_s"] <= 4.5
    dong = _tao(tmp_path / "dong.mp4",
                "testsrc2=s=320x240:r=24:d=3,tpad=stop_mode=clone:stop_duration=4",
                dai=7.0)
    r2 = qc.do_hinh(str(dong), thoi_luong=7.0)
    assert r2["dong_s"] >= 3.5 and r2["den_s"] == 0


def test_tep_bi_CUT_thi_T17_HONG(tmp_path):
    """ffprobe (T1) chi doc dau container; chi giai ma ca tep moi thay tep cut."""
    goc = _tao(tmp_path / "goc.mkv", "testsrc2=s=320x240:r=24:d=6")
    b = goc.read_bytes()
    cut = tmp_path / "cut.mkv"
    # Xoa mot khuc giua luong => goi hong giua chung.
    cut.write_bytes(b[:len(b) // 3] + b[len(b) // 3 + 4000:])
    r = qc.do_hinh(str(cut), thoi_luong=6.0)
    bc = qc.kiem(tt_ra={"co_video": True, "co_tieng": True, "thoi_luong": 6.0},
                 tt_nguon={"co_video": True, "co_tieng": True, "thoi_luong": 6.0},
                 am_luong={"lufs": qc.LUFS_DICH, "dinh_that": -2.0},
                 ke_hoach={"doan": []}, ban_ke_tieng={"doan": []},
                 hinh_ra=r, hinh_nguon=r)
    t17 = next(m for m in bc["muc"] if m["ma"] == "T17")
    assert t17["trang_thai"] == qc.HONG, r


def test_T13_so_voi_NGUON_ban_ra_den_ma_nguon_khong_thi_HONG(tmp_path):
    nguon = qc.do_hinh(str(_tao(tmp_path / "n.mp4", "testsrc2=s=320x240:r=24:d=7")),
                       thoi_luong=7.0)
    ra = qc.do_hinh(str(_tao(tmp_path / "r.mp4",
                             "testsrc2=s=320x240:r=24:d=3[a];color=black:s=320x240:r=24:d=4[b];"
                             "[a][b]concat=n=2:v=1:a=0", dai=7.0)), thoi_luong=7.0)
    bc = qc.kiem(tt_ra={"co_video": True, "co_tieng": True, "thoi_luong": 7.0},
                 tt_nguon={"co_video": True, "co_tieng": True, "thoi_luong": 7.0},
                 am_luong={"lufs": qc.LUFS_DICH, "dinh_that": -2.0},
                 ke_hoach={"doan": []}, ban_ke_tieng={"doan": []},
                 che_do_render=cdr.CAT_MA_HOA_LAI, hinh_ra=ra, hinh_nguon=nguon)
    t13 = next(m for m in bc["muc"] if m["ma"] == "T13")
    assert t13["trang_thai"] == qc.HONG
    assert t13["ti_le_den_ra"] > 0.4


def test_KHONG_con_ban_YAVG_tu_che():
    """Loai B da thay => xoa het, khong de hai bo do song song."""
    van = (Path(qc.__file__)).read_text(encoding="utf-8")
    for cu in ("signalstats", "DO_SANG_TOI_THIEU", "do_sang_trung_binh",
               "SO_KHUNG_DO_SANG"):
        assert cu not in van, cu
    assert qc.PHIEN_BAN_QC >= 4


@pytest.mark.parametrize("ma", ["T13", "T17"])
def test_khong_do_duoc_thi_KHONG_AP_DUNG(ma):
    bc = qc.kiem(tt_ra={"co_video": True, "co_tieng": True, "thoi_luong": 6.0},
                 tt_nguon={"co_video": True, "co_tieng": True, "thoi_luong": 6.0},
                 am_luong={"lufs": qc.LUFS_DICH, "dinh_that": -2.0},
                 ke_hoach={"doan": []}, ban_ke_tieng={"doan": []})
    assert next(m for m in bc["muc"] if m["ma"] == ma)["trang_thai"] == qc.KHONG_AP_DUNG
