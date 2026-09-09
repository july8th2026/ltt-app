"""EXT-15 — pricing versions, the simulator, and cost kept apart from revenue.

Three acceptance criteria, and all three are about what must **not** happen:

* **no retroactive price mutation** — publishing a new version cannot change
  what an issued quote promised, what a created job recorded, or what the ledger
  says;
* **the ledger remains billing truth** — nothing in pricing or costing writes,
  adjusts or hides a credit entry;
* **pricing publish is audited** — every publish, schedule and retire leaves a
  row naming who did it and why.

Plus the one the brief states in passing and which is easy to get wrong: cost
figures are **estimates**, and must be stored and shown as such.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import (costing, keys as devkeys, limits,
                                      pricing)
from platform_core.public_api.config import load_public_api_config
from platform_core.public_api.tables import (PRICE_ACTIVE, PRICE_DRAFT,
                                             PRICE_RETIRED, PRICE_SCHEDULED)
from server.api.inventory import API_V1_PREFIX

PEPPER = "pricing-test-pepper-" + "q" * 40
TOOL = "image.thumbnail"
SCOPES = ("tools:read", "jobs:create", "jobs:read", "artifacts:read")
INPUT = {"topic": "pricing", "count": 1}


@pytest.fixture()
def portal(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'pricing.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    for name in costing.RATE_ENV.values():
        monkeypatch.delenv(name, raising=False)
    limits.reset()

    import platform_core.db as dbmod
    import platform_core.storage as storage_mod
    dbmod.reset_engine()
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())

    # 🔴 Chỉ thay MÁY VẼ, không thay gì khác: dựng prompt, lưu trữ, báo
    #    credit và hình dạng kết quả đều chạy thật. Trước pha 06.3 chỗ này vá
    #    `thumbnail_jobs._goi_gemini`; hàm ấy đã bị xoá cùng động cơ Gemini.
    import apps.thumbnail.jobs as thumbnail_jobs
    from tests.gia_dieu_phoi_anh import tiem as _tiem_dieu_phoi
    _tiem_dieu_phoi(monkeypatch, thumbnail_jobs)

    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "pricing-secret-value",
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


def _sign_in(client, credits: int = 500) -> str:
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    email = f"pr-{uuid.uuid4().hex[:6]}@example.com"
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


def _issue(client) -> str:
    page = client.get("/developers/keys").text
    created = client.post("/developers/keys",
                          data={"name": "pricing", "csrf_token": _csrf(page),
                                "scopes": list(SCOPES)})
    return re.search(r"<code>(ltt_sk_[^<]+)</code>", created.text).group(1)


def _auth(token: str, idem: str = "") -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if idem:
        headers["Idempotency-Key"] = idem
    return headers


def _quote(client, token, payload=None):
    return client.post(f"{API_V1_PREFIX}/quotes",
                       json={"tool": TOOL, "input": dict(payload or INPUT)},
                       headers=_auth(token))


def _ledger_snapshot(user_id: str) -> list:
    from sqlalchemy import select

    from platform_core.models import CreditEntry

    gen, db = _session()
    try:
        rows = db.execute(select(CreditEntry).where(
            CreditEntry.user_id == user_id).order_by(
                CreditEntry.id)).scalars().all()
        return [(row.kind, row.delta, row.job_id, row.note) for row in rows]
    finally:
        _close(gen)


def _publish(db, **kwargs):
    version = pricing.create_version(db, **kwargs)
    pricing.publish(db, version, published_by="operator@example.com")
    return version


def _tool():
    from platform_core.public_api.catalog import build_catalog

    config = load_public_api_config({"LTT_PUBLIC_API": "1",
                                     "LTT_PUBLIC_API_TOOLS": TOOL})
    return next(item for item in build_catalog(config) if item.name == TOOL)


# ── A version records a regime; it does not price anything ───────────────────

def test_with_no_version_a_quote_is_still_priced_and_labelled(portal):
    """A deployment that never opens the pricing console still works.

    The label is a stable word rather than an empty string, because an empty
    field later reads as "lost" rather than "never set".
    """
    _sign_in(portal)
    token = _issue(portal)
    answer = _quote(portal, token)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["credit"] > 0
    assert body["pricing_version"] == pricing.UNVERSIONED


def test_the_published_version_names_itself_on_the_quote(portal):
    _sign_in(portal)
    token = _issue(portal)
    gen, db = _session()
    try:
        _publish(db, tool=TOOL, label="2026-08-a",
                 formula_ref="apps.thumbnail.manifest.credit_cost")
        db.commit()
    finally:
        _close(gen)

    body = _quote(portal, token).json()
    assert body["pricing_version"] == "2026-08-a"


def test_bounds_clamp_the_app_s_number_without_replacing_it(portal):
    """The app still computes the price; the published regime bounds it.

    If the two disagree the published bound wins — a customer was shown that
    bound and cannot be charged past it.
    """
    _sign_in(portal)
    token = _issue(portal)
    natural = _quote(portal, token).json()["credit"]
    assert natural > 1

    gen, db = _session()
    try:
        _publish(db, tool=TOOL, label="capped", max_credit=1)
        db.commit()
    finally:
        _close(gen)

    assert _quote(portal, token).json()["credit"] == 1


def test_the_job_holds_exactly_what_the_quote_promised(portal):
    """The bug this was written for: quoted 7, held 10.

    `submit_with_credit` recomputed the price from the app's formula and never
    saw the published cap, so the ceiling applied to what the customer was
    *shown* and not to what they were *charged*. No test caught it because every
    earlier case priced a call whose bounded price equalled its raw price —
    only pressing the button in a browser did.
    """
    from platform_core import credit

    user_id = _sign_in(portal)
    token = _issue(portal)
    gen, db = _session()
    try:
        _publish(db, tool=TOOL, label="capped-hold", max_credit=1)
        db.commit()
        before = credit.so_du(db, user_id)
    finally:
        _close(gen)

    quoted = _quote(portal, token, {"topic": "hold", "count": 4}).json()
    assert quoted["credit"] == 1, "the cap must reach the quote"

    created = portal.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quoted["quote"],
              "input": {"topic": "hold", "count": 4}},
        headers=_auth(token, f"pr-{uuid.uuid4().hex[:8]}"))
    assert created.status_code == 201, created.text
    assert created.json()["credit"]["held"] == 1, "held more than promised"

    gen, db = _session()
    try:
        assert credit.so_du(db, user_id) == before - 1
    finally:
        _close(gen)


def test_the_ui_path_still_prices_itself(portal):
    """No `quoted_credit` means compute as before — the web app never quotes."""
    from platform_core.job_submit import submit_with_credit

    user_id = _sign_in(portal)
    gen, db = _session()
    try:
        job = submit_with_credit(
            db, user_id=user_id, app_slug="thumbnail",
            job_type="thumbnail.generate",
            params={"topic": "ui", "count": 2, "owner_id": user_id})
        db.commit()
        from apps.thumbnail.manifest import _cost
        from platform_core import credit

        # 🔴 Đọc HÀM GIÁ, không gõ lại con số. Con số đổi 5 → 3 ngày 09/09 khi app
        #    đổi model; mệnh đề *"đường UI tự tính giá của nó"* thì không đổi, và
        #    một hằng số gõ tay ở đây chỉ đo được rằng ai đó chưa sửa nó.
        assert credit.so_da_giu(db, job.id) == _cost({"count": 2})
    finally:
        _close(gen)


def test_rounding_modes_do_what_they_say():
    class _Version:
        rounding = 10
        rounding_mode = "up"
        min_credit = None
        max_credit = None

    version = _Version()
    assert pricing.apply_bounds(11, version) == 20
    version.rounding_mode = "down"
    assert pricing.apply_bounds(19, version) == 10
    version.rounding_mode = "nearest"
    assert pricing.apply_bounds(14, version) == 10
    assert pricing.apply_bounds(16, version) == 20
    assert pricing.apply_bounds(7, None) == 7, "no version means no change"


def test_a_model_specific_version_beats_a_tool_wide_one(portal):
    gen, db = _session()
    try:
        _publish(db, tool=TOOL, label="wide", max_credit=100)
        _publish(db, tool=TOOL, label="narrow", model="fast", max_credit=7)
        db.commit()

        assert pricing.active_for(db, tool=TOOL).label == "wide"
        assert pricing.active_for(db, tool=TOOL, model="fast").label == "narrow"
        # …and a row naming a different model must not win.
        assert pricing.active_for(db, tool=TOOL, model="slow").label == "wide"
    finally:
        _close(gen)


# ── No retroactive price mutation ────────────────────────────────────────────

def test_publishing_a_new_price_does_not_change_an_issued_quote(portal):
    """The property the whole design exists for.

    The amount and the version label were signed together at the same instant;
    neither can be edited afterwards without breaking the signature.
    """
    _sign_in(portal)
    token = _issue(portal)
    gen, db = _session()
    try:
        _publish(db, tool=TOOL, label="old", max_credit=100)
        db.commit()
    finally:
        _close(gen)

    quoted = _quote(portal, token).json()
    assert quoted["pricing_version"] == "old"

    gen, db = _session()
    try:
        _publish(db, tool=TOOL, label="new", max_credit=1)
        db.commit()
    finally:
        _close(gen)

    # The quote is now priced under a regime that no longer applies, so the
    # platform refuses it rather than silently repricing.
    refused = portal.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quoted["quote"], "input": INPUT},
        headers=_auth(token, f"pr-{uuid.uuid4().hex[:8]}"))
    assert refused.status_code == 409, refused.text
    assert refused.json()["code"] == "price_changed"
    assert refused.json()["quoted_credit"] == quoted["credit"]


def test_a_job_keeps_the_version_it_was_quoted_under(portal):
    _sign_in(portal)
    token = _issue(portal)
    gen, db = _session()
    try:
        _publish(db, tool=TOOL, label="at-submit-time")
        db.commit()
    finally:
        _close(gen)

    quoted = _quote(portal, token).json()
    created = portal.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quoted["quote"], "input": INPUT},
        headers=_auth(token, f"pr-{uuid.uuid4().hex[:8]}"))
    assert created.status_code == 201, created.text

    gen, db = _session()
    try:
        _publish(db, tool=TOOL, label="much-later")
        db.commit()

        from platform_core.models import Job
        from platform_core.public_api.invocation import api_meta

        job = db.get(Job, created.json()["id"])
        assert api_meta(job)["pricing_version"] == "at-submit-time"
    finally:
        _close(gen)


def test_publishing_closes_the_old_window_rather_than_editing_it(portal):
    gen, db = _session()
    try:
        first = _publish(db, tool=TOOL, label="first", max_credit=50)
        db.commit()
        assert first.status == PRICE_ACTIVE
        assert first.effective_until is None

        second = _publish(db, tool=TOOL, label="second", max_credit=60)
        db.commit()
        db.refresh(first)

        assert first.effective_until is not None, "the old window must close"
        assert first.max_credit == 50, "the old numbers must not be edited"
        assert first.label == "first"
        assert pricing.active_for(db, tool=TOOL).label == second.label
    finally:
        _close(gen)


def test_retiring_stops_a_version_without_repricing_what_it_priced(portal):
    gen, db = _session()
    try:
        version = _publish(db, tool=TOOL, label="retiring", max_credit=42)
        db.commit()
        pricing.retire(db, version)
        db.commit()

        assert version.status == PRICE_RETIRED
        assert version.max_credit == 42
        assert pricing.active_for(db, tool=TOOL) is None
    finally:
        _close(gen)


# ── The ledger remains billing truth ─────────────────────────────────────────

def test_pricing_and_costing_never_touch_the_ledger(portal):
    """Snapshot every credit row before and after, and compare.

    The strongest form of "does not touch the ledger" is to look at all of it.
    """
    user_id = _sign_in(portal)
    token = _issue(portal)
    quoted = _quote(portal, token).json()
    portal.post(f"{API_V1_PREFIX}/jobs",
                json={"tool": TOOL, "quote": quoted["quote"], "input": INPUT},
                headers=_auth(token, f"pr-{uuid.uuid4().hex[:8]}"))

    before = _ledger_snapshot(user_id)
    assert before, "this test needs a ledger to compare"

    gen, db = _session()
    try:
        version = _publish(db, tool=TOOL, label="ledger-probe", max_credit=1)
        costing.observe(db, job_id="j1", tool=TOOL, kind="duration_ms",
                        quantity=5000, unit_cost_micros=3)
        costing.margin(db, since=datetime.now(timezone.utc)
                       - timedelta(days=1))
        costing.margin_by_tool(db, since=datetime.now(timezone.utc)
                               - timedelta(days=1))
        pricing.retire(db, version)
        db.commit()
    finally:
        _close(gen)

    assert _ledger_snapshot(user_id) == before


# ── The simulator ────────────────────────────────────────────────────────────

def test_the_simulator_uses_the_production_formula(portal):
    """Not a copy of the arithmetic — the same call the quote path makes.

    A simulator with its own maths answers a question nobody asked; what matters
    is what the customer would actually be billed.
    """
    _sign_in(portal)
    token = _issue(portal)
    quoted = _quote(portal, token, {"topic": "x", "count": 3}).json()

    gen, db = _session()
    try:
        simulated = pricing.simulate(db, tool=_tool(),
                                     params={"topic": "x", "count": 3})
    finally:
        _close(gen)
    assert simulated.credit == quoted["credit"]
    assert simulated.tool == TOOL


def test_a_simulation_charges_nothing_and_mints_no_quote(portal):
    user_id = _sign_in(portal)
    _issue(portal)
    before = _ledger_snapshot(user_id)

    gen, db = _session()
    try:
        result = pricing.simulate(db, tool=_tool(), params=INPUT)
        db.commit()
    finally:
        _close(gen)

    assert result.credit > 0
    assert not hasattr(result, "quote"), "a simulation must not be presentable"
    assert _ledger_snapshot(user_id) == before


def test_the_simulator_reports_when_a_bound_moved_the_number(portal):
    gen, db = _session()
    try:
        _publish(db, tool=TOOL, label="tight", max_credit=1)
        db.commit()
        result = pricing.simulate(db, tool=_tool(),
                                  params={"topic": "x", "count": 4})
        assert result.raw_credit > 1
        assert result.credit == 1
        assert result.bounded is True
        assert result.pricing_version == "tight"
    finally:
        _close(gen)


# ── Cost is evidence plus an assumption, and says so ─────────────────────────

def test_no_configured_rate_means_no_observation(portal):
    """A cost of exactly nothing is a claim this module is not entitled to."""
    gen, db = _session()
    try:
        assert costing.rates({}) == {}
        assert costing.observe(db, job_id="j", tool=TOOL, kind="duration_ms",
                               quantity=1000, unit_cost_micros=0) is None
    finally:
        _close(gen)


def test_a_rate_turns_a_measurement_into_a_labelled_estimate(portal):
    gen, db = _session()
    try:
        row = costing.observe(db, job_id="j", tool=TOOL, kind="duration_ms",
                              quantity=2000, unit_cost_micros=5,
                              source="evidence:job_events")
        db.commit()
        assert row.cost_micros == 10_000
        assert row.is_estimate is True, "money from a configured rate is a guess"
        assert row.source == "evidence:job_events", "the quantity was measured"
    finally:
        _close(gen)


def test_tokens_are_only_counted_when_the_handler_reported_them(portal):
    """`api_keys.total_tokens` is a per-credential running total shared by every
    job it served; splitting it would be invention, not measurement."""
    class _Job:
        id = "j1"
        result = {"image_keys": ["a"], "tokens": 1234}
        params = {"_api": {"tool": TOOL}}

    class _Bare:
        id = "j2"
        result = {"image_keys": ["a"]}
        params = {"_api": {"tool": TOOL}}

    assert costing._tokens(_Job()) == 1234
    assert costing._tokens(_Bare()) == 0


def test_margin_reads_revenue_from_the_ledger_and_cost_from_observations(portal):
    user_id = _sign_in(portal)
    token = _issue(portal)
    quoted = _quote(portal, token).json()
    portal.post(f"{API_V1_PREFIX}/jobs",
                json={"tool": TOOL, "quote": quoted["quote"], "input": INPUT},
                headers=_auth(token, f"pr-{uuid.uuid4().hex[:8]}"))

    since = datetime.now(timezone.utc) - timedelta(hours=1)
    gen, db = _session()
    try:
        window = costing.margin(db, since=since)
        assert window.revenue_credit == quoted["credit"]
        assert window.cost_micros == 0
        assert window.cost_is_estimate is True

        costing.observe(db, job_id="j", tool=TOOL, kind="duration_ms",
                        quantity=1000, unit_cost_micros=2)
        db.commit()
        richer = costing.margin(db, since=since)
        assert richer.cost_micros == 2000
        assert richer.observations == 1
    finally:
        _close(gen)
    assert user_id


def test_a_negative_margin_alerts_the_operators_not_a_null_user(portal):
    """The notification table's owner is a foreign key to a real person, and it
    should stay that way — a nullable owner would make every other query handle
    a case that exists for one alert."""
    from platform_core.public_api import notifications
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    try:
        operator = tao_nguoi_dung(db, email=f"op-{uuid.uuid4().hex[:6]}@x.com",
                                  password="a-good-password-12", role="admin",
                                  is_verified=True)
        db.flush()
        costing.observe(db, job_id="j", tool=TOOL, kind="duration_ms",
                        quantity=1_000_000, unit_cost_micros=50)
        db.commit()

        raised = costing.scan_for_alerts(db, hours=24)
        db.commit()
        assert raised, "a negative estimated margin should be said out loud"
        rows = notifications.list_for(db, user_id=operator.id)
        assert any(row.kind == costing.ALERT_KIND for row in rows)
        body = next(row for row in rows if row.kind == costing.ALERT_KIND).body
        assert "ƯỚC LƯỢNG" in body, "the alert must not read as settled cost"
    finally:
        _close(gen)


def test_a_healthy_margin_says_nothing(portal):
    user_id = _sign_in(portal)
    token = _issue(portal)
    quoted = _quote(portal, token).json()
    portal.post(f"{API_V1_PREFIX}/jobs",
                json={"tool": TOOL, "quote": quoted["quote"], "input": INPUT},
                headers=_auth(token, f"pr-{uuid.uuid4().hex[:8]}"))

    gen, db = _session()
    try:
        costing.observe(db, job_id="j", tool=TOOL, kind="duration_ms",
                        quantity=10, unit_cost_micros=1)
        db.commit()
        assert costing.scan_for_alerts(db, hours=24) == []
    finally:
        _close(gen)
    assert user_id


# ── Version lifecycle rules ──────────────────────────────────────────────────

def test_a_draft_is_not_in_force_until_it_is_published(portal):
    gen, db = _session()
    try:
        pricing.create_version(db, tool=TOOL, label="draft-only", max_credit=1)
        db.commit()
        assert pricing.active_for(db, tool=TOOL) is None
    finally:
        _close(gen)


def test_a_future_version_is_scheduled_rather_than_active(portal):
    gen, db = _session()
    try:
        soon = datetime.now(timezone.utc) + timedelta(days=1)
        version = pricing.create_version(db, tool=TOOL, label="next-week",
                                         effective_from=soon)
        pricing.publish(db, version, published_by="op@example.com")
        db.commit()

        assert version.status == PRICE_SCHEDULED
        assert pricing.active_for(db, tool=TOOL) is None
        assert pricing.active_for(db, tool=TOOL,
                                  now=soon + timedelta(minutes=1)) is version
    finally:
        _close(gen)


def test_the_timeline_separates_now_next_and_done(portal):
    gen, db = _session()
    try:
        current = _publish(db, tool=TOOL, label="current")
        future = pricing.create_version(
            db, tool=TOOL, label="future",
            effective_from=datetime.now(timezone.utc) + timedelta(days=2))
        pricing.publish(db, future, published_by="op@example.com")
        db.commit()

        # A draft that starts *now* is still upcoming: it has never been in
        # force, so it cannot be history — and the person who just created it
        # would never look for it there. Caught by making one in a browser.
        draft = pricing.create_version(db, tool=TOOL, label="just-drafted")
        db.commit()

        line = pricing.timeline(db, tool=TOOL)
        assert line.current is current
        assert {row.label for row in line.upcoming} == {"future", "just-drafted"}
        assert draft not in line.history
    finally:
        _close(gen)


def test_a_version_refuses_nonsense(portal):
    gen, db = _session()
    try:
        pricing.create_version(db, tool=TOOL, label="taken")
        db.commit()
        cases = (
            {"tool": "", "label": "x"},
            {"tool": TOOL, "label": ""},
            {"tool": TOOL, "label": "taken"},
            {"tool": TOOL, "label": "y", "rounding_mode": "sideways"},
            {"tool": TOOL, "label": "z", "min_credit": 10, "max_credit": 1},
            {"tool": TOOL, "label": "w",
             "effective_from": datetime.now(timezone.utc),
             "effective_until": datetime.now(timezone.utc)
             - timedelta(hours=1)},
        )
        for kwargs in cases:
            with pytest.raises(pricing.PricingError):
                pricing.create_version(db, **kwargs)
            db.rollback()
    finally:
        _close(gen)


def test_a_retired_version_cannot_be_republished(portal):
    gen, db = _session()
    try:
        version = _publish(db, tool=TOOL, label="gone")
        pricing.retire(db, version)
        db.commit()
        assert version.status == PRICE_RETIRED
        with pytest.raises(pricing.PricingError):
            pricing.publish(db, version)
    finally:
        _close(gen)


def test_a_draft_starts_as_draft():
    assert PRICE_DRAFT == "draft"
    assert PRICE_ACTIVE == "active"


# ── The portal simulator ─────────────────────────────────────────────────────

def test_the_portal_prices_a_call_without_charging_for_it(portal):
    user_id = _sign_in(portal)
    _issue(portal)
    before = _ledger_snapshot(user_id)

    page = portal.get(f"/developers/pricing?tool={TOOL}")
    assert page.status_code == 200, page.text[:300]
    assert "credit" in page.text
    assert _ledger_snapshot(user_id) == before


def test_the_portal_simulation_matches_the_real_quote(portal):
    _sign_in(portal)
    token = _issue(portal)
    payload = {"topic": "match", "count": 2}
    quoted = _quote(portal, token, payload).json()["credit"]

    import json

    page = portal.get("/developers/pricing", params={
        "tool": TOOL, "input": json.dumps(payload)}).text
    assert f">{quoted}</strong>" in page.replace(" ", "") or str(quoted) in page


def test_bad_json_is_reported_rather_than_swallowed(portal):
    _sign_in(portal)
    _issue(portal)
    page = portal.get("/developers/pricing",
                      params={"tool": TOOL, "input": "{not json"}).text
    assert "b-err" in page


def test_the_portal_page_says_a_simulation_is_not_a_quote(portal):
    _sign_in(portal)
    _issue(portal)
    page = portal.get("/developers/pricing").text
    assert "KHÔNG sinh báo giá" in page
