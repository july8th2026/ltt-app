"""ASV final — hai bo cham MOS cua bang xep hang giong `en` (phep kiem NANG).

    Distill-MOS (MIT)  +  DNSMOS P.835 (CC BY 4.0)

Chot ba thu:

  ① ca hai CHAY duoc trong `qc-venv` va tra so trong thang da cong bo;
  ② weights di kem goi `distillmos` dung la ban da khai trong
     `docs/auto_scan_video_final/THIRD_PARTY_METRICS.md` (sha256);
  ③ chung xep TIENG SACH tren TIENG DA TRON NHIEU — mot phep do khong phan
     biet duoc hai thu do thi khong xep hang duoc giong nao.

Chay:  set LTT_TEST_NANG=1
"""
from __future__ import annotations

import pathlib
import subprocess

import pytest

from tests import rao_chan_nang
from tests.fixtures import asv_e2e

pytestmark = [rao_chan_nang.NANG, rao_chan_nang.CHI_KHI_BAT]

RUNNER = pathlib.Path(__file__).resolve().parents[1] / "tools" / "do_gioi_giong_mos.py"

CAU = ("A quiet harbour town wakes up slowly, and the first sound of the "
       "morning is almost always the same one: a rope knocking against a mast.")

#: sha256 cua `distillmos/weights/distill_mos_v7.pt` trong goi `distillmos`
#: 0.9.1 — doc tu ban CAI THAT trong qc-venv ngay 23/09/2026.
SHA_DISTILL = "b18b3ac60227267cfb91e5d00ce22cc7b73716fd92f269484da1446e27031a40"


@pytest.fixture(scope="module")
def ket_qua(tmp_path_factory):
    from apps.asv_gpu.do_luong import venv

    if not venv.san_sang() or not asv_e2e.co_sapi():
        pytest.skip("can qc-venv + SAPI")
    from platform_core import media

    d = tmp_path_factory.mktemp("mos")
    sach = asv_e2e.noi(CAU, d / "sach.wav")
    ban = d / "ban.wav"
    subprocess.run([media.ffmpeg_bin(), "-y", "-loglevel", "error", "-i", str(sach),
                    "-f", "lavfi", "-i", "anoisesrc=c=white:r=16000:a=0.25",
                    "-filter_complex", "amix=inputs=2:duration=first:normalize=0",
                    "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(ban)],
                   check=True)
    return venv.chay(RUNNER, {"doan": [{"ma": "sach", "tep": str(sach)},
                                       {"ma": "ban", "tep": str(ban)}]},
                     timeout_s=600)


def test_ca_hai_bo_cham_tra_so_trong_thang(ket_qua):
    for ma in ("sach", "ban"):
        r = ket_qua["ket_qua"][ma]
        assert 1.0 <= r["distill_mos"] <= 5.0, (ma, r)
        # DNSMOS co the vang neu may khong co tep .onnx — do la mot cau tra loi
        # hop le, nhung no phai NOI RA thay vi tra mot so bia.
        if "dnsmos_ovrl" in r:
            for k in ("dnsmos_sig", "dnsmos_bak", "dnsmos_ovrl"):
                assert 1.0 <= r[k] <= 5.0, (ma, k, r)
        else:
            assert r.get("dnsmos") == "khong_kha_dung", r


def test_xep_tieng_sach_tren_tieng_tron_nhieu(ket_qua):
    sach = ket_qua["ket_qua"]["sach"]
    ban = ket_qua["ket_qua"]["ban"]
    assert sach["distill_mos"] > ban["distill_mos"], (sach, ban)
    if "dnsmos_ovrl" in sach and "dnsmos_ovrl" in ban:
        assert sach["dnsmos_ovrl"] > ban["dnsmos_ovrl"], (sach, ban)


def test_weights_distill_mos_dung_ban_da_khai():
    """Giay phep MIT gan vao DUNG tep weights nay, khong phai 'mot ban nao do'."""
    import hashlib

    from apps.asv_gpu.do_luong import venv

    if not venv.san_sang():
        pytest.skip("chua co qc-venv")
    p = subprocess.run(
        [str(venv.python_qc()), "-c",
         "import distillmos,pathlib;"
         "print(pathlib.Path(distillmos.__file__).parent/'weights'/'distill_mos_v7.pt')"],
        capture_output=True, text=True)
    if p.returncode != 0:
        pytest.skip("qc-venv chua cai distillmos")
    tep = pathlib.Path(p.stdout.strip())
    assert tep.is_file(), tep
    assert hashlib.sha256(tep.read_bytes()).hexdigest() == SHA_DISTILL
