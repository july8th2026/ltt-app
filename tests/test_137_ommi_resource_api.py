"""Kho tài nguyên OMMI — tầng HTTP với hai người dùng thật.

Test service (`test_136`) chứng minh hàm lọc đúng. File này chứng minh **route**
cũng lọc đúng: một handler quên truyền `owner_id`, hoặc lấy nó từ body thay vì
từ phiên, thì service vẫn đúng mà API vẫn rò rỉ.
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'ommi-api.db').as_posix()}")
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
    for email in ("ommi-a@example.com", "ommi-b@example.com"):
        ids[email] = tao_nguoi_dung(db, email=email, password="Strong-pass-123",
                                    is_verified=True).id
    db.commit(); db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-resource-api-test",
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

    a, token_a = login("ommi-a@example.com")
    b, token_b = login("ommi-b@example.com")
    # ID thật của A cần cho phép thử "gài owner_id của nạn nhân vào body" —
    # gài một ID bịa thì handler nào cũng 404 và test không chứng minh được gì.
    yield a, token_a, b, token_b, ids["ommi-a@example.com"]
    a.close(); b.close(); dbmod.reset_engine(); storage_mod._storage = None


def _create(client, token, name="Nhân vật chính", kind="character"):
    response = client.post("/prompt-ai-ommi/api/resources",
                           headers={"X-CSRF-Token": token},
                           json={"kind": kind, "name": name})
    assert response.status_code == 201, response.text
    return response.json()


def test_owner_creates_reads_and_updates(api):
    a, token_a, *_rest = api
    made = _create(a, token_a)
    assert made["kind"] == "character" and made["is_catalog"] is False

    got = a.get(f"/prompt-ai-ommi/api/resources/{made['id']}")
    assert got.status_code == 200
    assert got.json()["name"] == "Nhân vật chính"

    updated = a.put(f"/prompt-ai-ommi/api/resources/{made['id']}",
                    headers={"X-CSRF-Token": token_a},
                    json={"name": "Đã đổi tên", "tags": ["hero", "chinh"]})
    assert updated.status_code == 200
    assert a.get(f"/prompt-ai-ommi/api/resources/{made['id']}").json()["tags"] == [
        "chinh", "hero"]


def test_every_resource_endpoint_returns_404_for_another_user(api):
    """Khuôn bắt buộc: thêm endpoint kho tài nguyên nào cũng phải có mặt ở đây."""
    a, token_a, b, token_b, id_a = api
    made = _create(a, token_a)
    rid = made["id"]

    checks = [
        ("GET", f"/prompt-ai-ommi/api/resources/{rid}", None),
        ("GET", f"/prompt-ai-ommi/api/resources/{rid}/usage", None),
        ("PUT", f"/prompt-ai-ommi/api/resources/{rid}", {"name": "Cướp"}),
        ("POST", f"/prompt-ai-ommi/api/resources/{rid}/archive", {"archived": True}),
        ("POST", f"/prompt-ai-ommi/api/resources/{rid}/clone", {}),
    ]
    # Mỗi endpoint thử hai lần: body sạch, và body có gài `owner_id` của nạn
    # nhân. Lần thứ hai mới là kiểu tấn công thật — chỉ thử body sạch thì một
    # handler tin `owner_id` do client gửi vẫn qua được test.
    victim = id_a
    for method, path, body in checks:
        for payload in (body, {**(body or {}), "owner_id": victim}):
            response = b.request(method, path,
                                 headers={"X-CSRF-Token": token_b}, json=payload)
            assert response.status_code == 404, (
                f"{method} {path} với body {payload!r} trả "
                f"{response.status_code}, phải 404")

    # Và bản ghi không hề bị đổi.
    assert a.get(f"/prompt-ai-ommi/api/resources/{rid}").json()["name"] == \
        "Nhân vật chính"


def test_listing_is_scoped_to_the_caller(api):
    a, token_a, b, token_b, _id_a = api
    _create(a, token_a, "Của A")
    _create(b, token_b, "Của B")

    seen_a = a.get("/prompt-ai-ommi/api/resources").json()
    seen_b = b.get("/prompt-ai-ommi/api/resources").json()
    assert [i["name"] for i in seen_a["items"]] == ["Của A"]
    assert [i["name"] for i in seen_b["items"]] == ["Của B"]
    assert seen_a["counts"]["character"] == 1


def test_owner_id_in_the_body_is_ignored(api):
    """Nếu handler tin `owner_id` do client gửi thì bất kỳ ai cũng đọc được kho
    người khác chỉ bằng cách thêm một trường vào JSON."""
    a, token_a, b, token_b, _id_a = api
    _create(a, token_a, "Của A")
    made_b = b.post("/prompt-ai-ommi/api/resources",
                    headers={"X-CSRF-Token": token_b},
                    json={"kind": "character", "name": "Giả mạo",
                          "owner_id": "user-a"})
    assert made_b.status_code == 201
    # Vẫn thuộc về B, và B vẫn chỉ thấy đúng một bản ghi của mình.
    assert [i["name"] for i in b.get(
        "/prompt-ai-ommi/api/resources").json()["items"]] == ["Giả mạo"]


def test_invalid_kind_is_a_400_not_a_500(api):
    a, token_a, *_rest = api
    response = a.post("/prompt-ai-ommi/api/resources",
                      headers={"X-CSRF-Token": token_a},
                      json={"kind": "khong-ton-tai", "name": "X"})
    assert response.status_code == 400


def test_write_without_csrf_is_rejected(api):
    a, _token_a, *_rest = api
    response = a.post("/prompt-ai-ommi/api/resources",
                      json={"kind": "character", "name": "Không token"})
    assert response.status_code == 400


def test_archived_resource_leaves_the_default_listing(api):
    a, token_a, *_rest = api
    made = _create(a, token_a)
    a.post(f"/prompt-ai-ommi/api/resources/{made['id']}/archive",
           headers={"X-CSRF-Token": token_a}, json={"archived": True})
    assert a.get("/prompt-ai-ommi/api/resources").json()["total"] == 0
    assert a.get("/prompt-ai-ommi/api/resources?archived=true"
                 ).json()["total"] == 1
