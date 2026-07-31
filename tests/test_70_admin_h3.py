"""
H3-admin — credit dùng thử sau xác thực + phân quyền trang quản trị /admin.

Chạy trên SQLite tạm (không cần PostgreSQL). Khoá ba tính chất:
- credit dùng thử cấp ĐÚNG MỘT LẦN sau lần xác thực email đầu tiên (idempotent
  theo chuyển trạng thái — bấm lại link không cấp thêm);
- `/admin` đá ẩn danh về /login (AuthenticationBackend của sqladmin);
- chỉ user role=admin vào được /admin; user thường bị chặn.
"""
from __future__ import annotations

import re

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    url = f"sqlite:///{(tmp_path / 'admin.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-secret-h3admin")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("LTT_TRIAL_CREDIT", "20")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.mailer import ConsoleMailer, set_mailer
    mailer = ConsoleMailer()
    set_mailer(mailer)

    from server.app import create_app
    c = TestClient(create_app(), base_url="https://testserver")
    c._mailer = mailer
    try:
        yield c
    finally:
        dbmod.reset_engine()
        set_mailer(None)


def _csrf(client, path):
    m = re.search(r'name="csrf_token" value="([^"]+)"', client.get(path).text)
    assert m, f"khong tim thay csrf o {path}"
    return m.group(1)


def _so_du_email(email: str) -> int:
    import platform_core.db as dbmod
    from platform_core.credit import so_du
    from platform_core.users import tim_theo_email
    gen = dbmod.get_session(); db = next(gen)
    try:
        u = tim_theo_email(db, email)
        return so_du(db, u.id) if u else -1
    finally:
        try: next(gen)
        except StopIteration: pass


def _dang_ky_va_lay_link(client, email):
    tok = _csrf(client, "/register")
    client.post("/register", data={"email": email, "password": "matkhau-tot",
                                    "csrf_token": tok}, follow_redirects=False)
    for e in client._mailer.sent:
        m = re.search(r'href="([^"]+)"', e.html)
        if m and "/verify-email" in m.group(1):
            return m.group(1).split("testserver", 1)[1]
    raise AssertionError("khong thay link xac thuc")


# ── Credit dùng thử ───────────────────────────────────────────────────────────

def test_credit_dung_thu_cap_mot_lan(client):
    email = "trial@example.com"
    path = _dang_ky_va_lay_link(client, email)
    assert _so_du_email(email) == 0          # chưa xác thực → chưa có credit

    r = client.get(path)                     # xác thực lần đầu
    assert r.status_code == 200
    assert _so_du_email(email) == 20         # được cấp credit dùng thử

    client.get(path)                         # bấm lại link (đã verified)
    assert _so_du_email(email) == 20         # KHÔNG cấp lại (idempotent)


# ── Phân quyền /admin ─────────────────────────────────────────────────────────

def test_admin_da_an_danh_ve_login(client):
    r = client.get("/admin/", follow_redirects=False)
    assert r.status_code in (302, 303, 307)
    assert "/login" in r.headers.get("location", "")


def test_admin_chi_cho_role_admin(client):
    import platform_core.db as dbmod
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email="sep@example.com", password="matkhau-tot-12",
                       role="admin", is_verified=True)
        tao_nguoi_dung(db, email="thuong@example.com", password="matkhau-tot-12",
                       role="user", is_verified=True)
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    def _login(email):
        tok = _csrf(client, "/login")
        return client.post("/login", data={"username": email,
                                            "password": "matkhau-tot-12",
                                            "csrf_token": tok},
                           follow_redirects=False)

    # User thường: đăng nhập được nhưng /admin bị đá về /login.
    assert _login("thuong@example.com").status_code == 303
    r = client.get("/admin/", follow_redirects=False)
    assert "/login" in r.headers.get("location", ""), "user thuong khong duoc vao /admin"
    _lt = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/").text).group(1)
    client.post("/logout", data={"csrf_token": _lt}, follow_redirects=False)

    # Admin: vào /admin được (200).
    assert _login("sep@example.com").status_code == 303
    r = client.get("/admin/", follow_redirects=False)
    assert r.status_code == 200, f"admin phai vao duoc /admin, nhan {r.status_code}"


def test_admin_session_khong_lo_token(client):
    """P0-5: SessionAdmin KHÔNG được render token phiên thô. Token phiên = PK
    của bảng Session (users.py:tao_phien); admin xem trang Phiên mà thấy token
    là lấy được phiên sống → mạo danh không cần mật khẩu."""
    import platform_core.db as dbmod
    from platform_core.users import tao_nguoi_dung, tao_phien
    gen = dbmod.get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email="sep3@example.com", password="matkhau-tot-12",
                       role="admin", is_verified=True)
        victim = tao_nguoi_dung(db, email="nan@example.com",
                                password="matkhau-tot-12", is_verified=True)
        db.commit()
        sid = tao_phien(db, victim)          # token phiên của "nạn nhân"
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    tok = _csrf(client, "/login")
    client.post("/login", data={"username": "sep3@example.com",
                                "password": "matkhau-tot-12", "csrf_token": tok},
                follow_redirects=False)
    r = client.get("/admin/session/list")
    assert r.status_code == 200
    assert sid not in r.text, "token phien bi render tren trang admin (P0-5)!"


def _login_admin(client, email):
    import platform_core.db as dbmod
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email=email, password="matkhau-tot-12",
                       role="admin", is_verified=True); db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass
    tok = _csrf(client, "/login")
    client.post("/login", data={"username": email, "password": "matkhau-tot-12",
                                "csrf_token": tok}, follow_redirects=False)


def test_apikey_admin_khong_lo_credential(client):
    """H8.4: trang APIKEYS liệt kê key KHÔNG được lộ credential thô — chỉ preview."""
    import platform_core.db as dbmod
    from platform_core import api_keys
    gen = dbmod.get_session(); db = next(gen)
    try:
        api_keys.tao_key(db, provider="gemini", credential="AIzaSECRETXYZ7777",
                         name="g", categories=["image"]); db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass
    _login_admin(client, "boss5@example.com")
    r = client.get("/admin/api-key/list")
    assert r.status_code == 200
    assert "AIzaSECRETXYZ7777" not in r.text      # KHÔNG lộ secret thô
    assert "...7777" in r.text                     # chỉ preview


def test_them_api_key_qua_view_ma_hoa(client):
    """H8.4: Add view tạo key với credential ĐÃ mã hoá (không lưu thô)."""
    import re as _re
    _login_admin(client, "boss6@example.com")
    page = client.get("/admin/api-key-them")
    assert page.status_code == 200
    ctok = _re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    r = client.post("/admin/api-key-them", data={
        "csrf_token": ctok, "provider": "gemini", "name": "test",
        "credential": "AIzaNEWSECRET8888", "categories": "image",
        "priority": "100"}, follow_redirects=False)
    assert r.status_code == 200 and "Đã thêm" in r.text

    import platform_core.db as dbmod
    from platform_core import api_keys
    from platform_core.models import ApiKey
    from sqlalchemy import select
    gen = dbmod.get_session(); db = next(gen)
    try:
        k = db.execute(select(ApiKey).where(ApiKey.name == "test")).scalars().first()
        assert k is not None
        assert "AIzaNEWSECRET8888" not in k.credential_enc      # đã mã hoá
        assert api_keys.lay_credential(db, k) == "AIzaNEWSECRET8888"
    finally:
        try: next(gen)
        except StopIteration: pass


def test_grant_credit_can_csrf(client):
    """W1.3: cấp credit tay (mutation sổ tiền) PHẢI có CSRF token hợp lệ."""
    import re as _re
    import platform_core.db as dbmod
    from platform_core.users import tao_nguoi_dung

    gen = dbmod.get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email="boss4@example.com", password="matkhau-tot-12",
                       role="admin", is_verified=True)
        victim = tao_nguoi_dung(db, email="kh4@example.com",
                                password="matkhau-tot-12", is_verified=True)
        db.commit(); uid = victim.id
    finally:
        try: next(gen)
        except StopIteration: pass

    tok = _csrf(client, "/login")
    client.post("/login", data={"username": "boss4@example.com",
                                "password": "matkhau-tot-12", "csrf_token": tok},
                follow_redirects=False)

    # POST KHÔNG csrf → 400, KHÔNG cấp credit.
    r = client.post("/admin/grant-credit",
                    data={"user_id": uid, "amount": "100"}, follow_redirects=False)
    assert r.status_code == 400
    assert _so_du_email("kh4@example.com") == 0

    # GET lấy csrf hợp lệ → POST cấp được.
    page = client.get("/admin/grant-credit").text
    ctok = _re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    r2 = client.post("/admin/grant-credit",
                     data={"user_id": uid, "amount": "100", "csrf_token": ctok},
                     follow_redirects=False)
    assert r2.status_code == 200
    assert _so_du_email("kh4@example.com") == 100
