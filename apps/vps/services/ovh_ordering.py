"""OVH Additional IP cart driver with explicit preview-before-checkout guards."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from uuid import UUID
from urllib.parse import urlencode

from apps.vps.services.ovh import (CheckoutNotSent, OvhCatalogIpQuote, OvhClient,
                                   OvhError, OvhPreparedIpCart)


class OvhOrderingClient(OvhClient):
    @staticmethod
    def _cart_id(value):
        try:
            return str(UUID(str(value)))
        except (ValueError, TypeError, AttributeError):
            raise OvhError("invalid OVH cart identity") from None

    def preview_cart(self, cart_id, item_id):
        prefix = "/order/cart/" + self._cart_id(cart_id)
        cart = self.get(prefix)
        if not isinstance(cart, dict) or cart.get("items") != [item_id]:
            raise OvhError("OVH cart must contain exactly one intended item")
        item = self.get(prefix + "/item/" + self._order_id(item_id))
        settings = item.get("settings", {}) if isinstance(item, dict) else {}
        if (type(settings.get("quantity")) is not int
                or settings["quantity"] != 1
                or settings.get("planCode") != "ip-failover-arin"
                or settings.get("pricingMode") != "default"
                or item.get("duration") != "P1M" or item.get("options") != []):
            raise OvhError("OVH cart product or quantity changed")
        configuration_ids = item.get("configurations")
        if not isinstance(configuration_ids, list) or len(configuration_ids) != 3:
            raise OvhError("OVH cart configuration is incomplete")
        actual = {}
        for configuration_id in configuration_ids:
            configuration = self.get(prefix + "/item/" + self._order_id(item_id)
                                     + "/configuration/" + self._order_id(configuration_id))
            label = configuration["label"]
            if label in actual:
                raise OvhError("OVH cart has duplicate configuration")
            actual[label] = configuration["value"]
        if actual != {"country": "SG", "datacenter": "SGP",
                      "destination": self.config.service_name}:
            raise OvhError("OVH cart destination or location changed")
        preview = self.get(prefix + "/checkout")
        try:
            price = preview["prices"]["withTax"]
            value = Decimal(str(price["value"])) * 100
            if (not value.is_finite() or value != value.to_integral_value()
                    or not 0 < value <= 500 or price["currencyCode"] != "USD"):
                raise OvhError("OVH cart price is outside the supported billing guard")
            expire = datetime.fromisoformat(cart["expire"].replace("Z", "+00:00"))
            if expire.tzinfo is None or expire <= datetime.now(timezone.utc):
                raise OvhError("OVH cart expired")
            contracts = tuple(contract["name"] for contract in preview["contracts"])
            if not contracts or any(not isinstance(name, str) for name in contracts):
                raise OvhError("OVH contracts have invalid shape")
            fingerprints = []
            for contract in preview["contracts"]:
                shape = {key: contract[key] for key in ("content", "name", "url")}
                if any(not isinstance(value, str) or not value for value in shape.values()):
                    raise OvhError("OVH contract contents are incomplete")
                fingerprints.append(hashlib.sha256(json.dumps(
                    shape, sort_keys=True, separators=(",", ":"),
                    ensure_ascii=True).encode("ascii")).hexdigest())
            return OvhPreparedIpCart(
                cart_id=self._cart_id(cart_id), item_id=item_id, quantity=1,
                with_tax_minor=int(value), currency="USD", expires=cart["expire"],
                contracts=contracts, contract_fingerprints=tuple(fingerprints))
        except (KeyError, TypeError, ValueError, InvalidOperation):
            raise OvhError("OVH cart preview has invalid shape") from None

    def catalog_additional_ipv4_quote(self, *, ip_plan_code, ip_country, ip_datacenter,
                                      ip_duration, ip_currency):
        """Read-only list price for ONE Additional IPv4 (R22, 17/09).

        Health must answer "can the worker buy an IP for the next VPS?" without
        creating carts every refresh. `GET /order/catalog/formatted/ip` is the
        public catalog (measured 17/09: ip-failover-arin, SG/SGP, USD 2.39/month,
        `priceInUcents` 239000000). Contracts are NOT in the catalog; the worker
        still validates the real cart preview and contract fingerprints before
        checkout, so this quote only opens capacity, never pays.
        """
        if (ip_plan_code != "ip-failover-arin" or ip_duration != "P1M"
                or ip_country != "SG" or ip_datacenter != "SGP" or ip_currency != "USD"):
            raise OvhError("unsupported OVH Additional IP catalog query")
        catalog = self.get("/order/catalog/formatted/ip?" + urlencode({"ovhSubsidiary": "ASIA"}))
        try:
            plans = [plan for plan in catalog["plans"] if plan.get("planCode") == ip_plan_code]
            if len(plans) != 1:
                raise OvhError("OVH catalog plan is missing or ambiguous")
            details = plans[0]["details"]
            options = {item["name"]: item["values"]
                       for item in details["product"]["configurations"]}
            if (ip_country not in options.get("country", ())
                    or ip_datacenter not in options.get("datacenter", ())):
                raise OvhError("OVH catalog no longer offers the configured location")
            monthly = [price for price in details["pricings"]["default"]
                       if price.get("intervalUnit") == "month" and price.get("interval") == 1
                       and "renew" in price.get("capacities", ())
                       and price["price"]["currencyCode"] == ip_currency]
            if len(monthly) != 1:
                raise OvhError("OVH catalog monthly price is missing or ambiguous")
            ucents = monthly[0]["priceInUcents"]
            if type(ucents) is not int or ucents <= 0 or ucents % 1_000_000:
                raise OvhError("OVH catalog price has invalid precision")
        except (KeyError, TypeError, AttributeError):
            raise OvhError("OVH catalog has invalid shape") from None
        return OvhCatalogIpQuote(quantity=1, with_tax_minor=ucents // 1_000_000,
                                 currency=ip_currency)

    def adopt_prepared_cart(self, cart_id):
        """Explicit operator-configured predecessor: GET only, no replacement."""
        cart_id = self._cart_id(cart_id)
        cart = self.get("/order/cart/" + cart_id)
        if (not isinstance(cart, dict) or not isinstance(cart.get("items"), list)
                or len(cart["items"]) != 1):
            raise OvhError("predecessor cart must contain exactly one item")
        return self.preview_cart(cart_id, cart["items"][0])

    def prepare_additional_ipv4(self, *, description, quantity, ip_plan_code,
                               ip_country, ip_datacenter, ip_duration, ip_currency):
        if (quantity != 1 or ip_plan_code != "ip-failover-arin"
                or ip_country != "SG" or ip_datacenter != "SGP"
                or ip_duration != "P1M" or ip_currency != "USD"
                or not description.startswith("ltt-vps:")):
            raise OvhError("unsupported OVH Additional IP order")
        found = self.get("/order/cart?" + urlencode({"description": description}))
        if not isinstance(found, list) or len(found) > 1:
            raise OvhError("OVH cart recovery is ambiguous")
        if found:
            cart_id = self._cart_id(found[0])
            cart = self.get("/order/cart/" + cart_id)
            items = cart.get("items", [])
            if len(items) != 1:
                raise OvhError("incomplete predecessor cart requires recovery")
            return self.preview_cart(cart_id, items[0])
        cart = self.post("/order/cart", {
            "ovhSubsidiary": "ASIA", "description": description})
        cart_id = self._cart_id(cart["cartId"])
        prefix = "/order/cart/" + cart_id
        self.post(prefix + "/assign")
        item = self.post(prefix + "/ip", {
            "planCode": ip_plan_code, "duration": ip_duration,
            "pricingMode": "default", "quantity": 1})
        item_id = item["itemId"]
        for label, value in (("country", ip_country), ("datacenter", ip_datacenter),
                             ("destination", self.config.service_name)):
            self.post(prefix + "/item/" + self._order_id(item_id) + "/configuration",
                      {"label": label, "value": value})
        return self.preview_cart(cart_id, item_id)

    def checkout_cart(self, cart_id, *, expected):
        """Expected preview is mandatory; any quote/contract change blocks POST."""
        try:
            current = self.preview_cart(cart_id, expected.item_id)
        except OvhError as exc:
            # Includes an expired cart: still before the payment POST.
            raise CheckoutNotSent("OVH cart preview unavailable before checkout") from exc
        if current != expected:
            raise CheckoutNotSent("OVH cart preview changed before checkout")
        result = self.post("/order/cart/" + current.cart_id + "/checkout", {
            "autoPayWithPreferredPaymentMethod": True,
            "waiveRetractationPeriod": True})
        order_id = result.get("orderId")
        self._order_id(order_id)
        return order_id

    def recover_order(self, *, cart_id, item_id):
        """Return the order created by a checkout whose response was lost, or None.

        OVH exposes no cart -> order link. `GET /order/cart/{id}/checkout` is the
        dry-run quotation (ovh/order-cart-examples, order-a-new-ip-address.py),
        never an order lookup: its `orderId` is not ours. Correlating by price,
        date, text or inventory delta is forbidden, so the honest answer is
        "unknown" and the caller escalates to NEEDS_REVIEW with the cart kept.
        """
        del cart_id, item_id
        return None
