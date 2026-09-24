"""Mua IP OVH trên đường TẠO MỚI: bằng chứng khách đã cam kết trả là GIỮ CHỖ.

🔴 Đo trên production 2026-09-24 12:57: job `2159e8ef` chết 3/3 lần ở 80%
   (`dang cap dia chi cong khai`) với
   `BackendConflict: acquisition requires a paid VPS subscription`, và
   `vps_external_mutation` không có hàng `OVH_IP_ACQUIRE` nào — cửa chặn trước
   khi chạm OVH.

Gốc: `cd3c7058` (23/09) chuyển đường tạo mới sang `credit.giu_cho`/`quyet_toan`,
nên `paid_until` chỉ được đặt ở `jobs._quyet_toan` — **sau** bước cấp IP. Cửa
`ensure_free_ip` vẫn hỏi `billing.con_han` ⇒ máy mới luôn `paid_until = None`
⇒ hồi quy TẤT ĐỊNH: không ai tạo được máy nào nữa.

Vì sao `test_1030` không đỏ: fixture ở đó đặt `paid_until = 2099-01-01` cho MỌI
ca, nên luồng "chưa trả tiền vì đang giữ chỗ" chưa từng được đo.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from platform_core.db import Base


class _DaQuaCua(BaseException):
    """Cửa đã cho đi qua. Kế thừa `BaseException` để `except Exception` của
    `ensure_free_ip` không bắt nó và biến nó thành một lỗi khác."""


@pytest.fixture()
def db():
    import platform_core.models as _models  # noqa: F401
    from apps.vps import tables as _tables  # noqa: F401

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _coi(db, *, paid_until=None):
    """Một máy MỚI đúng như production dựng nó: chưa có `paid_until`."""
    from platform_core.models import CREDIT_GRANT, CreditEntry, User
    from apps.vps.tables import VpsGateway, VpsInfrastructureProfile, VpsInstance

    profile = VpsInfrastructureProfile(
        id="profile-ovh", slug="ovh-sgp-prod", name="OVH", region="sgp",
        status="ACTIVE", accept_new=True, is_default=True,
        compute_backend_type="proxmox", public_ip_backend_type="ovh_static_pool",
        gateway_backend_type="nft", credential_ref="LTT_OVH",
        provider_config={
            "auto_acquire": True, "ip_plan_code": "ip-failover-arin",
            "ip_country": "SG", "ip_datacenter": "SGP", "ip_duration": "P1M",
            "ip_currency": "USD", "max_ip_with_tax_minor": 500,
            "order_delivery_timeout_seconds": 3600,
        },
    )
    gateway = VpsGateway(
        id="gateway-ovh", infrastructure_profile_id=profile.id,
        ten="OVH gateway", vung="sgp", ip_cong_khai="192.0.2.1")
    may = VpsInstance(
        id="instance-new", user_id="chu-may", plan_id="vps-nho",
        os_id="winsrv2016-core", gateway_id=gateway.id,
        infrastructure_profile_id=profile.id, profile_resolution_state="PINNED",
        vmid=208, paid_until=paid_until)
    db.add_all((profile, gateway, may,
                User(id="chu-may", email="chu@vi.du", password_hash="x"),
                CreditEntry(user_id="chu-may", delta=5000, kind=CREDIT_GRANT,
                            note="von test")))
    db.commit()
    return profile, gateway, may


class _ProviderChanCua:
    """Chạm tới provider = cửa đã cho đi qua."""

    def list_additional_ipv4(self):
        raise _DaQuaCua()


class _Gateway:
    def list_mappings(self):
        return {}


def _mua(db, profile, gateway, may, *, job_id):
    from apps.vps.services.ovh_acquisition import ensure_free_ip

    return ensure_free_ip(
        db, profile, instance=may, gateway_row=gateway,
        provider=_ProviderChanCua(), gateway=_Gateway(),
        operation_id=f"provision:{may.id}", job_id=job_id)


def test_giu_cho_con_song_mo_cua_mua_ip_du_chua_dat_paid_until(db):
    """Đây là ca của production: tiền đang được GIỮ, chưa quyết toán."""
    from platform_core import credit

    profile, gateway, may = _coi(db)
    credit.giu_cho(db, "chu-may", 1490, "job-tao-may")
    db.commit()

    with pytest.raises(_DaQuaCua):
        _mua(db, profile, gateway, may, job_id="job-tao-may")


def test_khong_tra_tien_khong_giu_cho_thi_van_bi_chan(db):
    """Cửa không được mở rộng hơn: không có bằng chứng nào thì không mua."""
    from apps.vps.services.backends.contracts import BackendConflict

    profile, gateway, may = _coi(db)

    with pytest.raises(BackendConflict, match="paid VPS subscription"):
        _mua(db, profile, gateway, may, job_id="job-tao-may")


def test_giu_cho_da_nha_khong_con_mo_cua(db):
    """R4 vẫn đứng: job đã nhả tiền thì không được mua IP cho nó nữa."""
    from platform_core import credit
    from apps.vps.services.backends.contracts import BackendConflict

    profile, gateway, may = _coi(db)
    credit.giu_cho(db, "chu-may", 1490, "job-tao-may")
    credit.hoan(db, "chu-may", "job-tao-may")
    db.commit()

    with pytest.raises(BackendConflict, match="paid VPS subscription"):
        _mua(db, profile, gateway, may, job_id="job-tao-may")


def test_may_da_tra_tien_van_mua_duoc_khong_can_job(db):
    """Đường gia hạn/dựng lại không có job giữ chỗ — `paid_until` vẫn là bằng chứng."""
    profile, gateway, may = _coi(
        db, paid_until=datetime(2099, 1, 1, tzinfo=timezone.utc))

    with pytest.raises(_DaQuaCua):
        _mua(db, profile, gateway, may, job_id="")


def test_duong_tao_may_truyen_job_id_toi_cua_mua_ip(db, monkeypatch):
    """Cửa chỉ đúng nếu `job_id` **tới được** nó: chốt cả sợi dây, không chỉ cửa.

    ⛔ Không đo bằng chữ ký hàm: một chữ ký có tham số `job_id` mà người gọi
       không truyền vẫn để nguyên hồi quy.
    """
    from apps.vps import jobs as vps_jobs
    from apps.vps.services import ovh_acquisition

    profile, gateway, may = _coi(db)
    da_nhan = {}

    def _bat(db_, profile_, **kw):
        da_nhan.update(kw)
        raise _DaQuaCua()

    monkeypatch.setattr(ovh_acquisition, "reserve_for_provision", _bat)
    monkeypatch.setattr(vps_jobs.backend_factory, "public_ip_backend",
                        lambda *a, **k: object())
    monkeypatch.setattr(vps_jobs.backend_factory, "ovh_ordering_client",
                        lambda *a, **k: object())
    monkeypatch.setattr(vps_jobs.backend_factory, "gateway_backend",
                        lambda *a, **k: object())
    gateway.cho_phep_ip_rieng = True
    db.commit()

    with pytest.raises(_DaQuaCua):
        vps_jobs._cap_ip_cong_khai(
            db, may, gateway, "10.50.0.60", profile,
            operation_id=f"provision:{may.id}", job_id="job-tao-may")

    assert da_nhan.get("job_id") == "job-tao-may"
