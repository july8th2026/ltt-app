"""Cong noi bo: loi co kieu, pham vi chu so huu, va "duyet TRUOC khi giu credit"."""
from __future__ import annotations

import pytest

from tests import test_2085_asv_cong_noi_bo_vong_doi as _vd
from tests.test_2085_asv_cong_noi_bo_vong_doi import CAI_DAT, CHU, KHAC, ve_tai_len

db = _vd.db
giai_doan_gia = _vd.giai_doan_gia


def _dem(db):
    from platform_core.models import CreditEntry
    from apps.auto_scan_video.tables import AsvRun
    return db.query(AsvRun).count(), db.query(CreditEntry).count()


@pytest.mark.parametrize("nguon,dich", [("vi", "vi"), ("en", "zh"), ("ja", "vi"),
                                        ("zh", "fr")])
def test_cap_ngon_ngu_sai_bi_tu_choi_TRUOC_khi_giu_credit(db, tmp_path, nguon, dich):
    from apps.auto_scan_video import cong_noi_bo as cong

    uid = ve_tai_len(db, tmp_path)
    truoc = _dem(db)
    with pytest.raises(cong.LoiDauVao) as e:
        cong.submit_run(db, CHU, cong.YeuCauChay(
            cai_dat={**CAI_DAT, "ngon_ngu_nguon": nguon, "ngon_ngu_dich": dich},
            upload_id=uid))
    assert e.value.ma == "dau_vao_sai"
    assert _dem(db) == truoc, "tu choi cap ngon ngu ma van tao run / dong credit"


def test_nguoi_khac_KHONG_cham_duoc_run(db, tmp_path, giai_doan_gia):
    from apps.auto_scan_video import cong_noi_bo as cong

    p = cong.submit_run(db, CHU, cong.YeuCauChay(cai_dat=CAI_DAT,
                                                 upload_id=ve_tai_len(db, tmp_path)))
    for goi in (lambda: cong.get_status(db, KHAC, p.run_id),
                lambda: cong.cancel_run(db, KHAC, p.run_id),
                lambda: cong.retry_run(db, KHAC, p.run_id, "render"),
                lambda: cong.get_result(db, KHAC, p.run_id)):
        with pytest.raises(cong.LoiKhongTimThay) as e:
            goi()
        assert e.value.ma == "khong_tim_thay"
    # "Khong co" va "khong phai cua ban" la MOT cau (I6).
    with pytest.raises(cong.LoiKhongTimThay) as e2:
        cong.get_status(db, KHAC, "khong-ton-tai")
    with pytest.raises(cong.LoiKhongTimThay) as e1:
        cong.get_status(db, KHAC, p.run_id)
    assert str(e1.value) == str(e2.value)
    # Run cua CHU van nguyen.
    assert cong.get_status(db, CHU, p.run_id).trang_thai == "queued"


def test_ve_tai_len_cua_nguoi_khac_bi_tu_choi(db, tmp_path):
    from apps.auto_scan_video import cong_noi_bo as cong

    uid_cua_chu = ve_tai_len(db, tmp_path)
    with pytest.raises(cong.LoiKhongTimThay):
        cong.submit_run(db, KHAC, cong.YeuCauChay(cai_dat=CAI_DAT,
                                                  upload_id=uid_cua_chu))


def test_thieu_credit_la_loi_co_kieu_va_khong_de_lai_gi(db, tmp_path):
    from apps.auto_scan_video import cong_noi_bo as cong

    ngheo = "u-cong-ngheo"
    from tests.conftest import bao_dam_user
    bao_dam_user(db, ngheo)
    db.commit()
    uid = ve_tai_len(db, tmp_path, owner=ngheo)
    truoc = _dem(db)
    with pytest.raises(cong.LoiThieuCredit) as e:
        cong.submit_run(db, ngheo, cong.YeuCauChay(cai_dat=CAI_DAT, upload_id=uid))
    assert e.value.ma == "thieu_credit"
    assert _dem(db) == truoc


@pytest.mark.parametrize("cai_dat,uid,run_id", [
    ({**CAI_DAT, "khoa_la": 1}, True, ""),              # truong la
    ({**CAI_DAT, "logo": [{"x": 0.1}]}, True, ""),       # logo can anh -> chi route
    ({**CAI_DAT, "timing_mode": "bay"}, True, ""),
    ({**CAI_DAT, "preset": "bay"}, True, ""),
    ({**CAI_DAT, "cat": [0.1, 0.9]}, True, ""),          # cat o preset giu hinh
    ({**CAI_DAT, "tu_dien": {"A=B": "c"}}, True, ""),
    ({**CAI_DAT, "giong_id": "a", "voice_id": "b"}, True, ""),
    (CAI_DAT, False, ""),                                # khong nguon
    (CAI_DAT, True, "x"),                                # hai nguon
])
def test_dau_vao_sai(db, tmp_path, cai_dat, uid, run_id):
    from apps.auto_scan_video import cong_noi_bo as cong

    truoc = _dem(db)
    with pytest.raises(cong.LoiDauVao):
        cong.submit_run(db, CHU, cong.YeuCauChay(
            cai_dat=cai_dat, upload_id=ve_tai_len(db, tmp_path) if uid else "",
            nguon_run_id=run_id))
    assert _dem(db) == truoc


def test_giai_doan_khong_ton_tai_la_dau_vao_sai(db, tmp_path, giai_doan_gia):
    from apps.auto_scan_video import cong_noi_bo as cong

    p = cong.submit_run(db, CHU, cong.YeuCauChay(cai_dat=CAI_DAT,
                                                 upload_id=ve_tai_len(db, tmp_path)))
    with pytest.raises(cong.LoiDauVao):
        cong.retry_run(db, CHU, p.run_id, "khong_co")


def test_co_tat_thi_cong_dong(db, tmp_path, monkeypatch):
    from apps.auto_scan_video import cong_noi_bo as cong

    uid = ve_tai_len(db, tmp_path)
    monkeypatch.delenv("LTT_AUTO_SCAN_VIDEO", raising=False)
    with pytest.raises(cong.LoiChuaMo) as e:
        cong.submit_run(db, CHU, cong.YeuCauChay(cai_dat=CAI_DAT, upload_id=uid))
    assert e.value.ma == "chua_mo"


def test_thieu_nguoi_dung(db):
    from apps.auto_scan_video import cong_noi_bo as cong

    for goi in (lambda: cong.get_status(db, "", "x"),
                lambda: cong.submit_run(db, " ", cong.YeuCauChay(cai_dat=CAI_DAT,
                                                                 upload_id="x"))):
        with pytest.raises(cong.LoiDauVao):
            goi()


def test_moi_loi_deu_la_LoiCongNoiBo_va_ma_khong_trung():
    from apps.auto_scan_video import cong_noi_bo as cong

    lop = [cong.LoiDauVao, cong.LoiKhongTimThay, cong.LoiThieuCredit,
           cong.LoiXungDot, cong.LoiChuaMo]
    assert all(issubclass(k, cong.LoiCongNoiBo) for k in lop)
    assert len({k.ma for k in lop}) == len(lop)
