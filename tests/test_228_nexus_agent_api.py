"""Nexus N2.6 — bề mặt cho agent: ký request, không dùng token.

Q93 ràng buộc 1 nói khoá riêng không bao giờ rời máy. Hệ quả kỹ thuật là agent
**không thể** dùng bearer token: token chép được, và chép được nghĩa là ai đọc
được ổ đĩa hay log của máy đó đều trở thành máy đó. Nên mỗi request được ký.

Bốn phần của chuỗi được ký đều load-bearing, và test ở đây bỏ từng phần một để
chứng minh điều đó — vì thiết kế này "vẫn chạy" trong lúc thử dù thiếu phần nào,
và chỉ sai khi có người tấn công.
"""
from __future__ import annotations

import json
import time

import pytest
from fastapi.testclient import TestClient

PASSWORD = "mat-khau-test-rat-dai-0123456789"


@pytest.fixture()
def app_bat(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'agent.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "agent-secret-value")
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


def _user_va_ma():
    """Tạo user + mã ghép, trả `(user_id, ma)`."""
    from platform_core.db import get_session
    from platform_core.nexus import devices
    from platform_core.users import tao_nguoi_dung

    gen = get_session()
    db = next(gen)
    try:
        user = tao_nguoi_dung(db, email="agent@example.com", password=PASSWORD,
                              is_verified=True)
        db.flush()
        _row, ma = devices.tao_ma_ghep(db, user_id=user.id)
        db.commit()
        return user.id, ma
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _ghep(client):
    """Ghép một máy thật. Trả `(device_id, private_bytes)`."""
    from platform_core.nexus import agent_auth

    _user_id, ma = _user_va_ma()
    priv, pub = agent_auth.new_keypair_for_test()
    r = client.post("/nexus-agent/enroll",
                    json={"code": ma, "public_key": pub,
                          "display_name": "May test", "platform": "windows"})
    assert r.status_code == 200, r.text
    return r.json()["device_id"], priv


def _ky(priv, method: str, path: str, body: bytes, *, moc: str = ""):
    from platform_core.nexus import agent_auth

    ts = moc or str(int(time.time()))
    sig = agent_auth.sign(priv, method=method, path=path,
                          timestamp=ts, body=body)
    return {agent_auth.HEADER_TIMESTAMP: ts,
            agent_auth.HEADER_SIGNATURE: sig}


# ── Ghép máy ─────────────────────────────────────────────────────────────────

def test_ghep_may_qua_HTTP(app_bat):
    device_id, _priv = _ghep(app_bat)
    assert device_id


def test_ma_sai_thi_400_va_khong_noi_vi_sao(app_bat):
    from platform_core.nexus import agent_auth

    _priv, pub = agent_auth.new_keypair_for_test()
    r = app_bat.post("/nexus-agent/enroll",
                     json={"code": "ZZZZZZZZ", "public_key": pub})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "enroll_failed"


def test_body_khong_phai_JSON_thi_400_chu_khong_500(app_bat):
    r = app_bat.post("/nexus-agent/enroll", content=b"khong phai json",
                     headers={"Content-Type": "application/json"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "invalid_request"


def test_tran_nhip_ghep_theo_IP(app_bat):
    """`devices.py` cố ý không tự giới hạn nhịp và nói rằng route phải làm.
    Đây là chỗ trả nợ câu đó — nếu quên, mã 40 bit trở thành thứ dò được."""
    from server.nexus import routes as agent_routes

    ma_429 = 0
    for _ in range(agent_routes.GHEP_MOI_PHUT + 3):
        r = app_bat.post("/nexus-agent/enroll",
                         json={"code": "ZZZZZZZZ", "public_key": "x"})
        if r.status_code == 429:
            ma_429 += 1
    assert ma_429 >= 1, "khong co tran nhip cho /enroll"


# ── Nhịp tim có ký ───────────────────────────────────────────────────────────

def test_nhip_tim_co_ky_thi_duoc(app_bat):
    from platform_core.nexus import agent_auth

    device_id, priv = _ghep(app_bat)
    path = "/nexus-agent/heartbeat"
    headers = {agent_auth.HEADER_DEVICE: device_id, **_ky(priv, "POST", path, b"")}
    r = app_bat.post(path, content=b"", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    assert r.json()["revoked"] is False


def test_khong_ky_thi_401(app_bat):
    device_id, _priv = _ghep(app_bat)
    from platform_core.nexus import agent_auth

    r = app_bat.post("/nexus-agent/heartbeat", content=b"",
                     headers={agent_auth.HEADER_DEVICE: device_id})
    assert r.status_code == 401


def test_ky_bang_khoa_KHAC_thi_401(app_bat):
    """Biết `device_id` không đủ — phải giữ khoá riêng của chính máy đó."""
    from platform_core.nexus import agent_auth

    device_id, _priv = _ghep(app_bat)
    khac, _pub = agent_auth.new_keypair_for_test()

    path = "/nexus-agent/heartbeat"
    headers = {agent_auth.HEADER_DEVICE: device_id, **_ky(khac, "POST", path, b"")}
    r = app_bat.post(path, content=b"", headers=headers)
    assert r.status_code == 401


def test_chu_ky_cua_duong_KHAC_khong_dung_lai_duoc(app_bat):
    """`path` nằm trong chuỗi ký. Thiếu nó thì một chữ ký lấy từ request vô hại
    đem dùng cho request nguy hiểm."""
    from platform_core.nexus import agent_auth

    device_id, priv = _ghep(app_bat)
    # Ky cho /heartbeat roi dem dung o /session/redeem.
    headers = {agent_auth.HEADER_DEVICE: device_id,
               **_ky(priv, "POST", "/nexus-agent/heartbeat", b"")}
    r = app_bat.post("/nexus-agent/session/redeem", content=b"", headers=headers)
    assert r.status_code == 401


def test_chu_ky_qua_CU_bi_tu_choi(app_bat):
    """`timestamp` nằm trong chuỗi ký. Thiếu nó thì một chữ ký nghe được là dùng
    lại được mãi mãi."""
    from platform_core.nexus import agent_auth

    device_id, priv = _ghep(app_bat)
    path = "/nexus-agent/heartbeat"
    cu = str(int(time.time()) - agent_auth.SKEW_S - 60)
    headers = {agent_auth.HEADER_DEVICE: device_id,
               **_ky(priv, "POST", path, b"", moc=cu)}
    r = app_bat.post(path, content=b"", headers=headers)
    assert r.status_code == 401


def test_doi_BODY_sau_khi_ky_bi_tu_choi(app_bat):
    """Băm body nằm trong chuỗi ký. Thiếu nó thì nội dung sửa được mà chữ ký vẫn
    đúng."""
    from platform_core.nexus import agent_auth

    device_id, priv = _ghep(app_bat)
    path = "/nexus-agent/session/redeem"
    body = json.dumps({"ticket": "a" * 40}).encode()
    headers = {agent_auth.HEADER_DEVICE: device_id,
               **_ky(priv, "POST", path, body)}
    r = app_bat.post(path, content=json.dumps({"ticket": "b" * 40}).encode(),
                     headers=headers)
    assert r.status_code == 401


def test_thiet_bi_da_THU_HOI_thi_nhip_tim_401(app_bat):
    from platform_core.nexus import agent_auth, devices
    from platform_core.db import get_session

    device_id, priv = _ghep(app_bat)
    gen = get_session()
    db = next(gen)
    try:
        row = db.get(devices.NexusDevice, device_id)
        devices.thu_hoi(db, row, by="owner")
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    path = "/nexus-agent/heartbeat"
    headers = {agent_auth.HEADER_DEVICE: device_id, **_ky(priv, "POST", path, b"")}
    r = app_bat.post(path, content=b"", headers=headers)
    assert r.status_code == 401


# ── Đổi vé ───────────────────────────────────────────────────────────────────

def test_thiet_bi_dich_doi_duoc_ve_cua_no(app_bat):
    from platform_core.db import get_session
    from platform_core.nexus import agent_auth, devices, sessions

    device_id, priv = _ghep(app_bat)
    gen = get_session()
    db = next(gen)
    try:
        row = db.get(devices.NexusDevice, device_id)
        _r, ve = sessions.cap_ve(db, user_id=row.user_id, device=row)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    path = "/nexus-agent/session/redeem"
    body = json.dumps({"ticket": ve}).encode()
    headers = {agent_auth.HEADER_DEVICE: device_id, **_ky(priv, "POST", path, body)}
    r = app_bat.post(path, content=body, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["quyen"] == sessions.QUYEN_DIEU_KHIEN


def test_thiet_bi_KHAC_khong_doi_duoc_ve_khong_danh_cho_no(app_bat):
    """Hai phép kiểm độc lập: chữ ký nói *ai gọi*, `session.device_id` nói *vé
    này của ai*. Thiếu phép thứ hai thì một thiết bị hợp lệ đổi vé của máy khác."""
    from platform_core.db import get_session
    from platform_core.nexus import agent_auth, devices, sessions

    d1, _p1 = _ghep(app_bat)

    # Ghep may thu hai cho CUNG chu.
    gen = get_session()
    db = next(gen)
    try:
        row1 = db.get(devices.NexusDevice, d1)
        _r, ma2 = devices.tao_ma_ghep(db, user_id=row1.user_id)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    priv2, pub2 = agent_auth.new_keypair_for_test()
    r = app_bat.post("/nexus-agent/enroll",
                     json={"code": ma2, "public_key": pub2})
    d2 = r.json()["device_id"]

    # Ve danh cho d1, nhung d2 di doi.
    gen = get_session()
    db = next(gen)
    try:
        row1 = db.get(devices.NexusDevice, d1)
        _r, ve = sessions.cap_ve(db, user_id=row1.user_id, device=row1)
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    path = "/nexus-agent/session/redeem"
    body = json.dumps({"ticket": ve}).encode()
    headers = {agent_auth.HEADER_DEVICE: d2, **_ky(priv2, "POST", path, body)}
    r = app_bat.post(path, content=body, headers=headers)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "redeem_failed"


# ── Fail-closed ──────────────────────────────────────────────────────────────

@pytest.fixture()
def app_tat(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'agentoff.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "agent-secret-value")
    monkeypatch.delenv("LTT_NEXUS", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from server.app import create_app

    client = TestClient(create_app(), base_url="https://testserver")
    try:
        yield client
    finally:
        dbmod.reset_engine()


def test_co_tat_thi_MOI_duong_agent_tra_404(app_tat):
    for duong in ("/nexus-agent/enroll", "/nexus-agent/heartbeat",
                  "/nexus-agent/session/redeem"):
        r = app_tat.post(duong, json={})
        assert r.status_code == 404, f"{duong} tra {r.status_code} khi co TAT"


def test_moi_handler_agent_deu_kiem_co():
    """Quên phép kiểm ở một đường mới là mở lại cửa mà không ai thấy."""
    import inspect

    from server.nexus import routes as agent_routes

    # Loc theo module: `vars()` cua module con chua ca thu duoc import (vd
    # `Header` cua FastAPI), va bat chung lam handler thi test do vi ly do sai.
    handlers = [obj for ten, obj in vars(agent_routes).items()
                if inspect.isfunction(obj) and not ten.startswith("_")
                and obj.__module__ == agent_routes.__name__]
    assert handlers
    thieu = [fn.__name__ for fn in handlers
             if "nexus.enabled()" not in inspect.getsource(fn)]
    assert thieu == [], f"duong agent khong kiem co: {thieu}"


def test_loi_luon_la_JSON_khong_bao_gio_HTML(app_tat):
    """Bên gọi là máy. Q88 cùng tinh thần: máy gọi máy không nhận HTML."""
    r = app_tat.post("/nexus-agent/enroll", json={})
    assert r.headers["content-type"].startswith("application/json")
    assert r.headers.get("cache-control") == "no-store"
