"""The outbound HTTP call for one webhook delivery.

Isolated in its own module because this is the one place the platform makes a
request to an address an untrusted party chose. Everything here is a defence:

* the target is re-validated **before every attempt and after every redirect** —
  DNS can change between the moment a subscription was created and now;
* redirects are followed manually and capped, because a permissive client would
  happily follow a 302 into ``127.0.0.1``;
* the response is read with a hard cap and a short timeout, so a receiver cannot
  hold a worker thread open or feed it a gigabyte;
* nothing of the platform's is attached: no cookies, no API key, no internal
  header. The only credential involved is the subscription's own signature.
"""
from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request

from platform_core.public_api import webhooks

USER_AGENT = "LTTStudios-Webhook/1.0"


def _opener() -> urllib.request.OpenerDirector:
    # No redirect handler and no cookie handler: redirects are followed by hand
    # so each hop can be re-validated, and a cookie jar would be shared state
    # between customers' endpoints.
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    return urllib.request.build_opener(_NoRedirect)


def build_headers(subscription, delivery, *, body: bytes | None = None,
                  timestamp: int | None = None) -> dict:
    """The headers one delivery is sent with, including its signature(s).

    Separated from sending so the signature can be checked in a test without a
    receiver — the thing most worth checking is exactly the thing that needs a
    server to observe otherwise.
    """
    from platform_core import secretbox
    from platform_core.public_api import webhook_console

    payload_body = webhooks.canonical_body(delivery.payload or {}) \
        if body is None else body
    stamp = int(time.time()) if timestamp is None else int(timestamp)
    signatures = [webhooks.sign(secretbox.giai_ma(subscription.secret_enc),
                                timestamp=stamp, event_id=delivery.event_id,
                                body=payload_body)]

    # During a rotation grace window the event is signed with both secrets, so a
    # receiver that has switched and one that has not both verify. They travel
    # comma-separated and a verifier accepts if *any* entry matches.
    previous = webhook_console.grace_secret(subscription)
    if previous:
        signatures.append(webhooks.sign(previous, timestamp=stamp,
                                        event_id=delivery.event_id,
                                        body=payload_body))
    return {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        webhooks.SIGNATURE_HEADER: ",".join(signatures),
        webhooks.TIMESTAMP_HEADER: str(stamp),
        webhooks.EVENT_HEADER: delivery.event_id,
    }


def send_delivery(subscription, delivery, *, require_https: bool = True,
                  resolver=None, timeout: float = webhooks.DELIVERY_TIMEOUT_S) -> int:
    """POST one signed event. Returns the HTTP status code."""
    body = webhooks.canonical_body(delivery.payload or {})
    headers = build_headers(subscription, delivery, body=body)

    url = subscription.url
    opener = _opener()
    for _hop in range(webhooks.MAX_REDIRECTS + 1):
        webhooks.validate_target(url, require_https=require_https,
                                 resolver=resolver)
        request = urllib.request.Request(url, data=body, headers=headers,
                                         method="POST")
        try:
            with opener.open(request, timeout=timeout) as response:
                response.read(webhooks.MAX_RESPONSE_BYTES)
                return int(response.status)
        except urllib.error.HTTPError as exc:
            status = int(exc.code)
            location = exc.headers.get("Location") if exc.headers else None
            if status in (301, 302, 303, 307, 308) and location:
                # Re-validated at the top of the next iteration — that is the
                # whole reason redirects are handled here instead of by urllib.
                url = urllib.parse.urljoin(url, location)
                continue
            try:
                exc.read(webhooks.MAX_RESPONSE_BYTES)
            finally:
                exc.close()
            return status
    raise webhooks.WebhookError("Too many redirects.")
