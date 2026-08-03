"""H15.S4 TV-UI-001 — contract UI Tạo video."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_composer_co_label_drawer_va_keyboard_contract():
    page = _read("apps/taovideo/templates/taovideo.html")

    assert 'aria-controls="tv-compose"' in page
    assert 'aria-expanded="false"' in page
    assert 'class="tv-compose-scrim"' in page
    assert "function closeCompose()" in page
    assert "function openCompose()" in page
    assert "if(e.key==='Escape')closeCompose()" in page
    assert 'for="tv-prompt"' in page
    assert 'for="tv-files"' in page
    assert "Thời lượng<select" in page
    assert "Tỉ lệ<select" in page
    assert "Độ phân giải<select" in page
    assert "Số lượng<select" in page


def test_job_card_error_empty_progress_co_semantics():
    page = _read("apps/taovideo/templates/taovideo.html")

    assert 'role="alert"' in page
    assert 'role="progressbar"' in page
    assert 'aria-valuemin="0" aria-valuemax="100"' in page
    assert "{% set progress = [[j.progress or 0, 0]|max, 100]|min %}" in page
    assert 'class="tv-empty" role="status"' in page
    assert "data-open-compose" in page
    assert "Retry/Delete" not in page


def test_nav_khong_day_user_thuong_vao_settings_va_khong_co_link_gia():
    page = _read("apps/taovideo/templates/taovideo.html")

    assert '{% if is_admin(request) %}<a href="/settings">' in page
    assert 'href="/jobs?app=taovideo"' in page
    assert page.count('disabled aria-disabled="true"') == 1
    assert 'href="#tv-assets"' in page


def test_file_name_duoc_tao_bang_dom_khong_chich_html():
    page = _read("apps/taovideo/templates/taovideo.html")

    assert "title.textContent=kind+': '+file.name" in page
    assert "insertAdjacentHTML" not in page
    assert "out.replaceChildren()" in page


def test_render_error_workspace_va_translate_giu_form_contract():
    routes = _read("apps/taovideo/routes.py")

    assert "if isinstance(jobs, dict):" in routes
    assert 'jobs = jobs.get("items", [])' in routes
    assert "extra.setdefault(\"job_counts\"" in routes
    assert "extra.setdefault(\"prompt_history\"" in routes
    assert 'id="tv-prompt" name="prompt"' in routes
