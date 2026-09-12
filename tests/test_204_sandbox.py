"""EXT-12 — test mode: the whole API, with the provider replaced.

What is being defended here is a pair of claims a developer has to be able to
trust without reading our code:

* a test key **cannot** spend. Not "spends little" — the ledger is never
  touched, so a leaked test key costs nothing;
* live and test **never mix**. A test key sees only test work; a live key sees
  only live work, and neither can read, cancel or download the other's.

And one claim that keeps the sandbox honest: the response shape is the tool's
published contract, not a hand-written mock. A sandbox whose shape drifts from
production teaches an integration to parse something that will never arrive.
"""
from __future__ import annotations

import re
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import (keys as devkeys, limits, sandbox,
                                      webhooks)
from server.api.inventory import API_V1_PREFIX

PEPPER = "sandbox-test-pepper-" + "s" * 40
TOOL = "image.thumbnail"
SCOPES = ("tools:read", "jobs:create", "jobs:read", "jobs:cancel",
          "artifacts:read", "webhooks:manage")
INPUT = {"topic": "sandbox", "count": 1}
RECEIVER = "https://receiver.example.com/hook"

#: Every provider call the fixture saw. A test job must add nothing to it.
PROVIDER_CALLS: list = []


def _public_dns(host: str) -> list:
    """Resolve the test receiver without depending on somebody else's DNS."""
    if host.endswith("example.com"):
        return ["93.184.216.34"]
    raise OSError(f"unknown test host: {host}")


@pytest.fixture()
def portal(tmp_path, monkeypatch):
    monkeypatch.setattr(webhooks, "_system_resolver", _public_dns)
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'sandbox.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    monkeypatch.setenv("GEMINI_API_KEY", "stub-key-not-used")
    limits.reset()
    PROVIDER_CALLS.clear()

    import platform_core.db as dbmod
    import platform_core.storage as storage_mod
    dbmod.reset_engine()
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    # Job anh gianh `anh_3090` tu dual-model 5.5, va luat 0 fail-closed: khong co
    # dong `gpu_residency` thi worker chi tra job ve hang doi, khong chay handler.
    # Ly do day du: `tests/conftest.py::mo_cu_tru_3090`.
    from platform_core.llm import residency as _residency

    from tests.conftest import mo_cu_tru_3090
    mo_cu_tru_3090(_residency.ANH)

    import apps.thumbnail.jobs as thumbnail_jobs

    from tests.gia_dieu_phoi_anh import tiem as _tiem_dieu_phoi
    _tiem_dieu_phoi(monkeypatch, thumbnail_jobs,
                    khi_goi=lambda: PROVIDER_CALLS.append(1))

    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "sandbox-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": TOOL,
        "LTT_PUBLIC_API_RPM": "600", "LTT_PUBLIC_API_CREATE_RPM": "200",
    })
    with TestClient(app, base_url="https://testserver") as client:
        yield client
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
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def _sign_in(client, credits: int = 200) -> str:
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    email = f"sb-{uuid.uuid4().hex[:6]}@example.com"
    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=email, password="a-good-password-12")
        user.is_verified = True
        db.flush()
        if credits:
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


def _issue(client, mode: str = "live", scopes=SCOPES) -> str:
    page = client.get("/developers/keys").text
    created = client.post("/developers/keys",
                          data={"name": f"{mode} key", "mode": mode,
                                "csrf_token": _csrf(page),
                                "scopes": list(scopes)})
    found = re.search(r"<code>(ltt_[st]k_[^<]+)</code>", created.text)
    assert found, created.text[:400]
    return found.group(1)


def _auth(token: str, idem: str = "") -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if idem:
        headers["Idempotency-Key"] = idem
    return headers


def _run(client, token, payload=None) -> dict:
    """Quote, submit, run the worker once. Returns the finished job body."""
    body = dict(payload or INPUT)
    quote = client.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": TOOL, "input": body}, headers=_auth(token))
    assert quote.status_code == 200, quote.text
    created = client.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quote.json()["quote"], "input": body},
        headers=_auth(token, f"sb-{uuid.uuid4().hex[:10]}"))
    assert created.status_code == 201, created.text

    from platform_core.job_runner import _chay_mot_job

    assert _chay_mot_job("sandbox-worker") is True
    finished = client.get(f"{API_V1_PREFIX}/jobs/{created.json()['id']}",
                          headers=_auth(token))
    assert finished.status_code == 200, finished.text
    return finished.json()


def _balance(user_id: str) -> int:
    from platform_core import credit

    gen, db = _session()
    try:
        return credit.so_du(db, user_id)
    finally:
        _close(gen)


def _ledger_rows(user_id: str) -> list:
    from sqlalchemy import select

    from platform_core.models import CreditEntry

    gen, db = _session()
    try:
        return db.execute(select(CreditEntry).where(
            CreditEntry.user_id == user_id)).scalars().all()
    finally:
        _close(gen)


# ── A test key announces itself ──────────────────────────────────────────────

def test_a_test_key_is_recognisable_before_it_is_used(portal):
    """The prefix, not a field somewhere, is what a human sees first.

    A secret in a log or a screenshot has to be classifiable at a glance —
    "is this the one that can spend?" must not need a database lookup.
    """
    _sign_in(portal)
    assert _issue(portal, "live").startswith("ltt_sk_")
    assert _issue(portal, "test").startswith("ltt_tk_")


def test_both_prefixes_authenticate_through_the_same_door(portal):
    _sign_in(portal)
    for mode in ("live", "test"):
        token = _issue(portal, mode)
        answer = portal.get(f"{API_V1_PREFIX}/me", headers=_auth(token))
        assert answer.status_code == 200, (mode, answer.text)
        # …and /me says which world, so a deployment can assert it in its own
        # smoke check rather than discovering it from an invoice.
        assert answer.json()["mode"] == mode


def test_rotation_keeps_a_key_in_its_own_world(portal):
    """Rotation replaces secret material, never the environment.

    A key that quietly became live on rotation would point a finished
    integration at real money; the other direction would point production at
    mocks and look like an outage.
    """
    _sign_in(portal)
    token = _issue(portal, "test")
    key_id = token.split("_")[2]

    page = portal.get("/developers/keys").text
    rotated = portal.post(f"/developers/keys/{key_id}/rotate",
                          data={"csrf_token": _csrf(page)})
    found = re.search(r"<code>(ltt_[st]k_[^<]+)</code>", rotated.text)
    assert found and found.group(1).startswith("ltt_tk_"), rotated.text[:300]


# ── A test key cannot spend ──────────────────────────────────────────────────

def test_a_test_call_never_touches_the_ledger(portal):
    user_id = _sign_in(portal, credits=200)
    token = _issue(portal, "test")
    before = _balance(user_id)

    finished = _run(portal, token)

    assert finished["status"] == "succeeded", finished
    assert _balance(user_id) == before, "a test call moved credit"
    assert _ledger_rows(user_id) == [] or all(
        row.job_id != finished["id"] for row in _ledger_rows(user_id)), (
        "a test job wrote a ledger row")
    assert finished["credit"] == {"held": 0, "charged": 0}


def test_the_sandbox_is_open_to_an_account_that_has_not_paid(portal):
    """The developer a sandbox exists for is the one who has not paid yet.

    Requiring a balance for a call that spends nothing would shut the door on
    exactly that person, and it would be measuring something that cannot happen.
    """
    user_id = _sign_in(portal, credits=0)
    assert _balance(user_id) == 0
    token = _issue(portal, "test")

    finished = _run(portal, token)
    assert finished["status"] == "succeeded", finished


def test_a_hard_budget_does_not_refuse_a_call_that_spends_nothing(portal):
    from platform_core.public_api import budgets

    user_id = _sign_in(portal, credits=200)
    gen, db = _session()
    try:
        budgets.create(db, user_id=user_id, amount=budgets.MIN_AMOUNT,
                       hard_cap=True)
        db.commit()
    finally:
        _close(gen)

    live_token = _issue(portal, "live")
    test_token = _issue(portal, "test")
    # ⭐ Số ảnh phải VƯỢT trần — tính từ hàm giá, không gõ cứng. Bản trước
    #    ghi `count: 3` với chú thích "three images cost more than the cap":
    #    đúng khi một ảnh 5 credit, sai ngay khi giá xuống 3.
    from apps.thumbnail.manifest import _cost as _gia_thumbnail
    so = next((n for n in range(1, 5)
               if _gia_thumbnail({"count": n}) > budgets.MIN_AMOUNT), 4)
    assert _gia_thumbnail({"count": so}) > budgets.MIN_AMOUNT, (
        "tran ngan sach toi thieu nay khong con vuot duoc bang mot luot goi")
    over = {"topic": "sandbox", "count": so}

    # The live call is refused by the cap — that is EXT-11 still working…
    quote = portal.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": TOOL, "input": over},
                        headers=_auth(live_token)).json()
    refused = portal.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quote["quote"], "input": over},
        headers=_auth(live_token, f"sb-{uuid.uuid4().hex[:10]}"))
    assert refused.status_code == 429, refused.text
    assert refused.json()["source"] == "budget"

    # …and the same call on a test key goes through, because there is nothing
    # to cap.
    assert _run(portal, test_token, over)["status"] == "succeeded"


# ── A test key never reaches a provider ──────────────────────────────────────

def test_a_test_job_calls_no_provider_and_a_live_one_does(portal):
    _sign_in(portal, credits=200)

    _run(portal, _issue(portal, "test"))
    assert PROVIDER_CALLS == [], "the sandbox called the provider"

    _run(portal, _issue(portal, "live"))
    assert PROVIDER_CALLS, "the live path stopped calling the provider"


# ── Schema parity ────────────────────────────────────────────────────────────

def _published_tool(client, token):
    detail = client.get(f"{API_V1_PREFIX}/tools/{TOOL}", headers=_auth(token))
    assert detail.status_code == 200, detail.text
    return detail.json()


def test_the_sandbox_answers_the_shape_the_contract_promises(portal):
    """Driven by ``output_schema``, so the mock cannot drift from the contract.

    Every artifact field comes back as a downloadable artifact and every data
    field as data — the same partition a live job produces.
    """
    _sign_in(portal, credits=200)
    token = _issue(portal, "test")
    finished = _run(portal, token)
    outputs = _published_tool(portal, token)["output_schema"]["properties"]

    artifact_fields = {name for name, spec in outputs.items()
                       if str(spec.get("type", "")).startswith("artifact")}
    data_fields = set(outputs) - artifact_fields
    assert artifact_fields, "this test assumes the tool returns a file"

    assert {item["field"] for item in finished["outputs"]} == artifact_fields
    assert set(finished.get("result") or {}) == data_fields


def test_the_sandbox_returns_as_many_files_as_the_call_asked_for(portal):
    """Right shape, right *cardinality*.

    Caught by a browser check, not by a test: a live `count=2` call returns two
    images and the sandbox returned one, so an integration reading the second
    entry would have passed here and failed in production. The app declares
    which input multiplies which output (`api_contract["output_counts"]`);
    only the app can know that.
    """
    _sign_in(portal, credits=200)
    token = _issue(portal, "test")

    for count in (1, 2, 4):
        finished = _run(portal, token, {"topic": "sandbox", "count": count})
        images = [item for item in finished["outputs"]
                  if item["field"] == "image_keys"]
        assert len(images) == count, (count, finished["outputs"])
        assert [item["index"] for item in images] == list(range(count))


def test_a_tool_that_declares_no_count_still_answers_one(portal):
    """The declaration is optional, and its absence is not a failure."""
    class _Tool:
        output_schema = {"properties": {"files": {"type": "artifact[]"}}}
        output_counts: dict = {}

    class _Storage:
        def put(self, key, stream, content_type=""):
            return None

    result = sandbox.canned_result(_Tool(), {"count": 4}, _Storage())
    assert len(result["files"]) == 1


def test_a_sandbox_artifact_downloads_through_the_real_path(portal):
    _sign_in(portal, credits=200)
    token = _issue(portal, "test")
    finished = _run(portal, token)

    artifact = finished["outputs"][0]["id"]
    detail = portal.get(f"{API_V1_PREFIX}/artifacts/{artifact}",
                        headers=_auth(token))
    assert detail.status_code == 200, detail.text
    content = portal.get(f"{API_V1_PREFIX}/artifacts/{artifact}/content",
                         headers=_auth(token))
    assert content.status_code == 200
    assert content.content.startswith(b"\x89PNG"), "canned bytes are not an image"


def test_the_mode_is_named_on_every_job(portal):
    _sign_in(portal, credits=200)
    assert _run(portal, _issue(portal, "test"))["mode"] == "test"
    assert _run(portal, _issue(portal, "live"))["mode"] == "live"


# ── Live and test never mix ──────────────────────────────────────────────────

def test_neither_key_can_read_the_other_s_job(portal):
    """The same 404 ownership uses: no oracle, in either direction."""
    _sign_in(portal, credits=200)
    live_token = _issue(portal, "live")
    test_token = _issue(portal, "test")

    live_job = _run(portal, live_token)["id"]
    test_job = _run(portal, test_token)["id"]

    assert portal.get(f"{API_V1_PREFIX}/jobs/{live_job}",
                      headers=_auth(test_token)).status_code == 404
    assert portal.get(f"{API_V1_PREFIX}/jobs/{test_job}",
                      headers=_auth(live_token)).status_code == 404


def test_a_listing_shows_one_world_at_a_time(portal):
    _sign_in(portal, credits=200)
    live_token = _issue(portal, "live")
    test_token = _issue(portal, "test")
    live_job = _run(portal, live_token)["id"]
    test_job = _run(portal, test_token)["id"]

    live_ids = [item["id"] for item in portal.get(
        f"{API_V1_PREFIX}/jobs", headers=_auth(live_token)).json()["items"]]
    test_ids = [item["id"] for item in portal.get(
        f"{API_V1_PREFIX}/jobs", headers=_auth(test_token)).json()["items"]]

    assert live_job in live_ids and test_job not in live_ids
    assert test_job in test_ids and live_job not in test_ids


def test_a_job_made_before_this_existed_reads_as_live(portal):
    """Every job without a mode is live work — including everything the web UI
    creates. A test key must not inherit the account's whole history."""
    user_id = _sign_in(portal, credits=200)
    live_token = _issue(portal, "live")
    test_token = _issue(portal, "test")

    from platform_core import jobs as jobq

    gen, db = _session()
    try:
        legacy = jobq.submit(db, user_id=user_id, app_slug="thumbnail",
                             job_type="thumbnail.tao_anh",
                             params={"topic": "old", "count": 1})
        db.commit()
        legacy_id = legacy.id
    finally:
        _close(gen)

    live_ids = [item["id"] for item in portal.get(
        f"{API_V1_PREFIX}/jobs", headers=_auth(live_token)).json()["items"]]
    test_ids = [item["id"] for item in portal.get(
        f"{API_V1_PREFIX}/jobs", headers=_auth(test_token)).json()["items"]]
    assert legacy_id in live_ids
    assert legacy_id not in test_ids


def test_a_test_key_cannot_cancel_a_live_job(portal):
    _sign_in(portal, credits=200)
    live_token = _issue(portal, "live")
    test_token = _issue(portal, "test")

    quote = portal.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": TOOL, "input": INPUT},
                        headers=_auth(live_token)).json()
    created = portal.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quote["quote"], "input": INPUT},
        headers=_auth(live_token, f"sb-{uuid.uuid4().hex[:10]}"))
    job_id = created.json()["id"]

    denied = portal.post(f"{API_V1_PREFIX}/jobs/{job_id}/cancel",
                         headers=_auth(test_token))
    assert denied.status_code == 404, denied.text
    # …and the live owner can still cancel it, so the refusal was about the
    # world and not about breaking cancellation.
    assert portal.post(f"{API_V1_PREFIX}/jobs/{job_id}/cancel",
                       headers=_auth(live_token)).status_code == 200


def test_a_test_key_cannot_download_a_live_artifact(portal):
    _sign_in(portal, credits=200)
    live_token = _issue(portal, "live")
    test_token = _issue(portal, "test")

    artifact = _run(portal, live_token)["outputs"][0]["id"]
    denied = portal.get(f"{API_V1_PREFIX}/artifacts/{artifact}",
                        headers=_auth(test_token))
    assert denied.status_code == 404, denied.text


# ── The webhook a receiver actually gets ─────────────────────────────────────

def test_a_test_delivery_is_signed_like_a_live_one_and_says_it_is_test(portal):
    """The whole point of exercising webhooks in a sandbox.

    Same signature algorithm, same header, same payload shape — otherwise a
    receiver that verifies here would reject production traffic. ``mode`` is
    what lets one receiver serve both worlds.
    """
    from platform_core.public_api import webhook_console

    user_id = _sign_in(portal, credits=200)
    test_token = _issue(portal, "test")
    created = portal.post(f"{API_V1_PREFIX}/webhooks",
                          json={"url": RECEIVER},
                          headers=_auth(test_token))
    assert created.status_code in (200, 201), created.text
    secret = created.json()["secret"]

    _run(portal, test_token)

    gen, db = _session()
    try:
        rows = webhook_console.deliveries_for(db, user_id=user_id)
    finally:
        _close(gen)
    assert rows, "a finished test job queued no delivery"
    payload = dict(rows[0].payload or {})
    assert payload["data"]["mode"] == "test"

    body = webhooks.canonical_body(payload)
    stamp = int(time.time())
    signature = webhooks.sign(secret, timestamp=stamp,
                              event_id=payload["id"], body=body)
    assert webhooks.verify(secret, timestamp=stamp, event_id=payload["id"],
                           body=body, signature=signature)


def test_a_live_delivery_still_says_live(portal):
    from platform_core.public_api import webhook_console

    user_id = _sign_in(portal, credits=200)
    live_token = _issue(portal, "live")
    portal.post(f"{API_V1_PREFIX}/webhooks",
                json={"url": RECEIVER},
                headers=_auth(live_token))
    _run(portal, live_token)

    gen, db = _session()
    try:
        rows = webhook_console.deliveries_for(db, user_id=user_id)
    finally:
        _close(gen)
    assert rows and dict(rows[0].payload)["data"]["mode"] == "live"


# ── The portal ───────────────────────────────────────────────────────────────

def test_the_portal_names_the_environment_of_every_key(portal):
    _sign_in(portal)
    _issue(portal, "live")
    _issue(portal, "test")

    page = portal.get("/developers/keys").text
    assert "Test" in page and "Live" in page
    assert 'name="mode"' in page, "the portal offers no way to choose"


def test_the_usage_page_marks_a_test_line(portal):
    _sign_in(portal, credits=200)
    _run(portal, _issue(portal, "test"))
    page = portal.get("/developers/usage").text
    assert "Test" in page


# ── The unit rules, without an HTTP app ──────────────────────────────────────

def test_is_test_defaults_to_live_for_anything_unset():
    assert sandbox.is_test("test") is True
    assert sandbox.is_test("live") is False
    assert sandbox.is_test("") is False
    assert sandbox.is_test(None) is False
    assert sandbox.is_test("TEST") is False, "only the exact token counts"


def test_the_canned_result_follows_the_schema_it_is_given():
    class _Tool:
        output_schema = {"properties": {
            "picture": {"type": "artifact"},
            "gallery": {"type": "artifact[]"},
            "package": {"type": "object"},
            "caption": {"type": "string"},
        }}
        output_counts = {"gallery": "count"}

    class _Storage:
        def __init__(self):
            self.written = []

        def put(self, key, stream, content_type=""):
            self.written.append((key, stream.read(), content_type))

    storage = _Storage()
    result = sandbox.canned_result(_Tool(), {"owner_id": "u1", "count": 3},
                                   storage)

    assert set(result) == {"picture", "gallery", "package", "caption"}
    assert isinstance(result["gallery"], list) and len(result["gallery"]) == 3
    assert result["package"]["sandbox"] is True
    assert result["caption"] == sandbox.SAMPLE_TEXT
    assert len(storage.written) == 4, "one file per artifact, three in the list"
    assert all(data.startswith(b"\x89PNG") for _key, data, _ct in storage.written)
    assert all(key.startswith("users/u1/sandbox/")
               for key, _data, _ct in storage.written)
