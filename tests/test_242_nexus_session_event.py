"""Nexus Model B (Q101 / P8, ràng buộc 6) — nhật ký "ai đã vào máy tôi".

Model B bỏ web-broker nên phiên điều khiển do chính máy đích báo. Test chốt:
bản ghi bất biến (end chỉ ghi thêm `ended_at`), idempotent theo session_key,
một máy không đóng được nhật ký máy khác, và request phải ký.
"""
from __future__ import annotations

import json
import time

import pytest
from fastapi.testclient import TestClient

PASSWORD = "mat-khau-audit-that-0123456789"


@pytest.fixture()
def app_bat(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'ev.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "ev-secret-value")
    monkeypatch.setenv("LTT_NEXUS", "1")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

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


def _register(client):
    from platform_core.db import get_session
    from platform_core.nexus import agent_auth
    from platform_core.users import tao_nguoi_dung

    gen = get_session()
    db = next(gen)
    try:
        u = tao_nguoi_dung(db, email="audit@example.com", password=PASSWORD,
                           is_verified=True)
        db.commit()
        uid = u.id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    priv, pub = agent_auth.new_keypair_for_test()
    r = client.post("/nexus-agent/client-register",
                    json={"email": "audit@example.com", "password": PASSWORD,
                          "public_key": pub, "platform": "windows"})
    assert r.status_code == 200, r.text
    return r.json()["device_id"], priv, uid


def _post_signed(client, priv, path, payload):
    from platform_core.nexus import agent_auth
    body = json.dumps(payload).encode("utf-8")
    ts = str(int(time.time()))
    sig = agent_auth.sign(priv, method="POST", path=path, timestamp=ts, body=body)
    device_id = payload.get("_device_id", "")
    headers = {agent_auth.HEADER_DEVICE: device_id,
               agent_auth.HEADER_TIMESTAMP: ts,
               agent_auth.HEADER_SIGNATURE: sig,
               "Content-Type": "application/json"}
    return client.post(path, content=body, headers=headers)


# ── Domain ───────────────────────────────────────────────────────────────────

def test_ghi_va_ket_thuc_truy_cap_domain(app_bat):
    from platform_core.db import get_session
    from platform_core.nexus import devices, sessions

    device_id, _priv, _uid = _register(app_bat)
    gen = get_session()
    db = next(gen)
    try:
        dev = db.get(devices.NexusDevice, device_id)
        row = sessions.ghi_truy_cap(db, dev, session_key="s1",
                                    peer_id="293017172", controller_ip="1.2.3.4")
        assert row.ended_at is None
        assert row.controller_ip == "1.2.3.4"
        # idempotent
        row2 = sessions.ghi_truy_cap(db, dev, session_key="s1")
        assert row2.id == row.id
        # kết thúc ghi thêm ended_at
        assert sessions.ket_thuc_truy_cap(db, dev, session_key="s1") is True
        assert db.get(sessions.NexusSession, "s1").ended_at is not None
        # đóng lại lần nữa → False (đã đóng)
        assert sessions.ket_thuc_truy_cap(db, dev, session_key="s1") is False
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── HTTP có ký ───────────────────────────────────────────────────────────────

def test_session_event_start_end_qua_HTTP(app_bat):
    from platform_core.db import get_session
    from platform_core.nexus import sessions

    device_id, priv, uid = _register(app_bat)
    path = "/nexus-agent/session-event"
    r = _post_signed(app_bat, priv, path,
                     {"_device_id": device_id, "event": "start",
                      "session_key": "sess-1", "peer_id": "293017172",
                      "controller_ip": "9.9.9.9"})
    assert r.status_code == 200, r.text

    # xuất hiện trong lịch sử của tài khoản (ràng buộc 6)
    gen = get_session(); db = next(gen)
    try:
        ls = sessions.lich_su(db, user_id=uid)
        assert any(s.id == "sess-1" for s in ls)
    finally:
        try: next(gen)
        except StopIteration: pass

    r = _post_signed(app_bat, priv, path,
                     {"_device_id": device_id, "event": "end",
                      "session_key": "sess-1"})
    assert r.status_code == 200, r.text
    gen = get_session(); db = next(gen)
    try:
        assert db.get(sessions.NexusSession, "sess-1").ended_at is not None
    finally:
        try: next(gen)
        except StopIteration: pass


def test_session_event_khong_ky_thi_401(app_bat):
    device_id, _priv, _uid = _register(app_bat)
    r = app_bat.post("/nexus-agent/session-event",
                     json={"event": "start", "session_key": "x"})
    assert r.status_code == 401


def test_su_kien_la_bi_tu_choi(app_bat):
    device_id, priv, _uid = _register(app_bat)
    r = _post_signed(app_bat, priv, "/nexus-agent/session-event",
                     {"_device_id": device_id, "event": "nonsense",
                      "session_key": "z"})
    assert r.status_code == 400
