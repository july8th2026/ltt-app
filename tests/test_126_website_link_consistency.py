"""WEB-002: App/Support/Legal/Commerce links share one current contract."""
from __future__ import annotations

import json
from pathlib import Path

from server.templating import PUBLIC_LINKS


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_public_links_match_wordpress_content_contract():
    contract = json.loads((ROOT / "docs/lttstudios-website/wordpress-content-contract.json")
                          .read_text(encoding="utf-8"))
    assert PUBLIC_LINKS == contract["marketing"]
    assert contract["control_plane"] == {
        "catalog": "https://app.lttstudios.com/",
        "login": "https://app.lttstudios.com/login",
        "register": "https://app.lttstudios.com/register",
        "commerce": "https://app.lttstudios.com/nap",
    }


def test_default_legal_links_use_live_pretty_urls_and_callbacks_stay_legacy():
    for rel in ("config.example.json", "data/config.json"):
        config = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        assert config["app_privacy_policy_url"] == PUBLIC_LINKS["privacy"]
        assert config["privacy_policy_url"] == PUBLIC_LINKS["privacy"]
        assert config["app_terms_url"] == PUBLIC_LINKS["terms"]
        assert config["tiktok_redirect_uri"] == "REPLACE_ME_tiktok_redirect_uri"
        assert config["meta_redirect_uri"] == "REPLACE_ME_meta_redirect_uri"

    route_map = json.loads((ROOT / "docs/lttstudios-website/route-map.json")
                           .read_text(encoding="utf-8"))
    callbacks = {rule["production"] for rule in route_map["rules"]
                 if rule["disposition"] == "oauth_callback"}
    assert callbacks == {"/legal/callback.html", "/auth/fb-callback.html"}


def test_all_base_shells_render_the_shared_product_legal_footer():
    partial = (ROOT / "server/templates/_platform_footer.html").read_text(encoding="utf-8")
    assert "Credit &amp; thanh toán" in partial
    assert "public_links.privacy" in partial and "public_links.terms" in partial
    for name in ("base.html", "base_public.html", "base_plain.html"):
        body = (ROOT / "server/templates" / name).read_text(encoding="utf-8")
        assert '{% include "_platform_footer.html" %}' in body
