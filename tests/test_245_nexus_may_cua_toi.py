"""Trang "Máy của tôi" — người dùng tự xem/đổi tên/thu hồi máy Nexus của mình.

Model B (Q101): web KHÔNG điều khiển máy, nhưng phải cắt được quyền truy cập khi
mất máy. Test chốt ba điều: chỉ thấy máy CỦA MÌNH, thu hồi có tác dụng thật, và
mọi hành động đổi trạng thái đều đòi CSRF.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

PASSWORD = "test-mat-khau-may-0123456789"


@pytest.fixture()
def app_bat(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'may.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "may-secret-value")
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


def _tao_user(email: str):
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


def _dang_nhap(client, email: str):
    import re

    client.post("/logout", follow_redirects=False)
    tok = re.search(r'name="csrf_token" value="([^"]+)"',
                    client.get("/login").text).group(1)
    r = client.post("/login", data={"username": email, "password": PASSWORD,
                                    "csrf_token": tok},
                    follow_redirects=False)
    assert r.status_code in (302, 303), r.text


def _dang_ky_may(client, email: str, ten: str = "May A"):
    from platform_core.nexus import agent_auth

    priv, pub = agent_auth.new_keypair_for_test()
    r = client.post("/nexus-agent/client-register",
                    json={"email": email, "password": PASSWORD,
                          "public_key": pub, "display_name": ten,
                          "platform": "windows"})
    assert r.status_code == 200, r.text
    return r.json()["device_id"], priv


def _csrf(html: str) -> str:
    import re
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    assert m, "khong thay csrf token trong trang"
    return m.group(1)


# ── Xem ──────────────────────────────────────────────────────────────────────

def test_trang_hien_may_cua_minh(app_bat):
    _tao_user("a@example.com")
    _dang_ky_may(app_bat, "a@example.com", "May lam viec")
    _dang_nhap(app_bat, "a@example.com")
    r = app_bat.get("/may-cua-toi")
    assert r.status_code == 200, r.text
    assert "May lam viec" in r.text


def test_chua_co_may_thi_moi_tai_xuong(app_bat):
    _tao_user("a@example.com")
    _dang_nhap(app_bat, "a@example.com")
    r = app_bat.get("/may-cua-toi")
    assert r.status_code == 200
    assert "/tai-xuong" in r.text          # trạng thái rỗng dẫn đi tải app


def test_khong_thay_may_cua_tai_khoan_khac(app_bat):
    """Bảo mật: máy người khác không được lộ."""
    _tao_user("a@example.com")
    _tao_user("b@example.com")
    _dang_ky_may(app_bat, "b@example.com", "May cua B")
    _dang_nhap(app_bat, "a@example.com")
    r = app_bat.get("/may-cua-toi")
    assert r.status_code == 200
    assert "May cua B" not in r.text


def test_chua_dang_nhap_thi_ve_login(app_bat):
    r = app_bat.get("/may-cua-toi", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "/login" in r.headers.get("location", "")


def test_tat_co_thi_404(app_bat, monkeypatch):
    _tao_user("a@example.com")
    _dang_nhap(app_bat, "a@example.com")
    monkeypatch.setenv("LTT_NEXUS", "0")
    r = app_bat.get("/may-cua-toi")
    assert r.status_code == 404


# ── Đổi tên ──────────────────────────────────────────────────────────────────

def test_doi_ten_may(app_bat):
    _tao_user("a@example.com")
    did, _ = _dang_ky_may(app_bat, "a@example.com", "Ten cu")
    _dang_nhap(app_bat, "a@example.com")
    token = _csrf(app_bat.get("/may-cua-toi").text)
    r = app_bat.post(f"/may-cua-toi/{did}/doi-ten",
                     data={"ten": "Ten moi", "csrf_token": token},
                     follow_redirects=False)
    assert r.status_code == 303
    assert "Ten moi" in app_bat.get("/may-cua-toi").text


def test_doi_ten_khong_csrf_thi_khong_doi(app_bat):
    _tao_user("a@example.com")
    did, _ = _dang_ky_may(app_bat, "a@example.com", "Ten cu")
    _dang_nhap(app_bat, "a@example.com")
    r = app_bat.post(f"/may-cua-toi/{did}/doi-ten",
                     data={"ten": "Bi doi", "csrf_token": "sai"},
                     follow_redirects=False)
    assert r.status_code == 303
    assert "loi=csrf" in r.headers.get("location", "")
    assert "Bi doi" not in app_bat.get("/may-cua-toi").text


# ── Thu hồi ──────────────────────────────────────────────────────────────────

def test_thu_hoi_may_thi_may_do_het_dung_duoc(app_bat):
    """Thu hồi phải cắt thật: request đã ký của máy đó bị từ chối sau đó."""
    import time

    from platform_core.nexus import agent_auth

    _tao_user("a@example.com")
    did, priv = _dang_ky_may(app_bat, "a@example.com", "May mat")

    # trước khi thu hồi: máy dùng được
    path = "/nexus-agent/status"
    ts = str(int(time.time()))
    sig = agent_auth.sign(priv, method="POST", path=path, timestamp=ts, body=b"")
    truoc = app_bat.post(path, content=b"", headers={
        agent_auth.HEADER_DEVICE: did, agent_auth.HEADER_TIMESTAMP: ts,
        agent_auth.HEADER_SIGNATURE: sig})
    assert truoc.status_code == 200, truoc.text

    _dang_nhap(app_bat, "a@example.com")
    token = _csrf(app_bat.get("/may-cua-toi").text)
    r = app_bat.post(f"/may-cua-toi/{did}/thu-hoi",
                     data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 303
    assert "ok=thu-hoi" in r.headers.get("location", "")

    # sau khi thu hồi: chính máy đó không còn được chấp nhận
    ts2 = str(int(time.time()))
    sig2 = agent_auth.sign(priv, method="POST", path=path, timestamp=ts2, body=b"")
    sau = app_bat.post(path, content=b"", headers={
        agent_auth.HEADER_DEVICE: did, agent_auth.HEADER_TIMESTAMP: ts2,
        agent_auth.HEADER_SIGNATURE: sig2})
    assert sau.status_code == 401, "thu hoi ma may van dung duoc"


def test_khong_thu_hoi_duoc_may_nguoi_khac(app_bat):
    _tao_user("a@example.com")
    _tao_user("b@example.com")
    did_b, _ = _dang_ky_may(app_bat, "b@example.com", "May cua B")
    _dang_nhap(app_bat, "a@example.com")
    token = _csrf(app_bat.get("/may-cua-toi").text)
    r = app_bat.post(f"/may-cua-toi/{did_b}/thu-hoi",
                     data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 303
    assert "loi=khong-thay" in r.headers.get("location", "")
