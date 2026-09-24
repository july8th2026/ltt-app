"""ASV final — bo do `gioi` chay THAT trong qc-venv (phep kiem NANG).

Tieng that: SAPI (Windows) — hai giong co nhan khong ai cai duoc, ngay trong
he dieu hanh, khong mang, khong ban quyen:

    David  -> nam        Zira -> nu

⛔ Hai diem khong phai mot ban hieu chinh — ban hieu chinh that la 20 preset
   engine (`docs/auto_scan_video_final/L_DO_GIONG.md` muc A, chay bang
   `tools/do_gioi_giong.py`). Phep kiem nay chot MOT thu khac han: rang duong
   ong con NOI, con tai duoc weights ghim, va con tra dung CHIEU.

Chay:  set LTT_TEST_NANG=1
"""
from __future__ import annotations

import pytest

from tests import rao_chan_nang
from tests.fixtures import asv_e2e

pytestmark = [rao_chan_nang.NANG, rao_chan_nang.CHI_KHI_BAT]

CAU = ("The lighthouse keeper climbed the stairs every evening and wrote one "
       "line in the logbook before going back down to the harbour road, "
       "where the wind was always waiting for him.")


@pytest.fixture(scope="module")
def ket_qua(tmp_path_factory):
    from apps.asv_gpu.do_luong import gioi, venv

    if not venv.san_sang() or not asv_e2e.co_sapi():
        pytest.skip("can qc-venv + SAPI")
    d = tmp_path_factory.mktemp("gioi")
    clip = []
    for ma, giong in (("nam", asv_e2e.GIONG_NAM), ("nu", asv_e2e.GIONG_NU)):
        p = asv_e2e.noi(CAU, d / f"{ma}.wav", giong=giong)
        clip.append({"ma": ma, "tep": str(p)})
    return gioi.do_gioi(clip)["ket_qua"]


def test_doc_dung_chieu(ket_qua):
    assert ket_qua["nam"]["nhan"] == "nam"
    assert ket_qua["nu"]["nhan"] == "nu"


def test_hai_giong_ro_thi_do_tin_cao(ket_qua):
    """Hai giong TTS he dieu hanh khong he mo ho; `do_tin` phai noi ra dieu do.

    Neu nguong nay do, thu dang hong la `do_tin` (hoac weights), khong phai hai
    giong SAPI — chung khong doi.
    """
    for ma in ("nam", "nu"):
        assert ket_qua[ma]["do_tin"] > 0.90, (ma, ket_qua[ma])
        assert ket_qua[ma]["ti_le_cua_so_nam"] in (0.0, 1.0), (ma, ket_qua[ma])


def test_co_cot_doi_chieu_va_khong_bia_khi_thieu(ket_qua):
    """`f0_trung_vi` di kem de doi chieu, va no phai LA MOT SO hoac `None`."""
    for ma in ("nam", "nu"):
        f0 = ket_qua[ma]["f0_trung_vi"]
        assert f0 is None or 70.0 <= f0 <= 400.0, (ma, f0)
        assert ket_qua[ma]["so_cua_so"] >= 1
    # Chieu vat ly: giong nam SAPI tram hon giong nu SAPI. Neu ca hai deu do
    # duoc ma thu tu nguoc, bo do F0 dang nhay quang tam — bay da ghi o
    # `apps/ltt_voice/toc_do.py`.
    a, b = ket_qua["nam"]["f0_trung_vi"], ket_qua["nu"]["f0_trung_vi"]
    if a is not None and b is not None:
        assert a < b, (a, b)
