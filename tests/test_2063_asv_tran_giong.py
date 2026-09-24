"""test_2063 — bộ đọc đường cong tốc độ giọng (D5/B).

⭐ Chốt CÁCH ĐỌC trước khi có âm thanh: phép kiểm này chạy ⛔ không cần TTS.
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

_P = (pathlib.Path(__file__).resolve().parents[1] / "docs" / "auto_scan_video_final"
      / "bang_chung" / "d5_tran_giong" / "doc_duong_cong.py")
_spec = importlib.util.spec_from_file_location("doc_duong_cong", _P)
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)


def _bo(cer_theo_toc, mos_theo_toc, n=12):
    return {"theo_toc_do": {
        str(t): {f"c{i}": {"cer": cer_theo_toc[t] + i * 0.001,
                           "dnsmos": mos_theo_toc[t] - i * 0.001}
                 for i in range(n)}
        for t in cer_theo_toc}}


def test_2063_KHONG_co_doi_chung_thi_TU_CHOI_doc():
    """⛔ Không có mức 1,00 thì ⛔ không có gì để gọi là 'gãy'."""
    with pytest.raises(KeyError, match="DOI CHUNG"):
        dc.doc(_bo({1.15: 0.10}, {1.15: 3.5}))


def test_2063_toc_do_KHONG_lam_xau_thi_KHONG_bao_gay():
    """Đối chứng dương: mọi mức y hệt đối chứng ⇒ ⛔ không mức nào gãy."""
    r = dc.doc(_bo({1.00: 0.10, 1.15: 0.10, 1.45: 0.10},
                   {1.00: 3.5, 1.15: 3.5, 1.45: 3.5}))
    assert r["gay_tai"] is None
    assert all(not m["GAY"] for m in r["muc"].values())
    assert "CHAT VO CO" in r["ket_luan_ve_tran_hien_tai"]


def test_2063_TIEM_mot_buoc_nhay_that_thi_PHAI_bao_gay():
    """Bánh cóc có răng: CER nhảy hẳn ở 1,35 ⇒ phải bắt được, và bắt ĐÚNG mức."""
    r = dc.doc(_bo({1.00: 0.10, 1.15: 0.101, 1.35: 0.30, 1.45: 0.40},
                   {1.00: 3.5, 1.15: 3.5, 1.35: 3.5, 1.45: 3.5}))
    assert r["gay_tai"] == 1.35
    assert r["muc"][1.35]["GAY_theo_cer"] is True
    assert r["muc"][1.15]["GAY"] is False


def test_2063_DNSMOS_tut_cung_la_GAY_du_CER_yen():
    """⭐ Hai thước cạnh nhau: dễ nghe hiểu YÊN mà chất lượng TỤT vẫn là gãy."""
    r = dc.doc(_bo({1.00: 0.10, 1.25: 0.10}, {1.00: 3.5, 1.25: 2.0}))
    assert r["muc"][1.25]["GAY_theo_dnsmos"] is True
    assert r["muc"][1.25]["GAY_theo_cer"] is False


def test_2063_MOT_cau_ngoai_le_KHONG_du_de_goi_la_gay():
    """🔴 Điều kiện (2) — phép dấu — chặn đúng ca này.

    Một câu hỏng nặng kéo trung vị thì vẫn ⛔ chưa phải gãy: ⛔ đa số câu phải
    cùng xấu đi. ⛔ Thiếu vế này là để một ngoại lệ đóng cả một trần.
    """
    bo = _bo({1.00: 0.10, 1.25: 0.10}, {1.00: 3.5, 1.25: 3.5})
    bo["theo_toc_do"]["1.25"]["c0"]["cer"] = 0.95      # một câu hỏng nặng
    r = dc.doc(bo)
    assert r["muc"][1.25]["GAY"] is False
    assert r["muc"][1.25]["cer_so_cau_xau_di"].startswith("1/")


def test_2063_so_sanh_THEO_CAP_chu_khong_so_hai_dam_may():
    """Ghép cặp theo câu: dời đều mọi câu ⛔ không được làm đổi kết luận."""
    a = dc.doc(_bo({1.00: 0.10, 1.25: 0.10}, {1.00: 3.5, 1.25: 3.5}))
    b = dc.doc(_bo({1.00: 0.30, 1.25: 0.30}, {1.00: 4.5, 1.25: 4.5}))
    assert a["gay_tai"] == b["gay_tai"] is None
