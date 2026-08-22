"""Đăng nhập một-chạm từ ứng dụng LTT Nexus sang trình duyệt (B3).

Vì sao có file này: bấm **Nạp credit** trong ứng dụng mở `/nap` rồi bắt đăng nhập
lại. Cùng một tài khoản, cùng một máy — người dùng đọc việc đó là "app và web là
hai hệ khác nhau".

Đường nối này nguy hiểm hơn vẻ ngoài của nó vì vé đi qua **thanh địa chỉ**, nên
test ở đây chốt cả phần *không được làm*: vé không dùng lại được, không sống lâu,
không nhận cookie phiên thay vé, và không chuyển hướng ra ngoài tên miền.
"""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

PASSWORD = "test-mat-khau-sso-0123456789"


@pytest.fixture()
def app_bat(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'sso.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "sso-secret-value")
    monkeypatch.setenv("LTT_NEXUS", "1")
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


def _tao_user(email: str = "s@example.com"):
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung

    gen = get_session(); db = next(gen)
    try:
        u = tao_nguoi_dung(db, email=email, password=PASSWORD, is_verified=True)
        db.commit()
        return u.id
    finally:
        try: next(gen)
        except StopIteration: pass


def _dang_ky_may(client, email: str = "s@example.com"):
    from platform_core.nexus import agent_auth

    priv, pub = agent_auth.new_keypair_for_test()
    r = client.post("/nexus-agent/client-register",
                    json={"email": email, "password": PASSWORD,
                          "public_key": pub, "display_name": "May",
                          "platform": "windows"})
    assert r.status_code == 200, r.text
    return r.json()["device_id"], priv


def _xin_ve(client, device_id, priv):
    from platform_core.nexus import agent_auth

    path = "/nexus-agent/web-login"
    ts = str(int(time.time()))
    sig = agent_auth.sign(priv, method="POST", path=path, timestamp=ts, body=b"")
    return client.post(path, content=b"", headers={
        agent_auth.HEADER_DEVICE: device_id,
        agent_auth.HEADER_TIMESTAMP: ts,
        agent_auth.HEADER_SIGNATURE: sig})


# ── Đường sáng ───────────────────────────────────────────────────────────────

def test_xin_ve_roi_doi_ve_thi_vao_duoc_trang_can_dang_nhap(app_bat):
    _tao_user()
    did, priv = _dang_ky_may(app_bat)

    r = _xin_ve(app_bat, did, priv)
    assert r.status_code == 200, r.text
    ve = r.json()["ticket"]
    assert r.json()["path"] == "/nexus-sso"

    r2 = app_bat.get(f"/nexus-sso?ma={ve}&next=/may-cua-toi",
                     follow_redirects=False)
    assert r2.status_code == 303
    assert r2.headers["location"] == "/may-cua-toi"
    # Phiên đã có thật: trang đòi đăng nhập nay mở được, không còn 303 về /login.
    assert app_bat.get("/may-cua-toi", follow_redirects=False).status_code == 200


def test_khong_co_next_thi_ve_trang_may_cua_toi(app_bat):
    _tao_user()
    did, priv = _dang_ky_may(app_bat)
    ve = _xin_ve(app_bat, did, priv).json()["ticket"]
    r = app_bat.get(f"/nexus-sso?ma={ve}", follow_redirects=False)
    assert r.headers["location"] == "/may-cua-toi"


def test_ve_khong_bi_cache(app_bat):
    """Vé nằm trong URL; phản hồi bị cache lại là một cách rò nó."""
    _tao_user()
    did, priv = _dang_ky_may(app_bat)
    ve = _xin_ve(app_bat, did, priv).json()["ticket"]
    r = app_bat.get(f"/nexus-sso?ma={ve}", follow_redirects=False)
    assert "no-store" in r.headers.get("cache-control", "")


# ── Đường tối ────────────────────────────────────────────────────────────────

def test_ve_chi_dung_duoc_MOT_lan(app_bat):
    """Vé nằm lại trong lịch sử trình duyệt — dùng lại được là một cửa sau."""
    _tao_user()
    did, priv = _dang_ky_may(app_bat)
    ve = _xin_ve(app_bat, did, priv).json()["ticket"]

    assert app_bat.get(f"/nexus-sso?ma={ve}",
                       follow_redirects=False).headers["location"] == "/may-cua-toi"
    app_bat.post("/logout", follow_redirects=False)

    r = app_bat.get(f"/nexus-sso?ma={ve}", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/login"), "ve dung lai duoc lan hai"


def test_ve_het_han_thi_khong_doi_duoc(app_bat, monkeypatch):
    import datetime

    from platform_core.db import get_session
    from platform_core.models import Session as SessionRow
    from platform_core.nexus import sso
    from platform_core.users import _bam_sid

    _tao_user()
    did, priv = _dang_ky_may(app_bat)
    ve = _xin_ve(app_bat, did, priv).json()["ticket"]

    gen = get_session(); db = next(gen)
    try:
        row = db.get(SessionRow, _bam_sid(ve))
        assert row is not None
        row.expires_at = (datetime.datetime.now(datetime.timezone.utc)
                          - datetime.timedelta(seconds=1))
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    r = app_bat.get(f"/nexus-sso?ma={ve}", follow_redirects=False)
    assert r.headers["location"].startswith("/login")
    assert sso.VE_TTL.total_seconds() <= 300, "ve song qua lau cho mot thu di qua URL"


def test_cookie_phien_thuong_KHONG_dung_thay_ve_duoc(app_bat):
    """Nếu nhận cả phiên thường thì đây thành 'đưa cookie qua URL cũng vào được'."""
    from platform_core.db import get_session
    from platform_core.models import User
    from platform_core.users import tao_phien

    uid = _tao_user()
    gen = get_session(); db = next(gen)
    try:
        sid_thuong = tao_phien(db, db.get(User, uid), user_agent="Mozilla/5.0")
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    r = app_bat.get(f"/nexus-sso?ma={sid_thuong}", follow_redirects=False)
    assert r.headers["location"].startswith("/login")


def test_ve_bia_ra_thi_ve_login(app_bat):
    _tao_user()
    r = app_bat.get("/nexus-sso?ma=khong-phai-ve-that", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/login")


@pytest.mark.parametrize("xau", [
    "https://ke-xau.example/lua",
    "//ke-xau.example/lua",
    "http://ke-xau.example",
])
def test_next_ra_ngoai_ten_mien_bi_chan(app_bat, xau):
    """Open-redirect gắn sẵn phiên đăng nhập là món quà cho kẻ lừa đảo."""
    _tao_user()
    did, priv = _dang_ky_may(app_bat)
    ve = _xin_ve(app_bat, did, priv).json()["ticket"]
    r = app_bat.get(f"/nexus-sso?ma={ve}&next={xau}", follow_redirects=False)
    assert not r.headers["location"].startswith("http"), r.headers["location"]
    assert "ke-xau.example" not in r.headers["location"]


def test_xin_ve_phai_co_chu_ky(app_bat):
    _tao_user()
    did, _ = _dang_ky_may(app_bat)
    r = app_bat.post("/nexus-agent/web-login", content=b"", headers={
        "X-LTT-Device": did, "X-LTT-Timestamp": str(int(time.time())),
        "X-LTT-Signature": "chu-ky-bia"})
    assert r.status_code == 401


def test_tat_nexus_thi_ca_hai_dau_deu_404(tmp_path, monkeypatch):
    import platform_core.db as dbmod
    from platform_core.public_api import limits

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'off.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "sso-secret-value")
    monkeypatch.setenv("LTT_NEXUS", "0")
    limits.reset()
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from server.app import create_app

    client = TestClient(create_app(), base_url="https://testserver")
    try:
        assert client.get("/nexus-sso?ma=x",
                          follow_redirects=False).status_code == 404
        assert client.post("/nexus-agent/web-login",
                           content=b"").status_code == 404
    finally:
        limits.reset()
        dbmod.reset_engine()
