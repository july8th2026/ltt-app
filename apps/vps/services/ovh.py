"""Minimal read-only OVH API client for provider inventory and health."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class OvhError(RuntimeError):
    """OVH could not be read; response bodies are deliberately not exposed."""


@dataclass(frozen=True)
class OvhConfig:
    application_key: str
    application_secret: str
    consumer_key: str
    service_name: str
    api_base: str = "https://ca.api.ovh.com/1.0"

    def verify(self) -> "OvhConfig":
        if self.api_base.rstrip("/") != "https://ca.api.ovh.com/1.0":
            raise OvhError("unsupported OVH API endpoint")
        if not all((self.application_key, self.application_secret,
                    self.consumer_key, self.service_name)):
            raise OvhError("OVH credential reference is incomplete")
        return self


@dataclass(frozen=True)
class OvhIpObservation:
    cidr: str
    address: str
    kind: str
    country: str
    routed_to: str


Transport = Callable[[str, str, dict[str, str]], Any]


class OvhClient:
    def __init__(self, config: OvhConfig, *, transport: Transport | None = None):
        self.config = config.verify()
        self._transport = transport or self._request
        self._clock_offset: int | None = None

    @staticmethod
    def _request(method: str, url: str, headers: dict[str, str]):
        try:
            with urlopen(Request(url, method=method, headers=headers), timeout=30) as response:
                body = response.read(2_000_001)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise OvhError(f"OVH request failed ({type(exc).__name__})") from None
        if len(body) > 2_000_000:
            raise OvhError("OVH response exceeded safe size")
        try:
            return json.loads(body.decode("utf-8")) if body else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise OvhError("OVH returned malformed JSON") from None

    def _server_time(self) -> int:
        if self._clock_offset is None:
            value = self._transport("GET", self.config.api_base + "/auth/time", {})
            if isinstance(value, bool) or not isinstance(value, int):
                raise OvhError("OVH time endpoint returned invalid data")
            self._clock_offset = value - int(time.time())
        return int(time.time()) + self._clock_offset

    def get(self, path: str):
        if not path.startswith("/") or ".." in path:
            raise OvhError("invalid OVH API path")
        url = self.config.api_base + path
        timestamp = str(self._server_time())
        raw = "+".join((self.config.application_secret, self.config.consumer_key,
                        "GET", url, "", timestamp))
        signature = "$1$" + hashlib.sha1(raw.encode("utf-8")).hexdigest()
        return self._transport("GET", url, {
            "X-Ovh-Application": self.config.application_key,
            "X-Ovh-Consumer": self.config.consumer_key,
            "X-Ovh-Timestamp": timestamp,
            "X-Ovh-Signature": signature,
        })

    def health(self) -> bool:
        services = self.get("/vps")
        return isinstance(services, list) and self.config.service_name in services

    def list_additional_ipv4(self) -> list[OvhIpObservation]:
        cidrs = self.get("/ip")
        if not isinstance(cidrs, list):
            raise OvhError("OVH IP inventory has invalid shape")
        result = []
        for raw_cidr in cidrs:
            cidr = str(raw_cidr)
            if not cidr.endswith("/32") or ":" in cidr:
                continue
            detail = self.get("/ip/" + quote(cidr, safe=""))
            if not isinstance(detail, dict):
                raise OvhError("OVH IP detail has invalid shape")
            routed = detail.get("routedTo") or {}
            result.append(OvhIpObservation(
                cidr=cidr, address=cidr[:-3], kind=str(detail.get("type") or ""),
                country=str(detail.get("country") or ""),
                routed_to=str(routed.get("serviceName") or "")
                if isinstance(routed, dict) else "",
            ))
        return result


def client_tu_moi_truong(env: dict[str, str]) -> OvhClient:
    return OvhClient(OvhConfig(
        application_key=str(env.get("LTT_OVH_APPLICATION_KEY", "")).strip(),
        application_secret=str(env.get("LTT_OVH_APPLICATION_SECRET", "")).strip(),
        consumer_key=str(env.get("LTT_OVH_CONSUMER_KEY", "")).strip(),
        service_name=str(env.get("LTT_OVH_SERVICE_NAME", "")).strip(),
        api_base=str(env.get("LTT_OVH_API_BASE", "")).strip()
        or "https://ca.api.ovh.com/1.0",
    ))
