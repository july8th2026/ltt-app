"""Cong noi bo va route HTML: CUNG dau vao -> CUNG ho so lan chay.

🔑 Day la bang chung cho "mot duong, khong phai hai". Route nhan chuoi form
   (JSON), cong nhan gia tri da giai; ca hai di qua `dich_vu_tao.dung_cai_dat`.
   Neu mot ngay ai do them mot phep duyet vao route ma quen cong (hay nguoc
   lai), tep nay do.

Route that qua HTTP that (`test_423.moi_truong`: dang nhap, CSRF, multipart).
"""
from __future__ import annotations

import json

from tests import test_423_asv_giao_dien as _mt

moi_truong = _mt.moi_truong

_VUNG = [{"loai": "lam_mo", "y0": 0.80, "y1": 0.95, "x0": 0.1, "x1": 0.9}]
_LOP = [{"chu": "Dang ky kenh", "x": 0.1, "y": 0.8, "co_chu": 0.06,
         "mau": "trang", "vien": True}]
_PHU_DE = {"xuat_srt": True}
_AM = {"nen_db": -12.0}


def _id_cua(email: str) -> str:
    import platform_core.db as dbmod
    from platform_core.models import User

    db = next(dbmod.get_session())
    try:
        return db.query(User).filter(User.email == email).one().id
    finally:
        db.close()


def _run_moi_nhat(owner: str):
    import platform_core.db as dbmod
    from apps.auto_scan_video import tables as T

    db = next(dbmod.get_session())
    try:
        return (db.query(T.AsvRun).filter(T.AsvRun.owner_id == owner)
                .order_by(T.AsvRun.created_at.desc()).first())
    finally:
        db.close()


def _nop_qua_cong(owner: str, tmp_path, cai_dat: dict):
    import platform_core.db as dbmod
    from tests.test_2085_asv_cong_noi_bo_vong_doi import ve_tai_len
    from apps.auto_scan_video import cong_noi_bo as cong

    db = next(dbmod.get_session())
    try:
        (tmp_path / "cong").mkdir(exist_ok=True)
        uid = ve_tai_len(db, tmp_path / "cong", owner=owner)
        return cong.submit_run(db, owner, cong.YeuCauChay(cai_dat=cai_dat,
                                                          upload_id=uid))
    finally:
        db.close()


def test_route_va_cong_cho_CUNG_ho_so(moi_truong, tmp_path):
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    chu = _id_cua("asv-a@example.com")

    r = _mt._tao_run_cho(
        a, csrf, tmp_path, preset="smart_localize",
        ngon_ngu_nguon="en", ngon_ngu_dich="vi", tu_dien="Huệ = Huê",
        cat=json.dumps([0.1, 0.9]), vung=json.dumps(_VUNG),
        lop_phu=json.dumps(_LOP), phu_de=json.dumps(_PHU_DE),
        am_thanh=json.dumps(_AM))
    assert r.status_code == 200, r.text[:400]
    tu_route = _run_moi_nhat(chu)

    phieu = _nop_qua_cong(chu, tmp_path, {
        "timing_mode": "fit_original", "preset": "smart_localize",
        "giong_id": "Minh Đức", "ngon_ngu_nguon": "en", "ngon_ngu_dich": "vi",
        "tu_dien": {"Huệ": "Huê"}, "cat": [0.1, 0.9], "vung": _VUNG,
        "lop_phu": _LOP, "phu_de": _PHU_DE, "am_thanh": _AM})

    assert phieu.run_id != tu_route.id
    assert dict(phieu.cai_dat) == dict(tu_route.settings)
    # Va ho so do khong rong: moi tinh nang da thuc su vao.
    for k in ("cat", "vung", "lop_phu", "phu_de", "am_thanh"):
        assert k in tu_route.settings, k
    assert tu_route.settings["tu_dien"] == {"Huệ": "Huê"}


def test_route_va_cong_cho_CUNG_ho_so_toi_thieu(moi_truong, tmp_path):
    """Truong hop binh thuong: khong tinh nang nao -> khong khoa thua nao."""
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    chu = _id_cua("asv-a@example.com")

    assert _mt._tao_run_cho(a, csrf, tmp_path).status_code == 200
    tu_route = _run_moi_nhat(chu)
    phieu = _nop_qua_cong(chu, tmp_path, {"timing_mode": "fit_original",
                                          "giong_id": "Minh Đức"})
    assert dict(phieu.cai_dat) == dict(tu_route.settings)


def test_cap_ngon_ngu_sai_CUNG_cau_loi_o_hai_cua(moi_truong, tmp_path):
    import pytest

    from apps.auto_scan_video import cong_noi_bo as cong
    from tests.fixtures import asv_media as fx

    fx.require_ffmpeg()
    _app, a, csrf, _b, _cb = moi_truong
    chu = _id_cua("asv-a@example.com")

    r = _mt._tao_run_cho(a, csrf, tmp_path, ngon_ngu_nguon="vi",
                         ngon_ngu_dich="vi")
    assert r.status_code == 400
    with pytest.raises(cong.LoiDauVao) as e:
        _nop_qua_cong(chu, tmp_path, {"timing_mode": "fit_original",
                                      "giong_id": "Minh Đức",
                                      "ngon_ngu_nguon": "vi", "ngon_ngu_dich": "vi"})
    assert str(e.value) in r.text
    assert _run_moi_nhat(chu) is None
