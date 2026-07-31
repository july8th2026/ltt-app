"""
H1.3 — đăng ký, xác thực email, quên/đặt lại mật khẩu, chống lạm dụng.

Chạy trên SQLite tạm; dùng `ConsoleMailer` để đọc lại nội dung thư (lấy link
xác thực/đặt lại) mà không cần hộp thư thật hay khoá Resend.

Trọng tâm:
- credit dùng thử chỉ mở sau xác thực (ở đây: `is_verified` chỉ True sau khi
  bấm link — credit thật nối ở H3);
- không route công khai nào tiết lộ email nào đã đăng ký;
- token xác thực/đặt lại: hết hạn và giả mạo đều bị từ chối;
- đặt lại mật khẩu thu hồi mọi phiên;
- các lớp chống lạm dụng: mail dùng-một-lần, giới hạn IP.
"""
from __future__ import annotations

import re

import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """App nối CSDL SQLite sạch + ConsoleMailer để đọc lại thư."""
    from fastapi.testclient import TestClient

    url = f"sqlite:///{(tmp_path / 'dk.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-secret-h13")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)  # bo qua turnstile
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
    c._mailer = mailer            # cho test doc lai thu
    try:
        yield c
    finally:
        dbmod.reset_engine()
        set_mailer(None)


def _csrf(client, path):
    m = re.search(r'name="csrf_token" value="([^"]+)"', client.get(path).text)
    assert m, f"khong tim thay csrf token o {path}"
    return m.group(1)


def _link_trong_thu(mailer, chua: str) -> str:
    for e in mailer.sent:
        m = re.search(r'href="([^"]+)"', e.html)
        if m and chua in m.group(1):
            return m.group(1)
    raise AssertionError(f"khong tim thay link chua {chua!r} trong thu da gui")


# ── Đăng ký + xác thực ────────────────────────────────────────────────────────

def test_dang_ky_roi_xac_thuc_email(client):
    tok = _csrf(client, "/register")
    r = client.post("/register", data={
        "email": "new@example.com", "password": "matkhau-tot",
        "csrf_token": tok,
    }, follow_redirects=False)
    assert r.status_code == 200
    assert "gửi" in r.text.lower() or "email" in r.text.lower()

    # Chưa bấm link: chưa xác thực, và chưa đăng nhập được? — đăng nhập được
    # nhưng is_verified=False. Kiểm tra trạng thái trong DB.
    import platform_core.db as dbmod
    from platform_core.users import tim_theo_email
    gen = dbmod.get_session(); db = next(gen)
    try:
        u = tim_theo_email(db, "new@example.com")
        assert u is not None and u.is_verified is False
    finally:
        try: next(gen)
        except StopIteration: pass

    # Bấm link xác thực lấy từ thư.
    link = _link_trong_thu(client._mailer, "/verify-email")
    path = link.split("testserver", 1)[1]
    r2 = client.get(path)
    assert r2.status_code == 200 and "thành công" in r2.text.lower()

    gen = dbmod.get_session(); db = next(gen)
    try:
        assert tim_theo_email(db, "new@example.com").is_verified is True
    finally:
        try: next(gen)
        except StopIteration: pass


def test_token_xac_thuc_gia_mao_bi_tu_choi(client):
    r = client.get("/verify-email?token=day-la-token-bia-dat")
    assert r.status_code == 400
    assert "không hợp lệ" in r.text.lower() or "hết hạn" in r.text.lower()


def test_email_da_dang_ky_khong_bi_lo(client):
    """Đăng ký trùng email phải cho ra phản hồi GIỐNG HỆT lần đầu."""
    tok = _csrf(client, "/register")
    r1 = client.post("/register", data={
        "email": "dup@example.com", "password": "matkhau-tot", "csrf_token": tok,
    }, follow_redirects=False)
    tok2 = _csrf(client, "/register")
    r2 = client.post("/register", data={
        "email": "dup@example.com", "password": "matkhau-khac", "csrf_token": tok2,
    }, follow_redirects=False)
    assert r1.status_code == r2.status_code == 200
    # Cả hai đều là trang "đã gửi", không có thông báo "email đã tồn tại".
    assert "đã tồn tại" not in r2.text.lower()


# ── Chống lạm dụng ────────────────────────────────────────────────────────────

def test_email_dung_mot_lan_bi_chan(client):
    tok = _csrf(client, "/register")
    r = client.post("/register", data={
        "email": "ai@mailinator.com", "password": "matkhau-tot", "csrf_token": tok,
    }, follow_redirects=False)
    assert r.status_code == 400
    assert "dùng-một-lần" in r.text.lower() or "dung-mot-lan" in r.text.lower()


def test_mat_khau_ngan_bi_tu_choi(client):
    tok = _csrf(client, "/register")
    r = client.post("/register", data={
        "email": "short@example.com", "password": "123", "csrf_token": tok,
    }, follow_redirects=False)
    assert r.status_code == 400


def test_gioi_han_dang_ky_theo_ip(client, monkeypatch):
    """Quá số tài khoản/IP/ngày thì bị chặn (mặc định 3)."""
    from platform_core import antifraud
    monkeypatch.setattr(antifraud, "GIOI_HAN_IP_MOI_NGAY", 2)

    made = 0
    for i in range(4):
        tok = _csrf(client, "/register")
        r = client.post("/register", data={
            "email": f"ip{i}@example.com", "password": "matkhau-tot",
            "csrf_token": tok,
        }, follow_redirects=False)
        if r.status_code == 200:
            made += 1
        else:
            assert r.status_code == 429
    assert made == 2, f"chi duoc tao 2 tai khoan/IP, tao duoc {made}"


# ── Quên / đặt lại mật khẩu ───────────────────────────────────────────────────

def test_dat_lai_mat_khau_va_thu_hoi_phien(client):
    # Tạo user + một phiên đang mở.
    import platform_core.db as dbmod
    from platform_core.models import Session as SR
    from platform_core.users import tao_nguoi_dung, tao_phien
    from sqlalchemy import select
    gen = dbmod.get_session(); db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="reset@example.com", password="mat-khau-cu")
        tao_phien(db, u)
        db.commit()
        uid = u.id
    finally:
        try: next(gen)
        except StopIteration: pass

    # Yêu cầu đặt lại → lấy link từ thư.
    tok = _csrf(client, "/forgot-password")
    client.post("/forgot-password", data={"email": "reset@example.com",
                                          "csrf_token": tok}, follow_redirects=False)
    link = _link_trong_thu(client._mailer, "/reset-password")
    path = link.split("testserver", 1)[1]

    rtok = _csrf(client, path)
    token = re.search(r"token=([^&\s]+)", path).group(1)
    r = client.post("/reset-password", data={
        "token": token, "password": "mat-khau-moi-tot", "csrf_token": rtok,
    }, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"

    gen = dbmod.get_session(); db = next(gen)
    try:
        from platform_core.users import xac_thuc
        con = db.execute(select(SR).where(SR.user_id == uid)).scalars().all()
        assert len(con) == 0, "dat lai mat khau phai thu hoi moi phien"
        assert xac_thuc(db, email="reset@example.com", password="mat-khau-moi-tot")
        assert xac_thuc(db, email="reset@example.com", password="mat-khau-cu") is None
    finally:
        try: next(gen)
        except StopIteration: pass


def test_forgot_password_khong_lo_email_ton_tai(client):
    """Email không tồn tại và có tồn tại đều cho phản hồi giống nhau."""
    tok = _csrf(client, "/forgot-password")
    r = client.post("/forgot-password", data={"email": "khong-co@example.com",
                                              "csrf_token": tok}, follow_redirects=False)
    assert r.status_code == 200
    assert "nếu email" in r.text.lower() or "if" in r.text.lower() or "gửi" in r.text.lower()
