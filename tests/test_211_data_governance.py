"""EXT-19 — what we keep about a customer, for how long, and what never goes.

Two acceptance criteria:

* **audit and billing records survive** — proven by aging everything by a decade
  and checking the ledger, the admin log and the pricing versions are untouched;
* **no raw secret and no presigned URL is retained** — proven by making a real
  key, a real webhook, a real artifact, then searching every table's contents.

And one property the inventory only earns if it is enforced: every claim in it
must be **true**. A retention policy naming a function nobody calls is worse than
no policy, because it reads as a promise — which is exactly the state
`api_security_events` was in when this file was written.
"""
from __future__ import annotations

import inspect
import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from platform_core.public_api import governance, keys as devkeys, limits
from server.api.inventory import API_V1_PREFIX

PEPPER = "gov-test-pepper-" + "g" * 40
TOOL = "image.thumbnail"
SCOPES = ("tools:read", "jobs:create", "jobs:read", "artifacts:read",
          "webhooks:manage")
RECEIVER = "https://receiver.example.com/hook"


def _public_dns(host: str) -> list:
    if host.endswith("example.com"):
        return ["93.184.216.34"]
    raise OSError(f"unknown test host: {host}")


@pytest.fixture()
def portal(tmp_path, monkeypatch):
    from platform_core.public_api import webhooks

    monkeypatch.setattr(webhooks, "_system_resolver", _public_dns)
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'gov.db').as_posix()}")
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
    # Job anh gianh `anh_3090` tu dual-model 5.5, va luat 0 fail-closed: khong co
    # dong `gpu_residency` thi worker chi tra job ve hang doi, khong chay handler.
    # Ly do day du: `tests/conftest.py::mo_cu_tru_3090`.
    from platform_core.llm import residency as _residency

    from tests.conftest import mo_cu_tru_3090
    mo_cu_tru_3090(_residency.ANH)

    import apps.thumbnail.jobs as thumbnail_jobs
    from tests.gia_dieu_phoi_anh import tiem as _tiem_dieu_phoi
    _tiem_dieu_phoi(monkeypatch, thumbnail_jobs)

    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "gov-secret-value",
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


def _account(client) -> tuple:
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    email = f"gov-{uuid.uuid4().hex[:6]}@example.com"
    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=email, password="a-good-password-12")
        user.is_verified = True
        db.flush()
        credit.cap_tay(db, user.id, 500, by="test")
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
    made = client.post("/developers/keys",
                       data={"name": "gov", "csrf_token": _csrf(keys_page),
                             "scopes": list(SCOPES)})
    token = re.search(r"<code>(ltt_sk_[^<]+)</code>", made.text).group(1)
    return user_id, token


def _run_one_call(client, token) -> str:
    auth = {"Authorization": f"Bearer {token}"}
    payload = {"topic": "governance", "count": 1}
    quote = client.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": TOOL, "input": payload}, headers=auth)
    created = client.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quote.json()["quote"], "input": payload},
        headers={**auth, "Idempotency-Key": f"gov-{uuid.uuid4().hex[:10]}"})
    assert created.status_code == 201, created.text

    from platform_core.job_runner import _chay_mot_job

    assert _chay_mot_job("gov-worker") is True
    return created.json()["id"]


def _every_row_as_text(db) -> str:
    """Everything in every table, flattened. Blunt on purpose.

    A search for a secret has to look where nobody thought to put one.
    """
    from platform_core.db import Base

    chunks = []
    for table in Base.metadata.sorted_tables:
        try:
            rows = db.execute(select(table)).all()
        except Exception:  # noqa: BLE001 - a table this deployment lacks
            continue
        for row in rows:
            chunks.append(" ".join(str(value) for value in row))
    return "\n".join(chunks)


# ── The inventory is complete, and its claims are true ───────────────────────

def test_every_table_has_a_retention_class(portal):
    """The ratchet. On its first run it found twenty-five stores nobody had
    written a policy for — including every chat message and storyboard scene."""
    from platform_core.db import Base
    from platform_core.registry import load_app_tables

    load_app_tables()
    missing = governance.unclassified(sorted(Base.metadata.tables))
    assert missing == [], (
        f"these tables hold data nobody has classified: {missing}. Add them to "
        f"governance.STORES, or to NOT_CUSTOMER_DATA if they hold nothing "
        f"about a customer.")


def test_every_class_is_one_of_the_declared_ones():
    for store in governance.STORES:
        assert store.klass in governance.CLASSES, store.table


def test_every_purge_claim_names_a_function_that_exists_and_runs():
    """The failure that motivated this whole prompt.

    `api_security_events` shipped with a `purge_expired()` nothing called. A
    policy that names a function nobody runs is not a policy, it is a promise —
    so every `purged_by` claim is checked against the worker's own sweep.
    """
    import platform_core.job_runner as runner
    from platform_core import registry

    sweep = inspect.getsource(runner._don_du_lieu_het_han)
    other_sweeps = (inspect.getsource(runner.run_forever)
                    + inspect.getsource(runner))

    # Từ 2026-08-24 hợp đồng app có `AppManifest.bao_tri`, và nền tảng gọi nó
    # trong cùng vòng bảo trì (dưới cùng một lease). Nên một app dọn bảng của
    # chính nó là một lời khai HỢP LỆ — nhưng vẫn phải kiểm, không phải tin.
    # Không mở rộng phép kiểm ở đây thì một app dọn dữ liệu đúng cách sẽ bị báo
    # đỏ, và cách sửa dễ nhất khi đó là **xoá lời khai** — tức mất đúng thứ luật
    # này sinh ra để giữ.
    # Duyệt MỌI app, không qua `registry.viec_bao_tri()` — hàm đó lọc theo cờ
    # bật/tắt (fail-closed lúc chạy, đúng như nó phải thế). Nhưng chính sách lưu
    # trữ là một văn bản **tĩnh**: nó phải kiểm được như nhau dù app đang bật hay
    # tắt. Dùng hàm lọc ở đây thì test xanh trên máy có `LTT_VPS=1` và đỏ trên
    # máy không có — loại hỏng tệ hơn cả việc không kiểm.
    for item in registry.discover():
        ham = item.manifest.bao_tri
        if ham is not None:
            other_sweeps += inspect.getsource(inspect.getmodule(ham))

    for store in governance.STORES:
        if not store.purged_by:
            continue
        function = store.purged_by.split(" ")[0]         # "module.function"
        module, _, name = function.rpartition(".")
        assert name, store.purged_by
        # The claim must name something the worker actually calls.
        assert f"{name}" in sweep or f"{name}" in other_sweeps, (
            f"{store.table} claims it is purged by {store.purged_by}, but the "
            f"worker never calls it")


def test_operational_stores_all_declare_who_removes_them():
    """A row that never leaves is a decision, and it has to be a stated one."""
    for store in governance.by_class(governance.OPERATIONAL):
        assert store.retention_days, store.table
        assert store.purged_by, (
            f"{store.table} has a retention window but nothing that enforces it")


def test_evidence_is_never_given_a_retention_window():
    """An audit trail that ages out is not an audit trail."""
    for store in governance.by_class(governance.EVIDENCE):
        assert store.retention_days is None, store.table
        assert not store.purged_by, store.table


def test_every_store_says_why_it_exists():
    """A store nobody can justify is one to delete.

    The check is for a *reason*, not for a word count. An earlier version
    demanded twenty characters and started pushing me to pad descriptions that
    were already clear — "Nhãn người dùng gắn." explains a tag table completely.
    A length threshold measures verbosity; what matters is that somebody wrote
    something meant, so the bar is set where only emptiness and placeholders
    fall below it.
    """
    placeholders = {"todo", "tbd", "n/a", "-", "?", "xxx"}
    for store in governance.STORES:
        reason = store.reason.strip()
        assert reason, store.table
        assert reason.lower().rstrip(".") not in placeholders, store.table
        assert len(reason.split()) >= 3, (
            f"{store.table}: a reason should be a sentence, not a label")
        assert store.readable_by, store.table


# ── Audit and billing records survive ────────────────────────────────────────

def test_a_decade_of_retention_leaves_the_ledger_and_the_audit_log_intact(portal):
    """The acceptance criterion, applied with a blunt instrument.

    Everything is aged ten years and every sweep is run. What must remain is
    what somebody would need to answer a billing dispute or an access question.
    """
    from platform_core.models import CreditEntry, NhatKyAdmin
    from platform_core.public_api import pricing
    from platform_core.public_api.tables import ApiPricingVersion

    user_id, token = _account(portal)
    _run_one_call(portal, token)

    gen, db = _session()
    try:
        db.add(NhatKyAdmin(admin_email="op@example.com", hanh_dong="test",
                           doi_tuong="x", chi_tiet="y"))
        version = pricing.create_version(db, tool=TOOL, label="kept")
        pricing.publish(db, version, published_by="op@example.com")
        db.commit()

        # Compared as tuples, not ORM rows: two sessions give two objects for
        # the same row, and `==` on those compares identity.
        ledger_before = sorted(
            (row.id, row.kind, row.delta, row.job_id)
            for row in db.execute(select(CreditEntry)).scalars())
        assert ledger_before, "this test needs a ledger"

        ancient = datetime.now(timezone.utc) - timedelta(days=3650)
        from platform_core.db import Base

        for table in Base.metadata.sorted_tables:
            if "created_at" in table.c:
                db.execute(table.update().values(created_at=ancient))
        db.commit()
    finally:
        _close(gen)

    import platform_core.job_runner as runner

    runner._don_du_lieu_het_han()

    gen, db = _session()
    try:
        ledger_after = sorted(
            (row.id, row.kind, row.delta, row.job_id)
            for row in db.execute(select(CreditEntry)).scalars())
        assert ledger_after == ledger_before
        assert db.execute(select(NhatKyAdmin)).all(), "the audit log was purged"
        assert db.execute(select(ApiPricingVersion)).all(), "pricing history went"
        from platform_core.public_api.tables import DeveloperApiKey

        assert db.execute(select(DeveloperApiKey)).all(), "key evidence went"
    finally:
        _close(gen)


def test_the_operational_stores_really_do_empty(portal):
    """The other half: a sweep that preserves everything preserves nothing."""
    from platform_core.public_api import security_log
    from platform_core.public_api.tables import ApiRequestLog, ApiSecurityEvent

    user_id, token = _account(portal)
    portal.get(f"{API_V1_PREFIX}/jobs/nope",
               headers={"Authorization": f"Bearer {token}"})
    portal.get(f"{API_V1_PREFIX}/me",
               headers={"Authorization": "Bearer ltt_sk_" + "a" * 32 + "_"
                        + "b" * 43})

    gen, db = _session()
    try:
        assert db.execute(select(ApiRequestLog)).all()
        assert db.execute(select(ApiSecurityEvent)).all()
        ancient = datetime.now(timezone.utc) - timedelta(days=3650)
        from platform_core.db import Base

        for table in Base.metadata.sorted_tables:
            if "created_at" in table.c:
                db.execute(table.update().values(created_at=ancient))
        db.commit()
    finally:
        _close(gen)

    import platform_core.job_runner as runner

    runner._don_du_lieu_het_han()

    gen, db = _session()
    try:
        assert db.execute(select(ApiRequestLog)).all() == []
        assert db.execute(select(ApiSecurityEvent)).all() == []
        assert security_log.list_recent(db) == []
    finally:
        _close(gen)


def test_a_pending_webhook_delivery_is_never_purged(portal):
    """The row *is* the queue. Deleting it drops a callback silently."""
    from platform_core.public_api import outbox
    from platform_core.public_api.tables import (WebhookDelivery,
                                                 WEBHOOK_PENDING)

    user_id, _token = _account(portal)
    gen, db = _session()
    try:
        ancient = datetime.now(timezone.utc) - timedelta(days=3650)
        db.add(WebhookDelivery(
            id=str(uuid.uuid4()), subscription_id="s1", user_id=user_id,
            event_id="e1", event_type="job.succeeded", job_id="j1",
            payload={}, status=WEBHOOK_PENDING, created_at=ancient,
            next_attempt_at=ancient))
        db.commit()

        assert outbox.purge_expired(db) == 0, "a queued callback was deleted"
        db.commit()
        assert db.execute(select(WebhookDelivery)).all()
    finally:
        _close(gen)


def test_an_in_flight_idempotency_record_is_never_purged(portal):
    """Removing it mid-call reintroduces the double charge it prevents."""
    from platform_core.public_api import idempotency
    from platform_core.public_api.tables import (ApiIdempotencyRecord,
                                                 IDEMPOTENCY_IN_PROGRESS)

    gen, db = _session()
    try:
        ancient = datetime.now(timezone.utc) - timedelta(days=3650)
        db.add(ApiIdempotencyRecord(
            id=str(uuid.uuid4()), key_id="k1", user_id="u1",
            operation="create_job", idempotency_key="abc", request_hash="h",
            status=IDEMPOTENCY_IN_PROGRESS, created_at=ancient))
        db.commit()
        assert idempotency.purge_expired(db) == 0
        db.commit()
        assert db.execute(select(ApiIdempotencyRecord)).all()
    finally:
        _close(gen)


def test_every_sweep_is_idempotent(portal):
    """Running it twice must not do anything the first run did not."""
    import platform_core.job_runner as runner

    user_id, token = _account(portal)
    _run_one_call(portal, token)

    runner._don_du_lieu_het_han()
    gen, db = _session()
    try:
        first = _every_row_as_text(db)
    finally:
        _close(gen)

    runner._don_du_lieu_het_han()
    gen, db = _session()
    try:
        assert _every_row_as_text(db) == first
    finally:
        _close(gen)


# ── No raw secret, no presigned URL, retained anywhere ───────────────────────

def test_no_table_holds_a_key_secret_or_a_webhook_secret(portal):
    """Made for real, then searched for everywhere.

    Blunt by design: the interesting leak is always in the table nobody thought
    to check.
    """
    user_id, token = _account(portal)
    created = portal.post(f"{API_V1_PREFIX}/webhooks", json={"url": RECEIVER},
                          headers={"Authorization": f"Bearer {token}"})
    hook_secret = created.json()["secret"]
    key_secret = token.split("_", 3)[-1]
    _run_one_call(portal, token)

    gen, db = _session()
    try:
        blob = _every_row_as_text(db)
    finally:
        _close(gen)

    assert key_secret not in blob, "a key secret is stored somewhere"
    assert hook_secret not in blob, "a webhook signing secret is stored in clear"
    assert token not in blob


def test_no_table_holds_a_presigned_url(portal):
    """A presigned URL is a bearer credential with an expiry.

    Storing one turns a row that looks like metadata into a key to somebody's
    file, and rows outlive expiries in every incident that matters.
    """
    user_id, token = _account(portal)
    job_id = _run_one_call(portal, token)
    auth = {"Authorization": f"Bearer {token}"}
    finished = portal.get(f"{API_V1_PREFIX}/jobs/{job_id}", headers=auth).json()
    artifact = finished["outputs"][0]["id"]
    detail = portal.get(f"{API_V1_PREFIX}/artifacts/{artifact}",
                        headers=auth).json()
    url = str(detail.get("url") or "")

    gen, db = _session()
    try:
        blob = _every_row_as_text(db)
    finally:
        _close(gen)

    if url:
        assert url not in blob, "a presigned URL was written to the database"
    for marker in ("X-Amz-Signature", "X-Amz-Credential", "Signature="):
        assert marker not in blob, f"{marker} found in stored data"


def test_the_request_log_keeps_no_payload(portal):
    """It records that a call happened, not what was in it."""
    from platform_core.public_api.tables import ApiRequestLog

    user_id, token = _account(portal)
    secret_topic = f"topic-{uuid.uuid4().hex}"
    portal.post(f"{API_V1_PREFIX}/quotes",
                json={"tool": TOOL, "input": {"topic": secret_topic,
                                              "count": 1}},
                headers={"Authorization": f"Bearer {token}"})

    gen, db = _session()
    try:
        rows = db.execute(select(ApiRequestLog)).all()
        assert rows, "this test needs a recorded request"
        assert secret_topic not in " ".join(str(value) for row in rows
                                            for value in row)
    finally:
        _close(gen)


# ── Lifecycle: revoking on the way out ───────────────────────────────────────

def test_archiving_a_project_revokes_its_keys(portal):
    """Already true before this prompt; locked down here because the inventory
    now promises it."""
    from platform_core.public_api import projects
    from platform_core.public_api.tables import DeveloperApiKey

    user_id, token = _account(portal)
    gen, db = _session()
    try:
        project = projects.default_for(db, user_id=user_id)
        db.flush()
        revoked = projects.archive(db, project)
        db.commit()
        assert revoked >= 1
        keys = db.execute(select(DeveloperApiKey).where(
            DeveloperApiKey.user_id == user_id)).scalars().all()
        assert all(key.revoked_at is not None for key in keys)
        # …and the key rows themselves stay: they are evidence of spend.
        assert keys
    finally:
        _close(gen)

    assert portal.get(f"{API_V1_PREFIX}/me",
                      headers={"Authorization": f"Bearer {token}"}
                      ).status_code == 401


# ── Legal text is linked, never written here ─────────────────────────────────

def test_the_legal_links_point_at_the_existing_site():
    """Restating a legal promise creates a second promise, and the two differ."""
    for name, url in governance.LEGAL_LINKS.items():
        assert url.startswith("https://lttstudios.com/"), name

    source = inspect.getsource(governance)
    for word in ("chúng tôi cam kết", "điều khoản sử dụng", "quyền của bạn"):
        assert word not in source.lower(), (
            f"governance.py appears to restate legal text ({word!r}); link to "
            f"the approved page instead")


# ── What a customer can see and take ─────────────────────────────────────────

def test_the_privacy_page_is_built_from_the_policy_not_written_by_hand(portal):
    """A privacy page that describes a rule nobody runs is the worst kind of
    wrong: it is a promise, in writing, that the code does not keep."""
    _account(portal)
    page = portal.get("/developers/privacy").text
    assert page.count("<code>") >= 20, "the table should list every store"
    for store in governance.by_class(governance.EVIDENCE):
        assert store.table in page, store.table
    assert "governance.py" in page


def test_the_privacy_page_links_legal_text_rather_than_restating_it(portal):
    _account(portal)
    page = portal.get("/developers/privacy").text
    for url in governance.LEGAL_LINKS.values():
        assert url in page


def test_a_customer_can_export_the_api_data_held_about_them(portal):
    import json

    user_id, token = _account(portal)
    _run_one_call(portal, token)

    answer = portal.get("/developers/privacy/export")
    assert answer.status_code == 200
    assert "attachment" in answer.headers.get("content-disposition", "")
    body = json.loads(answer.content)

    assert body["account"]["id"] == user_id
    # Lists, not the word "[redacted]". An earlier redactor matched the
    # substring `api_key` and swallowed the customer's whole key list — the most
    # useful part of their own export. Only visible by reading the output.
    assert isinstance(body["api_keys"], list) and body["api_keys"]
    assert body["api_keys"][0]["key_id"]
    assert isinstance(body["jobs"], list) and body["jobs"]
    assert isinstance(body["credit_entries"], list) and body["credit_entries"]
    # …and it says what it does NOT cover, rather than implying it covers all.
    assert "KHÔNG bao gồm" in body["scope"]


def test_redaction_hides_secret_values_without_hiding_public_ones(portal):
    """The line the redactor has to draw.

    A key *id* is public by design — it is what a support conversation refers
    to. The stored digest is not. Blurring the two made the export useless while
    protecting nothing that was not already unstored.
    """
    from platform_core.public_api import support

    clean = support.redact({
        "api_keys": [{"key_id": "abc123", "name": "production"}],
        "verifier_digest": "d", "webhook_secret_enc": "s",
        "authorization": "Bearer x", "pepper_version": 1})
    assert clean["api_keys"][0]["key_id"] == "abc123"
    assert clean["api_keys"][0]["name"] == "production"
    for field in ("verifier_digest", "webhook_secret_enc", "authorization"):
        assert clean[field] == support.REDACTED, field


def test_the_export_carries_no_secret(portal):
    """Same redaction the support trace uses: one definition of what must never
    leave, applied in both directions."""
    user_id, token = _account(portal)
    created = portal.post(f"{API_V1_PREFIX}/webhooks", json={"url": RECEIVER},
                          headers={"Authorization": f"Bearer {token}"})
    hook_secret = created.json()["secret"]
    key_secret = token.split("_", 3)[-1]
    _run_one_call(portal, token)

    blob = portal.get("/developers/privacy/export").text
    assert key_secret not in blob
    assert hook_secret not in blob
    assert token not in blob


def test_the_export_belongs_to_the_signed_in_account_only(portal):
    """Two accounts, one export: it must contain exactly one of them."""
    import json

    first_id, first_token = _account(portal)
    _run_one_call(portal, first_token)
    second_id, _second_token = _account(portal)      # signs in as the second

    body = json.loads(portal.get("/developers/privacy/export").content)
    assert body["account"]["id"] == second_id
    assert first_id not in json.dumps(body)


def test_an_anonymous_visitor_cannot_export_anything(portal):
    portal.cookies.clear()
    answer = portal.get("/developers/privacy/export", follow_redirects=False)
    assert answer.status_code in (302, 303, 307)
