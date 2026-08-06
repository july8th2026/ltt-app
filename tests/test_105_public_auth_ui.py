"""Regression guards for H15.S1 public catalog and authentication UI."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "server" / "templates"


def _read(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def test_auth_pages_share_one_brand_partial():
    for name in (
        "login.html",
        "register.html",
        "forgot_password.html",
        "reset_password.html",
        "register_sent.html",
        "verify_result.html",
    ):
        assert '{% include "_auth_brand.html" %}' in _read(name)


def test_auth_form_controls_have_programmatic_labels():
    expected = {
        "login.html": ("login-username", "login-password"),
        "register.html": ("register-email", "register-password"),
        "forgot_password.html": ("forgot-email",),
        "reset_password.html": ("reset-password",),
    }
    for name, field_ids in expected.items():
        source = _read(name)
        for field_id in field_ids:
            assert f'for="{field_id}"' in source
            assert f'id="{field_id}"' in source


def test_auth_errors_and_success_states_are_announced():
    assert 'role="alert"' in _read("login.html")
    assert 'role="alert"' in _read("register.html")
    assert 'role="alert"' in _read("forgot_password.html")
    assert 'role="alert"' in _read("reset_password.html")
    assert 'role="status"' in _read("register_sent.html")
    assert 'role="status"' in _read("verify_result.html")


def test_plain_auth_shell_has_mobile_and_focus_contract():
    source = _read("base_plain.html")
    assert "min-height:44px" in source
    assert "var(--focus-shadow)" in source
    assert "@media(max-width:480px)" in source
    assert '<main class="box">' in source


def test_public_catalog_search_and_mobile_menu_have_accessible_names():
    home = _read("home.html")
    header = _read("_header.html")
    assert 'for="catsearch"' in home
    assert 'id="catsearch"' in home
    # H24: nhan gio di qua catalog dich. Van chot rang nut CO ten doc duoc cho
    # trinh doc man hinh — do moi la dieu test nay canh.
    assert "aria-label=" in header
    assert "Mở danh sách ứng dụng" in header
