"""Khóa hợp đồng UP-UI-001 cho studio Upscale."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_upscale_mobile_settings_progressive_disclosure():
    page = _read("apps/upscalevideo/templates/upscalevideo.html")
    css = _read("server/static/ltt.css")
    assert 'id="up-settings-toggle"' in page
    assert 'aria-controls="upform" aria-expanded="false"' in page
    assert "form.classList.toggle('mobile-open')" in page
    assert ".up-settings.mobile-open{display:block}" in css


def test_upscale_compare_is_one_accessible_synchronized_surface():
    page = _read("apps/upscalevideo/templates/upscalevideo.html")
    assert 'id="up-compare-range" type="range"' in page
    assert 'id="up-compare-divider"' in page
    assert "function syncOutput()" in page
    assert "preview.addEventListener('play'" in page
    assert 'class="up-use-compare" href="#up-compare"' in page
    assert "up-inline-compare" not in page


def test_upscale_queue_exposes_status_and_progress_semantics():
    page = _read("apps/upscalevideo/templates/upscalevideo.html")
    assert 'aria-labelledby="up-job-title-{{j.id}}"' in page
    assert 'role="progressbar"' in page
    assert 'aria-valuenow="{{j.progress}}"' in page
    assert 'class="up-state up-state-{{j.status}}"' in page
    assert 'aria-disabled="true"' in page
