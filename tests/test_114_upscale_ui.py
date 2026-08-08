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
    assert 'id="up-compare-divider" role="slider" tabindex="0"' in page
    assert 'aria-valuemin="0" aria-valuemax="100" aria-valuenow="50"' in page
    assert "setPointerCapture" in page and "hasPointerCapture" in page
    assert "event.key==='ArrowLeft'" in page and "event.key==='Home'" in page
    assert 'id="up-compare-range"' not in page
    assert "function syncOutput(force=false)" in page
    assert "Math.abs(outputPreview.currentTime-preview.currentTime)>.12" in page
    assert "setInterval(()=>syncOutput(false),100)" in page
    assert 'class="up-use-compare" href="#up-compare"' in page
    assert "up-inline-compare" not in page


def test_upscale_queue_exposes_status_and_progress_semantics():
    page = _read("apps/upscalevideo/templates/upscalevideo.html")
    assert 'aria-labelledby="up-job-title-{{j.id}}"' in page
    assert 'role="progressbar"' in page
    assert 'aria-valuenow="{{j.progress}}"' in page
    assert 'class="up-state up-state-{{j.status}}"' in page
    assert 'aria-disabled="true"' in page
    assert 'data-job-filter="done"' in page
    assert 'data-job-filter="processing"' in page
    assert 'data-job-view="grid"' in page
    assert 'id="up-job-sort"' in page
    assert 'class="up-job-thumb"' in page and '/source#t=0.1' in page
    assert '/jobs/{{j.id}}/download' in page
