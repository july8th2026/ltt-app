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


def send_delivery(subscription, delivery, *, require_https: bool = True,
                  resolver=None, timeout: float = webhooks.DELIVERY_TIMEOUT_S) -> int:
    """POST one signed event. Returns the HTTP status code."""
    from platform_core import secretbox

    secret = secretbox.giai_ma(subscription.secret_enc)
    body = webhooks.canonical_body(delivery.payload or {})
    timestamp = int(time.time())
    signature = webhooks.sign(secret, timestamp=timestamp,
                              event_id=delivery.event_id, body=body)
    headers = {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        webhooks.SIGNATURE_HEADER: signature,
        webhooks.TIMESTAMP_HEADER: str(timestamp),
        webhooks.EVENT_HEADER: delivery.event_id,
    }

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
