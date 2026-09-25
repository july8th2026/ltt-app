"""Tao/sua MOT A record tren Cloudflare — chi dung cho rDNS cua IP khach.

Pham vi hep co chu y: token `LTT_CF_DNS_TOKEN` duoc cap quyen **DNS:Edit tren
dung mot zone**. Tep nay khong lam gi ngoai viec dat mot ban ghi A tro ve mot
dia chi IPv4 da kiem.
"""
from __future__ import annotations

import json
import logging
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)

GOC = "https://api.cloudflare.com/client/v4"


class CloudflareError(RuntimeError):
    pass


class CloudflareDns:
    def __init__(self, token: str, zone: str = "lttstudios.com", *, goi=None):
        if not str(token or "").strip():
            raise CloudflareError("thieu token Cloudflare")
        self.token = str(token).strip()
        self.zone = str(zone).strip()
        self._goi = goi or self._goi_that
        self._zone_id: str | None = None

    def _goi_that(self, method: str, duong: str, payload: dict | None = None):
        body = (json.dumps(payload, separators=(",", ":")).encode("utf-8")
                if payload is not None else None)
        req = Request(GOC + duong, data=body, method=method, headers={
            "Authorization": "Bearer " + self.token,
            "Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=30) as r:
                return json.loads(r.read() or b"null")
        except HTTPError as exc:
            chi_tiet = exc.read().decode("utf-8", "replace")[:300]
            raise CloudflareError(f"Cloudflare {exc.code}: {chi_tiet}") from None
        except OSError as exc:
            raise CloudflareError(f"Cloudflare khong goi duoc ({type(exc).__name__})") from None

    def zone_id(self) -> str:
        if self._zone_id is None:
            ra = self._goi("GET", f"/zones?name={self.zone}")
            ds = (ra or {}).get("result") or []
            if not ds:
                raise CloudflareError(f"khong thay zone {self.zone}")
            self._zone_id = str(ds[0]["id"])
        return self._zone_id

    def dat_a_record(self, ten: str, ip: str) -> None:
        """Tao A record, hoac sua neu da co. Idempotent — job chay lai duoc."""
        zid = self.zone_id()
        ra = self._goi("GET", f"/zones/{zid}/dns_records?type=A&name={ten}")
        co = (ra or {}).get("result") or []
        than = {"type": "A", "name": ten, "content": str(ip), "ttl": 3600,
                "proxied": False}
        if co:
            if str(co[0].get("content")) == str(ip):
                return                       # da dung roi, khong ghi lai
            self._goi("PUT", f"/zones/{zid}/dns_records/{co[0]['id']}", than)
            return
        self._goi("POST", f"/zones/{zid}/dns_records", than)


def client_tu_moi_truong(env: dict | None = None) -> CloudflareDns:
    e = env if env is not None else os.environ
    return CloudflareDns(e.get("LTT_CF_DNS_TOKEN", ""),
                         e.get("LTT_CF_DNS_ZONE", "lttstudios.com"))
