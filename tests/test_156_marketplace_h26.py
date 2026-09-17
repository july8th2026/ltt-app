"""H26.4: Marketplace là UI customer, taxonomy/lifecycle lấy từ manifest."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import platform_core.db as dbmod

    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'market.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-market-h26")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from server.app import create_app
    test_client = TestClient(
        create_app(), base_url="https://testserver", follow_redirects=False)
    try:
        yield test_client
    finally:
        dbmod.reset_engine()


def _login(client, email="market-h26@example.com"):
    import platform_core.db as dbmod
    from platform_core.users import tao_nguoi_dung

    gen = dbmod.get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email=email, password="matkhau-tot-12",
                       is_verified=True)
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass
    page = client.get("/login").text
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    response = client.post("/login", data={
        "username": email, "password": "matkhau-tot-12",
        "csrf_token": token,
    })
    assert response.status_code == 303


def test_marketplace_card_la_mot_link_khong_lap_icon_hoac_metadata_dev(client):
    _login(client)
    body = client.get("/").text
    cards = re.findall(r'<a class="market-card".*?</a>', body, re.S)
    assert cards
    assert all(card.count("<a ") == 1 for card in cards)
    assert all('data-categories="' in card and 'data-lifecycle="' in card
               for card in cards)
    assert all("market-cover" in card and "market-cover><span" not in card
               for card in cards)
    assert "cần: api" not in body and "cần: gpu" not in body


def test_filter_hai_truc_va_card_khong_con_bi_bat_su_kien_category(client):
    _login(client, "market-filter@example.com")
    body = client.get("/").text
    assert 'id="market-categories"' in body
    assert 'id="market-lifecycles"' in body
    assert "#market-categories button[data-category]" in body
    assert 'class="market-card"' in body
    assert 'class="market-card" data-category=' not in body


def test_lifecycle_mac_dinh_duoc_xep_phat_hanh_truoc(client):
    _login(client, "market-order@example.com")
    body = client.get("/").text
    sequence = re.findall(r'class="market-card"[^>]*data-lifecycle="([^"]+)"', body)
    assert sequence
    orders = {"released": 0, "development": 1, "maintenance": 2}
    customer_orders = [orders[value] for value in sequence if value in orders]
    assert customer_orders == sorted(customer_orders)


def test_tao_anh_mot_entry_hai_mode_va_route_thumbnail_cu_con_hoat_dong(client):
    _login(client, "market-image@example.com")
    home = client.get("/").text
    # C3 Golden UI 17/09: "Mở app" -> "Mở ứng dụng" (chữ Việt trọn vẹn); ý định giữ nguyên.
    assert home.count('href="/taoanh" aria-label="Mở ứng dụng Tạo ảnh AI"') == 1
    assert 'href="/thumbnail" aria-label="Mở ứng dụng' not in home
    general = client.get("/taoanh")
    assert general.status_code == 200
    assert 'href="/taoanh" aria-current="page"' in general.text
    canonical = client.get("/taoanh/thumbnail")
    assert canonical.status_code == 200
    assert 'href="/taoanh/thumbnail" aria-current="page"' in canonical.text
    assert 'hx-get="/thumbnail/studio-fragment"' in canonical.text
    legacy = client.get("/thumbnail", follow_redirects=False)
    assert legacy.status_code == 308
    assert legacy.headers["location"] == "/taoanh/thumbnail"


def test_css_khoa_empty_state_responsive_va_touch_target():
    css = (ROOT / "server" / "static" / "ltt.css").read_text(encoding="utf-8")
    assert ".market-empty[hidden]{display:none}" in css
    assert "@media(max-width:900px){.market-grid{grid-template-columns:repeat(2" in css
    assert "@media(max-width:400px){.market-grid{grid-template-columns:minmax(0,1fr)" in css
    assert ".market-categories button{min-height:44px}" in css
    assert ".image-product-tabs a{display:flex;min-height:44px" in css


def test_catalog_en_bien_dich_duoc_va_co_lifecycle_moi():
    from babel.messages.pofile import read_po

    po = ROOT / "locale" / "en" / "LC_MESSAGES" / "messages.po"
    with po.open("rb") as stream:
        catalog = read_po(stream)
    assert not catalog.fuzzy
    expected = {
        "Đã phát hành": "Released",
        "Đang phát triển": "In development",
        "Đang bảo trì": "Maintenance",
    }
    assert {msgid: catalog[msgid].string for msgid in expected} == expected
