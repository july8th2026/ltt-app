"""H15.S2.3 operator boundary and Settings/Status UI guards."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_settings_and_status_require_operator_not_only_login():
    settings = _read("server/routes/settings.py")
    status = _read("server/routes/status.py")
    assert "Depends(require_login)" not in settings
    assert "Depends(require_login)" not in status
    assert settings.count("Depends(require_operator)") == 7
    assert "Depends(require_operator)" in status


def test_user_shell_hides_operator_links():
    header = _read("server/templates/_header.html")
    home = _read("server/templates/home.html")
    assert '{% if is_admin(request) %}<a href="/settings"' in header
    assert '{% if is_admin(request) %}<a href="/settings"' in home


def test_settings_ia_and_accessible_status_contract():
    settings = _read("server/templates/settings.html")
    status = _read("server/templates/status.html")
    assert 'class="card settings-group"' in settings
    assert 'aria-label="Mục cấu hình"' in settings
    assert 'for="content-calendar-file"' in settings
    assert 'role="alert"' in settings and 'role="status"' in settings
    assert 'role="alert"' in status and 'role="status"' in status
