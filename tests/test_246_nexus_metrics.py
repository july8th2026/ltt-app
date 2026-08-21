"""Số liệu vận hành Nexus — đếm sự kiện + khối tóm tắt trên trang tình trạng.

Vì sao cần: trước cái này người vận hành không có cách nào biết có bao nhiêu máy
đã ghép, bao nhiêu đang bật, hay có ai bị relay chặn vì hết credit — tức là bán
một dịch vụ mà không nhìn thấy nó chạy. Test chốt: bộ đếm có tăng, và khối tóm
tắt không bao giờ làm vỡ trang tình trạng.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

PASSWORD = "test-mat-khau-metric-0123456789"
SECRET = "test-relay-secret-metric-xyz"


@pytest.fixture()
def app_bat(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'met.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "met-secret-value")
    monkeypatch.setenv("LTT_NEXUS", "1")
    monkeypatch.setenv("LTT_NEXUS_RELAY_SECRET", SECRET)
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    monkeypatch.delenv("LTT_NEXUS_GIA_MAY_THANG", raising=False)

    from platform_core.public_api import limits, metrics
    limits.reset()
    metrics.reset()

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
        metrics.reset()
        dbmod.reset_engine()


def _tao_user(email: str = "m@example.com"):
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung

    gen = get_session(); db = next(gen)
    try:
        u = tao_nguoi_dung(db, email=email, password=PASSWORD, is_verified=True)
        db.commit()
        return u.id
    finally:
        try: next(gen)
        except StopIteration: pass


def _dang_ky(client, email: str = "m@example.com"):
    from platform_core.nexus import agent_auth

    priv, pub = agent_auth.new_keypair_for_test()
    r = client.post("/nexus-agent/client-register",
                    json={"email": email, "password": PASSWORD,
                          "public_key": pub, "display_name": "May",
                          "platform": "windows"})
    assert r.status_code == 200, r.text
    return r.json()["device_id"], priv


def _dem() -> dict:
    from platform_core.public_api import metrics
    snap = metrics.snapshot()
    return snap.get("counters", snap) if isinstance(snap, dict) else {}


# ── Bộ đếm ───────────────────────────────────────────────────────────────────

def test_dang_ky_may_thi_tang_bo_dem(app_bat):
    _tao_user()
    _dang_ky(app_bat)
    assert _dem().get("nexus:dang_ky_may", 0) >= 1


def test_relay_cho_qua_va_bi_chan_duoc_dem_rieng(app_bat, monkeypatch):
    """Con số quan trọng nhất của billing: bao nhiêu lượt bị chặn vì chưa trả."""
    import time

    from platform_core.nexus import agent_auth

    _tao_user()
    did, priv = _dang_ky(app_bat)

    # gắn rustdesk_id cho máy (qua /status có ký)
    path = "/nexus-agent/status"
    body = b'{"rustdesk_id":"123456789"}'
    ts = str(int(time.time()))
    sig = agent_auth.sign(priv, method="POST", path=path, timestamp=ts, body=body)
    r = app_bat.post(path, content=body, headers={
        agent_auth.HEADER_DEVICE: did, agent_auth.HEADER_TIMESTAMP: ts,
        agent_auth.HEADER_SIGNATURE: sig,
        "Content-Type": "application/json"})
    assert r.status_code == 200, r.text

    hdr = {"X-LTT-Relay-Secret": SECRET}
    # miễn phí → cho qua
    r1 = app_bat.get("/nexus-agent/relay-check?id=123456789", headers=hdr)
    assert r1.status_code == 200 and r1.json()["allowed"] is True
    assert _dem().get("nexus:relay_cho_qua", 0) >= 1

    # có giá mà chưa trả → chặn
    monkeypatch.setenv("LTT_NEXUS_GIA_MAY_THANG", "50")
    r2 = app_bat.get("/nexus-agent/relay-check?id=123456789", headers=hdr)
    assert r2.status_code == 200 and r2.json()["allowed"] is False
    assert _dem().get("nexus:relay_chan", 0) >= 1


def test_bo_dem_hong_khong_lam_hong_duong_phuc_vu(app_bat, monkeypatch):
    """Số liệu là thứ yếu: nó hỏng thì khách vẫn phải đăng ký được."""
    from platform_core.public_api import metrics

    def no(*a, **k):
        raise RuntimeError("metrics down")

    monkeypatch.setattr(metrics, "increment", no)
    _tao_user()
    _dang_ky(app_bat)          # không được ném


# ── Khối tóm tắt trên trang tình trạng ───────────────────────────────────────

def test_tom_tat_nexus_dem_dung_so_may(app_bat):
    from server.routes.status import _tom_tat_nexus

    _tao_user()
    _dang_ky(app_bat)
    tt = _tom_tat_nexus()
    assert tt is not None
    assert tt["may"] == 1
    assert tt["thu_hoi"] == 0
    assert "phien" in tt


def test_tom_tat_none_khi_nexus_tat(app_bat, monkeypatch):
    from server.routes.status import _tom_tat_nexus

    monkeypatch.setenv("LTT_NEXUS", "0")
    assert _tom_tat_nexus() is None


def test_tom_tat_hong_thi_tra_loi_chu_khong_nem(app_bat, monkeypatch):
    """Trang tình trạng phải mở được ngay cả khi phần Nexus hỏng."""
    import platform_core.db as dbmod
    from server.routes import status as status_mod

    def no(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(dbmod, "get_session", no)
    tt = status_mod._tom_tat_nexus()
    assert tt is not None and tt.get("loi")


# ── Cảnh báo khi relay im lặng ───────────────────────────────────────────────

def test_tham_relay_khong_khai_dia_chi_thi_khong_bao(app_bat, monkeypatch):
    """Chưa khai địa chỉ relay → không đoán, không báo động giả."""
    from platform_core.job_runner import _tham_relay_nexus

    monkeypatch.delenv("LTT_NEXUS_RELAY_HOST", raising=False)
    assert _tham_relay_nexus() is True
    assert _dem().get("nexus:relay_im_lang", 0) == 0


def test_tham_relay_chet_thi_dem_de_canh_bao_bay(app_bat, monkeypatch):
    """Relay không nghe → đếm, để ngưỡng ở ops_alerts bắn thư cho người trực."""
    from platform_core.job_runner import _tham_relay_nexus

    # cổng 9 (discard) hiếm khi mở; địa chỉ loopback nên không ra ngoài mạng
    monkeypatch.setenv("LTT_NEXUS_RELAY_HOST", "127.0.0.1:9")
    assert _tham_relay_nexus() is False
    assert _dem().get("nexus:relay_im_lang", 0) >= 1


def test_tham_relay_song_thi_khong_dem(app_bat, monkeypatch):
    import socket
    import threading

    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    cong = srv.getsockname()[1]
    threading.Thread(target=lambda: srv.accept(), daemon=True).start()
    try:
        from platform_core.job_runner import _tham_relay_nexus

        monkeypatch.setenv("LTT_NEXUS_RELAY_HOST", f"127.0.0.1:{cong}")
        assert _tham_relay_nexus() is True
        assert _dem().get("nexus:relay_im_lang", 0) == 0
    finally:
        srv.close()


def test_tat_nexus_thi_khong_tham_relay(app_bat, monkeypatch):
    from platform_core.job_runner import _tham_relay_nexus

    monkeypatch.setenv("LTT_NEXUS", "0")
    monkeypatch.setenv("LTT_NEXUS_RELAY_HOST", "127.0.0.1:9")
    assert _tham_relay_nexus() is True
    assert _dem().get("nexus:relay_im_lang", 0) == 0


def test_nguong_canh_bao_relay_da_khai(app_bat):
    """Đếm mà không có ngưỡng thì không ai được báo — chốt cả hai đi cùng nhau."""
    from platform_core.public_api import ops_alerts

    assert "nexus:relay_im_lang" in ops_alerts.NGUONG
    gan = {"counters": {"nexus:relay_im_lang": 5}}
    truoc = {"counters": {}}
    ten = [d["ten"] for d in ops_alerts.danh_gia(gan, truoc)]
    assert "nexus:relay_im_lang" in ten
