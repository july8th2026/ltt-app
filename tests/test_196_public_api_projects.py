"""EXT-04 — the ownership hierarchy: account → project → key.

Two questions decide whether this layer is worth having, and both are answered
by behaviour rather than by the schema:

* can an owner retire one integration without disturbing another, and
* does retiring one destroy any evidence about money that already moved?
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import keys as devkeys, limits, projects
from platform_core.public_api.tables import (ApiProject, PROJECT_ACTIVE,
                                             PROJECT_ARCHIVED)
from platform_core.public_api.scopes import (SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
                                             SCOPE_TOOLS_READ)
from platform_core.registry import AppManifest, LoadedApp, ToolSpec
from server.api.context import is_trusted_peer
from server.api.inventory import API_V1_PREFIX

PEPPER = "projects-test-pepper-" + "j" * 40
TOOL = "text.projected"
ALL_SCOPES = (SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ)


def _cost(params: dict) -> int:
    return 5


def _fixture_apps():
    tool = ToolSpec(
        name=TOOL, job_type="sampleproj.generate", description="Fixture tool.",
        params_schema={"prompt": {"type": "string", "required": True,
                                  "max_length": 100}},
        returns={"text": "text"}, api_exposed=True,
        api_contract={"scopes": (SCOPE_JOBS_CREATE,)})
    manifest = AppManifest(
        slug="sampleproj", display_name="Sample", route_prefix="/sampleproj",
        job_types=("sampleproj.generate",), credit_cost=_cost,
        lifecycle="released", surface="customer", tools=(tool,))
    return [LoadedApp(manifest=manifest, router=None, error="")]


@pytest.fixture()
def api(tmp_path, monkeypatch):
    import platform_core.registry as registry_mod
    monkeypatch.setattr(registry_mod, "discover", _fixture_apps)
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'projects.db').as_posix()}")
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
        "LTT_SESSION_SECRET": "projects-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": TOOL,
    })
    with TestClient(app) as client:
        yield client
    from server.api import deps
    deps.set_principal_resolver(None)
    limits.reset()
    dbmod.reset_engine()


@pytest.fixture()
def db(api):
    from platform_core.db import get_session

    gen = get_session()
    session = next(gen)
    try:
        yield session
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _user(db, credits: int = 500):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    user = tao_nguoi_dung(db, email=f"pj-{uuid.uuid4().hex[:8]}@example.com",
                          password="a-good-password-12")
    db.flush()
    credit.cap_tay(db, user.id, credits, by="test")
    db.commit()
    return user


def _key(db, user, *, project=None, **kwargs):
    key, token = devkeys.issue(db, user_id=user.id, scopes=ALL_SCOPES,
                               project_id=project.id if project else "",
                               env={devkeys.PEPPER_ENV: PEPPER}, **kwargs)
    db.commit()
    return key, token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Hierarchy ────────────────────────────────────────────────────────────────

def test_a_project_belongs_to_one_account_and_slugs_are_unique_within_it(db):
    alice, bob = _user(db), _user(db)
    first = projects.create(db, user_id=alice.id, name="Web Site")
    second = projects.create(db, user_id=alice.id, name="Web Site")
    theirs = projects.create(db, user_id=bob.id, name="Web Site")
    db.commit()

    assert first.slug == "web-site"
    # Two integrations with the same name is a normal thing to want; refusing
    # the second teaches nothing, so it is suffixed instead.
    assert second.slug == "web-site-2"
    # …but the namespace is per account, so another customer keeps the clean one.
    assert theirs.slug == "web-site"


def test_a_vietnamese_name_becomes_a_readable_slug(db):
    """A slug exists to be read in a log line; a row of dashes is not that."""
    user = _user(db)
    project = projects.create(db, user_id=user.id, name="Trang bán hàng")
    assert project.slug == "trang-ban-hang"
    assert projects.slugify("Đội ngũ nội bộ") == "doi-ngu-noi-bo"
    # A name with nothing left after folding still gets a usable slug.
    assert projects.slugify("!!!") == "default"


def test_the_default_project_is_created_on_first_use_not_at_signup(db):
    user = _user(db)
    assert projects.list_for(db, user_id=user.id) == []
    default = projects.default_for(db, user_id=user.id)
    db.commit()
    assert default.slug == "default"
    assert projects.default_for(db, user_id=user.id).id == default.id


def test_a_key_carries_its_project_all_the_way_to_the_api(api, db):
    user = _user(db)
    project = projects.create(db, user_id=user.id, name="Batch")
    _key_row, token = _key(db, user, project=project)

    body = api.get(f"{API_V1_PREFIX}/me", headers=_auth(token)).json()
    assert body["project_id"] == project.id
    assert body["account_id"] == user.id


def test_a_project_cannot_be_fetched_by_a_different_account(db):
    alice, bob = _user(db), _user(db)
    project = projects.create(db, user_id=alice.id, name="Private")
    db.commit()
    assert projects.get_owned(db, user_id=bob.id, project_id=project.id) is None
    assert projects.get_owned(db, user_id=alice.id,
                              project_id=project.id).id == project.id


def test_projects_are_capped_per_account(db, monkeypatch):
    monkeypatch.setattr(projects, "MAX_PROJECTS_PER_USER", 2)
    user = _user(db)
    projects.create(db, user_id=user.id, name="One")
    projects.create(db, user_id=user.id, name="Two")
    with pytest.raises(projects.ProjectError):
        projects.create(db, user_id=user.id, name="Three")


# ── Archiving ────────────────────────────────────────────────────────────────

def test_archiving_a_project_revokes_its_keys_and_leaves_the_others_alone(api, db):
    user = _user(db)
    retiring = projects.create(db, user_id=user.id, name="Old")
    keeping = projects.create(db, user_id=user.id, name="New")
    _old_row, old_token = _key(db, user, project=retiring)
    _new_row, new_token = _key(db, user, project=keeping)

    assert api.get(f"{API_V1_PREFIX}/me", headers=_auth(old_token)).status_code == 200

    revoked = projects.archive(db, retiring)
    db.commit()
    assert revoked == 1
    assert retiring.status == PROJECT_ARCHIVED

    # The retired integration stops immediately…
    assert api.get(f"{API_V1_PREFIX}/me",
                   headers=_auth(old_token)).status_code == 401
    # …and the other one never noticed.
    assert api.get(f"{API_V1_PREFIX}/me",
                   headers=_auth(new_token)).status_code == 200


def test_archiving_destroys_no_evidence_about_money(api, db):
    """The invariant that makes archiving safe to offer at all."""
    import sqlalchemy as sa
    from platform_core.models import CreditEntry, Job

    user = _user(db)
    project = projects.create(db, user_id=user.id, name="Spender")
    _row, token = _key(db, user, project=project)

    quote = api.post(f"{API_V1_PREFIX}/quotes",
                     json={"tool": TOOL, "input": {"prompt": "hi"}},
                     headers=_auth(token)).json()
    created = api.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quote["quote"], "input": {"prompt": "hi"}},
        headers={**_auth(token), "Idempotency-Key": "projects-spend-1"})
    assert created.status_code == 201

    def _counts():
        return (int(db.execute(sa.select(sa.func.count(Job.id))).scalar_one()),
                int(db.execute(sa.select(sa.func.count(CreditEntry.id)))
                    .scalar_one()))

    before = _counts()
    projects.archive(db, project)
    db.commit()
    assert _counts() == before
    assert before[0] == 1 and before[1] >= 1


def test_unarchiving_brings_the_project_back_but_not_the_keys(db):
    user = _user(db)
    project = projects.create(db, user_id=user.id, name="Seasonal")
    key_row, _token = _key(db, user, project=project)
    projects.archive(db, project)
    db.commit()

    projects.unarchive(db, project)
    db.commit()
    assert project.status == PROJECT_ACTIVE
    # Revocation is one-way: a credential that was announced as dead stays dead.
    assert key_row.revoked_at is not None


def test_the_default_project_comes_back_if_it_was_archived(db):
    user = _user(db)
    default = projects.default_for(db, user_id=user.id)
    projects.archive(db, default)
    db.commit()
    # Otherwise the account could no longer create a key at all.
    assert projects.default_for(db, user_id=user.id).status == PROJECT_ACTIVE


# ── Key restrictions ─────────────────────────────────────────────────────────

def test_an_ip_allowlist_is_stored_as_canonical_cidr(db):
    user = _user(db)
    key, _token = _key(db, user, allowed_ips=["203.0.113.4", "198.51.100.0/24",
                                              " 203.0.113.4 "])
    assert key.allowed_ips == ["203.0.113.4/32", "198.51.100.0/24"]


def test_a_nonsense_ip_is_refused_at_issue_time(db):
    user = _user(db)
    with pytest.raises(devkeys.DeveloperKeyError):
        devkeys.issue(db, user_id=user.id, allowed_ips=["not-an-address"],
                      env={devkeys.PEPPER_ENV: PEPPER})


@pytest.mark.parametrize("caller,allowed", [
    ("203.0.113.4", True),
    ("203.0.113.5", False),
    ("198.51.100.77", True),
    ("", False),
    ("garbage", False),
])
def test_the_allowlist_decides_by_range_and_fails_closed(db, caller, allowed):
    user = _user(db)
    key, _token = _key(db, user, allowed_ips=["203.0.113.4",
                                              "198.51.100.0/24"])
    assert devkeys.ip_allowed(key, caller) is allowed


def test_an_empty_allowlist_means_anywhere(db):
    user = _user(db)
    key, _token = _key(db, user)
    assert devkeys.ip_allowed(key, "203.0.113.4") is True
    assert devkeys.ip_allowed(key, "") is True


def test_a_key_restricted_to_another_address_is_refused_by_the_api(api, db):
    user = _user(db)
    _row, token = _key(db, user, allowed_ips=["198.51.100.0/24"])
    # TestClient presents as testclient/127.0.0.1, which is outside the range.
    denied = api.get(f"{API_V1_PREFIX}/me", headers=_auth(token))
    assert denied.status_code == 401
    # Same body as every other credential failure: telling the caller "right
    # key, wrong address" confirms the key is real to whoever stole it.
    assert denied.json()["code"] == "unauthorized"


def test_a_key_restricted_to_the_calling_address_still_works(api, db):
    user = _user(db)
    _row, token = _key(db, user, allowed_ips=["127.0.0.1/32"])
    # A real peer address, because the default TestClient peer is the literal
    # string "testclient" — which is exactly the "address cannot be determined"
    # case the allowlist is supposed to refuse.
    with TestClient(api.app, client=("127.0.0.1", 40001)) as caller:
        assert caller.get(f"{API_V1_PREFIX}/me",
                          headers=_auth(token)).status_code == 200


def test_expiry_is_enforced_and_bounded(db):
    user = _user(db)
    soon = datetime.now(timezone.utc) + timedelta(days=1)
    key, _token = _key(db, user, expires_at=soon)
    assert key.is_usable() is True
    assert key.is_usable(now=soon + timedelta(seconds=1)) is False

    with pytest.raises(devkeys.DeveloperKeyError):
        devkeys.issue(db, user_id=user.id,
                      expires_at=datetime.now(timezone.utc) - timedelta(days=1),
                      env={devkeys.PEPPER_ENV: PEPPER})
    with pytest.raises(devkeys.DeveloperKeyError):
        devkeys.issue(db, user_id=user.id,
                      expires_at=datetime.now(timezone.utc) + timedelta(days=400),
                      env={devkeys.PEPPER_ENV: PEPPER})


# ── Trusted proxy ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("peer,trusted", [
    ("127.0.0.1", True),
    ("::1", True),
    ("173.245.48.9", True),          # inside the configured CIDR
    ("173.245.49.9", False),         # just outside it
    ("203.0.113.7", False),
    ("garbage", False),
])
def test_trusted_proxies_accept_ranges_as_well_as_addresses(peer, trusted):
    configured = ("127.0.0.1", "::1", "173.245.48.0/24")
    assert is_trusted_peer(peer, configured) is trusted


def test_an_unparseable_trust_entry_widens_nothing():
    """A typo in a config file must not turn into "believe everyone"."""
    assert is_trusted_peer("203.0.113.7", ("not-a-cidr",)) is False
    assert is_trusted_peer("203.0.113.7", ("0.0.0.0/33",)) is False


def test_a_forwarded_address_is_only_believed_from_a_trusted_peer(api, db):
    """The header decides the allowlist outcome only when the peer is trusted."""
    user = _user(db)
    _row, token = _key(db, user, allowed_ips=["198.51.100.7/32"])
    forwarded = {**_auth(token), "CF-Connecting-IP": "198.51.100.7"}

    # From loopback — a trusted proxy by default — the header is believed, and
    # the key is allowed through on the strength of it.
    with TestClient(api.app, client=("127.0.0.1", 40002)) as trusted:
        assert trusted.get(f"{API_V1_PREFIX}/me",
                           headers=forwarded).status_code == 200
        other = {**_auth(token), "CF-Connecting-IP": "198.51.100.8"}
        assert trusted.get(f"{API_V1_PREFIX}/me",
                           headers=other).status_code == 401

    # From anywhere else the same header is ignored, so the caller is judged by
    # its real address and refused. Otherwise an IP allowlist would be bypassable
    # by anyone who can reach the process directly.
    with TestClient(api.app, client=("203.0.113.9", 40003)) as untrusted:
        assert untrusted.get(f"{API_V1_PREFIX}/me",
                             headers=forwarded).status_code == 401


# ── Migration safety ─────────────────────────────────────────────────────────

def test_a_key_without_a_project_keeps_working(api, db):
    """The V2 data shape, still valid: project_id is nullable for a reason."""
    user = _user(db)
    key, token = _key(db, user)
    assert key.project_id is None
    response = api.get(f"{API_V1_PREFIX}/me", headers=_auth(token))
    assert response.status_code == 200
    assert response.json()["project_id"] == ""


def test_the_migration_backfills_a_default_project_for_existing_keys(db):
    """What the migration does, expressed against the same tables it touches."""
    import sqlalchemy as sa

    user = _user(db)
    key, _token = _key(db, user)
    assert key.project_id is None

    # This is the backfill, in the same order the migration performs it.
    project = projects.default_for(db, user_id=user.id)
    db.execute(sa.text(
        "UPDATE developer_api_keys SET project_id = :pid "
        "WHERE user_id = :uid AND project_id IS NULL"),
        {"pid": project.id, "uid": user.id})
    db.commit()
    db.refresh(key)

    assert key.project_id == project.id
    assert db.execute(sa.select(sa.func.count(ApiProject.id)).where(
        ApiProject.user_id == user.id)).scalar_one() == 1
