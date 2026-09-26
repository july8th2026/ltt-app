"""DELETE /bindings/{tag} + 400 khi role sai — spec Sec 6.1."""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'routes-bindings2.db').as_posix()}")
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
    user_id = tao_nguoi_dung(db, email="ommi-bindings2@example.com",
                             password="Strong-pass-123", is_verified=True).id
    db.commit(); db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-bindings2-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})

    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": "ommi-bindings2@example.com", "password": "Strong-pass-123",
        "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
    studio = client.get("/prompt-ai-ommi")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)

    yield client, csrf, user_id
    client.close(); dbmod.reset_engine(); storage_mod._storage = None


def _tao_project(client, csrf) -> str:
    resp = client.post("/prompt-ai-ommi/api/projects",
                       headers={"X-CSRF-Token": csrf}, json={"name": "Du an X"})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _tao_variant(user_id: str) -> str:
    import platform_core.db as dbmod
    db = next(dbmod.get_session())
    from apps.prompt_ai_ommi.services import resources as rsvc
    resource = rsvc.create(db, owner_id=user_id, kind="character", name="Nhân vật A")
    variant = rsvc.add_variant(db, resource_id=resource.id, owner_id=user_id,
                               storage_key=f"ommi/{user_id}/{resource.id}/a.png")
    db.commit()
    variant_id = variant.id
    db.close()
    return variant_id


def test_delete_tag_khong_ton_tai_tra_404(api):
    client, csrf, user_id = api
    project_id = _tao_project(client, csrf)
    resp = client.delete(
        f"/prompt-ai-ommi/api/projects/{project_id}/bindings/@IMAGE_9",
        headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 404, resp.text


def test_delete_dung_tag_tra_ve_danh_sach_con_lai(api):
    client, csrf, user_id = api
    project_id = _tao_project(client, csrf)
    variant_id = _tao_variant(user_id)
    client.put(f"/prompt-ai-ommi/api/projects/{project_id}/bindings",
              headers={"X-CSRF-Token": csrf},
              json={"scene_id": "s1",
                    "items": [{"kind": "image", "variant_id": variant_id}]})
    resp = client.delete(
        f"/prompt-ai-ommi/api/projects/{project_id}/bindings/@IMAGE_1"
        "?scene_id=s1", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200, resp.text
    assert resp.json()["bindings"] == []


def test_put_role_sai_tra_400(api):
    client, csrf, user_id = api
    project_id = _tao_project(client, csrf)
    variant_id = _tao_variant(user_id)
    resp = client.put(f"/prompt-ai-ommi/api/projects/{project_id}/bindings",
                      headers={"X-CSRF-Token": csrf},
                      json={"scene_id": "s1",
                            "items": [{"kind": "image", "variant_id": variant_id,
                                      "role": "khong_ton_tai"}]})
    assert resp.status_code == 400, resp.text
