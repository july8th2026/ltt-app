"""H15.S4 TV-FEAT-002 — prompt guidance, seed và remix capability."""

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_prompt_guidance_tat_dinh_va_bo_qua_enum_la():
    from apps.taovideo.routes import _compose_prompt

    plain = _compose_prompt("A runner", "bad", "bad", "bad")
    guided = _compose_prompt("A runner", "tracking", "dynamic", "cinematic")
    assert plain == "A runner"
    assert guided.startswith("A runner\n\nDirection:")
    assert "smooth subject tracking shot" in guided
    assert "dynamic energetic motion" in guided
    assert "filmic color grading" in guided


def test_seed_validation():
    from apps.taovideo.routes import _clean_seed

    assert _clean_seed("") is None
    assert _clean_seed("0") == 0
    assert _clean_seed("2147483647") == 2_147_483_647
    for value in ("x", "-1", "2147483648"):
        with pytest.raises(ValueError, match="Seed"):
            _clean_seed(value)


def test_model_registry_khai_capability_thay_vi_hardcode_ui():
    from apps.taovideo import models

    for model in models.MODELS.values():
        assert model["supports_seed"] is True
        assert model["prompt_controls"] == ["camera", "motion", "visual_style"]


def test_modelark_chi_gui_seed_khi_co(monkeypatch):
    from apps.taovideo import modelark
    sent = []

    class _Response:
        status_code = 200
        text = '{"id":"task-1"}'

        @staticmethod
        def json():
            return {"id": "task-1"}

    import httpx
    monkeypatch.setattr(httpx, "post", lambda *a, **kw: sent.append(kw["json"]) or _Response())
    base = dict(api_key="local-test", model_endpoint="ep-test",
                content=[{"type": "text", "text": "p"}], resolution="720p",
                duration=5, aspect_ratio="16:9")
    modelark.submit(**base)
    modelark.submit(**base, seed=123)
    assert "seed" not in sent[0]
    assert sent[1]["seed"] == 123


def test_ui_co_preview_capability_bien_the_va_remix():
    page = (ROOT / "apps/taovideo/templates/taovideo.html").read_text(encoding="utf-8")
    routes = (ROOT / "apps/taovideo/routes.py").read_text(encoding="utf-8")
    quotes = (ROOT / "apps/taovideo/quotes.py").read_text(encoding="utf-8")
    jobs = (ROOT / "apps/taovideo/jobs.py").read_text(encoding="utf-8")

    assert '<details class="tv-fieldset tv-assist" id="tv-assist">' in page
    assert 'hx-post="/taovideo/prompt-assist"' in page
    assert 'name="camera"' in page and 'name="motion"' in page
    assert 'name="visual_style"' in page and 'name="seed"' in page
    assert 'class="tv-remix"' in page
    assert "q('[name=count]').value='2'" in page
    assert 'params["seed"] = (fixed_seed + variant)' in quotes
    assert 'seed = int(params["seed"])' in jobs
