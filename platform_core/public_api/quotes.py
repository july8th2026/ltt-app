"""Signed quotes for the Public API.

A quote is the platform's promise: *this exact input, for this account, costs
this many credits, until this moment*. It is signed so the server does not have
to remember it, and bound so it cannot be moved to another account, another
tool or another input.

Modelled on the signed-payload + one-shot ``intent`` pattern an app in this
repository already runs in production (see ``docs/PUBLIC_API/DECISIONS_V1.md``
PA-9; the platform must not name apps — ``AGENTS.md`` 8.4). The shape is reused,
that app's logic is not:
pricing still comes from ``registry.credit_for()``, the one place that knows
what a job costs (Q5: a job whose price cannot be looked up is refused, never
run for free).

Q84 is the reason a quote exists at all: the customer is never charged more than
the amount held against the quote they approved. Provider overshoot is the
platform's variance, not a surprise on the invoice.
"""
from __future__ import annotations

import uuid

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from platform_core.public_api.errors import (invalid_request, quote_expired,
                                             quote_invalid)
from platform_core.public_api.idempotency import canonical_hash

QUOTE_TTL_S = 15 * 60
_SALT = "ltt-public-api-quote-v1"
_VERSION = 1


def _serializer(secret: str) -> URLSafeTimedSerializer:
    if not str(secret or "").strip():
        raise invalid_request("Quotes are not configured on this deployment.")
    return URLSafeTimedSerializer(str(secret))


def fingerprint(tool_name: str, params: dict) -> str:
    """What the quote is bound to: the tool plus the exact priced input."""
    return canonical_hash({"tool": str(tool_name), "params": params or {}})


def issue(*, secret: str, user_id: str, key_id: str, tool_name: str,
          params: dict, credit: int,
          pricing_version: str = "") -> tuple[str, dict]:
    """Mint a quote token and its payload.

    ``pricing_version`` travels **inside the signature**. That is the whole
    mechanism behind "no retroactive price change": the label and the amount
    were written together, at the same moment, and neither can be edited
    afterwards without breaking the signature (EXT-15).
    """
    payload = {
        "v": _VERSION,
        "user_id": str(user_id),
        # Recorded for audit, deliberately **not** part of the binding: an
        # account may quote with one key and submit with another (a deploy that
        # rotates keys between the two calls is normal), and both keys bill the
        # same account anyway.
        "key_id": str(key_id),
        "tool": str(tool_name),
        "fingerprint": fingerprint(tool_name, params),
        "credit": int(credit),
        "pricing_version": str(pricing_version or ""),
        "intent": uuid.uuid4().hex,
    }
    return _serializer(secret).dumps(payload, salt=_SALT), payload


def verify(*, secret: str, token: str, user_id: str,
           max_age: int | None = None) -> dict:
    """Decode a quote for ``user_id``. Raises 400 on tamper, expiry or theft."""
    if not str(token or "").strip():
        raise invalid_request("A quote token is required.")
    # Read the TTL at call time rather than binding it as a default: a default
    # freezes the value at import, so changing it (an operator tightening the
    # window, a test shortening it) would silently have no effect.
    ttl = QUOTE_TTL_S if max_age is None else int(max_age)
    try:
        payload = _serializer(secret).loads(token, salt=_SALT, max_age=ttl)
    except SignatureExpired as exc:
        raise quote_expired("This quote has expired; request a new one.") from exc
    except BadSignature as exc:
        raise quote_invalid("This quote is not valid.") from exc
    if not isinstance(payload, dict) or payload.get("v") != _VERSION:
        raise quote_invalid("This quote is not valid.")
    if str(payload.get("user_id") or "") != str(user_id):
        # Same answer as a forged signature on purpose: a caller must not learn
        # that somebody else's quote exists and is merely mis-addressed.
        raise quote_invalid("This quote is not valid.")
    if len(str(payload.get("intent") or "")) != 32:
        raise quote_invalid("This quote is not valid.")
    if int(payload.get("credit", -1)) < 0:
        raise quote_invalid("This quote is not valid.")
    return payload


def check_matches(payload: dict, *, tool_name: str, params: dict) -> None:
    """Refuse a quote that was priced for a different input.

    Without this a caller could quote a one-second video and submit a
    ten-minute one under the same token — the fingerprint is what makes the
    price a promise about *this* request rather than about a token.
    """
    if str(payload.get("tool") or "") != str(tool_name):
        raise quote_invalid("This quote was issued for a different tool.")
    if str(payload.get("fingerprint") or "") != fingerprint(tool_name, params):
        raise quote_invalid(
            "This quote was issued for a different input; request a new quote.")
