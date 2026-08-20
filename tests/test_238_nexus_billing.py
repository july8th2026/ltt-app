"""Nexus Phase 5 — thuê bao theo máy/tháng (Q98).

Mặc định an toàn được chốt kỹ nhất: **giá 0 → miễn phí, không cưỡng chế, không
trừ**. Đây là điều charter đòi (không tự bật thu phí) và cũng là điều dễ vô tình
làm sai nhất — một `da_thanh_toan` trả False khi giá 0 sẽ chặn mọi người dùng
trong khi chưa ai định thu tiền.
"""
from __future__ import annotations

import pytest

from platform_core import credit
from platform_core.nexus import billing, sessions
from platform_core.nexus.devices import NexusError


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'bill.db').as_posix()}")
    monkeypatch.delenv("LTT_NEXUS_GIA_MAY_THANG", raising=False)
    monkeypatch.delenv("LTT_NEXUS_AN_HAN_NGAY", raising=False)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        try: next(gen)
        except StopIteration: pass
        dbmod.reset_engine()


def _khoa():
    from platform_core.nexus import agent_auth
    _p, pub = agent_auth.new_keypair_for_test()
    return pub


def _may(db, *, credit_ban_dau=0):
    from platform_core.users import tao_nguoi_dung
    from platform_core.nexus import devices
    u = tao_nguoi_dung(db, email="bill@ex.com", password="mat-khau-dai-123456",
                       is_verified=True)
    db.flush()
    if credit_ban_dau:
        credit.nap(db, u.id, credit_ban_dau)
    _r, ma = devices.tao_ma_ghep(db, user_id=u.id)
    dev = devices.doi_ma(db, code=ma, public_key=_khoa(), display_name="M")
    db.flush()
    return u, dev


# ── Mặc định miễn phí: giá 0 không chặn ai ──────────────────────────────────

def test_gia_mac_dinh_la_0():
    assert billing.gia_may_thang(env={}) == 0


def test_mien_phi_thi_luon_thanh_toan(db):
    _u, dev = _may(db)
    assert billing.da_thanh_toan(dev, env={}) is True     # paid_until None van OK
    # cap_ve khong bi chan khi mien phi
    _row, _ve = sessions.cap_ve(db, user_id=dev.user_id, device=dev)


def test_mien_phi_thi_thu_phi_khong_lam_gi(db):
    _u, dev = _may(db, credit_ban_dau=1000)
    ket = billing.thu_phi_thang(db, env={})
    assert ket["tru"] == 0
    assert credit.so_du(db, dev.user_id) == 1000          # khong tru dong nao


# ── Có giá: trừ credit, đẩy hạn, cưỡng chế ──────────────────────────────────

def test_co_gia_tru_mot_thang_va_day_han(db, monkeypatch):
    monkeypatch.setenv("LTT_NEXUS_GIA_MAY_THANG", "100")
    u, dev = _may(db, credit_ban_dau=250)
    ket = billing.thu_phi_thang(db)
    assert ket["tru"] == 1
    assert credit.so_du(db, u.id) == 150                  # 250 - 100
    assert dev.paid_until is not None
    # Chay lai ngay: con han, khong tru lai (idempotent trong thang)
    ket2 = billing.thu_phi_thang(db)
    assert ket2["tru"] == 0
    assert credit.so_du(db, u.id) == 150


def test_co_gia_da_thanh_toan_sau_khi_tru(db, monkeypatch):
    monkeypatch.setenv("LTT_NEXUS_GIA_MAY_THANG", "100")
    u, dev = _may(db, credit_ban_dau=100)
    assert billing.da_thanh_toan(dev) is False            # chua tra
    billing.thu_phi_thang(db)
    assert billing.da_thanh_toan(dev) is True             # da tra


def test_het_credit_thi_khong_tru_va_cap_ve_tu_choi(db, monkeypatch):
    monkeypatch.setenv("LTT_NEXUS_GIA_MAY_THANG", "100")
    u, dev = _may(db, credit_ban_dau=50)                  # khong du 100
    ket = billing.thu_phi_thang(db)
    assert ket["thieu_credit"] == 1 and ket["tru"] == 0
    assert credit.so_du(db, u.id) == 50                   # khong tru gi
    assert dev.paid_until is None                         # khong day han
    with pytest.raises(NexusError):
        sessions.cap_ve(db, user_id=dev.user_id, device=dev)   # bi chan


def test_nap_them_credit_roi_thu_lai_thi_thanh_toan(db, monkeypatch):
    monkeypatch.setenv("LTT_NEXUS_GIA_MAY_THANG", "100")
    u, dev = _may(db, credit_ban_dau=50)
    billing.thu_phi_thang(db)                             # thieu -> khong tra
    credit.nap(db, u.id, 100)                             # khach nap them
    billing.thu_phi_thang(db)
    assert billing.da_thanh_toan(dev) is True
    # Gio cap_ve duoc.
    sessions.cap_ve(db, user_id=dev.user_id, device=dev)


# ── credit.tru: không để số dư âm ───────────────────────────────────────────

def test_tru_khong_du_thi_False_va_khong_ghi(db):
    from platform_core.users import tao_nguoi_dung
    from platform_core.models import CREDIT_NEXUS_BILL
    u = tao_nguoi_dung(db, email="t@ex.com", password="mat-khau-dai-123456",
                       is_verified=True)
    credit.nap(db, u.id, 30); db.flush()
    assert credit.tru(db, u.id, 100, kind=CREDIT_NEXUS_BILL) is False
    assert credit.so_du(db, u.id) == 30                   # nguyen ven
    assert credit.tru(db, u.id, 20, kind=CREDIT_NEXUS_BILL) is True
    assert credit.so_du(db, u.id) == 10


def test_may_thu_hoi_khong_bi_tinh_phi(db, monkeypatch):
    monkeypatch.setenv("LTT_NEXUS_GIA_MAY_THANG", "100")
    from platform_core.nexus import devices
    u, dev = _may(db, credit_ban_dau=500)
    devices.thu_hoi(db, dev, by="owner"); db.flush()
    ket = billing.thu_phi_thang(db)
    assert ket["tru"] == 0                                # may da thu hoi -> bo qua
    assert credit.so_du(db, u.id) == 500
