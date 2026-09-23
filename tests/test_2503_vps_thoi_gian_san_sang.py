"""Trang tao may phai NOI TRUOC bao lau may san sang — va noi bang so DO DUOC.

Chu du an chot 23/09/2026: giu cach mua IP OVH theo yeu cau, nhung phai noi
that voi khach rang ho se cho. Hien trang khong noi gi: khach bam "Tao may" roi
nhin mot dong trang thai, trong khi phia sau he thong dang dat mua mot dia chi
IP o OVH voi `order_delivery_timeout_seconds = 3600`.

⭐ So phai DO, khong duoc viet cung. Mot con so viet cung la mot loi hua khong
   ai kiem lai: ha tang cham di thi trang van noi "3 phut" mai mai. Nguon do la
   chinh cac may da tao xong — `tao_moi` -> `tao_xong` trong `vps_event`.

   Do that tren production 16/09: may `d96b66f3` mat 3 phut 24 giay.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from apps.vps.services import provisioning
from platform_core.db import Base


@pytest.fixture()
def db():
    import platform_core.models as _models  # noqa: F401
    from apps.vps import tables as _tables  # noqa: F401
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


GOC = datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc)


def _lan_tao(db, instance_id: str, giay: int, *, xong: bool = True, thu_tu=0):
    from apps.vps.tables import VpsEvent
    bat_dau = GOC + timedelta(hours=thu_tu)
    db.add(VpsEvent(instance_id=instance_id, loai="tao_moi", boi="u",
                    chi_tiet={}, created_at=bat_dau))
    if xong:
        db.add(VpsEvent(instance_id=instance_id, loai="tao_xong", boi="he_thong",
                        chi_tiet={}, created_at=bat_dau + timedelta(seconds=giay)))
    db.flush()


def test_chua_co_may_nao_tao_xong_thi_khong_hua_gi(db):
    """Khong co mau = khong biet. Khong biet thi im, dung doan mot con so."""
    assert provisioning.thoi_gian_san_sang(db) is None


def test_mot_mau_van_chua_du_de_hua(db):
    """Mot lan do khong phai mot phan bo. Hua tu no la hua tu may rui."""
    _lan_tao(db, "i-1", 204)
    assert provisioning.thoi_gian_san_sang(db) is None


def test_du_mau_thi_tra_p50_va_p90_tinh_bang_giay(db):
    for i, giay in enumerate([100, 200, 300, 400, 500]):
        _lan_tao(db, f"i-{i}", giay, thu_tu=i)
    kq = provisioning.thoi_gian_san_sang(db)
    assert kq is not None
    assert kq.so_mau == 5
    assert kq.p50_giay == 300
    assert kq.p90_giay == 500


def test_may_tao_KHONG_xong_khong_lam_lech_con_so(db):
    """May hong khong co `tao_xong`, nen no khong co thoi gian de dem.

    Dem no bang 'bay gio tru luc bat dau' la bien moi may hong thanh mot con so
    khong lo, va loi hua cho khach se troi ra vo tan.
    """
    for i, giay in enumerate([100, 200, 300]):
        _lan_tao(db, f"i-{i}", giay, thu_tu=i)
    _lan_tao(db, "i-hong", 0, xong=False, thu_tu=9)
    kq = provisioning.thoi_gian_san_sang(db)
    assert kq.so_mau == 3


def test_chi_lay_cac_lan_tao_GAN_DAY(db):
    """Ha tang doi thi so cu khong con noi ve ha tang hien tai."""
    for i in range(30):
        _lan_tao(db, f"i-{i}", 100 + i, thu_tu=i)
    kq = provisioning.thoi_gian_san_sang(db, toi_da_mau=10)
    assert kq.so_mau == 10
    # 10 lan gan nhat la 120..129 giay, khong phai 100..129
    assert kq.p50_giay >= 120


def test_thu_tu_su_kien_lon_xon_khong_lam_am_thoi_gian(db):
    """`tao_xong` truoc `tao_moi` (lech dong ho, ghi lai) khong duoc thanh so am."""
    from apps.vps.tables import VpsEvent
    db.add(VpsEvent(instance_id="i-lech", loai="tao_moi", boi="u", chi_tiet={},
                    created_at=GOC + timedelta(seconds=500)))
    db.add(VpsEvent(instance_id="i-lech", loai="tao_xong", boi="he_thong",
                    chi_tiet={}, created_at=GOC))
    for i, giay in enumerate([100, 200]):
        _lan_tao(db, f"i-{i}", giay, thu_tu=i + 1)
    db.flush()
    kq = provisioning.thoi_gian_san_sang(db)
    assert kq is None or kq.p50_giay >= 0
