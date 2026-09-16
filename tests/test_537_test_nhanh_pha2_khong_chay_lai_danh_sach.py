"""test_537 — `test_nhanh.py` pha 2 KHÔNG chạy lại cả danh sách tệp (17/09/2026).

🔴 `gate.py --pham-vi server:web` truyền 467 tệp. `chung` mang cả danh sách ấy, nên
pha 2 `chung + co` chạy LẠI toàn bộ 467 tệp trên MỘT tiến trình sau khi pha 1 đã
chạy song song xong — một lượt L2 kéo dài hơn cả L3.
"""
from __future__ import annotations

import argparse
import importlib.util
import pathlib

GOC = pathlib.Path(__file__).resolve().parents[1]


def _nap():
    spec = importlib.util.spec_from_file_location("test_nhanh_537", GOC / "tools" / "test_nhanh.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _chay_gia(m, monkeypatch, con_lai):
    goi = []
    monkeypatch.setattr(m, "_chay", lambda argv, nhan: (goi.append((nhan, list(argv))) or (0, 0.0)))
    ns = argparse.Namespace(lf=False, lf_rong_thi_khong_chay=False, noi_tiep=False, n="2",
                            k="", cho=15.0, khong_khoa=True)
    assert m._than(ns, con_lai) == 0
    return goi


def test_co_danh_sach_pha2_chi_chay_tep_noi_tiep_nam_trong_danh_sach(monkeypatch):
    m = _nap()
    thuong = "tests/test_532_voice_phan_loai_catalog.py"
    noi_tiep = m.TEP_NOI_TIEP[0]
    goi = _chay_gia(m, monkeypatch, [thuong, noi_tiep])
    assert len(goi) == 2
    pha1, pha2 = goi[0][1], goi[1][1]
    assert thuong in pha1 and "-n" in pha1
    assert noi_tiep in pha2
    assert thuong not in pha2, "pha 2 chay lai tep khong phai noi tiep"
    for khac in m.TEP_NOI_TIEP[1:]:
        assert khac not in pha2, "pha 2 chay tep noi tiep KHONG duoc yeu cau"


def test_danh_sach_khong_co_tep_noi_tiep_thi_khong_co_pha2(monkeypatch):
    m = _nap()
    goi = _chay_gia(m, monkeypatch, ["tests/test_532_voice_phan_loai_catalog.py"])
    assert len(goi) == 1 and goi[0][0].startswith("PHA 1")


def test_khong_danh_sach_giu_hanh_vi_day_du(monkeypatch):
    m = _nap()
    goi = _chay_gia(m, monkeypatch, [])
    assert len(goi) == 2
    pha2 = goi[1][1]
    assert all(t in pha2 for t in m.TEP_NOI_TIEP if (GOC / t).is_file())
