"""Máy "muốn chạy" mà đang tắt thì hệ thống bật lại — có TRẦN.

🔴 Đo 25/09: host reboot lúc ~22:04, hai máy khách nằm tắt **17,4 giờ**. `onboot`
   sửa đúng gốc đó (Proxmox tự bật cùng host), nhưng nó ⛔ không phủ các đường
   khác: VM crash, OOM killer, một `qmstart` hỏng, hay ai đó tắt tay trên host.

⚠️ Và đây là chỗ một bản vá "tự chữa" dễ thành tai hoạ: máy **không boot được**
   sẽ bị bật lại mãi mãi, mỗi giờ một lần, và không ai biết vì nó im lặng thành
   công ở phía lệnh. Nên phải có **trần** và phải **ghi sự kiện khách đọc được**.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from platform_core.db import Base

NOW = datetime(2026, 9, 25, 16, 0, tzinfo=timezone.utc)


@pytest.fixture()
def db():
    import platform_core.models as _models  # noqa: F401
    from apps.vps import tables as _tables  # noqa: F401

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _coi(db, *, dien_mong="chay", trang_thai="dang_chay", tac_vu_dang=""):
    from apps.vps.tables import VpsGateway, VpsInfrastructureProfile, VpsInstance

    p = VpsInfrastructureProfile(
        id="p", slug="ovh-sgp-prod", name="OVH", region="sgp", status="ACTIVE",
        accept_new=True, is_default=True, compute_backend_type="proxmox",
        public_ip_backend_type="ovh_static_pool", gateway_backend_type="nft",
        credential_ref="LTT_OVH")
    db.add_all((p, VpsGateway(id="gw", infrastructure_profile_id=p.id, ten="gw",
                              vung="sgp", ip_cong_khai="51.79.166.36"),
                VpsInstance(id="may-208", user_id="u", plan_id="vps-nho", ten="A",
                            os_id="winsrv2016-core", gateway_id="gw", vmid=208,
                            trang_thai=trang_thai, dien_mong_muon=dien_mong,
                            infrastructure_profile_id=p.id)))
    db.commit()
    if tac_vu_dang:
        # ⛔ Constructor KHONG dat duoc `tac_vu` (cot co validator ep ve rong).
        #    `trang_thai_may.dat` la **duong ghi duy nhat** — test phai di dung
        #    duong ay, neu khong no do mot the gioi khong ton tai.
        from apps.vps import trang_thai_may as tt

        may = db.get(VpsInstance, "may-208")
        tt.dat(may, tac_vu=tac_vu_dang)
        db.commit()
    return p


def _su_kien(db, loai="tu_bat_lai"):
    from apps.vps.tables import VpsEvent

    return db.execute(select(VpsEvent).where(VpsEvent.loai == loai)).scalars().all()


def test_may_muon_chay_ma_dang_tat_thi_BAT_LAI(db):
    from apps.vps import bao_tri

    p = _coi(db)
    da_bat = []
    n = bao_tri._bat_lai_may_muon_chay(
        db, p, doc_dien=lambda vmid: "tat",
        bat=lambda vmid: da_bat.append(vmid), now=NOW)
    db.commit()

    assert n == 1 and da_bat == [208]
    assert len(_su_kien(db)) == 1, "phai ghi su kien khach doc duoc"


def test_may_dang_chay_thi_KHONG_dung_toi(db):
    from apps.vps import bao_tri

    p = _coi(db)
    da_bat = []
    assert bao_tri._bat_lai_may_muon_chay(
        db, p, doc_dien=lambda vmid: "chay",
        bat=lambda vmid: da_bat.append(vmid), now=NOW) == 0
    assert da_bat == []


def test_KHONG_doc_duoc_dien_thi_KHONG_bat(db):
    """⛔ `khong_ro` là một lần hỏi THẤT BẠI, không phải bằng chứng máy đang tắt.
    Bật một máy có thể đang chạy là cách tạo ra sự cố từ một lần mất mạng."""
    from apps.vps import bao_tri

    p = _coi(db)
    da_bat = []
    assert bao_tri._bat_lai_may_muon_chay(
        db, p, doc_dien=lambda vmid: "khong_ro",
        bat=lambda vmid: da_bat.append(vmid), now=NOW) == 0
    assert da_bat == []


def test_may_dang_co_THAO_TAC_thi_khong_chen_vao(db):
    from apps.vps import bao_tri

    p = _coi(db, tac_vu_dang="dang_kd_lai")
    da_bat = []
    assert bao_tri._bat_lai_may_muon_chay(
        db, p, doc_dien=lambda vmid: "tat",
        bat=lambda vmid: da_bat.append(vmid), now=NOW) == 0
    assert da_bat == []


@pytest.mark.parametrize("trang_thai", ["loi", "da_xoa", "bi_treo"])
def test_may_KHONG_o_trang_thai_phuc_vu_thi_khong_bat(db, trang_thai):
    """Máy lỗi/đã xoá/bị treo vì hết tiền: bật lại là đi ngược nghiệp vụ."""
    from apps.vps import bao_tri

    p = _coi(db, trang_thai=trang_thai)
    da_bat = []
    assert bao_tri._bat_lai_may_muon_chay(
        db, p, doc_dien=lambda vmid: "tat",
        bat=lambda vmid: da_bat.append(vmid), now=NOW) == 0
    assert da_bat == []


def test_TRAN_chan_vong_lap_bat_tat(db):
    """⚠️ Một máy không boot được sẽ bị bật lại mỗi giờ, mãi mãi, và im lặng
    thành công ở phía lệnh. Trần là thứ biến nó thành một tín hiệu."""
    from apps.vps import bao_tri
    from apps.vps.tables import VpsEvent

    p = _coi(db)
    for lan in range(bao_tri.TRAN_TU_BAT_MOI_NGAY):
        db.add(VpsEvent(instance_id="may-208", loai="tu_bat_lai", boi="he_thong",
                        chi_tiet={}, created_at=NOW - timedelta(hours=lan + 1)))
    db.commit()

    da_bat = []
    assert bao_tri._bat_lai_may_muon_chay(
        db, p, doc_dien=lambda vmid: "tat",
        bat=lambda vmid: da_bat.append(vmid), now=NOW) == 0
    assert da_bat == [], "cham tran ma van bat = vong lap vo tan"


def test_tran_chi_tinh_trong_24_gio(db):
    """Trần là 'mỗi ngày', không phải 'mãi mãi' — máy hỏng hôm qua đã sửa thì
    hôm nay phải được bật lại."""
    from apps.vps import bao_tri
    from apps.vps.tables import VpsEvent

    p = _coi(db)
    for _ in range(bao_tri.TRAN_TU_BAT_MOI_NGAY + 2):
        db.add(VpsEvent(instance_id="may-208", loai="tu_bat_lai", boi="he_thong",
                        chi_tiet={}, created_at=NOW - timedelta(days=3)))
    db.commit()

    da_bat = []
    assert bao_tri._bat_lai_may_muon_chay(
        db, p, doc_dien=lambda vmid: "tat",
        bat=lambda vmid: da_bat.append(vmid), now=NOW) == 1
    assert da_bat == [208]
