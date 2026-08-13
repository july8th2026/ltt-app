"""Webhook subscriptions, transactional outbox, signing and SSRF defence.

Three properties, in the order they matter:

**A webhook must never be able to affect a job.** Delivery is a separate row
written in the same transaction as the job's terminal state (a transactional
outbox), then sent by the worker. A receiver that is down, slow or hostile can
therefore delay nothing and settle nothing differently — the money side has
already committed.

**A webhook must not become an SSRF channel.** The customer chooses the URL, so
the platform is being asked to make an outbound request to an address an
untrusted party picked. Every hop is validated — scheme, host, resolved IP,
and again after each redirect — against loopback, private, link-local and
cloud-metadata ranges. No platform credential is ever attached.

**A receiver must be able to prove the call came from us.** Each delivery is
signed ``HMAC-SHA256(secret, "<timestamp>.<event_id>.<raw body>")``, which binds
the signature to a moment, to one immutable event and to the exact bytes — so a
replayed body, a resent old event or a modified payload all fail verification.

The subscription secret is **encrypted at rest**, not hashed: the server has to
reproduce it to sign with it. That is the opposite requirement to a developer
API key, and mixing the two would break one of them.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import socket
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from platform_core.public_api.errors import invalid_request

EVENT_JOB_SUCCEEDED = "job.succeeded"
EVENT_JOB_FAILED = "job.failed"
EVENT_JOB_CANCELLED = "job.cancelled"
# Terminal states only. A "job.running" event would be a second, weaker copy of
# information the caller can already poll for, and every extra event is another
# request the platform makes to an address a customer controls.
TERMINAL_EVENTS = (EVENT_JOB_SUCCEEDED, EVENT_JOB_FAILED, EVENT_JOB_CANCELLED)

SIGNATURE_HEADER = "X-LTT-Signature"
TIMESTAMP_HEADER = "X-LTT-Timestamp"
EVENT_HEADER = "X-LTT-Event-Id"
SIGNATURE_VERSION = "v1"

MAX_ATTEMPTS = 6
BASE_BACKOFF_S = 30
MAX_BACKOFF_S = 6 * 3600
DELIVERY_TIMEOUT_S = 10
MAX_RESPONSE_BYTES = 8 * 1024
MAX_REDIRECTS = 3
SECRET_BYTES = 32

# Anything that is not a public unicast address. `is_private` already covers RFC
# 1918 and unique-local; the rest are called out because they are the ones that
# actually get abused: the cloud metadata service, loopback, link-local.
METADATA_ADDRESSES = frozenset({"169.254.169.254", "fd00:ec2::254"})


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WebhookError(Exception):
    """A delivery could not be attempted at all (bad target, bad config)."""


# ── Target validation (SSRF) ──────────────────────────────────────────────────

def validate_target(url: str, *, require_https: bool = True,
                    resolver=None) -> str:
    """Check a customer-supplied URL, or raise.

    Called both when a subscription is created **and** before every delivery,
    including after each redirect: DNS can change between those moments, and a
    name that resolved to a public address yesterday can point at 127.0.0.1
    today (DNS rebinding).
    """
    raw = str(url or "").strip()
    if not raw:
        raise invalid_request("A webhook URL is required.")
    if len(raw) > 2000:
        raise invalid_request("This webhook URL is too long.")
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    allowed = {"https"} if require_https else {"https", "http"}
    if scheme not in allowed:
        raise invalid_request("Webhook URLs must use https.")
    if parsed.username or parsed.password:
        # Credentials in the URL would be echoed into logs and are never needed.
        raise invalid_request("Webhook URLs must not contain credentials.")
    host = parsed.hostname or ""
    if not host:
        raise invalid_request("This webhook URL has no host.")

    for address in _resolve(host, resolver):
        _reject_internal(address)
    return raw


def _resolve(host: str, resolver=None) -> list:
    """Every address the host resolves to — all of them must be public.

    Checking only the first answer is a hole: a name can return one public and
    one private address, and which one a client connects to is not something
    this code controls.
    """
    try:
        literal = ipaddress.ip_address(host)
        return [literal]
    except ValueError:
        pass
    lookup = resolver or _system_resolver
    try:
        addresses = lookup(host)
    except OSError as exc:
        raise invalid_request("This webhook host could not be resolved.") from exc
    if not addresses:
        raise invalid_request("This webhook host could not be resolved.")
    return [ipaddress.ip_address(address) for address in addresses]


def _system_resolver(host: str) -> list:
    return sorted({info[4][0] for info in socket.getaddrinfo(host, None)})


def _reject_internal(address) -> None:
    if (address.is_loopback or address.is_private or address.is_link_local
            or address.is_multicast or address.is_reserved
            or address.is_unspecified
            or str(address) in METADATA_ADDRESSES):
        # One message for every rejected class: a caller must not be able to use
        # the error text to map the platform's internal network.
        raise invalid_request("This webhook URL is not allowed.")


# ── Signing ───────────────────────────────────────────────────────────────────

def new_secret() -> str:
    import secrets

    return secrets.token_urlsafe(SECRET_BYTES)


def signature_payload(timestamp: int, event_id: str, body: bytes) -> bytes:
    return b".".join([str(int(timestamp)).encode("ascii"),
                      str(event_id).encode("ascii"), body])


def sign(secret: str, *, timestamp: int, event_id: str, body: bytes) -> str:
    digest = hmac.new(str(secret).encode("utf-8"),
                      signature_payload(timestamp, event_id, body),
                      hashlib.sha256).hexdigest()
    return f"{SIGNATURE_VERSION}={digest}"


def verify(secret: str, *, timestamp: int, event_id: str, body: bytes,
           signature: str, tolerance_s: int = 300) -> bool:
    """What a receiver runs. Shipped here so the docs and the tests agree."""
    if abs(int(time.time()) - int(timestamp)) > tolerance_s:
        return False
    expected = sign(secret, timestamp=timestamp, event_id=event_id, body=body)
    return hmac.compare_digest(expected, str(signature or ""))


# ── Event payloads ────────────────────────────────────────────────────────────

def job_event_type(status: str) -> str:
    from platform_core.models import JOB_CANCELLED, JOB_DONE, JOB_ERROR

    return {JOB_DONE: EVENT_JOB_SUCCEEDED, JOB_ERROR: EVENT_JOB_FAILED,
            JOB_CANCELLED: EVENT_JOB_CANCELLED}.get(str(status), "")


def build_payload(*, event_id: str, event_type: str, job_id: str,
                  tool: str, status: str, created_at: datetime | None = None) -> dict:
    """Deliberately thin: identifiers and status, never results or params.

    A webhook goes to an address the platform cannot vouch for, and a
    misconfigured one is a data leak. The receiver fetches what it needs through
    the authenticated API using the ids in here.
    """
    return {
        "id": str(event_id),
        "type": str(event_type),
        "created_at": (created_at or _now()).isoformat(),
        "data": {"job_id": str(job_id), "tool": str(tool or ""),
                 "status": str(status)},
    }


def canonical_body(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


# ── Retry schedule ────────────────────────────────────────────────────────────

def next_attempt_at(attempt: int, *, now: datetime | None = None,
                    jitter: float = 0.0) -> datetime:
    """Exponential backoff with jitter, capped.

    Jitter is passed in rather than drawn here so the schedule is deterministic
    in tests; the worker supplies a random value. Without it, a receiver that
    goes down takes every pending delivery with it and then gets all of them
    back in one synchronised wave when it returns.
    """
    delay = min(MAX_BACKOFF_S, BASE_BACKOFF_S * (2 ** max(0, int(attempt) - 1)))
    spread = delay * 0.2 * max(0.0, min(1.0, float(jitter)))
    return (now or _now()) + timedelta(seconds=delay + spread)


def new_event_id() -> str:
    return uuid.uuid4().hex
