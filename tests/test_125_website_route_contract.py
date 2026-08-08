"""WEB-001: one explicit map between legacy static files and WordPress URLs."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs" / "lttstudios-website"
MAP = SITE / "route-map.json"


def _contract():
    return json.loads(MAP.read_text(encoding="utf-8"))


def test_route_map_covers_every_legacy_html_page_once():
    contract = _contract()
    all_sources = [rule["source"] for rule in contract["rules"]]
    assert len(all_sources) == len(set(all_sources)), "duplicate source route"
    # Canonical WordPress targets can exist without a file in the legacy
    # static reference bundle. Such entries remain in the route contract so
    # production audit still checks them, but do not pretend a source file
    # exists (WEB-001 regression found 2026-08-08).
    mapped = [rule["source"] for rule in contract["rules"]
              if rule.get("source_exists", True)]

    files = {
        "/" if path.relative_to(SITE).as_posix() == "index.html"
        else "/vi/" if path.relative_to(SITE).as_posix() == "vi/index.html"
        else "/" + path.relative_to(SITE).as_posix()
        for path in SITE.rglob("*.html")
        if "assets" not in path.relative_to(SITE).parts
    }
    assert set(mapped) == files


def test_pretty_urls_and_callback_exceptions_are_unambiguous():
    contract = _contract()
    assert contract["production_owner"] == "wordpress"
    assert contract["source_owner"] == "legacy-static-reference"

    callbacks = []
    for rule in contract["rules"]:
        target = rule["production"]
        if rule["disposition"] == "oauth_callback":
            callbacks.append(rule)
            assert target == rule["source"] and target.endswith(".html")
        elif target is not None:
            assert target == "/" or target.endswith("/")
            assert ".html" not in target
    assert {rule["source"] for rule in callbacks} == {
        "/auth/fb-callback.html", "/legal/callback.html"
    }


def test_no_old_vi_route_can_point_to_an_unrelated_product():
    rules = {rule["source"]: rule for rule in _contract()["rules"]}
    assert rules["/vi/"]["production"] == "/"
    for source, rule in rules.items():
        if source.startswith("/vi/") and rule["production"]:
            assert "/ai-automation/" not in rule["production"]
