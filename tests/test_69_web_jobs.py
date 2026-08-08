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
    ua = tao_nguoi_dung(s, email="a@x.com", password="matkhau-tot",
                        is_verified=True, role="admin")
    ub = tao_nguoi_dung(s, email="b@x.com", password="matkhau-tot",
                        is_verified=True, role="admin")
    tao_nguoi_dung(s, email="customer@x.com", password="matkhau-tot",
                   is_verified=True)
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
    assert 'name="date_from"' in html and 'name="date_to"' in html


def test_timeline_owner_va_debug_chi_operator(env):
    client, _ = env
    _login(client, "a@x.com")
    submitted = client.post("/demo/queue", data={
        "text": "timeline", "csrf_token": _demo_csrf(client),
    }, follow_redirects=False)
    job_path = submitted.headers["location"]
    job_id = job_path.rsplit("/", 1)[-1]

    detail = client.get(job_path)
    assert detail.status_code == 200
    assert "Lịch sử xử lý" in detail.text
    assert "Đã tiếp nhận yêu cầu" in detail.text
    history = client.get("/api/jobs?app=demo&status=queued")
    assert history.status_code == 200
    assert history.json()["items"][0]["id"] == job_id
    assert "params" not in history.json()["items"][0]
    api_detail = client.get(f"/api/jobs/{job_id}")
    assert api_detail.status_code == 200
    assert api_detail.json()["events"][0]["code"] == "submitted"
    debug = client.get(f"/ops/jobs/{job_id}/events")
    assert debug.status_code == 200
    assert debug.json()["events"][0]["code"] == "submitted"
    export = client.get(f"/ops/jobs/{job_id}/support-export")
    assert export.status_code == 200
    assert export.headers["content-disposition"].startswith("attachment;")
    assert export.json()["job"]["id"] == job_id
    assert "params" not in export.json()["job"]
    retention = client.get("/ops/jobs-retention")
    assert retention.status_code == 200
    assert retention.json()["policy"]["customer_days"] == 365

    _login(client, "customer@x.com")
    assert client.get(f"/ops/jobs/{job_id}/events").status_code == 403
    assert client.get(f"/ops/jobs/{job_id}/support-export").status_code == 403
    assert client.get("/ops/jobs-retention").status_code == 403
    assert client.get(f"/api/jobs/{job_id}").status_code == 404


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


def test_owner_huy_job_va_thu_lai_tao_job_moi(env):
    client, (ua_id, _) = env
    _login(client, "a@x.com")
    tok = _demo_csrf(client)
    submitted = client.post("/demo/queue", data={"text": "retry me", "csrf_token": tok},
                            follow_redirects=False)
    old_path = submitted.headers["location"]
    old_id = old_path.rsplit("/", 1)[-1]
    detail = client.get(old_path)
    action_csrf = re.search(r'name="csrf_token" value="([^"]+)"', detail.text).group(1)

    cancelled = client.post(old_path + "/cancel", data={"csrf_token": action_csrf},
                            follow_redirects=False)
    assert cancelled.status_code == 303

    import platform_core.db as dbmod
    from platform_core import credit
    from platform_core.models import JOB_CANCELLED, Job, JobEvent
    gen = dbmod.get_session(); db = next(gen)
    try:
        assert db.get(Job, old_id).status == JOB_CANCELLED
        assert credit.so_du(db, ua_id) == 100  # hold của job cũ đã hoàn
        assert [event.event_code for event in db.query(JobEvent).filter_by(
            job_id=old_id).order_by(JobEvent.sequence)] == [
                "submitted", "cancelled", "credit_refunded"]
    finally:
        try: next(gen)
        except StopIteration: pass

    detail2 = client.get(old_path)
    retry_csrf = re.search(r'name="csrf_token" value="([^"]+)"', detail2.text).group(1)
    retried = client.post(old_path + "/retry", data={"csrf_token": retry_csrf},
                          follow_redirects=False)
    assert retried.status_code == 303
    assert retried.headers["location"].startswith("/jobs/")
    assert retried.headers["location"] != old_path


def test_user_khac_khong_huy_duoc_job(env):
    client, _ = env
    _login(client, "a@x.com")
    submitted = client.post("/demo/queue", data={"text": "owner only",
                            "csrf_token": _demo_csrf(client)}, follow_redirects=False)
    job_path = submitted.headers["location"]

    _login(client, "b@x.com")
    csrf = _demo_csrf(client)
    denied = client.post(job_path + "/cancel", data={"csrf_token": csrf},
                         follow_redirects=False)
    assert denied.status_code == 404


def test_normal_user_khong_vao_duoc_cau_hinh_va_status_operator(env):
    client, _ = env
    _login(client, "customer@x.com")
    assert client.get("/settings", follow_redirects=False).status_code == 403
    assert client.get("/status", follow_redirects=False).status_code == 403
