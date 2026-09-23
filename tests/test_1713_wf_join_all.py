"""JOIN ALL 3 nhánh KHÔNG được mở sau tín hiệu đầu (audit 22/09, spec §5.7)."""
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.
from __future__ import annotations

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401


def _join(db, che_do="ALL", n=3, can=0):
    from platform_core.workflow import join
    return join.tao(db, run_id="r1", owner_id="u1", che_do=che_do,
                    so_nhanh=n, can=can)


def test_all_mot_tin_hieu_chua_mo(db):
    from platform_core.workflow import cho_doi
    wp = _join(db)
    cho_doi.ghi_tin_hieu(db, wp.id, seq=1, status="SUCCEEDED")
    assert cho_doi.da_mo(db, wp.id) is False


def test_all_du_ba_tin_hieu_thi_mo_ke_ca_co_nhanh_hong(db):
    from platform_core.workflow import cho_doi
    wp = _join(db)
    for i, st in enumerate(("SUCCEEDED", "FAILED", "SUCCEEDED"), start=1):
        cho_doi.ghi_tin_hieu(db, wp.id, seq=i, status=st)
    assert cho_doi.da_mo(db, wp.id) is True


def test_any_van_mo_sau_mot(db):
    from platform_core.workflow import cho_doi
    wp = _join(db, che_do="ANY")
    cho_doi.ghi_tin_hieu(db, wp.id, seq=1, status="SUCCEEDED")
    assert cho_doi.da_mo(db, wp.id) is True


def test_join_ghi_so_nguon_va_khong_niem_phong_ALL(db):
    wp = _join(db)
    assert wp.so_nguon == 3 and wp.sealed is False
