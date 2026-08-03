"""H15.S11.1 Script Studio UI/history/editor contract."""
from pathlib import Path


def test_script_templates_have_scoped_editor_and_accessibility():
    root = Path(__file__).parents[1] / "apps" / "kichban" / "templates"
    page = (root / "script.html").read_text("utf-8")
    result = (root / "_script_view.html").read_text("utf-8")
    assert 'class="script-layout"' in page and 'id="script-count"' in page
    assert "script-job-list" in page and "innerHTML" not in page
    assert "data-script-field" in result and "Tải .md" in result
    assert 'role="progressbar"' in result and 'aria-valuenow="{{job.progress}}"' in result
    assert page.count('style="') == 0
    assert result.count('style="') == 1 and 'style="width:{{job.progress}}%"' in result
    assert "onclick=" not in result


def test_script_css_is_responsive_and_scoped():
    css = (Path(__file__).parents[1] / "server" / "static" / "ltt.css").read_text("utf-8")
    assert ".script-studio" in css and ".script-workspace" in css
    assert "@media(max-width:820px){.script-layout" in css
