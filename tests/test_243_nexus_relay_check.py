"""Nexus Model B (Q101 / cưỡng chế relay) — hbbs hỏi platform "ID này trả phí chưa?"

Răng thật của thu phí: relay LTT (hbbs đã fork) hỏi `/nexus-agent/relay-check`
trước khi môi giới kết nối. Test chốt: chưa cấu hình bí mật → 404 (fail-closed
cấu hình); sai bí mật → 401; ID lạ → cho qua (fail-open dữ liệu, không do LTT
quản); ID đã đăng ký + chưa trả (có giá) → chặn.
"""
from __future__ import annotations

import json
import time

import pytest
from fastapi.testclient import TestClient

PASSWORD = "test-mat-khau-relay-0123456789"
SECRET = "relay-shared-secret-xyz"


@pytest.fixture()
def app_bat(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'relay.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "relay-secret-value")
    monkeypatch.setenv("LTT_NEXUS", "1")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    monkeypatch.delenv("LTT_NEXUS_GIA_MAY_THANG", raising=False)

    from platform_core.public_api import limits
    limits.reset()
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from server.app import create_app

    client = TestClient(create_app(), base_url="https://testserver")
    try:
        yield client
    finally:
        limits.reset()
        dbmod.reset_engine()


def _register(client, email="relay@example.com"):
    from platform_core.db import get_session
    from platform_core.nexus import agent_auth
    from platform_core.users import tao_nguoi_dung

    gen = get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email=email, password=PASSWORD, is_verified=True)
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass
    priv, pub = agent_auth.new_keypair_for_test()
    r = client.post("/nexus-agent/client-register",
                    json={"email": email, "password": PASSWORD,
                          "public_key": pub, "platform": "windows"})
    assert r.status_code == 200, r.text
    return r.json()["device_id"], priv


def _report_id(client, device_id, priv, rid):
    from platform_core.nexus import agent_auth
    path = "/nexus-agent/status"
    body = json.dumps({"rustdesk_id": rid}).encode("utf-8")
    ts = str(int(time.time()))
    sig = agent_auth.sign(priv, method="POST", path=path, timestamp=ts, body=body)
    return client.post(path, content=body, headers={
        agent_auth.HEADER_DEVICE: device_id,
        agent_auth.HEADER_TIMESTAMP: ts,
        agent_auth.HEADER_SIGNATURE: sig,
        "Content-Type": "application/json"})


# ── Domain ───────────────────────────────────────────────────────────────────

def test_dat_va_tim_theo_rustdesk_id(app_bat):
    from platform_core.db import get_session
    from platform_core.nexus import devices

    device_id, _priv = _register(app_bat)
    gen = get_session(); db = next(gen)
    try:
        dev = db.get(devices.NexusDevice, device_id)
        assert devices.dat_rustdesk_id(db, dev, rustdesk_id="224404082") is True
        assert devices.dat_rustdesk_id(db, dev, rustdesk_id="224404082") is False
        found = devices.tim_theo_rustdesk_id(db, rustdesk_id="224404082")
        assert found is not None and found.id == device_id
        assert devices.tim_theo_rustdesk_id(db, rustdesk_id="000") is None
    finally:
        try: next(gen)
        except StopIteration: pass


# ── /relay-check ─────────────────────────────────────────────────────────────

def test_chua_cau_hinh_bi_mat_thi_404(app_bat, monkeypatch):
    monkeypatch.delenv("LTT_NEXUS_RELAY_SECRET", raising=False)
    r = app_bat.get("/nexus-agent/relay-check", params={"id": "1"})
    assert r.status_code == 404


def test_sai_bi_mat_thi_401(app_bat, monkeypatch):
    monkeypatch.setenv("LTT_NEXUS_RELAY_SECRET", SECRET)
    r = app_bat.get("/nexus-agent/relay-check", params={"id": "1"},
                    headers={"X-LTT-Relay-Secret": "sai"})
    assert r.status_code == 401


def test_id_la_thi_cho_qua(app_bat, monkeypatch):
    monkeypatch.setenv("LTT_NEXUS_RELAY_SECRET", SECRET)
    r = app_bat.get("/nexus-agent/relay-check", params={"id": "999"},
                    headers={"X-LTT-Relay-Secret": SECRET})
    assert r.status_code == 200
    assert r.json() == {"allowed": True, "managed": False}


def test_da_dang_ky_mien_phi_thi_cho_qua(app_bat, monkeypatch):
    device_id, priv = _register(app_bat)
    assert _report_id(app_bat, device_id, priv, "224404082").status_code == 200
    monkeypatch.setenv("LTT_NEXUS_RELAY_SECRET", SECRET)
    r = app_bat.get("/nexus-agent/relay-check", params={"id": "224404082"},
                    headers={"X-LTT-Relay-Secret": SECRET})
    assert r.status_code == 200
    assert r.json()["allowed"] is True
    assert r.json()["managed"] is True


def test_co_gia_chua_tra_thi_chan(app_bat, monkeypatch):
    device_id, priv = _register(app_bat)
    assert _report_id(app_bat, device_id, priv, "293017172").status_code == 200
    monkeypatch.setenv("LTT_NEXUS_GIA_MAY_THANG", "50")   # có giá + chưa trả
    monkeypatch.setenv("LTT_NEXUS_RELAY_SECRET", SECRET)
    r = app_bat.get("/nexus-agent/relay-check", params={"id": "293017172"},
                    headers={"X-LTT-Relay-Secret": SECRET})
    assert r.status_code == 200
    assert r.json()["allowed"] is False
    assert r.json()["managed"] is True
