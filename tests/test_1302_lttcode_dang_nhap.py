"""LTTCODE — đăng nhập bằng tài khoản LTT Studios (spec LTTCODEAPP 2026-09-17-dang-nhap).

Ứng dụng desktop mở trình duyệt tới `/lttcode/authorize` (PKCE S256 + loopback
127.0.0.1), người dùng bấm Cho phép, ứng dụng đổi mã một lần lấy một khoá
`ltt_sk_` riêng cho máy đó. Các tính chất phải giữ:

* mã một lần, sống 120 giây, chỉ lưu digest; mọi lý do từ chối trả CÙNG một lỗi,
  và mã bị tiêu kể cả khi verifier sai (không cho dò verifier trên một mã);
* khoá cấp ra đúng người, đủ scope để chat, có tên máy, hết hạn sau 365 ngày;
* `next` sau đăng nhập giữ nguyên query (nền tảng mặc định làm rơi nó) và vẫn qua
  bộ lọc open-redirect;
* form Cho phép không 302 sang 127.0.0.1 (CSP `form-action 'self'` chặn) mà trả
  một trang dẫn về loopback.
"""
from __future__ import annotations

import base64
import hashlib
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, unquote, urlparse

import pytest
from fastapi.testclient import TestClient

from apps.lttcode import dang_nhap
from platform_core.public_api import keys as devkeys

PEPPER = "lttcode-login-pepper-" + "p" * 40
PASSWORD = "a-good-password-12"
VERIFIER = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"   # RFC 7636 phụ lục B
CHALLENGE = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
STATE = "st4te-abcdefghijklmnop"
PORT = 53123


# ── Thuần ────────────────────────────────────────────────────────────────────

def test_s256_dung_vector_rfc7636():
    assert dang_nhap.s256(VERIFIER) == CHALLENGE


def test_kiem_tham_so():
    ok = dang_nhap.kiem_tham_so(str(PORT), STATE, CHALLENGE, "S256", "LAPTOP-01 (nha)")
    assert ok == (PORT, STATE, CHALLENGE, "LAPTOP-01 nha")
    assert dang_nhap.kiem_tham_so("80", STATE, CHALLENGE, "S256", "x") is None
    assert dang_nhap.kiem_tham_so("70000", STATE, CHALLENGE, "S256", "x") is None
    assert dang_nhap.kiem_tham_so(str(PORT), "ngan", CHALLENGE, "S256", "x") is None
    assert dang_nhap.kiem_tham_so(str(PORT), STATE, CHALLENGE, "plain", "x") is None
    assert dang_nhap.kiem_tham_so(str(PORT), STATE, CHALLENGE[:-1], "S256", "x") is None
    assert dang_nhap.kiem_tham_so(str(PORT), STATE, CHALLENGE, "S256", "<script>")[3] == "script"
    assert dang_nhap.kiem_tham_so(str(PORT), STATE, CHALLENGE, "S256", "")[3] == "PC"


# ── Nền tảng ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def may(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'login.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.lttcode.tables  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    from apps.lttcode import routes_dang_nhap
    routes_dang_nhap.GIOI_HAN_TOKEN.xoa()
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "lttcode-login-secret",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"), "LTT_PUBLIC_API": "1",
    })
    try:
        with TestClient(app, base_url="https://testserver") as client:
            yield client
    finally:
        dbmod.reset_engine()


def _db():
    from platform_core.db import get_session
    return get_session()


def _dang_ky(client, email="dev@example.com"):
    from platform_core.users import tao_nguoi_dung

    gen = _db()
    db = next(gen)
    try:
        user = tao_nguoi_dung(db, email=email, password=PASSWORD)
        user.is_verified = True
        db.commit()
        uid = user.id
    finally:
        with pytest.raises(StopIteration):
            next(gen)
    form = client.get("/login")
    r = client.post("/login", data={"username": email, "password": PASSWORD,
                                    "csrf_token": _csrf(form.text)}, follow_redirects=False)
    assert r.status_code in (302, 303), r.text
    return uid


def _csrf(html):
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert m
    return m.group(1)


def _q(**kw):
    p = {"port": str(PORT), "state": STATE, "code_challenge": CHALLENGE,
         "code_challenge_method": "S256", "device": "LAPTOP-01"}
    p.update(kw)
    return p


def _cho_phep(client):
    trang = client.get("/lttcode/authorize", params=_q())
    assert trang.status_code == 200, trang.text
    r = client.post("/lttcode/authorize", data={**_q(), "action": "allow", "csrf_token": _csrf(trang.text)})
    assert r.status_code == 200, r.text
    m = re.search(r'href="(http://127\.0\.0\.1:\d+/callback\?[^"]+)"', r.text)
    assert m, r.text
    url = urlparse(m.group(1).replace("&amp;", "&"))
    q = parse_qs(url.query)
    assert url.port == PORT and q["state"] == [STATE]
    return q["code"][0], r


def test_chua_dang_nhap_chuyen_login_giu_nguyen_query(may):
    from server.auth.session import safe_next

    r = may.get("/lttcode/authorize", params=_q(), follow_redirects=False)
    assert r.status_code == 303
    loc = r.headers["location"]
    assert loc.startswith("/login?next=")
    nxt = unquote(loc[len("/login?next="):])
    assert safe_next(nxt) == nxt
    assert nxt.startswith("/lttcode/authorize?") and f"code_challenge={CHALLENGE}" in nxt


def test_tham_so_sai_tra_400(may):
    _dang_ky(may)
    assert may.get("/lttcode/authorize", params=_q(code_challenge_method="plain")).status_code == 400


def test_cho_phep_roi_doi_ma_lay_khoa_dung_nguoi_dung_scope(may):
    uid = _dang_ky(may)
    code, trang = _cho_phep(may)
    assert "no-store" in trang.headers["cache-control"]
    assert '<meta name="referrer" content="no-referrer">' in trang.text

    r = may.post("/lttcode/token", json={"code": code, "code_verifier": VERIFIER, "port": PORT})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["api_key"].startswith("ltt_sk_") and body["name"] == "LTTCODE – LAPTOP-01"
    assert "no-store" in r.headers["cache-control"]

    gen = _db()
    db = next(gen)
    try:
        key = devkeys.verify(db, body["api_key"])
        assert key is not None and key.user_id == uid
        assert "jobs:create" in key.scopes
        het_han = key.expires_at if key.expires_at.tzinfo else key.expires_at.replace(tzinfo=timezone.utc)
        assert timedelta(days=364) < het_han - datetime.now(timezone.utc) <= timedelta(days=365)
    finally:
        with pytest.raises(StopIteration):
            next(gen)

    # Mã chết sau một lần dùng.
    lai = may.post("/lttcode/token", json={"code": code, "code_verifier": VERIFIER, "port": PORT})
    assert lai.status_code == 400 and lai.json() == {"error": "invalid_grant"}


def test_verifier_sai_bi_tu_choi_va_ma_bi_tieu(may):
    _dang_ky(may)
    code, _ = _cho_phep(may)
    sai = may.post("/lttcode/token", json={"code": code, "code_verifier": "x" * 43, "port": PORT})
    assert sai.status_code == 400 and sai.json() == {"error": "invalid_grant"}
    dung = may.post("/lttcode/token", json={"code": code, "code_verifier": VERIFIER, "port": PORT})
    assert dung.json() == {"error": "invalid_grant"}


def test_sai_port_va_het_han(may, monkeypatch):
    _dang_ky(may)
    code, _ = _cho_phep(may)
    assert may.post("/lttcode/token", json={"code": code, "code_verifier": VERIFIER, "port": PORT + 1}).status_code == 400

    code2, _ = _cho_phep(may)
    that = dang_nhap._bay_gio
    monkeypatch.setattr(dang_nhap, "_bay_gio", lambda: that() + timedelta(seconds=dang_nhap.HAN_MA_S + 1))
    assert may.post("/lttcode/token", json={"code": code2, "code_verifier": VERIFIER, "port": PORT}).json() == {"error": "invalid_grant"}


def test_tu_choi_dan_ve_loopback_voi_access_denied(may):
    _dang_ky(may)
    trang = may.get("/lttcode/authorize", params=_q())
    r = may.post("/lttcode/authorize", data={**_q(), "action": "deny", "csrf_token": _csrf(trang.text)})
    assert r.status_code == 200
    assert "error=access_denied" in r.text and "code=" not in r.text


def test_csrf_sai_tra_400(may):
    _dang_ky(may)
    r = may.post("/lttcode/authorize", data={**_q(), "action": "allow", "csrf_token": "sai"})
    assert r.status_code == 400


def test_revoke_bang_chinh_khoa(may):
    _dang_ky(may)
    code, _ = _cho_phep(may)
    khoa = may.post("/lttcode/token", json={"code": code, "code_verifier": VERIFIER, "port": PORT}).json()["api_key"]
    assert may.post("/lttcode/revoke", headers={"Authorization": f"Bearer {khoa}"}).status_code == 204
    assert may.post("/lttcode/revoke", headers={"Authorization": "Bearer rac"}).status_code == 204
    gen = _db()
    db = next(gen)
    try:
        assert devkeys.verify(db, khoa) is None
    finally:
        with pytest.raises(StopIteration):
            next(gen)


def test_gioi_han_luot_doi_ma_theo_ip(may):
    for _ in range(dang_nhap.LUOT_TOKEN_MOI_PHUT):
        assert may.post("/lttcode/token", json={"code": "x", "code_verifier": "y", "port": PORT}).status_code == 400
    assert may.post("/lttcode/token", json={"code": "x", "code_verifier": "y", "port": PORT}).status_code == 429


def test_ma_luu_duoi_dang_digest(may):
    uid = _dang_ky(may)
    gen = _db()
    db = next(gen)
    try:
        code = dang_nhap.tao_ma(db, user_id=uid, challenge=CHALLENGE, port=PORT, device="PC")
        db.commit()
        from apps.lttcode.tables import LttcodeAuthCode
        row = db.query(LttcodeAuthCode).one()
        assert row.code_digest == hashlib.sha256(code.encode()).hexdigest() and code not in row.code_digest
        assert base64.urlsafe_b64decode(code + "=" * (-len(code) % 4))
    finally:
        with pytest.raises(StopIteration):
            next(gen)
