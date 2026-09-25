"""Vòng đời yêu cầu marketplace: yêu_cầu → duyệt/từ_chối/thu_hồi + nhật ký.

Không đụng mạng, không đụng AppContainer — thuần CSDL. Phép kiểm cài đặt thật
(qua vỏ) nằm ở `test_4234`/`test_4239`.
"""
from __future__ import annotations

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401


def _admin(id_="admin1"):
    from platform_core.models import User
    return User(id=id_, email=f"{id_}@x.test", role="admin",
               password_hash="x", display_name="Admin")


def _user(id_="u1"):
    from platform_core.models import User
    return User(id=id_, email=f"{id_}@x.test", role="user",
               password_hash="x", display_name="User")


def test_yeu_cau_tao_hang_cho_duyet_va_ghi_nhat_ky(db):  # noqa: F811
    from platform_core.models import (MARKETPLACE_CHO_DUYET,
                                      MarketplacePieceNhatKy)
    from platform_core.workflow import marketplace as mp
    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar",
                      phien_ban="1.2.3", mien=["bar.example.com"])
    assert hang.trang_thai == MARKETPLACE_CHO_DUYET
    assert hang.ten == "@foo/piece-bar"
    logs = db.query(MarketplacePieceNhatKy).filter_by(yeu_cau_id=hang.id).all()
    assert [l.hanh_dong for l in logs] == ["yeu_cau"]


def test_yeu_cau_chua_dang_nhap_bi_tu_choi(db):  # noqa: F811
    from platform_core.workflow import marketplace as mp
    with pytest.raises(mp.LoiKhongDuQuyen):
        mp.yeu_cau(db, nguoi=None, ten="@foo/piece-bar", phien_ban="1.2.3")


def test_duyet_admin_chuyen_trang_thai_va_ghi_nhat_ky(db):  # noqa: F811
    from platform_core.models import MARKETPLACE_DA_DUYET, MarketplacePieceNhatKy
    from platform_core.workflow import marketplace as mp
    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban="1.2.3")
    admin = _admin()
    ra = mp.duyet(db, yeu_cau_id=hang.id, nguoi=admin)
    assert ra.trang_thai == MARKETPLACE_DA_DUYET
    assert ra.nguoi_duyet_id == admin.id
    hanh_dong = [l.hanh_dong for l in
                db.query(MarketplacePieceNhatKy).filter_by(yeu_cau_id=hang.id)]
    assert hanh_dong == ["yeu_cau", "duyet"]


def test_tu_choi_ghi_ly_do(db):  # noqa: F811
    from platform_core.models import MARKETPLACE_TU_CHOI
    from platform_core.workflow import marketplace as mp
    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban="1.2.3")
    ra = mp.tu_choi(db, yeu_cau_id=hang.id, nguoi=_admin(), ly_do="khong ro nguon")
    assert ra.trang_thai == MARKETPLACE_TU_CHOI
    assert ra.ly_do_tu_choi == "khong ro nguon"


def test_khong_duyet_lai_hang_da_quyet_dinh(db):  # noqa: F811
    """Một hàng đã `da_duyet` thì không duyệt/từ chối được lần hai — ngăn một
    admin thứ hai vô tình ghi đè quyết định (và lịch sử `nhat_ky`) của lần
    trước."""
    from platform_core.workflow import marketplace as mp
    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban="1.2.3")
    mp.duyet(db, yeu_cau_id=hang.id, nguoi=_admin())
    with pytest.raises(mp.LoiMarketplace):
        mp.duyet(db, yeu_cau_id=hang.id, nguoi=_admin())
    with pytest.raises(mp.LoiMarketplace):
        mp.tu_choi(db, yeu_cau_id=hang.id, nguoi=_admin())


def test_thu_hoi_dua_ve_tu_choi_va_xoa_khoi_allowlist(db, tmp_path, monkeypatch):  # noqa: F811
    from platform_core.models import MARKETPLACE_TU_CHOI
    from platform_core.workflow import connector, marketplace as mp
    monkeypatch.setattr(connector, "THU_MUC_MARKETPLACE", tmp_path / "mkt")
    hang = mp.yeu_cau(db, nguoi=_user(), ten="@foo/piece-bar", phien_ban="1.2.3",
                      mien=["bar.example.com"])
    mp.duyet(db, yeu_cau_id=hang.id, nguoi=_admin())
    # Giả lập đã cài xong (không đi qua `cai_dat()` thật — test đó ở 4234/4239).
    al = mp.doc_allowlist_marketplace()
    al["pieces"][hang.ten] = hang.phien_ban
    al["mien"][hang.ten] = list(hang.mien)
    mp.ghi_allowlist_marketplace(al)
    assert "@foo/piece-bar" in mp.doc_allowlist_marketplace()["pieces"]

    ra = mp.thu_hoi(db, yeu_cau_id=hang.id, nguoi=_admin(), ly_do="phat hien loi")
    assert ra.trang_thai == MARKETPLACE_TU_CHOI
    assert "@foo/piece-bar" not in mp.doc_allowlist_marketplace()["pieces"]
