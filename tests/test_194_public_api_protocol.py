"""EXT-02 — the protocol contract: execution modes, headers, error registry.

The failures this file is written against are all the same shape: a rule that
exists in somebody's head instead of in a declaration. A tool that is
"obviously" asynchronous, a correlation id that is "obviously" on every
response, a 409 that "obviously" means out-of-credit. Each of those was true
until it quietly was not.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from platform_core.models import Job
from platform_core.public_api import errors as E, keys as devkeys, limits, protocol
from platform_core.public_api.error_registry import (REGISTRY, RETRY_AFTER_DELAY,
                                                     RETRY_CLASSES, RETRY_MATRIX,
                                                     is_retryable, spec_for)
from platform_core.public_api.protocol import (ASYNC_JOB, BATCH,
                                               EXECUTION_MODES, MODES_IN_USE,
                                               NOT_PUBLIC, STREAM, SYNC,
                                               ProtocolError,
                                               PublicOperationContract,
                                               check_mode_rules)
from platform_core.public_api.scopes import (SCOPE_JOBS_CANCEL,
                                             SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
                                             SCOPE_TOOLS_READ, SCOPE_USAGE_READ)
from platform_core.registry import (AppManifest, LoadedApp, RegistryError,
                                    ToolSpec)
from server.api.inventory import API_V1_PREFIX, API_V1_ROUTES

PEPPER = "protocol-test-pepper-" + "p" * 40
TOOL = "text.protocol"
ALL_SCOPES = (SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
              SCOPE_JOBS_CANCEL, SCOPE_USAGE_READ)


def _cost(params: dict) -> int:
    return 5


def _manifest(**contract_extra):
    tool = ToolSpec(
        name=TOOL, job_type="sampleproto.generate", description="Fixture tool.",
        params_schema={"prompt": {"type": "string", "required": True,
                                  "max_length": 100}},
        returns={"text": "text"}, api_exposed=True,
        api_contract={"scopes": (SCOPE_JOBS_CREATE,), **contract_extra})
    return AppManifest(
        slug="sampleproto", display_name="Sample", route_prefix="/sampleproto",
        job_types=("sampleproto.generate",), credit_cost=_cost,
        lifecycle="released", surface="customer", tools=(tool,))


def _fixture_apps():
    return [LoadedApp(manifest=_manifest(), router=None, error="")]


@pytest.fixture()
def api(tmp_path, monkeypatch):
    import platform_core.registry as registry_mod
    monkeypatch.setattr(registry_mod, "discover", _fixture_apps)
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'protocol.db').as_posix()}")
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
        "LTT_SESSION_SECRET": "protocol-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": TOOL,
        "LTT_PUBLIC_API_RPM": "30",
    })
    with TestClient(app) as client:
        yield client
    from server.api import deps
    deps.set_principal_resolver(None)
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


def _account(credits: int = 1000):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=f"p-{uuid.uuid4().hex[:8]}@example.com",
                              password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, user.id, credits, by="test")
        _key, token = devkeys.issue(db, user_id=user.id, scopes=ALL_SCOPES,
                                    env={devkeys.PEPPER_ENV: PEPPER})
        db.commit()
        return user.id, token
    finally:
        _close(gen)


def _auth(token: str, idem: str = "") -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if idem:
        headers["Idempotency-Key"] = idem
    return headers


def _job_count() -> int:
    import sqlalchemy as sa

    gen, db = _session()
    try:
        return int(db.execute(sa.select(sa.func.count(Job.id))).scalar_one())
    finally:
        _close(gen)


# ── Execution modes: declared, not inferred ──────────────────────────────────

def test_every_route_declares_a_mode_the_platform_can_honour():
    for route in API_V1_ROUTES:
        assert route.execution_mode in EXECUTION_MODES, route.path
        # A route may not declare a mode that has a specification but no
        # implementation: STREAM and BATCH are written down (§1.1 of
        # PROTOCOL_V1.md) precisely so the first user has rules to follow, and
        # letting a route claim one before then is how the rules get skipped.
        assert route.execution_mode in MODES_IN_USE, route.path


def test_exactly_one_route_is_chargeable_and_it_is_the_async_one():
    async_routes = [f"{r.method} {r.path}" for r in API_V1_ROUTES
                    if r.execution_mode == ASYNC_JOB]
    assert async_routes == [f"POST {API_V1_PREFIX}/jobs"]


def test_no_sync_route_creates_a_job(api):
    """The SYNC promise, checked against behaviour rather than intent."""
    _user_id, token = _account()
    before = _job_count()
    for route in API_V1_ROUTES:
        if route.execution_mode != SYNC or route.method != "GET":
            continue
        if "{" in route.path:                    # needs an id we do not have
            continue
        api.get(route.path, headers=_auth(token))
    assert _job_count() == before


def test_every_published_tool_declares_a_mode():
    from platform_core.public_api.catalog import build_catalog
    from platform_core.public_api.config import load_public_api_config
    from platform_core.registry import discover

    everything = ",".join(sorted({
        tool.name for item in discover() if not item.error
        for tool in item.manifest.tools}))
    catalog = build_catalog(load_public_api_config(
        {"LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": everything}))
    assert catalog, "the repository publishes at least one tool"
    for tool in catalog:
        assert tool.execution_mode in MODES_IN_USE, tool.name
        assert tool.to_public_dict()["execution_mode"] == tool.execution_mode


def test_the_catalog_publishes_the_mode_to_callers(api):
    _user_id, token = _account()
    body = api.get(f"{API_V1_PREFIX}/tools", headers=_auth(token)).json()
    assert body["items"][0]["execution_mode"] == ASYNC_JOB
    one = api.get(f"{API_V1_PREFIX}/tools/{TOOL}",
                  headers=_auth(token)).json()
    assert one["execution_mode"] == ASYNC_JOB


def test_capabilities_advertises_only_modes_that_work(api):
    body = api.get(f"{API_V1_PREFIX}/capabilities").json()
    assert body["execution_modes"] == list(MODES_IN_USE)
    # STREAM da MO 2026-08-23 (Q107): moi CLI dang phuc vu deu bat buoc streaming,
    # nen mot cua khong-streaming la cua khong ai di qua.
    assert STREAM in body["execution_modes"]
    # BATCH van la dac ta khong nguoi dung — va do la chu y: mot che do duoc phep
    # viet ra truoc khi co ai dung, nhung khong duoc lang le co nguoi dung.
    assert BATCH not in body["execution_modes"]


@pytest.mark.parametrize("mode", [BATCH])
def test_a_manifest_cannot_opt_into_an_unimplemented_mode(mode):
    """STREAM da roi khoi danh sach nay 2026-08-23 khi Q107 mo no.

    BATCH o lai mot minh, va no van dang gac dung mot cai: khoang cach giua
    `EXECUTION_MODES` va `MODES_IN_USE` la co chu y."""
    from platform_core.registry import _validate_api_contract

    manifest = _manifest(execution_mode=mode)
    with pytest.raises(RegistryError) as raised:
        _validate_api_contract(manifest, manifest.tools[0])
    assert mode in str(raised.value)


def test_a_manifest_cannot_invent_a_mode():
    from platform_core.registry import _validate_api_contract

    manifest = _manifest(execution_mode="FIRE_AND_FORGET")
    with pytest.raises(RegistryError):
        _validate_api_contract(manifest, manifest.tools[0])


# ── The mode rules themselves ────────────────────────────────────────────────

def test_a_chargeable_async_operation_must_require_a_quote_and_a_key():
    with pytest.raises(ProtocolError):
        PublicOperationContract(name="x.pay", execution_mode=ASYNC_JOB,
                                chargeable=True, requires_quote=True)
    with pytest.raises(ProtocolError):
        PublicOperationContract(name="x.pay", execution_mode=ASYNC_JOB,
                                chargeable=True,
                                requires_idempotency_key=True)
    ok = PublicOperationContract(name="x.pay", execution_mode=ASYNC_JOB,
                                 chargeable=True, requires_quote=True,
                                 requires_idempotency_key=True)
    assert ok.execution_mode == ASYNC_JOB


def test_a_sync_operation_may_not_charge():
    with pytest.raises(ProtocolError):
        PublicOperationContract(name="x.cheap", execution_mode=SYNC,
                                chargeable=True)


def test_a_sunset_without_a_deprecation_date_is_refused():
    with pytest.raises(ProtocolError):
        PublicOperationContract(name="x.old", execution_mode=SYNC,
                                sunset_on="Wed, 01 Jan 2027 00:00:00 GMT")


def test_not_public_operations_carry_no_scopes():
    with pytest.raises(ProtocolError):
        check_mode_rules(PublicOperationContract(
            name="x.internal", execution_mode=NOT_PUBLIC,
            scopes=(SCOPE_JOBS_READ,)))


# ── The error registry ───────────────────────────────────────────────────────

def test_every_code_in_the_codebase_is_registered():
    """A code without an entry is a code with no documented retry behaviour."""
    declared = {value for name, value in vars(E).items()
                if name.startswith("CODE_") and isinstance(value, str)}
    missing = sorted(declared - set(REGISTRY))
    assert not missing, f"unregistered error codes: {missing}"


def test_registry_entries_are_well_formed():
    for code, spec in REGISTRY.items():
        assert spec.code == code
        assert 400 <= spec.status <= 599
        assert spec.retry in RETRY_CLASSES
        assert spec.action.strip(), code
        if spec.reuse_idempotency_key:
            # Reusing a key only makes sense where retrying is on the table.
            assert is_retryable(code), code


def test_the_registry_status_matches_what_the_helper_actually_raises():
    raised = {
        E.CODE_INVALID_REQUEST: E.invalid_request(),
        E.CODE_UNAUTHORIZED: E.unauthorized(),
        E.CODE_FORBIDDEN: E.forbidden(),
        E.CODE_NOT_FOUND: E.not_found(),
        E.CODE_CONFLICT: E.conflict(),
        E.CODE_PAYLOAD_TOO_LARGE: E.payload_too_large(),
        E.CODE_RATE_LIMITED: E.rate_limited(),
        E.CODE_READ_ONLY: E.read_only(),
        E.CODE_MISSING_SCOPE: E.missing_scope(),
        E.CODE_TOOL_NOT_ALLOWED: E.tool_not_allowed(),
        E.CODE_INSUFFICIENT_CREDIT: E.insufficient_credit(),
        E.CODE_PRICE_CHANGED: E.price_changed(),
        E.CODE_IDEMPOTENCY_CONFLICT: E.idempotency_conflict(),
        E.CODE_IDEMPOTENCY_IN_PROGRESS: E.idempotency_in_progress(),
        E.CODE_QUOTE_EXPIRED: E.quote_expired(),
        E.CODE_QUOTE_INVALID: E.quote_invalid(),
    }
    for code, error in raised.items():
        assert error.code == code
        assert error.status == spec_for(code).status, code


def test_credential_failures_are_not_split_into_separate_codes():
    """The one place EXT-02 deliberately refuses to be more specific.

    Separate codes for "unknown key id" and "wrong secret" would turn the
    endpoint into an oracle for enumerating key ids. `test_192` proves the
    behaviour; this proves nobody added the codes back through the registry.
    """
    forbidden_codes = {"invalid_api_key", "key_expired", "key_revoked",
                       "unknown_key"}
    assert not forbidden_codes & set(REGISTRY)
    assert spec_for(E.CODE_UNAUTHORIZED).status == 401


def test_the_sdks_retry_exactly_what_the_registry_says_is_retryable():
    """The SDKs cannot import this registry — they ship as one standalone file
    to customers — so the two are kept honest by a test instead of by code."""
    import re
    from pathlib import Path

    registry_retryable = {spec.status for spec in REGISTRY.values()
                          if is_retryable(spec.code)}
    root = Path(__file__).resolve().parent.parent
    for path, pattern in (
            (root / "sdk" / "python" / "ltt_public_api.py",
             r"RETRY_STATUSES = frozenset\(\{([^}]*)\}\)"),
            (root / "sdk" / "typescript" / "ltt-public-api.ts",
             r"RETRY_STATUSES = new Set\(\[([^\]]*)\]\)")):
        match = re.search(pattern, path.read_text(encoding="utf-8"))
        assert match, f"cannot find the retry set in {path.name}"
        statuses = {int(bit) for bit in re.findall(r"\d+", match.group(1))}
        # Gateway statuses (502/504) come from infrastructure in front of the
        # app, so they are never in a registry the app itself writes.
        assert statuses - {502, 504} <= registry_retryable, path.name
        assert 400 not in statuses and 409 not in statuses, (
            f"{path.name} must not blind-retry a 409: two of the three are "
            f"only retryable after the caller fixes something")


def test_the_retry_matrix_covers_the_dangerous_case():
    entries = {label: (retry, note) for label, retry, note in RETRY_MATRIX}
    network = next(key for key in entries if "network" in key)
    retry, note = entries[network]
    assert retry == RETRY_AFTER_DELAY
    assert "Idempotency-Key" in note


# ── Headers ──────────────────────────────────────────────────────────────────

def test_every_response_carries_the_correlation_id_and_version(api):
    _user_id, token = _account()
    ok = api.get(f"{API_V1_PREFIX}/tools", headers=_auth(token))
    assert ok.status_code == 200
    assert ok.headers[protocol.HEADER_CORRELATION_ID]
    assert ok.headers[protocol.HEADER_API_VERSION] == protocol.API_VERSION

    # Anonymous, and a failure: both still traceable.
    anon = api.get(f"{API_V1_PREFIX}/health")
    assert anon.headers[protocol.HEADER_CORRELATION_ID]
    denied = api.get(f"{API_V1_PREFIX}/tools")
    assert denied.status_code == 401
    assert denied.headers[protocol.HEADER_CORRELATION_ID]


def test_the_header_id_is_the_same_id_the_problem_body_carries(api):
    denied = api.get(f"{API_V1_PREFIX}/jobs/does-not-exist",
                     headers=_auth(_account()[1]))
    assert denied.status_code == 404
    assert (denied.headers[protocol.HEADER_CORRELATION_ID]
            == denied.json()["request_id"])


def test_a_caller_cannot_choose_its_own_correlation_id(api):
    """The id is minted here, never accepted from the caller.

    Echoing a caller-supplied value would be friendly for distributed tracing
    and would also let anyone write whatever they like into the platform's log
    lines, and let two callers claim the same id — which is precisely the
    property support relies on to be unique.
    """
    given = "trace-" + uuid.uuid4().hex
    response = api.get(f"{API_V1_PREFIX}/health",
                       headers={protocol.HEADER_CORRELATION_ID: given})
    assert response.headers[protocol.HEADER_CORRELATION_ID] != given


def test_rate_limiting_answers_with_a_retry_after_header(api):
    _user_id, token = _account()
    last = None
    for _ in range(40):                      # LTT_PUBLIC_API_RPM is 30 here
        last = api.get(f"{API_V1_PREFIX}/tools", headers=_auth(token))
        if last.status_code == 429:
            break
    assert last.status_code == 429
    body = last.json()
    assert body["code"] in (E.CODE_RATE_LIMITED, E.CODE_CONCURRENCY_LIMITED)
    # The number was already in the body for the platform's own SDKs; the
    # header is what every other HTTP client in the world reads.
    assert last.headers[protocol.HEADER_RETRY_AFTER] == str(body["retry_after"])
    assert is_retryable(body["code"])


def test_creating_a_job_returns_its_address(api):
    _user_id, token = _account()
    quote = api.post(f"{API_V1_PREFIX}/quotes",
                     json={"tool": TOOL, "input": {"prompt": "hi"}},
                     headers=_auth(token)).json()
    created = api.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quote["quote"], "input": {"prompt": "hi"}},
        headers=_auth(token, "protocol-location-key-1"))
    assert created.status_code == 201
    location = created.headers["Location"]
    assert location == f"{API_V1_PREFIX}/jobs/{created.json()['id']}"
    assert api.get(location, headers=_auth(token)).status_code == 200


def test_a_deprecated_route_announces_itself(api, monkeypatch):
    """Nothing is deprecated yet, so the hook is proved with a stand-in.

    A deprecation mechanism that has never run once is a mechanism that will be
    discovered to be broken on the day it matters most.
    """
    import server.api.inventory as inventory
    from dataclasses import replace

    patched = tuple(
        replace(route, deprecated_on="Wed, 01 Jan 2031 00:00:00 GMT",
                sunset_on="Fri, 01 Aug 2031 00:00:00 GMT")
        if route.path.endswith("/health") else route
        for route in inventory.API_V1_ROUTES)
    monkeypatch.setattr(inventory, "API_V1_ROUTES", patched)

    response = api.get(f"{API_V1_PREFIX}/health")
    assert response.headers[protocol.HEADER_DEPRECATION].endswith("2031 00:00:00 GMT")
    assert response.headers[protocol.HEADER_SUNSET].startswith("Fri, 01 Aug")
    # An undeprecated route says nothing, rather than saying "not deprecated".
    other = api.get(f"{API_V1_PREFIX}/capabilities")
    assert protocol.HEADER_DEPRECATION not in other.headers


# ── The three 409s a caller must be able to tell apart ───────────────────────

def test_out_of_credit_is_its_own_code_with_the_numbers_to_act_on(api):
    _user_id, token = _account(credits=1)
    quote = api.post(f"{API_V1_PREFIX}/quotes",
                     json={"tool": TOOL, "input": {"prompt": "hi"}},
                     headers=_auth(token)).json()
    refused = api.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quote["quote"], "input": {"prompt": "hi"}},
        headers=_auth(token, "protocol-broke-key-1"))
    assert refused.status_code == 409
    body = refused.json()
    assert body["code"] == E.CODE_INSUFFICIENT_CREDIT
    assert body["required_credit"] == 5 and body["balance"] == 1
    assert spec_for(body["code"]).reuse_idempotency_key is True


def test_an_expired_quote_says_so_rather_than_just_invalid(api, monkeypatch):
    import platform_core.public_api.quotes as quotes_mod

    _user_id, token = _account()
    quote = api.post(f"{API_V1_PREFIX}/quotes",
                     json={"tool": TOOL, "input": {"prompt": "hi"}},
                     headers=_auth(token)).json()
    monkeypatch.setattr(quotes_mod, "QUOTE_TTL_S", -1)
    stale = api.post(
        f"{API_V1_PREFIX}/jobs",
        json={"tool": TOOL, "quote": quote["quote"], "input": {"prompt": "hi"}},
        headers=_auth(token, "protocol-stale-key-1"))
    assert stale.status_code == 400
    assert stale.json()["code"] == E.CODE_QUOTE_EXPIRED
    # Expired is fixable by re-quoting; a tampered one never is.
    assert spec_for(E.CODE_QUOTE_EXPIRED).retry != spec_for(
        E.CODE_QUOTE_INVALID).retry


def test_a_key_reused_with_a_different_body_is_told_to_stop_not_to_wait(api):
    _user_id, token = _account()

    def _quote(prompt: str):
        return api.post(f"{API_V1_PREFIX}/quotes",
                        json={"tool": TOOL, "input": {"prompt": prompt}},
                        headers=_auth(token)).json()

    key = "protocol-one-key-two-bodies"
    first = _quote("one")
    assert api.post(f"{API_V1_PREFIX}/jobs",
                    json={"tool": TOOL, "quote": first["quote"],
                          "input": {"prompt": "one"}},
                    headers=_auth(token, key)).status_code == 201
    second = _quote("two")
    clash = api.post(f"{API_V1_PREFIX}/jobs",
                     json={"tool": TOOL, "quote": second["quote"],
                           "input": {"prompt": "two"}},
                     headers=_auth(token, key))
    assert clash.status_code == 409
    assert clash.json()["code"] == E.CODE_IDEMPOTENCY_CONFLICT
    assert is_retryable(E.CODE_IDEMPOTENCY_CONFLICT) is False
    # …while the in-progress case with the *same* body is worth waiting for.
    assert is_retryable(E.CODE_IDEMPOTENCY_IN_PROGRESS) is True


def test_a_missing_scope_names_the_scope(api):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=f"n-{uuid.uuid4().hex[:8]}@example.com",
                              password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, user.id, 100, by="test")
        _key, token = devkeys.issue(db, user_id=user.id,
                                    scopes=(SCOPE_JOBS_READ,),
                                    env={devkeys.PEPPER_ENV: PEPPER})
        db.commit()
    finally:
        _close(gen)

    denied = api.get(f"{API_V1_PREFIX}/tools", headers=_auth(token))
    assert denied.status_code == 403
    body = denied.json()
    assert body["code"] == E.CODE_MISSING_SCOPE
    assert body["required_scope"] == SCOPE_TOOLS_READ


# ── STREAM: bốn lời hứa phải được KHAI, không phải được tin (Q107) ──────────
#
# ⭐ Đây là triết lý của `protocol.py` áp cho chế độ mới nhất: *"the mode is
#    declared, not inferred, and the declaration is checked"*. Một chế độ có bốn
#    lời hứa mà không chỗ nào bắt khai chúng thì bốn lời hứa đó sống trong đầu
#    người viết route — đúng thứ EXT-02 sinh ra để chống.

def _stream_extra(**ghi_de):
    d = {"event_types": ("message_start", "content_block_delta", "message_stop"),
         "heartbeat_seconds": 15,
         "usage_event": "message_delta",
         "cancel_on_disconnect": True,
         "settles_from_measured_usage": True}
    d.update(ghi_de)
    return d


def test_stream_khai_du_thi_hop_le():
    from platform_core.public_api.protocol import STREAM

    c = PublicOperationContract(name="chat.stream", execution_mode=STREAM,
                                chargeable=True, extra=_stream_extra())
    assert c.execution_mode == STREAM


@pytest.mark.parametrize("thieu", ["event_types", "heartbeat_seconds",
                                   "usage_event", "cancel_on_disconnect"])
def test_stream_thieu_mot_loi_hua_thi_BI_CHAN(thieu):
    from platform_core.public_api.protocol import STREAM

    extra = _stream_extra()
    extra.pop(thieu)
    with pytest.raises(ProtocolError) as e:
        PublicOperationContract(name="chat.stream", execution_mode=STREAM,
                                chargeable=True, extra=extra)
    assert thieu in str(e.value)


def test_stream_co_thu_tien_phai_khai_QUYET_TOAN_THEO_SO_DO():
    """🔴 Chỗ tiền rò. Một luồng bị cắt giữa chừng vẫn đã đốt GPU; không khai
    rằng mình quyết toán theo số ĐÃ ĐO thì mặc định rơi về "thu trọn phần đã
    giữ" — đúng lỗi tiền im lặng đã tìm ra ở cửa job hôm 23/08."""
    from platform_core.public_api.protocol import STREAM

    with pytest.raises(ProtocolError) as e:
        PublicOperationContract(name="chat.stream", execution_mode=STREAM,
                                chargeable=True,
                                extra=_stream_extra(settles_from_measured_usage=None))
    assert "measured" in str(e.value)


def test_stream_KHONG_duoc_doi_quote():
    """Giá token không biết trước được, nên không ký trước được."""
    from platform_core.public_api.protocol import STREAM

    with pytest.raises(ProtocolError):
        PublicOperationContract(name="chat.stream", execution_mode=STREAM,
                                chargeable=True, requires_quote=True,
                                extra=_stream_extra())


def test_stream_KHONG_doi_idempotency_key():
    """⭐ Q107, và nó là cả lý do chế độ này dùng được.

    Đo thật 23/08: **không CLI nào gửi header đó** — Codex không, Claude Code
    không, SDK OpenAI tự sinh rồi vứt đi. Đòi nó = tính năng không tồn tại."""
    from platform_core.public_api.protocol import STREAM

    c = PublicOperationContract(name="chat.stream", execution_mode=STREAM,
                                chargeable=True, extra=_stream_extra())
    assert c.requires_idempotency_key is False


def test_TIEP_NOI_thi_doi_lai_khoa_ngay():
    """⛔ Q107 bỏ đòi khoá **vì ta không tiếp nối luồng**. Ngày nào có tiếp nối
    thì đòi hỏi đó sống lại: tiếp nối mà không có khoá là mời một lượt bị thu
    hai lần."""
    from platform_core.public_api.protocol import STREAM

    with pytest.raises(ProtocolError) as e:
        PublicOperationContract(name="chat.stream", execution_mode=STREAM,
                                chargeable=True, extra=_stream_extra(resumable=True))
    assert "resume" in str(e.value)


def test_route_STREAM_THAT_co_khai_hop_dong():
    """⭐ Hợp đồng chỉ có nghĩa khi bộ kiểm chạy trên ĐƯỜNG THẬT.

    Tới 23/08, `PublicOperationContract` chỉ được dựng trong test: một hợp đồng
    có bộ kiểm mà bộ kiểm không bao giờ chạy lúc phục vụ. `server/api/streaming.py`
    nay dựng nó **ở cấp module**, nên `check_mode_rules` chạy ngay khi nạp app —
    một bản sau lỡ bỏ mất một lời hứa của `STREAM` sẽ làm **app không khởi động
    được**, thay vì lặng lẽ phục vụ sai.
    """
    from platform_core.public_api.protocol import STREAM
    from server.api.streaming import HOP_DONG

    assert HOP_DONG.execution_mode == STREAM
    assert HOP_DONG.chargeable is True
    assert HOP_DONG.requires_idempotency_key is False       # Q107
    assert HOP_DONG.requires_quote is False
    for loi_hua in ("event_types", "heartbeat_seconds", "usage_event",
                    "cancel_on_disconnect", "settles_from_measured_usage"):
        assert HOP_DONG.extra.get(loi_hua), loi_hua
