"""Nexus Model B (Q101 / D-P7) — bề mặt HTTP cho client native.

Client đăng nhập bằng tài khoản LTT (email+mật khẩu) qua `/nexus-agent/client-
register` rồi hỏi trạng thái thuê bao qua `/nexus-agent/status` (có ký). Test ở
đây chốt: đăng nhập sai không nói vì sao, có trần theo IP (chống dò mật khẩu),
và `status` phải ký được — không ký thì 401.
"""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

PASSWORD = "mat-khau-client-that-0123456789"


@pytest.fixture()
def app_bat(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'client.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "client-secret-value")
    monkeypatch.setenv("LTT_NEXUS", "1")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    monkeypatch.delenv("LTT_NEXUS_GIA_MAY_THANG", raising=False)

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


def _tao_user(email: str = "client@example.com"):
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung

    gen = get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email=email, password=PASSWORD, is_verified=True)
        db.commit()
        return u.id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _dang_ky(client, email: str = "client@example.com"):
    """Đăng ký một máy bằng tài khoản. Trả `(device_id, private_bytes)`."""
    from platform_core.nexus import agent_auth

    priv, pub = agent_auth.new_keypair_for_test()
    r = client.post("/nexus-agent/client-register",
                    json={"email": email, "password": PASSWORD,
                          "public_key": pub, "display_name": "May cua toi",
                          "platform": "windows"})
    assert r.status_code == 200, r.text
    return r.json()["device_id"], priv


def _ky(priv, method: str, path: str, body: bytes):
    from platform_core.nexus import agent_auth

    ts = str(int(time.time()))
    sig = agent_auth.sign(priv, method=method, path=path, timestamp=ts, body=body)
    return {agent_auth.HEADER_TIMESTAMP: ts, agent_auth.HEADER_SIGNATURE: sig}


# ── Đăng ký bằng tài khoản ───────────────────────────────────────────────────

def test_dang_ky_bang_tai_khoan_qua_HTTP(app_bat):
    _tao_user()
    device_id, _priv = _dang_ky(app_bat)
    assert device_id


def test_sai_mat_khau_thi_400_va_khong_noi_vi_sao(app_bat):
    from platform_core.nexus import agent_auth

    _tao_user()
    _priv, pub = agent_auth.new_keypair_for_test()
    r = app_bat.post("/nexus-agent/client-register",
                     json={"email": "client@example.com", "password": "sai",
                           "public_key": pub})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "register_failed"


def test_tran_dang_nhap_theo_IP(app_bat):
    """Điểm nhận mật khẩu phải chống dò: quá trần → 429."""
    from platform_core.nexus import agent_auth
    from server.nexus import routes

    _priv, pub = agent_auth.new_keypair_for_test()
    ma_429 = 0
    for _ in range(routes.DANG_NHAP_MOI_PHUT + 3):
        r = app_bat.post("/nexus-agent/client-register",
                         json={"email": "x@example.com", "password": "sai",
                               "public_key": pub})
        if r.status_code == 429:
            ma_429 += 1
    assert ma_429 >= 1, "khong co tran cho /client-register"


def test_tat_co_thi_404(app_bat, monkeypatch):
    monkeypatch.setenv("LTT_NEXUS", "0")
    r = app_bat.post("/nexus-agent/client-register",
                     json={"email": "x@example.com", "password": "y",
                           "public_key": "z"})
    assert r.status_code == 404


# ── Trạng thái thuê bao (có ký) ──────────────────────────────────────────────

def test_status_co_ky_mien_phi_thi_paid_true(app_bat):
    from platform_core.nexus import agent_auth

    _tao_user()
    device_id, priv = _dang_ky(app_bat)
    path = "/nexus-agent/status"
    headers = {agent_auth.HEADER_DEVICE: device_id, **_ky(priv, "POST", path, b"")}
    r = app_bat.post(path, content=b"", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["paid"] is True          # giá 0 (miễn phí)
    assert body["price_per_month"] == 0
    assert "credit_balance" in body


def test_status_khong_ky_thi_401(app_bat):
    _tao_user()
    _dang_ky(app_bat)
    r = app_bat.post("/nexus-agent/status", content=b"")
    assert r.status_code == 401


def test_status_co_gia_chua_tra_thi_paid_false(app_bat, monkeypatch):
    from platform_core.nexus import agent_auth

    _tao_user()
    device_id, priv = _dang_ky(app_bat)
    monkeypatch.setenv("LTT_NEXUS_GIA_MAY_THANG", "50")
    path = "/nexus-agent/status"
    headers = {agent_auth.HEADER_DEVICE: device_id, **_ky(priv, "POST", path, b"")}
    r = app_bat.post(path, content=b"", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["paid"] is False
    assert r.json()["price_per_month"] == 50
