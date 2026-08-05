"""Tổng quan và Chi phí — số liệu phải là của CHÍNH người gọi.

Ảnh giao diện tham chiếu hiển thị "Tổng chi phí team hôm nay" bằng USD. Cả hai
đều không được sao chép: khái niệm team chưa tồn tại trong nền tảng, và Q31 đã
chốt đơn vị là credit. Test này chốt cả hai điều đó.
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'ov.db').as_posix()}")
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
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    for email, amount in (("ov-a@example.com", 120), ("ov-b@example.com", 40)):
        user = tao_nguoi_dung(db, email=email, password="Strong-pass-123",
                              is_verified=True)
        credit.cap_tay(db, user.id, amount, by="test")
    db.commit(); db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-overview-test",
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

    a, token_a = login("ov-a@example.com")
    b, token_b = login("ov-b@example.com")
    yield a, token_a, b, token_b
    a.close(); b.close(); dbmod.reset_engine(); storage_mod._storage = None


def test_overview_counts_only_the_callers_own_things(api):
    a, token_a, b, token_b = api
    a.post("/prompt-ai-ommi/api/resources", headers={"X-CSRF-Token": token_a},
           json={"kind": "character", "name": "Của A"})
    a.post("/prompt-ai-ommi/api/library/meta", headers={"X-CSRF-Token": token_a},
           json={"name": "Meta của A"})
    for _ in range(3):
        b.post("/prompt-ai-ommi/api/resources", headers={"X-CSRF-Token": token_b},
               json={"kind": "prop", "name": "Của B"})

    seen = a.get("/prompt-ai-ommi/api/overview").json()
    assert seen["counts"]["resources"] == 1
    assert seen["counts"]["meta_prompts"] == 1
    assert seen["resource_kinds"] == {"character": 1, "background": 0, "prop": 0,
                                      "vehicle": 0, "misc": 0}

    other = b.get("/prompt-ai-ommi/api/overview").json()
    assert other["counts"]["resources"] == 3
    assert other["counts"]["meta_prompts"] == 0


def test_overview_reports_the_callers_own_balance(api):
    a, _token_a, b, _token_b = api
    assert a.get("/prompt-ai-ommi/api/overview").json()["credit_balance"] == 120
    assert b.get("/prompt-ai-ommi/api/overview").json()["credit_balance"] == 40


def test_credit_summary_is_in_credit_and_never_a_currency(api):
    """Ảnh tham chiếu dùng USD. Quy đổi ở đây tạo cách tính giá thứ hai, trong
    khi Q31 chốt 1 credit = 100đ ở đúng một chỗ."""
    a, *_ = api
    body = a.get("/prompt-ai-ommi/api/credit").json()
    assert body["balance"] == 120
    assert body["added"] == 120 and body["spent"] == 0
    # Không có trường tiền tệ nào lọt ra.
    text = json.dumps(body)
    for banned in ("usd", "USD", "$", "vnd", "VND"):
        assert banned not in text, f"phản hồi chứa đơn vị tiền tệ: {banned}"


def test_credit_entries_never_cross_users(api):
    a, _token_a, b, _token_b = api
    entries = a.get("/prompt-ai-ommi/api/credit").json()["entries"]
    assert len(entries) == 1 and entries[0]["delta"] == 120
    other = b.get("/prompt-ai-ommi/api/credit").json()["entries"]
    assert len(other) == 1 and other[0]["delta"] == 40


def test_overview_needs_a_login(api):
    from fastapi.testclient import TestClient
    a, *_ = api
    anon = TestClient(a.app, base_url="https://testserver", follow_redirects=False)
    response = anon.get("/prompt-ai-ommi/api/overview")
    assert response.status_code in (302, 303, 401, 403)
