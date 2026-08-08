"""Thư viện OMMI — tầng HTTP.

Điểm nhạy nhất ở đây là `publish`: nó ghi vào không gian MỌI NGƯỜI đọc. Quyền
admin phải lấy từ CSDL, không bao giờ từ body — nên test replay mọi endpoint
ghi với `role: "admin"` và `is_admin: true` gài sẵn trong JSON.
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

KINDS = ["meta", "snippet", "style"]


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'lib-api.db').as_posix()}")
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
    for email in ("lib-a@example.com", "lib-b@example.com"):
        ids[email] = tao_nguoi_dung(db, email=email, password="Strong-pass-123",
                                    is_verified=True).id
    db.commit(); db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-library-api-test",
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

    a, token_a = login("lib-a@example.com")
    b, token_b = login("lib-b@example.com")
    yield a, token_a, ids["lib-a@example.com"], b, token_b
    a.close(); b.close(); dbmod.reset_engine(); storage_mod._storage = None


def _create(client, token, kind, name="Mục của tôi", body="noi dung"):
    made = client.post(f"/prompt-ai-ommi/api/library/{kind}",
                       headers={"X-CSRF-Token": token},
                       json={"name": name, "body": body})
    assert made.status_code == 201, made.text
    return made.json()


@pytest.mark.parametrize("kind", KINDS)
def test_owner_creates_reads_and_edits(api, kind):
    a, token_a, *_ = api
    made = _create(a, token_a, kind)
    got = a.get(f"/prompt-ai-ommi/api/library/{kind}/{made['id']}")
    assert got.status_code == 200 and got.json()["name"] == "Mục của tôi"

    edited = a.put(f"/prompt-ai-ommi/api/library/{kind}/{made['id']}",
                   headers={"X-CSRF-Token": token_a},
                   json={"body": "noi dung moi", "note": "sua"})
    assert edited.status_code == 200
    assert edited.json()["body"] == "noi dung moi"


@pytest.mark.parametrize("kind", KINDS)
def test_every_library_endpoint_is_404_for_another_user(api, kind):
    a, token_a, id_a, b, token_b = api
    made = _create(a, token_a, kind)
    item = made["id"]
    checks = [
        ("GET", f"/prompt-ai-ommi/api/library/{kind}/{item}", None),
        ("PUT", f"/prompt-ai-ommi/api/library/{kind}/{item}", {"name": "Cướp"}),
        ("POST", f"/prompt-ai-ommi/api/library/{kind}/{item}/archive",
         {"archived": True}),
        ("POST", f"/prompt-ai-ommi/api/library/{kind}/{item}/clone", {}),
    ]
    for method, path, body in checks:
        # Thử cả body sạch lẫn body gài owner_id của nạn nhân — đó mới là kiểu
        # tấn công thật, và bản test đầu tiên của kho tài nguyên đã bỏ sót nó.
        for payload in (body, {**(body or {}), "owner_id": id_a}):
            response = b.request(method, path,
                                 headers={"X-CSRF-Token": token_b}, json=payload)
            assert response.status_code == 404, (
                f"{method} {path} với {payload!r} trả {response.status_code}")
    assert a.get(f"/prompt-ai-ommi/api/library/{kind}/{item}"
                 ).json()["name"] == "Mục của tôi"


@pytest.mark.parametrize("kind", KINDS)
def test_listing_separates_private_from_catalog(api, kind):
    a, token_a, *_ = api
    _create(a, token_a, kind, "Riêng của tôi")
    private = a.get(f"/prompt-ai-ommi/api/library/{kind}").json()
    catalog = a.get(f"/prompt-ai-ommi/api/library/{kind}?catalog=true").json()
    assert [i["name"] for i in private["items"]] == ["Riêng của tôi"]
    assert catalog["items"]
    assert all(item["is_catalog"] for item in catalog["items"])
    assert "Riêng của tôi" not in [item["name"] for item in catalog["items"]]


@pytest.mark.parametrize("kind", KINDS)
def test_a_normal_user_cannot_publish_even_by_claiming_admin(api, kind):
    """Quyền admin phải đọc từ CSDL. Nếu handler tin `role` trong body thì bất
    kỳ ai cũng đẩy được nội dung vào không gian mọi người đọc."""
    a, token_a, *_ = api
    made = _create(a, token_a, kind)
    before = a.get(f"/prompt-ai-ommi/api/library/{kind}?catalog=true").json()
    before_ids = {item["id"] for item in before["items"]}
    for payload in ({}, {"role": "admin"}, {"is_admin": True}):
        response = a.post(
            f"/prompt-ai-ommi/api/library/{kind}/{made['id']}/publish",
            headers={"X-CSRF-Token": token_a}, json=payload)
        assert response.status_code == 403, f"{payload!r} → {response.status_code}"
    after = a.get(f"/prompt-ai-ommi/api/library/{kind}?catalog=true").json()
    assert {item["id"] for item in after["items"]} == before_ids


@pytest.mark.parametrize("kind", KINDS)
def test_user_can_clone_a_builtin_template_into_private_library(api, kind):
    a, token_a, *_ = api
    catalog = a.get(f"/prompt-ai-ommi/api/library/{kind}?catalog=true").json()
    source = catalog["items"][0]
    made = a.post(f"/prompt-ai-ommi/api/library/{kind}/{source['id']}/clone",
                  headers={"X-CSRF-Token": token_a}, json={})
    assert made.status_code == 201, made.text
    copied = made.json()
    assert copied["is_catalog"] is False
    assert copied["cloned_from_id"] == source["id"]
    assert copied["body"] == source["body"]


@pytest.mark.parametrize("kind", KINDS)
def test_cloning_a_private_item_of_someone_else_is_404(api, kind):
    a, token_a, _id_a, b, token_b = api
    made = _create(a, token_a, kind)
    response = b.post(f"/prompt-ai-ommi/api/library/{kind}/{made['id']}/clone",
                      headers={"X-CSRF-Token": token_b}, json={})
    assert response.status_code == 404


@pytest.mark.parametrize("kind", ["meta", "snippet"])
def test_history_is_returned_with_the_item(api, kind):
    a, token_a, *_ = api
    made = _create(a, token_a, kind)
    a.put(f"/prompt-ai-ommi/api/library/{kind}/{made['id']}",
          headers={"X-CSRF-Token": token_a},
          json={"body": "ban hai", "note": "lan sua thu nhat"})
    detail = a.get(f"/prompt-ai-ommi/api/library/{kind}/{made['id']}").json()
    assert [v["version"] for v in detail["versions"]] == [2, 1]
    assert detail["versions"][0]["note"] == "lan sua thu nhat"


def test_unknown_kind_is_a_400(api):
    a, token_a, *_ = api
    assert a.get("/prompt-ai-ommi/api/library/khong-co-loai").status_code == 400


def test_write_without_csrf_is_rejected(api):
    a, _token_a, *_ = api
    response = a.post("/prompt-ai-ommi/api/library/meta",
                      json={"name": "Không token"})
    assert response.status_code == 400
