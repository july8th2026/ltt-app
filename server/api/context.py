"""Per-request context for ``/api/v1``: request id and a trustworthy client IP.

Both helpers exist because the obvious implementation is wrong here.

**Request id.** ``server/app.py`` already stamps every response with
``X-Correlation-ID``. The Public API reuses that value instead of minting a
second one, so a support ticket, a process log line, a ``job_events`` row and
the caller's error body all carry the same string.

**Client IP.** ``server/auth/session.py:client_ip`` believes ``CF-Connecting-IP``
unconditionally. That is defensible for the browser surface, where the origin
only ever accepts loopback connections from ``cloudflared``. It is not
defensible as a general rule: the moment anything else can reach this process
(a second reverse proxy, a test harness, an operator curling the port), a caller
can hand-write that header and become any IP it likes — which would poison rate
limits and abuse counters keyed on it. So here the header is believed **only**
when the socket peer is itself a trusted proxy, and ``X-Forwarded-For`` is never
read at all.
"""
from __future__ import annotations

import uuid

CLIENT_IP_HEADER = "cf-connecting-ip"
UNKNOWN_CLIENT_IP = "unknown"


def request_id(request) -> str:
    """The correlation id for this request; mint one if the middleware missed."""
    existing = getattr(request.state, "correlation_id", "")
    if existing:
        return str(existing)
    minted = str(uuid.uuid4())
    request.state.correlation_id = minted
    return minted


def peer_ip(request) -> str:
    client = getattr(request, "client", None)
    host = getattr(client, "host", "") if client is not None else ""
    return host or UNKNOWN_CLIENT_IP


def is_trusted_peer(peer: str, trusted_proxies) -> bool:
    """Exact address or CIDR block. Both, because operators write both.

    Cloudflare publishes its edge as ranges, not addresses, so a trust list that
    only did exact matches would force an operator to paste hundreds of lines and
    re-paste them whenever the ranges change. An unparseable entry is ignored
    rather than trusted: a typo in a config file must not widen who is believed.
    """
    import ipaddress

    entries = list(trusted_proxies or ())
    if peer in set(entries):
        return True
    try:
        address = ipaddress.ip_address(str(peer or "").strip())
    except ValueError:
        return False
    for entry in entries:
        text = str(entry).strip()
        if "/" not in text:
            continue
        try:
            if address in ipaddress.ip_network(text, strict=False):
                return True
        except ValueError:
            continue
    return False


def client_ip(request, trusted_proxies) -> str:
    """Caller IP, honouring ``CF-Connecting-IP`` only from a trusted peer."""
    peer = peer_ip(request)
    if is_trusted_peer(peer, trusted_proxies):
        forwarded = (request.headers.get(CLIENT_IP_HEADER) or "").strip()
        # A proxy may chain values; the first entry is the original client.
        candidate = forwarded.split(",")[0].strip()
        if candidate:
            return candidate[:45]
    return peer
