"""Kích hoạt thuê bao TỨC THÌ — không bắt khách chờ vòng quét.

Vì sao có file này: vòng thu phí chạy **15 phút một lần**
(`job_runner.ALERT_SCAN_INTERVAL_S`). Máy vừa đăng ký có `paid_until` rỗng nên
`da_thanh_toan()` trả False và relay chặn — nghĩa là khách **đã có credit** vẫn
không kết nối được trong tối đa 15 phút đầu, đúng lúc họ thử sản phẩm lần đầu.

Test ở đây chốt ba điều: đăng ký là thu phí ngay, hỏi trạng thái cũng thu phí
ngay (nạp credit xong mở khoá trong vòng một phút), và một máy hỏng không được
giết cả lượt thu phí của những máy khác.
"""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

PASSWORD = "test-mat-khau-kichhoat-0123456789"


@pytest.fixture()
def app_bat(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'kh.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "kh-secret-value")
    monkeypatch.setenv("LTT_NEXUS", "1")
    monkeypatch.setenv("LTT_NEXUS_GIA_MAY_THANG", "50")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    from platform_core.public_api import limits
    limits.reset()

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from server.app import create_app

    client = TestClient(create_app(), base_url="https://testserver")
    try:
        yield client
    finally:
        limits.reset()
        dbmod.reset_engine()


def _tao_user(email: str = "k@example.com", credit_ban_dau: int = 0):
    from platform_core import credit as credit_mod
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung

    gen = get_session(); db = next(gen)
    try:
        u = tao_nguoi_dung(db, email=email, password=PASSWORD, is_verified=True)
        db.commit()
        if credit_ban_dau:
            credit_mod.cap_tay(db, u.id, credit_ban_dau, by="test", note="nap ban dau")
            db.commit()
        return u.id
    finally:
        try: next(gen)
        except StopIteration: pass


def _dang_ky(client, email: str = "k@example.com"):
    from platform_core.nexus import agent_auth

    priv, pub = agent_auth.new_keypair_for_test()
    r = client.post("/nexus-agent/client-register",
                    json={"email": email, "password": PASSWORD,
                          "public_key": pub, "display_name": "May",
                          "platform": "windows"})
    assert r.status_code == 200, r.text
    return r.json()["device_id"], priv


def _status(client, device_id, priv, body: bytes = b""):
    from platform_core.nexus import agent_auth

    path = "/nexus-agent/status"
    ts = str(int(time.time()))
    sig = agent_auth.sign(priv, method="POST", path=path, timestamp=ts, body=body)
    return client.post(path, content=body, headers={
        agent_auth.HEADER_DEVICE: device_id, agent_auth.HEADER_TIMESTAMP: ts,
        agent_auth.HEADER_SIGNATURE: sig, "Content-Type": "application/json"})


def _may(device_id):
    from platform_core.db import get_session
    from platform_core.nexus.devices import NexusDevice

    gen = get_session(); db = next(gen)
    try:
        d = db.get(NexusDevice, device_id)
        return (d.paid_until, d.user_id)
    finally:
        try: next(gen)
        except StopIteration: pass


# ── Kích hoạt ngay lúc đăng ký ───────────────────────────────────────────────

def test_dang_ky_co_credit_thi_dung_duoc_NGAY(app_bat):
    """Khách có credit: cài xong là dùng được, không chờ vòng quét 15 phút."""
    _tao_user(credit_ban_dau=500)
    did, priv = _dang_ky(app_bat)
    han, _ = _may(did)
    assert han is not None, "dang ky xong ma chua co han -> khach bi chan 15 phut"
    r = _status(app_bat, did, priv)
    assert r.json()["paid"] is True


def test_dang_ky_khong_co_credit_thi_chua_thanh_toan(app_bat):
    """Không đủ credit → không trừ, không đẩy hạn, không nợ."""
    _tao_user(credit_ban_dau=0)
    did, priv = _dang_ky(app_bat)
    han, _ = _may(did)
    assert han is None
    assert _status(app_bat, did, priv).json()["paid"] is False


def test_dang_ky_tru_dung_mot_lan(app_bat):
    from platform_core import credit as credit_mod
    from platform_core.db import get_session

    uid = _tao_user(credit_ban_dau=500)
    did, priv = _dang_ky(app_bat)
    gen = get_session(); db = next(gen)
    try:
        assert credit_mod.so_du(db, uid) == 450
    finally:
        try: next(gen)
        except StopIteration: pass
    # hỏi trạng thái nhiều lần KHÔNG được trừ thêm (còn hạn)
    for _ in range(3):
        _status(app_bat, did, priv)
    gen = get_session(); db = next(gen)
    try:
        assert credit_mod.so_du(db, uid) == 450, "bi tru nhieu lan trong mot ky"
    finally:
        try: next(gen)
        except StopIteration: pass


# ── Nạp credit xong mở khoá ngay ở lần hỏi trạng thái kế tiếp ────────────────

def test_nap_credit_xong_thi_status_mo_khoa_ngay(app_bat):
    """Đây là đường khách thoát khỏi trạng thái bị chặn — phải nhanh, không chờ."""
    from platform_core import credit as credit_mod
    from platform_core.db import get_session

    uid = _tao_user(credit_ban_dau=0)
    did, priv = _dang_ky(app_bat)
    assert _status(app_bat, did, priv).json()["paid"] is False

    gen = get_session(); db = next(gen)
    try:
        credit_mod.cap_tay(db, uid, 100, by="test", note="khach nap")
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    assert _status(app_bat, did, priv).json()["paid"] is True, \
        "nap credit roi ma van bi chan -> khach phai cho vong quet"


# ── Vòng quét: một máy hỏng không giết cả lượt ───────────────────────────────

def test_mot_may_hong_khong_giet_ca_luot_thu_phi(app_bat, monkeypatch):
    """Một dòng dữ liệu lạ không được làm CẢ nền tảng ngừng thu tiền."""
    from platform_core.db import get_session
    from platform_core.nexus import billing

    _tao_user("a@example.com", credit_ban_dau=500)
    _tao_user("b@example.com", credit_ban_dau=500)
    did_a, _ = _dang_ky(app_bat, "a@example.com")
    did_b, _ = _dang_ky(app_bat, "b@example.com")

    # ép cả hai về "tới kỳ"
    from platform_core.nexus.devices import NexusDevice
    gen = get_session(); db = next(gen)
    try:
        for d in (db.get(NexusDevice, did_a), db.get(NexusDevice, did_b)):
            d.paid_until = None
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    that_bai = {"n": 0}
    goc = billing.thu_phi_mot_may

    def hong_may_dau(db_, dev, **kw):
        if dev.id == did_a and that_bai["n"] == 0:
            that_bai["n"] += 1
            raise RuntimeError("dong du lieu la")
        return goc(db_, dev, **kw)

    monkeypatch.setattr(billing, "thu_phi_mot_may", hong_may_dau)
    gen = get_session(); db = next(gen)
    try:
        ket = billing.thu_phi_thang(db)
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    assert ket.get("loi", 0) >= 1, "khong ghi nhan may hong"
    assert ket["tru"] >= 1, "mot may hong da giet ca luot thu phi"


def test_mien_phi_thi_khong_dung_toi_credit(app_bat, monkeypatch):
    from platform_core import credit as credit_mod
    from platform_core.db import get_session

    monkeypatch.setenv("LTT_NEXUS_GIA_MAY_THANG", "0")
    uid = _tao_user(credit_ban_dau=100)
    did, priv = _dang_ky(app_bat)
    gen = get_session(); db = next(gen)
    try:
        assert credit_mod.so_du(db, uid) == 100
    finally:
        try: next(gen)
        except StopIteration: pass
    assert _status(app_bat, did, priv).json()["paid"] is True
