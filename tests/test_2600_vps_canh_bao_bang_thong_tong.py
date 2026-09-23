"""Lop canh bang thong THEO TONG phai NOI RA khi no mat tin hieu.

🔴 Van de, chu du an chi ra 23/09/2026. `_can_ham_theo_tong` doc bo dem cua
   cong vao OVH qua SSH. Doc hong (SSH chet, thieu bien moi truong) thi no
   `log.warning` roi `return set()` — tuc **im lang ngung canh**. Mot dong log
   trong mot vong bao tri chay moi gio la mot dong khong ai doc.

   Cai gia neu SSH hong dai ngay: cong vao la OVH VPS-1 Singapore, han muc
   1 TB/thang, vuot thi OVH ham 10 Mbps cho TAT CA — ke ca VM100-107, viec
   that cua chu du an. Thu dau tien phat hien ra se la hoa don, hoac ca nen
   tang bong cham.

⭐ Day dung khuon "do vang mat thi xoa cung xanh"
   (`docs/BAY_TRONG_CONG_CHAT_LUONG.md`): mot lop bao ve bien mat trong im
   lang thi khong phep kiem nao do duoc rang no da bien mat.

Nen o day chot BA dieu:
  1. Doc hong  -> tin hieu BAT  (co doi chung: doc duoc -> TAT).
  2. Tin hieu ay den duoc CHO NGUOI VAN HANH NHIN: dict ket qua vong bao tri,
     va `profiles.canh_bao` (trang admin doc).
  3. Lop RIENG (han muc tung khach) VAN chay khi lop tong mat tin hieu —
     khong nao long phep kiem nao dang co.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from apps.vps import bao_tri, profiles
from apps.vps.services.ssh_lenh import SshLenhError
from platform_core.db import Base

PID = "p-ovh"
BAY_GIO = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def db():
    import platform_core.models as _models  # noqa: F401
    from apps.vps import tables as _tables  # noqa: F401
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture()
def profile(db):
    from apps.vps.tables import VpsInfrastructureProfile
    p = VpsInfrastructureProfile(
        id=PID, slug="ovh-sgp", name="OVH-SGP", region="sgp", status="ACTIVE",
        accept_new=True, is_default=True, compute_backend_type="proxmox",
        public_ip_backend_type="ovh_static_pool", gateway_backend_type="nft",
        credential_ref="LTT_OVH")
    db.add(p)
    db.flush()
    return p


def _doc_hong(monkeypatch, ly_do="cong vao khong tra loi trong 60s"):
    monkeypatch.setattr(bao_tri, "_doc_cau_hinh_cong_vao",
                        lambda *a, **k: (_ for _ in ()).throw(SshLenhError(ly_do)))


def _router_gia(monkeypatch):
    """Router doc duoc, khong ham ai. Thieu no thi `_dong_bo_bang_thong` bo ngang
    o buoc 1 va lop TONG khong bao gio chay — tuc phep kiem do nham thu."""
    from types import SimpleNamespace
    from apps.vps.services import backend_factory
    monkeypatch.setattr(backend_factory, "router_backend", lambda profile:
                        SimpleNamespace(doc_bang_thong=lambda: {},
                                        danh_sach_giam_toc=lambda: set(),
                                        theo_doi_bang_thong=lambda ip: None,
                                        dat_giam_toc=lambda ip, bat: None))


def _doc_duoc(monkeypatch, rx=1, tx=1):
    monkeypatch.setattr(bao_tri, "_doc_cau_hinh_cong_vao", lambda *a, **k: object())
    monkeypatch.setattr(bao_tri, "_doc_bo_dem_cong_vao", lambda dich, **k: (rx, tx))


# ── 1. tin hieu BAT khi mat, TAT khi co lai ─────────────────────────────────

def test_doc_bo_dem_hong_thi_ghi_mot_tin_hieu_KHONG_khoe(db, profile, monkeypatch):
    _doc_hong(monkeypatch)
    bao_tri._can_ham_theo_tong(profile, [], now=BAY_GIO, db=db)
    db.flush()
    trang_thai = dict(profiles.canh_bao(db, PID)).get(bao_tri.THANH_PHAN_BANG_THONG_TONG)
    assert trang_thai is not None, "mat tin hieu ma khong ai thay"
    assert trang_thai != "HEALTHY"


def test_doc_duoc_thi_tin_hieu_TAT(db, profile, monkeypatch):
    """Doi chung. Thieu no thi phep tren xanh ca khi tin hieu BAT vinh vien."""
    _doc_duoc(monkeypatch)
    bao_tri._can_ham_theo_tong(profile, [], now=BAY_GIO, db=db)
    db.flush()
    assert bao_tri.THANH_PHAN_BANG_THONG_TONG not in dict(profiles.canh_bao(db, PID))


def test_doc_duoc_tro_lai_thi_xoa_tin_hieu_cu(db, profile, monkeypatch):
    _doc_hong(monkeypatch)
    bao_tri._can_ham_theo_tong(profile, [], now=BAY_GIO, db=db)
    db.flush()
    _doc_duoc(monkeypatch)
    bao_tri._can_ham_theo_tong(profile, [], now=BAY_GIO, db=db)
    db.flush()
    assert bao_tri.THANH_PHAN_BANG_THONG_TONG not in dict(profiles.canh_bao(db, PID))


def test_hong_lien_tiep_duoc_DEM_chu_khong_chi_ghi_lan_cuoi(db, profile, monkeypatch):
    """Mot lan hong thoang qua khac han mot tuan SSH chet. Phai phan biet duoc."""
    _doc_hong(monkeypatch)
    for _ in range(3):
        bao_tri._can_ham_theo_tong(profile, [], now=BAY_GIO, db=db)
    db.flush()
    assert bao_tri.so_lan_mat_tin_hieu(profile) == 3
    _doc_duoc(monkeypatch)
    bao_tri._can_ham_theo_tong(profile, [], now=BAY_GIO, db=db)
    assert bao_tri.so_lan_mat_tin_hieu(profile) == 0


# ── 2. tin hieu den duoc cho NGUOI VAN HANH nhin ────────────────────────────

def test_thanh_phan_nay_KHONG_nam_trong_tap_preflight_ghi(db):
    """`preflight` duyet `REQUIRED_HEALTH_COMPONENTS` va doi mot trang thai cho
    TUNG thanh phan. Them thanh phan nay vao do se lam preflight ném KeyError —
    no do boi VONG BAO TRI, khong phai boi preflight."""
    assert bao_tri.THANH_PHAN_BANG_THONG_TONG not in profiles.REQUIRED_HEALTH_COMPONENTS
    assert bao_tri.THANH_PHAN_BANG_THONG_TONG in profiles.CANH_BAO_BAO_TRI
    assert not set(profiles.CANH_BAO_BAO_TRI) & set(profiles.REQUIRED_HEALTH_COMPONENTS)


def test_ket_qua_vong_bao_tri_dem_so_profile_mat_tin_hieu(db, profile, monkeypatch):
    """Dong `log.info` tong ket cua vong bao tri phai NOI duoc so nay."""
    _router_gia(monkeypatch)
    _doc_hong(monkeypatch)
    # Khong co may nao song, nen lop rieng khong lam gi — dung y: phep nay do
    # DUNG mot thu, la con so mat tin hieu co len toi dict ket qua khong.
    assert bao_tri._dong_bo_bang_thong_pinned(db) == 0
    assert bao_tri.dem_profile_mat_tin_hieu(db) == 1


def test_dong_bo_bang_thong_pinned_LUON_tra_mot_so_nguyen(db, profile, monkeypatch):
    """🔴 Do that 23/09: ban dau toi cho ham nay tra `int` HOAC `dict` tuy mot
    co. `test_555` do ngay — no gia lap ham nay bang mot `int`, va `mot_luot`
    thi da doi sang doc dict.

    Mot ham doi KIEU tra ve theo tham so la mot ham ma MOI cho gia lap no deu
    phai biet ca co do. So profile mat tin hieu nay dem rieng o
    `dem_profile_mat_tin_hieu`.
    """
    _router_gia(monkeypatch)
    _doc_duoc(monkeypatch)
    assert isinstance(bao_tri._dong_bo_bang_thong_pinned(db), int)
    assert isinstance(bao_tri.dem_profile_mat_tin_hieu(db), int)


# ── 3. KHONG noi long lop dang co ───────────────────────────────────────────

def test_mat_tin_hieu_tong_thi_KHONG_ep_ham_may_nao(db, profile, monkeypatch):
    """Fail-open la CHU Y cho mot lan hong thoang qua — chot lai de doi sau
    phai co nguoi quyet, chu khong troi di trong mot ban sua khac."""
    _doc_hong(monkeypatch)
    assert bao_tri._can_ham_theo_tong(profile, [], now=BAY_GIO, db=db) == set()


def test_lop_RIENG_van_ham_khach_vuot_han_muc_khi_lop_tong_mat_tin_hieu(
        db, profile, monkeypatch):
    """Lop tong bo luot khong duoc keo theo lop rieng — hai cau hoi khac nhau."""
    from apps.vps import bang_thong
    from apps.vps.cost import lay_plan
    from apps.vps.tables import VpsInstance

    plan = lay_plan("vps-nho")
    may = VpsInstance(id="i-1", user_id="u", plan_id="vps-nho", ten="m",
                      os_id="winsrv2016-core", gateway_id=None,
                      bang_thong_byte=(plan.bang_thong_gb + 1) * 1024 ** 3)
    assert bang_thong.vuot_han_muc(may) is True
