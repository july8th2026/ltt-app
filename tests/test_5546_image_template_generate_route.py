"""tests/test_5546_image_template_generate_route.py.

🔴 Phép gọi HTTP THẬT (qua TestClient dựng từ `server.app.create_app()`) cho
endpoint Task 11 — kiểm tra bị lọt hết ở kiểm tĩnh mà chỉ hiện ra khi ĐƯỜNG
CHẠY THẬT được nạp qua FastAPI (bài học 45 phép kiểm XANH bỏ qua NameError).
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'tpl-route.db').as_posix()}")
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
    user = tao_nguoi_dung(db, email="tpl-a@example.com",
                          password="Strong-pass-123", is_verified=True)
    credit.cap_tay(db, user.id, 200, by="test")

    from apps.prompt_ai_ommi.tables import OmmiImageTemplate
    # ⚠️ `OmmiImageTemplate.owner_id` là NOT NULL (khác `OmmiResource` cho
    # phép NULL=catalog) — mẫu catalog thật vẫn có một admin làm chủ, đánh
    # dấu bằng `share_level` (xem `services/nhap_mau_goc.py:124-125`).
    tpl = OmmiImageTemplate(name="Mau X", owner_id=user.id,
                           prompt_text="Ve {SUBJECT} {STYLE} {EXTRA} {EQUIPMENT}",
                           n_outputs=1, aspect="1:1", asset_type="prop",
                           requires_ref=False, multi_ref_max=1,
                           negative_lock="", is_builtin=True)
    db.add(tpl); db.commit()
    tpl_id = tpl.id
    db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-tpl-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})
    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": "tpl-a@example.com", "password": "Strong-pass-123",
        "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
    studio = client.get("/prompt-ai-ommi")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
    yield client, csrf, tpl_id
    client.close(); dbmod.reset_engine(); storage_mod._storage = None


def test_generate_from_template_quotes_then_confirms(api):
    client, token, tpl_id = api
    made = client.post("/prompt-ai-ommi/api/resources",
                       headers={"X-CSRF-Token": token},
                       json={"kind": "prop", "name": "A"})
    assert made.status_code == 201, made.text
    rid = made.json()["id"]

    quoted = client.post(f"/prompt-ai-ommi/api/image-templates/{tpl_id}/generate",
                        headers={"X-CSRF-Token": token},
                        json={"resource_id": rid})
    assert quoted.status_code == 200, quoted.text
    assert quoted.json()["confirmed"] is False

    started = client.post(f"/prompt-ai-ommi/api/image-templates/{tpl_id}/generate",
                         headers={"X-CSRF-Token": token},
                         json={"resource_id": rid, "confirmed": True})
    assert started.status_code == 200, started.text
    assert started.json()["confirmed"] is True


def test_generate_from_unknown_template_is_404(api):
    client, token, _tpl_id = api
    resp = client.post(
        "/prompt-ai-ommi/api/image-templates/khong-ton-tai/generate",
        headers={"X-CSRF-Token": token}, json={"resource_id": "x"})
    assert resp.status_code == 404


def test_generate_with_unknown_resource_is_client_error_not_500(api):
    """Kênh THẬT bắt được lỗi mà kiểm tĩnh bỏ qua: `rsvc.get_owned` raise
    `ResourceNotFound`, phải được `_resource_error` dịch thành 404 — nếu tên
    hàm/khoá lỗi sai chỗ nào, route này trả 500 chứ không phải 404."""
    client, token, tpl_id = api
    resp = client.post(f"/prompt-ai-ommi/api/image-templates/{tpl_id}/generate",
                       headers={"X-CSRF-Token": token},
                       json={"resource_id": "khong-ton-tai", "confirmed": True})
    assert resp.status_code == 404, resp.text
