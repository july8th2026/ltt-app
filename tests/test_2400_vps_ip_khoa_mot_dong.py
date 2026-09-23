"""Bo cap IP OVH chi khoa MOT dong moi vong — khong gianh het IP cua luong khac.

🔴 Su co do 23/09/2026. R16 (`dc516d5c`) doi `LIMIT 1` thanh `LIMIT 20` de buoc qua
   dong da tat gia han. Tren PostgreSQL, `SELECT ... FOR UPDATE SKIP LOCKED LIMIT 20`
   khoa MOI dong FREE cua profile; luong xin IP thu hai bo qua het dong dang khoa va
   nem `CapacityExhausted` trong khi van con IP trong.

   Phep kiem that la `test_1010::test_real_postgres_two_ip_allocators_...` — nhung no
   chi chay khi `LTT_VPS_PG_TEST=1`, nen gate khong bao gio thay: do 0/3 khi chay ca
   module, va XANH khi chay rieng (ket noi moi so le hai luong — may man ve thoi diem).

⭐ Tep nay chay trong bo test thuong (SQLite): ghi lai MOI cau `FOR UPDATE` ma bo cap
   IP THAT SU gui di, dich sang PostgreSQL, va doi moi cau chi khoa mot dong.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from platform_core.db import Base


@pytest.fixture()
def db():
    import platform_core.models as _models  # noqa: F401
    from apps.vps import tables as _tables  # noqa: F401
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _profile(db):
    from apps.vps.tables import VpsInfrastructureProfile
    p = VpsInfrastructureProfile(
        id="p-ovh", slug="ovh", name="OVH", region="sgp", status="ACTIVE",
        compute_backend_type="proxmox", public_ip_backend_type="ovh_static_pool",
        gateway_backend_type="nft", credential_ref="LTT_OVH")
    db.add(p)
    db.commit()
    return p


def _ip(db, row_id, *, huy_gia_han=False):
    from apps.vps.tables import VpsIp
    meta = {"renewal_cancelled_at": "2026-09-30T00:00:00+00:00"} if huy_gia_han else {}
    db.add(VpsIp(id=row_id, infrastructure_profile_id="p-ovh", gateway_id="g-ovh",
                 dia_chi=f"192.0.2.{row_id[-1]}", state="FREE", provider_metadata=meta))
    db.commit()


def _cau_khoa(db, monkeypatch):
    """Moi cau SELECT ... FOR UPDATE ma bo cap IP gui qua `db.execute`, dang PostgreSQL."""
    ghi = []
    goc = db.execute

    def gian_diep(stmt, *a, **k):
        if getattr(stmt, "_for_update_arg", None) is not None:
            ghi.append(str(stmt.compile(dialect=postgresql.dialect(),
                                        compile_kwargs={"literal_binds": True})))
        return goc(stmt, *a, **k)

    monkeypatch.setattr(db, "execute", gian_diep)
    return ghi


def test_moi_cau_khoa_chi_khoa_MOT_dong_ke_ca_khi_buoc_qua_dong_R16(db, monkeypatch):
    from apps.vps.services.backends.public_ip import OvhStaticIpPoolBackend
    profile = _profile(db)
    _ip(db, "ip-1", huy_gia_han=True)
    _ip(db, "ip-2", huy_gia_han=True)
    _ip(db, "ip-3")
    cau = _cau_khoa(db, monkeypatch)

    ra = OvhStaticIpPoolBackend(db, profile).reserve(reservation_key="k", label="m")

    assert ra.id == "ip-3"                       # R16 van buoc qua dong da tat gia han
    assert len(cau) == 3, cau
    for c in cau:
        assert "FOR UPDATE SKIP LOCKED" in c, c
        assert "LIMIT 1" in c and "LIMIT 20" not in c, c


def test_het_dong_dung_duoc_thi_bao_CapacityExhausted_va_dung_lai(db, monkeypatch):
    from apps.vps.services.backends.contracts import CapacityExhausted
    from apps.vps.services.backends.public_ip import OvhStaticIpPoolBackend
    profile = _profile(db)
    _ip(db, "ip-1", huy_gia_han=True)
    _ip(db, "ip-2", huy_gia_han=True)
    cau = _cau_khoa(db, monkeypatch)

    with pytest.raises(CapacityExhausted):
        OvhStaticIpPoolBackend(db, profile).reserve(reservation_key="k", label="m")
    # hai dong bi loai + mot lan hoi khong con gi = ba cau; vong lap khong quay mai
    assert len(cau) == 3, cau
