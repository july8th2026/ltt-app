"""Regression tests for the adaptive page-width contract."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_base_exposes_named_page_width_contract() -> None:
    base = _read("server/templates/base.html")
    css = _read("server/static/ltt.css")

    assert "{% block page_mode %}standard{% endblock %}" in base
    assert "page--' ~ (_page_mode|trim)" in base
    assert ".page--catalog{max-width:1600px}" in css
    assert ".page--wide{max-width:1600px" in css
    assert ".page--immersive{max-width:1800px" in css


def test_multi_column_apps_declare_their_page_mode() -> None:
    expected = {
        "immersive": (
            "apps/taovideo/templates/taovideo.html",
            "apps/upscalevideo/templates/upscalevideo.html",
            "apps/autosubvideo/templates/autosubvideo.html",
            "apps/agent/templates/agent_canvas.html",
        ),
        "wide": (
            "apps/thumbnail/templates/thumbnail.html",
            "apps/taoanh/templates/image.html",
            "apps/chataistudio/templates/chataistudio.html",
            "apps/taoclipngan/templates/taoclipngan.html",
        ),
    }

    for mode, templates in expected.items():
        marker = f"{{% block page_mode %}}{mode}{{% endblock %}}"
        for template in templates:
            assert marker in _read(template), template


def test_immersive_workspaces_do_not_escape_with_negative_margins() -> None:
    upscale = _read("server/static/ltt.css")
    autosub = _read("frontend/autosub-studio/src/studio.css")

    assert ".up-studio" in upscale
    assert ".studio-shell" in autosub
    for forbidden in ("margin:-20px", "margin:-14px", "margin:-12px", "margin:-8px"):
        assert forbidden not in upscale
        assert forbidden not in autosub
