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


#: macOS là HAI khoá, không phải một: bản Apple Silicon và bản Intel là hai file
#: `.dmg` **không thay thế nhau được**. Tách ở tầng khoá nền tảng thì cả trang tải
#: lẫn client tự-cập-nhật cùng chọn đúng mà không phải viết luật riêng ở hai nơi.
NEN_TANG = {"windows", "macos", "macos_intel", "ios", "android"}


def test_manifest_mac_dinh_co_du_nen_tang():
    from platform_core.nexus import versions

    m = versions.manifest()
    assert set(m["platforms"]) == NEN_TANG
    assert m["version"]
    # Thứ tự hiển thị phải phủ đúng các khoá — thiếu một khoá thì nền tảng đó có
    # file mà không bao giờ hiện ra trang tải, và hỏng lặng lẽ.
    assert set(versions.PLATFORM_ORDER) == NEN_TANG


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
    assert set(j["platforms"]) == NEN_TANG


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


# ── File cài một-file cho tự cập nhật ────────────────────────────────────────

def test_manifest_co_truong_setup_cho_tu_cap_nhat(app_bat):
    """Client đọc `setup_url`/`setup_sha256`; thiếu là không tự cập nhật được."""
    from platform_core.nexus import versions

    win = versions.manifest()["platforms"]["windows"]
    assert "setup_url" in win and "setup_sha256" in win


def test_dl_phuc_vu_file_exe_dung_content_type(app_bat):
    """File cài tải bằng client, không phải trình duyệt — nhưng content-type sai
    làm Cloudflare/proxy xử lý lạ, nên vẫn phải đúng."""
    client, tmp_path = app_bat
    dist = tmp_path / "data" / "nexus_dist"
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "LTTNexus-1.2.0-win-x64-setup.exe").write_bytes(b"MZ" + b"\x00" * 64)
    r = client.get("/nexus/dl/LTTNexus-1.2.0-win-x64-setup.exe")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/vnd.microsoft.portable-executable"
    assert r.content.startswith(b"MZ")


def test_setup_url_doc_de_tu_data_file(app_bat):
    client, tmp_path = app_bat
    (tmp_path / "data" / "nexus_versions.json").write_text(json.dumps({
        "version": "1.2.0",
        "platforms": {"windows": {
            "available": True, "kind": "zip",
            "url": "/nexus/dl/LTTNexus-1.2.0-win-x64.zip", "sha256": "a" * 64,
            "setup_url": "/nexus/dl/LTTNexus-1.2.0-win-x64-setup.exe",
            "setup_sha256": "b" * 64}},
    }), encoding="utf-8")
    j = client.get("/nexus/version.json").json()
    win = j["platforms"]["windows"]
    assert win["setup_url"].endswith("-setup.exe")
    assert len(win["setup_sha256"]) == 64


def test_trang_tai_moi_file_cai_TRUOC_ban_zip(app_bat):
    """Có file cài một-file thì trang phải mời cái đó trước, zip là lối phụ.

    Vì sao chốt bằng test: bản zip bắt người dùng tự giải nén đúng chỗ, và nó
    **không tự cập nhật sạch được** (không ghi đè nổi exe đang chạy, không biết
    thư mục cài ở đâu) — đó chính là lý do đường tự-cập-nhật tải `setup_url`.
    Để hai nút ngang nhau, hoặc chỉ có zip, là đẩy việc chọn sai sang người dùng.
    """
    client, tmp_path = app_bat
    (tmp_path / "data" / "nexus_versions.json").write_text(json.dumps({
        "version": "1.4.0",
        "platforms": {"windows": {
            "label": "Windows 10/11 (64-bit)", "available": True, "kind": "zip",
            "url": "/nexus/dl/LTTNexus-1.4.0-win-x64.zip", "sha256": "c" * 64,
            "setup_url": "/nexus/dl/LTTNexus-1.4.0-win-x64-setup.exe",
            "setup_sha256": "d" * 64}},
    }), encoding="utf-8")
    html = client.get("/tai-xuong").text
    assert "LTTNexus-1.4.0-win-x64-setup.exe" in html, "khong moi file cai"
    assert "d" * 64 in html, "thieu SHA-256 cua file cai"
    # Zip vẫn còn, nhưng là lối phụ.
    assert "LTTNexus-1.4.0-win-x64.zip" in html
    assert html.index("-setup.exe") < html.index("win-x64.zip"), \
        "zip dang duoc moi truoc file cai"


def test_khong_co_setup_url_thi_van_moi_zip_nhu_cu(app_bat):
    """Nền tảng chưa có file cài (Android/macOS) không được rơi vào trang trống."""
    client, tmp_path = app_bat
    (tmp_path / "data" / "nexus_versions.json").write_text(json.dumps({
        "version": "1.4.0",
        "platforms": {"android": {
            "label": "Android (arm64)", "available": True, "kind": "apk",
            "url": "/nexus/dl/LTTNexus-1.4.0-android.apk", "sha256": "e" * 64}},
    }), encoding="utf-8")
    html = client.get("/tai-xuong").text
    assert "LTTNexus-1.4.0-android.apk" in html
    assert "Tải xuống" in html


def test_khong_moi_hai_link_tro_cung_mot_file(app_bat):
    """macOS dùng CÙNG một `.dmg` cho `url` lẫn `setup_url`.

    Trang từng hiện cả nút "Tải file cài" lẫn dòng "Hoặc tải bản zip
    chạy-không-cài" trỏ đúng file đó. Hai lựa chọn nhìn như khác nhau mà thực ra
    là một — người đọc sẽ dừng lại cân nhắc một quyết định không tồn tại.
    """
    client, tmp_path = app_bat
    mot_file = "/nexus/dl/LTTNexus-1.4.0-macos-aarch64.dmg"
    (tmp_path / "data" / "nexus_versions.json").write_text(json.dumps({
        "version": "1.4.0",
        "platforms": {"macos": {
            "label": "macOS — Apple Silicon", "available": True, "kind": "dmg",
            "url": mot_file, "sha256": "f" * 64,
            "setup_url": mot_file, "setup_sha256": "f" * 64}},
    }), encoding="utf-8")
    html = client.get("/tai-xuong").text
    assert html.count(mot_file) == 1, "moi cung mot file hai lan"
    assert "chạy-không-cài" not in html
