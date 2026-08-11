"""H32.5 — Seedance customer UI parity and responsive drawer contracts."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_paid_action_stays_with_quote_and_saved_assets_are_progressive_disclosure():
    page = _read("apps/taovideo/templates/taovideo.html")

    assert 'class="tv-submit-dock"' in page
    assert page.index('class="tv-cost"') < page.index('class="tv-create"')
    assert '<details class="tv-fieldset tv-assets" id="tv-assets">' in page
    assert 'data-open-assets' in page
    assert "assets.open=true" in page


def test_mobile_drawer_hides_offscreen_controls_and_has_an_explicit_close():
    page = _read("apps/taovideo/templates/taovideo.html")
    css = _read("server/static/ltt.css")

    assert 'class="tv-compose-close"' in page
    assert "compose.toggleAttribute('inert',hidden)" in page
    assert "compose.setAttribute('aria-hidden',String(hidden))" in page
    assert "if(compact.matches)drawer.focus()" in page
    assert "compact.addEventListener('change',syncComposeMode)" in page
    assert ".tv-compose-close{display:none}" in css
    assert ".tv-compose-open .tv-drawer{display:none}" in css


def test_customer_history_statuses_go_through_i18n_and_hide_raw_worker_message():
    page = _read("apps/taovideo/templates/taovideo.html")

    assert "('running','Đang xử lý')" in page
    assert "{{ _(label) }}" in page
    for marker in ('{{ _(\"Hoàn tất\") }}', '{{ _(\"Lỗi\") }}',
                   '{{ _(\"Đã hủy\") }}', '{{ _(\"Đang chờ\") }}',
                   '{{ _(\"Đang xử lý\") }}'):
        assert marker in page
    assert "j.progress_msg or 'Đang tạo'" not in page


def test_compact_library_controls_keep_accessible_names():
    page = _read("apps/taovideo/templates/taovideo.html")
    css = _read("server/static/ltt.css")

    assert 'select name="model" aria-label="{{ _' in page
    assert 'select name="aspect" aria-label="{{ _' in page
    assert 'select name="sort" aria-label="{{ _' in page
    assert ".tv-library>header{min-height:48px}" in css
    assert ".tv-library-filters{align-items:center" in css


def test_quote_loading_and_failure_never_leave_paid_action_looking_ready():
    page = _read("apps/taovideo/templates/taovideo.html")

    assert "function quoteBusy()" in page
    assert "function quoteDone(ok)" in page
    assert "createButton.disabled=!ok" in page
    assert "htmx:beforeRequest" in page
    assert "htmx:afterRequest" in page
    assert "htmx:sendError" in page
