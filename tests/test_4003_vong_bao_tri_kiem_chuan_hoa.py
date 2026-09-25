"""Máy lệch chuẩn phải HIỆN RA, không im lặng.

`tools/vps_chuan_hoa.py` kéo máy về chuẩn được — nhưng nó chạy bằng tay. Một
phép kiểm chạy bằng tay gộp hai trạng thái vào cùng một sự im lặng: *"chưa ai
chạy"* và *"chạy rồi, đạt"*. Đúng bài học 24/09 với cổng quản trị.

⇒ Vòng bảo trì tự đo mỗi ngày và ghi **một bản ghi sức khoẻ mỗi lượt**.

⚠️ Mốc RIÊNG: ba phép soi trong `mot_luot` từng dùng chung một mốc 24 giờ, và
   phép chạy trước khoá hai phép kia trong im lặng (lỗi thật, sửa 24/09). Thêm
   phép thứ tư mà dùng lại mốc chung là dựng lại chính cái bẫy đó.
"""
import pytest
from sqlalchemy import create_engine, select
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


def _coi(db):
    from apps.vps.tables import VpsGateway, VpsInfrastructureProfile, VpsInstance, VpsIp

    p = VpsInfrastructureProfile(
        id="profile-ovh", slug="ovh-sgp-prod", name="OVH", region="sgp",
        status="ACTIVE", accept_new=True, is_default=True,
        compute_backend_type="proxmox", public_ip_backend_type="ovh_static_pool",
        gateway_backend_type="nft", credential_ref="LTT_OVH")
    gw = VpsGateway(id="gw", infrastructure_profile_id=p.id, ten="gw", vung="sgp",
                    ip_cong_khai="51.79.166.36")
    db.add_all((p, gw,
                VpsInstance(id="may-208", user_id="u", plan_id="vps-nho", ten="A",
                            os_id="winsrv2016-core", gateway_id="gw", vmid=208,
                            trang_thai="dang_chay",
                            infrastructure_profile_id=p.id),
                VpsIp(id="ip1", gateway_id="gw", dia_chi="51.79.215.194",
                      state="BOUND", instance_id="may-208",
                      infrastructure_profile_id=p.id)))
    db.commit()
    return p


def _ban_ghi(db):
    from apps.vps import bao_tri
    from apps.vps.tables import VpsProfileHealth

    return db.execute(select(VpsProfileHealth).where(
        VpsProfileHealth.component == bao_tri.THANH_PHAN_CHUAN_HOA)).scalars().all()


def test_may_dung_chuan_thi_HEALTHY(db):
    from apps.vps import bao_tri

    p = _coi(db)
    bao_tri._kiem_chuan_hoa(db, p,
                            doc_cpu=lambda vmid: "host",
                            doc_fw=lambda vmid: {"enable": 1, "ipfilter": 1,
                                                 "macfilter": 1},
                            doc_onboot=lambda vmid: "1")
    db.commit()
    ban = _ban_ghi(db)
    assert len(ban) == 1 and ban[0].status == "HEALTHY"


def test_may_con_kvm64_thi_keu_va_NEU_TEN(db):
    from apps.vps import bao_tri

    p = _coi(db)
    bao_tri._kiem_chuan_hoa(db, p,
                            doc_cpu=lambda vmid: "kvm64",
                            doc_fw=lambda vmid: {"enable": 1, "ipfilter": 1,
                                                 "macfilter": 1},
                            doc_onboot=lambda vmid: "1")
    db.commit()
    ban = _ban_ghi(db)
    assert ban[0].status == "DEGRADED"
    assert "208" in ban[0].summary and "cpu" in ban[0].summary.lower()


def test_may_tat_chong_gia_mao_thi_keu(db):
    from apps.vps import bao_tri

    p = _coi(db)
    bao_tri._kiem_chuan_hoa(db, p, doc_cpu=lambda vmid: "host",
                            doc_fw=lambda vmid: {}, doc_onboot=lambda vmid: "1")
    db.commit()
    assert _ban_ghi(db)[0].status == "DEGRADED"
    assert "208" in _ban_ghi(db)[0].summary


def test_MOI_luot_deu_ghi_mot_ban_ghi(db):
    """"Chưa ai chạy" phải khác "chạy rồi, đạt"."""
    from apps.vps import bao_tri

    p = _coi(db)
    for _ in range(3):
        bao_tri._kiem_chuan_hoa(db, p, doc_cpu=lambda vmid: "host",
                                doc_fw=lambda vmid: {"enable": 1, "ipfilter": 1,
                                                     "macfilter": 1},
                                doc_onboot=lambda vmid: "1")
    db.commit()
    assert len(_ban_ghi(db)) == 3


def test_thanh_phan_NGOAI_tap_bat_buoc_va_KHONG_chan_ban():
    from apps.vps import bao_tri, profiles

    assert bao_tri.THANH_PHAN_CHUAN_HOA in profiles.CANH_BAO_BAO_TRI
    assert bao_tri.THANH_PHAN_CHUAN_HOA not in profiles.REQUIRED_HEALTH_COMPONENTS
    assert bao_tri.THANH_PHAN_CHUAN_HOA not in profiles.CHAN_BAN


def test_moc_RIENG_khong_dung_chung_voi_phep_soi_khac():
    """Ba phép soi trước từng dùng chung một mốc và khoá lẫn nhau 24 giờ."""
    import ast
    import pathlib

    cay = ast.parse(pathlib.Path("apps/vps/bao_tri.py").read_text(encoding="utf-8"))
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "_kiem_chuan_hoa_dinh_ky")
    ten_global = {t for n in ast.walk(ham) if isinstance(n, ast.Global) for t in n.names}
    assert ten_global == {"_moc_chuan_hoa"}, ten_global


def test_thieu_onboot_thi_keu(db):
    """🔴 Hạng mục thứ ba (25/09): thiếu `onboot` ⇒ host reboot là khách mất máy.
    Hai máy đã nằm tắt **17,4 giờ** vì đúng cờ này."""
    from apps.vps import bao_tri

    p = _coi(db)
    bao_tri._kiem_chuan_hoa(db, p, doc_cpu=lambda vmid: "host",
                            doc_fw=lambda vmid: {"enable": 1, "ipfilter": 1,
                                                 "macfilter": 1},
                            doc_onboot=lambda vmid: "0")
    db.commit()
    ban = _ban_ghi(db)
    assert ban[0].status == "DEGRADED"
    assert "onboot" in ban[0].summary
