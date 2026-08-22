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
                                  "url": "/nexus/dl/LTTNexus.zip",
                                  "sha256": "deadbeef", "kind": "zip"}},
    }), encoding="utf-8")
    r = client.get("/tai-xuong")
    assert r.status_code == 200
    assert "Tải xuống" in r.text
    assert "deadbeef" in r.text


def test_dl_phuc_vu_file_that(app_bat):
    """Thả file vào data/nexus_dist/ → /nexus/dl/<tên> trả đúng nội dung + type."""
    client, tmp_path = app_bat
    dist = tmp_path / "data" / "nexus_dist"
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "LTTNexus-1.0.0-android-arm64.apk").write_bytes(b"PK\x03\x04apkbytes")
    r = client.get("/nexus/dl/LTTNexus-1.0.0-android-arm64.apk")
    assert r.status_code == 200, r.text
    assert r.content == b"PK\x03\x04apkbytes"
    assert r.headers["content-type"] == "application/vnd.android.package-archive"
    assert "immutable" in r.headers.get("cache-control", "")


def test_dl_khong_co_file_tra_404(app_bat):
    client, _ = app_bat
    r = client.get("/nexus/dl/khong-ton-tai.zip")
    assert r.status_code == 404


@pytest.mark.parametrize("bad", [
    "..%2f..%2fsecrets%2fapp.env",   # path traversal đã encode
    "a/b.zip",                        # có gạch chéo
    ".hidden",                        # bắt đầu bằng dấu chấm
    "con;rm.zip",                     # ký tự lạ
])
def test_dl_chan_path_traversal(app_bat, bad):
    client, tmp_path = app_bat
    # tạo một file "mồi" ngoài dist để chắc chắn không rò
    (tmp_path / "data" / "secret.txt").write_text("top-secret", encoding="utf-8")
    r = client.get(f"/nexus/dl/{bad}")
    assert r.status_code == 404
    assert "top-secret" not in r.text


# ── Cài thẳng từ Safari (itms-services) — chỉ khi IPA đã ký ──────────────────

def test_manifest_ios_404_khi_chua_ky(app_bat):
    """Chưa có chữ ký phân phối thì KHÔNG được đưa ra link itms-services.

    Bấm vào một link như vậy sẽ không có chuyện gì xảy ra — người dùng tưởng
    app hỏng. Thà không hiện nút còn hơn hiện một nút chết.
    """
    client, tmp_path = app_bat
    (tmp_path / "data" / "nexus_versions.json").write_text(json.dumps({
        "platforms": {"ios": {"available": True, "url": "/nexus/dl/a.ipa",
                              "signed": False}},
    }), encoding="utf-8")
    assert client.get("/nexus/ios-manifest.plist").status_code == 404


def test_manifest_ios_khi_da_ky(app_bat):
    client, tmp_path = app_bat
    (tmp_path / "data" / "nexus_versions.json").write_text(json.dumps({
        "version": "2.0.0",
        "platforms": {"ios": {"available": True, "signed": True,
                              "url": "/nexus/dl/LTTNexus-2.0.0-ios.ipa"}},
    }), encoding="utf-8")
    r = client.get("/nexus/ios-manifest.plist")
    assert r.status_code == 200, r.text
    body = r.text
    # iOS doi URL TUYET DOI + https, khong nhan duong dan tuong doi
    assert "https://testserver/nexus/dl/LTTNexus-2.0.0-ios.ipa" in body
    assert "com.lttstudios.nexus" in body       # phai trung CFBundleIdentifier
    assert "<key>kind</key><string>software</string>" in body
    assert "2.0.0" in body
    assert r.headers["content-type"].startswith("application/xml")


def test_trang_hien_nut_cai_iphone_khi_da_ky(app_bat):
    client, tmp_path = app_bat
    (tmp_path / "data" / "nexus_versions.json").write_text(json.dumps({
        "platforms": {"ios": {"label": "iOS", "available": True, "signed": True,
                              "url": "/nexus/dl/x.ipa"}},
    }), encoding="utf-8")
    html = client.get("/tai-xuong").text
    assert "itms-services://" in html
    assert "Cài lên iPhone" in html
    assert "Safari" in html                    # nhac dung Safari


def test_trang_KHONG_hien_nut_cai_khi_chua_ky(app_bat):
    client, tmp_path = app_bat
    (tmp_path / "data" / "nexus_versions.json").write_text(json.dumps({
        "platforms": {"ios": {"label": "iOS", "available": True, "signed": False,
                              "url": "/nexus/dl/x.ipa"}},
    }), encoding="utf-8")
    html = client.get("/tai-xuong").text
    assert "itms-services://" not in html
    assert "Tải xuống" in html                 # van tai file ve duoc
