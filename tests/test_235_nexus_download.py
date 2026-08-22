"""Nexus N3.3b — trang tải: đọc bản phát hành + nói trước cảnh báo SmartScreen.

Hai tầng test: `release.ban_phat_hanh_hien_tai` (đọc file, fail-safe) và trang
`/nexus/tai` render thật qua app. Trang tải là chỗ Q95 đặt hai nghĩa vụ cụ thể —
công bố SHA-256 và nói trước cảnh báo — nên hai thứ đó được chốt bằng test, không
để trôi vào một lần sửa template sau này.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PASSWORD = "mat-khau-test-rat-dai-0123456789"

VALID = {
    "version": "1.2.0",
    "sha256": "a" * 64,
    "url": "https://app.lttstudios.com/nexus/tai/nexus-agent-1.2.0.zip",
    "size": 12345678,
    "signature": "khong-quan-trong-o-tang-hien-thi",
}


# ── release.ban_phat_hanh_hien_tai — fail-safe ──────────────────────────────

def test_thieu_file_tra_None(tmp_path, monkeypatch):
    from platform_core.nexus import release
    monkeypatch.setenv("LTT_NEXUS_RELEASE_MANIFEST",
                       str(tmp_path / "khong_co.json"))
    assert release.ban_phat_hanh_hien_tai() is None


def test_json_hong_tra_None_khong_nem(tmp_path, monkeypatch):
    from platform_core.nexus import release
    p = tmp_path / "m.json"
    p.write_text("{ khong phai json", encoding="utf-8")
    monkeypatch.setenv("LTT_NEXUS_RELEASE_MANIFEST", str(p))
    assert release.ban_phat_hanh_hien_tai() is None


def test_thieu_truong_tra_None(tmp_path, monkeypatch):
    from platform_core.nexus import release
    p = tmp_path / "m.json"
    thieu = dict(VALID); thieu.pop("sha256")
    p.write_text(json.dumps(thieu), encoding="utf-8")
    monkeypatch.setenv("LTT_NEXUS_RELEASE_MANIFEST", str(p))
    assert release.ban_phat_hanh_hien_tai() is None


def test_hop_le_tra_dict(tmp_path, monkeypatch):
    from platform_core.nexus import release
    p = tmp_path / "m.json"
    p.write_text(json.dumps(VALID), encoding="utf-8")
    monkeypatch.setenv("LTT_NEXUS_RELEASE_MANIFEST", str(p))
    m = release.ban_phat_hanh_hien_tai()
    assert m is not None and m["version"] == "1.2.0"


# ── /nexus/tai render thật ──────────────────────────────────────────────────

@pytest.fixture()
def app_bat(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'tai.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "tai-secret-value")
    monkeypatch.setenv("LTT_NEXUS", "1")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    monkeypatch.delenv("LTT_NEXUS_RELEASE_MANIFEST", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    import importlib
    import apps.nexus.manifest as manifest_mod
    importlib.reload(manifest_mod)
    import apps.nexus.routes as routes_mod
    importlib.reload(routes_mod)

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver")
    client._data_dir = tmp_path / "data"       # de test ghi manifest dung cho
    try:
        yield client
    finally:
        dbmod.reset_engine()


def _csrf(html: str) -> str:
    found = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    assert found
    return found.group(1)


def _dang_nhap(client) -> None:
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung
    gen = get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email="tai@example.com", password=PASSWORD,
                       is_verified=True)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    page = client.get("/login").text
    r = client.post("/login", data={"username": "tai@example.com",
                    "password": PASSWORD, "csrf_token": _csrf(page)},
                    follow_redirects=False)
    assert r.status_code == 303


def _ghi_manifest(client) -> None:
    d = Path(client._data_dir) / "nexus"
    d.mkdir(parents=True, exist_ok=True)
    (d / "release_manifest.json").write_text(json.dumps(VALID), encoding="utf-8")


# Hai test dưới đo trang `/nexus/tai` của bảng điều khiển web-broker. Từ khi
# `/nexus` đổi thành trang giới thiệu (Q101/A7), bề mặt đó nằm sau cờ
# `LTT_NEXUS_WEB_BROKER` và mặc định TẮT — nên phải bật cờ mới đo được. Giữ lại
# thay vì xoá: cờ còn thì hành vi sau cờ vẫn phải đúng.


def test_co_ban_thi_hien_sha256_va_canh_bao_smartscreen(app_bat, monkeypatch):
    monkeypatch.setenv("LTT_NEXUS_WEB_BROKER", "1")
    _dang_nhap(app_bat)
    _ghi_manifest(app_bat)
    r = app_bat.get("/nexus/tai")
    assert r.status_code == 200, r.text[:400]
    # Q95: SHA-256 phai co mat de khach doi chieu.
    assert VALID["sha256"] in r.text
    # Q95: noi truoc canh bao SmartScreen bang ten no thay.
    assert "SmartScreen" in r.text or "Windows protected your PC" in r.text
    # Canh bao T1: dung doc ma ghep qua dien thoai.
    assert "qua điện thoại" in r.text
    # Nut tai tro dung URL trong manifest.
    assert VALID["url"] in r.text


def test_chua_co_ban_thi_noi_that_khong_gay(app_bat, monkeypatch):
    monkeypatch.setenv("LTT_NEXUS_WEB_BROKER", "1")
    _dang_nhap(app_bat)
    # KHONG ghi manifest -> None
    r = app_bat.get("/nexus/tai")
    assert r.status_code == 200, r.text[:400]
    assert "Chưa có bản phát hành" in r.text
    # Khong hien nut tai gay khi chua co ban.
    assert "nexus-agent-1.2.0.zip" not in r.text


def test_co_tat_thi_404(tmp_path, monkeypatch):
    """Cờ LTT_NEXUS tắt → /nexus/tai trả 404, không lộ bề mặt.

    Phải ĐĂNG NHẬP trước: `require_login` chạy trước handler, nên nếu không đăng
    nhập thì ta chỉ đo được chuyển hướng tới /login, không đo được lớp chặn 404
    của chính route. 404 (không phải 403) là có chủ ý — xem `_bat_buoc_bat`.
    """
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'off.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "off-secret-value")
    monkeypatch.setenv("LTT_NEXUS", "0")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    import importlib
    import apps.nexus.manifest as manifest_mod
    importlib.reload(manifest_mod)
    import apps.nexus.routes as routes_mod
    importlib.reload(routes_mod)
    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver")
    try:
        _dang_nhap(client)          # login la platform-level, khong phu thuoc co
        r = client.get("/nexus/tai", follow_redirects=False)
        assert r.status_code == 404, r.text[:300]
    finally:
        dbmod.reset_engine()
