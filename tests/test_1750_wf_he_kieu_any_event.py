"""Spec §4.7 — `any` nối được mọi kiểu; `event` cho cổng ra trigger."""
from __future__ import annotations

from platform_core.workflow import he_kieu as hk


def test_any_va_event_la_kieu_co_ban():
    assert {"any", "event"} <= hk.KIEU_CO_BAN
    assert hk.hop_le("any") and hk.hop_le("event") and hk.hop_le("event[]")


def test_any_noi_duoc_hai_chieu_voi_moi_kieu():
    for k in sorted(hk.KIEU_CO_BAN) + [f"{k}[]" for k in sorted(hk.KIEU_CO_BAN)]:
        assert hk.ep_duoc(k, "any"), k
        assert hk.ep_duoc("any", k), k


def test_any_khong_lam_hai_kieu_khac_noi_duoc_voi_nhau():
    # `any` là một cửa MỞ, không phải một cầu: image vẫn không sang được video.
    assert not hk.ep_duoc("image", "video")
    assert not hk.ep_duoc("event", "text")


def test_event_van_theo_luat_T_sang_T_mang():
    assert hk.ep_duoc("event", "event[]")
    assert not hk.ep_duoc("event[]", "event")


def test_bang_xuat_ra_co_any_va_danh_dau_phien_ban_2():
    luat = hk.xuat_luat_noi_day()
    assert luat["phien_ban"] == 2
    assert "any" in luat["kieu"] and "event" in luat["kieu"]
    cap = {tuple(c) for c in luat["cap_noi_duoc"]}
    assert ("image", "any") in cap and ("any", "video[]") in cap
    assert ("image", "video") not in cap
