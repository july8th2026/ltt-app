"""Suc khoe profile VPS co HAI tang: chan ban, va canh bao.

🔴 Do 23/09/2026. `select_profile` doi CA SAU thanh phan HEALTHY. Mot trong sau
   la `network`, va `network` lay thang `domains.network` cua May B — mien do
   do CHI vi mot phep: `wireguard.gateway.tx_dropped`. 12/13 phep kiem mang con
   lai deu PASS (wg handshake 72s, nftables bat, fail-closed dung, 10 IP cong
   khai, 8 anh xa).

   Hau qua do duoc tren bang `vps_profile_health` tu 16/09: HEALTHY 608 ·
   CRITICAL 136 · DEGRADED 94 · STALE 173. Cua hang bat tat theo cua so 10
   phut — 15:10 xanh, 15:20 do, 15:30 do. Khach ban duoc hay khong phu thuoc
   vao viec ho bam trung cua so nao.

⭐ Goi roi trong duong ham KHONG ngan `qm clone` chay. Do 30 giay luc 15:40
   ngay 23/09: 1.786 goi TX, 0 goi roi, 0,12 Mbit/s — cac cum roi la tung dot.
   Do la tin hieu CHAT LUONG, khong phai tin hieu GIAO DUOC HAY KHONG.

   Nen: `select_profile` (giu cua hang mo) chi doi tang `CHAN_BAN`.
        `activate_profile` (nguoi van hanh bat ban lan dau) van doi CA SAU.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from apps.vps import profiles
from platform_core.db import Base


@pytest.fixture()
def db():
    import platform_core.models as _models  # noqa: F401
    from apps.vps import tables as _tables  # noqa: F401
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


PID = "p-ovh"


def _profile(db):
    from apps.vps.tables import VpsInfrastructureProfile
    p = VpsInfrastructureProfile(
        id=PID, slug="ovh-sgp", name="OVH-SGP", region="sgp", status="ACTIVE",
        accept_new=True, is_default=True, compute_backend_type="proxmox",
        public_ip_backend_type="ovh_static_pool", gateway_backend_type="nft",
        credential_ref="LTT_OVH")
    db.add(p)
    db.flush()
    return p


def _health(db, **trang_thai):
    """Ghi mot ban ghi suc khoe tuoi cho moi thanh phan bat buoc."""
    from apps.vps.tables import VpsProfileHealth
    now = datetime.now(timezone.utc)
    for thanh_phan in profiles.REQUIRED_HEALTH_COMPONENTS:
        db.add(VpsProfileHealth(
            infrastructure_profile_id=PID, component=thanh_phan,
            status=trang_thai.get(thanh_phan, "HEALTHY"),
            summary="", observed_at=now, generated_at=now))
    db.flush()


# ── hai tang phu kin, khong chong lan ────────────────────────────────────────

def test_hai_tang_chia_doi_dung_tap_thanh_phan_bat_buoc():
    """Them mot thanh phan ma quen xep tang = mot thanh phan khong ai gac."""
    assert set(profiles.CHAN_BAN) | set(profiles.CANH_BAO) == set(
        profiles.REQUIRED_HEALTH_COMPONENTS)
    assert not set(profiles.CHAN_BAN) & set(profiles.CANH_BAO)


def test_network_nam_o_tang_canh_bao_chu_khong_chan_ban():
    assert "network" in profiles.CANH_BAO
    assert "network" not in profiles.CHAN_BAN


@pytest.mark.parametrize("thanh_phan", ["compute", "ip", "gateway", "capacity"])
def test_bon_thanh_phan_giao_duoc_van_chan_ban(thanh_phan):
    assert thanh_phan in profiles.CHAN_BAN


# ── hanh vi that ─────────────────────────────────────────────────────────────

def test_network_do_KHONG_con_dong_cua_hang(db):
    """Chinh ca 23/09: mot bo dem goi roi khong duoc chan ban nua."""
    _profile(db)
    _health(db, network="CRITICAL")
    ok, ly_do, _ = profiles.health_prerequisites(db, PID)
    assert ok is True, ly_do
    assert profiles.select_profile(db, region="sgp").id == PID


def test_compute_do_VAN_dong_cua_hang(db):
    _profile(db)
    _health(db, compute="CRITICAL")
    ok, ly_do, _ = profiles.health_prerequisites(db, PID)
    assert ok is False
    assert "compute" in ly_do
    with pytest.raises(profiles.ProfileNotReady):
        profiles.select_profile(db, region="sgp")


def test_bat_ban_lan_dau_van_doi_ca_sau_thanh_phan(db):
    """`activate_profile` la mot quyet dinh CO NGUOI — no giu fail-closed day du."""
    _profile(db)
    _health(db, network="CRITICAL")
    with pytest.raises(profiles.ProfileNotReady):
        profiles.activate_profile(db, PID)


def test_thanh_phan_chan_ban_bi_thieu_van_la_dong_cua(db):
    """Thieu ban ghi khac han 'co ban ghi mau xanh'. Fail-closed giu nguyen."""
    from apps.vps.tables import VpsProfileHealth
    _profile(db)
    _health(db)
    for row in db.query(VpsProfileHealth).filter(
            VpsProfileHealth.component == "ip").all():
        db.delete(row)
    db.flush()
    ok, ly_do, _ = profiles.health_prerequisites(db, PID)
    assert ok is False
    assert "ip" in ly_do


def test_thanh_phan_canh_bao_bi_thieu_khong_dong_cua(db):
    from apps.vps.tables import VpsProfileHealth
    _profile(db)
    _health(db)
    for row in db.query(VpsProfileHealth).filter(
            VpsProfileHealth.component == "network").all():
        db.delete(row)
    db.flush()
    assert profiles.health_prerequisites(db, PID)[0] is True


def test_thanh_phan_chan_ban_qua_cu_van_dong_cua(db):
    """Cu = khong biet. Khong biet thi khong ban — day khong phai canh bao."""
    from apps.vps.tables import VpsProfileHealth
    _profile(db)
    _health(db)
    cu = datetime.now(timezone.utc) - timedelta(
        seconds=profiles.HEALTH_MAX_AGE_SECONDS + 60)
    for row in db.query(VpsProfileHealth).filter(
            VpsProfileHealth.component == "capacity").all():
        row.observed_at = cu
    db.flush()
    ok, ly_do, _ = profiles.health_prerequisites(db, PID)
    assert ok is False
    assert "capacity" in ly_do


# ── canh bao phai NHIN THAY duoc, khong phai bi bo ───────────────────────────

def test_canh_bao_liet_ke_dung_thanh_phan_dang_do(db):
    """Bo `network` khoi cong ban ma khong ai nhin no = bo that.

    Do la ca `tong_da_hua_gb` da mac: mot ham viet ra de canh, khong ai goi.
    """
    _profile(db)
    _health(db, network="CRITICAL")
    canh = dict(profiles.canh_bao(db, PID))
    assert canh.get("network") == "CRITICAL"
    assert "compute" not in canh


def test_khong_co_gi_do_thi_khong_co_canh_bao(db):
    _profile(db)
    _health(db)
    assert profiles.canh_bao(db, PID) == []
