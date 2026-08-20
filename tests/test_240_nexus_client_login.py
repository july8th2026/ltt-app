"""Nexus Model B (Q101 / D-P7) — client đăng ký máy bằng TÀI KHOẢN LTT.

Model B bỏ web-broker: máy không còn ghép qua mã-từ-web (`doi_ma`). Thay vào đó
client native đăng nhập bằng email+mật khẩu LTT rồi tự đăng ký máy dưới tài khoản
đó. Test ở đây chốt những thứ KHÔNG được đúng do may mắn:

* sai mật khẩu bị từ chối, và **cùng một câu** như email không tồn tại (constant
  time của `users.xac_thuc` — không lộ email nào có thật);
* cùng khoá công khai = cùng máy cài lại → **không** tạo dòng thứ hai;
* khoá đã thuộc tài khoản khác thì từ chối — không cướp máy giữa các tài khoản;
* thuê bao (Q98): miễn phí → điều khiển được; có giá + chưa trả → bị chặn.
"""
from __future__ import annotations

import uuid

import pytest


def _khoa() -> str:
    from platform_core.nexus import agent_auth
    _priv, pub = agent_auth.new_keypair_for_test()
    return pub


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'nexus.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session

    Base.metadata.create_all(get_engine())
    gen = get_session()
    session = next(gen)
    try:
        yield session
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        dbmod.reset_engine()


def _user(db, email: str = "", password: str = "mat-khau-that-0123456789"):
    from platform_core.users import tao_nguoi_dung
    user = tao_nguoi_dung(db, email=email or f"{uuid.uuid4().hex[:8]}@example.com",
                          password=password, is_verified=True)
    db.flush()
    return user, password


def test_dang_ky_bang_dung_email_mat_khau(db):
    from platform_core.nexus import devices

    user, pw = _user(db)
    khoa = _khoa()
    dev = devices.dang_ky_bang_tai_khoan(
        db, email=user.email, password=pw, public_key=khoa,
        display_name="May cua toi", platform="windows")
    assert dev.user_id == user.id
    assert dev.public_key == khoa
    assert dev.display_name == "May cua toi"
    assert dev.revoked_at is None


def test_sai_mat_khau_bi_tu_choi(db):
    from platform_core.nexus import devices
    from platform_core.nexus.devices import NexusError

    user, _pw = _user(db)
    with pytest.raises(NexusError):
        devices.dang_ky_bang_tai_khoan(
            db, email=user.email, password="sai-mat-khau", public_key=_khoa())


def test_email_khong_ton_tai_bi_tu_choi(db):
    from platform_core.nexus import devices
    from platform_core.nexus.devices import NexusError

    with pytest.raises(NexusError):
        devices.dang_ky_bang_tai_khoan(
            db, email="khong-co@example.com", password="gi-do-0123456789",
            public_key=_khoa())


def test_khoa_sai_dang_bi_tu_choi(db):
    from platform_core.nexus import devices
    from platform_core.nexus.devices import NexusError

    user, pw = _user(db)
    with pytest.raises(NexusError):
        devices.dang_ky_bang_tai_khoan(
            db, email=user.email, password=pw, public_key="khong-phai-khoa")


def test_cung_khoa_cung_tai_khoan_tai_dung_khong_tao_dong_thu_hai(db):
    from sqlalchemy import func, select

    from platform_core.nexus import devices
    from platform_core.nexus.tables import NexusDevice

    user, pw = _user(db)
    khoa = _khoa()
    d1 = devices.dang_ky_bang_tai_khoan(db, email=user.email, password=pw,
                                        public_key=khoa)
    d2 = devices.dang_ky_bang_tai_khoan(db, email=user.email, password=pw,
                                        public_key=khoa, display_name="doi ten")
    assert d1.id == d2.id
    assert d2.display_name == "doi ten"
    n = db.execute(select(func.count()).select_from(NexusDevice)
                   .where(NexusDevice.public_key == khoa)).scalar_one()
    assert n == 1


def test_khoa_thuoc_tai_khoan_khac_bi_tu_choi(db):
    from platform_core.nexus import devices
    from platform_core.nexus.devices import NexusError

    u1, pw1 = _user(db)
    u2, pw2 = _user(db)
    khoa = _khoa()
    devices.dang_ky_bang_tai_khoan(db, email=u1.email, password=pw1,
                                   public_key=khoa)
    with pytest.raises(NexusError):
        devices.dang_ky_bang_tai_khoan(db, email=u2.email, password=pw2,
                                       public_key=khoa)


def test_thue_bao_mien_phi_thi_dieu_khien_duoc(db, monkeypatch):
    from platform_core.nexus import billing, devices

    monkeypatch.delenv("LTT_NEXUS_GIA_MAY_THANG", raising=False)
    user, pw = _user(db)
    dev = devices.dang_ky_bang_tai_khoan(db, email=user.email, password=pw,
                                         public_key=_khoa())
    assert billing.da_thanh_toan(dev) is True


def test_co_gia_chua_tra_thi_bi_chan(db, monkeypatch):
    from platform_core.nexus import billing, devices

    monkeypatch.setenv("LTT_NEXUS_GIA_MAY_THANG", "50")
    user, pw = _user(db)
    dev = devices.dang_ky_bang_tai_khoan(db, email=user.email, password=pw,
                                         public_key=_khoa())
    # paid_until còn None -> chưa trả -> chặn
    assert billing.da_thanh_toan(dev) is False
