"""Regression guards for Q52 / H15.S0 LTT Carbon Red design contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "server" / "static" / "ltt.css").read_text(encoding="utf-8")
BASE = (ROOT / "server" / "templates" / "base.html").read_text(encoding="utf-8")
PUBLIC = (ROOT / "server" / "templates" / "base_public.html").read_text(encoding="utf-8")
PLAIN = (ROOT / "server" / "templates" / "base_plain.html").read_text(encoding="utf-8")
HEADER = (ROOT / "server" / "templates" / "_header.html").read_text(encoding="utf-8")
SPEC = (ROOT / "docs" / "DESIGN_SYSTEM_LTT.md").read_text(encoding="utf-8")


def test_semantic_tokens_have_one_runtime_source():
    required = (
        "--surface-canvas",
        "--surface-raised",
        "--border-subtle",
        "--text-primary",
        "--brand-primary",
        "--status-success",
        "--status-warning",
        "--status-danger",
        "--focus-ring",
    )
    for token in required:
        assert token in CSS
        assert token in SPEC

    # Template-local palettes previously overrode ltt.css and created two truths.
    assert "--accent:#3b6ef2" not in BASE
    assert "--accent2:#7aa2f7" not in BASE
    assert "--surface-canvas" not in BASE


def test_shared_shells_load_versioned_design_system():
    for template in (BASE, PUBLIC, PLAIN):
        assert '/static/ltt.css?v={{ asset_ver }}' in template


def test_accessibility_contract_is_enforced_in_css():
    assert ":focus-visible" in CSS
    assert "prefers-reduced-motion:reduce" in CSS
    assert "@media(pointer:coarse)" in CSS
    assert "min-height:44px" in CSS
    assert "min-width:44px" in CSS
    assert "e.key!=='Escape'" in HEADER
    assert "restoreFocus" in HEADER


def test_retired_blue_palette_is_not_a_shared_shell_primary():
    template_dir = ROOT / "server" / "templates"
    shared_templates = "".join(
        path.read_text(encoding="utf-8")
        for path in (template_dir / "base.html", template_dir / "base_public.html",
                     template_dir / "base_plain.html", template_dir / "_header.html",
                     template_dir / "error.html")
    )
    shared = (CSS + shared_templates).lower()
    for retired_colour in ("#3b6ef2", "#7aa2f7", "#8a5cf6"):
        assert retired_colour not in shared


def test_mobile_header_can_shrink_without_forcing_catalog_overflow():
    assert ".hdr-logo{margin-right:0;font-size:0}" in CSS
    assert ".hdr-right{gap:5px;min-width:0}" in CSS
