"""Minimal Python client for the LTT Studios Public API.

No third-party dependencies: a customer integrating one API should not have to
adopt our HTTP library. Standard library only.

The one rule this client exists to enforce, because getting it wrong costs the
customer money:

    a chargeable POST is retried **only** with the same Idempotency-Key.

Everything else — GET retries, waiting for a job, downloading an artifact,
verifying a webhook signature — is convenience.

    from ltt_public_api import LttClient

    client = LttClient(base_url="https://app.lttstudios.com", api_key="ltt_sk_…")
    quote = client.quote("image.thumbnail", {"topic": "bánh mì", "count": 2})
    job = client.create_job(quote, {"topic": "bánh mì", "count": 2})
    job = client.wait_for_job(job["id"])
    for artifact in job.get("outputs", []):
        print(client.artifact_url(artifact["id"]))
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field

__all__ = ["LttClient", "LttApiError", "verify_webhook"]

USER_AGENT = "ltt-public-api-python/1.0"
DEFAULT_TIMEOUT = 30.0

# A GET is safe to repeat, so transient failures are retried. A chargeable POST
# is not repeated unless the caller's Idempotency-Key makes it safe — see
# `create_job`.
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
MAX_RETRIES = 3


class LttApiError(RuntimeError):
    """One problem+json response, kept whole so callers can branch on `code`."""

    def __init__(self, status: int, payload: dict):
        self.status = int(status)
        self.payload = dict(payload or {})
        self.code = str(self.payload.get("code") or "")
        self.request_id = str(self.payload.get("request_id") or "")
        detail = self.payload.get("detail") or self.payload.get("title") or ""
        super().__init__(f"{self.status} {self.code}: {detail}")

    @property
    def retry_after(self) -> int:
        try:
            return int(self.payload.get("retry_after") or 0)
        except (TypeError, ValueError):
            return 0


@dataclass
class LttClient:
    base_url: str
    api_key: str
    timeout: float = DEFAULT_TIMEOUT
    max_retries: int = MAX_RETRIES
    # Injectable so tests can drive the client against an in-process app; a real
    # integration never sets it.
    transport: object = field(default=None, repr=False)

    # ── HTTP ──────────────────────────────────────────────────────────────────

    def _url(self, path: str) -> str:
        return self.base_url.rstrip("/") + "/api/v1" + path

    def _request(self, method: str, path: str, *, body=None,
                 headers: dict | None = None, retry: bool = False):
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }
        if payload is not None:
            request_headers["Content-Type"] = "application/json"
        request_headers.update(headers or {})

        attempt = 0
        while True:
            attempt += 1
            try:
                status, response_headers, raw = self._send(
                    method, self._url(path), payload, request_headers)
            except OSError:
                if retry and attempt <= self.max_retries:
                    time.sleep(min(8.0, 0.5 * 2 ** (attempt - 1)))
                    continue
                raise
            if status in RETRY_STATUSES and retry and attempt <= self.max_retries:
                # `retry_after` from the server beats a guess from the client.
                wait = 0
                try:
                    wait = int(json.loads(raw or b"{}").get("retry_after") or 0)
                except (ValueError, AttributeError, TypeError):
                    wait = 0
                time.sleep(max(wait, min(8.0, 0.5 * 2 ** (attempt - 1))))
                continue
            return status, response_headers, raw

    def _send(self, method: str, url: str, payload, headers):
        if self.transport is not None:
            return self.transport(method, url, payload, headers)
        request = urllib.request.Request(url, data=payload, headers=headers,
                                         method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read()
            exc.close()
            return int(exc.code), dict(exc.headers or {}), body

    def _json(self, method: str, path: str, *, body=None, headers=None,
              retry: bool = False) -> dict:
        status, response_headers, raw = self._request(
            method, path, body=body, headers=headers, retry=retry)
        try:
            parsed = json.loads(raw or b"{}")
        except ValueError:
            parsed = {}
        if status >= 400:
            raise LttApiError(status, parsed if isinstance(parsed, dict) else {})
        if isinstance(parsed, dict):
            parsed.setdefault("_headers", response_headers)
        return parsed

    # ── Reads (safe to retry) ────────────────────────────────────────────────

    # @covers GET /me
    def me(self) -> dict:
        return self._json("GET", "/me", retry=True)

    # @covers GET /capabilities
    def capabilities(self) -> dict:
        return self._json("GET", "/capabilities", retry=True)

    # @covers GET /tools
    def tools(self, *, limit: int = 20, offset: int = 0) -> dict:
        return self._json("GET", f"/tools?limit={int(limit)}&offset={int(offset)}",
                          retry=True)

    # @covers GET /models
    def models(self, *, limit: int = 20, offset: int = 0) -> dict:
        """Model aliases this key may use. Aliases, never provider model ids —
        the platform publishes names it controls, so a provider swap does not
        become your migration."""
        query = urllib.parse.urlencode({"limit": int(limit),
                                        "offset": int(offset)})
        return self._json("GET", f"/models?{query}", retry=True)

    # @covers GET /models/{model_name}
    def model(self, name: str) -> dict:
        return self._json("GET", f"/models/{urllib.parse.quote(name)}",
                          retry=True)

    # @covers GET /health
    def health(self) -> dict:
        """Liveness of the API surface. No credential required, so this is the
        one call worth making before blaming your key."""
        return self._json("GET", "/health", retry=True)

    # @covers GET /tools/{tool_name}
    def tool(self, name: str) -> dict:
        return self._json("GET", f"/tools/{urllib.parse.quote(name)}", retry=True)

    # @covers GET /jobs/{job_id}
    def job(self, job_id: str) -> dict:
        return self._json("GET", f"/jobs/{urllib.parse.quote(job_id)}", retry=True)

    # @covers GET /jobs
    def jobs(self, *, status: str = "", limit: int = 20, offset: int = 0) -> dict:
        query = urllib.parse.urlencode(
            {"status": status, "limit": limit, "offset": offset})
        return self._json("GET", f"/jobs?{query}", retry=True)

    # @covers GET /credits/balance
    def balance(self) -> dict:
        return self._json("GET", "/credits/balance", retry=True)

    # @covers GET /usage
    def usage(self, **params) -> dict:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v})
        return self._json("GET", f"/usage?{query}" if query else "/usage",
                          retry=True)

    # @covers GET /artifacts/{artifact_id}
    def artifact_url(self, artifact_id: str) -> str:
        return self._json(
            "GET", f"/artifacts/{urllib.parse.quote(artifact_id)}",
            retry=True)["url"]

    # @covers GET /artifacts/{artifact_id}/content
    def download_artifact(self, artifact_id: str) -> bytes:
        _status, _headers, raw = self._request(
            "GET", f"/artifacts/{urllib.parse.quote(artifact_id)}/content",
            retry=True)
        return raw

    # ── Writes ───────────────────────────────────────────────────────────────

    # @covers POST /quotes
    def quote(self, tool: str, tool_input: dict) -> dict:
        """Price a call. Cheap, chargeable-free, and safe to repeat."""
        return self._json("POST", "/quotes",
                          body={"tool": tool, "input": tool_input}, retry=True)

    # @covers POST /jobs
    def create_job(self, quote: dict, tool_input: dict, *,
                   idempotency_key: str = "") -> dict:
        """Run a quoted call.

        The key is generated once, here, and reused for every retry of *this*
        call. That is the difference between a timeout costing nothing and a
        timeout costing the customer a second job: the server returns the first
        job for a repeated key, and a *new* key would create a second one.
        """
        key = idempotency_key or uuid.uuid4().hex
        return self._json(
            "POST", "/jobs",
            body={"tool": quote["tool"], "quote": quote["quote"],
                  "input": tool_input},
            headers={"Idempotency-Key": key},
            # Safe precisely because the key is fixed for the whole loop.
            retry=True)

    # @covers POST /jobs/{job_id}/cancel
    def cancel_job(self, job_id: str) -> dict:
        return self._json("POST", f"/jobs/{urllib.parse.quote(job_id)}/cancel")

    def wait_for_job(self, job_id: str, *, timeout: float = 600.0,
                     poll_interval: float = 2.0) -> dict:
        """Poll until the job reaches a terminal state, or raise TimeoutError."""
        deadline = time.monotonic() + float(timeout)
        while True:
            job = self.job(job_id)
            if job.get("status") in ("succeeded", "failed", "cancelled"):
                return job
            if time.monotonic() >= deadline:
                raise TimeoutError(f"job {job_id} did not finish in {timeout}s")
            time.sleep(poll_interval)

    # ── Uploads ──────────────────────────────────────────────────────────────

    # @covers POST /uploads
    # @covers POST /uploads/{upload_id}/content
    # @covers POST /uploads/{upload_id}/confirm
    def upload(self, tool: str, field_name: str, filename: str,
               content_type: str, data: bytes) -> str:
        """Create a ticket, send the bytes, confirm. Returns the upload id."""
        ticket = self._json("POST", "/uploads", body={
            "tool": tool, "field": field_name, "filename": filename,
            "content_type": content_type, "size": len(data)})
        target = ticket.get("upload") or {}
        if str(target.get("method", "")).upper() == "PUT":
            self._put_bytes(target["url"], data,
                            dict(target.get("headers") or {}))
        else:
            self._post_multipart(target.get("url") or
                                 f"/uploads/{ticket['id']}/content",
                                 filename, content_type, data)
        self._json("POST", f"/uploads/{ticket['id']}/confirm")
        return ticket["id"]

    def _put_bytes(self, url: str, data: bytes, headers: dict) -> None:
        request = urllib.request.Request(url, data=data, method="PUT",
                                         headers=headers or {})
        with urllib.request.urlopen(request, timeout=self.timeout):
            return

    def _post_multipart(self, path: str, filename: str, content_type: str,
                        data: bytes) -> None:
        boundary = uuid.uuid4().hex
        body = b"".join([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            data, f"\r\n--{boundary}--\r\n".encode(),
        ])
        url = path if path.startswith("http") else self.base_url.rstrip("/") + path
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type": f"multipart/form-data; boundary={boundary}",
                   "User-Agent": USER_AGENT}
        if self.transport is not None:
            self.transport("POST", url, body, headers)
            return
        request = urllib.request.Request(url, data=body, headers=headers,
                                         method="POST")
        with urllib.request.urlopen(request, timeout=self.timeout):
            return

    # ── Webhooks ─────────────────────────────────────────────────────────────

    # @covers POST /webhooks
    def create_webhook(self, url: str, events=()) -> dict:
        return self._json("POST", "/webhooks",
                          body={"url": url, "events": list(events)})

    # @covers GET /webhooks
    def webhooks(self) -> dict:
        return self._json("GET", "/webhooks", retry=True)

    # @covers DELETE /webhooks/{webhook_id}
    def delete_webhook(self, webhook_id: str) -> dict:
        return self._json("DELETE", f"/webhooks/{urllib.parse.quote(webhook_id)}")

    # @covers GET /webhooks/deliveries
    def webhook_deliveries(self, *, subscription_id: str = "",
                           status: str = "", limit: int = 20,
                           offset: int = 0) -> dict:
        """What we tried to send you, and how it went.

        The first thing to read when a callback did not arrive: it separates
        "we never sent it" from "we sent it and your endpoint refused".
        """
        params = {"limit": int(limit), "offset": int(offset)}
        if subscription_id:
            params["subscription_id"] = subscription_id
        if status:
            params["status"] = status
        query = urllib.parse.urlencode(params)
        return self._json("GET", f"/webhooks/deliveries?{query}", retry=True)


def verify_webhook(secret: str, *, timestamp, event_id: str, body: bytes,
                   signature: str, tolerance_s: int = 300) -> bool:
    """Check a delivery came from LTT and is not a replay.

    Run this before trusting anything in the payload. The timestamp check is
    what stops an old, valid delivery being replayed at you later.
    """
    try:
        sent_at = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(int(time.time()) - sent_at) > int(tolerance_s):
        return False
    payload = b".".join([str(sent_at).encode("ascii"),
                         str(event_id).encode("ascii"), body])
    expected = hmac.new(str(secret).encode("utf-8"), payload,
                        hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"v1={expected}", str(signature or ""))


# The one route no client method wraps, and why that is deliberate:
# @covers-not GET /openapi.json — machine-readable spec, not a call your code
# makes. Fetch it with any HTTP client, or download the versioned copy from the
# developer portal; wrapping it would imply the SDK parses it, which it does not.
