"""P3: sellable slots are the minimum of independent measured limits."""
from dataclasses import replace

import pytest

from apps.vps.services.capacity import SucChua


def _capacity():
    return SucChua(ram_mb_tong=65536, dia_gb_tong=1000,
                   cpu_tong=20, ram_mb_da_hua=0, vcpu_da_hua=0,
                   dia_gb_da_hua=0, dia_gb_dang_dung=100)


@pytest.mark.parametrize("ip,gateway,expected", [(3, 20, 3), (20, 2, 2), (0, 20, 0)])
def test_minimum_ip_and_gateway_limits(ip, gateway, expected):
    from apps.vps.services.sellable_capacity import sellable_slots
    result = sellable_slots(_capacity(), "vps-nho", free_ipv4=ip, gateway_slots=gateway)
    assert result.slots == expected
    assert result.slots == min(result.compute_slots, ip, gateway)


@pytest.mark.parametrize("bad", [None, -1, True, "20"])
def test_unknown_or_invalid_limits_never_mean_unlimited(bad):
    from apps.vps.services.sellable_capacity import sellable_slots
    assert sellable_slots(_capacity(), "vps-nho", free_ipv4=bad,
                          gateway_slots=20).slots == 0


def test_compute_ram_and_cpu_are_counted_in_slots():
    from apps.vps.services.sellable_capacity import sellable_slots
    base = _capacity()
    plentiful = sellable_slots(base, "vps-nho", free_ipv4=100, gateway_slots=100)
    assert plentiful.slots > 1
    exhausted = replace(base, ram_mb_da_hua=base.ram_mb_ban_duoc)
    assert sellable_slots(exhausted, "vps-nho", free_ipv4=100, gateway_slots=100).slots == 0
    exhausted = replace(base, vcpu_da_hua=60)
    assert sellable_slots(exhausted, "vps-nho", free_ipv4=100, gateway_slots=100).slots == 0


def test_storage_unknown_full_or_invalid_plan_fails_closed():
    from apps.vps.services.sellable_capacity import sellable_slots
    for capacity, plan in [(replace(_capacity(), dia_gb_tong=0), "vps-nho"),
                           (replace(_capacity(), dia_gb_dang_dung=1000), "vps-nho"),
                           (_capacity(), "missing")]:
        assert sellable_slots(capacity, plan, free_ipv4=100, gateway_slots=100).slots == 0


def test_auto_acquisition_adds_only_one_promised_ipv4_slot():
    from apps.vps.services.sellable_capacity import effective_ipv4_slots

    health = {"free": 0, "replenishable": 1}
    assert effective_ipv4_slots(health, promised_without_ip=0) == 1
    assert effective_ipv4_slots(health, promised_without_ip=1) == 0
    assert effective_ipv4_slots({"free": 2, "replenishable": 1},
                                promised_without_ip=1) == 2
    assert effective_ipv4_slots({"free": 0, "replenishable": True},
                                promised_without_ip=0) == 0
