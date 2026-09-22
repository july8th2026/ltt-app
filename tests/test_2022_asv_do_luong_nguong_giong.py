"""ASV final — chinh sach DOC SAI tu WER/CER (`sua_chua.NGUONG_DOC_SAI`).

Con so nguong duoc hieu chinh tu tieng that (L_GIONG.md); bai nay chot HINH
DANG chinh sach, doc con so tu bang chu khong chep lai no.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import sua_chua as sc


def _kq(nn, **chi_so):
    return {"ma": "s1", "ngon_ngu": nn, "doc_ra": "x", **chi_so}


@pytest.mark.parametrize("nn", sorted(sc.NGUONG_DOC_SAI))
def test_VUOT_moi_nguong_thi_DOC_SAI_sua_o_voice(nn):
    ng = sc.NGUONG_DOC_SAI[nn]
    tren = {k: v + 0.01 for k, v in ng.items()}
    kk = sc.tu_qc_giong([_kq(nn, **tren)])
    assert [k.loai for k in kk] == [sc.DOC_SAI]
    assert kk[0].giai_doan == "voice_synthesis" and kk[0].do_tin == 1.0
    assert sc.giong_khong_dat([_kq(nn, **tren)])[0]["nguong"] == ng


@pytest.mark.parametrize("nn", sorted(sc.NGUONG_DOC_SAI))
def test_BANG_nguong_hoac_duoi_mot_chi_so_thi_DAT(nn):
    ng = sc.NGUONG_DOC_SAI[nn]
    for k in ng:
        vao = {kk: vv + 0.01 for kk, vv in ng.items()}
        vao[k] = ng[k]          # dung bang nguong o MOT chi so
        assert sc.tu_qc_giong([_kq(nn, **vao)]) == []


def test_ngon_ngu_CHUA_hieu_chinh_thi_KHONG_sinh_viec_sua():
    assert "xx" not in sc.NGUONG_DOC_SAI
    assert sc.tu_qc_giong([_kq("xx", wer=1.0, cer=1.0)]) == []
    assert sc.giong_khong_dat([_kq("xx", wer=1.0, cer=1.0)]) == []


def test_thieu_chi_so_thi_KHONG_suy_ra_loi():
    """Doan `bo_qua` (tham chieu rong) khong co `wer` — khong phai doc sai."""
    for nn in sc.NGUONG_DOC_SAI:
        assert sc.tu_qc_giong([{"ma": "s1", "ngon_ngu": nn, "bo_qua": "rong"}]) == []


def test_bang_nguong_co_tieng_Viet_va_chi_dung_chi_so_da_do():
    assert "vi" in sc.NGUONG_DOC_SAI, "nguong vi phai duoc hieu chinh (L_GIONG.md)"
    for nn, ng in sc.NGUONG_DOC_SAI.items():
        assert set(ng) <= {"wer", "cer"} and "wer" in ng, (nn, ng)
        assert all(0 < v < 1 for v in ng.values()), (nn, ng)
