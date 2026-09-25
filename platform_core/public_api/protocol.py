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

#: Answered inside the request, but it **costs money**. Q106, 2026-08-23.
#:
#: This mode exists because ``ltt_llm`` produced an operation the first two modes
#: genuinely could not describe. A chat completion is chargeable and calls a GPU,
#: so it is not SYNC; it finishes in tens of seconds and the caller wants the
#: answer in the response, so forcing it into ASYNC_JOB would mean every customer
#: writes a polling loop before their first "hello" comes back.
#:
#: The line we are NOT crossing: this mode still refuses to enqueue. Anything
#: that cannot finish inside :data:`SYNC_BILLED_MAX_SECONDS` is an async job that
#: has not admitted it yet — the same sentence SYNC has always carried, with a
#: bigger number and a price attached.
SYNC_BILLED = "SYNC_BILLED"

#: Incremental output over one connection. **Opened 2026-08-23 (Q107).**
#:
#: It was reserved until then for a reason that no longer covers every case: D5
#: said the only streaming capability the platform had ran through a
#: consumer-account sidecar, and reselling that is a different class of risk from
#: a customer using it themselves. That still holds for ``chataistudio``. It does
#: **not** hold for ``ltt_llm`` — our own model, our own hardware, nobody's
#: account in the middle.
#:
#: What forced it open: every CLI worth serving requires streaming. Claude Code
#: aborts a stream that goes silent, Claude Desktop refuses a gateway that
#: buffers, and Codex times out on an idle stream. A non-streaming door is a door
#: none of them walk through.
#:
#: What it buys beyond compatibility: **streaming escapes the 125-second
#: ceiling**. Cloudflare's clock measures the wait for the *first byte*, so a
#: stream that keeps sending has no wall — which is why SYNC_BILLED must cap
#: ``max_tokens`` and this mode need not.
STREAM = "STREAM"

#: One request carrying many child operations. Reserved; no operation uses it.
BATCH = "BATCH"

#: Declared so the answer is on the record, and enforced by the catalog.
NOT_PUBLIC = "NOT_PUBLIC"

EXECUTION_MODES = (ASYNC_JOB, SYNC, SYNC_BILLED, STREAM, BATCH, NOT_PUBLIC)

#: Modes a *tool* may declare. A tool that is not public simply is not in the
#: catalog, so ``NOT_PUBLIC`` is a route-level answer, not a tool-level one.
TOOL_MODES = (ASYNC_JOB, SYNC, SYNC_BILLED, STREAM, BATCH)

#: Modes with an operation behind them today. The gap between this and
#: ``EXECUTION_MODES`` is deliberate and tested: a mode may be specified before
#: anything uses it, but it may not quietly acquire a user without the
#: certification its rules demand.
MODES_IN_USE = (ASYNC_JOB, SYNC, SYNC_BILLED, STREAM)


class ProtocolError(Exception):
    """A declaration that contradicts the mode it claims."""


# ── What each mode promises ──────────────────────────────────────────────────

#: A SYNC operation must finish inside this budget. It is deliberately far below
#: the Cloudflare 125-second ceiling: an operation that needs *most* of a
#: request's lifetime is an async job that has not admitted it yet.
SYNC_MAX_SECONDS = 5

#: The largest response a SYNC operation may produce. Larger output belongs in
#: an artifact, which is what the async path already produces.
SYNC_MAX_RESPONSE_BYTES = 1 * 1024 * 1024

#: What a STREAM contract must spell out in ``extra`` before it may exist.
#:
#: These are the mode's promises turned into declared data. A promise nobody is
#: forced to write down is a promise that lives in the route author's head, which
#: is exactly the failure EXT-02 was written against.
STREAM_PHAI_KHAI = (
    #: The SSE event names this operation emits, so a client — and the docs —
    #: can be written against a list rather than against observation.
    "event_types",
    #: Seconds between keep-alives during a silent gap. Without it a long prefill
    #: reads as a dead connection: Claude Code aborts after 300s of silence and
    #: Codex's `stream_idle_timeout_ms` defaults to the same.
    "heartbeat_seconds",
    #: The event that carries the credit ACTUALLY charged. Not the hold — the
    #: bill. A caller must be able to read what it paid from the stream itself.
    "usage_event",
    #: Whether abandoning the connection stops the work. `False` means a customer
    #: who hits Ctrl-C keeps paying for tokens nobody will read.
    "cancel_on_disconnect",
)

#: A SYNC_BILLED operation must finish inside this budget.
#:
#: 🔴 90 IS NOT A ROUND NUMBER, IT IS A CEILING MINUS A MARGIN. Cloudflare's
#:    default Proxy Read Timeout is **125 seconds** (verified 2026-08-27). The
#:    caller otherwise sees a 524 with no way to tell "it failed" from "it worked
#:    and you were disconnected". The 35-second margin covers TLS, tunnel
#:    variance and settlement; admission separately budgets model load/prefill.
#:
#: ⛔ RAISING THIS NUMBER DOES NOT BUY TIME — it only moves where the failure
#:    happens, from our clean 400 to Cloudflare's opaque 524. The way to serve a
#:    longer call is ASYNC_JOB, not a bigger constant.
SYNC_BILLED_MAX_SECONDS = 90

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
    SYNC_BILLED: (
        f"Answered in the request, and chargeable. Must require an "
        f"Idempotency-Key; must hold credit before touching a provider and "
        f"settle from measured usage exactly once; must not enqueue a job; must "
        f"finish within {SYNC_BILLED_MAX_SECONDS}s and return at most "
        f"{SYNC_MAX_RESPONSE_BYTES // 1024}KiB. No quote: the price is not "
        f"knowable before the work runs, so the hold is a ceiling and the "
        f"settlement is the truth."),
    STREAM: (
        "Server-Sent Events over the same authenticated surface. Must declare "
        "its event types, a heartbeat interval, the event carrying the credit "
        "actually charged, and cancel-on-disconnect. Chargeable streams settle "
        "from measured usage, never from the hold. No quote: the price is not "
        "knowable before the work runs. No Idempotency-Key is required (Q107) "
        "because no CLI sends one and this mode offers no resume; an operation "
        "that ever adds resume must require the key again."),
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
    if mode == STREAM:
        # 🔴 BỐN LỜI HỨA CỦA `STREAM` PHẢI ĐƯỢC **KHAI**, KHÔNG PHẢI ĐƯỢC TIN.
        #
        #    Đây là cả triết lý của file này: *"the mode is declared, not
        #    inferred, and the declaration is checked"*. Một chế độ có bốn lời
        #    hứa mà không chỗ nào bắt khai chúng thì bốn lời hứa đó sống trong
        #    đầu người viết route — đúng thứ EXT-02 sinh ra để chống.
        thieu = [ten for ten in STREAM_PHAI_KHAI if ten not in (contract.extra or {})]
        if thieu:
            raise ProtocolError(
                f"{contract.name}: a STREAM operation must declare "
                f"{', '.join(thieu)} in `extra`; the mode promises these and "
                f"the promise is only real when it is written down")
        if contract.requires_quote:
            # Cùng lý do như SYNC_BILLED: quote là giá ký TRƯỚC khi chạy, mà giá
            # token không biết trước được.
            raise ProtocolError(
                f"{contract.name}: STREAM cannot require a quote — the price "
                f"depends on output that does not exist yet")
        if contract.chargeable and not contract.extra.get("settles_from_measured_usage"):
            # 🔴 CHỖ TIỀN RÒ. Một luồng bị cắt giữa chừng vẫn đã đốt GPU. Không
            #    khai rằng mình quyết toán theo SỐ ĐÃ ĐO thì mặc định rơi về
            #    "thu trọn phần đã giữ" — đúng lỗi tiền im lặng đã tìm ra ở cửa
            #    job hôm 23/08.
            raise ProtocolError(
                f"{contract.name}: a chargeable STREAM must declare "
                f"settles_from_measured_usage — a stream cut short still burned "
                f"GPU, and charging the held ceiling for it is a silent overcharge")
        if contract.extra.get("resumable") and not contract.requires_idempotency_key:
            # Q107 bỏ đòi khoá idempotency vì KHÔNG CLI NÀO GỬI NÓ và ta KHÔNG
            # tiếp nối luồng. Ngày nào có tiếp nối thì đòi hỏi đó sống lại ngay:
            # tiếp nối mà không có khoá là mời một lượt bị thu hai lần.
            raise ProtocolError(
                f"{contract.name}: a resumable STREAM must require an "
                f"Idempotency-Key — resume without one bills the same work twice")
    if mode == SYNC_BILLED:
        if not contract.chargeable:
            # A free operation answered in the request is plain SYNC, and SYNC
            # carries stricter promises (no provider, no GPU, 5s). Letting a free
            # call sit here would quietly buy it a 90-second budget it never
            # justified.
            raise ProtocolError(
                f"{contract.name}: SYNC_BILLED is for chargeable work; a free "
                f"in-request operation is SYNC")
        if not contract.requires_idempotency_key:
            # 🔴 THE WHOLE REASON THIS MODE IS ALLOWED TO EXIST WITHOUT A QUOTE.
            #    ASYNC_JOB is safe to retry because the quote pins a price and the
            #    key pins an identity. Here there is no quote, so the key is the
            #    only thing standing between a network retry and paying twice for
            #    the same generation.
            raise ProtocolError(
                f"{contract.name}: a chargeable SYNC_BILLED must require an "
                f"Idempotency-Key — without a quote it is the only thing that "
                f"stops a retry from buying the work twice")
        if contract.requires_quote:
            # Not a style rule. A quote is a signed price agreed BEFORE the work,
            # and token cost is not knowable before the work. Demanding one would
            # force us to sign a number we cannot honour.
            raise ProtocolError(
                f"{contract.name}: SYNC_BILLED cannot require a quote — the "
                f"price depends on output that does not exist yet")
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
HEADER_MAX_BODY_BYTES = "X-LTT-Max-Body-Bytes"

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
