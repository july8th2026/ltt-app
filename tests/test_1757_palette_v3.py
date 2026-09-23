"""Spec §13.1/§13.4 — MỘT đường palette, sinh từ registry, kèm luật nối dây."""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'api.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    tao_nguoi_dung(db, email="palette@example.com", password="Strong-pass-123",
                   is_verified=True)
    db.commit(); db.close(); dbmod.reset_engine()
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "palette-v3-test-session",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})
    client = TestClient(app, base_url="https://testserver", follow_redirects=True)
    page = client.get("/login")
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
    assert client.post("/login", data={
        "username": "palette@example.com", "password": "Strong-pass-123",
        "csrf_token": token, "next": "/agent/canvas"}).status_code == 200
    yield client
    client.close(); dbmod.reset_engine()


def test_palette_can_dang_nhap(api):
    from fastapi.testclient import TestClient as TC
    khach = TC(api.app, base_url="https://testserver", follow_redirects=False)
    assert khach.get("/agent/api/v3/palette").status_code in (302, 303, 401, 403)
    khach.close()


def test_palette_nhom_theo_category_dung_thu_tu(api):
    from platform_core.workflow import nut
    body = api.get("/agent/api/v3/palette").json()
    assert body["phien_ban"] == 3
    ten_nhom = [n["category"] for n in body["nhom"]]
    assert ten_nhom == [c for c in nut.CATEGORY if c in ten_nhom]
    assert "TRIGGERS" in ten_nhom and "LTT_APPS" in ten_nhom


def test_moi_node_mang_du_thong_tin_the_palette(api):
    body = api.get("/agent/api/v3/palette").json()
    apps = next(n for n in body["nhom"] if n["category"] == "LTT_APPS")["nut"]
    nd = next(x for x in apps if x["type"] == "app.transcript.run")
    assert nd["type_version"] == 1 and nd["kind"] == "app"
    assert nd["title"] and nd["description"] and nd["app_name"]
    assert nd["gia"] == {"kieu": "theo_registry", "so": 0,
                         "job_type": "transcript.run"}
    assert nd["resource"]["class"] == "gpu"
    assert {"ten": "audio", "kieu": "audio", "bat_buoc": True,
            "nhieu": False} in nd["cong_vao"]
    assert {"ten": "transcript", "kieu": "json", "bat_buoc": True,
            "nhieu": False} in nd["cong_ra"]
    assert nd["tham_so"]["type"] == "object"
    assert nd["publish_duoc"] is True


def test_node_loi_chua_publish_duoc_thi_bao_ra_chu_khong_giau(api):
    body = api.get("/agent/api/v3/palette").json()
    trig = next(n for n in body["nhom"] if n["category"] == "TRIGGERS")["nut"]
    assert [x["type"] for x in trig] == ["trigger.manual"]
    assert trig[0]["publish_duoc"] is False


def test_khong_lo_job_type_noi_bo_cua_provider(api):
    # `gia.job_type` la lan cua NEN TANG, khong phai ten provider — nhung
    # `api_contract`, `sync_executor`, `admission_*` thi KHONG duoc ra ngoai.
    tho = api.get("/agent/api/v3/palette").text
    for cam in ("sync_executor", "api_contract", "admission_token_pool",
                "kiem_truoc", "tuy_chon_dong"):
        assert cam not in tho


def test_luat_noi_day_la_CUNG_mot_bang_voi_he_kieu(api):
    from platform_core.workflow import he_kieu
    body = api.get("/agent/api/v3/luat-noi-day").json()
    assert body == he_kieu.xuat_luat_noi_day()
    # Palette nhung san cung bang => Canvas chi can MOT luot goi khi mo trang.
    assert api.get("/agent/api/v3/palette").json()["luat_noi_day"] == body


def test_palette_loc_theo_quyen_app_cua_nguoi_dung(api, monkeypatch):
    from platform_core import app_access
    monkeypatch.setattr(app_access, "muc_quyen",
                        lambda db, user, slug: app_access.ENABLED
                        if slug != "transcript" else "")
    apps = next(n for n in api.get("/agent/api/v3/palette").json()["nhom"]
                if n["category"] == "LTT_APPS")["nut"]
    assert "app.transcript.run" not in {x["type"] for x in apps}
