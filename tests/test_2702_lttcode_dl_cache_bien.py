"""Bo cai LTTCODE phai duoc bien (Cloudflare) cache - do 23/09: 279MB phuc vu voi
no-store / BYPASS, moi luot tai keo tron qua tunnel. `/nexus/dl/` da co ngoai le
nay (cong khai, giong het moi nguoi, version trong ten file) - `/lttcode/dl/`
dung dung ly le do (xem test_1301_lttcode_routes.py: khong doi hoi dang nhap).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import apps.lttcode.routes  # noqa: F401  (gan test vao thanh phan app:lttcode)


@pytest.fixture()
def may(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'lc.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(data))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "lttcode-dl-cache-secret")
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


def test_bo_cai_lttcode_duoc_cache_immutable_o_bien(may):
    client, data = may
    dist = data / "lttcode_dist"
    dist.mkdir()
    (dist / "LTTCODE_0.2.0_x64-setup.exe").write_bytes(b"MZ-fake-installer")

    r = client.get("/lttcode/dl/LTTCODE_0.2.0_x64-setup.exe")
    assert r.status_code == 200
    cc = r.headers.get("cache-control", "")
    assert "immutable" in cc
    assert "no-store" not in cc


def test_duong_khac_ngoai_dl_van_no_store(may):
    """Chi /lttcode/dl/ duoc mo, khong phai ca app /lttcode/... — vd trang cong khai."""
    client, _ = may
    r = client.get("/lttcode")
    assert r.status_code == 200
    assert r.headers.get("cache-control") == "no-store"
