"""VPS V4 R21 — a failed power command re-measures the machine; force stop exists.

Measured 16/09 on production: soft stop of VM 204 (no OS yet, ignores ACPI)
timed out. `dien_mong_muon=tat` + `dien_quan_sat=khong_ro` projected to
"Đã tắt" with only a "Bật" button while the VM kept running, and the designed
customer-initiated force stop had no route.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from platform_core.db import Base
from tests.fixtures.vps_proxmox_gia import ProxmoxGia


@pytest.fixture()
def db():
    import platform_core.models as _models  # noqa: F401
    from apps.vps import tables as _tables  # noqa: F401
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _may_vua_xin_tat(db):
    from apps.vps import trang_thai_may as tt
    from apps.vps.tables import VpsInstance

    may = VpsInstance(id="m-204", user_id="owner", plan_id="vps-nho",
                      os_id="winsrv2022-core", gateway_id="g", vmid=204,
                      **tt.moi())
    tt.dat(may, vong_doi=tt.HOAT_DONG, dien_quan_sat=tt.CHAY, tac_vu=tt.KHONG_CO)
    tt.dat(may, dien_mong_muon=tt.TAT)          # what `dieu_khien.xin` does
    db.add(may)
    db.commit()
    return may


def test_failed_soft_stop_remeasures_power_and_shows_running(db):
    from apps.vps import jobs
    from apps.vps.tables import VpsEvent, VpsInstance

    _may_vua_xin_tat(db)
    px = ProxmoxGia(dien="running", vmid=204)
    jobs._ghi_thao_tac_hong(db, None, {"instance_id": "m-204", "boi": "owner"}, "tat",
                            "tac_vu_that_bai", "VM quit/powerdown failed - got timeout",
                            client=px)
    may = db.get(VpsInstance, "m-204")
    assert (may.trang_thai, may.dien_mong_muon, may.dien_quan_sat) == (
        "dang_chay", "chay", "chay")
    assert db.execute(select(VpsEvent.loai)).scalars().all() == ["tat_that_bai"]


def test_without_a_measurement_the_old_projection_still_says_stopped(db):
    """Counterfactual of the production bug: no re-measure keeps 'Đã tắt'."""
    from apps.vps import jobs
    from apps.vps.tables import VpsInstance

    _may_vua_xin_tat(db)
    jobs._ghi_thao_tac_hong(db, None, {"instance_id": "m-204"}, "tat",
                            "tac_vu_that_bai", "timeout", client=None)
    assert db.get(VpsInstance, "m-204").trang_thai == "da_tat"


def test_force_stop_route_exists_and_uses_the_audited_command():
    from apps.vps import routes
    from apps.vps.services import dieu_khien

    paths = {getattr(r, "path", "") for r in routes.router.routes}
    assert "/{instance_id}/tat-cung" in paths
    assert "tat_cung" in dieu_khien.LENH
