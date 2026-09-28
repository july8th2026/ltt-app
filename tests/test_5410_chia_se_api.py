"""Tang HTTP cua chia se bang ma."""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'share-api.db').as_posix()}")
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
    ids = {}
    for email, role in (("share-a@example.com", "user"),
                        ("share-b@example.com", "user")):
        ids[email] = tao_nguoi_dung(db, email=email, password="Strong-pass-123",
                                    is_verified=True, role=role).id
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt
    row = OmmiMetaPrompt(owner_id=ids["share-a@example.com"], name="Meta cua A",
                         body="noi dung")
    db.add(row); db.commit()
    item_id = row.id
    db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-share-api-test",
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

    a, token_a = login("share-a@example.com")
    b, token_b = login("share-b@example.com")
    yield a, token_a, b, token_b, item_id
    a.close(); b.close(); dbmod.reset_engine(); storage_mod._storage = None


def test_owner_shares_and_stranger_receives(api):
    a, token_a, b, token_b, item_id = api
    made = a.post("/prompt-ai-ommi/api/share", headers={"X-CSRF-Token": token_a},
                  json={"target_kind": "meta_prompt", "target_id": item_id})
    assert made.status_code == 201, made.text
    code = made.json()["code"]

    preview = b.get(f"/prompt-ai-ommi/api/share/{code}")
    assert preview.status_code == 200 and preview.json()["name"] == "Meta cua A"

    received = b.post(f"/prompt-ai-ommi/api/share/{code}/nhan",
                      headers={"X-CSRF-Token": token_b}, json={})
    assert received.status_code == 201, received.text

    private_b = b.get("/prompt-ai-ommi/api/library/meta")
    assert [i["name"] for i in private_b.json()["items"]] == ["Meta cua A"]


def test_revoked_code_is_rejected_at_http_layer(api):
    a, token_a, b, token_b, item_id = api
    made = a.post("/prompt-ai-ommi/api/share", headers={"X-CSRF-Token": token_a},
                  json={"target_kind": "meta_prompt", "target_id": item_id})
    code = made.json()["code"]
    revoked = a.delete(f"/prompt-ai-ommi/api/share/{code}",
                       headers={"X-CSRF-Token": token_a})
    assert revoked.status_code == 200

    rejected = b.post(f"/prompt-ai-ommi/api/share/{code}/nhan",
                      headers={"X-CSRF-Token": token_b}, json={})
    assert rejected.status_code == 400


def test_a_normal_user_cannot_set_catalog_level(api):
    a, token_a, *_rest, item_id = api
    response = a.post(f"/prompt-ai-ommi/api/library/meta/{item_id}/share-level",
                      headers={"X-CSRF-Token": token_a},
                      json={"level": "catalog"})
    assert response.status_code == 403
