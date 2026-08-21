"""Trang tải LTT Nexus + version.json (Model B, Q101: web = hướng dẫn/tải).

Công khai, không phụ thuộc cờ LTT_NEXUS. Test chốt: trang render 4 nền tảng;
version.json là JSON hợp lệ; và manifest đọc đè từ data/nexus_versions.json.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def app_bat(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'dl.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "dl-secret-value")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from server.app import create_app

    client = TestClient(create_app(), base_url="https://testserver")
    try:
        yield client, tmp_path
    finally:
        dbmod.reset_engine()


def test_manifest_mac_dinh_co_4_nen_tang():
    from platform_core.nexus import versions

    m = versions.manifest()
    assert set(m["platforms"]) == {"windows", "macos", "ios", "android"}
    assert m["version"]


def test_manifest_doc_de_tu_data_file(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path))
    (tmp_path / "nexus_versions.json").write_text(json.dumps({
        "version": "9.9.9",
        "platforms": {"windows": {"available": True, "url": "https://x/y.zip",
                                  "sha256": "abc"}},
    }), encoding="utf-8")
    from platform_core.nexus import versions

    m = versions.manifest()
    assert m["version"] == "9.9.9"
    assert m["platforms"]["windows"]["available"] is True
    assert m["platforms"]["windows"]["url"] == "https://x/y.zip"
    # nền tảng không khai vẫn giữ mặc định (không mất)
    assert m["platforms"]["android"]["available"] is False


def test_trang_tai_render(app_bat):
    client, _ = app_bat
    r = client.get("/tai-xuong")
    assert r.status_code == 200, r.text
    body = r.text
    assert "LTT Nexus" in body
    assert "Windows" in body and "macOS" in body and "Android" in body
    assert "Đang chuẩn bị" in body        # mặc định chưa có URL


def test_version_json(app_bat):
    client, _ = app_bat
    r = client.get("/nexus/version.json")
    assert r.status_code == 200, r.text
    j = r.json()
    assert "version" in j and "platforms" in j
    assert set(j["platforms"]) == {"windows", "macos", "ios", "android"}


def test_trang_tai_hien_nut_tai_khi_co_url(app_bat, monkeypatch):
    client, tmp_path = app_bat
    (tmp_path / "data" / "nexus_versions.json").write_text(json.dumps({
        "version": "1.0.0",
        "platforms": {"windows": {"label": "Windows 10/11 (64-bit)",
                                  "available": True,
                                  "url": "https://dl.lttstudios.com/LTTNexus.zip",
                                  "sha256": "deadbeef", "kind": "zip"}},
    }), encoding="utf-8")
    r = client.get("/tai-xuong")
    assert r.status_code == 200
    assert "Tải xuống" in r.text
    assert "deadbeef" in r.text
