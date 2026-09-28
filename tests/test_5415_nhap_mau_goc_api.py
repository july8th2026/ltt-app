"""POST /api/admin/nhap-mau-goc - chi admin, idempotent o tang HTTP.

So dem 12 (meta_prompt) la cua Lan G, do TRUC TIEP tren ban sao Studio that
(27/09/2026) - xem apps/prompt_ai_ommi/services/nhap_mau_goc.py docstring.
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'nmg-api.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LTT_STORAGE", raising=False)
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    tao_nguoi_dung(db, email="admin@example.com", password="Strong-pass-123",
                   is_verified=True, role="admin")
    tao_nguoi_dung(db, email="user@example.com", password="Strong-pass-123",
                   is_verified=True, role="user")
    db.commit(); db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-nhap-mau-goc-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})

    def login(email):
        client = TestClient(app, base_url="https://testserver",
                            follow_redirects=True)
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        assert client.post("/login", data={
            "username": email, "password": "Strong-pass-123",
            "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
        studio = client.get("/prompt-ai-ommi")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
        return client, csrf

    admin, admin_token = login("admin@example.com")
    user, user_token = login("user@example.com")
    yield admin, admin_token, user, user_token
    admin.close(); user.close(); dbmod.reset_engine(); storage_mod._storage = None


def test_normal_user_cannot_import(api):
    _admin, _at, user, user_token = api
    response = user.post("/prompt-ai-ommi/api/admin/nhap-mau-goc",
                         headers={"X-CSRF-Token": user_token}, json={})
    assert response.status_code == 403


def test_admin_import_is_idempotent(api):
    """`total` cua thu vien catalog GOM ca builtin TINH (khong o CSDL, xem
    services/builtin_catalog.py) va cac ban ghi vua nhap - nen bai nay so
    CHENH LECH truoc/sau, khong go cung 12 vao assert."""
    admin, admin_token, *_ = api
    before = admin.get("/prompt-ai-ommi/api/library/meta?catalog=true&limit=200")
    assert before.status_code == 200, before.text
    total_before = before.json()["total"]

    first = admin.post("/prompt-ai-ommi/api/admin/nhap-mau-goc",
                       headers={"X-CSRF-Token": admin_token}, json={})
    assert first.status_code == 200, first.text
    assert first.json()["meta_prompt"]["them"] == 12

    second = admin.post("/prompt-ai-ommi/api/admin/nhap-mau-goc",
                       headers={"X-CSRF-Token": admin_token}, json={})
    assert second.status_code == 200
    assert second.json()["meta_prompt"] == {"them": 0, "bo_qua": 12}

    catalog = admin.get("/prompt-ai-ommi/api/library/meta?catalog=true&limit=200")
    assert catalog.status_code == 200, catalog.text
    assert catalog.json()["total"] == total_before + 12
