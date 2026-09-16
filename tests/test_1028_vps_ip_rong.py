"""VPS V4 R16 — keep at most one idle paid OVH IPv4 (owner decision 16/09).

Idle monthly addresses beyond the one kept get `renew.deleteAtExpiration=true`
at OVH (read back), and are never handed to a new machine afterwards.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from platform_core.db import Base

NOW = datetime(2026, 9, 30, tzinfo=timezone.utc)


@pytest.fixture()
def db():
    import platform_core.models as _models  # noqa: F401
    from apps.vps import tables as _tables  # noqa: F401
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


class _OvhFake:
    def __init__(self):
        self.renew = {}
        self.puts = []

    def set_ip_delete_at_expiration(self, address, value):
        self.puts.append((address, value))
        self.renew[address] = value
        return {"renew": {"automatic": True, "deleteAtExpiration": value},
                "expiration": "2026-10-16"}


def _profile(db):
    from apps.vps.tables import VpsInfrastructureProfile
    p = VpsInfrastructureProfile(
        id="p-ovh", slug="ovh", name="OVH", region="sgp", status="ACTIVE",
        compute_backend_type="proxmox", public_ip_backend_type="ovh_static_pool",
        gateway_backend_type="nft", credential_ref="LTT_OVH")
    db.add(p)
    db.commit()
    return p


def _ip(db, address, *, idle_days, state="FREE", billing_mode="monthly", meta=None):
    from apps.vps.tables import VpsIp
    metadata = dict(meta or {})
    if idle_days is not None:
        metadata["free_since"] = (NOW - timedelta(days=idle_days)).isoformat()
    row = VpsIp(infrastructure_profile_id="p-ovh", gateway_id="g-ovh", dia_chi=address,
                state=state, billing_mode=billing_mode, monthly_cost_minor=239,
                provider_metadata=metadata)
    db.add(row)
    db.commit()
    return row


def test_keeps_the_most_recently_idle_address_and_cancels_the_rest(db):
    from apps.vps.services import ip_rong
    profile = _profile(db)
    newest = _ip(db, "192.0.2.10", idle_days=8)
    older = _ip(db, "192.0.2.11", idle_days=20)
    oldest = _ip(db, "192.0.2.12", idle_days=40)
    fake = _OvhFake()
    result = ip_rong.ap_dung(db, profile, fake, now=NOW)
    assert result["giu"] == 1 and result["da_huy_gia_han"] == 2
    assert sorted(fake.puts) == [("192.0.2.11", True), ("192.0.2.12", True)]
    assert "renewal_cancelled_at" not in newest.provider_metadata
    assert older.provider_metadata["expiration"] == "2026-10-16"
    assert oldest.provider_metadata["renewal_cancelled_at"]


def test_recently_freed_pre_owned_and_bound_addresses_are_untouched(db):
    from apps.vps.services import ip_rong
    profile = _profile(db)
    _ip(db, "192.0.2.20", idle_days=1)
    _ip(db, "192.0.2.21", idle_days=2)                           # < 7 days idle
    _ip(db, "192.0.2.22", idle_days=90, billing_mode="pre_owned")
    _ip(db, "192.0.2.23", idle_days=90, state="BOUND")
    unknown = _ip(db, "192.0.2.24", idle_days=None)              # no idle clock yet
    fake = _OvhFake()
    result = ip_rong.ap_dung(db, profile, fake, now=NOW)
    assert fake.puts == [] and result["da_huy_gia_han"] == 0
    assert unknown.provider_metadata["free_since"] == NOW.isoformat()


def test_cancelled_address_is_never_reserved_for_a_new_machine(db):
    from apps.vps.services.backends.contracts import CapacityExhausted
    from apps.vps.services.backends.public_ip import OvhStaticIpPoolBackend
    profile = _profile(db)
    _ip(db, "192.0.2.30", idle_days=30, meta={"renewal_cancelled_at": NOW.isoformat()})
    pool = OvhStaticIpPoolBackend(db, profile)
    with pytest.raises(CapacityExhausted):
        pool.reserve(reservation_key="k1", label="m1")
    assert pool.health().details["free"] == 0
    kept = _ip(db, "192.0.2.31", idle_days=3)
    assert pool.reserve(reservation_key="k2", label="m2").address == kept.dia_chi


def test_ovh_client_put_is_signed_limited_and_read_back():
    from apps.vps.services.ovh import OvhClient, OvhConfig, OvhError

    state = {"deleteAtExpiration": False}
    calls = []

    def transport(method, url, headers, body=None):
        calls.append((method, url, headers, body))
        if url.endswith("/auth/time"):
            return 2000000000
        if method == "PUT":
            state["deleteAtExpiration"] = json.loads(body)["renew"]["deleteAtExpiration"]
            return None
        return {"renew": {"automatic": True, **state}, "expiration": "2026-10-16"}

    client = OvhClient(OvhConfig(application_key="ak", application_secret="as",
                                 consumer_key="ck", service_name="svc"), transport=transport)
    after = client.set_ip_delete_at_expiration("192.0.2.40", True)
    assert after["renew"]["deleteAtExpiration"] is True
    method, url, headers, body = [c for c in calls if c[0] == "PUT"][0]
    assert url.endswith("/ip/service/ip-192.0.2.40/serviceInfos")
    expected = "$1$" + hashlib.sha1("+".join(
        ("as", "ck", "PUT", url, body.decode("ascii"), headers["X-Ovh-Timestamp"])
    ).encode("utf-8")).hexdigest()
    assert headers["X-Ovh-Signature"] == expected
    with pytest.raises(OvhError):
        client._signed("PUT", "/ip/192.0.2.40", {})
    with pytest.raises(OvhError):
        client._signed("DELETE", "/ip/service/ip-192.0.2.40/serviceInfos", {})
