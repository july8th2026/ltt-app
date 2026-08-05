"""Ảnh của tài nguyên OMMI — upload, xác nhận, xoá.

Hai lỗ hổng đặc trưng của luồng upload hai bước, cả hai đều được thử ở đây:

1. Gắn ảnh vào tài nguyên của người khác — handler quên kiểm chủ sở hữu.
2. Xác nhận một khoá lưu trữ KHÔNG thuộc thư mục của mình. Người gọi tự chọn
   `key`, nên nếu chỉ kiểm "file có tồn tại" thì gửi khoá của người khác là gắn
   được ảnh người ta vào tài nguyên của mình.
"""
from __future__ import annotations

import io
import json
import re

import pytest
from fastapi.testclient import TestClient

PNG = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'ommi-img.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LTT_STORAGE", raising=False)
    monkeypatch.delenv("LTT_R2_BROWSER_UPLOAD_ENABLED", raising=False)
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
    for email in ("img-a@example.com", "img-b@example.com"):
        ids[email] = tao_nguoi_dung(db, email=email, password="Strong-pass-123",
                                    is_verified=True).id
    db.commit(); db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-image-test",
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

    a, token_a = login("img-a@example.com")
    b, token_b = login("img-b@example.com")
    yield (a, token_a, ids["img-a@example.com"],
           b, token_b, ids["img-b@example.com"], storage_mod)
    a.close(); b.close(); dbmod.reset_engine(); storage_mod._storage = None


def _resource(client, token, name="Nhân vật"):
    response = client.post("/prompt-ai-ommi/api/resources",
                           headers={"X-CSRF-Token": token},
                           json={"kind": "character", "name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _upload(client, token, rid, data=PNG, content_type="image/png"):
    return client.post(
        f"/prompt-ai-ommi/api/resources/{rid}/images",
        data={"csrf_token": token, "label": "goc"},
        files={"file": ("a.png", io.BytesIO(data), content_type)})


def test_upload_attaches_an_image_and_sets_the_cover(api):
    a, token_a, *_ = api
    rid = _resource(a, token_a)
    response = _upload(a, token_a, rid)
    assert response.status_code == 201, response.text
    variant = response.json()

    detail = a.get(f"/prompt-ai-ommi/api/resources/{rid}").json()
    assert [v["id"] for v in detail["variants"]] == [variant["id"]]
    assert detail["cover_variant_id"] == variant["id"]
    assert variant["bytes_size"] == len(PNG)


def test_cannot_upload_into_someone_elses_resource(api):
    a, token_a, _id_a, b, token_b, *_ = api
    rid = _resource(a, token_a)
    assert _upload(b, token_b, rid).status_code == 404
    assert a.get(f"/prompt-ai-ommi/api/resources/{rid}").json()["variants"] == []


def test_ticket_requires_owning_the_resource(api):
    a, token_a, _id_a, b, token_b, *_ = api
    rid = _resource(a, token_a)
    response = b.post(f"/prompt-ai-ommi/api/resources/{rid}/images/ticket",
                      headers={"X-CSRF-Token": token_b},
                      json={"content_type": "image/png"})
    assert response.status_code == 404


def test_ticket_falls_back_to_local_when_direct_upload_is_off(api):
    a, token_a, id_a, *_ = api
    rid = _resource(a, token_a)
    body = a.post(f"/prompt-ai-ommi/api/resources/{rid}/images/ticket",
                  headers={"X-CSRF-Token": token_a},
                  json={"content_type": "image/png"}).json()
    assert body["mode"] == "local"
    # Khoá luôn nằm trong thư mục của chính người gọi.
    assert body["key"].startswith(f"ommi/{id_a}/{rid}/")
    # Khoá phải NGẮN: Windows chặn ở 260 ký tự và LocalStorage còn thêm hậu tố
    # `.part<pid>` khi ghi. Khoá dài đã thật sự làm upload vỡ trên fixture.
    assert len(body["key"]) < 120, f"khoá quá dài: {len(body['key'])}"


def test_confirm_rejects_a_key_outside_the_callers_own_folder(api):
    """Client tự chọn `key`. Chỉ kiểm 'file có tồn tại' là chưa đủ — phải kiểm
    khoá thuộc đúng thư mục người gọi, nếu không gửi khoá của người khác là gắn
    được ảnh của họ vào tài nguyên của mình."""
    a, token_a, _id_a, b, token_b, id_b, storage_mod = api
    rid_a = _resource(a, token_a)
    rid_b = _resource(b, token_b)

    # B tải ảnh thật của mình lên, rồi A thử xác nhận khoá đó.
    assert _upload(b, token_b, rid_b).status_code == 201
    stolen = b.get(f"/prompt-ai-ommi/api/resources/{rid_b}"
                   ).json()["variants"][0]["storage_key"]
    assert storage_mod.get_storage().exists(stolen)

    response = a.post(f"/prompt-ai-ommi/api/resources/{rid_a}/images/confirm",
                      headers={"X-CSRF-Token": token_a}, json={"key": stolen})
    assert response.status_code == 400
    assert a.get(f"/prompt-ai-ommi/api/resources/{rid_a}").json()["variants"] == []


def test_confirm_rejects_a_key_with_no_file_behind_it(api):
    a, token_a, id_a, *_ = api
    rid = _resource(a, token_a)
    ghost = f"ommi/{id_a}/{rid}/khong-co-that.png"
    response = a.post(f"/prompt-ai-ommi/api/resources/{rid}/images/confirm",
                      headers={"X-CSRF-Token": token_a}, json={"key": ghost})
    assert response.status_code == 400


def test_confirm_records_an_image_the_caller_really_uploaded(api):
    a, token_a, id_a, *_ = api
    rid = _resource(a, token_a)
    key = a.post(f"/prompt-ai-ommi/api/resources/{rid}/images/ticket",
                 headers={"X-CSRF-Token": token_a},
                 json={"content_type": "image/png"}).json()["key"]
    _a, _t, _i, _b, _tb, _ib, storage_mod = api
    storage_mod.get_storage().put(key, io.BytesIO(PNG), content_type="image/png")

    response = a.post(f"/prompt-ai-ommi/api/resources/{rid}/images/confirm",
                      headers={"X-CSRF-Token": token_a},
                      json={"key": key, "width": 800, "height": 600})
    assert response.status_code == 201, response.text
    assert response.json()["width"] == 800
    assert response.json()["bytes_size"] == len(PNG)


def test_only_image_types_are_accepted(api):
    a, token_a, *_ = api
    rid = _resource(a, token_a)
    assert _upload(a, token_a, rid, b"GIF89a", "image/gif").status_code == 400


def test_empty_file_is_rejected(api):
    a, token_a, *_ = api
    rid = _resource(a, token_a)
    assert _upload(a, token_a, rid, b"").status_code == 400


def test_other_user_cannot_delete_an_image(api):
    a, token_a, _id_a, b, token_b, *_ = api
    rid = _resource(a, token_a)
    variant = _upload(a, token_a, rid).json()
    response = b.delete(
        f"/prompt-ai-ommi/api/resources/{rid}/images/{variant['id']}",
        headers={"X-CSRF-Token": token_b})
    assert response.status_code == 404
    assert len(a.get(f"/prompt-ai-ommi/api/resources/{rid}"
                     ).json()["variants"]) == 1


def test_owner_deletes_an_image_and_the_cover_moves_on(api):
    a, token_a, *_ = api
    rid = _resource(a, token_a)
    first = _upload(a, token_a, rid).json()
    second = _upload(a, token_a, rid).json()
    assert a.delete(f"/prompt-ai-ommi/api/resources/{rid}/images/{first['id']}",
                    headers={"X-CSRF-Token": token_a}).status_code == 200
    detail = a.get(f"/prompt-ai-ommi/api/resources/{rid}").json()
    assert detail["cover_variant_id"] == second["id"]


def test_image_url_is_not_readable_by_another_user(api):
    a, token_a, _id_a, b, _token_b, *_ = api
    rid = _resource(a, token_a)
    variant = _upload(a, token_a, rid).json()
    path = f"/prompt-ai-ommi/api/resources/{rid}/images/{variant['id']}/url"
    assert a.get(path).status_code == 200
    assert b.get(path).status_code == 404


def test_image_url_points_at_a_route_that_actually_serves_the_file(api):
    """Bản đầu trả `download_token` của storage và ảnh 404 trên browser: token
    nằm trong RAM của TỪNG tiến trình, mà web và worker là hai tiến trình khác
    nhau. Test phải đi hết đường — lấy URL RỒI tải thật."""
    a, token_a, *_ = api
    rid = _resource(a, token_a)
    variant = _upload(a, token_a, rid).json()

    body = a.get(f"/prompt-ai-ommi/api/resources/{rid}/images/{variant['id']}/url").json()
    assert "token" not in body, "token của storage không dùng được xuyên tiến trình"
    served = a.get(body["url"])
    assert served.status_code == 200, served.text
    assert served.content == PNG


def test_serving_route_refuses_a_key_owned_by_someone_else(api):
    a, token_a, _id_a, b, _token_b, id_b, _sm = api
    rid_a = _resource(a, token_a)
    _upload(a, token_a, rid_a)
    # B đoán đúng dạng khoá của A vẫn không đọc được.
    stolen = a.get(f"/prompt-ai-ommi/api/resources/{rid_a}").json()["variants"][0]["storage_key"]
    assert b.get(f"/prompt-ai-ommi/f/{stolen}").status_code == 404
