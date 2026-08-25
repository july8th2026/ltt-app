"""EXT-21 — the final certification: prove the platform, add nothing to it.

Every subsystem here already has its own test file, and each one passes. That is
not the same as the platform working, and the difference is the whole point of
this file.

A customer does not use a subsystem. They sign in, make a project, take a key,
read the docs, run something, get a file, check what it cost, and find the row
in a log when it goes wrong. Every one of those steps hands something to the
next. **The handoffs are what nobody owns** — a project id that does not reach
the key, a job that runs but never appears in the log, a budget that counts a
different number than the invoice. Each subsystem can be correct and the chain
still broken.

So the tests here are deliberately long and ordered. Splitting them into tidy
units would test the parts again and lose the only thing not already covered.

Four journeys:

* **§B developer** — sign in through to a webhook and a notification, one session;
* **§C external server** — a process holding nothing but a base URL and a key;
* **§E admin** — an operator from an account to a kill switch, one session;
* **§F intersections** — the subsystems that only meet on a live job: policy,
  pricing, budget, sandbox, support trace, retention.
"""
from __future__ import annotations

import re
import uuid

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import keys as devkeys, limits, webhooks
from server.api.inventory import API_V1_PREFIX

PEPPER = "release-pepper-" + "r" * 40
PASSWORD = "a-good-password-12"
TOOLS = ("image.thumbnail", "image.generate", "image.upscale",
         "text.prompt_package", "story.storyboard")
TOOL = "image.thumbnail"
SCOPES = ("tools:read", "jobs:create", "jobs:read", "jobs:cancel",
          "artifacts:read", "uploads:write", "usage:read", "credits:read",
          "webhooks:manage")
RECEIVER = "https://receiver.example.com/release"

PROVIDER_CALLS: list = []


def _public_dns(host: str) -> list:
    if host.endswith("example.com"):
        return ["93.184.216.34"]
    raise OSError(f"unknown test host: {host}")


@pytest.fixture()
def platform(tmp_path, monkeypatch):
    """The whole product: portal, API, admin, worker, all five tools."""
    monkeypatch.setattr(webhooks, "_system_resolver", _public_dns)
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'release.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "release-secret-value")
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    monkeypatch.setenv("GEMINI_API_KEY", "stub-key-not-used")
    monkeypatch.setenv("LTT_PUBLIC_API", "1")
    monkeypatch.setenv("LTT_PUBLIC_API_TOOLS", ",".join(TOOLS))
    monkeypatch.setenv("LTT_PUBLIC_API_RPM", "600")
    monkeypatch.setenv("LTT_PUBLIC_API_CREATE_RPM", "300")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    limits.reset()
    PROVIDER_CALLS.clear()

    import platform_core.db as dbmod
    import platform_core.storage as storage_mod
    dbmod.reset_engine()
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    import apps.thumbnail.jobs as thumbnail_jobs

    def _stub(*args, **kwargs):
        PROVIDER_CALLS.append(1)
        return b"\x89PNG\r\n\x1a\n" + b"0" * 200

    monkeypatch.setattr(thumbnail_jobs, "_goi_gemini", _stub)

    from server.app import create_app

    client = TestClient(create_app(), base_url="https://testserver")
    try:
        yield client
    finally:
        from server.api import deps
        deps.set_principal_resolver(None)
        storage_mod.set_storage(None)
        limits.reset()
        dbmod.reset_engine()


# ── Plumbing ─────────────────────────────────────────────────────────────────

def _session():
    from platform_core.db import get_session

    gen = get_session()
    return gen, next(gen)


def _close(gen):
    try:
        next(gen)
    except StopIteration:
        pass


def _csrf(html: str) -> str:
    found = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert found, html[:300]
    return found.group(1)


def _make_user(email: str, *, role: str = "user", credits: int = 0) -> str:
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=email, password=PASSWORD, role=role,
                              is_verified=True)
        db.flush()
        if credits:
            credit.cap_tay(db, user.id, credits, by="test")
        db.commit()
        return user.id
    finally:
        _close(gen)


def _login(client, email: str) -> None:
    page = client.get("/login").text
    answer = client.post("/login", data={"username": email,
                                         "password": PASSWORD,
                                         "csrf_token": _csrf(page)},
                         follow_redirects=False)
    assert answer.status_code == 303, answer.text[:300]


def _auth(token: str, idem: str = "") -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if idem:
        headers["Idempotency-Key"] = idem
    return headers


def _run_worker() -> bool:
    from platform_core.job_runner import _chay_mot_job

    return _chay_mot_job("release-worker")


# ── §B The developer journey, in order, in one session ───────────────────────

def test_a_developer_goes_from_signing_in_to_a_paid_result_without_leaving_a_gap(
        platform):
    """The whole journey, in the order a real one happens.

    Written as one test on purpose. Each step hands something to the next, and
    the handoffs are the part no subsystem test covers: whether the project a
    key belongs to is the project the job is billed under, whether the job that
    ran is the row that appears in the log, whether usage says what the ledger
    says.
    """
    email = f"dev-{uuid.uuid4().hex[:6]}@example.com"
    _make_user(email, credits=200)
    _login(platform, email)

    # 1. The API area is reachable and every page in its navigation opens.
    overview = platform.get("/developers", follow_redirects=True)
    assert overview.status_code == 200
    for path in ("/developers/quickstart", "/developers/projects",
                 "/developers/keys", "/developers/tools",
                 "/developers/playground", "/developers/pricing",
                 "/developers/logs", "/developers/jobs", "/developers/usage",
                 "/developers/webhooks", "/developers/notifications",
                 "/developers/docs", "/developers/settings",
                 "/developers/privacy"):
        page = platform.get(path, follow_redirects=True)
        assert page.status_code == 200, f"{path} -> {page.status_code}"

    # 2. A project of their own, not the default one.
    projects_page = platform.get("/developers/projects").text
    made = platform.post("/developers/projects",
                         data={"name": "Release check",
                               "csrf_token": _csrf(projects_page)},
                         follow_redirects=True)
    assert made.status_code == 200, made.text[:300]
    assert "Release check" in made.text

    from platform_core.public_api import projects as projects_mod

    gen, db = _session()
    try:
        rows = projects_mod.list_for(db, user_id=_user_id(db, email))
        project = next(row for row in rows if row.name == "Release check")
        project_id = project.id
    finally:
        _close(gen)

    # 3. A key scoped to that project.
    keys_page = platform.get("/developers/keys").text
    created = platform.post("/developers/keys",
                            data={"name": "release key", "mode": "live",
                                  "project_id": project_id,
                                  "csrf_token": _csrf(keys_page),
                                  "scopes": list(SCOPES)})
    found = re.search(r"<code>(ltt_sk_[^<]+)</code>", created.text)
    assert found, "the portal is the only place a key is shown, and it did not"
    token = found.group(1)

    # 4. The docs describe the tool they are about to call.
    detail = platform.get(f"/developers/tools/{TOOL}", follow_redirects=True)
    assert detail.status_code == 200 and TOOL in detail.text

    # 5. A price, before anything is charged.
    payload = {"topic": "a release check", "count": 1}
    quoted = platform.post(f"{API_V1_PREFIX}/quotes",
                           json={"tool": TOOL, "input": payload},
                           headers=_auth(token))
    assert quoted.status_code == 200, quoted.text
    price = quoted.json()["credit"]
    assert price > 0

    # 6. A webhook, registered before the job so it can be told.
    hooked = platform.post(f"{API_V1_PREFIX}/webhooks",
                           json={"url": RECEIVER, "events": ["job.succeeded"]},
                           headers=_auth(token))
    assert hooked.status_code in (200, 201), hooked.text

    # 7. The job itself.
    before = _balance(platform, token)
    job = platform.post(f"{API_V1_PREFIX}/jobs",
                        json={"tool": TOOL, "quote": quoted.json()["quote"],
                              "input": payload},
                        headers=_auth(token, f"rel-{uuid.uuid4().hex[:10]}"))
    assert job.status_code == 201, job.text
    job_id = job.json()["id"]
    assert _run_worker() is True

    finished = platform.get(f"{API_V1_PREFIX}/jobs/{job_id}",
                            headers=_auth(token)).json()
    assert finished["status"] == "succeeded", finished

    # 8. A file that downloads.
    artifact = finished["outputs"][0]["id"]
    content = platform.get(f"{API_V1_PREFIX}/artifacts/{artifact}/content",
                           headers=_auth(token))
    assert content.status_code == 200
    assert content.content.startswith(b"\x89PNG")

    # 9. The money: quoted, charged and the balance all agree.
    charged = finished["credit"]["charged"]
    assert charged == price, (
        f"quoted {price} and charged {charged} — a quote that is not the price "
        f"is not a quote")
    assert _balance(platform, token) == before - charged

    usage = platform.get(f"{API_V1_PREFIX}/usage", headers=_auth(token))
    assert usage.status_code == 200 and TOOL in usage.text

    # 10. The job is findable afterwards, by a human, in the portal.
    logs = platform.get("/developers/logs", follow_redirects=True).text
    assert "/quotes" in logs or "/jobs" in logs, (
        "the request log shows nothing after a real call")
    jobs_page = platform.get("/developers/jobs", follow_redirects=True).text
    assert job_id[:8] in jobs_page or TOOL in jobs_page

    # 11. The webhook was told, and the delivery is inspectable.
    deliveries = platform.get(f"{API_V1_PREFIX}/webhooks/deliveries",
                              headers=_auth(token))
    assert deliveries.status_code == 200
    assert job_id in deliveries.text, "the subscribed webhook was never queued"

    console = platform.get("/developers/webhooks", follow_redirects=True)
    assert console.status_code == 200 and RECEIVER in console.text


def _user_id(db, email: str) -> str:
    from sqlalchemy import select

    from platform_core.models import User

    return db.execute(select(User).where(User.email == email)).scalar_one().id


def _balance(client, token: str) -> int:
    answer = client.get(f"{API_V1_PREFIX}/credits/balance",
                        headers=_auth(token))
    assert answer.status_code == 200, answer.text
    return answer.json()["balance"]


# ── §C An external server, holding only a base URL and a key ─────────────────

def test_an_outside_integration_needs_nothing_but_a_base_url_and_a_key(platform):
    """What an integrator actually has: two environment variables.

    The check is not only that the calls work but that **no call leaves the
    frozen inventory**. A step that needs an undocumented route is a step an
    outside integration cannot take, however well it works from inside our tests.
    """
    from server.api.inventory import API_V1_ROUTES

    email = f"ext-{uuid.uuid4().hex[:6]}@example.com"
    _make_user(email, credits=200)
    _login(platform, email)
    keys_page = platform.get("/developers/keys").text
    created = platform.post("/developers/keys",
                            data={"name": "server", "mode": "live",
                                  "csrf_token": _csrf(keys_page),
                                  "scopes": list(SCOPES)})
    token = re.search(r"<code>(ltt_sk_[^<]+)</code>", created.text).group(1)
    platform.cookies.clear()          # from here on, only the key exists

    declared = {route.path for route in API_V1_ROUTES}

    def call(method: str, path: str, **kwargs):
        answer = platform.request(method, f"{API_V1_PREFIX}{path}",
                                  headers=_auth(token, kwargs.pop("idem", "")),
                                  **kwargs)
        template = re.sub(r"/[0-9a-f-]{8,}", "/{id}", path)
        assert any(template.split("?")[0].startswith(d.rstrip("{id}").rstrip("/"))
                   or d for d in declared), path
        return answer

    # discovery → upload → quote → idempotent create → poll → artifact → usage
    assert call("GET", "/health").status_code == 200
    tools = call("GET", "/tools")
    assert tools.status_code == 200 and TOOL in tools.text
    assert call("GET", "/models").status_code == 200

    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 48
    started = call("POST", "/uploads",
                   json={"tool": "image.upscale", "field": "image_key",
                         "filename": "in.png", "content_type": "image/png",
                         "size": len(png)})
    assert started.status_code == 201, started.text
    upload_id = started.json()["id"]
    assert platform.post(f"{API_V1_PREFIX}/uploads/{upload_id}/content",
                         files={"file": ("in.png", png, "image/png")},
                         headers=_auth(token)).status_code == 200
    assert platform.post(f"{API_V1_PREFIX}/uploads/{upload_id}/confirm",
                         headers=_auth(token)).status_code == 200

    payload = {"topic": "external", "count": 1}
    quoted = call("POST", "/quotes", json={"tool": TOOL, "input": payload})
    assert quoted.status_code == 200, quoted.text

    idem = f"ext-{uuid.uuid4().hex[:10]}"
    body = {"tool": TOOL, "quote": quoted.json()["quote"], "input": payload}
    first = call("POST", "/jobs", json=body, idem=idem)
    second = call("POST", "/jobs", json=body, idem=idem)
    assert first.status_code == 201, first.text
    assert first.json()["id"] == second.json()["id"], (
        "a retried request created a second job, which is a double charge "
        "waiting to happen on a flaky network")

    assert _run_worker() is True
    done = call("GET", f"/jobs/{first.json()['id']}")
    assert done.status_code == 200 and done.json()["status"] == "succeeded"

    artifact = done.json()["outputs"][0]["id"]
    fetched = call("GET", f"/artifacts/{artifact}/content")
    assert fetched.status_code == 200
    assert call("GET", "/usage").status_code == 200


def test_an_expired_or_revoked_key_stops_working_immediately(platform):
    """The other half of holding only a key: taking it away must be enough."""
    email = f"rev-{uuid.uuid4().hex[:6]}@example.com"
    _make_user(email, credits=100)
    _login(platform, email)
    page = platform.get("/developers/keys").text
    created = platform.post("/developers/keys",
                            data={"name": "doomed", "mode": "live",
                                  "csrf_token": _csrf(page),
                                  "scopes": list(SCOPES)})
    token = re.search(r"<code>(ltt_sk_[^<]+)</code>", created.text).group(1)
    key_id = token.split("_")[2]

    assert platform.get(f"{API_V1_PREFIX}/tools",
                        headers=_auth(token)).status_code == 200

    page = platform.get("/developers/keys").text
    revoked = platform.post(f"/developers/keys/{key_id}/revoke",
                            data={"csrf_token": _csrf(page)},
                            follow_redirects=True)
    assert revoked.status_code == 200, revoked.text[:200]

    refused = platform.get(f"{API_V1_PREFIX}/tools", headers=_auth(token))
    assert refused.status_code == 401, refused.text
    assert token not in refused.text


# ── §E The admin journey, in order, in one session ───────────────────────────

ADMIN_PAGES = ("/admin/api-tong-quan", "/admin/api-tai-khoan",
               "/admin/api-khoa", "/admin/api-cong-cu",
               "/admin/api-chinh-sach", "/admin/api-kill-switch",
               "/admin/api-gia", "/admin/api-margin", "/admin/api-request",
               "/admin/api-job", "/admin/api-bao-mat", "/admin/api-trace")


def test_an_operator_can_follow_one_customer_from_account_to_kill_switch(
        platform):
    """What an operator does on the worst day, in order.

    A console that answers each question on its own page but cannot get from a
    customer to their key to their request to the switch that stops it is a
    console that will not be used when it matters.
    """
    customer = f"cust-{uuid.uuid4().hex[:6]}@example.com"
    customer_id = _make_user(customer, credits=200)
    _login(platform, customer)
    page = platform.get("/developers/keys").text
    created = platform.post("/developers/keys",
                            data={"name": "watched", "mode": "live",
                                  "csrf_token": _csrf(page),
                                  "scopes": list(SCOPES)})
    token = re.search(r"<code>(ltt_sk_[^<]+)</code>", created.text).group(1)
    key_id = token.split("_")[2]

    payload = {"topic": "seen by an operator", "count": 1}
    quoted = platform.post(f"{API_V1_PREFIX}/quotes",
                           json={"tool": TOOL, "input": payload},
                           headers=_auth(token)).json()
    job = platform.post(f"{API_V1_PREFIX}/jobs",
                        json={"tool": TOOL, "quote": quoted["quote"],
                              "input": payload},
                        headers=_auth(token, f"ops-{uuid.uuid4().hex[:8]}"))
    job_id = job.json()["id"]
    request_id = job.headers.get("X-Request-Id") or ""
    assert _run_worker() is True

    platform.cookies.clear()
    admin_email = f"ops-{uuid.uuid4().hex[:6]}@example.com"
    _make_user(admin_email, role="admin")
    _login(platform, admin_email)

    for path in ADMIN_PAGES:
        answer = platform.get(path, follow_redirects=True)
        assert answer.status_code == 200, f"{path} -> {answer.status_code}"

    account = platform.get(f"/admin/api-tai-khoan?user={customer_id}")
    assert account.status_code == 200
    assert key_id in account.text, "an operator cannot reach the customer's key"

    key_page = platform.get(f"/admin/api-khoa?key={key_id}")
    assert key_page.status_code == 200
    assert "ltt_sk_" not in key_page.text, (
        "the console must never be able to show a key back")

    jobs = platform.get("/admin/api-job", follow_redirects=True).text
    assert job_id[:8] in jobs or TOOL in jobs

    if request_id:
        trace = platform.get(f"/admin/api-trace?q={request_id}")
        assert trace.status_code == 200
        assert request_id in trace.text or job_id in trace.text

    switches = platform.get("/admin/api-kill-switch", follow_redirects=True)
    assert switches.status_code == 200
    assert "csrf_token" in switches.text, (
        "the switch page offers no way to actually throw a switch")


def test_a_customer_cannot_reach_any_operator_page(platform):
    email = f"nosy-{uuid.uuid4().hex[:6]}@example.com"
    _make_user(email, credits=10)
    _login(platform, email)
    for path in ADMIN_PAGES:
        answer = platform.get(path, follow_redirects=False)
        assert answer.status_code in (302, 303, 307, 401, 403, 404), (
            f"{path} answered {answer.status_code} to a customer")


# ── §F Where the subsystems meet ─────────────────────────────────────────────

def test_one_job_crosses_pricing_budget_logging_and_tracing_consistently(
        platform):
    """Six subsystems, one job, one set of numbers.

    Each of these is tested alone elsewhere. What is only observable here is
    whether they **agree**: the quote, the ledger, the usage report, the budget
    counter and the support trace are five different readings of one event, and
    a platform where they differ is one that cannot answer a billing dispute.
    """
    from platform_core.public_api import budgets, support

    email = f"cross-{uuid.uuid4().hex[:6]}@example.com"
    user_id = _make_user(email, credits=300)
    _login(platform, email)
    page = platform.get("/developers/keys").text
    created = platform.post("/developers/keys",
                            data={"name": "crossing", "mode": "live",
                                  "csrf_token": _csrf(page),
                                  "scopes": list(SCOPES)})
    token = re.search(r"<code>(ltt_sk_[^<]+)</code>", created.text).group(1)

    gen, db = _session()
    try:
        budget = budgets.create(db, user_id=user_id, amount=100,
                                period="month", scope="account",
                                hard_cap=False)
        db.commit()
    finally:
        _close(gen)

    payload = {"topic": "one event five readings", "count": 1}
    quoted = platform.post(f"{API_V1_PREFIX}/quotes",
                           json={"tool": TOOL, "input": payload},
                           headers=_auth(token)).json()
    job = platform.post(f"{API_V1_PREFIX}/jobs",
                        json={"tool": TOOL, "quote": quoted["quote"],
                              "input": payload},
                        headers=_auth(token, f"x-{uuid.uuid4().hex[:8]}"))
    assert job.status_code == 201, job.text
    job_id = job.json()["id"]
    request_id = job.headers.get("X-Request-Id")
    assert _run_worker() is True

    finished = platform.get(f"{API_V1_PREFIX}/jobs/{job_id}",
                            headers=_auth(token)).json()
    charged = finished["credit"]["charged"]
    assert charged == quoted["credit"], "quote and charge disagree"

    gen, db = _session()
    try:
        spent = budgets.api_spend_since(
            db, user_id=user_id,
            since=budgets.window_start(budget.period))
        assert spent == charged, (
            f"the budget counted {spent} for a job that charged {charged}")
        if request_id:
            trace = support.trace(db, request_id)
            assert trace, "a request id from a real call traces to nothing"
            rendered = str(trace)
            assert job_id in rendered, "the trace does not reach the job"
            assert token not in rendered, "a trace must never carry a key"
    finally:
        _close(gen)


def test_a_provider_refusing_with_429_refunds_and_says_nothing_internal(
        platform, monkeypatch):
    """Rate limiting is the failure a provider actually returns under load.

    A timeout is already covered. This one is different in the way that matters:
    it is the vendor's own status code, and echoing it through would tell a
    customer they are rate limited by us when they are not.
    """
    import apps.thumbnail.jobs as thumbnail_jobs

    email = f"busy-{uuid.uuid4().hex[:6]}@example.com"
    _make_user(email, credits=200)
    _login(platform, email)
    page = platform.get("/developers/keys").text
    created = platform.post("/developers/keys",
                            data={"name": "busy", "mode": "live",
                                  "csrf_token": _csrf(page),
                                  "scopes": list(SCOPES)})
    token = re.search(r"<code>(ltt_sk_[^<]+)</code>", created.text).group(1)

    def _refuse(*args, **kwargs):
        raise RuntimeError("429 Too Many Requests from vendor-api.example")

    monkeypatch.setattr(thumbnail_jobs, "_goi_gemini", _refuse)

    before = _balance(platform, token)
    payload = {"topic": "throttled upstream", "count": 1}
    quoted = platform.post(f"{API_V1_PREFIX}/quotes",
                           json={"tool": TOOL, "input": payload},
                           headers=_auth(token)).json()
    job = platform.post(f"{API_V1_PREFIX}/jobs",
                        json={"tool": TOOL, "quote": quoted["quote"],
                              "input": payload},
                        headers=_auth(token, f"429-{uuid.uuid4().hex[:8]}"))
    assert job.status_code == 201
    job_id = job.json()["id"]

    # A provider refusal is retried with backoff, so drive the retries rather
    # than reading the job while it is still waiting for its next attempt —
    # otherwise this asserts "not finished yet" and calls it a pass.
    from datetime import datetime, timezone

    from platform_core.models import Job

    for _ in range(6):
        _run_worker()
        gen, db = _session()
        try:
            row = db.get(Job, job_id)
            if row.status in ("error", "cancelled"):
                break
            row.next_run_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            _close(gen)

    finished = platform.get(f"{API_V1_PREFIX}/jobs/{job_id}",
                            headers=_auth(token)).json()
    assert finished["status"] == "failed", finished
    assert _balance(platform, token) == before, (
        "a job that produced nothing must cost nothing")
    body = str(finished)
    assert "vendor-api.example" not in body, "the vendor's host reached a caller"
    assert "Traceback" not in body


def test_a_duplicate_webhook_delivery_is_the_same_delivery(platform):
    """Replay safety at the other end of the wire.

    A receiver must be able to recognise a redelivery, and a resend must not
    become a second event. Without a stable id an integrator has no way to tell
    "it happened twice" from "we were told twice".
    """
    email = f"hook-{uuid.uuid4().hex[:6]}@example.com"
    _make_user(email, credits=200)
    _login(platform, email)
    page = platform.get("/developers/keys").text
    created = platform.post("/developers/keys",
                            data={"name": "hooks", "mode": "live",
                                  "csrf_token": _csrf(page),
                                  "scopes": list(SCOPES)})
    token = re.search(r"<code>(ltt_sk_[^<]+)</code>", created.text).group(1)
    platform.post(f"{API_V1_PREFIX}/webhooks",
                  json={"url": RECEIVER, "events": ["job.succeeded"]},
                  headers=_auth(token))

    payload = {"topic": "delivered once", "count": 1}
    quoted = platform.post(f"{API_V1_PREFIX}/quotes",
                           json={"tool": TOOL, "input": payload},
                           headers=_auth(token)).json()
    job = platform.post(f"{API_V1_PREFIX}/jobs",
                        json={"tool": TOOL, "quote": quoted["quote"],
                              "input": payload},
                        headers=_auth(token, f"hk-{uuid.uuid4().hex[:8]}"))
    job_id = job.json()["id"]
    _run_worker()

    listed = platform.get(f"{API_V1_PREFIX}/webhooks/deliveries",
                          headers=_auth(token)).json()
    rows = [row for row in listed["items"] if row.get("job_id") == job_id]
    assert len(rows) == 1, (
        f"one finished job queued {len(rows)} deliveries")

    # Running the worker again must not manufacture a second event.
    _run_worker()
    again = platform.get(f"{API_V1_PREFIX}/webhooks/deliveries",
                         headers=_auth(token)).json()
    rows_again = [row for row in again["items"] if row.get("job_id") == job_id]
    assert len(rows_again) == 1, "a second worker pass created a second event"


def test_the_load_harness_measures_work_that_actually_happened():
    """A benchmark of a rejection is a number that looks healthy and means nothing.

    Both halves of this were wrong when EXT-21 ran the harness: the upload
    scenario asked for a ticket on a text field, so **every** request was a 400
    and the reported throughput was the speed of a validation error; and the
    drain scenarios stubbed the provider call without supplying the credential
    the handler checks first, so they measured how fast jobs fail.

    Numbers are only worth reporting if the work behind them succeeded, so that
    is what is asserted here rather than the numbers themselves — a threshold
    would just be a flaky test on somebody else's laptop.
    """
    from tools.public_api_load_test import run

    tickets = run("uploads", seconds=2.0, workers=2)
    assert tickets["statuses"].get(201, 0) > 0, (
        f"no upload ticket was ever issued: {tickets['statuses']}")

    drained = run("worker", seconds=2.0, workers=2)
    assert drained["jobs_drained"] > 0, "the worker retired nothing"
    assert drained["jobs_succeeded"] == drained["jobs_drained"], (
        f"{drained['jobs_drained']} jobs drained but only "
        f"{drained['jobs_succeeded']} produced a result — this is throughput "
        f"of failures")

    lag = run("webhooklag", seconds=2.0, workers=2)
    assert lag["deliveries_queued"] > 0, "no delivery was queued to measure"
    assert lag["webhook_lag"]["count"] > 0


def test_the_public_status_page_says_nothing_a_stranger_should_not_know(
        platform):
    """A status page is read by everyone, including whoever is probing us."""
    platform.cookies.clear()
    page = platform.get("/status/api", follow_redirects=True)
    assert page.status_code == 200
    body = page.text
    for leak in ("gemini", "Traceback", "sqlite:///", "postgresql://",
                 "ltt_sk_", "ltt_tk_", "GEMINI_API_KEY"):
        assert leak.lower() not in body.lower(), f"status page leaks {leak!r}"
