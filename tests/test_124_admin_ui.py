"""ADM-001: operator surfaces share the Carbon Red responsive contract."""
from __future__ import annotations

import re

import pytest


@pytest.fixture()
def admin_client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'admin-ui.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-secret-admin-ui")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email="operator@example.com", password="matkhau-tot-12",
                       role="admin", is_verified=True)
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver")
    token = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text)
    assert token
    response = client.post("/login", data={"username": "operator@example.com",
                                            "password": "matkhau-tot-12",
                                            "csrf_token": token.group(1)},
                           follow_redirects=False)
    assert response.status_code == 303
    try:
        yield client
    finally:
        dbmod.reset_engine()


def test_custom_console_has_accessible_responsive_operator_shell(admin_client):
    response = admin_client.get("/admin/apikeys")
    assert response.status_code == 200
    body = response.text
    assert 'class="skip-link"' in body
    assert 'aria-label="Điều hướng quản trị"' in body
    assert 'class="adm-mobilemenu"' in body
    assert 'aria-current="page"' in body
    assert "Hệ thống vận hành" in body
    assert "🏠" not in body and "🔑" not in body


def test_sqladmin_uses_shared_carbon_red_tokens(admin_client):
    response = admin_client.get("/admin/user/list")
    assert response.status_code == 200
    body = response.text
    # ⭐ `?v=` la BAT BUOC, khong phai tuy chon — va truoc `admin_mvp_v3` dong
    #    nay chot dung truong hop SAI. Trang SQLAdmin nap `ltt.css` khong kem
    #    phien ban, nen sau moi lan doi CSS no phuc vu ban cu tu Cloudflare toi
    #    het TTL, trong khi trang tu viet da doi (CLAUDE.md quy tac 6). Loi nay
    #    da tung lam production hien chip thanh radio tho.
    assert 'href="/static/ltt.css?v=' in body
    # Golden UI DL-004 (16/09): Tabler tro ve TOKEN, khong hex — `#ef3731` duoi chu
    # trang chi 3,99:1 (duoi AA). Chot y dinh: mau chinh = token nen do cua he.
    assert "--tblr-primary:var(--brand-fill)" in body and "#ef3731" not in body
    assert 'aria-label="Điều hướng quản trị nhanh"' in body
    assert 'id="sqladmin-content"' in body
    assert "#3b6ef2" not in body
