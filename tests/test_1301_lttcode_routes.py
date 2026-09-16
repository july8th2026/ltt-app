"""LTTCODE — route công khai của kênh phát hành (spec updater LTTCODEAPP §2).

Không route nào đòi đăng nhập: app LTTCODE trên máy người dùng hỏi cập nhật
khi chưa có (và không bao giờ gửi) tài khoản hay khoá API.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import apps.lttcode.routes  # noqa: F401  (gắn test vào thành phần app:lttcode)

IID = "3f2b8c1e-6a4d-4e2f-9b1a-0c5d7e8f9a10"


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


def _ghi_manifest(data, **ban):
    r = {"version": "0.2.0", "pub_date": "2026-09-20T10:00:00Z", "file": "LTTCODE_0.2.0_x64-setup.exe",
         "signature": "sig", "sha256": "ab" * 32, "notes": "ghi chu", "rollout_percent": 100,
         "session_format": 3, "revoked": False}
    r.update(ban)
    (data / "lttcode_releases.json").write_text(json.dumps(
        {"channels": {"stable": {"kill_switch": False, "min_version": "0.0.0", "releases": [r]}}}),
        encoding="utf-8")


def test_cap_nhat_co_ban_moi_khong_can_dang_nhap(may):
    client, data = may
    _ghi_manifest(data)
    r = client.get("/lttcode/update/stable/windows/x86_64/0.1.0", headers={"X-LTTCODE-Install-Id": IID})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["version"] == "0.2.0"
    assert body["url"] == "https://testserver/lttcode/dl/LTTCODE_0.2.0_x64-setup.exe"
    assert body["signature"] == "sig" and body["mandatory"] is False
    assert "no-store" in r.headers.get("cache-control", "")


def test_khong_co_ban_moi_tra_204_rong(may):
    client, data = may
    _ghi_manifest(data)
    r = client.get("/lttcode/update/stable/windows/x86_64/0.2.0")
    assert r.status_code == 204 and r.content == b""


def test_chua_co_manifest_tra_204(may):
    client, _ = may
    assert client.get("/lttcode/update/stable/windows/x86_64/0.1.0").status_code == 204


def test_install_id_sai_dinh_dang_bi_bo_qua(may):
    client, data = may
    _ghi_manifest(data, rollout_percent=99)
    r = client.get("/lttcode/update/stable/windows/x86_64/0.1.0", headers={"X-LTTCODE-Install-Id": "khong-phai-uuid"})
    assert r.status_code == 204


def test_tham_so_sai(may):
    client, _ = may
    assert client.get("/lttcode/update/stable/linux/x86_64/0.1.0").status_code == 400
    assert client.get("/lttcode/update/nightly/windows/x86_64/0.1.0").status_code == 404


def test_tai_bo_cai_va_chan_thoat_thu_muc(may):
    client, data = may
    dist = data / "lttcode_dist"
    dist.mkdir()
    (dist / "LTTCODE_0.2.0_x64-setup.exe").write_bytes(b"MZ-fake-installer")
    (data / "bi_mat.txt").write_text("khong duoc lo", encoding="utf-8")

    r = client.get("/lttcode/dl/LTTCODE_0.2.0_x64-setup.exe")
    assert r.status_code == 200 and r.content == b"MZ-fake-installer"
    assert r.headers["content-type"].startswith("application/vnd.microsoft.portable-executable")
    assert client.head("/lttcode/dl/LTTCODE_0.2.0_x64-setup.exe").status_code == 200

    assert client.get("/lttcode/dl/..%2Fbi_mat.txt").status_code == 404
    assert client.get("/lttcode/dl/.hidden").status_code == 404
    assert client.get("/lttcode/dl/khong-co.exe").status_code == 404


def test_trang_tai_cong_khai(may):
    client, data = may
    r = client.get("/lttcode")
    assert r.status_code == 200, r.text
    _ghi_manifest(data)
    r = client.get("/lttcode")
    assert r.status_code == 200
    assert "0.2.0" in r.text
    assert "/lttcode/dl/LTTCODE_0.2.0_x64-setup.exe" in r.text
