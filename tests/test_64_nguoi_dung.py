"""
H1.2 — người dùng, mật khẩu, phiên đăng nhập phía máy chủ.

Chạy trên SQLite tạm (mỗi test một file) để không bắt máy chạy test phải có
PostgreSQL. Logic trong `platform_core/users.py` là SQLAlchemy thuần và chỉ
dùng kiểu dữ liệu chạy được ở cả hai, nên vẫn kiểm chứng đúng hành vi.

Trọng tâm:
- mật khẩu không bao giờ lưu thô;
- xác thực sai không tiết lộ email nào đã đăng ký;
- phiên **thu hồi được** ở máy chủ (điểm khác biệt so với cookie ký thuần);
- đổi mật khẩu đá mọi phiên;
- đường đăng nhập CSDL và đường admin-env cùng chạy, không đá nhau.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Một CSDL SQLite sạch cho mỗi test, đã dựng đủ bảng."""
    url = f"sqlite:///{(tmp_path / 'h12.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    # KHONG reload models: Base.metadata song o platform_core.db (khong reload),
    # reload models se dinh nghia lai bang tren cung metadata -> xung dot. Chi
    # can import mot lan de bang duoc dang ky, roi create_all len engine moi.
    import platform_core.models as models  # noqa: F401

    engine = dbmod.get_engine()
    dbmod.Base.metadata.create_all(engine)

    gen = dbmod.get_session()
    session = next(gen)
    try:
        yield session
    finally:
        session.close()
        dbmod.reset_engine()


# ── Nghiệp vụ người dùng ──────────────────────────────────────────────────────

def test_tao_va_tim_nguoi_dung(db):
    from platform_core.users import tao_nguoi_dung, tim_theo_email

    u = tao_nguoi_dung(db, email="Bob@Example.com", password="matkhau123")
    db.commit()
    assert u.email == "bob@example.com", "email phai chuan hoa ve chu thuong"
    assert u.id and len(u.id) == 36, "id phai la UUID"
    assert u.is_verified is False, "moi tao thi chua xac thuc"

    assert tim_theo_email(db, "BOB@example.com") is not None, "tim phai khong phan biet hoa thuong"


def test_khong_luu_mat_khau_tho(db):
    from platform_core.users import tao_nguoi_dung

    u = tao_nguoi_dung(db, email="a@x.com", password="sieu-bi-mat-999")
    db.commit()
    assert "sieu-bi-mat-999" not in u.password_hash, "mat khau tho khong duoc nam trong hash"
    assert u.password_hash, "phai co hash"


def test_email_trung_bi_tu_choi(db):
    from platform_core.users import UserError, tao_nguoi_dung

    tao_nguoi_dung(db, email="dup@x.com", password="a")
    db.commit()
    with pytest.raises(UserError):
        tao_nguoi_dung(db, email="DUP@x.com", password="b")


def test_xac_thuc_dung_va_sai(db):
    from platform_core.users import tao_nguoi_dung, xac_thuc

    tao_nguoi_dung(db, email="c@x.com", password="dung-mat-khau")
    db.commit()

    assert xac_thuc(db, email="c@x.com", password="dung-mat-khau") is not None
    assert xac_thuc(db, email="c@x.com", password="sai") is None
    # Email khong ton tai va sai mat khau deu tra None — khong phan biet duoc.
    assert xac_thuc(db, email="khong-co@x.com", password="gi-do") is None


def test_tai_khoan_bi_khoa_khong_dang_nhap_duoc(db):
    from platform_core.users import tao_nguoi_dung, xac_thuc

    u = tao_nguoi_dung(db, email="d@x.com", password="pw")
    u.is_active = False
    db.commit()
    assert xac_thuc(db, email="d@x.com", password="pw") is None


# ── Phiên đăng nhập phía máy chủ ──────────────────────────────────────────────

def test_phien_tao_ra_tra_lai_dung_user(db):
    from platform_core.users import lay_user_tu_phien, tao_nguoi_dung, tao_phien

    u = tao_nguoi_dung(db, email="e@x.com", password="pw")
    sid = tao_phien(db, u)
    db.commit()

    lay = lay_user_tu_phien(db, sid)
    assert lay is not None and lay.email == "e@x.com"
    assert u.last_login_at is not None, "tao phien phai ghi last_login_at"


def test_phien_thu_hoi_duoc(db):
    """Điểm khác biệt cốt lõi so với cookie ký thuần: xoá được một phiên."""
    from platform_core.users import (lay_user_tu_phien, tao_nguoi_dung,
                                     tao_phien, thu_hoi_phien)

    u = tao_nguoi_dung(db, email="f@x.com", password="pw")
    sid = tao_phien(db, u)
    db.commit()
    assert lay_user_tu_phien(db, sid) is not None

    thu_hoi_phien(db, sid)
    db.commit()
    assert lay_user_tu_phien(db, sid) is None, "phien da thu hoi khong con dung duoc"


def test_doi_mat_khau_da_moi_phien(db):
    """Đổi mật khẩu phải đá mọi phiên đang mở — kẻ chiếm phiên mất quyền."""
    from platform_core.users import (doi_mat_khau, lay_user_tu_phien,
                                     tao_nguoi_dung, tao_phien)

    u = tao_nguoi_dung(db, email="g@x.com", password="cu")
    sid1 = tao_phien(db, u)
    sid2 = tao_phien(db, u)
    db.commit()
    assert lay_user_tu_phien(db, sid1) is not None
    assert lay_user_tu_phien(db, sid2) is not None

    doi_mat_khau(db, u, "moi")
    db.commit()
    assert lay_user_tu_phien(db, sid1) is None, "phien cu phai chet sau khi doi mat khau"
    assert lay_user_tu_phien(db, sid2) is None


def test_phien_het_han_bi_tu_choi_va_don(db):
    from datetime import timedelta

    from platform_core.users import (lay_user_tu_phien, tao_nguoi_dung,
                                     tao_phien)
    import platform_core.users as um

    u = tao_nguoi_dung(db, email="h@x.com", password="pw")
    sid = tao_phien(db, u)
    # Ep het han bang cach lui thoi diem tao ve qua khu xa hon TTL.
    from platform_core.models import Session as SessionRow
    row = db.get(SessionRow, sid)
    row.expires_at = um._bay_gio() - timedelta(seconds=1)
    db.commit()

    assert lay_user_tu_phien(db, sid) is None
    assert db.get(SessionRow, sid) is None, "phien het han phai bi don ngay"


# ── Luồng đăng nhập qua HTTP ──────────────────────────────────────────────────

@pytest.fixture()
def client_db(tmp_path, monkeypatch):
    """App web nối tới một CSDL SQLite sạch, có sẵn một user đã tạo."""
    from fastapi.testclient import TestClient

    url = f"sqlite:///{(tmp_path / 'web.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-secret-khong-bi-mat")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401  — dang ky bang vao Base.metadata
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session()
    s = next(gen)
    tao_nguoi_dung(s, email="user@x.com", password="matkhau-tot", is_verified=True)
    s.commit()
    s.close()

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver")
    try:
        yield client
    finally:
        dbmod.reset_engine()


def _csrf(client, path="/login") -> str:
    import re
    html = client.get(path).text
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert m, "khong tim thay csrf token trong form"
    return m.group(1)


def test_dang_nhap_bang_user_csdl(client_db):
    tok = _csrf(client_db)
    r = client_db.post("/login", data={
        "username": "user@x.com", "password": "matkhau-tot", "csrf_token": tok,
    }, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/"
    # Sau khi dang nhap, mo trang chu khong bi da ve /login.
    r2 = client_db.get("/", follow_redirects=False)
    assert r2.status_code == 200


def test_dang_nhap_sai_mat_khau_bi_tu_choi(client_db):
    tok = _csrf(client_db)
    r = client_db.post("/login", data={
        "username": "user@x.com", "password": "sai-roi", "csrf_token": tok,
    }, follow_redirects=False)
    assert r.status_code == 401


def test_dang_xuat_thu_hoi_phien(client_db):
    tok = _csrf(client_db)
    client_db.post("/login", data={
        "username": "user@x.com", "password": "matkhau-tot", "csrf_token": tok,
    }, follow_redirects=False)
    assert client_db.get("/", follow_redirects=False).status_code == 200

    client_db.post("/logout", follow_redirects=False)
    # Sau dang xuat, trang chu da ve /login.
    r = client_db.get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"
