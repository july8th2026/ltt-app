"""Signed OVH API transport; mutations have no implicit network retry."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from ipaddress import IPv4Address, IPv4Interface
import logging
import re
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)


class OvhError(RuntimeError):
    """OVH could not be read; response bodies are deliberately not exposed.

    `status` + `ma_loi` la **bo phan loai**, khong phai noi dung: mot ma HTTP va
    ma loi ngan cua OVH (`errorCode`/`class`). Than phan hoi van khong bao gio ra
    ngoai — no co the vong lai chinh yeu cau.

    🔴 Vi sao can: `_request` tung gop MOI HTTPError thanh mot cau duy nhat
       `OVH request failed (HTTPError)`. Trong MOT ngay 25/09/2026 dieu do gay ba
       trieu chung khac nhau:
         1. `409 already setted` (PTR da dung) khong phan biet duoc voi that bai;
         2. `403 credential is not valid` (khoa chet) bi doc thanh "khong co ban
            ghi reverse" — cong cu khai sai MOI IP;
         3. suc khoe ho so in `periodic preflight unavailable (OvhError)`, mot
            dong khong dan tới bat cu hanh dong nao — mat 6 phep do moi ra goc.
       Mot ma so ba ky tu tach ba trieu chung do ra.
    """

    def __init__(self, *args, status: int | None = None, ma_loi: str = ""):
        super().__init__(*args)
        self.status = status
        self.ma_loi = ma_loi


class CheckoutNotSent(OvhError):
    """Checkout was refused locally before any payment POST was issued."""


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


@dataclass(frozen=True)
class OvhPreparedIpCart:
    """Non-secret, validated cart evidence used by the acquisition journal."""

    cart_id: str
    item_id: int
    quantity: int
    with_tax_minor: int
    currency: str
    expires: str
    contracts: tuple[str, ...]
    contract_fingerprints: tuple[str, ...] = ()


@dataclass(frozen=True)
class OvhCatalogIpQuote:
    """Read-only catalog price; carries no contracts (checked at cart preview)."""

    quantity: int
    with_tax_minor: int
    currency: str
    contract_fingerprints: None = None


Transport = Callable[..., Any]


def _ma_loi_ovh(exc) -> str:
    """Chi doc `errorCode`/`class` tu than loi — ⛔ khong bao gio `message`.

    OVH dat cau tra loi tu do vao `message`, va cau do co khi vong lai chinh yeu
    cau (co the mang duong dan, tham so). `errorCode` va `class` la tu vung dong
    cua OVH (`INVALID_CREDENTIAL`, `Client::Forbidden`) nen an toan de ghi log.
    """
    try:
        than = exc.read(4096)
    except Exception as doc_loi:              # noqa: BLE001 - loi khong co than
        # `URLError`/`TimeoutError` khong co `.read()`; do la binh thuong, khong
        # phai su co. Nhung van khai ra: mot ham "doc ma loi" im lang tra rong la
        # dung cai lam ma loi bien mat, va ta dang o day vi chuyen do.
        # ⚠️ Chi TEN LOP — than loi cua nha cung cap khong duoc vao log.
        log.debug("OVH: khong doc duoc than loi (%s)", type(doc_loi).__name__)
        return ""
    try:
        doc = json.loads(than.decode("utf-8", "replace"))
    except (json.JSONDecodeError, AttributeError):
        return ""
    if not isinstance(doc, dict):
        return ""
    for khoa in ("errorCode", "class"):
        gia = doc.get(khoa)
        if isinstance(gia, str) and re.fullmatch(r"[A-Za-z_:]{1,60}", gia):
            return gia
    return ""


class OvhClient:
    def __init__(self, config: OvhConfig, *, transport: Transport | None = None):
        self.config = config.verify()
        self._transport = transport or self._request
        self._clock_offset: int | None = None

    @staticmethod
    def _request(method: str, url: str, headers: dict[str, str], data=None):
        try:
            with urlopen(Request(url, data=data, method=method,
                                 headers=headers), timeout=30) as response:
                body = response.read(2_000_001)
        except (HTTPError, URLError, TimeoutError) as exc:
            status = getattr(exc, "code", None)
            raise OvhError(f"OVH request failed ({type(exc).__name__})",
                           status=status if isinstance(status, int) else None,
                           ma_loi=_ma_loi_ovh(exc)) from None
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

    def post(self, path: str, payload: dict | None = None):
        """Sign exactly the bytes sent, and never repeat an ambiguous POST."""
        if (not (path == "/order/cart" or path.startswith("/order/cart/"))
                or ".." in path or "?" in path or "#" in path):
            raise OvhError("unsupported OVH mutation path")
        url = self.config.api_base + path
        body = json.dumps(payload or {}, separators=(",", ":"),
                          ensure_ascii=True).encode("ascii")
        timestamp = str(self._server_time())
        raw = "+".join((self.config.application_secret, self.config.consumer_key,
                        "POST", url, body.decode("ascii"), timestamp))
        headers = {
            "Content-Type": "application/json",
            "X-Ovh-Application": self.config.application_key,
            "X-Ovh-Consumer": self.config.consumer_key,
            "X-Ovh-Timestamp": timestamp,
            "X-Ovh-Signature": "$1$" + hashlib.sha1(raw.encode("utf-8")).hexdigest(),
        }
        return self._transport("POST", url, headers, body)

    def dat_reverse(self, address: str, ten: str) -> None:
        """Dat PTR cho MOT dia chi. OVH **doi forward-confirm** — xem `rdns.py`.

        Rao `post()` chi mo cho `/order/cart`; day la duong thu hai va **duy nhat**
        duoc mo them, voi mot path co dinh theo dia chi da kiem.
        """
        import ipaddress

        dia_chi = str(ipaddress.IPv4Address(str(address or "").strip()))
        ten = str(ten or "").strip().rstrip(".")
        if not ten or " " in ten or "/" in ten:
            raise OvhError("ten reverse khong hop le")
        khoi = quote(dia_chi + "/32", safe="")
        # ⭐ Idempotent, va no KHONG phai toi uu: OVH tra **409 "already setted"**
        #    khi PTR da dung, va `_request` gop moi HTTPError thanh mot `OvhError`
        #    khong mang ma so — nen "da dat roi" va "that bai" ra cung mot ket qua.
        #    Hoi truoc thi hai trang thai do tach ra duoc. (Cung khuon "hai trang
        #    thai gop thanh mot gia tri" da can sau lan trong ngay 24/09.)
        try:
            hien = self.get(f"/ip/{khoi}/reverse/{quote(dia_chi, safe='')}")
            if str((hien or {}).get("reverse", "")).rstrip(".") == ten:
                return
        except OvhError:
            pass          # chua co ban ghi nao — di tiep va dat
        # ⚠️ KHONG dau cham cuoi. Do that 25/09/2026: gui `...com.` thi OVH tra
        #    400 "Cannot check if ...com. resolves to <ip>" — mot thong diep
        #    **chi sai cho**: no day nguoi doc di tim loi o DNS (A record da
        #    resolve dung, kiem bang nslookup) trong khi loi nam o dinh dang ten.
        #    Cung mot ten khong dau cham: 200 OK ngay lap tuc.
        self._post_duong_khac(f"/ip/{khoi}/reverse",
                              {"ipReverse": dia_chi, "reverse": ten})

    def _post_duong_khac(self, path: str, payload: dict):
        """POST toi mot duong KHONG phai gio hang. Danh sach cho phep o day."""
        import re as _re

        if not _re.fullmatch(r"/ip/[0-9.%A-Fa-f]+/reverse", path):
            raise OvhError("unsupported OVH mutation path")
        url = self.config.api_base + path
        body = json.dumps(payload, separators=(",", ":"),
                          ensure_ascii=True).encode("ascii")
        timestamp = str(self._server_time())
        raw = "+".join((self.config.application_secret, self.config.consumer_key,
                        "POST", url, body.decode("ascii"), timestamp))
        return self._transport("POST", url, {
            "Content-Type": "application/json",
            "X-Ovh-Application": self.config.application_key,
            "X-Ovh-Consumer": self.config.consumer_key,
            "X-Ovh-Timestamp": timestamp,
            "X-Ovh-Signature": "$1$" + hashlib.sha1(raw.encode("utf-8")).hexdigest(),
        }, body)

    @staticmethod
    def ip_service_name(address: str) -> str:
        """OVH service identity of one Additional IPv4 (`ip-<address>` for /32).

        Same derivation the OVH Manager uses (`ovh/manager` ip-ip.service.js:
        `ip-${block === '32' ? ip : ipBlock}`).
        """
        return "ip-" + str(IPv4Address(address))

    def ip_renewal(self, address: str) -> dict:
        """Read `renew` + `expiration` of one IP service (read-only)."""
        info = self.get("/ip/service/" + quote(self.ip_service_name(address), safe="")
                        + "/serviceInfos")
        renew = (info or {}).get("renew") if isinstance(info, dict) else None
        if not isinstance(renew, dict) or type(renew.get("deleteAtExpiration")) is not bool:
            raise OvhError("OVH IP serviceInfos has invalid shape")
        return {"renew": dict(renew), "expiration": str(info.get("expiration") or "")}

    def set_ip_delete_at_expiration(self, address: str, value: bool) -> dict:
        """Stop (or restore) automatic renewal of one IP service; read back.

        `PUT .../serviceInfos` with `renew.deleteAtExpiration` is the documented
        non-renewal switch (community-verified live: imbue-ai/mngr client.py).
        The service keeps working until `expiration`; nothing is deleted now.
        """
        current = self.ip_renewal(address)
        if current["renew"]["deleteAtExpiration"] is value:
            return current
        path = ("/ip/service/" + quote(self.ip_service_name(address), safe="")
                + "/serviceInfos")
        self._signed("PUT", path, {"renew": {**current["renew"],
                                             "deleteAtExpiration": bool(value)}})
        after = self.ip_renewal(address)
        if after["renew"]["deleteAtExpiration"] is not value:
            raise OvhError("OVH IP renewal read-back did not match")
        return after

    def _signed(self, method: str, path: str, payload: dict):
        """Signed non-GET call limited to exact IP-service renewal paths."""
        if (method != "PUT" or not re.fullmatch(
                r"/ip/service/ip-\d{1,3}(?:\.\d{1,3}){3}/serviceInfos", path)):
            raise OvhError("unsupported OVH mutation path")
        url = self.config.api_base + path
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        timestamp = str(self._server_time())
        raw = "+".join((self.config.application_secret, self.config.consumer_key,
                        method, url, body.decode("ascii"), timestamp))
        headers = {
            "Content-Type": "application/json",
            "X-Ovh-Application": self.config.application_key,
            "X-Ovh-Consumer": self.config.consumer_key,
            "X-Ovh-Timestamp": timestamp,
            "X-Ovh-Signature": "$1$" + hashlib.sha1(raw.encode("utf-8")).hexdigest(),
        }
        return self._transport(method, url, headers, body)

    def health(self) -> bool:
        services = self.get("/vps")
        return isinstance(services, list) and self.config.service_name in services

    @staticmethod
    def _order_id(order_id):
        if type(order_id) is not int or order_id <= 0:
            raise OvhError("invalid OVH order identity")
        return str(order_id)

    def order_status(self, order_id):
        value = self.get("/me/order/" + self._order_id(order_id) + "/status")
        allowed = {"cancelled", "cancelling", "checking", "delivered",
                   "delivering", "documentsRequested", "notPaid", "unknown"}
        if not isinstance(value, str) or value not in allowed:
            raise OvhError("OVH order status has invalid shape")
        return value

    def order_ipv4(self, order_id):
        """Resolve exact order domain via IP-service identity, not label parsing."""
        prefix = "/me/order/" + self._order_id(order_id) + "/details"
        ids = self.get(prefix)
        if not isinstance(ids, list) or len(ids) > 100:
            raise OvhError("OVH order details have invalid shape")
        addresses = set()
        service_names = None
        for detail_id in ids:
            detail = self.get(prefix + "/" + self._order_id(detail_id))
            if not isinstance(detail, dict) or type(detail.get("cancelled")) is not bool:
                raise OvhError("OVH order detail has invalid shape")
            if detail["cancelled"]:
                continue
            domain = detail.get("domain")
            if not isinstance(domain, str):
                raise OvhError("OVH order domain has invalid shape")
            try:
                interface = IPv4Interface(domain)
            except ValueError:
                # Real Additional-IP orders use an internal IP-service domain.
                # Join exact API identities; never extract digits from a name
                # or assume a newly appeared inventory address belongs to us.
                if service_names is None:
                    names = self.get("/ip/service")
                    if (not isinstance(names, list) or len(names) > 1000
                            or any(not isinstance(name, str) for name in names)
                            or len(set(names)) != len(names)):
                        raise OvhError("OVH IP service identities have invalid shape") from None
                    service_names = set(names)
                if domain not in service_names:
                    continue
                service = self.get("/ip/service/" + quote(domain, safe=""))
                try:
                    interface = IPv4Interface(service["ip"])
                except (KeyError, TypeError, ValueError):
                    raise OvhError("OVH IP service address has invalid shape") from None
            if interface.network.prefixlen == 32:
                addresses.add(str(interface.ip))
        return sorted(addresses)

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
