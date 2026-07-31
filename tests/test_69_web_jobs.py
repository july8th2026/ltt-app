"""
H2.3 — web submit qua hàng đợi + trang job + cách ly người dùng.

Trọng tâm bảo mật: **người dùng A không đọc được job của người dùng B.** Mọi
truy vấn job lọc theo user đang đăng nhập; xem job người khác → 404.
"""
from __future__ import annotations

import re

import pytest


@pytest.fixture()
def env(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    url = f"sqlite:///{(tmp_path / 'w.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-h23")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); s = next(gen)
    ua = tao_nguoi_dung(s, email="a@x.com", password="matkhau-tot", is_verified=True)
    ub = tao_nguoi_dung(s, email="b@x.com", password="matkhau-tot", is_verified=True)
    credit.nap(s, ua.id, 100)
    credit.nap(s, ub.id, 100)
    s.commit()
    ids = (ua.id, ub.id)
    s.close()

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver")
    yield client, ids
    dbmod.reset_engine()


def _login(client, email):
    client.post("/logout", follow_redirects=False)   # bo phien cu neu co
    tok = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").text).group(1)
    r = client.post("/login", data={"username": email, "password": "matkhau-tot",
                                    "csrf_token": tok}, follow_redirects=False)
    assert r.status_code == 303


def _demo_csrf(client):
    return re.search(r'name="csrf_token" value="([^"]+)"', client.get("/demo").text).group(1)


def test_submit_qua_hang_doi_tao_job_va_chuyen_trang(env):
    client, _ = env
    _login(client, "a@x.com")
    tok = _demo_csrf(client)
    r = client.post("/demo/queue", data={"text": "xin chao", "csrf_token": tok},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/jobs/")


def test_job_hien_o_trang_viec_cua_toi(env):
    client, _ = env
    _login(client, "a@x.com")
    tok = _demo_csrf(client)
    client.post("/demo/queue", data={"text": "abc", "csrf_token": tok},
                follow_redirects=False)
    html = client.get("/jobs").text
    assert "demo.reverse" in html


def test_A_khong_doc_duoc_job_cua_B(env):
    client, (ua_id, ub_id) = env
    # B tạo job.
    _login(client, "b@x.com")
    tok = _demo_csrf(client)
    r = client.post("/demo/queue", data={"text": "cua B", "csrf_token": tok},
                    follow_redirects=False)
    job_b = r.headers["location"]      # /jobs/<id cua B>

    # A đăng nhập, cố xem job của B → 404.
    _login(client, "a@x.com")
    r2 = client.get(job_b, follow_redirects=False)
    assert r2.status_code == 404, "A khong duoc doc job cua B"
    r3 = client.get(job_b + "/progress", follow_redirects=False)
    assert r3.status_code == 404


def test_thieu_credit_khong_tao_job(env):
    client, (ua_id, _) = env
    # Rut het credit cua A.
    import platform_core.db as dbmod
    from platform_core import credit
    gen = dbmod.get_session(); s = next(gen)
    credit.cap_tay(s, ua_id, -100, by="test"); s.commit()
    try: next(gen)
    except StopIteration: pass

    _login(client, "a@x.com")
    tok = _demo_csrf(client)
    r = client.post("/demo/queue", data={"text": "x" * 500, "csrf_token": tok},
                    follow_redirects=False)
    assert r.status_code == 400
    assert "credit" in r.text.lower()


def test_tien_do_fragment_tra_html(env):
    client, _ = env
    _login(client, "a@x.com")
    tok = _demo_csrf(client)
    r = client.post("/demo/queue", data={"text": "abc", "csrf_token": tok},
                    follow_redirects=False)
    jid = r.headers["location"].split("/jobs/")[1]
    frag = client.get(f"/jobs/{jid}/progress")
    assert frag.status_code == 200
    assert "job-progress" in frag.text
