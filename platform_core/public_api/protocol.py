"""The protocol standard for ``/api/v1``: execution modes and conventions.

EXT-02 exists because of a specific failure mode. V2 shipped five tools that all
happen to be asynchronous jobs, so "how does an operation execute" never had to
be written down — it was simply what the one implementation did. The moment a
sixth capability arrives that is cheap and synchronous, or that streams, or that
batches, the answer gets invented at the route, and then the docs, the SDK, the
playground and the client all learn a different answer.

So the mode is declared, not inferred, and the declaration is checked:

* every route in the inventory declares one (:mod:`server.api.inventory`);
* every published tool declares one (``api_contract["execution_mode"]``);
* :func:`check_mode_rules` refuses declarations that break the mode's own rules.

Nothing here talks HTTP. The rules are about what a mode *promises*, and the
promises are the same whether they are served by FastAPI or anything else.
"""
from __future__ import annotations

from dataclasses import dataclass, field

API_VERSION = "v1"

# ── Execution modes ──────────────────────────────────────────────────────────

#: Work that costs money and takes longer than a request should: a quote is
#: signed, credit is held, a row lands in ``jobs``, a worker runs it. This is
#: the default and, today, the only mode any tool uses.
ASYNC_JOB = "ASYNC_JOB"

#: Answered inside the request. Only for work that is bounded in time and size
#: and does not touch a provider, a GPU or the queue — reads, mostly.
SYNC = "SYNC"

#: Incremental output over one connection. Reserved and fully specified, but no
#: operation uses it (D5): the only streaming capability the platform has runs
#: through a consumer-account sidecar, and reselling that is a different class
#: of risk from a customer using it themselves.
STREAM = "STREAM"

#: One request carrying many child operations. Reserved; no operation uses it.
BATCH = "BATCH"

#: Declared so the answer is on the record, and enforced by the catalog.
NOT_PUBLIC = "NOT_PUBLIC"

EXECUTION_MODES = (ASYNC_JOB, SYNC, STREAM, BATCH, NOT_PUBLIC)

#: Modes a *tool* may declare. A tool that is not public simply is not in the
#: catalog, so ``NOT_PUBLIC`` is a route-level answer, not a tool-level one.
TOOL_MODES = (ASYNC_JOB, SYNC, STREAM, BATCH)

#: Modes with an operation behind them today. The gap between this and
#: ``EXECUTION_MODES`` is deliberate and tested: a mode may be specified before
#: anything uses it, but it may not quietly acquire a user without the
#: certification its rules demand.
MODES_IN_USE = (ASYNC_JOB, SYNC)


class ProtocolError(Exception):
    """A declaration that contradicts the mode it claims."""


# ── What each mode promises ──────────────────────────────────────────────────

#: A SYNC operation must finish inside this budget. It is deliberately far below
#: the Cloudflare 100-second ceiling: an operation that needs *most* of a
#: request's lifetime is an async job that has not admitted it yet.
SYNC_MAX_SECONDS = 5

#: The largest response a SYNC operation may produce. Larger output belongs in
#: an artifact, which is what the async path already produces.
SYNC_MAX_RESPONSE_BYTES = 1 * 1024 * 1024

MODE_RULES = {
    ASYNC_JOB: (
        "Chargeable. Requires a signed quote and an Idempotency-Key; holds "
        "credit and the job row in one transaction; answers 201 with a job id "
        "and a Location header; terminal states are succeeded/failed/cancelled; "
        "settlement happens exactly once."),
    SYNC: (
        f"Answered in the request. Must be free, must not enqueue a job, must "
        f"not call a provider or the GPU, must finish within "
        f"{SYNC_MAX_SECONDS}s and return at most "
        f"{SYNC_MAX_RESPONSE_BYTES // 1024}KiB."),
    STREAM: (
        "Server-Sent Events over the same authenticated surface. Requires: "
        "declared event types, a heartbeat, a final usage event carrying the "
        "credit actually charged, cancel-on-disconnect, and resume that cannot "
        "charge twice. No operation may declare this mode until those semantics "
        "have a test."),
    BATCH: (
        "One parent operation with child operations. Requires: a parent id and "
        "child ids, per-item validation before any credit moves, one quote "
        "covering the batch, partial success reported per child, cancellation "
        "of the remaining children, and one Idempotency-Key for the parent."),
    NOT_PUBLIC: "Not reachable from /api/v1 at all.",
}


@dataclass(frozen=True)
class PublicOperationContract:
    """What one public operation promises, independent of its transport.

    ``chargeable`` and ``idempotent`` are separate on purpose: a call can move
    money without being safe to repeat blindly (job creation), and a call can be
    safe to repeat without moving money (every read). The retry matrix in
    :mod:`platform_core.public_api.error_registry` is written against exactly
    this pair.
    """

    name: str
    execution_mode: str
    chargeable: bool = False
    requires_quote: bool = False
    requires_idempotency_key: bool = False
    scopes: tuple = ()
    #: Set once an operation is on its way out. Surfaces as RFC 8594 headers.
    deprecated_on: str = ""
    sunset_on: str = ""
    notes: str = ""
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        check_mode_rules(self)


def check_mode_rules(contract: PublicOperationContract) -> None:
    """Refuse a contract that does not keep the promises of its own mode."""
    mode = contract.execution_mode
    if mode not in EXECUTION_MODES:
        raise ProtocolError(
            f"{contract.name}: unknown execution_mode {mode!r}; "
            f"expected one of {', '.join(EXECUTION_MODES)}")
    if mode == ASYNC_JOB and contract.chargeable and not (
            contract.requires_quote and contract.requires_idempotency_key):
        # This is the invariant the whole surface rests on. A chargeable async
        # call without a quote has no agreed price, and without an idempotency
        # key a network retry buys the work twice.
        raise ProtocolError(
            f"{contract.name}: a chargeable ASYNC_JOB must require both a "
            f"quote and an Idempotency-Key")
    if mode == SYNC and contract.chargeable:
        raise ProtocolError(
            f"{contract.name}: SYNC operations must be free — anything worth "
            f"charging for is worth quoting and queueing")
    if mode == NOT_PUBLIC and contract.scopes:
        raise ProtocolError(
            f"{contract.name}: NOT_PUBLIC operations cannot carry scopes")
    if contract.sunset_on and not contract.deprecated_on:
        raise ProtocolError(
            f"{contract.name}: a sunset date without a deprecation date gives "
            f"callers no warning window")


def mode_of_tool(contract: dict) -> str:
    """The execution mode a published tool declares, defaulting to async.

    The default is not a shrug: every tool that exists today runs on a worker
    and charges credit, so a manifest that says nothing is saying ASYNC_JOB.
    Declaring anything else is an explicit act, and the registry validates it.
    """
    return str((contract or {}).get("execution_mode") or ASYNC_JOB)


# ── Conventions the whole surface follows ────────────────────────────────────

#: What public identifiers actually look like today — written down as observed,
#: not as wished for. They are opaque, non-sequential and stable for the life of
#: the resource; none carries a type prefix. Prefixes would read better in a
#: support ticket, but retrofitting them onto ids already handed out means
#: translating in both directions forever, and the only real benefit is
#: cosmetic. If they are ever introduced it is a v2 concern.
ID_SHAPES = {
    "job": "UUID4",
    "upload": "UUID4",
    "webhook": "UUID4",
    "delivery": "UUID4",
    "key_id": "random token, appears inside the key and in every log line",
    "artifact": "<job_id>.<output_field>.<index> — derived, not stored",
}

#: Header names. One place, so a route cannot invent a spelling.
HEADER_CORRELATION_ID = "X-Correlation-ID"
HEADER_API_VERSION = "X-LTT-API-Version"
HEADER_IDEMPOTENCY_KEY = "Idempotency-Key"
HEADER_RETRY_AFTER = "Retry-After"
HEADER_DEPRECATION = "Deprecation"
HEADER_SUNSET = "Sunset"

CONVENTIONS = {
    "content_type_request": "application/json (except upload content bodies)",
    "content_type_response": "application/json",
    "content_type_error": "application/problem+json",
    "timestamps": "ISO 8601, always UTC, always with an explicit offset (…Z)",
    "ids": "opaque strings with a resource prefix; never a database row number",
    "pagination": "limit/offset, limit<=100, offset<=100000, has_more flag",
    "sorting": "newest first; no client-chosen sort until a listing needs one",
    "filtering": "exact-match query parameters only (status, tool, key_id)",
    "correlation": f"{HEADER_CORRELATION_ID} on every response and in every "
                   f"problem document",
    "versioning": f"{HEADER_API_VERSION} on every response; breaking changes "
                  f"get a new path version, never a mutation of v1",
    "deprecation": f"{HEADER_DEPRECATION} and {HEADER_SUNSET} (RFC 8594) once "
                   f"an operation is scheduled for removal",
    "idempotency": f"{HEADER_IDEMPOTENCY_KEY} required on every chargeable "
                   f"mutation; same key + same body replays the first answer, "
                   f"same key + different body is a conflict",
}
