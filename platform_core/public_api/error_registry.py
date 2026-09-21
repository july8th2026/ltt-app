"""Every public error: its status, whether retrying helps, and what to do.

The failure this closes is not "the API lacks error codes" — V2 had twelve. It
is that three completely different problems all answered ``409 conflict``: you
are out of credit, the price moved since your quote, and you reused an
Idempotency-Key with a different body. Those need three different reactions —
top up, re-quote, fix your client — and a caller had only prose to tell them
apart. Prose is not a contract.

So each code is registered once, here, with the one thing a machine actually
needs to decide: **does retrying this exact request ever succeed, and under what
condition.** Docs, SDK retry logic and the playground all read this table, and a
test fails if a code exists in the codebase without an entry.

One deliberate exception. Every credential failure — missing header, malformed
token, unknown key id, wrong secret, revoked key, expired key — answers the same
``401 unauthorized``, and this registry keeps it that way. Splitting it would be
friendlier to the honest caller and would also turn the endpoint into a key
oracle: an attacker learns which of a million guessed key ids exists. The honest
caller has the portal, which knows exactly why their key is dead; the attacker
gets one answer. ``tests/test_192`` holds this.
"""
from __future__ import annotations

from dataclasses import dataclass

from llm_gateway.error_contract import ERROR_SPECS
from platform_core.public_api import errors as E

# ── Retry classes ────────────────────────────────────────────────────────────

#: Retrying the identical request will always fail the same way. Change the
#: request or stop.
RETRY_NEVER = "never"

#: The request is fine; something about the account or the quote is not. Fix
#: that first — retrying before then just burns rate limit.
RETRY_AFTER_FIX = "after_fix"

#: Transient. Retry with exponential backoff, honouring ``Retry-After`` when the
#: response carries it.
RETRY_AFTER_DELAY = "after_delay"
RETRY_AMBIGUOUS = "ambiguous"

RETRY_CLASSES = (RETRY_NEVER, RETRY_AFTER_FIX, RETRY_AFTER_DELAY, RETRY_AMBIGUOUS)


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    status: int
    retry: str
    action: str
    #: True when a retry of a *chargeable* call must carry the original
    #: Idempotency-Key. This is the field that keeps a retry from becoming a
    #: second purchase, and it is why the matrix below is not just "5xx = retry".
    reuse_idempotency_key: bool = False


def _spec(code, status, retry, action, reuse=False) -> ErrorSpec:
    return ErrorSpec(code=code, status=status, retry=retry, action=action,
                     reuse_idempotency_key=reuse)


REGISTRY = {spec.code: spec for spec in (
    # ── 400: the request itself is wrong ─────────────────────────────────────
    _spec(E.CODE_INVALID_REQUEST, 400, RETRY_NEVER,
          "Read `detail`; it names the field. Fix the request."),
    _spec(E.CODE_QUOTE_EXPIRED, 400, RETRY_AFTER_FIX,
          "Quotes live 15 minutes. Request a new quote and submit that."),
    _spec(E.CODE_QUOTE_INVALID, 400, RETRY_NEVER,
          "The quote does not belong to this account/tool/input. Request one "
          "for the exact call you are making."),
    _spec(E.CODE_MODEL_NOT_FOUND, 400, RETRY_AFTER_FIX,
          "That `model` is not served here. Call GET /api/v1/models for the "
          "names in service and send one of those."),

    # ── 401: credentials. One answer for all causes, on purpose. ─────────────
    _spec(E.CODE_UNAUTHORIZED, 401, RETRY_NEVER,
          "The key is missing, malformed, unknown, revoked or expired — the "
          "API will not say which. Check the key in the developer portal."),

    # ── 403: authenticated, but not allowed to do this ───────────────────────
    _spec(E.CODE_FORBIDDEN, 403, RETRY_NEVER,
          "This key may not perform this action."),
    _spec(E.CODE_MISSING_SCOPE, 403, RETRY_AFTER_FIX,
          "The key lacks a scope this endpoint needs. `required_scope` names "
          "it; issue a key that has it."),
    _spec(E.CODE_TOOL_NOT_ALLOWED, 403, RETRY_AFTER_FIX,
          "This key is restricted to a tool allowlist that excludes this tool, "
          "or the deployment does not publish it."),

    # ── 404 / 405 ────────────────────────────────────────────────────────────
    _spec(E.CODE_NOT_FOUND, 404, RETRY_NEVER,
          "No such resource, or it belongs to another account — the two are "
          "indistinguishable by design."),
    _spec(E.CODE_METHOD_NOT_ALLOWED, 405, RETRY_NEVER,
          "Wrong HTTP method for this path."),

    # ── 409: state, not syntax. Three distinct causes, three reactions. ──────
    _spec(E.CODE_CONFLICT, 409, RETRY_NEVER,
          "The resource is not in a state that allows this."),
    _spec(E.CODE_INSUFFICIENT_CREDIT, 409, RETRY_AFTER_FIX,
          "Top up credit, then submit again with the same Idempotency-Key.",
          reuse=True),
    _spec(E.CODE_PRICE_CHANGED, 409, RETRY_AFTER_FIX,
          "The price moved between quote and submit. Request a new quote; the "
          "old one is refused rather than silently repriced.", reuse=True),
    _spec(E.CODE_IDEMPOTENCY_CONFLICT, 409, RETRY_NEVER,
          "This Idempotency-Key was already used with a different body. Use a "
          "new key for a new call — never reuse one across different inputs."),
    _spec(E.CODE_IDEMPOTENCY_IN_PROGRESS, 409, RETRY_AFTER_DELAY,
          "Your first attempt is still running. Retry the identical request "
          "with the same key in a moment and you will get its answer.",
          reuse=True),

    # ── 413 / 422 ────────────────────────────────────────────────────────────
    _spec(E.CODE_PAYLOAD_TOO_LARGE, 413, RETRY_NEVER,
          "Send large media through the upload endpoints, not in the JSON "
          "body."),
    _spec(E.CODE_UNPROCESSABLE, 422, RETRY_NEVER,
          "The body parsed but failed validation. Read `detail`."),

    # ── 429: slow down. All three carry Retry-After. ─────────────────────────
    _spec(E.CODE_RATE_LIMITED, 429, RETRY_AFTER_DELAY,
          "Wait for `Retry-After` seconds, then retry with the same "
          "Idempotency-Key if the call was chargeable.", reuse=True),
    _spec(E.CODE_CONCURRENCY_LIMITED, 429, RETRY_AFTER_DELAY,
          "Too many of your jobs are running. Wait for one to finish; polling "
          "harder will not start it sooner.", reuse=True),
    _spec(E.CODE_QUOTA_EXCEEDED, 429, RETRY_AFTER_DELAY,
          "The account's daily credit ceiling is reached. It rolls forward "
          "continuously, so retry later or raise the ceiling.", reuse=True),

    # ── 5xx: ours, not yours ─────────────────────────────────────────────────
    _spec(E.CODE_INTERNAL, 500, RETRY_AFTER_DELAY,
          "Retry with backoff and the same Idempotency-Key. Quote the "
          "X-Correlation-ID if it persists.", reuse=True),
    _spec(E.CODE_READ_ONLY, 503, RETRY_AFTER_DELAY,
          "The API is accepting reads only. Writes resume without any change "
          "on your side.", reuse=True),
    _spec(E.CODE_SERVICE_UNAVAILABLE, 503, RETRY_AFTER_DELAY,
          "Retry with backoff and the same Idempotency-Key.", reuse=True),
)}

# Lỗi model dùng cùng vocabulary B→A. Trong chu kỳ rollout, registry legacy
# không bị viết đè: renderer có cờ riêng lấy status/retry đích từ taxonomy model.
MODEL_REGISTRY = {
    code: ErrorSpec(
        code=code,
        status=spec.status,
        retry=spec.retry,
        action=(REGISTRY[code].action if code in REGISTRY else spec.recovery),
        reuse_idempotency_key=(
            REGISTRY[code].reuse_idempotency_key if code in REGISTRY else False
        ),
    )
    for code, spec in ERROR_SPECS.items()
    if code not in REGISTRY
}
REGISTRY.update(MODEL_REGISTRY)


def spec_for(code: str) -> ErrorSpec:
    try:
        return REGISTRY[str(code)]
    except KeyError as exc:
        raise KeyError(
            f"error code {code!r} is not registered; add it to "
            f"platform_core/public_api/error_registry.py so callers are told "
            f"whether retrying helps") from exc


def is_retryable(code: str) -> bool:
    return spec_for(code).retry != RETRY_NEVER


def as_rows() -> list:
    """The registry as plain data — for docs, the portal and the SDKs."""
    return [{"code": spec.code, "status": spec.status, "retry": spec.retry,
             "reuse_idempotency_key": spec.reuse_idempotency_key,
             "action": spec.action}
            for spec in sorted(REGISTRY.values(),
                               key=lambda item: (item.status, item.code))]


# ── The retry matrix, stated once ────────────────────────────────────────────
#
# Written by status because that is what a generic HTTP client sees before it
# has parsed anything. The per-code table above refines it; where they disagree,
# the code wins, and that is the point of having codes.

RETRY_MATRIX = (
    ("4xx (except 409/429)", RETRY_NEVER,
     "The request is wrong. Repeating it unchanged is a bug in the client."),
    ("409", RETRY_AFTER_FIX,
     "State, not syntax. The code says which state; two of the three are "
     "fixable and then retryable with the same Idempotency-Key."),
    ("422", RETRY_NEVER, "Validation failed. Fix the body."),
    ("429", RETRY_AFTER_DELAY,
     "Honour Retry-After. Exponential backoff with jitter after that; do not "
     "retry faster than the header says."),
    ("5xx", RETRY_AFTER_DELAY,
     "Retry with backoff, capped attempts. Always reuse the Idempotency-Key."),
    ("network timeout / connection reset", RETRY_AFTER_DELAY,
     "The dangerous one: the request may have succeeded. Retry ONLY with the "
     "original Idempotency-Key — that turns an unknown outcome into a replay "
     "of the first answer instead of a second purchase."),
)

#: The rule that makes the matrix safe, and the reason the SDKs refuse to retry
#: a chargeable call without a key.
IDEMPOTENCY_RULE = (
    "A chargeable POST may only be retried when it carries the same "
    "Idempotency-Key as the original attempt. Without one, a retry after a "
    "timeout is a second job and a second hold; with one, the server replays "
    "the first answer and no money moves twice."
)
