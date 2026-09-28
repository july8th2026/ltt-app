"""tests/test_5507_trash_routes_api.py."""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'trash-api.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LTT_STORAGE", raising=False)
    monkeypatch.setenv("LTT_PROMPT_AI_OMMI_ROLLOUT", "public")
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    db = next(dbmod.get_session())
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    user = tao_nguoi_dung(db, email="trash-a@example.com",
                          password="Strong-pass-123", is_verified=True)
    credit.cap_tay(db, user.id, 100, by="test")
    db.commit(); db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-trash-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})
    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": "trash-a@example.com", "password": "Strong-pass-123",
        "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
    studio = client.get("/prompt-ai-ommi")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
    yield client, csrf
    client.close(); dbmod.reset_engine(); storage_mod._storage = None


def test_delete_then_list_then_restore(api):
    client, token = api
    made = client.post("/prompt-ai-ommi/api/resources",
                       headers={"X-CSRF-Token": token},
                       json={"kind": "prop", "name": "Kiem"})
    rid = made.json()["id"]

    deleted = client.post(f"/prompt-ai-ommi/api/resources/{rid}/delete",
                          headers={"X-CSRF-Token": token})
    assert deleted.status_code == 200, deleted.text
    trash_id = deleted.json()["trash_id"]

    listed = client.get("/prompt-ai-ommi/api/trash")
    assert listed.status_code == 200
    assert any(item["id"] == trash_id for item in listed.json()["items"])

    restored = client.post(f"/prompt-ai-ommi/api/trash/{trash_id}/restore",
                           headers={"X-CSRF-Token": token})
    assert restored.status_code == 200, restored.text
    assert restored.json()["id"] == rid

    again = client.get(f"/prompt-ai-ommi/api/resources/{rid}")
    assert again.status_code == 200


def test_purge_endpoint_permanently_removes_a_ticket_before_its_deadline(api):
    """⭐ Ca tiêm lỗi bổ sung: sau `DELETE /api/trash/{id}`, cùng vé đó KHÔNG
    còn xuất hiện trong `GET /api/trash`, và restore vé đó phải bị từ chối —
    một cài đặt chỉ xoá "về mặt hiển thị" (còn nằm trong CSDL) vẫn cho qua bài
    kiểm cũ vốn không gọi lại `list`/`restore` sau `DELETE`.
    """
    client, token = api
    made = client.post("/prompt-ai-ommi/api/resources",
                       headers={"X-CSRF-Token": token},
                       json={"kind": "prop", "name": "Se bi xoa han"})
    rid = made.json()["id"]
    deleted = client.post(f"/prompt-ai-ommi/api/resources/{rid}/delete",
                          headers={"X-CSRF-Token": token})
    trash_id = deleted.json()["trash_id"]

    purged = client.delete(f"/prompt-ai-ommi/api/trash/{trash_id}",
                           headers={"X-CSRF-Token": token})
    assert purged.status_code == 200, purged.text
    assert purged.json()["da_xoa_ban"] == 1

    listed = client.get("/prompt-ai-ommi/api/trash")
    assert all(item["id"] != trash_id for item in listed.json()["items"])

    restored = client.post(f"/prompt-ai-ommi/api/trash/{trash_id}/restore",
                           headers={"X-CSRF-Token": token})
    assert restored.status_code == 404


def test_trash_endpoints_are_scoped_to_the_logged_in_owner(api, tmp_path,
                                                           monkeypatch):
    """Một khách không thấy, không khôi phục được, không purge được vé của
    khách khác — dù biết đúng `trash_id`.
    """
    client, token = api
    made = client.post("/prompt-ai-ommi/api/resources",
                       headers={"X-CSRF-Token": token},
                       json={"kind": "prop", "name": "Cua alice"})
    rid = made.json()["id"]
    deleted = client.post(f"/prompt-ai-ommi/api/resources/{rid}/delete",
                          headers={"X-CSRF-Token": token})
    trash_id = deleted.json()["trash_id"]

    # Đăng nhập bằng một khách KHÁC trong cùng CSDL.
    import platform_core.db as dbmod
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    tao_nguoi_dung(db, email="trash-b@example.com",
                   password="Strong-pass-456", is_verified=True)
    db.commit(); db.close()

    other = client.__class__(
        client.app, base_url="https://testserver", follow_redirects=True)
    page = other.get("/login")
    import re as _re
    other_token = _re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    other.post("/login", data={"username": "trash-b@example.com",
                               "password": "Strong-pass-456",
                               "csrf_token": other_token, "next": "/prompt-ai-ommi"})
    studio = other.get("/prompt-ai-ommi")
    other_csrf = _re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)

    listed = other.get("/api/trash".replace("/api", "/prompt-ai-ommi/api"))
    assert all(item["id"] != trash_id for item in listed.json()["items"])

    restored = other.post(f"/prompt-ai-ommi/api/trash/{trash_id}/restore",
                          headers={"X-CSRF-Token": other_csrf})
    assert restored.status_code == 404

    purged = other.delete(f"/prompt-ai-ommi/api/trash/{trash_id}",
                          headers={"X-CSRF-Token": other_csrf})
    assert purged.status_code == 404
    other.close()
