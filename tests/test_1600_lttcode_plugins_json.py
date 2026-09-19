"""LTTCODE — `/lttcode/plugins.json`: danh mục `dshmarket` cho `DSHM_REGISTRY_URL`.

App LTTCODE trên máy người dùng trỏ thẳng vào route này (`sidecar.rs`,
`desktop/sidecar/market/plugins.json` ở kho LTTCODEAPP) trước và độc lập với
mọi tài khoản — không đăng nhập, không khoá API, cùng luật với các route khác
trong `routes.py`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import apps.lttcode.routes  # noqa: F401  (gắn test vào thành phần app:lttcode)

_NGUON = Path(__file__).resolve().parent.parent / "apps" / "lttcode" / "plugins.json"


@pytest.fixture()
def may(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'lc.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(data))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "lttcode-test-secret")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from server.app import create_app

    client = TestClient(create_app(), base_url="https://testserver")
    try:
        yield client, data
    finally:
        dbmod.reset_engine()


def test_tra_200_json_hop_le_khong_can_dang_nhap(may):
    client, _ = may
    r = client.get("/lttcode/plugins.json")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/json")
    body = r.json()
    assert isinstance(body.get("plugins"), list) and len(body["plugins"]) == body["count"]


def test_khop_dung_tep_nguon(may):
    client, _ = may
    r = client.get("/lttcode/plugins.json")
    assert r.json() == json.loads(_NGUON.read_text(encoding="utf-8"))


def test_cache_control_mac_dinh_no_store(may):
    # Middleware chung (server/app.py) ghi đè Cache-Control cho mọi path ngoài
    # /static//nexus/dl/ — route này không tự đặt gì khác (xem routes.py).
    client, _ = may
    r = client.get("/lttcode/plugins.json")
    assert r.headers.get("cache-control") == "no-store"
