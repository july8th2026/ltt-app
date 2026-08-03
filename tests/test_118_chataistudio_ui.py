"""H15.S10.1 Chat Studio UI contract."""
from pathlib import Path


def test_chat_template_uses_scoped_accessible_ui_and_safe_dom():
    src = (Path(__file__).parents[1] / "apps" / "chataistudio" / "templates" /
           "chataistudio.html").read_text("utf-8")
    assert 'class="chat-layout"' in src and 'aria-label="Hội thoại"' in src
    assert 'aria-live="polite"' in src and 'role="status"' in src
    assert 'maxlength="20000"' in src and 'id="chat-count"' in src
    assert 'name="attachments"' in src and "multiple" in src
    assert "Ảnh được gửi tới OpenAI" in src
    assert "/export/{{active.id}}.md" in src and "/branch/{{active.id}}" in src
    assert "innerHTML" not in src and "textContent" in src
    assert 'style="' not in src and "onsubmit=" not in src


def test_chat_css_has_responsive_shell_and_touch_targets():
    css = (Path(__file__).parents[1] / "server" / "static" / "ltt.css").read_text("utf-8")
    assert ".chat-layout" in css and ".chat-composer" in css
    assert ".chat-conv button{width:44px;height:44px" in css
    assert "@media(max-width:760px){.chat-heading" in css
