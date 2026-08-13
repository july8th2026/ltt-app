"""EXT-11 — budgets, alerts and the D3 fix.

Three properties decide whether a budget feature is safe: it never writes to the
ledger, a hard cap refuses deterministically, and the alerts do not become noise.
Everything here tests one of those.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import (alerting, budgets, keys as devkeys, limits,
                                      notifications)
from platform_core.public_api.tables import ApiNotification
from server.api.inventory import API_V1_PREFIX

PEPPER = "budget-test-pepper-" + "b" * 40
TOOL = "image.thumbnail"
SCOPES = ("tools:read", "jobs:create", "jobs:read")


@pytest.fixture()
def portal(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'budgets.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    monkeypatch.setenv("GEMINI_API_KEY", "stub-key-not-used")
    limits.reset()

    import platform_core.db as dbmod
    import platform_core.storage as storage_mod
    dbmod.reset_engine()
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())

    import apps.thumbnail.jobs as thumbnail_jobs
    monkeypatch.setattr(thumbnail_jobs, "_goi_gemini",
                        lambda *a, **k: b"\x89PNG\r\n\x1a\n" + b"0" * 100)

    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "budget-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": TOOL,
    })
    with TestClient(app, base_url="https://testserver") as client:
        yield client
    from server.api import deps
    deps.set_principal_resolver(None)
    storage_mod.set_storage(None)
    limits.reset()
    dbmod.reset_engine()


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
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def _account(client, credits: int = 500):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    email = f"bg-{uuid.uuid4().hex[:6]}@example.com"
    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=email, password="a-good-password-12")
        user.is_verified = True
        db.flush()
        credit.cap_tay(db, user.id, credits, by="test")
        db.commit()
        user_id = user.id
    finally:
        _close(gen)

    page = client.get("/login").text
    client.post("/login", data={"username": email,
                                "password": "a-good-password-12",
                                "csrf_token": _csrf(page)},
                follow_redirects=False)
    keys_page = client.get("/developers/keys").text
    created = client.post("/developers/keys",
                          data={"name": "budget", "csrf_token": _csrf(keys_page),
                                "scopes": list(SCOPES)})
    token = re.search(r"<code>(ltt_sk_[^<]+)</code>", created.text).group(1)
    return user_id, token


def _run(client, token, *, count: int = 1, key: str = ""):
    payload = {"topic": "budget", "count": count}
    quote = client.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": TOOL, "input": payload},
                        headers={"Authorization": f"Bearer {token}"})
    assert quote.status_code == 200, quote.text
    return client.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quote.json()["quote"], "input": payload},
        headers={"Authorization": f"Bearer {token}",
                 "Idempotency-Key": key or f"bg-{uuid.uuid4().hex[:8]}"})


def _ledger(user_id: str) -> list:
    import sqlalchemy as sa
    from platform_core.models import CreditEntry

    gen, db = _session()
    try:
        return [(row.kind, row.delta) for row in db.execute(
            sa.select(CreditEntry).where(CreditEntry.user_id == user_id)
            .order_by(CreditEntry.id)).scalars().all()]
    finally:
        _close(gen)


# ── The D3 fix: the ceiling counts API spending only ────────────────────────

def test_web_spending_does_not_consume_the_api_allowance(portal):
    """The defect EXT-01 found and D3 decided: a customer using the web app
    could exhaust the daily allowance that exists to bound a leaked API key."""
    from platform_core import credit

    user_id, token = _account(portal)
    assert _run(portal, token).status_code == 201        # 5 credits via the API

    # A job created the way the UI creates one: no API meta on its params.
    gen, db = _session()
    try:
        from platform_core.job_submit import submit_with_credit

        submit_with_credit(db, user_id=user_id, app_slug="thumbnail",
                           job_type="thumbnail.generate",
                           params={"topic": "made in the ui", "count": 4,
                                   "owner_id": user_id})
        db.commit()
        since = budgets.window_start(budgets.PERIOD_DAY)
        api_only = budgets.api_spend_since(db, user_id=user_id, since=since)
        everything = -sum(
            delta for kind, delta in _ledger(user_id) if delta < 0)
    finally:
        _close(gen)

    assert api_only == 5, "only the API job counts"
    assert everything > api_only, "the UI job did spend, it just is not counted"
    assert credit.so_du(*_balance_args(user_id)) >= 0


def _balance_args(user_id: str):
    gen, db = _session()
    try:
        from platform_core import credit

        return db, user_id
    finally:
        _close(gen)


# ── Hard caps ────────────────────────────────────────────────────────────────

def test_a_hard_cap_refuses_the_call_that_would_cross_it(portal):
    user_id, token = _account(portal)
    gen, db = _session()
    try:
        budgets.create(db, user_id=user_id, amount=10, period="day",
                       hard_cap=True)
        db.commit()
    finally:
        _close(gen)

    assert _run(portal, token).status_code == 201        # 5 of 10
    assert _run(portal, token).status_code == 201        # 10 of 10
    refused = _run(portal, token)                        # would be 15
    assert refused.status_code == 429
    body = refused.json()
    assert body["code"] == "quota_exceeded"
    # The refusal names which rule applied — otherwise every support
    # conversation about a 429 starts with an investigation.
    assert body["source"] == "budget" and body["limit"] == 10


def test_a_soft_budget_never_refuses_anything(portal):
    """Somebody who asked to be *told* at 80% must not be silently stopped."""
    user_id, token = _account(portal)
    gen, db = _session()
    try:
        budgets.create(db, user_id=user_id, amount=10, period="day",
                       hard_cap=False)
        db.commit()
    finally:
        _close(gen)

    for _ in range(4):
        assert _run(portal, token).status_code == 201    # 20 credits, over 10


def test_the_stricter_of_operator_and_customer_wins(portal):
    user_id, _token = _account(portal)
    gen, db = _session()
    try:
        budgets.create(db, user_id=user_id, amount=1000, period="day",
                       hard_cap=True)
        db.commit()
        # The operator allows less than the customer asked for.
        cap = budgets.effective_cap(db, user_id=user_id, operator_daily=50)
        assert cap["limit"] == 50 and cap["source"] == "operator"
        # …and the other way around.
        cap = budgets.effective_cap(db, user_id=user_id, operator_daily=5000)
        assert cap["limit"] == 1000 and cap["source"] == "budget"
    finally:
        _close(gen)


def test_a_budget_never_writes_to_the_ledger(portal):
    """The property that makes a self-service field safe to put near money."""
    user_id, token = _account(portal)
    assert _run(portal, token).status_code == 201
    before = _ledger(user_id)

    gen, db = _session()
    try:
        budget = budgets.create(db, user_id=user_id, amount=10, period="day",
                                hard_cap=True)
        db.commit()
        budgets.status(db, budget)
        alerting.scan_account(db, user_id=user_id)
        db.commit()
    finally:
        _close(gen)

    assert _ledger(user_id) == before


def test_a_replayed_call_is_not_counted_twice(portal):
    """Idempotent replay must not look like a second purchase to a budget."""
    user_id, token = _account(portal)
    payload = {"topic": "budget", "count": 1}
    quote = portal.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": TOOL, "input": payload},
                        headers={"Authorization": f"Bearer {token}"}).json()
    body = {"tool": TOOL, "quote": quote["quote"], "input": payload}
    headers = {"Authorization": f"Bearer {token}",
               "Idempotency-Key": f"bg-replay-{uuid.uuid4().hex[:6]}"}

    first = portal.post(f"{API_V1_PREFIX}/jobs", json=body, headers=headers)
    assert first.status_code == 201
    # The identical request again — which is what a client retrying a timeout
    # sends, and the only thing that counts as a replay.
    again = portal.post(f"{API_V1_PREFIX}/jobs", json=body, headers=headers)
    assert again.status_code == 200 and again.json()["id"] == first.json()["id"]

    gen, db = _session()
    try:
        spent = budgets.api_spend_since(
            db, user_id=user_id, since=budgets.window_start("day"))
    finally:
        _close(gen)
    assert spent == 5


def test_a_project_budget_only_counts_that_project(portal):
    from platform_core.public_api import projects

    user_id, token = _account(portal)
    assert _run(portal, token).status_code == 201

    gen, db = _session()
    try:
        other = projects.create(db, user_id=user_id, name="Elsewhere")
        db.commit()
        since = budgets.window_start("day")
        assert budgets.api_spend_since(db, user_id=user_id, since=since,
                                       project_id=other.id) == 0
        assert budgets.api_spend_since(db, user_id=user_id, since=since) == 5
    finally:
        _close(gen)


# ── Alerts ───────────────────────────────────────────────────────────────────

def _alerts(user_id: str) -> list:
    gen, db = _session()
    try:
        return notifications.list_for(db, user_id=user_id)
    finally:
        _close(gen)


def test_crossing_a_threshold_raises_one_alert_not_many(portal):
    user_id, token = _account(portal)
    gen, db = _session()
    try:
        budgets.create(db, user_id=user_id, amount=10, period="day")
        db.commit()
    finally:
        _close(gen)
    assert _run(portal, token).status_code == 201        # 5 of 10 = 50%

    gen, db = _session()
    try:
        first = alerting.scan_account(db, user_id=user_id)
        db.commit()
        again = alerting.scan_account(db, user_id=user_id)
        db.commit()
    finally:
        _close(gen)

    kinds = [row.kind for row in first]
    assert notifications.BUDGET_THRESHOLD in kinds
    assert again == [], "the same condition must not alert twice in cooldown"


def test_each_threshold_is_its_own_news(portal):
    user_id, token = _account(portal)
    gen, db = _session()
    try:
        budgets.create(db, user_id=user_id, amount=10, period="day")
        db.commit()
    finally:
        _close(gen)

    _run(portal, token)                                   # 50%
    gen, db = _session()
    try:
        alerting.scan_account(db, user_id=user_id)
        db.commit()
    finally:
        _close(gen)

    _run(portal, token)                                   # 100%
    gen, db = _session()
    try:
        raised = alerting.scan_account(db, user_id=user_id)
        db.commit()
    finally:
        _close(gen)
    assert any(row.kind == notifications.BUDGET_EXCEEDED for row in raised)


def test_a_low_balance_is_raised_once_a_day(portal):
    user_id, _token = _account(portal, credits=5)
    gen, db = _session()
    try:
        first = alerting.scan_account(db, user_id=user_id)
        db.commit()
        second = alerting.scan_account(db, user_id=user_id)
        db.commit()
        assert any(row.kind == notifications.LOW_CREDIT for row in first)
        assert second == []
        # …and again once the cooldown has passed.
        later = datetime.now(timezone.utc) + timedelta(days=2)
        third = alerting.scan_account(db, user_id=user_id, now=later)
        db.commit()
        assert any(row.kind == notifications.LOW_CREDIT for row in third)
    finally:
        _close(gen)


def test_an_expiring_key_is_flagged_before_it_dies(portal):
    user_id, _token = _account(portal)
    gen, db = _session()
    try:
        devkeys.issue(db, user_id=user_id, name="short",
                      expires_at=datetime.now(timezone.utc) + timedelta(days=3),
                      env={devkeys.PEPPER_ENV: PEPPER})
        db.commit()
        raised = alerting.scan_account(db, user_id=user_id)
        db.commit()
    finally:
        _close(gen)
    assert any(row.kind == notifications.KEY_EXPIRING for row in raised)


def test_a_dead_webhook_endpoint_is_reported(portal):
    from platform_core.public_api.tables import (WEBHOOK_DEAD, WebhookDelivery,
                                                 WebhookSubscription)
    from platform_core import secretbox

    user_id, _token = _account(portal)
    gen, db = _session()
    try:
        subscription = WebhookSubscription(
            id=str(uuid.uuid4()), user_id=user_id, url="https://example.com/x",
            secret_enc=secretbox.ma_hoa("s" * 32), events=[], enabled=True,
            created_at=datetime.now(timezone.utc))
        db.add(subscription)
        for index in range(alerting.DEAD_DELIVERY_THRESHOLD):
            db.add(WebhookDelivery(
                id=str(uuid.uuid4()), subscription_id=subscription.id,
                user_id=user_id, event_id=f"e{index}", event_type="job.succeeded",
                payload={}, status=WEBHOOK_DEAD, attempts=6,
                next_attempt_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc)))
        db.commit()
        raised = alerting.scan_account(db, user_id=user_id)
        db.commit()
    finally:
        _close(gen)
    assert any(row.kind == notifications.WEBHOOK_FAILING for row in raised)


def test_only_money_and_credentials_are_worth_an_email():
    for kind in (notifications.LOW_CREDIT, notifications.BUDGET_EXCEEDED,
                 notifications.KEY_EXPIRING):
        assert kind in notifications.EMAIL_KINDS
    # A threshold the customer set to be informed by is not an interruption.
    assert notifications.BUDGET_THRESHOLD not in notifications.EMAIL_KINDS


def test_an_email_failure_does_not_lose_the_alert(portal):
    class _Broken:
        def send(self, email):
            raise RuntimeError("smtp is down")

    user_id, _token = _account(portal, credits=1)
    gen, db = _session()
    try:
        raised = alerting.scan_account(db, user_id=user_id)
        db.commit()
        row = next(item for item in raised
                   if item.kind == notifications.LOW_CREDIT)
        assert notifications.send_email_for(db, row, mailer=_Broken()) is False
    finally:
        _close(gen)
    assert any(item.kind == notifications.LOW_CREDIT
               for item in _alerts(user_id))


# ── Validation and tenancy ───────────────────────────────────────────────────

@pytest.mark.parametrize("amount", [0, 5, -100, "abc"])
def test_a_useless_budget_is_refused(portal, amount):
    user_id, _token = _account(portal)
    gen, db = _session()
    try:
        with pytest.raises(budgets.BudgetError):
            budgets.create(db, user_id=user_id, amount=amount, period="day")
    finally:
        _close(gen)


def test_thresholds_are_bounded(portal):
    with pytest.raises(budgets.BudgetError):
        budgets.normalize_thresholds([3])
    with pytest.raises(budgets.BudgetError):
        budgets.normalize_thresholds([150])
    assert budgets.normalize_thresholds([80, 50, 50]) == [50, 80]


def test_one_account_never_sees_another_accounts_budget_or_alerts(portal):
    first_id, _token = _account(portal)
    gen, db = _session()
    try:
        budgets.create(db, user_id=first_id, amount=99, period="day")
        notifications.raise_alert(db, user_id=first_id,
                                  kind=notifications.LOW_CREDIT,
                                  subject="balance", title="AliceOnlyAlert")
        db.commit()
    finally:
        _close(gen)

    portal.post("/logout", data={}, follow_redirects=False)
    _account(portal)
    assert "AliceOnlyAlert" not in portal.get("/developers/notifications").text
    assert "99" not in _budget_cell(portal.get("/developers/usage").text)


def _budget_cell(html: str) -> str:
    match = re.search(r"Ngân sách của bạn.*?</div>", html, re.S)
    return match.group(0) if match else ""


# ── The pages ────────────────────────────────────────────────────────────────

def test_a_budget_can_be_created_and_deleted_from_the_page(portal):
    user_id, _token = _account(portal)
    page = portal.get("/developers/usage").text
    portal.post("/developers/budgets",
                data={"amount": "250", "period": "month", "project_id": "",
                      "hard_cap": "1", "csrf_token": _csrf(page)},
                follow_redirects=False)

    gen, db = _session()
    try:
        rows = budgets.list_for(db, user_id=user_id)
        assert len(rows) == 1 and rows[0].amount == 250
        assert rows[0].hard_cap is True
        budget_id = rows[0].id
    finally:
        _close(gen)

    page = portal.get("/developers/usage").text
    assert "250" in page
    portal.post(f"/developers/budgets/{budget_id}/delete",
                data={"csrf_token": _csrf(page)}, follow_redirects=False)
    gen, db = _session()
    try:
        assert budgets.list_for(db, user_id=user_id) == []
    finally:
        _close(gen)


def _usage_rows(html: str) -> str:
    """Just the results table: the filter dropdown lists every tool whatever
    the filter is, so searching the whole page proves nothing."""
    match = re.search(r"Chi tiêu theo lời gọi.*?</table>", html, re.S)
    if not match:
        return ""
    body = re.search(r"<tbody>.*?</tbody>", match.group(0), re.S)
    return body.group(0) if body else ""


def test_the_usage_page_filters_by_tool_key_and_status(portal):
    _user_id, token = _account(portal)
    assert _run(portal, token).status_code == 201

    assert TOOL in _usage_rows(portal.get(f"/developers/usage?tool={TOOL}").text)
    assert TOOL not in _usage_rows(
        portal.get("/developers/usage?tool=image.generate").text)
    # The job is queued, not succeeded, so filtering on succeeded empties it.
    assert TOOL not in _usage_rows(
        portal.get("/developers/usage?status=succeeded").text)
    assert TOOL in _usage_rows(
        portal.get("/developers/usage?status=queued").text)


def test_the_notifications_page_marks_everything_read(portal):
    user_id, _token = _account(portal, credits=1)
    gen, db = _session()
    try:
        alerting.scan_account(db, user_id=user_id)
        db.commit()
        assert notifications.unread_count(db, user_id=user_id) >= 1
    finally:
        _close(gen)

    page = portal.get("/developers/notifications").text
    portal.post("/developers/notifications/read",
                data={"csrf_token": _csrf(page)}, follow_redirects=False)
    gen, db = _session()
    try:
        assert notifications.unread_count(db, user_id=user_id) == 0
    finally:
        _close(gen)


def test_the_worker_scans_for_alerts():
    """A scanner nobody runs is a scanner that never fires."""
    from pathlib import Path

    source = Path("platform_core/job_runner.py").read_text(encoding="utf-8")
    assert "alerting.scan_all" in source
    assert "notifications.purge_expired" in source
