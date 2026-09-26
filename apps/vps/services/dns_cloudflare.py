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
    """`status` + `ma_loi` la **bo phan loai**, khong phai noi dung.

    🔴 Ra soat 26/09/2026 cho tep nay 5/10 — thap nhat trong bay lop noi — vi hai ly
       do doc lap, va **toi viet no hom truoc**:

       1. Day la lop loi DUY NHAT khong co `.status`. `OvhError`, `ProxmoxError`,
          `VultrError`, `GatewayError` deu co. Nguoi goi khong phan biet duoc `429`
          (bi ham nhip ⇒ cho roi thu lai) voi `403` (token sai ⇒ thu lai vo nghia).
       2. No nhet 300 ky tu **than loi tho** vao message — dung cai da tranh o
          `ovh._ma_loi_ovh`, noi chi lay ma dinh danh. Than loi Cloudflare mang **ten
          ban ghi**, tuc mang IP cua khach.

    ⭐ Cung mot nguoi, cung mot ngay, da sua dung lop loi nay o `ovh.py` roi lap lai
      o day. **Biet ve cai bay khong mien nhiem no** — thu chan duoc la mot phep kiem.
    """

    def __init__(self, *args, status: int | None = None, ma_loi: str = ""):
        super().__init__(*args)
        self.status = status
        self.ma_loi = ma_loi


def ma_loi_cloudflare(exc) -> str:
    """Ma loi so cua Cloudflare tu than phan hoi. Chuoi rong neu khong doc duoc.

    Chi lay `errors[].code` — mot SO. ⛔ Khong bao gio lay `message`: no la van ban
    tu do cua nha cung cap va co khi vong lai chinh yeu cau.
    """
    try:
        than = exc.read(4096)
    except Exception:                         # noqa: BLE001 - loi khong co than
        return ""
    try:
        doc = json.loads(than.decode("utf-8", "replace") if isinstance(than, bytes)
                         else str(than))
    except (json.JSONDecodeError, AttributeError):
        return ""
    if not isinstance(doc, dict):
        return ""
    for muc in doc.get("errors") or []:
        if isinstance(muc, dict) and muc.get("code") is not None:
            ma = str(muc["code"])
            return ma if ma.isdigit() and len(ma) <= 10 else ""
    return ""


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
            # ⛔ KHONG dua than loi tho vao thong diep: no mang ten ban ghi, tuc
            #    mang IP cua khach. Chi ma HTTP + ma so cua Cloudflare.
            ma_loi = ma_loi_cloudflare(exc)
            raise CloudflareError(
                f"Cloudflare {exc.code}" + (f" ma {ma_loi}" if ma_loi else ""),
                status=int(exc.code), ma_loi=ma_loi) from None
        except OSError as exc:
            # Loi mang khong co ma HTTP — `status=None` noi dung dieu do, khac han
            # voi `status=0` (se bi doc la "co ma, bang 0").
            raise CloudflareError(
                f"Cloudflare khong goi duoc ({type(exc).__name__})") from None

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
