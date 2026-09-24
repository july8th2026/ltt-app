"""ASV final — bo do giong + SQUIM chay THAT trong qc-venv (phep kiem NANG).

Tieng that: SAPI en-US (Windows) — tieng noi that, khong ban quyen, khong mang.
Chot hai chieu: doc DUNG kich ban -> WER thap; cat mat nua sau tep tieng (nuot
chu that) -> WER cao. Va SQUIM cham tieng sach cao hon tieng tron nhieu trang.

Chay:  set LTT_TEST_NANG=1  (nap whisper large-v3 + SQUIM len card).
"""
from __future__ import annotations

import subprocess

import pytest

from tests import rao_chan_nang
from tests.fixtures import asv_e2e

pytestmark = [rao_chan_nang.NANG, rao_chan_nang.CHI_KHI_BAT]

CAU = ("The quick brown fox jumps over the lazy dog, and then the dog "
       "runs back home before the rain starts.")


@pytest.fixture(scope="module")
def tep(tmp_path_factory):
    from apps.asv_gpu.do_luong import venv
    if not venv.san_sang() or not asv_e2e.co_sapi():
        pytest.skip("can qc-venv + SAPI")
    from platform_core import media
    d = tmp_path_factory.mktemp("do")
    goc = asv_e2e.noi(CAU, d / "goc.wav")
    ra = {}
    for ten, loc in (("dung", []), ("cat_nua", ["-t", f"{asv_e2e.giay_wav(goc) / 2:.2f}"]),
                     ("nhieu", None)):
        p = d / f"{ten}.wav"
        if loc is None:
            cmd = [media.ffmpeg_bin(), "-y", "-loglevel", "error", "-i", str(goc),
                   "-f", "lavfi", "-i", "anoisesrc=c=white:r=16000:a=0.2",
                   "-filter_complex", "amix=inputs=2:duration=first:normalize=0"]
        else:
            cmd = [media.ffmpeg_bin(), "-y", "-loglevel", "error", "-i", str(goc), *loc]
        subprocess.run([*cmd, "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(p)],
                       check=True)
        ra[ten] = str(p)
    return ra


def test_giong_va_squim_that(tep):
    from apps.asv_gpu.do_luong import bo_do
    dv = bo_do.DauVao(doan_tieng=[{"ma": k, "tep": v, "chu": CAU} for k, v in tep.items()],
                      ngon_ngu_dich="en")
    kq = bo_do.chay_tat_ca(dv)
    g, s = kq["giong"], kq["chat_luong_tieng"]
    assert g["trang_thai"] == s["trang_thai"] == bo_do.XONG, kq
    w = {k: r["wer"] for k, r in g["ket_qua"].items()}
    assert w["dung"] <= 0.1, g["ket_qua"]["dung"]
    assert w["cat_nua"] >= 0.3, g["ket_qua"]["cat_nua"]
    assert s["ket_qua"]["dung"]["si_sdr"] > s["ket_qua"]["nhieu"]["si_sdr"] + 5
    # Tai nguyen tu bao: tien trinh con da thoat (VRAM tra lai) — co so do.
    assert g["tai_nguyen"]["giay_tuong"] > 0 and s["tai_nguyen"]["ram_dinh_mb"] > 0
