"""EXT-05 — the developer API area: one portal, reachable, tenant-safe.

The failure this file exists to prevent is the one the EXT-01 audit found: a
feature that works perfectly and that nobody can find. Everything else here is
about the second failure mode of a portal — showing one customer another
customer's integration.
"""
from __future__ import annotations

import re
import uuid

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import keys as devkeys, limits, projects

PEPPER = "devtab-test-pepper-" + "t" * 40

# Every section the area promises, and whether it is built. Named-but-unbuilt
# sections are rendered as plain text, never as links (EXT-08/09/11 own them).
BUILT = ("/developers", "/developers/projects", "/developers/keys",
         "/developers/tools", "/developers/jobs", "/developers/usage",
         "/developers/webhooks", "/developers/docs", "/developers/settings")


@pytest.fixture()
def portal(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'devtab.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    limits.reset()

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "devtab-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": "image.thumbnail",
    })
    # https, because the session cookie is marked secure.
    with TestClient(app, base_url="https://testserver") as client:
        yield client
    from server.api import deps
    deps.set_principal_resolver(None)
    limits.reset()
    dbmod.reset_engine()


def _csrf(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "no CSRF token on the page"
    return match.group(1)


def _register(client, email: str) -> None:
    """A verified account with credit, signed in."""
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung

    gen = get_session()
    db = next(gen)
    try:
        user = tao_nguoi_dung(db, email=email, password="a-good-password-12")
        user.is_verified = True
        db.flush()
        credit.cap_tay(db, user.id, 500, by="test")
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    page = client.get("/login")
    response = client.post("/login", data={
        "username": email, "password": "a-good-password-12",
        "csrf_token": _csrf(page.text)}, follow_redirects=False)
    assert response.status_code in (302, 303), response.text


# ── Reachability ─────────────────────────────────────────────────────────────

def test_the_api_area_is_two_clicks_from_anywhere_signed_in(portal):
    """The gap EXT-01 found: the portal existed and nothing linked to it."""
    _register(portal, f"nav-{uuid.uuid4().hex[:6]}@example.com")
    home = portal.get("/").text
    # One click opens the account menu, the second is this link.
    assert 'href="/developers"' in home


@pytest.mark.parametrize("path", BUILT)
def test_every_built_section_answers(portal, path):
    _register(portal, f"sec-{uuid.uuid4().hex[:6]}@example.com")
    response = portal.get(path)
    assert response.status_code == 200, path
    # Each section renders the shared shell, so navigation never disappears.
    assert 'class="dev-nav"' in response.text


def test_the_navigation_is_the_same_on_every_section(portal):
    _register(portal, f"same-{uuid.uuid4().hex[:6]}@example.com")
    links = None
    for path in BUILT:
        # Only the nav block: a section may of course link elsewhere in its body
        # (the overview's call-to-action does).
        block = re.search(r'<nav class="dev-nav".*?</nav>', portal.get(path).text,
                          re.S)
        assert block, path
        found = re.findall(r'<a href="(/developers[^"]*)"', block.group(0))
        if links is None:
            links = found
        assert found == links, path


def test_unbuilt_sections_are_named_but_not_linked(portal):
    """A dead link is worse than an honest label: the shape of the area is
    information a developer uses to plan; a 404 is not.

    Which sections are unbuilt is read from the declaration rather than listed
    here — the first version of this test named them, and building the
    playground turned a correct change into a red suite.
    """
    from server.routes.developer import SECTIONS

    _register(portal, f"soon-{uuid.uuid4().hex[:6]}@example.com")
    page = portal.get("/developers").text
    unbuilt = [(key, label) for key, href, label in SECTIONS if href is None]
    assert unbuilt, "every section is built — delete this test rather than lie"
    for key, label in unbuilt:
        # Named, so a developer knows the area is coming…
        assert label.lower() in page.lower(), label
        # …but not a link, and not a route that half-answers.
        assert f'href="/developers/{key}"' not in page, key
        assert portal.get(f"/developers/{key}").status_code == 404, key


def test_the_current_section_is_marked_for_assistive_technology(portal):
    _register(portal, f"aria-{uuid.uuid4().hex[:6]}@example.com")
    page = portal.get("/developers/keys").text
    assert 'aria-current="page"' in page
    assert page.count('aria-current="page"') == 1


def test_there_is_exactly_one_portal(portal):
    """No second place to manage a key: revoking the wrong one is a real cost."""
    _register(portal, f"one-{uuid.uuid4().hex[:6]}@example.com")
    for path in BUILT:
        text = portal.get(path).text
        # The creation form lives on exactly one section.
        if path != "/developers/keys":
            assert 'action="/developers/keys"' not in text, path


# ── Overview ─────────────────────────────────────────────────────────────────

def test_the_overview_answers_what_do_i_have_and_is_anything_wrong(portal):
    _register(portal, f"ov-{uuid.uuid4().hex[:6]}@example.com")
    page = portal.get("/developers").text
    for fragment in ("credit", "Project", "Webhook", "request/"):
        assert fragment.lower() in page.lower(), fragment


def test_a_new_account_is_told_the_three_steps_to_a_first_call(portal):
    """Empty state: the most common visit is the first one."""
    _register(portal, f"new-{uuid.uuid4().hex[:6]}@example.com")
    page = portal.get("/developers").text
    assert 'href="/developers/projects"' in page
    assert 'href="/developers/keys"' in page
    assert 'href="/developers/docs"' in page


def test_the_overview_counts_what_the_account_actually_has(portal):
    email = f"count-{uuid.uuid4().hex[:6]}@example.com"
    _register(portal, email)

    from platform_core.db import get_session
    from platform_core.models import User
    from sqlalchemy import select

    gen = get_session()
    db = next(gen)
    try:
        user = db.execute(select(User).where(User.email == email)).scalar_one()
        project = projects.create(db, user_id=user.id, name="Counted")
        devkeys.issue(db, user_id=user.id, project_id=project.id,
                      env={devkeys.PEPPER_ENV: PEPPER})
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    page = portal.get("/developers").text
    # One project, one active key — and the empty-state CTA is gone.
    assert "Counted" not in page          # the overview counts, it does not list
    assert ">1</strong>" in page


# ── Tenancy ──────────────────────────────────────────────────────────────────

def test_no_section_shows_another_account_anything(portal):
    first = f"a-{uuid.uuid4().hex[:6]}@example.com"
    _register(portal, first)

    from platform_core.db import get_session
    from platform_core.models import User
    from sqlalchemy import select

    gen = get_session()
    db = next(gen)
    try:
        alice = db.execute(select(User).where(User.email == first)).scalar_one()
        secret_project = projects.create(db, user_id=alice.id,
                                         name="AliceOnlyProject")
        key, _token = devkeys.issue(db, user_id=alice.id,
                                    project_id=secret_project.id,
                                    name="AliceOnlyKey",
                                    env={devkeys.PEPPER_ENV: PEPPER})
        alice_key_id = key.key_id
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    portal.post("/logout", data={}, follow_redirects=False)
    _register(portal, f"b-{uuid.uuid4().hex[:6]}@example.com")
    for path in BUILT:
        text = portal.get(path).text
        assert "AliceOnlyProject" not in text, path
        assert "AliceOnlyKey" not in text, path
        assert alice_key_id not in text, path


def test_every_section_needs_a_session(portal):
    for path in BUILT:
        response = portal.get(path, follow_redirects=False)
        assert response.status_code in (302, 303), path
        assert "/login" in response.headers.get("location", ""), path


def test_writes_still_need_a_csrf_token(portal):
    _register(portal, f"csrf-{uuid.uuid4().hex[:6]}@example.com")
    before = portal.get("/developers/projects").text
    refused = portal.post("/developers/projects",
                          data={"name": "NoToken"}, follow_redirects=False)
    assert refused.status_code in (302, 303)
    assert "NoToken" not in portal.get("/developers/projects").text
    assert "NoToken" not in before


# ── Sections carry their own content ─────────────────────────────────────────

def test_the_tools_section_lists_what_this_deployment_sells(portal):
    _register(portal, f"tool-{uuid.uuid4().hex[:6]}@example.com")
    page = portal.get("/developers/tools").text
    assert "image.thumbnail" in page
    assert "ASYNC_JOB" in page
    # …and never how it is implemented.
    for leak in ("gemini", "thumbnail.", "provider", "credential"):
        assert leak.lower() not in page.lower(), leak


def test_the_docs_section_gives_a_runnable_first_call(portal):
    _register(portal, f"doc-{uuid.uuid4().hex[:6]}@example.com")
    page = portal.get("/developers/docs").text
    assert "curl" in page and "/api/v1/me" in page
    assert "Authorization: Bearer" in page


def test_creating_a_project_lands_back_on_the_projects_section(portal):
    _register(portal, f"flow-{uuid.uuid4().hex[:6]}@example.com")
    page = portal.get("/developers/projects")
    created = portal.post("/developers/projects",
                          data={"name": "Flow", "csrf_token": _csrf(page.text)},
                          follow_redirects=False)
    assert created.status_code == 303
    assert created.headers["location"] == "/developers/projects"
    assert "Flow" in portal.get("/developers/projects").text
