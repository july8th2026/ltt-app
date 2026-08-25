"""
H1.4 — phân quyền app cho từng người dùng.

Trọng tâm: chặn ở **tầng route**, không chỉ ẩn nút. Test quan trọng nhất là gõ
thẳng URL của một app bị ẩn/khoá và xác nhận bị chặn — vì "ẩn khỏi trang chủ
nhưng vẫn gọi được URL" là lỗ hổng chứ không phải phân quyền.

Chạy trên SQLite tạm. Dùng app khách hàng `agent` làm đối tượng; `qualitylab` có
surface admin và được kiểm riêng để không biến app vận hành thành UI khách.
"""
from __future__ import annotations

import re

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'q.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); s = next(gen)
    try:
        yield s
    finally:
        s.close(); dbmod.reset_engine()


# ── Nghiệp vụ ─────────────────────────────────────────────────────────────────

def test_mac_dinh_la_mo(db):
    from platform_core.app_access import ENABLED, muc_quyen
    from platform_core.users import tao_nguoi_dung
    u = tao_nguoi_dung(db, email="a@x.com", password="pw12345678")
    db.commit()
    assert muc_quyen(db, u, "bat-ky-app-nao") == ENABLED


def test_admin_luon_mo_du_co_dong_khoa(db):
    from platform_core.app_access import ENABLED, dat_quyen, muc_quyen
    from platform_core.users import tao_nguoi_dung
    admin = tao_nguoi_dung(db, email="ad@x.com", password="pw12345678", role="admin")
    db.commit()
    # Kể cả khi có dòng khoá, admin vẫn mở.
    dat_quyen(db, admin.id, "qualitylab", "hidden")
    db.commit()
    assert muc_quyen(db, admin, "qualitylab") == ENABLED


def test_dat_quyen_va_ve_mac_dinh_thi_xoa_dong(db):
    from platform_core.app_access import HIDDEN, dat_quyen, muc_quyen
    from platform_core.models import AppAccess
    from platform_core.users import tao_nguoi_dung
    from sqlalchemy import select

    u = tao_nguoi_dung(db, email="b@x.com", password="pw12345678")
    db.commit()

    dat_quyen(db, u.id, "qualitylab", HIDDEN)
    db.commit()
    assert muc_quyen(db, u, "qualitylab") == HIDDEN
    assert db.execute(select(AppAccess)).scalars().all(), "phai co dong khi khac mac dinh"

    dat_quyen(db, u.id, "qualitylab", "enabled")  # ve mac dinh
    db.commit()
    assert db.execute(select(AppAccess)).scalars().all() == [], \
        "ve mac dinh phai XOA dong, khong luu"


def test_dat_quyen_gia_tri_sai_bi_tu_choi(db):
    from platform_core.app_access import dat_quyen
    from platform_core.users import tao_nguoi_dung
    u = tao_nguoi_dung(db, email="c@x.com", password="pw12345678")
    db.commit()
    with pytest.raises(ValueError):
        dat_quyen(db, u.id, "qualitylab", "superuser")


# ── Ánh xạ path → app ─────────────────────────────────────────────────────────

def test_app_cho_path_khop_prefix_dai_nhat():
    from platform_core.app_access import app_cho_path
    from platform_core.registry import discover
    loaded = discover()

    assert app_cho_path("/agent", loaded) == "agent"
    assert app_cho_path("/agent/canvas", loaded) == "agent"
    # Một app khai nav NGOÀI `route_prefix` của nó vẫn phải khớp đúng chủ.
    # Ví dụ cũ ở đây là socialbot (`/sheet/facebook`, `/manual/tiktok`), gỡ
    # 2026-08-25; `thumbnail` giữ nguyên vai trò đó vì nó là app con của
    # `taoanh` (`catalog_parent`) nhưng vẫn có prefix riêng.
    assert app_cho_path("/thumbnail", loaded) == "thumbnail"
    assert app_cho_path("/thumbnail/lich-su", loaded) == "thumbnail"
    # Đường không thuộc app nào.
    assert app_cho_path("/login", loaded) is None
    assert app_cho_path("/", loaded) is None
    assert app_cho_path("/health/ready", loaded) is None


# ── Chặn qua HTTP (điểm cốt lõi) ──────────────────────────────────────────────

@pytest.fixture()
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    url = f"sqlite:///{(tmp_path / 'web.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-h14")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); s = next(gen)
    u = tao_nguoi_dung(s, email="user@x.com", password="matkhau-tot", is_verified=True)
    s.commit()
    uid = u.id
    s.close()

    from server.app import create_app
    c = TestClient(create_app(), base_url="https://testserver")
    c._uid = uid
    try:
        yield c
    finally:
        dbmod.reset_engine()


def _dang_nhap(client):
    html = client.get("/login").text
    tok = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    r = client.post("/login", data={"username": "user@x.com",
                                    "password": "matkhau-tot", "csrf_token": tok},
                    follow_redirects=False)
    assert r.status_code == 303


def _dat_quyen_db(level):
    import platform_core.db as dbmod
    from platform_core.app_access import dat_quyen
    gen = dbmod.get_session(); s = next(gen)
    try:
        from sqlalchemy import select
        from platform_core.models import User
        uid = s.execute(select(User.id).where(User.email == "user@x.com")).scalar_one()
        dat_quyen(s, uid, "agent", level)
        s.commit()
    finally:
        try: next(gen)
        except StopIteration: pass


def test_app_mo_thi_vao_duoc(client):
    _dang_nhap(client)
    r = client.get("/agent/canvas", follow_redirects=False)
    assert r.status_code == 200


def test_app_an_thi_go_url_thang_bi_404(client):
    """Gõ thẳng URL app bị ẩn → 404, không phải vào được."""
    _dang_nhap(client)
    _dat_quyen_db("hidden")
    r = client.get("/agent/canvas", follow_redirects=False)
    assert r.status_code == 404


def test_app_khoa_thi_go_url_thang_bi_403(client):
    _dang_nhap(client)
    _dat_quyen_db("locked")
    r = client.get("/agent/canvas", follow_redirects=False)
    assert r.status_code == 403


def test_app_an_bi_bo_khoi_trang_chu(client):
    _dang_nhap(client)
    assert "LTT Agent AI" in client.get("/").text, "khi mo thi phai hien tren trang chu"
    _dat_quyen_db("hidden")
    assert "LTT Agent AI" not in client.get("/").text, \
        "khi an thi phai bien khoi trang chu"


def test_app_surface_admin_tra_404_cho_customer(client):
    """App `surface="admin"` phải trả 404 cho khách thường, không phải 403.

    Trước 2026-08-25 dùng `demo`; app đó đã gỡ nên dùng `qualitylab` — cũng
    `surface="admin"` (Q83). Tính chất được chốt là của **hợp đồng surface**,
    không của một app.
    """
    _dang_nhap(client)
    assert client.get("/qualitylab", follow_redirects=False).status_code == 404


def test_an_danh_khong_bi_middleware_nuot_redirect(client):
    """Chưa đăng nhập vào một route app vẫn phải được require_login đưa về
    /login (303); middleware phân quyền không được nuốt mất redirect đó."""
    r = client.get("/qualitylab", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/login")
