"""OVH Additional IPv4 acquisition is automatic, bounded and recoverable."""
from types import SimpleNamespace
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from platform_core.db import Base


@pytest.fixture()
def db():
    import platform_core.models as _models  # noqa: F401
    from apps.vps import tables as _tables  # noqa: F401

    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _domain(db):
    from apps.vps.tables import VpsGateway, VpsInfrastructureProfile, VpsInstance

    profile = VpsInfrastructureProfile(
        id="profile-ovh", slug="ovh-sgp-prod", name="OVH", region="sgp",
        status="ACTIVE", accept_new=True, is_default=True,
        compute_backend_type="proxmox", public_ip_backend_type="ovh_static_pool",
        gateway_backend_type="nft", credential_ref="LTT_OVH",
        provider_config={
            "auto_acquire": True,
            "ip_plan_code": "ip-failover-arin",
            "ip_country": "SG",
            "ip_datacenter": "SGP",
            "ip_duration": "P1M",
            "ip_currency": "USD",
            "max_ip_with_tax_minor": 500,
            "order_delivery_timeout_seconds": 3600,
        },
    )
    gateway = VpsGateway(
        id="gateway-ovh", infrastructure_profile_id=profile.id,
        ten="OVH gateway", vung="sgp", ip_cong_khai="192.0.2.1",
    )
    instance = VpsInstance(
        id="instance-new", user_id="owner", plan_id="vps-nho", os_id="win10",
        gateway_id=gateway.id, infrastructure_profile_id=profile.id,
        profile_resolution_state="PINNED", vmid=208,
        paid_until=datetime(2099, 1, 1, tzinfo=timezone.utc),
    )
    db.add_all((profile, gateway, instance))
    db.commit()
    return profile, gateway, instance


class _Provider:
    def __init__(self, *, quote_minor=239, checkout_error=False, recovered=None):
        self.config = SimpleNamespace(service_name="vps-fixture")
        self.quote_minor = quote_minor
        self.checkout_error = checkout_error
        self.recovered = recovered
        self.calls = []
        self.delivered = False

    def list_additional_ipv4(self):
        from apps.vps.services.ovh import OvhIpObservation
        rows = [OvhIpObservation(
            cidr="192.0.2.10/32", address="192.0.2.10", kind="failover",
            country="sg", routed_to="vps-fixture")]
        if self.delivered:
            rows.append(OvhIpObservation(
                cidr="192.0.2.11/32", address="192.0.2.11", kind="failover",
                country="sg", routed_to="vps-fixture"))
        return rows

    def prepare_additional_ipv4(self, **request):
        from apps.vps.services.ovh import OvhPreparedIpCart
        self.calls.append(("prepare", request))
        return OvhPreparedIpCart(
            cart_id="11111111-1111-4111-8111-111111111111", item_id=77,
            quantity=1, with_tax_minor=self.quote_minor, currency="USD",
            expires="2099-01-01T00:00:00Z", contracts=("Cloud Base",),
            contract_fingerprints=("a" * 64,),
        )

    def checkout_cart(self, cart_id, *, expected):
        from apps.vps.services.ovh import OvhError
        assert expected.cart_id == cart_id and expected.with_tax_minor == self.quote_minor
        self.calls.append(("checkout", cart_id))
        if self.checkout_error:
            raise OvhError("fixture response lost")
        self.delivered = True
        return 9001

    def recover_order(self, *, cart_id, item_id):
        self.calls.append(("recover", cart_id, item_id))
        if self.recovered:
            self.delivered = True
        return self.recovered

    def order_status(self, order_id):
        self.calls.append(("status", order_id))
        return "delivered" if self.delivered else "delivering"

    def order_ipv4(self, order_id):
        return ["192.0.2.11"] if self.delivered else []


class _Gateway:
    def list_mappings(self):
        return {"192.0.2.10": "10.50.0.11"}


def test_delivery_in_progress_defers_without_review_or_duplicate_checkout(db):
    from apps.vps.services.ovh_acquisition import OrderDeliveryPending, ensure_free_ip
    from apps.vps.tables import VpsExternalMutation
    from platform_core.jobs import DangBan

    profile, gateway, instance = _domain(db)
    provider = _Provider()
    provider.order_status = lambda _: "delivering"
    arguments = dict(instance=instance, gateway_row=gateway, provider=provider,
                     gateway=_Gateway(), operation_id="slow-delivery", max_polls=1,
                     sleep=lambda _: pytest.fail("worker must not block on delivery"))
    for _ in range(2):
        with pytest.raises(OrderDeliveryPending) as caught:
            ensure_free_ip(db, profile, **arguments)
        assert isinstance(caught.value, DangBan)
    row = db.execute(select(VpsExternalMutation)).scalar_one()
    assert row.state == "REQUESTED" and row.provider_metadata["phase"] == "ORDERED"
    assert [call[0] for call in provider.calls].count("checkout") == 1
    provider.order_status = lambda _: "delivered"
    assert ensure_free_ip(db, profile, **arguments).address == "192.0.2.11"


def test_delivery_deadline_is_durable_and_does_not_restart_on_retry(db, monkeypatch):
    from datetime import timedelta
    from apps.vps.services import ovh_acquisition as acquisition
    from apps.vps.tables import VpsExternalMutation

    profile, gateway, instance = _domain(db)
    provider = _Provider()
    provider.order_status = lambda _: "delivering"
    first = datetime(2026, 9, 14, tzinfo=timezone.utc)
    monkeypatch.setattr(acquisition, "_now", lambda: first)
    arguments = dict(instance=instance, gateway_row=gateway, provider=provider,
                     gateway=_Gateway(), operation_id="deadline", max_polls=1,
                     sleep=lambda _: None)
    with pytest.raises(acquisition.OrderDeliveryPending):
        acquisition.ensure_free_ip(db, profile, **arguments)
    monkeypatch.setattr(acquisition, "_now", lambda: first + timedelta(seconds=3601))
    with pytest.raises(acquisition.AcquisitionNeedsReview):
        acquisition.ensure_free_ip(db, profile, **arguments)
    assert db.execute(select(VpsExternalMutation.state)).scalar_one() == "NEEDS_REVIEW"
    assert [call[0] for call in provider.calls].count("checkout") == 1


def test_pending_delivery_is_not_marked_as_instance_error_by_worker(db, monkeypatch):
    from apps.vps import jobs
    from apps.vps.services.ovh_acquisition import OrderDeliveryPending

    _, _, instance = _domain(db)
    closed = []
    monkeypatch.setattr(jobs, "_mo_db", lambda: (db, SimpleNamespace(close=lambda: closed.append(True))))
    monkeypatch.setattr(jobs, "_lay_may", lambda _db, _id: instance)

    def pending(_db, _instance):
        raise OrderDeliveryPending()

    monkeypatch.setattr(jobs, "_profile_for_job", pending)
    monkeypatch.setattr(jobs, "_danh_dau_loi", lambda *_args: pytest.fail(
        "a paid order still delivering must not mark the VPS as failed"))
    with pytest.raises(OrderDeliveryPending):
        jobs._tao_may({"instance_id": instance.id})
    assert closed == [True]


def test_pending_delivery_uses_core_queue_without_consuming_attempt_or_credit(db):
    from apps.vps.services.ovh_acquisition import OrderDeliveryPending
    from platform_core import job_runner, jobs
    from platform_core.models import CreditEntry, Job

    job = Job(id="pending-job", user_id="owner", app_slug="vps",
              job_type="vps.provision", status="running", attempts=2,
              worker_id="fixture-worker")
    db.add(job)
    db.commit()
    before = db.execute(select(CreditEntry)).scalars().all()
    kind, delay = job_runner._provider_failure_kind(
        OrderDeliveryPending(), provider_state="")
    assert kind == "resource_wait" and delay == 20
    jobs.defer_resource(db, job, retry_after=delay)
    db.commit()
    db.refresh(job)
    assert job.status == "queued" and job.attempts == 2 and job.worker_id == ""
    assert db.execute(select(CreditEntry)).scalars().all() == before


def test_web_acquisition_checks_out_one_ip_and_imports_provider_readback(db):
    from apps.vps.services.ovh_acquisition import ensure_free_ip
    from apps.vps.tables import VpsExternalMutation, VpsIp

    profile, gateway, instance = _domain(db)
    provider = _Provider()
    result = ensure_free_ip(
        db, profile, instance=instance, gateway_row=gateway,
        provider=provider, gateway=_Gateway(), operation_id="provision:instance-new",
        sleep=lambda _seconds: None,
    )

    assert result.address == "192.0.2.11"
    assert [call[0] for call in provider.calls].count("checkout") == 1
    row = db.execute(select(VpsExternalMutation)).scalar_one()
    assert row.state == "OBSERVED"
    assert row.provider_metadata["order_id"] == 9001
    ip = db.execute(select(VpsIp).where(VpsIp.dia_chi == "192.0.2.11")).scalar_one()
    assert ip.state == "FREE" and ip.monthly_cost_minor == 239


def test_unexpected_quote_fails_before_checkout(db):
    from apps.vps.services.ovh_acquisition import UnexpectedBilling, ensure_free_ip
    from apps.vps.tables import VpsExternalMutation

    profile, gateway, instance = _domain(db)
    provider = _Provider(quote_minor=501)
    with pytest.raises(UnexpectedBilling):
        ensure_free_ip(
            db, profile, instance=instance, gateway_row=gateway,
            provider=provider, gateway=_Gateway(), operation_id="provision:instance-new",
            sleep=lambda _seconds: None,
        )
    assert not any(call[0] == "checkout" for call in provider.calls)
    row = db.execute(select(VpsExternalMutation)).scalar_one()
    assert row.state == "FAILED" and row.last_error_code == "UNEXPECTED_BILLING"


def test_lost_checkout_response_never_repeats_purchase_without_recovery(db):
    from apps.vps.services.ovh_acquisition import AcquisitionNeedsReview, ensure_free_ip
    from apps.vps.tables import VpsExternalMutation

    profile, gateway, instance = _domain(db)
    provider = _Provider(checkout_error=True, recovered=None)
    with pytest.raises(AcquisitionNeedsReview):
        ensure_free_ip(
            db, profile, instance=instance, gateway_row=gateway,
            provider=provider, gateway=_Gateway(), operation_id="provision:instance-new",
            sleep=lambda _seconds: None,
        )
    with pytest.raises(AcquisitionNeedsReview):
        ensure_free_ip(
            db, profile, instance=instance, gateway_row=gateway,
            provider=provider, gateway=_Gateway(), operation_id="provision:instance-new",
            sleep=lambda _seconds: None,
        )
    assert [call[0] for call in provider.calls].count("checkout") == 1
    assert db.execute(select(VpsExternalMutation.state)).scalar_one() == "NEEDS_REVIEW"


def test_lost_checkout_response_adopts_exact_recovered_order(db):
    from apps.vps.services.ovh_acquisition import ensure_free_ip

    profile, gateway, instance = _domain(db)
    provider = _Provider(checkout_error=True, recovered=9002)
    result = ensure_free_ip(
        db, profile, instance=instance, gateway_row=gateway,
        provider=provider, gateway=_Gateway(), operation_id="provision:instance-new",
        sleep=lambda _seconds: None,
    )
    assert result.address == "192.0.2.11"
    assert [call[0] for call in provider.calls].count("checkout") == 1


@pytest.mark.parametrize("blocked", ["protected", "disabled", "wrong_gateway",
                                     "unpaid", "expired"])
def test_acquisition_refuses_protected_or_invalid_scope_before_provider(db, blocked):
    from apps.vps.services.ovh_acquisition import ensure_free_ip
    from apps.vps.services.backends.contracts import BackendConflict

    profile, gateway, instance = _domain(db)
    if blocked == "protected":
        instance.vmid = 100
    elif blocked == "disabled":
        profile.status = "DISABLED"
        profile.accept_new = profile.is_default = False
    elif blocked == "wrong_gateway":
        gateway.infrastructure_profile_id = "other-profile"
    elif blocked == "unpaid":
        instance.paid_until = None
    else:
        instance.paid_until = datetime(2000, 1, 1, tzinfo=timezone.utc)
    db.commit()
    provider = _Provider()
    with pytest.raises(BackendConflict):
        ensure_free_ip(db, profile, instance=instance, gateway_row=gateway,
                       provider=provider, gateway=_Gateway(), operation_id="scope-check",
                       sleep=lambda _seconds: None)
    assert provider.calls == []


def test_subscription_revoked_during_cart_preparation_blocks_checkout(db):
    from apps.vps.services.backends.contracts import BackendConflict
    from apps.vps.services.ovh_acquisition import ensure_free_ip
    from apps.vps.tables import VpsExternalMutation

    profile, gateway, instance = _domain(db)
    provider = _Provider()
    prepare = provider.prepare_additional_ipv4

    def revoke(**request):
        prepared = prepare(**request)
        instance.paid_until = None
        db.commit()
        return prepared

    provider.prepare_additional_ipv4 = revoke
    with pytest.raises(BackendConflict):
        ensure_free_ip(db, profile, instance=instance, gateway_row=gateway,
                       provider=provider, gateway=_Gateway(), operation_id="revoked",
                       sleep=lambda _: None)
    assert not any(call[0] == "checkout" for call in provider.calls)
    # Nothing was paid, so this is a safe stop, not an ambiguous outcome (R5).
    assert db.execute(select(VpsExternalMutation.state)).scalar_one() == "INTENT"


@pytest.mark.parametrize("state", ["loi", "da_xoa", "refunded"])
def test_acquisition_refuses_failed_deleted_or_refunded_vps(db, state):
    """R4: a refund does not move paid_until back, so billing alone is not enough."""
    from apps.vps.services.backends.contracts import BackendConflict
    from apps.vps.services.ovh_acquisition import ensure_free_ip
    from apps.vps.tables import VpsEvent

    profile, gateway, instance = _domain(db)
    if state == "refunded":
        db.add(VpsEvent(instance_id=instance.id, loai="hoan_tien", chi_tiet={}))
    else:
        instance.trang_thai = state
    db.commit()
    provider = _Provider()
    with pytest.raises(BackendConflict):
        ensure_free_ip(db, profile, instance=instance, gateway_row=gateway,
                       provider=provider, gateway=_Gateway(), operation_id="late-retry",
                       sleep=lambda _: None)
    assert provider.calls == []


def test_rebuild_after_ambiguous_checkout_never_checks_out_again(db):
    """R3: a rebuild's new operation_id must not reach a second checkout."""
    from apps.vps.services.ovh_acquisition import AcquisitionNeedsReview, ensure_free_ip

    profile, gateway, instance = _domain(db)
    profile.provider_config = {**profile.provider_config,
                               "adopt_ip_cart_id": "11111111-1111-4111-8111-111111111111"}
    db.commit()
    provider = _Provider(checkout_error=True, recovered=None)
    provider.adopt_prepared_cart = lambda cart_id: provider.prepare_additional_ipv4()
    with pytest.raises(AcquisitionNeedsReview):
        ensure_free_ip(db, profile, instance=instance, gateway_row=gateway,
                       provider=provider, gateway=_Gateway(),
                       operation_id="provision:instance-new", sleep=lambda _: None)
    with pytest.raises(AcquisitionNeedsReview):
        ensure_free_ip(db, profile, instance=instance, gateway_row=gateway,
                       provider=provider, gateway=_Gateway(),
                       operation_id="rebuild:new-uuid", sleep=lambda _: None)
    assert [call[0] for call in provider.calls].count("checkout") == 1


def test_cart_changed_before_post_is_not_ambiguous_and_retry_is_allowed(db):
    """R5: the driver proves no POST was sent, so the claim is released."""
    from apps.vps.services.backends.contracts import BackendConflict
    from apps.vps.services.ovh import CheckoutNotSent
    from apps.vps.services.ovh_acquisition import ensure_free_ip
    from apps.vps.tables import VpsExternalMutation

    profile, gateway, instance = _domain(db)
    provider = _Provider()
    real_checkout = provider.checkout_cart

    def expired_once(cart_id, *, expected):
        provider.checkout_cart = real_checkout
        raise CheckoutNotSent("fixture cart expired")

    provider.checkout_cart = expired_once
    arguments = dict(instance=instance, gateway_row=gateway, provider=provider,
                     gateway=_Gateway(), operation_id="provision:instance-new",
                     sleep=lambda _: None)
    with pytest.raises(BackendConflict):
        ensure_free_ip(db, profile, **arguments)
    row = db.execute(select(VpsExternalMutation)).scalar_one()
    assert row.state == "INTENT" and row.provider_metadata["phase"] == "PREPARED"
    assert ensure_free_ip(db, profile, **arguments).address == "192.0.2.11"
    assert [call[0] for call in provider.calls].count("checkout") == 1


def test_driver_recovery_never_uses_the_dry_run_quotation():
    """R2: GET /order/cart/{id}/checkout is a quotation, not an order lookup."""
    driver, cart_id, state, calls = _ordering_driver()
    assert driver.recover_order(cart_id=cart_id, item_id=77) is None
    assert calls == []


def test_driver_expired_cart_before_post_is_reported_as_not_sent():
    from apps.vps.services.ovh import CheckoutNotSent

    driver, cart_id, state, calls = _ordering_driver()
    expected = driver.preview_cart(cart_id, 77)
    state["price"] = "2.40"
    with pytest.raises(CheckoutNotSent):
        driver.checkout_cart(cart_id, expected=expected)
    assert not any(method == "POST" for method, _, _ in calls)


def test_completed_acquisition_retry_does_not_buy_a_second_address(db):
    from apps.vps.services.ovh_acquisition import ensure_free_ip

    profile, gateway, instance = _domain(db)
    provider = _Provider()
    arguments = dict(instance=instance, gateway_row=gateway, provider=provider,
                     gateway=_Gateway(), operation_id="same-operation",
                     sleep=lambda _seconds: None)
    first = ensure_free_ip(db, profile, **arguments)
    second = ensure_free_ip(db, profile, **arguments)
    assert second.id == first.id
    assert [call[0] for call in provider.calls].count("checkout") == 1


def test_restart_after_checkout_recovers_without_any_new_purchase(db):
    from apps.vps.services import mutation_journal as journal
    from apps.vps.services.ovh_acquisition import acquisition_policy, ensure_free_ip

    profile, gateway, instance = _domain(db)
    request, _ = acquisition_policy(profile)
    row = journal.intent(db, operation_id="crashed-operation", instance=instance,
                         step="OVH_IP_ACQUIRE", request=request)
    row.state = "REQUESTED"
    row.provider_metadata = {
        "phase": "CHECKOUT_REQUESTED", "cart_id": "fixture-cart", "item_id": 77,
        "baseline": ["192.0.2.10/32"], "with_tax_minor": 239,
    }
    db.commit()
    provider = _Provider(recovered=9001)
    result = ensure_free_ip(db, profile, instance=instance, gateway_row=gateway,
                            provider=provider, gateway=_Gateway(),
                            operation_id="crashed-operation", sleep=lambda _: None)
    assert result.address == "192.0.2.11"
    assert not any(call[0] in ("prepare", "checkout") for call in provider.calls)
    assert row.state == "OBSERVED" and row.provider_metadata["order_id"] == 9001


def test_reserving_acquired_address_preserves_provider_order_evidence(db):
    from apps.vps.services.backends.public_ip import OvhStaticIpPoolBackend
    from apps.vps.tables import VpsIp

    profile, gateway, _ = _domain(db)
    ip = VpsIp(infrastructure_profile_id=profile.id, gateway_id=gateway.id,
               dia_chi="192.0.2.11", state="FREE",
               provider_metadata={"order_id": 9001})
    db.add(ip)
    db.commit()
    resource = OvhStaticIpPoolBackend(db, profile).reserve(
        reservation_key="provision:instance-new", label="new-vps")
    db.refresh(ip)
    assert resource.id == ip.id and ip.state == "RESERVED"
    assert ip.provider_metadata == {"order_id": 9001, "allocation_label": "new-vps"}


def test_worker_reservation_with_disabled_acquisition_never_loads_provider(db):
    from apps.vps.services.backends.public_ip import OvhStaticIpPoolBackend
    from apps.vps.services.backends.contracts import CapacityExhausted
    from apps.vps.services.ovh_acquisition import reserve_for_provision

    profile, gateway, instance = _domain(db)

    def forbidden():
        pytest.fail("disabled acquisition must not load billing credentials")

    with pytest.raises(CapacityExhausted):
        reserve_for_provision(db, profile, pool=OvhStaticIpPoolBackend(db, profile),
                              instance=instance, gateway_row=gateway,
                              reservation_key="disabled", operation_id="disabled",
                              provider_factory=forbidden, gateway_factory=forbidden)


def test_worker_reservation_buys_once_then_reserves_exact_imported_ip(db):
    from apps.vps.services.backends.public_ip import OvhStaticIpPoolBackend
    from apps.vps.services.ovh_acquisition import reserve_for_provision

    profile, gateway, instance = _domain(db)
    pool = OvhStaticIpPoolBackend(db, profile)
    # Test-only injection; production backend intentionally remains disabled.
    pool.auto_acquire = True
    provider = _Provider()
    result = reserve_for_provision(
        db, profile, pool=pool, instance=instance, gateway_row=gateway,
        reservation_key="worker-reserve", operation_id="worker-operation",
        provider_factory=lambda: provider, gateway_factory=_Gateway)
    assert result.address == "192.0.2.11" and result.state == "RESERVED"
    assert [call[0] for call in provider.calls].count("checkout") == 1


def test_signed_post_hashes_exact_transmitted_body_and_never_retries(monkeypatch):
    import hashlib
    from apps.vps.services.ovh import OvhClient, OvhConfig, OvhError

    monkeypatch.setattr("apps.vps.services.ovh.time.time", lambda: 2000000000)
    calls = []

    def transport(method, url, headers, body=None):
        if method == "GET":
            return 2000000000
        calls.append((method, url, headers, body))
        raise OvhError("fixture connection lost")

    client = OvhClient(OvhConfig(
        application_key="fixture-ak", application_secret="fixture-as",
        consumer_key="fixture-ck", service_name="fixture-service"), transport=transport)
    with pytest.raises(OvhError):
        client.post("/order/cart", {"description": "fixture"})
    assert len(calls) == 1
    method, url, headers, body = calls[0]
    independent = "+".join(("fixture-as", "fixture-ck", method, url,
                            body.decode("ascii"), "2000000000"))
    assert headers["X-Ovh-Signature"] == (
        "$1$" + hashlib.sha1(independent.encode("utf-8")).hexdigest())


def test_inventory_delta_without_order_ownership_is_never_imported(db):
    from apps.vps.services.ovh_acquisition import AcquisitionNeedsReview, ensure_free_ip
    from apps.vps.tables import VpsIp

    profile, gateway, instance = _domain(db)
    provider = _Provider()
    provider.order_ipv4 = lambda order_id: ["192.0.2.99"]
    with pytest.raises(AcquisitionNeedsReview):
        ensure_free_ip(db, profile, instance=instance, gateway_row=gateway,
                       provider=provider, gateway=_Gateway(), operation_id="wrong-order",
                       sleep=lambda _seconds: None)
    assert db.execute(select(VpsIp)).scalars().all() == []


def test_order_reader_uses_exact_domains_not_description_substrings():
    from apps.vps.services.ovh import OvhClient, OvhConfig

    def transport(method, url, headers):
        if url.endswith("/auth/time"):
            return 2000000000
        if url.endswith("/status"):
            return "delivered"
        if url.endswith("/details"):
            return [11, 12, 13]
        if url.endswith("/ip/service"):
            return []
        if url.endswith("/11"):
            return {"domain": "192.0.2.11/32", "cancelled": False}
        if url.endswith("/12"):
            return {"domain": "*001", "description": "IP 192.0.2.99", "cancelled": False}
        return {"domain": "192.0.2.12/32", "cancelled": True}

    client = OvhClient(OvhConfig(
        application_key="fixture-ak", application_secret="fixture-as",
        consumer_key="fixture-ck", service_name="fixture-service"), transport=transport)
    assert client.order_status(9001) == "delivered"
    assert client.order_ipv4(9001) == ["192.0.2.11"]


def test_order_reader_resolves_exact_internal_ip_service_identity():
    from apps.vps.services.ovh import OvhClient, OvhConfig

    calls = []

    def transport(method, url, headers):
        calls.append(url)
        if url.endswith("/auth/time"):
            return 2000000000
        if url.endswith("/details"):
            return [11, 12]
        if url.endswith("/11"):
            return {"domain": "ip-fixture-service", "cancelled": False}
        if url.endswith("/12"):
            return {"domain": "ip-fixture-service-prefix", "cancelled": False}
        if url.endswith("/ip/service"):
            return ["ip-fixture-service"]
        if url.endswith("/ip/service/ip-fixture-service"):
            return {"ip": "192.0.2.11/32"}
        pytest.fail("reader must not request a merely similar service identity")

    client = OvhClient(OvhConfig(
        application_key="fixture-ak", application_secret="fixture-as",
        consumer_key="fixture-ck", service_name="fixture-service"), transport=transport)
    assert client.order_ipv4(9001) == ["192.0.2.11"]
    assert sum(url.endswith("/ip/service") for url in calls) == 1


def _ordering_driver():
    from apps.vps.services.ovh import OvhConfig
    from apps.vps.services.ovh_ordering import OvhOrderingClient

    calls = []
    state = {"price": "2.39", "quantity": 1, "destination": "fixture-service",
             "contract_content": "fixture approved terms"}
    cart_id = "11111111-1111-4111-8111-111111111111"

    def transport(method, url, headers, body=None):
        calls.append((method, url, body))
        if method == "POST":
            return {"orderId": 9001}
        if url.endswith("/auth/time"):
            return 2000000000
        if url.endswith("/checkout"):
            return {"prices": {"withTax": {"value": state["price"], "currencyCode": "USD"}},
                    "contracts": [{"name": "Cloud Base",
                                   "content": state["contract_content"],
                                   "url": "https://example.invalid/fixture-contract"}]}
        if url.endswith("/item/77"):
            return {"settings": {"quantity": state["quantity"],
                                 "planCode": "ip-failover-arin", "pricingMode": "default"},
                    "duration": "P1M", "options": [], "configurations": [1, 2, 3]}
        if "/configuration/" in url:
            key = {"1": "country", "2": "datacenter", "3": "destination"}[url.rsplit("/", 1)[1]]
            return {"label": key,
                    "value": {"country": "SG", "datacenter": "SGP",
                              "destination": state["destination"]}[key]}
        return {"items": [77], "expire": "2099-01-01T00:00:00Z"}

    driver = OvhOrderingClient(OvhConfig(
        application_key="fixture-ak", application_secret="fixture-as",
        consumer_key="fixture-ck", service_name="fixture-service"), transport=transport)
    return driver, cart_id, state, calls


def test_ordering_checkout_revalidates_quote_before_any_payment():
    from apps.vps.services.ovh import OvhError

    driver, cart_id, state, calls = _ordering_driver()
    expected = driver.preview_cart(cart_id, 77)
    state["price"] = "2.40"
    with pytest.raises(OvhError):
        driver.checkout_cart(cart_id, expected=expected)
    assert not any(method == "POST" for method, _, _ in calls)


def test_ordering_checkout_refuses_changed_contract_content_with_same_name():
    from apps.vps.services.ovh import OvhError

    driver, cart_id, state, calls = _ordering_driver()
    expected = driver.preview_cart(cart_id, 77)
    state["contract_content"] = "fixture changed terms, unchanged contract name"
    with pytest.raises(OvhError):
        driver.checkout_cart(cart_id, expected=expected)
    assert not any(method == "POST" for method, _, _ in calls)


@pytest.mark.parametrize("field,value", [("quantity", 2), ("destination", "wrong-service")])
def test_ordering_checkout_refuses_cart_identity_changes(field, value):
    from apps.vps.services.ovh import OvhError

    driver, cart_id, state, calls = _ordering_driver()
    expected = driver.preview_cart(cart_id, 77)
    state[field] = value
    with pytest.raises(OvhError):
        driver.checkout_cart(cart_id, expected=expected)
    assert not any(method == "POST" for method, _, _ in calls)


def test_ordering_checkout_pays_once_when_exact_preview_matches():
    import json

    driver, cart_id, state, calls = _ordering_driver()
    expected = driver.preview_cart(cart_id, 77)
    assert driver.checkout_cart(cart_id, expected=expected) == 9001
    posts = [(url, body) for method, url, body in calls if method == "POST"]
    assert len(posts) == 1
    assert json.loads(posts[0][1]) == {
        "autoPayWithPreferredPaymentMethod": True, "waiveRetractationPeriod": True}


def test_adopting_prepared_cart_only_reads_without_creating_replacement():
    driver, cart_id, state, calls = _ordering_driver()
    prepared = driver.adopt_prepared_cart(cart_id)
    assert prepared.cart_id == cart_id and prepared.with_tax_minor == 239
    assert not any(method == "POST" for method, _, _ in calls)


def test_coordinator_adopts_configured_cart_without_preparing_another(db):
    from apps.vps.services.ovh_acquisition import ensure_free_ip

    profile, gateway, instance = _domain(db)
    cart_id = "11111111-1111-4111-8111-111111111111"
    profile.provider_config = {**profile.provider_config, "adopt_ip_cart_id": cart_id}
    db.commit()
    provider = _Provider()
    prepared = provider.prepare_additional_ipv4()
    provider.calls.clear()
    provider.adopt_prepared_cart = lambda actual: prepared if actual == cart_id else None
    result = ensure_free_ip(db, profile, instance=instance, gateway_row=gateway,
                            provider=provider, gateway=_Gateway(), operation_id="adopt",
                            sleep=lambda _: None)
    assert result.address == "192.0.2.11"
    assert not any(call[0] == "prepare" for call in provider.calls)
    assert [call[0] for call in provider.calls].count("checkout") == 1


def test_same_adopted_cart_cannot_be_used_by_a_second_instance(db):
    from apps.vps.services.backends.contracts import BackendConflict
    from apps.vps.services.ovh_acquisition import ensure_free_ip
    from apps.vps.tables import VpsInstance

    profile, gateway, instance = _domain(db)
    cart_id = "11111111-1111-4111-8111-111111111111"
    profile.provider_config = {**profile.provider_config, "adopt_ip_cart_id": cart_id}
    db.commit()
    provider = _Provider()
    prepared = provider.prepare_additional_ipv4()
    provider.adopt_prepared_cart = lambda actual: prepared
    ensure_free_ip(db, profile, instance=instance, gateway_row=gateway,
                   provider=provider, gateway=_Gateway(), operation_id="first-instance",
                   sleep=lambda _: None)
    second = VpsInstance(
        id="second-instance", user_id="owner", plan_id="vps-nho", os_id="win10",
        gateway_id=gateway.id, infrastructure_profile_id=profile.id,
        profile_resolution_state="PINNED", vmid=209,
        paid_until=datetime(2099, 1, 1, tzinfo=timezone.utc))
    db.add(second)
    db.commit()
    provider.calls.clear()
    with pytest.raises(BackendConflict):
        ensure_free_ip(db, profile, instance=second, gateway_row=gateway,
                       provider=provider, gateway=_Gateway(), operation_id="second-instance",
                       sleep=lambda _: None)
    assert provider.calls == []


def test_configured_bounded_capacity_requires_real_readonly_quote(db, monkeypatch):
    from apps.vps.services import backend_factory

    profile, _, _ = _domain(db)
    cart_id = "11111111-1111-4111-8111-111111111111"
    profile.provider_config = {**profile.provider_config, "adopt_ip_cart_id": cart_id,
                               "max_ip_with_tax_minor": 239,
                               "accepted_contract_fingerprints": ["a" * 64]}
    profile.network_config = {"mapping_strategy": "ovh_gwnat"}
    db.commit()
    provider = _Provider()
    quote = provider.prepare_additional_ipv4()
    reads = []

    def adopt(actual):
        reads.append(actual)
        return quote

    monkeypatch.setattr(backend_factory, "ovh_ordering_client", lambda _: SimpleNamespace(
        adopt_prepared_cart=adopt))
    pool = backend_factory.public_ip_backend(db, profile)
    assert reads == [], "constructor must not load provider credentials"
    assert pool.capabilities().dynamic_acquisition is True
    health = pool.health()
    assert health.status == "HEALTHY" and health.details["replenishable"] == 1
    assert reads == [cart_id]


def test_bounded_capacity_never_advertises_a_changed_or_unreadable_quote(db, monkeypatch):
    from apps.vps.services import backend_factory
    from apps.vps.services.ovh import OvhError

    profile, _, _ = _domain(db)
    profile.provider_config = {**profile.provider_config,
                               "adopt_ip_cart_id": "11111111-1111-4111-8111-111111111111",
                               "max_ip_with_tax_minor": 239,
                               "accepted_contract_fingerprints": ["a" * 64]}
    profile.network_config = {"mapping_strategy": "ovh_gwnat"}
    db.commit()

    reads = []

    def failed(actual):
        reads.append(actual)
        raise OvhError("fixture URL/body must not reach health summary")

    monkeypatch.setattr(backend_factory, "ovh_ordering_client", lambda _: SimpleNamespace(
        adopt_prepared_cart=failed))
    health = backend_factory.public_ip_backend(db, profile).health()
    assert health.status == "CRITICAL" and health.details["replenishable"] == 0
    assert "fixture URL/body" not in health.summary
    assert reads == [profile.provider_config["adopt_ip_cart_id"]]


@pytest.mark.parametrize("change", [
    {"with_tax_minor": 240}, {"with_tax_minor": True},
    {"quantity": 2}, {"quantity": True}, {"currency": "EUR"},
    {"contract_fingerprints": ("b" * 64,)},
])
def test_bounded_capacity_rejects_quote_drift(db, monkeypatch, change):
    from dataclasses import replace
    from apps.vps.services import backend_factory

    profile, _, _ = _domain(db)
    profile.provider_config = {**profile.provider_config,
        "adopt_ip_cart_id": "11111111-1111-4111-8111-111111111111",
        "max_ip_with_tax_minor": 239,
        "accepted_contract_fingerprints": ["a" * 64]}
    profile.network_config = {"mapping_strategy": "ovh_gwnat"}
    db.commit()
    quote = replace(_Provider().prepare_additional_ipv4(), **change)
    reads = []

    def adopt(cart_id):
        reads.append(cart_id)
        return quote

    monkeypatch.setattr(backend_factory, "ovh_ordering_client", lambda _: SimpleNamespace(
        adopt_prepared_cart=adopt))
    pool = backend_factory.public_ip_backend(db, profile)
    assert pool.capabilities().dynamic_acquisition is True
    health = pool.health()
    assert health.details["replenishable"] == 0 and health.status == "CRITICAL"
    assert len(reads) == 1
