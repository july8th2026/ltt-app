"""Bounded acquisition coordinator; provider mutations never retry blindly.

This coordinator is not enabled in production until the signed provider driver,
order-to-IP attribution and gateway address installation pass their tests.
"""
from datetime import datetime, timezone
from ipaddress import IPv4Address
import logging
from uuid import UUID

from sqlalchemy import select, update

from apps.vps.services import billing, mutation_journal as journal
from apps.vps.services.backends.contracts import (
    BackendConflict, CapacityExhausted, PublicIpResource,
)
from apps.vps.services.ovh import CheckoutNotSent
from apps.vps.tables import (VpsEvent, VpsExternalMutation,
                             VpsInfrastructureProfile, VpsIp)
from platform_core.jobs import DangBan

log = logging.getLogger(__name__)


class UnexpectedBilling(BackendConflict):
    pass


class AcquisitionNeedsReview(BackendConflict):
    pass


class OrderDeliveryPending(DangBan):
    """Paid order is processing; reuse platform deferred-job accounting."""

    def __init__(self):
        super().__init__("OVH order delivery is pending", retry_after_s=20)


def _now():
    return datetime.now(timezone.utc)


def reserve_for_provision(db, profile, *, pool, instance, gateway_row,
                          reservation_key, operation_id, provider_factory,
                          gateway_factory):
    """Prefer owned capacity; acquire at most once under the worker lease.

    Factories are lazy: disabled automatic capacity must not even access billing
    credentials. Gateway mapping remains in the existing PUBLIC_MAPPING journal.
    """
    arguments = {"reservation_key": reservation_key, "label": instance.id[:8]}
    try:
        return pool.reserve(**arguments)
    except CapacityExhausted:
        if (profile.public_ip_backend_type != "ovh_static_pool"
                or not pool.capabilities().dynamic_acquisition):
            raise
    ensure_free_ip(db, profile, instance=instance, gateway_row=gateway_row,
                   provider=provider_factory(), gateway=gateway_factory(),
                   operation_id=operation_id)
    # A second capacity race fails rather than buying another address.
    return pool.reserve(**arguments)


def acquisition_policy(profile):
    """Reject incomplete policy rather than inventing a spending allowance."""
    config = dict(profile.provider_config or {})
    expected = {
        "ip_plan_code": "ip-failover-arin", "ip_country": "SG",
        "ip_datacenter": "SGP", "ip_duration": "P1M", "ip_currency": "USD",
    }
    if config.get("auto_acquire") is not True:
        raise BackendConflict("automatic acquisition is not configured")
    if any(config.get(key) != value for key, value in expected.items()):
        raise UnexpectedBilling("OVH acquisition policy is incomplete or unsupported")
    ceiling = config.get("max_ip_with_tax_minor")
    if type(ceiling) is not int or not 0 < ceiling <= 500:
        raise UnexpectedBilling("OVH acquisition price ceiling is invalid")
    timeout = config.get("order_delivery_timeout_seconds", 3600)
    if type(timeout) is not int or timeout != 3600:
        raise UnexpectedBilling("OVH delivery deadline must match the 60-minute policy")
    expected["order_delivery_timeout_seconds"] = timeout
    if "accepted_contract_fingerprints" in config:
        expected["accepted_contract_fingerprints"] = config["accepted_contract_fingerprints"]
    if config.get("adopt_ip_cart_id"):
        try:
            expected["adopt_ip_cart_id"] = str(UUID(str(config["adopt_ip_cart_id"])))
        except (ValueError, TypeError, AttributeError):
            raise UnexpectedBilling("OVH predecessor cart identity is invalid") from None
    return expected, ceiling


def ensure_free_ip(db, profile, *, instance, gateway_row, provider, gateway,
                   operation_id, sleep=None, max_polls=1):
    """Acquire one address; an ambiguous predecessor forbids another checkout.

    The caller must own the provisioning lease. The conditional journal claim
    additionally prevents two workers issuing the same checkout.
    """
    request, ceiling = acquisition_policy(profile)
    # Kept as compatible arguments for existing test/caller injection. Provider
    # delivery is now read once per job claim, never a blocking polling loop.
    del sleep, max_polls

    def guard():
        db.refresh(instance)
        current = db.get(VpsInfrastructureProfile, profile.id)
        db.refresh(current)
        if (current.status == "DISABLED"
                or instance.infrastructure_profile_id != current.id
                or instance.profile_resolution_state != "PINNED"
                or instance.vmid in range(100, 108)
                or gateway_row.infrastructure_profile_id != current.id):
            raise BackendConflict("acquisition blocked by profile or protected scope")
        # Use the existing Q98 subscription authority. Buying provider IPs must
        # not create a second credit ledger or debit the customer twice.
        if not billing.con_han(instance):
            raise BackendConflict("acquisition requires a paid VPS subscription")
        # A refund does not move `paid_until` back (bao_tri._hoan_may_tao_hong),
        # so the subscription check alone would still buy for a refunded or
        # failed/deleted machine (review R4, 16/09).
        if instance.trang_thai in ("loi", "da_xoa"):
            raise BackendConflict("acquisition refused for a failed or deleted VPS")
        if db.execute(select(VpsEvent.id).where(
                VpsEvent.instance_id == instance.id,
                VpsEvent.loai == "hoan_tien").limit(1)).first() is not None:
            raise BackendConflict("acquisition refused for a refunded VPS")

    guard()
    # One purchase per instance across ALL operations. A rebuild gets a new
    # operation_id; without this it would reuse the cart claim and could POST
    # checkout for the same cart again (review R3, 16/09). Only a predecessor
    # that provably never reached checkout (FAILED/COMPENSATED) is ignored.
    for other in db.execute(select(VpsExternalMutation).where(
            VpsExternalMutation.instance_id == instance.id,
            VpsExternalMutation.step == "OVH_IP_ACQUIRE",
            VpsExternalMutation.operation_id != operation_id)).scalars():
        if other.state not in ("FAILED", "COMPENSATED") or (
                (other.provider_metadata or {}).get("phase")
                in ("CHECKOUT_REQUESTED", "ORDERED")):
            raise AcquisitionNeedsReview(
                "an earlier acquisition for this VPS may already have paid")
    cart_claim = None
    if request.get("adopt_ip_cart_id"):
        # One durable cart claim across ALL instance/operation IDs. The journal
        # unique key plus exact-instance validation prevents a second worker
        # assigning the same live cart to another customer or profile.
        cart_claim = journal.intent(
            db, operation_id="ovh-cart:" + request["adopt_ip_cart_id"],
            instance=instance, step="OVH_CART_CLAIM",
            request={"cart_id": request["adopt_ip_cart_id"]})
        db.commit()
    row = journal.intent(db, operation_id=operation_id, instance=instance,
                         step="OVH_IP_ACQUIRE", request=request)
    db.commit()

    def review(keep_metadata=None):
        # The session may be broken by the failure that brought us here; a
        # review written on it would fail and replace the real error, losing a
        # paid order_id (review R7). Roll back, then persist what we know.
        db.rollback()
        if keep_metadata is not None:
            row.provider_metadata = keep_metadata
        journal.needs_review(db, row)
        db.commit()
        raise AcquisitionNeedsReview("OVH acquisition requires exact provider read-back")

    def not_sent(metadata_before_checkout):
        # Nothing was paid: release the claim so the job may retry safely,
        # instead of a permanent NEEDS_REVIEW for a failure before POST (R5).
        db.rollback()
        row.state = "INTENT"
        row.provider_metadata = metadata_before_checkout
        row.last_error_code = "pre_checkout_failure"
        db.commit()

    if row.state in ("FAILED", "COMPENSATED", "NEEDS_REVIEW"):
        raise AcquisitionNeedsReview("OVH acquisition predecessor requires recovery")
    metadata = dict(row.provider_metadata or {})
    if row.state == "INTENT":
        claimed = db.execute(update(VpsExternalMutation).where(
            VpsExternalMutation.id == row.id,
            VpsExternalMutation.state == "INTENT",
        ).values(state="REQUESTED", attempts=VpsExternalMutation.attempts + 1))
        if claimed.rowcount != 1:
            db.rollback()
            raise AcquisitionNeedsReview("another worker owns acquisition")
        db.commit()
        metadata = {}
        try:
            baseline = [item.cidr for item in provider.list_additional_ipv4()]
            metadata = {"baseline": baseline, "phase": "PREPARING"}
            row.provider_metadata = metadata
            db.commit()
            guard()
            if request.get("adopt_ip_cart_id"):
                prepared = provider.adopt_prepared_cart(request["adopt_ip_cart_id"])
            else:
                prepared = provider.prepare_additional_ipv4(
                    description=f"ltt-vps:{row.id}", quantity=1,
                    **{key: value for key, value in request.items()
                       if key not in ("order_delivery_timeout_seconds",
                                      "accepted_contract_fingerprints")})
            metadata = {**metadata, "cart_id": prepared.cart_id,
                        "item_id": prepared.item_id,
                        "with_tax_minor": prepared.with_tax_minor,
                        "currency": prepared.currency,
                        "expires": prepared.expires,
                        "contract_fingerprints": list(prepared.contract_fingerprints),
                        "phase": "PREPARED"}
            row.provider_metadata = metadata
            if cart_claim is not None:
                journal.observed(db, cart_claim, external_ref=prepared.cart_id)
            db.commit()
            if (prepared.quantity != 1 or prepared.currency != "USD"
                    or type(prepared.with_tax_minor) is not int
                    or not 0 < prepared.with_tax_minor <= ceiling
                    or ("accepted_contract_fingerprints" in profile.provider_config
                        and list(prepared.contract_fingerprints) !=
                        profile.provider_config["accepted_contract_fingerprints"])):
                journal.failed(db, row, "UNEXPECTED_BILLING")
                db.commit()
                raise UnexpectedBilling("OVH quote does not match approved policy")
            guard()
        except (UnexpectedBilling, AcquisitionNeedsReview):
            raise
        except Exception as exc:
            # Everything above is read-only or an unpaid cart: never "ambiguous".
            not_sent(metadata)
            raise BackendConflict("OVH acquisition stopped before checkout") from exc

        prepared_metadata = metadata
        metadata = {**metadata, "phase": "CHECKOUT_REQUESTED",
                    "checkout_requested_at": _now().isoformat()}
        row.provider_metadata = metadata
        db.commit()
        try:
            order_id = provider.checkout_cart(prepared.cart_id, expected=prepared)
        except CheckoutNotSent as exc:
            # The driver proves the POST was never issued (quote/expiry changed).
            not_sent(prepared_metadata)
            raise BackendConflict("OVH cart changed before checkout") from exc
        except Exception:
            try:
                order_id = provider.recover_order(
                    cart_id=prepared.cart_id, item_id=prepared.item_id)
            except Exception:
                order_id = None
        if type(order_id) is not int or order_id <= 0:
            review(keep_metadata=metadata)
        metadata = {**metadata, "order_id": order_id, "phase": "ORDERED"}
        row.provider_metadata = metadata
        try:
            db.commit()
        except Exception:
            log.error("OVH checkout order %s could not be journaled; cart %s",
                      order_id, prepared.cart_id)
            review(keep_metadata=metadata)
    elif not metadata.get("order_id"):
        # Crash after checkout may leave only the durable cart identity. Recover
        # using read-only attribution, never by issuing a second checkout.
        if metadata.get("phase") != "CHECKOUT_REQUESTED":
            review()
        try:
            order_id = provider.recover_order(
                cart_id=metadata["cart_id"], item_id=metadata["item_id"])
        except Exception:
            review()
        if type(order_id) is not int or order_id <= 0:
            review()
        metadata = {**metadata, "order_id": order_id, "phase": "ORDERED"}
        row.provider_metadata = metadata
        db.commit()

    try:
        guard()
        status = provider.order_status(metadata["order_id"])
        if status != "delivered":
            if status not in ("checking", "delivering"):
                review()
            try:
                requested_at = datetime.fromisoformat(metadata["checkout_requested_at"])
                age = (_now() - requested_at).total_seconds()
            except (KeyError, TypeError, ValueError):
                review()
            if not 0 <= age < request["order_delivery_timeout_seconds"]:
                review()
            raise OrderDeliveryPending()
        mappings = gateway.list_mappings()
        ordered_addresses = provider.order_ipv4(metadata["order_id"])
        if len(ordered_addresses) != 1:
            review()
        candidates = [item for item in provider.list_additional_ipv4()
                      if item.cidr not in metadata["baseline"]
                      and item.kind == "failover"
                      and item.country.lower() == "sg"
                      and item.routed_to == provider.config.service_name
                      and item.address == ordered_addresses[0]
                      and item.address not in mappings]
        # Inventory delta AND exact order service identity are required.
        if len(candidates) != 1:
            review()
        item = candidates[0]
        address = str(IPv4Address(item.address))
        if item.cidr != address + "/32":
            review()
        ip = db.execute(select(VpsIp).where(
            VpsIp.gateway_id == gateway_row.id,
            VpsIp.dia_chi == address).with_for_update()).scalar_one_or_none()
        if ip is None:
            ip = VpsIp(infrastructure_profile_id=profile.id,
                       gateway_id=gateway_row.id, dia_chi=address,
                       backend_resource_id=item.cidr, state="FREE",
                       billing_mode="monthly",
                       monthly_cost_minor=metadata["with_tax_minor"],
                       last_observed_at=_now(),
                       provider_metadata={"order_id": metadata["order_id"]})
            db.add(ip)
        elif ip.infrastructure_profile_id != profile.id or ip.state != "FREE":
            review()
        journal.observed(db, row, external_ref=str(metadata["order_id"]))
        db.commit()
        return PublicIpResource(id=ip.id, address=address,
                                provider_id=item.cidr, state="FREE")
    except (AcquisitionNeedsReview, OrderDeliveryPending):
        raise
    except Exception:
        review()
