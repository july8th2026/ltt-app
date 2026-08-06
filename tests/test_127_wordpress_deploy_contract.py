"""WEB-003 deployment payload stays synchronized with the route contracts."""
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "deploy/wordpress/lttstudios-integration/lttstudios-integration.php"


def test_wordpress_plugin_redirects_every_contract_alias():
    source = PLUGIN.read_text(encoding="utf-8")
    contract = json.loads((ROOT / "docs/lttstudios-website/route-map.json")
                          .read_text(encoding="utf-8"))
    pairs = dict(re.findall(r"'(/[^']*)'\s*=>\s*'(/[^']*)'", source))
    expected = {rule["source"]: rule["production"] for rule in contract["rules"]
                if rule["disposition"] in {"redirect", "locale_fallback"}}
    assert pairs == expected


def test_wordpress_plugin_preserves_callbacks_and_connects_control_plane():
    source = PLUGIN.read_text(encoding="utf-8")
    assert "https://app.lttstudios.com" in source
    assert "/login" in source and "/register" in source and "/nap" in source
    assert "add_filter('home_url'" in source
    assert "$normalized_path === '/ltt-tools-ai/'" in source
    assert "function ltt_rewrite_header_cta" in source
    assert "ltt-v2-header__cta" in source
    assert "ob_start('ltt_rewrite_header_cta')" in source
    route_function = source.split("function ltt_legacy_route_map", 1)[1].split("add_action", 1)[0]
    assert "/auth/fb-callback.html" not in route_function
    assert "/legal/callback.html" not in route_function


def test_wordpress_payload_has_data_free_rollback():
    source = PLUGIN.read_text(encoding="utf-8").lower()
    forbidden = ("create table", "update_option", "wp_insert_post", "wp_create_user")
    assert not any(term in source for term in forbidden)
    readme = (ROOT / "deploy/wordpress/README.md").read_text(encoding="utf-8")
    assert "Rollback" in readme and "zero failures" in readme
