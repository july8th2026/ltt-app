"""
Đợt A2 — cổng parity `taovideo` (seedance_video, Pha 1: text→video).

Khoá: cost model token→VND→credit khớp bản gốc + estimate=settle nhất quán,
registry model đúng, manifest hợp đồng. (Async submit/poll cần mạng → không test ở đây.)
"""
from __future__ import annotations


def test_cost_token_formula():
    from apps.taovideo import cost
    # Hiệu chỉnh gốc: mini 480p/16:9/5s ≈ 50638 token.
    t = cost.uoc_tinh_token("480p", 5)
    assert 49000 <= t <= 52000, f"token uoc {t} lech hieu chinh goc"
    # 720p nhiều pixel hơn 480p → token cao hơn.
    assert cost.uoc_tinh_token("720p", 5) > t


def test_cost_credit_tu_ti_gia():
    from apps.taovideo import cost
    # 1 credit = 100đ; usd_to_vnd=26000. mini 480p/5s ~ $0.177 ~ 4600đ ~ 46-47 credit.
    c = cost.uoc_luong_credit("seedance-2.0-mini", "480p", 5, False)
    assert 40 <= c <= 55, f"credit {c} ngoai khoang ky vong"
    # video input rate cao hơn no-video? mini: (2.1 co video, 3.5 khong) → khong-video ĐẮT hơn.
    assert cost.usd_tu_token("seedance-2.0-mini", 50000, False) > \
           cost.usd_tu_token("seedance-2.0-mini", 50000, True)


def test_estimate_khop_exact_khi_cung_token():
    from apps.taovideo import cost
    tokens = cost.uoc_tinh_token("480p", 5)
    est = cost.uoc_luong_credit("seedance-2.0-mini", "480p", 5, False)
    exact = cost.credit_tu_token("seedance-2.0-mini", tokens, False)
    assert est == exact, "estimate va exact phai khop khi cung token"


def test_credit_toi_thieu_1():
    from apps.taovideo import cost
    assert cost.credit_tu_token("seedance-2.0-mini", 1, False) >= 1


def test_models_registry():
    from apps.taovideo import models
    assert models.DEFAULT_MODEL == "seedance-2.0-mini"
    assert models.provider_model("seedance-2.0-mini").startswith("ep-")
    opts = models.options()
    assert ("seedance-2.0-mini", "Seedance 2.0 Mini") in opts
    m = models.get("seedance-2.0")
    assert "1080p" in m["resolutions"] and "4k" in m["resolutions"]  # standard hỗ trợ 4k


def test_modelark_che_key():
    from apps.taovideo.modelark import _che
    assert _che("loi key=abcdef123456", "abcdef123456") == "loi key=***"


def test_manifest():
    from apps.taovideo.manifest import MANIFEST
    assert MANIFEST.slug == "taovideo" and MANIFEST.route_prefix == "/taovideo"
    assert MANIFEST.job_types == ("taovideo.generate",)
    assert MANIFEST.credit_cost({"model": "seedance-2.0-mini", "resolution": "480p",
                                 "duration": 5}) >= 1


def test_discover_khong_loi():
    from platform_core.registry import discover
    apps = {a.manifest.slug: a for a in discover()}
    assert "taovideo" in apps and not apps["taovideo"].error
