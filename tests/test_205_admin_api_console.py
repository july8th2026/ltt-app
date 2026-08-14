"""EXT-13 — the API admin console: what an operator can see, and change, and prove.

The acceptance is two sentences long, and both are about trust rather than
features: a non-admin is blocked, and every admin mutation is audited. So most of
what is checked here is refusal and evidence.

Three further properties are defended because losing any of them turns an
operator page into a liability:

* **no secret recovery.** No page returns a key, a webhook secret or a provider
  credential. The digest is one-way, and a console that appeared to look a key up
  would be either a lie or an exfiltration route;
* **destructive actions state a reason and are confirmed.** The audit row is read
  months later by somebody who was not there;
* **every list is bounded.** These tables grow with traffic, so an operator page
  that scans is a page that falls over on the day it is needed.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import admin_console, keys as devkeys

PEPPER = "admin-console-pepper-" + "a" * 40
TOOL = "image.thumbnail"
ADMIN_EMAIL = "operator@example.com"
PASSWORD = "a-good-password-12"


@pytest.fixture()
def console(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'adminapi.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "admin-console-secret")
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    monkeypatch.setenv("LTT_PUBLIC_API", "1")
    monkeypatch.setenv("LTT_PUBLIC_API_TOOLS", TOOL)
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

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


def _issue_key(user_id: str, *, mode: str = "live", name: str = "svc") -> str:
    """A real key through the real issuing path, so the row is realistic."""
    from platform_core.public_api import projects

    gen, db = _session()
    try:
        project = projects.default_for(db, user_id=user_id)
        db.flush()
        key, _token = devkeys.issue(db, user_id=user_id, name=name,
                                    scopes=("tools:read", "jobs:read"),
                                    project_id=project.id, mode=mode)
        db.commit()
        return key.key_id
    finally:
        _close(gen)


def _audit_rows() -> list:
    from sqlalchemy import select

    from platform_core.models import NhatKyAdmin

    gen, db = _session()
    try:
        return db.execute(select(NhatKyAdmin).order_by(
            NhatKyAdmin.id)).scalars().all()
    finally:
        _close(gen)


def _key_row(key_id: str):
    gen, db = _session()
    try:
        key = admin_console.key_by_id(db, key_id)
        return {"enabled": key.enabled, "revoked_at": key.revoked_at,
                "status": key.status()}
    finally:
        _close(gen)


def _token(client, key_id: str) -> str:
    """A CSRF token for an operator POST.

    Read from the key's own page when it still offers actions; a revoked key's
    page deliberately offers none, so fall back to another operator page that
    issues one. The token belongs to the session, not to the page.
    """
    page = client.get(f"/admin/api-khoa?key={key_id}").text
    found = re.search(r'name="csrf_token" value="([^"]+)"', page)
    if found:
        return found.group(1)
    return _csrf(client.get("/admin/grant-credit").text)


def _act(client, key_id: str, op: str, *, reason: str, confirm: bool = False):
    data = {"csrf_token": _token(client, key_id), "key_id": key_id, "op": op,
            "reason": reason}
    if confirm:
        data["confirm"] = "1"
    return client.post("/admin/api-khoa-action", data=data,
                       follow_redirects=False)


PAGES = ("/admin/api-tong-quan", "/admin/api-tai-khoan", "/admin/api-khoa",
         "/admin/api-cong-cu")


# ── Non-admin is blocked ─────────────────────────────────────────────────────

def test_a_signed_out_visitor_reaches_no_admin_page(console):
    for path in PAGES:
        answer = console.get(path, follow_redirects=False)
        assert answer.status_code in (302, 303, 307), (path, answer.status_code)
        assert "/login" in answer.headers.get("location", ""), path


def test_an_ordinary_customer_reaches_no_admin_page(console):
    """A signed-in developer is still not an operator.

    This is the case worth testing: the customer already has a valid session
    cookie for the same host, so nothing but the role check stands between them
    and every other account's credentials.
    """
    _make_user("customer@example.com")
    _login(console, "customer@example.com")
    for path in PAGES:
        answer = console.get(path, follow_redirects=False)
        assert answer.status_code in (302, 303, 307), (path, answer.status_code)
        assert "/login" in answer.headers.get("location", ""), path


def test_an_ordinary_customer_cannot_revoke_a_key(console):
    owner = _make_user("owner@example.com")
    key_id = _issue_key(owner)
    _make_user("attacker@example.com")
    _login(console, "attacker@example.com")

    answer = console.post("/admin/api-khoa-action",
                          data={"key_id": key_id, "op": "revoke",
                                "reason": "taking this over", "confirm": "1"},
                          follow_redirects=False)
    assert answer.status_code in (302, 303, 307, 400, 403)
    assert _key_row(key_id)["revoked_at"] is None, "a customer revoked a key"
    assert _audit_rows() == []


def test_an_operator_reaches_every_page(console):
    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)
    for path in PAGES:
        answer = console.get(path)
        assert answer.status_code == 200, (path, answer.status_code)
        assert 'aria-label="Điều hướng quản trị"' in answer.text, path


# ── Every mutation is audited ────────────────────────────────────────────────

def test_disabling_a_key_writes_one_audit_row_with_its_reason(console):
    owner = _make_user("dev1@example.com")
    key_id = _issue_key(owner)
    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)

    answer = _act(console, key_id, "disable", reason="suspected leak in CI logs")
    assert answer.status_code == 303, answer.text[:300]

    assert _key_row(key_id)["enabled"] is False
    assert _key_row(key_id)["status"] == "disabled"

    rows = _audit_rows()
    assert len(rows) == 1
    row = rows[0]
    assert row.hanh_dong == "api_khoa_disable"
    assert key_id in row.doi_tuong and owner in row.doi_tuong
    assert "suspected leak in CI logs" in row.chi_tiet
    assert row.admin_email == ADMIN_EMAIL, "the audit row must name who acted"


def test_revoking_a_key_is_audited_and_one_way(console):
    owner = _make_user("dev2@example.com")
    key_id = _issue_key(owner)
    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)

    assert _act(console, key_id, "revoke", reason="key published to a public repo",
                confirm=True).status_code == 303
    assert _key_row(key_id)["revoked_at"] is not None

    # …and a second attempt refuses rather than pretending to work again.
    again = _act(console, key_id, "revoke", reason="key published to a repo",
                 confirm=True)
    assert again.status_code == 303
    assert "err=" in again.headers["location"]

    rows = _audit_rows()
    assert [row.hanh_dong for row in rows] == ["api_khoa_revoke"], (
        "the refused second attempt must not be recorded as an action")


def test_enabling_a_disabled_key_is_audited_too(console):
    owner = _make_user("dev3@example.com")
    key_id = _issue_key(owner)
    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)

    _act(console, key_id, "disable", reason="paused during incident 42")
    _act(console, key_id, "enable", reason="incident 42 closed, safe to resume")

    assert _key_row(key_id)["enabled"] is True
    assert [row.hanh_dong for row in _audit_rows()] == ["api_khoa_disable",
                                                        "api_khoa_enable"]


def test_a_revoked_key_cannot_be_enabled_back(console):
    """The one-way property, stated where an operator would try to break it."""
    owner = _make_user("dev4@example.com")
    key_id = _issue_key(owner)
    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)

    _act(console, key_id, "revoke", reason="rotating away from this key",
         confirm=True)
    answer = _act(console, key_id, "enable", reason="actually we still need it")

    assert answer.status_code == 303 and "err=" in answer.headers["location"]
    assert _key_row(key_id)["revoked_at"] is not None
    assert [row.hanh_dong for row in _audit_rows()] == ["api_khoa_revoke"]


# ── Dangerous actions demand a reason and a confirmation ─────────────────────

def test_a_mutation_without_a_reason_changes_nothing(console):
    owner = _make_user("dev5@example.com")
    key_id = _issue_key(owner)
    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)

    for reason in ("", "   ", "oops"):
        answer = _act(console, key_id, "disable", reason=reason)
        assert answer.status_code == 303
        assert "err=" in answer.headers["location"], reason
    assert _key_row(key_id)["enabled"] is True
    assert _audit_rows() == []


def test_revoking_without_ticking_the_confirmation_changes_nothing(console):
    owner = _make_user("dev6@example.com")
    key_id = _issue_key(owner)
    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)

    answer = _act(console, key_id, "revoke", reason="a perfectly good reason",
                  confirm=False)
    assert answer.status_code == 303 and "err=" in answer.headers["location"]
    assert _key_row(key_id)["revoked_at"] is None
    assert _audit_rows() == []


def test_a_mutation_without_csrf_changes_nothing(console):
    owner = _make_user("dev7@example.com")
    key_id = _issue_key(owner)
    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)

    answer = console.post("/admin/api-khoa-action",
                          data={"key_id": key_id, "op": "disable",
                                "reason": "no csrf token attached"})
    assert answer.status_code == 400
    assert _key_row(key_id)["enabled"] is True
    assert _audit_rows() == []


def test_an_unknown_operation_is_refused(console):
    owner = _make_user("dev8@example.com")
    key_id = _issue_key(owner)
    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)

    answer = _act(console, key_id, "delete", reason="just remove it entirely")
    assert answer.status_code == 400
    assert _audit_rows() == []


def test_the_confirmation_wording_is_actually_on_the_page(console):
    """A confirmation the operator never sees is not a confirmation."""
    owner = _make_user("dev9@example.com")
    key_id = _issue_key(owner)
    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)

    page = console.get(f"/admin/api-khoa?key={key_id}").text
    assert 'name="confirm"' in page
    assert "không đảo ngược" in page
    assert 'name="reason"' in page
    assert f'minlength="{admin_console.MIN_REASON}"' in page


# ── No secret recovery ───────────────────────────────────────────────────────

def test_no_admin_page_returns_key_material(console):
    """Not "we do not show it" — there is nothing to show.

    The digest and its pepper version are the only stored artefacts of a key,
    and neither belongs on a screen: printing a digest invites somebody to
    treat it as a credential, and printing the pepper version narrows an
    offline attack.
    """
    owner = _make_user("dev10@example.com")

    from platform_core.public_api import projects

    gen, db = _session()
    try:
        project = projects.default_for(db, user_id=owner)
        db.flush()
        key, token = devkeys.issue(db, user_id=owner, name="secret probe",
                                   scopes=("tools:read",),
                                   project_id=project.id)
        db.commit()
        key_id, digest = key.key_id, key.verifier_digest
    finally:
        _close(gen)

    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)

    secret = token.split("_", 3)[-1]
    for path in (*PAGES, f"/admin/api-khoa?key={key_id}",
                 f"/admin/api-tai-khoan?user={owner}"):
        body = console.get(path).text
        assert secret not in body, path
        assert digest not in body, path
        assert "verifier_digest" not in body, path


def test_a_webhook_secret_never_appears_on_an_admin_page(console):
    owner = _make_user("dev11@example.com")
    _issue_key(owner)

    from platform_core import secretbox
    from platform_core.public_api import webhooks
    from platform_core.public_api.tables import WebhookSubscription

    gen, db = _session()
    try:
        secret = webhooks.new_secret()
        db.add(WebhookSubscription(
            id=str(uuid.uuid4()), user_id=owner,
            url="https://receiver.example.com/hook",
            # Stored encrypted, exactly as `POST /api/v1/webhooks` stores it.
            secret_enc=secretbox.ma_hoa(secret),
            events=list(webhooks.TERMINAL_EVENTS), enabled=True,
            created_at=datetime.now(timezone.utc)))
        db.commit()
    finally:
        _close(gen)

    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)
    body = console.get(f"/admin/api-tai-khoan?user={owner}").text
    assert "receiver.example.com" in body, "the endpoint itself is operational"
    assert secret not in body, "the signing secret leaked into an admin page"


# ── Bounded reads ────────────────────────────────────────────────────────────

def test_the_key_list_pages_rather_than_scanning(console):
    owner = _make_user("bulk@example.com")
    for index in range(7):
        _issue_key(owner, name=f"key-{index}")

    gen, db = _session()
    try:
        page = admin_console.keys_page(db, limit=3, offset=0)
        assert len(page.rows) == 3 and page.total == 7 and page.has_more
        second = admin_console.keys_page(db, limit=3, offset=3)
        assert len(second.rows) == 3 and second.has_more
        last = admin_console.keys_page(db, limit=3, offset=6)
        assert len(last.rows) == 1 and not last.has_more
        # …and a caller asking for everything still gets a bounded page.
        huge = admin_console.keys_page(db, limit=10_000, offset=0)
        assert huge.limit == admin_console.MAX_PAGE_SIZE
    finally:
        _close(gen)


def test_filters_narrow_the_key_list_by_derived_state(console):
    owner = _make_user("filter@example.com")
    live = _issue_key(owner, name="live one")
    test = _issue_key(owner, mode="test", name="test one")
    gone = _issue_key(owner, name="gone")

    gen, db = _session()
    try:
        devkeys.revoke(db, admin_console.key_by_id(db, gone))
        db.commit()

        ids = lambda page: {row["key"].key_id for row in page.rows}  # noqa: E731
        assert ids(admin_console.keys_page(db, mode="test")) == {test}
        assert ids(admin_console.keys_page(db, mode="live")) == {live, gone}
        assert ids(admin_console.keys_page(db, status="revoked")) == {gone}
        assert ids(admin_console.keys_page(db, status="active")) == {live, test}
        assert ids(admin_console.keys_page(db, query="filter@example.com")) == {
            live, test, gone}
    finally:
        _close(gen)


def test_an_expired_key_is_filtered_as_expired_not_active(console):
    """The derived state, not the column — the same word the customer sees."""
    owner = _make_user("expiry@example.com")

    from platform_core.public_api import projects

    gen, db = _session()
    try:
        project = projects.default_for(db, user_id=owner)
        db.flush()
        key, _token = devkeys.issue(
            db, user_id=owner, name="old", scopes=("tools:read",),
            project_id=project.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=1))
        # Issuing with a past expiry is refused, and rightly so — a key that is
        # dead on arrival is a mistake, not a feature. So the row is aged here
        # to reach the state a real key reaches by waiting.
        key.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()
        key_id = key.key_id

        assert {row["key"].key_id
                for row in admin_console.keys_page(db, status="expired").rows
                } == {key_id}
        assert admin_console.keys_page(db, status="active").rows == []
    finally:
        _close(gen)


def test_the_account_list_only_holds_accounts_with_keys(console):
    """An operator on the API console is asking about API users.

    The full customer base already has a page; repeating it here would bury the
    twelve accounts that matter under ten thousand that do not.
    """
    with_key = _make_user("hasakey@example.com")
    _make_user("nokey@example.com")
    _issue_key(with_key)

    gen, db = _session()
    try:
        page = admin_console.accounts_page(db)
        emails = {row["user"].email for row in page.rows}
        assert emails == {"hasakey@example.com"}
    finally:
        _close(gen)


# ── What the pages actually say ──────────────────────────────────────────────

def test_the_overview_counts_live_and_test_keys_apart(console):
    owner = _make_user("mix@example.com", credits=50)
    _issue_key(owner, name="live")
    _issue_key(owner, mode="test", name="test")

    gen, db = _session()
    try:
        data = admin_console.overview(db)
        assert data["keys"]["live"] == 1
        assert data["keys"]["test"] == 1
        assert data["keys"]["revoked"] == 0
        assert data["accounts_with_keys"] == 1
    finally:
        _close(gen)


def test_a_revoked_key_leaves_the_active_count_and_stays_countable(console):
    owner = _make_user("revoked@example.com")
    key_id = _issue_key(owner)

    gen, db = _session()
    try:
        devkeys.revoke(db, admin_console.key_by_id(db, key_id))
        db.commit()
        data = admin_console.overview(db)
        assert data["keys"]["live"] == 0
        assert data["keys"]["revoked"] == 1
        assert data["keys"]["total"] == 1, "evidence is kept, not deleted"
    finally:
        _close(gen)


def test_the_tools_page_separates_declared_from_published(console):
    """Two conditions, shown as two facts.

    A tool its app declares public but the deployment has not switched on is a
    normal state. Collapsing the two into one "enabled" column is how "why can
    nobody call this" becomes unanswerable from the console.
    """
    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)

    from platform_core.public_api.config import load_public_api_config

    gen, db = _session()
    try:
        rows = admin_console.tools_page(
            db, load_public_api_config({"LTT_PUBLIC_API": "1",
                                        "LTT_PUBLIC_API_TOOLS": TOOL}))
    finally:
        _close(gen)

    by_name = {row["name"]: row for row in rows}
    assert by_name[TOOL]["published"] is True
    others = [row for name, row in by_name.items() if name != TOOL]
    assert others, "this test assumes more than one tool declares itself public"
    assert all(row["published"] is False for row in others)
    assert all(row["declared"] is True for row in rows)

    page = console.get("/admin/api-cong-cu").text
    assert "LTT_PUBLIC_API_TOOLS" in page
    assert "EXT-14" in page, "the page must not imply it has a kill switch"


def test_the_key_detail_page_shows_the_evidence_for_acting(console):
    owner = _make_user("evidence@example.com")
    key_id = _issue_key(owner, name="chatty")

    from platform_core.public_api import request_log

    gen, db = _session()
    try:
        for status, code in ((429, "rate_limited"), (200, "")):
            request_log.record(db, request_id=uuid.uuid4().hex, user_id=owner,
                               key_id=key_id, method="POST",
                               route="/api/v1/jobs", status=status, code=code,
                               latency_ms=12, tool=TOOL, credit_delta=-5)
        db.commit()
    finally:
        _close(gen)

    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)
    page = console.get(f"/admin/api-khoa?key={key_id}").text
    assert "rate_limited" in page
    assert "/api/v1/jobs" in page

    gen, db = _session()
    try:
        usage = admin_console.key_usage(db, key_id=key_id)
        assert usage["calls"] == 2 and usage["failed"] == 1
        assert usage["credit_spent"] == 10
    finally:
        _close(gen)


def test_the_full_profile_link_reaches_the_profile_page(console):
    """A link that lands on an empty search form is broken but answers 200.

    Found by clicking it, not by a test — which is why it now has one.
    """
    owner = _make_user("profile@example.com")
    _issue_key(owner)
    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)

    page = console.get(f"/admin/api-tai-khoan?user={owner}").text
    assert f'href="/admin/nguoi-dung?q={owner}"' in page

    profile = console.get(f"/admin/nguoi-dung?q={owner}")
    assert profile.status_code == 200
    assert "profile@example.com" in profile.text


def test_an_unknown_key_or_account_answers_404(console):
    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)
    assert console.get("/admin/api-khoa?key=nope").status_code == 404
    assert console.get(
        f"/admin/api-tai-khoan?user={uuid.uuid4()}").status_code == 404


def test_the_admin_navigation_links_the_api_section(console):
    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)
    page = console.get("/admin/api-tong-quan").text
    for path in PAGES:
        assert f'href="{path}"' in page, path
    assert 'aria-current="page"' in page


# ── The rules, without an HTTP app ───────────────────────────────────────────

def test_a_reason_shorter_than_the_minimum_is_refused():
    class _Key:
        revoked_at = None
        enabled = True

    for reason in (None, "", "  ", "short"):
        with pytest.raises(admin_console.AdminActionError):
            admin_console.disable_key(None, _Key(), reason=reason)
        with pytest.raises(admin_console.AdminActionError):
            admin_console.revoke_key(None, _Key(), reason=reason)


def test_clamp_page_survives_nonsense():
    assert admin_console.clamp_page(None, None) == (admin_console.PAGE_SIZE, 0)
    assert admin_console.clamp_page("abc", "xyz") == (admin_console.PAGE_SIZE, 0)
    assert admin_console.clamp_page(-5, -5) == (1, 0)
    assert admin_console.clamp_page(10_000, 10) == (
        admin_console.MAX_PAGE_SIZE, 10)


# ── The policy and kill-switch pages (EXT-14) ────────────────────────────────

POLICY_PAGES = ("/admin/api-chinh-sach", "/admin/api-kill-switch")


def _post(client, path: str, page_path: str, data: dict):
    page = client.get(page_path).text
    return client.post(path, data={"csrf_token": _csrf(page), **data},
                       follow_redirects=False)


def test_the_policy_pages_are_operator_only(console):
    _make_user("nosy@example.com")
    _login(console, "nosy@example.com")
    for path in POLICY_PAGES:
        answer = console.get(path, follow_redirects=False)
        assert answer.status_code in (302, 303, 307), path
        assert "/login" in answer.headers.get("location", ""), path


def test_creating_a_policy_from_the_page_is_audited(console):
    from platform_core.public_api import policy

    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)

    answer = _post(console, "/admin/api-chinh-sach-action",
                   "/admin/api-chinh-sach",
                   {"op": "create", "name": "pro", "description": "paid tier",
                    "rpm_create": "40", "is_default": "1",
                    "reason": "new commercial tier agreed"})
    assert answer.status_code == 303, answer.text[:300]

    gen, db = _session()
    try:
        rows = policy.list_policies(db)
        assert len(rows) == 1
        assert rows[0].name == "pro" and rows[0].rpm_create == 40
        # Untouched fields stay NULL — inherit, not zero.
        assert rows[0].rpm_read is None
    finally:
        _close(gen)

    audit = _audit_rows()
    assert [row.hanh_dong for row in audit] == ["api_chinh_sach_create"]
    assert "new commercial tier agreed" in audit[0].chi_tiet
    assert audit[0].admin_email == ADMIN_EMAIL


def test_a_policy_change_without_a_reason_changes_nothing(console):
    from platform_core.public_api import policy

    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)
    answer = _post(console, "/admin/api-chinh-sach-action",
                   "/admin/api-chinh-sach",
                   {"op": "create", "name": "sneaky", "reason": "x"})
    assert answer.status_code == 303 and "err=" in answer.headers["location"]

    gen, db = _session()
    try:
        assert policy.list_policies(db) == []
    finally:
        _close(gen)
    assert _audit_rows() == []


def test_engaging_a_kill_switch_needs_confirmation_and_is_audited(console):
    from platform_core.public_api import policy

    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)

    refused = _post(console, "/admin/api-kill-switch-action",
                    "/admin/api-kill-switch",
                    {"op": "engage", "scope": "maintenance",
                     "reason": "database migration window"})
    assert refused.status_code == 303 and "err=" in refused.headers["location"]
    gen, db = _session()
    try:
        assert policy.active_switches(db) == []
    finally:
        _close(gen)
    assert _audit_rows() == []

    ok = _post(console, "/admin/api-kill-switch-action",
               "/admin/api-kill-switch",
               {"op": "engage", "scope": "maintenance", "confirm": "1",
                "reason": "database migration window"})
    assert ok.status_code == 303
    gen, db = _session()
    try:
        switches = policy.active_switches(db)
        assert len(switches) == 1
        assert switches[0].created_by == ADMIN_EMAIL
        assert switches[0].expires_at is None
    finally:
        _close(gen)
    assert [row.hanh_dong for row in _audit_rows()] == ["api_kill_engage"]


def test_a_switch_can_be_given_an_expiry_from_the_page(console):
    from platform_core.public_api import policy

    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)
    _post(console, "/admin/api-kill-switch-action", "/admin/api-kill-switch",
          {"op": "engage", "scope": "global_writes", "confirm": "1",
           "minutes": "30", "reason": "provider incident 91"})

    gen, db = _session()
    try:
        switch = policy.active_switches(db)[0]
        assert switch.expires_at is not None
    finally:
        _close(gen)


def test_releasing_a_switch_is_audited_too(console):
    from platform_core.public_api import policy

    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)
    _post(console, "/admin/api-kill-switch-action", "/admin/api-kill-switch",
          {"op": "engage", "scope": "maintenance", "confirm": "1",
           "reason": "database migration window"})

    gen, db = _session()
    try:
        switch_id = policy.active_switches(db)[0].id
    finally:
        _close(gen)

    _post(console, "/admin/api-kill-switch-action", "/admin/api-kill-switch",
          {"op": "release", "switch_id": switch_id,
           "reason": "migration finished, service restored"})

    gen, db = _session()
    try:
        assert policy.active_switches(db) == []
    finally:
        _close(gen)
    assert [row.hanh_dong for row in _audit_rows()] == ["api_kill_engage",
                                                        "api_kill_release"]


def test_the_policy_page_shows_where_each_number_comes_from(console):
    """The first question about any limit is "why is it that number"."""
    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)
    page = console.get("/admin/api-chinh-sach").text
    assert "Mức nền đang áp dụng" in page
    assert "global" in page
    assert "kế thừa" in page, "the page must say blank means inherit, not zero"


def test_the_kill_switch_page_says_its_scope_is_the_api(console):
    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)
    page = console.get("/admin/api-kill-switch").text
    assert "/api/v1" in page
    assert 'name="confirm"' in page
    assert "Không có công tắc nào đang bật" in page


# ── The pricing console and the margin view (EXT-15) ─────────────────────────

PRICING_PAGES = ("/admin/api-gia", "/admin/api-margin")


def test_the_pricing_pages_are_operator_only(console):
    _make_user("curious@example.com")
    _login(console, "curious@example.com")
    for path in PRICING_PAGES:
        answer = console.get(path, follow_redirects=False)
        assert answer.status_code in (302, 303, 307), path
        assert "/login" in answer.headers.get("location", ""), path


def test_creating_and_publishing_a_price_is_audited(console):
    from platform_core.public_api import pricing

    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)

    made = _post(console, "/admin/api-gia-action", "/admin/api-gia",
                 {"op": "create", "tool": "image.thumbnail", "label": "v1",
                  "max_credit": "40", "rounding_mode": "nearest",
                  "reason": "opening the commercial price"})
    assert made.status_code == 303, made.text[:300]

    gen, db = _session()
    try:
        rows = pricing.list_for(db, tool="image.thumbnail")
        assert len(rows) == 1 and rows[0].status == "draft"
        # A draft prices nothing until somebody publishes it.
        assert pricing.active_for(db, tool="image.thumbnail") is None
        version_id = rows[0].id
    finally:
        _close(gen)

    _post(console, "/admin/api-gia-action", "/admin/api-gia",
          {"op": "publish", "version_id": version_id, "tool": "image.thumbnail",
           "reason": "agreed with the product owner"})

    gen, db = _session()
    try:
        assert pricing.active_for(db, tool="image.thumbnail").label == "v1"
    finally:
        _close(gen)

    actions = [row.hanh_dong for row in _audit_rows()]
    assert actions == ["api_gia_create", "api_gia_publish"]
    assert "agreed with the product owner" in _audit_rows()[-1].chi_tiet


def test_a_price_change_without_a_reason_changes_nothing(console):
    from platform_core.public_api import pricing

    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)
    answer = _post(console, "/admin/api-gia-action", "/admin/api-gia",
                   {"op": "create", "tool": "image.thumbnail", "label": "sneaky",
                    "reason": "x"})
    assert answer.status_code == 303 and "err=" in answer.headers["location"]

    gen, db = _session()
    try:
        assert pricing.list_for(db) == []
    finally:
        _close(gen)
    assert _audit_rows() == []


def test_retiring_a_price_is_audited(console):
    from platform_core.public_api import pricing

    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)
    _post(console, "/admin/api-gia-action", "/admin/api-gia",
          {"op": "create", "tool": "image.thumbnail", "label": "v1",
           "rounding_mode": "nearest", "reason": "opening the price"})
    gen, db = _session()
    try:
        version_id = pricing.list_for(db)[0].id
    finally:
        _close(gen)
    _post(console, "/admin/api-gia-action", "/admin/api-gia",
          {"op": "publish", "version_id": version_id, "reason": "going live"})
    _post(console, "/admin/api-gia-action", "/admin/api-gia",
          {"op": "retire", "version_id": version_id,
           "reason": "withdrawing this tier"})

    assert [row.hanh_dong for row in _audit_rows()] == [
        "api_gia_create", "api_gia_publish", "api_gia_retire"]


def test_the_pricing_page_says_it_does_not_price(console):
    """The page has to explain the one thing about it people get wrong."""
    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)
    page = console.get("/admin/api-gia").text
    assert "credit_cost()" in page
    assert "hồi tố" in page


def test_the_margin_page_labels_its_cost_as_an_estimate(console):
    """A number that cannot be reconciled must not look like one that can."""
    _make_user(ADMIN_EMAIL, role="admin")
    _login(console, ADMIN_EMAIL)
    page = console.get("/admin/api-margin").text
    assert "ƯỚC LƯỢNG" in page
    assert "sổ credit" in page
    # With no rates configured the page must say why it is empty rather than
    # showing a confident zero.
    assert "Chưa cấu hình đơn giá" in page
