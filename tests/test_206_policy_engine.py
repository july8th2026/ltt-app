"""EXT-14 — the policy engine: how much, and the switch that says not now.

Three acceptance criteria drive this file, and each one is a property rather
than a feature:

* **deterministic precedence** — the same inputs resolve to the same numbers,
  whatever order rows were created in. A limit that depends on insertion order
  is a limit nobody can support;
* **abuse isolation** — one account cannot buy more rate by creating more keys,
  and one account being throttled does not throttle another;
* **UI apps unaffected** — every switch here is scoped to `/api/v1`. Turning the
  API off must not take the web app down with it.

And one more the brief states plainly: a **historical quote is unaffected**.
Changing a limit must not reprice work a customer was already promised.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import (capacity, keys as devkeys, limits,
                                      policy)
from platform_core.public_api.config import load_public_api_config
from platform_core.public_api.tables import (KILL_GLOBAL_WRITES, KILL_KEY,
                                             KILL_MAINTENANCE, KILL_PROJECT,
                                             KILL_TOOL, KILL_USER,
                                             POLICY_SCOPE_KEY,
                                             POLICY_SCOPE_PROJECT,
                                             POLICY_SCOPE_USER)
from server.api.inventory import API_V1_PREFIX

PEPPER = "policy-test-pepper-" + "p" * 40
TOOL = "image.thumbnail"
SCOPES = ("tools:read", "jobs:create", "jobs:read", "artifacts:read",
          "uploads:write")
INPUT = {"topic": "policy", "count": 1}
#: The published tool that actually takes an upload — the thumbnail tool has no
#: media input, so the upload ceiling has to be exercised somewhere real.
UPLOAD_TOOL = "image.upscale"


@pytest.fixture()
def portal(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'policy.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    monkeypatch.setenv("GEMINI_API_KEY", "stub-key-not-used")
    limits.reset()
    capacity.reset()

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
        "LTT_SESSION_SECRET": "policy-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1",
        "LTT_PUBLIC_API_TOOLS": f"{TOOL},{UPLOAD_TOOL}",
        "LTT_PUBLIC_API_RPM": "600", "LTT_PUBLIC_API_CREATE_RPM": "200",
    })
    with TestClient(app, base_url="https://testserver") as client:
        yield client
    from server.api import deps
    deps.set_principal_resolver(None)
    storage_mod.set_storage(None)
    limits.reset()
    capacity.reset()
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
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def _sign_in(client, credits: int = 500) -> str:
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    email = f"pol-{uuid.uuid4().hex[:6]}@example.com"
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
    return user_id


def _issue(client, name: str = "key") -> str:
    page = client.get("/developers/keys").text
    created = client.post("/developers/keys",
                          data={"name": name, "csrf_token": _csrf(page),
                                "scopes": list(SCOPES)})
    return re.search(r"<code>(ltt_sk_[^<]+)</code>", created.text).group(1)


def _auth(token: str, idem: str = "") -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if idem:
        headers["Idempotency-Key"] = idem
    return headers


def _config(**over):
    env = {"LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": TOOL}
    env.update(over)
    return load_public_api_config(env)


class _Principal:
    def __init__(self, user_id="u1", project_id="p1", key_id="k1"):
        self.user_id = user_id
        self.project_id = project_id
        self.key_id = key_id


# ── Precedence: deterministic, and only what a step actually sets ────────────

def test_with_no_policies_the_numbers_are_the_deployment_s_own(portal):
    gen, db = _session()
    try:
        resolved = policy.resolve(db, config=_config(
            LTT_PUBLIC_API_RPM="120", LTT_PUBLIC_API_CREATE_RPM="20"))
        assert resolved.rpm_read == 120
        # Reads and writes start from the one number that was already in force;
        # splitting them must not change an untouched deployment.
        assert resolved.rpm_write == 120
        assert resolved.rpm_create == 20
        assert set(resolved.sources.values()) == {"global"}
    finally:
        _close(gen)


def test_each_step_overrides_only_what_it_sets(portal):
    """The rule the whole engine rests on.

    A policy attached to raise one limit must not silently reset the four it
    says nothing about — the person attaching it would have no way to know.
    """
    gen, db = _session()
    try:
        tier = policy.create_policy(db, name="tier", rpm_read=100,
                                    rpm_create=10, max_active_jobs=5,
                                    is_default=True)
        narrow = policy.create_policy(db, name="narrow", rpm_create=3)
        policy.assign(db, policy=narrow, scope=POLICY_SCOPE_USER,
                      subject_id="u1")
        db.commit()

        resolved = policy.resolve(db, config=_config(), principal=_Principal())
        assert resolved.rpm_create == 3, "the narrow step should win"
        assert resolved.rpm_read == 100, "the tier's other fields survive"
        assert resolved.max_active_jobs == 5
        assert resolved.sources["rpm_create"] == "user:narrow"
        assert resolved.sources["rpm_read"] == "tier:tier"
        assert tier.is_default is True
    finally:
        _close(gen)


def test_the_chain_runs_widest_to_narrowest(portal):
    gen, db = _session()
    try:
        for name, scope, subject, value in (
            ("t", None, None, 10), ("u", POLICY_SCOPE_USER, "u1", 20),
            ("p", POLICY_SCOPE_PROJECT, "p1", 30),
            ("k", POLICY_SCOPE_KEY, "k1", 40),
        ):
            made = policy.create_policy(db, name=name, rpm_create=value,
                                        is_default=scope is None)
            if scope:
                policy.assign(db, policy=made, scope=scope, subject_id=subject)
        db.commit()

        resolved = policy.resolve(db, config=_config(), principal=_Principal())
        assert resolved.rpm_create == 40, "the credential is narrowest"
        assert resolved.sources["rpm_create"] == "key:k"

        # …and removing the narrowest step falls back exactly one level.
        policy.unassign(db, scope=POLICY_SCOPE_KEY, subject_id="k1")
        db.commit()
        assert policy.resolve(db, config=_config(),
                              principal=_Principal()).rpm_create == 30
    finally:
        _close(gen)


def test_a_tool_override_is_the_last_word(portal):
    gen, db = _session()
    try:
        made = policy.create_policy(
            db, name="per-tool", rpm_create=50,
            tool_overrides={TOOL: {"rpm_create": 2}})
        policy.assign(db, policy=made, scope=POLICY_SCOPE_USER,
                      subject_id="u1")
        db.commit()

        without = policy.resolve(db, config=_config(), principal=_Principal())
        withtool = policy.resolve(db, config=_config(), principal=_Principal(),
                                  tool_name=TOOL)
        assert without.rpm_create == 50
        assert withtool.rpm_create == 2
        assert withtool.sources["rpm_create"] == f"tool:{TOOL}"
    finally:
        _close(gen)


def test_a_tool_override_from_a_losing_policy_does_not_apply(portal):
    """Overrides come from the policy that won, not from every policy seen.

    A tool rule inside a policy that was overridden wholesale is a rule its
    author no longer intends to apply.
    """
    gen, db = _session()
    try:
        tier = policy.create_policy(
            db, name="tier", rpm_create=50, is_default=True,
            tool_overrides={TOOL: {"rpm_create": 1}})
        winner = policy.create_policy(db, name="winner", rpm_create=9)
        policy.assign(db, policy=winner, scope=POLICY_SCOPE_USER,
                      subject_id="u1")
        db.commit()

        resolved = policy.resolve(db, config=_config(), principal=_Principal(),
                                  tool_name=TOOL)
        assert resolved.rpm_create == 9, "the losing tier's tool rule applied"
        assert tier.tool_overrides[TOOL]["rpm_create"] == 1
    finally:
        _close(gen)


def test_resolution_does_not_depend_on_insertion_order(portal):
    """Deterministic, stated as the thing that could go wrong.

    Rows created in the reverse order must resolve to the same numbers; if they
    did not, the engine would be answering from row order.
    """
    gen, db = _session()
    try:
        narrow = policy.create_policy(db, name="narrow", rpm_create=3)
        policy.assign(db, policy=narrow, scope=POLICY_SCOPE_KEY,
                      subject_id="k1")
        policy.create_policy(db, name="tier", rpm_create=100, rpm_read=90,
                             is_default=True)
        db.commit()
        first = policy.resolve(db, config=_config(),
                               principal=_Principal()).as_dict()
    finally:
        _close(gen)

    gen, db = _session()
    try:
        for row in policy.list_policies(db):
            policy.delete_policy(db, row)
        policy.create_policy(db, name="tier", rpm_create=100, rpm_read=90,
                             is_default=True)
        narrow = policy.create_policy(db, name="narrow", rpm_create=3)
        policy.assign(db, policy=narrow, scope=POLICY_SCOPE_KEY,
                      subject_id="k1")
        db.commit()
        second = policy.resolve(db, config=_config(),
                                principal=_Principal()).as_dict()
    finally:
        _close(gen)

    assert first == second


def test_only_one_policy_can_be_the_default(portal):
    gen, db = _session()
    try:
        first = policy.create_policy(db, name="one", is_default=True)
        second = policy.create_policy(db, name="two", is_default=True)
        db.commit()
        db.refresh(first)
        assert second.is_default is True
        assert first.is_default is False, "two defaults make the tier ambiguous"
    finally:
        _close(gen)


def test_one_subject_holds_one_policy(portal):
    """Reassignment, not a second row: two policies on one subject would make
    the answer depend on which row came back first."""
    gen, db = _session()
    try:
        first = policy.create_policy(db, name="a", rpm_create=5)
        second = policy.create_policy(db, name="b", rpm_create=6)
        policy.assign(db, policy=first, scope=POLICY_SCOPE_USER, subject_id="u1")
        policy.assign(db, policy=second, scope=POLICY_SCOPE_USER, subject_id="u1")
        db.commit()

        assert len(policy.assignments_for(db, first.id)) == 0
        assert len(policy.assignments_for(db, second.id)) == 1
        assert policy.resolve(db, config=_config(),
                              principal=_Principal()).rpm_create == 6
    finally:
        _close(gen)


def test_deleting_a_policy_falls_back_rather_than_orphaning(portal):
    gen, db = _session()
    try:
        policy.create_policy(db, name="tier", rpm_create=30, is_default=True)
        narrow = policy.create_policy(db, name="narrow", rpm_create=4)
        policy.assign(db, policy=narrow, scope=POLICY_SCOPE_USER,
                      subject_id="u1")
        db.commit()
        assert policy.resolve(db, config=_config(),
                              principal=_Principal()).rpm_create == 4

        policy.delete_policy(db, narrow)
        db.commit()
        assert policy.resolve(db, config=_config(),
                              principal=_Principal()).rpm_create == 30
    finally:
        _close(gen)


def test_zero_is_a_real_limit_and_not_an_unset_marker(portal):
    """The reason every column is nullable.

    A rate of zero refuses everything, and it has to be expressible — a scheme
    that spent zero on "unset" could never say it.
    """
    gen, db = _session()
    try:
        made = policy.create_policy(db, name="frozen", rpm_create=0)
        policy.assign(db, policy=made, scope=POLICY_SCOPE_USER, subject_id="u1")
        db.commit()
        resolved = policy.resolve(db, config=_config(), principal=_Principal())
        assert resolved.rpm_create == 0
        assert resolved.sources["rpm_create"] == "user:frozen"
    finally:
        _close(gen)


def test_a_policy_refuses_nonsense(portal):
    gen, db = _session()
    try:
        policy.create_policy(db, name="taken")
        db.commit()
        for kwargs in ({"name": ""}, {"name": "taken"},
                       {"name": "x", "rpm_read": -1},
                       {"name": "y", "rpm_read": "abc"},
                       {"name": "z", "nonsense_field": 1}):
            with pytest.raises(policy.PolicyError):
                policy.create_policy(db, **kwargs)
            db.rollback()
    finally:
        _close(gen)


# ── Abuse isolation ──────────────────────────────────────────────────────────

def test_more_keys_do_not_buy_more_rate(portal):
    """The hole this prompt exists to close.

    Before EXT-14 the rate was bucketed on the key alone, so an account that
    wanted five times the rate created five keys — no exploit needed, just the
    credential page.
    """
    user_id = _sign_in(portal)
    first, second = _issue(portal, "one"), _issue(portal, "two")

    gen, db = _session()
    try:
        made = policy.create_policy(db, name="tight", rpm_read=3)
        policy.assign(db, policy=made, scope=POLICY_SCOPE_USER,
                      subject_id=user_id)
        db.commit()
    finally:
        _close(gen)
    limits.reset()

    seen = []
    for index in range(8):
        token = first if index % 2 == 0 else second
        seen.append(portal.get(f"{API_V1_PREFIX}/tools",
                               headers=_auth(token)).status_code)
    assert 429 in seen, "two keys shared one account allowance and never tripped"
    assert seen.count(200) <= 3, seen


def test_one_account_being_throttled_does_not_throttle_another(portal):
    noisy = _sign_in(portal)
    noisy_token = _issue(portal, "noisy")
    gen, db = _session()
    try:
        made = policy.create_policy(db, name="tight", rpm_read=2)
        policy.assign(db, policy=made, scope=POLICY_SCOPE_USER,
                      subject_id=noisy)
        db.commit()
    finally:
        _close(gen)
    limits.reset()

    for _ in range(5):
        portal.get(f"{API_V1_PREFIX}/tools", headers=_auth(noisy_token))
    assert portal.get(f"{API_V1_PREFIX}/tools",
                      headers=_auth(noisy_token)).status_code == 429

    _sign_in(portal)
    quiet_token = _issue(portal, "quiet")
    assert portal.get(f"{API_V1_PREFIX}/tools",
                      headers=_auth(quiet_token)).status_code == 200


def test_reads_and_writes_have_separate_allowances(portal):
    user_id = _sign_in(portal)
    token = _issue(portal)
    gen, db = _session()
    try:
        made = policy.create_policy(db, name="split", rpm_read=2, rpm_write=50)
        policy.assign(db, policy=made, scope=POLICY_SCOPE_USER,
                      subject_id=user_id)
        db.commit()
    finally:
        _close(gen)
    limits.reset()

    for _ in range(4):
        portal.get(f"{API_V1_PREFIX}/tools", headers=_auth(token))
    assert portal.get(f"{API_V1_PREFIX}/tools",
                      headers=_auth(token)).status_code == 429

    # A write still goes through: exhausting the read allowance must not
    # consume the one that protects the expensive calls.
    quote = portal.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": TOOL, "input": INPUT},
                        headers=_auth(token))
    assert quote.status_code == 200, quote.text


# ── Kill switches ────────────────────────────────────────────────────────────

def _engage(**kwargs):
    gen, db = _session()
    try:
        row = policy.engage(db, **kwargs)
        db.commit()
        return row.id
    finally:
        _close(gen)


def test_maintenance_stops_reads_and_writes_alike(portal):
    _sign_in(portal)
    token = _issue(portal)
    assert portal.get(f"{API_V1_PREFIX}/tools",
                      headers=_auth(token)).status_code == 200

    _engage(scope=KILL_MAINTENANCE, reason="migrating the database",
            created_by="operator@example.com")
    answer = portal.get(f"{API_V1_PREFIX}/tools", headers=_auth(token))
    assert answer.status_code == 503
    body = answer.json()
    assert body["code"] == "service_unavailable"
    # The reason an operator typed is written for a customer; withholding it
    # only moves the same conversation into a support ticket.
    assert "migrating the database" in body["detail"]


def test_the_global_write_switch_leaves_reads_alone(portal):
    _sign_in(portal)
    token = _issue(portal)
    _engage(scope=KILL_GLOBAL_WRITES, reason="provider incident 91",
            created_by="operator@example.com")

    assert portal.get(f"{API_V1_PREFIX}/tools",
                      headers=_auth(token)).status_code == 200
    refused = portal.post(f"{API_V1_PREFIX}/quotes",
                          json={"tool": TOOL, "input": INPUT},
                          headers=_auth(token))
    assert refused.status_code == 503
    assert refused.json()["code"] == "read_only"
    assert "incident 91" in refused.json()["detail"]


def test_a_suspended_account_is_told_so_and_not_told_to_retry(portal):
    user_id = _sign_in(portal)
    token = _issue(portal)
    _engage(scope=KILL_USER, subject=user_id, reason="chargeback under review",
            created_by="operator@example.com")

    answer = portal.get(f"{API_V1_PREFIX}/tools", headers=_auth(token))
    assert answer.status_code == 403, answer.text
    assert answer.json()["code"] == "forbidden"
    assert "chargeback under review" in answer.json()["detail"]


def test_switching_off_one_account_leaves_the_others_working(portal):
    blocked = _sign_in(portal)
    blocked_token = _issue(portal)
    _engage(scope=KILL_USER, subject=blocked, reason="abuse investigation",
            created_by="operator@example.com")
    assert portal.get(f"{API_V1_PREFIX}/tools",
                      headers=_auth(blocked_token)).status_code == 403

    _sign_in(portal)
    other = _issue(portal, "other")
    assert portal.get(f"{API_V1_PREFIX}/tools",
                      headers=_auth(other)).status_code == 200


def test_a_switched_off_tool_refuses_at_creation_not_at_the_provider(portal):
    _sign_in(portal)
    token = _issue(portal)
    quote = portal.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": TOOL, "input": INPUT},
                        headers=_auth(token))
    assert quote.status_code == 200

    _engage(scope=KILL_TOOL, subject=TOOL, reason="upstream model degraded",
            created_by="operator@example.com")
    refused = portal.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quote.json()["quote"], "input": INPUT},
        headers=_auth(token, f"pol-{uuid.uuid4().hex[:8]}"))
    assert refused.status_code == 503, refused.text
    assert refused.json()["code"] == "service_unavailable"
    assert "upstream model degraded" in refused.json()["detail"]


def test_a_switched_off_tool_holds_no_credit(portal):
    """Refusing costs the caller nothing; holding for work that cannot run
    costs a refund to reconcile and a conversation to have."""
    from platform_core import credit

    user_id = _sign_in(portal)
    token = _issue(portal)
    quote = portal.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": TOOL, "input": INPUT},
                        headers=_auth(token)).json()

    gen, db = _session()
    try:
        before = credit.so_du(db, user_id)
    finally:
        _close(gen)

    _engage(scope=KILL_TOOL, subject=TOOL, reason="upstream model degraded",
            created_by="operator@example.com")
    portal.post(f"{API_V1_PREFIX}/jobs",
                json={"tool": TOOL, "quote": quote["quote"], "input": INPUT},
                headers=_auth(token, f"pol-{uuid.uuid4().hex[:8]}"))

    gen, db = _session()
    try:
        assert credit.so_du(db, user_id) == before
    finally:
        _close(gen)


def test_an_expired_switch_simply_stops_applying(portal):
    """No sweeper. The commonest failure of an incident tool is that nobody
    remembers to turn it off."""
    _sign_in(portal)
    token = _issue(portal)

    gen, db = _session()
    try:
        row = policy.engage(db, scope=KILL_MAINTENANCE,
                            reason="ten minute window",
                            created_by="operator@example.com",
                            expires_at=datetime.now(timezone.utc)
                            + timedelta(minutes=10))
        db.commit()
        switch_id = row.id
    finally:
        _close(gen)
    assert portal.get(f"{API_V1_PREFIX}/tools",
                      headers=_auth(token)).status_code == 503

    gen, db = _session()
    try:
        db.get(type(row), switch_id).expires_at = (
            datetime.now(timezone.utc) - timedelta(seconds=1))
        db.commit()
    finally:
        _close(gen)
    assert portal.get(f"{API_V1_PREFIX}/tools",
                      headers=_auth(token)).status_code == 200


def test_the_broadest_switch_is_the_one_reported(portal):
    """When several apply, name the one whose lifting actually unblocks them."""
    user_id = _sign_in(portal)
    token = _issue(portal)
    _engage(scope=KILL_USER, subject=user_id, reason="account under review",
            created_by="op@example.com")
    _engage(scope=KILL_MAINTENANCE, reason="platform maintenance",
            created_by="op@example.com")

    body = portal.get(f"{API_V1_PREFIX}/tools", headers=_auth(token)).json()
    assert "platform maintenance" in body["detail"]


def test_a_switch_without_a_reason_is_refused(portal):
    gen, db = _session()
    try:
        for reason in ("", "  ", "short"):
            with pytest.raises(policy.PolicyError):
                policy.engage(db, scope=KILL_MAINTENANCE, reason=reason)
            db.rollback()
        with pytest.raises(policy.PolicyError):
            policy.engage(db, scope=KILL_TOOL, subject="",
                          reason="a good enough reason")
        db.rollback()
        with pytest.raises(policy.PolicyError):
            policy.engage(db, scope="nonsense", reason="a good enough reason")
        db.rollback()
        with pytest.raises(policy.PolicyError):
            policy.engage(db, scope=KILL_MAINTENANCE,
                          reason="a good enough reason",
                          expires_at=datetime.now(timezone.utc)
                          - timedelta(minutes=1))
    finally:
        _close(gen)


def test_releasing_a_switch_restores_service(portal):
    _sign_in(portal)
    token = _issue(portal)
    switch_id = _engage(scope=KILL_MAINTENANCE, reason="short outage",
                        created_by="op@example.com")
    assert portal.get(f"{API_V1_PREFIX}/tools",
                      headers=_auth(token)).status_code == 503

    gen, db = _session()
    try:
        policy.release(db, policy.switch_by_id(db, switch_id))
        db.commit()
    finally:
        _close(gen)
    assert portal.get(f"{API_V1_PREFIX}/tools",
                      headers=_auth(token)).status_code == 200


def test_one_credential_can_be_switched_off_without_the_account(portal):
    """The narrowest scope: a leaked key stops, the customer keeps working."""
    user_id = _sign_in(portal)
    blocked = _issue(portal, "leaked")
    working = _issue(portal, "healthy")

    _engage(scope=KILL_KEY, subject=blocked.split("_")[2],
            reason="credential rotated out", created_by="op@example.com")

    assert portal.get(f"{API_V1_PREFIX}/tools",
                      headers=_auth(blocked)).status_code == 403
    assert portal.get(f"{API_V1_PREFIX}/tools",
                      headers=_auth(working)).status_code == 200
    assert user_id


def test_a_project_can_be_switched_off_on_its_own(portal):
    user_id = _sign_in(portal)
    token = _issue(portal)

    gen, db = _session()
    try:
        key = devkeys.get_owned(db, user_id=user_id,
                                key_id=token.split("_")[2])
        project_id = str(key.project_id or "")
        assert project_id, "this test assumes keys carry a project (EXT-04)"
    finally:
        _close(gen)

    _engage(scope=KILL_PROJECT, subject=project_id,
            reason="integration paused by agreement", created_by="op@example.com")
    answer = portal.get(f"{API_V1_PREFIX}/tools", headers=_auth(token))
    assert answer.status_code == 403
    assert "integration paused by agreement" in answer.json()["detail"]


# ── The two properties the brief calls out ───────────────────────────────────

def test_the_web_app_keeps_working_while_the_api_is_switched_off(portal):
    """Every switch here is scoped to `/api/v1`.

    Turning the API off during an incident must not take the product down with
    it — and a customer mid-task in the web app is not the caller being
    rate-limited.
    """
    user_id = _sign_in(portal)
    token = _issue(portal)
    _engage(scope=KILL_MAINTENANCE, reason="api maintenance window",
            created_by="op@example.com")
    assert portal.get(f"{API_V1_PREFIX}/tools",
                      headers=_auth(token)).status_code == 503

    # The portal still answers…
    assert portal.get("/developers/keys").status_code == 200
    # …and a job submitted the way the web app submits one still runs.
    from platform_core import jobs as jobq

    gen, db = _session()
    try:
        job = jobq.submit(db, user_id=user_id, app_slug="thumbnail",
                          job_type="thumbnail.tao_anh",
                          params={"topic": "ui", "count": 1,
                                  "owner_id": user_id})
        db.commit()
        assert job.status == "queued"
    finally:
        _close(gen)


def test_a_policy_change_does_not_reprice_an_issued_quote(portal):
    """A limit is not a price. Refusing is allowed; repricing is not."""
    user_id = _sign_in(portal)
    token = _issue(portal)
    quote = portal.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": TOOL, "input": INPUT},
                        headers=_auth(token)).json()

    gen, db = _session()
    try:
        made = policy.create_policy(db, name="after", rpm_create=99,
                                    daily_credit=100000)
        policy.assign(db, policy=made, scope=POLICY_SCOPE_USER,
                      subject_id=user_id)
        db.commit()
    finally:
        _close(gen)
    limits.reset()

    created = portal.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quote["quote"], "input": INPUT},
        headers=_auth(token, f"pol-{uuid.uuid4().hex[:8]}"))
    assert created.status_code == 201, created.text
    assert created.json()["credit"]["held"] == quote["credit"]


# ── Capacity ─────────────────────────────────────────────────────────────────

def test_capacity_is_silent_when_the_pool_is_not_the_source(portal):
    """An empty credential pool says nothing.

    Every app here falls back to an environment credential, so refusing on an
    empty pool would ground a deployment that never opted into the pool — which
    is exactly what an earlier version of this guard did.
    """
    from platform_core.public_api.catalog import build_catalog

    gen, db = _session()
    try:
        tool = next(item for item in build_catalog(_config())
                    if item.name == TOOL)
        assert capacity.check(db, tool=tool) is None
    finally:
        _close(gen)


def test_capacity_refuses_when_storage_will_not_take_a_write(portal, monkeypatch):
    from platform_core.public_api.catalog import build_catalog

    capacity.reset()
    monkeypatch.setattr(capacity, "_storage_writable", lambda: False)
    gen, db = _session()
    try:
        tool = next(item for item in build_catalog(_config())
                    if item.name == TOOL)
        missing = capacity.check(db, tool=tool)
        assert missing is not None and missing.resource == "storage"
    finally:
        _close(gen)
    capacity.reset()


def test_a_job_is_refused_before_the_hold_when_capacity_is_gone(portal,
                                                               monkeypatch):
    from platform_core import credit

    user_id = _sign_in(portal)
    token = _issue(portal)
    quote = portal.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": TOOL, "input": INPUT},
                        headers=_auth(token)).json()

    gen, db = _session()
    try:
        before = credit.so_du(db, user_id)
    finally:
        _close(gen)

    capacity.reset()
    monkeypatch.setattr(capacity, "_storage_writable", lambda: False)
    refused = portal.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quote["quote"], "input": INPUT},
        headers=_auth(token, f"pol-{uuid.uuid4().hex[:8]}"))
    capacity.reset()

    assert refused.status_code == 503, refused.text
    assert refused.json()["resource"] == "storage"
    gen, db = _session()
    try:
        assert credit.so_du(db, user_id) == before
    finally:
        _close(gen)


# ── What is deliberately absent ──────────────────────────────────────────────

def test_no_priority_field_is_offered_because_nothing_schedules_it():
    """The brief allows priority classes "only if the scheduler supports it".

    `jobs.claim()` takes work strictly FIFO by `created_at`. A priority field
    that no scheduler consults would be a promise the platform cannot keep,
    visible in the admin UI and wrong.
    """
    import inspect

    from platform_core import jobs as jobq
    from platform_core.models import Job

    assert not hasattr(Job, "priority")
    assert "priority" not in policy.LIMIT_FIELDS
    source = inspect.getsource(jobq)
    assert "order_by(Job.created_at)" in source


# ── Upload ceiling ───────────────────────────────────────────────────────────

def test_the_upload_baseline_is_an_upload_size_not_the_json_body_cap(portal):
    """Caught by looking at the rendered admin page.

    The baseline was seeded from `max_body_bytes` — the 256 KB control-plane
    JSON cap — so the console read "uploads are capped at 256 KB", wrong by four
    orders of magnitude and about a completely different thing.
    """
    from platform_core.public_api.media import MULTIPART_LIMIT

    gen, db = _session()
    try:
        resolved = policy.resolve(db, config=_config())
        assert resolved.max_upload_bytes == MULTIPART_LIMIT
        assert resolved.max_upload_bytes > 1_000_000
    finally:
        _close(gen)


def test_a_policy_lowers_the_upload_ceiling_and_the_ticket_obeys(portal):
    user_id = _sign_in(portal)
    token = _issue(portal)
    ticket = {"tool": UPLOAD_TOOL, "field": "image_key",
              "filename": "big.png", "content_type": "image/png",
              "size": 400_000}

    gen, db = _session()
    try:
        made = policy.create_policy(db, name="small-uploads",
                                    max_upload_bytes=100_000)
        policy.assign(db, policy=made, scope=POLICY_SCOPE_USER,
                      subject_id=user_id)
        db.commit()
    finally:
        _close(gen)

    refused = portal.post(f"{API_V1_PREFIX}/uploads", json=ticket,
                          headers=_auth(token))
    assert refused.status_code == 400, refused.text

    ticket["size"] = 50_000
    allowed = portal.post(f"{API_V1_PREFIX}/uploads", json=ticket,
                          headers=_auth(token))
    assert allowed.status_code == 201, allowed.text


def test_a_policy_cannot_raise_the_upload_ceiling_past_the_platform_s(portal):
    """A tier that could opt past the media rules would be selling something
    the platform cannot deliver — Cloudflare rejects it at the edge."""
    user_id = _sign_in(portal)
    token = _issue(portal)

    gen, db = _session()
    try:
        made = policy.create_policy(db, name="greedy",
                                    max_upload_bytes=5_000_000_000)
        policy.assign(db, policy=made, scope=POLICY_SCOPE_USER,
                      subject_id=user_id)
        db.commit()
    finally:
        _close(gen)

    # The image rules cap this kind at 16 MB; the policy asked for 5 GB.
    refused = portal.post(
        f"{API_V1_PREFIX}/uploads",
        json={"tool": UPLOAD_TOOL, "field": "image_key", "filename": "huge.png",
              "content_type": "image/png", "size": 200_000_000},
        headers=_auth(token))
    assert refused.status_code == 400, refused.text
