"""Bounded acquisition coordinator; provider mutations never retry blindly.

This coordinator is not enabled in production until the signed provider driver,
order-to-IP attribution and gateway address installation pass their tests.
"""
from datetime import datetime, timezone
from ipaddress import IPv4Address
import time

from sqlalchemy import select, update

from apps.vps.services import billing, mutation_journal as journal
from apps.vps.services.backends.contracts import (
    BackendConflict, CapacityExhausted, PublicIpResource,
)
from apps.vps.tables import VpsExternalMutation, VpsInfrastructureProfile, VpsIp


class UnexpectedBilling(BackendConflict):
    pass


class AcquisitionNeedsReview(BackendConflict):
    pass


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
    return expected, ceiling


def ensure_free_ip(db, profile, *, instance, gateway_row, provider, gateway,
                   operation_id, sleep=time.sleep, max_polls=30):
    """Acquire one address; an ambiguous predecessor forbids another checkout.

    The caller must own the provisioning lease. The conditional journal claim
    additionally prevents two workers issuing the same checkout.
    """
    request, ceiling = acquisition_policy(profile)

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

    guard()
    row = journal.intent(db, operation_id=operation_id, instance=instance,
                         step="OVH_IP_ACQUIRE", request=request)
    db.commit()

    def review():
        journal.needs_review(db, row)
        db.commit()
        raise AcquisitionNeedsReview("OVH acquisition requires exact provider read-back")

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
        try:
            baseline = [item.cidr for item in provider.list_additional_ipv4()]
            metadata = {"baseline": baseline, "phase": "PREPARING"}
            row.provider_metadata = metadata
            db.commit()
            guard()
            prepared = provider.prepare_additional_ipv4(
                description=f"ltt-vps:{row.id}", quantity=1, **request)
            metadata = {**metadata, "cart_id": prepared.cart_id,
                        "item_id": prepared.item_id,
                        "with_tax_minor": prepared.with_tax_minor,
                        "currency": prepared.currency,
                        "expires": prepared.expires,
                        "contract_fingerprints": list(prepared.contract_fingerprints),
                        "phase": "PREPARED"}
            row.provider_metadata = metadata
            db.commit()
            if (prepared.quantity != 1 or prepared.currency != "USD"
                    or type(prepared.with_tax_minor) is not int
                    or not 0 < prepared.with_tax_minor <= ceiling):
                journal.failed(db, row, "UNEXPECTED_BILLING")
                db.commit()
                raise UnexpectedBilling("OVH quote does not match approved policy")
            guard()
            metadata = {**metadata, "phase": "CHECKOUT_REQUESTED"}
            row.provider_metadata = metadata
            db.commit()
            try:
                order_id = provider.checkout_cart(prepared.cart_id, expected=prepared)
            except Exception:
                order_id = provider.recover_order(
                    cart_id=prepared.cart_id, item_id=prepared.item_id)
            if type(order_id) is not int or order_id <= 0:
                review()
            metadata = {**metadata, "order_id": order_id, "phase": "ORDERED"}
            row.provider_metadata = metadata
            db.commit()
        except (UnexpectedBilling, AcquisitionNeedsReview):
            raise
        except Exception:
            review()
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
        for _ in range(max_polls):
            guard()
            if provider.order_status(metadata["order_id"]) != "delivered":
                sleep(2)
                continue
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
                           last_observed_at=datetime.now(timezone.utc),
                           provider_metadata={"order_id": metadata["order_id"]})
                db.add(ip)
            elif ip.infrastructure_profile_id != profile.id or ip.state != "FREE":
                review()
            journal.observed(db, row, external_ref=str(metadata["order_id"]))
            db.commit()
            return PublicIpResource(id=ip.id, address=address,
                                    provider_id=item.cidr, state="FREE")
    except AcquisitionNeedsReview:
        raise
    except Exception:
        review()
    review()
