"""P8 regression: authenticated Agent routes, CSRF, ownership and UX contract."""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient


def _csrf(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, html[:500]
    return match.group(1)


@pytest.fixture()
def web(tmp_path, monkeypatch):
    db_url = f"sqlite:///{(tmp_path / 'agent-web.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", db_url)
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    gen = dbmod.get_session(); db = next(gen)
    from platform_core import credit, users
    user = users.tao_nguoi_dung(db, email="agent@example.com", password="Strong-pass-123",
                                is_verified=True)
    other = users.tao_nguoi_dung(db, email="other@example.com", password="Strong-pass-123",
                                 is_verified=True)
    credit.cap_tay(db, user.id, 100, by="test")
    db.commit(); uid, other_id = user.id, other.id
    db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    client = TestClient(create_app(env={
        "LTT_ENV": "local-server-test", "LTT_CONFIG_PATH": str(cfg),
        "LTT_SESSION_SECRET": "agent-test-session-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
    }), base_url="https://testserver", follow_redirects=False)
    login = client.get("/login?next=/agent")
    response = client.post("/login", data={"username": "agent@example.com",
        "password": "Strong-pass-123", "csrf_token": _csrf(login.text), "next": "/agent"})
    assert response.status_code == 303 and response.headers["location"] == "/agent"

    # Va vao module CHUA route, khong phai package: `plan_once` duoc import
    # theo gia tri nen va o `apps.agent.routes` khong doi duoc cai handler goi.
    from apps.agent.routes import legacy_runs
    # ⛔ TRUOC 26/08 cho nay dung `text.script` — tool cua `kichban`, DA GO o
    #    Q109. Ke hoach vi vay khong qua duoc validator, va sau phep kiem trong
    #    tep nay do voi trieu chung khong he chi vao nguyen nhan (`assert 200 ==
    #    303`: route dung lai va dung trang kem loi thay vi chuyen huong).
    #
    # ⭐ Thay bang `text.prompt_package` (`prompt_ai_ommi`) — mot tool VAN CON
    #    trong palette va cung sinh van ban. Y dinh cua bo test khong doi: ke
    #    hoach -> bao gia -> giu cho -> chay. No khong phu thuoc vao viec tool do
    #    ten la gi.
    good_plan = {"version": 1, "budget_max_credit": 50, "steps": [{
        "id": "s1", "tool": "text.prompt_package", "after": [], "fanout": 1,
        "max_retry": 0, "on_fail": "retry_same", "verify": None,
        "params": {"title": "Mot tieu de thu", "story": "Mot cau chuyen thu."},
    }]}
    monkeypatch.setattr(legacy_runs, "plan_once", lambda *_a, **_k: dict(good_plan))
    yield client, uid, other_id, db_url
    client.close(); dbmod.reset_engine()


def _make_plan(client, budget=50):
    page = client.get("/agent")
    response = client.post("/agent/plan", data={
        "goal": "Viết một kịch bản thử nghiệm rõ ràng", "budget_max": budget,
        "csrf_token": _csrf(page.text),
    })
    return response


def test_manifest_nap_sach_va_an_danh_return_to(web):
    client, *_ = web
    from platform_core.registry import discover
    app = {item.slug: item for item in discover()}["agent"]
    assert not app.error and app.router is not None and app.manifest.public
    anon = TestClient(client.app, base_url="https://testserver", follow_redirects=False)
    response = anon.get("/agent")
    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=/agent"


def test_plan_hien_gia_va_chua_hold(web):
    client, uid, *_ = web
    response = _make_plan(client)
    assert response.status_code == 303
    run_id = response.headers["location"].rsplit("/", 1)[-1]
    page = client.get(response.headers["location"])
    # 10, khong phai 7. Doi tool => doi gia, va con so nay den tu he thong chu
    # khong tu tep test: `credit_for('prompt_ai_ommi.generate', ...)` mot minh
    # tra 6, con Agent giu cho 10 vi no cong them phan cua chinh no (fanout,
    # verifier, retry). Ghi ra vi hai so do khac nhau la CO LY DO, khong phai
    # mot trong hai sai.
    assert "tối đa 10 credit" in page.text.lower()
    from platform_core import credit
    from platform_core.db import get_session
    db = next(get_session())
    assert credit.so_da_giu(db, run_id) == 0 and credit.so_du(db, uid) == 100
    db.close()


def test_approve_csrf_idempotent_va_api_du_plan(web):
    client, uid, *_ = web
    location = _make_plan(client).headers["location"]
    page = client.get(location); run_id = location.rsplit("/", 1)[-1]
    response = client.post(location + "/approve", data={
        "csrf_token": _csrf(page.text), "version": 1})
    assert response.status_code == 303
    api = client.get(location + "/api").json()
    assert api["status"] == "running" and api["estimated"] == 10
    assert api["plan"]["steps"][0]["tool"] == "text.prompt_package"
    from platform_core import credit
    from platform_core.db import get_session
    db = next(get_session())
    assert credit.so_da_giu(db, run_id) == 10 and credit.so_du(db, uid) == 90
    db.close()
    assert client.post(location + "/approve", data={"version": 1}).status_code == 400


def test_plan_invalid_huu_ich_khong_tao_run(web, monkeypatch):
    client, uid, _other, _url = web
    from apps.agent.routes import legacy_runs
    monkeypatch.setattr(legacy_runs, "plan_once", lambda *_a, **_k: {
        "version": 1, "budget_max_credit": 50,
        "steps": [{"id": "s1", "tool": "missing.tool", "params": {}}]})
    response = _make_plan(client)
    assert response.status_code == 200 and "không tồn tại" in response.text
    from platform_core.db import get_session
    from platform_core.models import AgentRun
    db = next(get_session()); assert db.query(AgentRun).filter_by(user_id=uid).count() == 0
    db.close()


def test_khong_du_credit_khong_running(web):
    client, uid, *_ = web
    from platform_core import credit
    from platform_core.db import get_session
    db = next(get_session()); credit.cap_tay(db, uid, -96, by="test"); db.commit(); db.close()
    location = _make_plan(client).headers["location"]
    page = client.get(location)
    response = client.post(location + "/approve", data={
        "csrf_token": _csrf(page.text), "version": 1})
    assert response.status_code == 303 and "error=credit" in response.headers["location"]
    assert "Không đủ credit" in client.get(response.headers["location"]).text
    assert client.get(location + "/api").json()["status"] == "awaiting_approval"


def test_cancel_va_refresh_giu_trang_thai(web):
    client, *_ = web
    location = _make_plan(client).headers["location"]
    page = client.get(location)
    response = client.post(location + "/cancel", data={"csrf_token": _csrf(page.text)})
    assert response.status_code == 303
    assert client.get(location + "/api").json()["status"] == "cancelled"
    assert "cancelled" in client.get(location).text


def test_user_khac_khong_xem_run(web):
    client, _uid, other_id, _url = web
    location = _make_plan(client).headers["location"]
    from platform_core.db import get_session
    from platform_core.users import tao_phien
    from platform_core.models import User
    db = next(get_session()); sid = tao_phien(db, db.get(User, other_id)); db.commit(); db.close()
    other = TestClient(client.app, base_url="https://testserver", follow_redirects=False)
    with other as other_client:
        other_client.cookies.set("session", "")
        # SessionMiddleware cookie is signed, so authenticate through the public form.
        login = other_client.get("/login")
        other_client.post("/login", data={"username": "other@example.com",
            "password": "Strong-pass-123", "csrf_token": _csrf(login.text), "next": "/"})
        assert other_client.get(location).status_code == 404
        assert other_client.get(location + "/api").status_code == 404


def test_tick_va_ui_khong_lo_stack_or_secret(web, monkeypatch):
    client, *_ = web
    location = _make_plan(client).headers["location"]
    page = client.get(location)
    client.post(location + "/approve", data={"csrf_token": _csrf(page.text), "version": 1})
    # Va vao module that (`apps.agent.jobs`) chu khong vao mot module route:
    # moi module route deu tro toi cung mot doi tuong module nay.
    from apps.agent import jobs as agent_jobs
    from platform_core.agent import runs as agent_runs
    called = []
    monkeypatch.setattr(agent_jobs, "advance", lambda db, **kw: called.append(kw) or
                        agent_runs.get_owned(db, kw["run_id"], kw["user_id"]))
    page = client.get(location)
    response = client.post(location + "/tick", data={"csrf_token": _csrf(page.text)})
    assert response.status_code == 200 and called
    assert "Traceback" not in response.text and "token=" not in response.text
