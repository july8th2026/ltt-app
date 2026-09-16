"""LTTCODE — tìm kiếm web cho agent qua SearXNG riêng của công ty (P06).

Chủ dự án chốt 17/09: miễn phí, giới hạn lượt theo khoá (20/phút, 300/ngày).
Tính chất phải giữ:

* chỉ khoá `ltt_sk_` hợp lệ mới được tìm; khoá sai/thu hồi ⇒ 401;
* SearXNG sập, chậm, trả rác ⇒ 503 `search_unavailable` (không bao giờ 500);
* kết quả chuẩn hoá về `sources[]` (url/title/snippet/published_at), bỏ URL
  không phải http(s), cắt snippet, tối đa 8;
* không ghi câu truy vấn vào log (dữ liệu của người dùng).
"""
from __future__ import annotations

import json
import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from apps.lttcode import tim_kiem
from platform_core.public_api import keys as devkeys

PEPPER = "lttcode-search-pepper-" + "s" * 40

SEARX_OK = {
    "query": "asyncio gather",
    "results": [
        {"url": "https://docs.python.org/3/library/asyncio-task.html", "title": "Coroutines and Tasks",
         "content": "gather " * 200, "engine": "brave", "publishedDate": "2026-01-02T00:00:00"},
        {"url": "javascript:alert(1)", "title": "evil", "content": "x", "engine": "duckduckgo"},
        {"url": "https://stackoverflow.com/q/1", "title": "", "content": "", "engine": "stackoverflow",
         "publishedDate": None},
    ] + [{"url": f"https://example.org/{i}", "title": f"r{i}", "content": "c", "engine": "brave"} for i in range(20)],
    "unresponsive_engines": [["duckduckgo", "CAPTCHA"]],
}


# ── Thuần ────────────────────────────────────────────────────────────────────

def test_chuan_hoa_ket_qua():
    sources = tim_kiem.chuan_hoa(SEARX_OK, toi_da=5)
    assert len(sources) == 5
    assert sources[0]["url"] == "https://docs.python.org/3/library/asyncio-task.html"
    assert sources[0]["title"] == "Coroutines and Tasks"
    assert len(sources[0]["snippet"]) <= tim_kiem.DO_DAI_SNIPPET
    assert sources[0]["published_at"] == "2026-01-02T00:00:00"
    assert all(s["url"].startswith(("http://", "https://")) for s in sources)
    assert sources[1] == {"url": "https://stackoverflow.com/q/1"}
    assert tim_kiem.chuan_hoa({"results": "rac"}, toi_da=8) == []
    assert len(tim_kiem.chuan_hoa(SEARX_OK, toi_da=99)) == tim_kiem.TOI_DA_NGUON


def test_gioi_han_theo_khoa_phut_va_ngay():
    g = tim_kiem.GioiHanKhoa(moi_phut=2, moi_ngay=3)
    assert [g.cho_phep("k", now=0.0) for _ in range(3)] == [True, True, False]
    assert g.cho_phep("k", now=61.0) is True        # phút mới, ngày còn 0 lượt sau lượt này
    assert g.cho_phep("k", now=122.0) is False       # hết 3 lượt/ngày
    assert g.cho_phep("khac", now=122.0) is True
    assert g.cho_phep("k", now=86_401.0 + 61) is True  # ngày mới


# ── Route ────────────────────────────────────────────────────────────────────

@pytest.fixture()
def may(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'search.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    import apps.lttcode.tables  # noqa: F401
    from platform_core.db import Base, get_engine
    Base.metadata.create_all(get_engine())
    tim_kiem.GIOI_HAN.xoa()
    from server.app import create_app
    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "lttcode-search-secret",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
    })
    with TestClient(app, base_url="https://testserver") as client:
        yield client
    tim_kiem.dat_transport(None)
    dbmod.reset_engine()


def _khoa(revoke=False):
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung
    gen = get_session()
    db = next(gen)
    try:
        user = tao_nguoi_dung(db, email="s@example.com", password="a-good-password-12")
        row, token = devkeys.issue(db, user_id=user.id, name="LTTCODE – PC", scopes=("jobs:create",))
        if revoke:
            devkeys.revoke(db, row)
        db.commit()
        return token
    finally:
        with pytest.raises(StopIteration):
            next(gen)


def _searx(handler):
    seen = []

    def wrap(request: httpx.Request):
        seen.append(request)
        return handler(request)
    tim_kiem.dat_transport(httpx.MockTransport(wrap))
    return seen


def test_tim_kiem_tra_nguon_va_khong_log_truy_van(may, caplog):
    token = _khoa()
    seen = _searx(lambda r: httpx.Response(200, json=SEARX_OK))
    with caplog.at_level(logging.INFO):
        r = may.post("/lttcode/search", json={"query": "bí mật khách hàng", "max_results": 3},
                     headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["sources"]) == 3 and body["sources"][0]["url"].startswith("https://docs.python.org")
    assert "no-store" in r.headers["cache-control"]
    q = dict(seen[0].url.params)
    assert q["q"] == "bí mật khách hàng" and q["format"] == "json"
    assert str(seen[0].url).startswith(tim_kiem.SEARXNG_URL_MAC_DINH)
    assert "bí mật khách hàng" not in caplog.text
    assert "duckduckgo" in caplog.text   # engine hỏng được ghi để vận hành biết


def test_khoa_sai_hoac_thu_hoi_401(may):
    _searx(lambda r: httpx.Response(200, json=SEARX_OK))
    assert may.post("/lttcode/search", json={"query": "q"}).status_code == 401
    assert may.post("/lttcode/search", json={"query": "q"}, headers={"Authorization": "Bearer rac"}).status_code == 401
    token = _khoa(revoke=True)
    assert may.post("/lttcode/search", json={"query": "q"}, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_searxng_hong_tra_503(may):
    token = _khoa()
    h = {"Authorization": f"Bearer {token}"}

    def sap(_r):
        raise httpx.ConnectError("refused")
    _searx(sap)
    r = may.post("/lttcode/search", json={"query": "q"}, headers=h)
    assert r.status_code == 503 and r.json() == {"error": "search_unavailable"}
    _searx(lambda r: httpx.Response(403, text="forbidden"))
    assert may.post("/lttcode/search", json={"query": "q"}, headers=h).status_code == 503
    _searx(lambda r: httpx.Response(200, text="<html>"))
    assert may.post("/lttcode/search", json={"query": "q"}, headers=h).status_code == 503


def test_truy_van_rong_tra_400(may):
    token = _khoa()
    _searx(lambda r: httpx.Response(200, json=SEARX_OK))
    r = may.post("/lttcode/search", json={"query": "   "}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400


def test_vuot_gioi_han_tra_429(may, monkeypatch):
    token = _khoa()
    _searx(lambda r: httpx.Response(200, json=SEARX_OK))
    monkeypatch.setattr(tim_kiem, "GIOI_HAN", tim_kiem.GioiHanKhoa(moi_phut=2, moi_ngay=300))
    h = {"Authorization": f"Bearer {token}"}
    codes = [may.post("/lttcode/search", json={"query": "q"}, headers=h).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    assert json.loads(may.post("/lttcode/search", json={"query": "q"}, headers=h).text) == {"error": "rate_limited"}
