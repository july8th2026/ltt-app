"""W6 — the desktop app is gone, and must stay gone.

Removing code is easy; keeping it removed is not. Half-deleted desktop
machinery is worse than either state, because it looks available and fails at
the point of use — a browser that never opens, a port nobody listens on, a
config field the app no longer reads.
"""
from __future__ import annotations

import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Only ever read by the deleted localhost transport / OAuth relay.
DEAD_CONFIG_KEYS = [
    "oauth_redirect_port",
    "tiktok_oauth_port",
    "oauth_browser_path",
    "oauth_browser_profile",
    "tiktok_oauth_relay_url",
    "tiktok_oauth_relay_secret",
]

APP_DIRS = ("core", "server", "utils", "tools", "tests")

# tools/demo_fb and tools/demo_v2 are standalone recording aids for the TikTok
# audit submission (a teleprompter, slide generators). They are run by hand on
# a desktop, are not imported by the app, and never execute on the server — so
# their tkinter use is not a violation. Everything else is in scope.
SKIP_DIRS = ("demo_fb", "demo_v2", "demo_assets", "__pycache__")


def _app_py_files():
    for d in APP_DIRS:
        for path in (ROOT / d).rglob("*.py"):
            if not any(part in SKIP_DIRS for part in path.parts):
                yield path
    for name in ("worker_main.py", "version.py"):
        p = ROOT / name
        if p.exists():
            yield p


def _imported_names(path: pathlib.Path):
    """Every module name this file imports, from the AST.

    Parsing rather than grepping: a docstring that *mentions* customtkinter
    (server/app.py documents the boundary rule) is not an import of it.
    """
    import ast
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:                      # pragma: no cover
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, node.lineno
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                yield node.module, node.lineno


# ── the files themselves ───────────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "gui", "main.py", "run_gui.bat", "run_debug.bat", "build_exe.bat",
    "BOT_UP_FACEBOOK.spec", "setup_new_machine.bat", "check_environment.bat",
    "tests/gui_smoke_validator.py", "tests/test_30_operation_tab_split.py",
    # The relay tooling exercised a subsystem that no longer exists.
    "tools/check_oauth_relay.py", "tools/simulate_oauth_flow.py",
])
def test_desktop_artifact_is_gone(path):
    assert not (ROOT / path).exists(), f"{path} should have been deleted"


def test_no_module_imports_gui():
    offenders = [
        f"{path.relative_to(ROOT)}:{line}"
        for path in _app_py_files()
        for name, line in _imported_names(path)
        if name == "gui" or name.startswith("gui.")
    ]
    assert offenders == [], f"gui imports remain: {offenders}"


@pytest.mark.parametrize("package", ["customtkinter", "tkinter", "qrcode",
                                     "pyperclip", "google_auth_oauthlib"])
def test_no_desktop_only_package_is_imported(package):
    """A GUI toolkit import inside a request thread would raise on a headless
    server, and only at the moment the operator needed it."""
    offenders = [
        f"{path.relative_to(ROOT)}:{line}"
        for path in _app_py_files()
        for name, line in _imported_names(path)
        if name == package or name.startswith(package + ".")
    ]
    assert offenders == [], f"{package} imported at {offenders}"


def test_requirements_no_longer_ship_gui_packages():
    text = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    installs = [ln.strip() for ln in text.splitlines()
                if ln.strip() and not ln.strip().startswith("#")]
    for package in ("customtkinter", "Pillow", "qrcode", "google-auth-oauthlib"):
        assert not any(package.lower() in ln.lower() for ln in installs), \
            f"{package} is still installed but nothing imports it"


# ── the localhost OAuth transport ──────────────────────────────────────────

@pytest.mark.parametrize("module", ["core.auth_manager", "core.tiktok.auth_manager"])
@pytest.mark.parametrize("attr", ["start_oauth_flow", "_poll_relay", "_bind_server",
                                  "_open_oauth_browser", "_HTML_SUCCESS", "_HTML_ERROR"])
def test_transport_internals_are_gone(module, attr):
    import importlib
    mod = importlib.import_module(module)
    assert not hasattr(mod, attr), f"{module}.{attr} survived"
    manager = getattr(mod, "AuthManager", None) or mod.TikTokAuthManager
    assert not hasattr(manager, attr), f"{module}.{manager.__name__}.{attr} survived"


@pytest.mark.parametrize("module,attrs", [
    ("core.auth_manager", ["build_authorize_url", "complete_oauth",
                           "import_system_user_token", "test_token",
                           "revoke_account"]),
    ("core.tiktok.auth_manager", ["build_authorize_url", "complete_oauth",
                                  "generate_pkce_pair", "refresh_access_token",
                                  "revoke_account"]),
])
def test_the_web_facing_api_survived(module, attrs):
    """The other half of the deletion: everything the web app calls must remain."""
    import importlib
    mod = importlib.import_module(module)
    manager = getattr(mod, "AuthManager", None) or mod.TikTokAuthManager
    for attr in attrs:
        assert callable(getattr(manager, attr, None)), f"{module}.{attr} missing"


def test_sheet_client_never_waits_for_a_browser():
    """`InstalledAppFlow.run_local_server()` blocks forever on a headless
    server — inside a request, with no error explaining the hang."""
    src = (ROOT / "utils" / "sheet_client.py").read_text(encoding="utf-8")
    assert "run_local_server" not in src.replace(
        "# interactive fallback: `InstalledAppFlow.run_local_server()` binds a", "")
    # And it must refuse loudly instead.
    assert "Service Account" in src


def test_oauth_client_credentials_are_refused_with_a_next_step(tmp_path):
    from utils.sheet_client import SheetClient

    creds = tmp_path / "client.json"
    creds.write_text(json.dumps({
        "installed": {"client_id": "x", "client_secret": "y"},
        "type": "installed",
    }), encoding="utf-8")

    client = SheetClient(config={})
    with pytest.raises(RuntimeError) as exc:
        client._load_credentials(str(creds))
    message = str(exc.value)
    assert "Service Account" in message, "must say what to do instead"
    assert "chia sẻ" in message, "must mention sharing the Sheet"


# ── dead config keys ───────────────────────────────────────────────────────

@pytest.mark.parametrize("key", DEAD_CONFIG_KEYS)
def test_dead_key_absent_from_defaults(key):
    from core.config_defaults import DEFAULTS
    assert key not in DEFAULTS


@pytest.mark.parametrize("key", DEAD_CONFIG_KEYS)
def test_dead_key_not_editable_on_settings_page(key):
    """A field nothing reads invites the operator to 'fix' OAuth by editing a
    value with no effect."""
    from server.services.settings_schema import all_field_keys
    assert key not in set(all_field_keys())


@pytest.mark.parametrize("key", DEAD_CONFIG_KEYS)
def test_dead_key_absent_from_example_config(key):
    cfg = json.loads((ROOT / "config.example.json").read_text(encoding="utf-8"))
    assert key not in cfg


@pytest.mark.parametrize("key", DEAD_CONFIG_KEYS)
def test_dead_key_unread_by_any_module(key):
    offenders = [str(p.relative_to(ROOT)) for p in _app_py_files()
                 if key in p.read_text(encoding="utf-8")
                 and p.name != pathlib.Path(__file__).name]
    assert offenders == [], f"{key} still referenced in {offenders}"


# ── strings that would now be lies ─────────────────────────────────────────

def test_no_page_tells_the_operator_to_open_the_desktop_app():
    offenders = []
    for path in (ROOT / "server").rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        for phrase in ("app desktop → tab", "mở app desktop", "Thêm ở app desktop"):
            if phrase in text:
                offenders.append(f"{path.relative_to(ROOT)}: {phrase}")
    assert offenders == [], f"impossible instructions: {offenders}"


def test_worker_main_points_at_the_web_app():
    src = (ROOT / "worker_main.py").read_text(encoding="utf-8")
    assert "mở app desktop" not in src
    assert "Sheet FB" in src, "must name where workers are actually added"


# ── the maintenance daemon moved, it did not disappear ─────────────────────

def test_maintenance_daemon_has_an_owner():
    """Only gui/main_window.py started it. Without a new owner the retention
    policy would stop being enforced while every unit test still passed."""
    src = (ROOT / "server" / "app.py").read_text(encoding="utf-8")
    assert "MaintenanceDaemon" in src
    assert "lifespan" in src


# ── config files edited on Windows ─────────────────────────────────────────

BOM = "\ufeff"


def test_config_with_a_bom_still_loads():
    """PowerShell's `Out-File -Encoding utf8` and Notepad both write a UTF-8
    BOM. json.load() raises on it, which took the live site to an opaque 503
    from /health/ready while the service itself was running normally."""
    import tempfile

    from core.settings import load_settings

    with tempfile.TemporaryDirectory() as tmp:
        cfg = pathlib.Path(tmp) / "config.json"
        cfg.write_text(BOM + json.dumps({"sheet_id": "abc"}), encoding="utf-8")
        settings = load_settings(env={"LTT_ENV": "local-server-test",
                                      "LTT_CONFIG_PATH": str(cfg)})
        assert settings.config["sheet_id"] == "abc"


def test_settings_page_reads_a_bom_config():
    import tempfile

    from server.services.settings_service import load_config

    with tempfile.TemporaryDirectory() as tmp:
        cfg = pathlib.Path(tmp) / "config.json"
        cfg.write_text(BOM + json.dumps({"sheet_id": "abc"}), encoding="utf-8")
        assert load_config({"LTT_CONFIG_PATH": str(cfg)})["sheet_id"] == "abc"


def test_worker_store_reads_a_bom_file():
    import tempfile

    from core.worker_store import load_workers

    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "workers.json"
        path.write_text(BOM + json.dumps({"_schema_version": 1, "facebook": []}),
                        encoding="utf-8")
        assert load_workers(platform="facebook", path=str(path)) == []
