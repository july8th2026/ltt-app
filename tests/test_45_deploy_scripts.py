"""
P9 — deployment script sanity checks.

Guards a real bug found while building the package: Windows PowerShell 5.1
reads a .ps1 file using the system ANSI codepage unless it has a UTF-8
BOM. An em-dash in a message string therefore turned into mojibake and
broke the parser with "The string is missing the terminator" — a
deployment script that fails to parse on the target server is worse than
no script, because it fails halfway through an install.

Keeping deploy scripts pure ASCII sidesteps codepage issues entirely.
"""
from __future__ import annotations

import os

import pytest

DEPLOY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deploy", "windows",
)

EXPECTED_SCRIPTS = (
    "install.ps1", "update.ps1", "rollback.ps1",
    "backup.ps1", "restore.ps1", "set-service-env.ps1",
    # Q28 lich backup + bootstrap: truoc day khong nam trong bo guard ASCII/BOM
    # (audit 2026-07-31 W0/W1). Them vao de regression khong lot luoi.
    "5-lich-backup.ps1", "bootstrap-server2016.ps1",
)


def _scripts() -> list:
    return [f for f in sorted(os.listdir(DEPLOY_DIR)) if f.endswith(".ps1")]


def _read(name: str) -> str:
    with open(os.path.join(DEPLOY_DIR, name), "r", encoding="utf-8") as f:
        return f.read()


def test_restore_actually_restores_the_database():
    """W0.4/P0-4: backup dung pg_dump (-Fc) nen restore PHAI pg_restore file
    .dump; neu chi Expand-Archive thi 'khoi phuc' mat toan bo CSDL (user/credit/
    job). Chot bang cach doi restore.ps1 co pg_restore + doc LTT_DATABASE_URL."""
    text = _read("restore.ps1")
    assert "pg_restore" in text, "restore.ps1 khong pg_restore -> backup khong cuu duoc DB"
    assert "LTT_DATABASE_URL" in text


def test_update_runs_migrations_before_start():
    """W0.6/P0-6: ban phat hanh doi schema ma update.ps1 khong 'alembic upgrade
    head' -> service boot tren schema cu, loi runtime/hong du lieu."""
    text = _read("update.ps1")
    assert "alembic upgrade head" in text
    # Migration phai chay TRUOC khi Start-Service.
    assert text.index("alembic upgrade head") < text.index("Start-Service $ServiceName")


def test_service_env_loader_allows_empty_optional_integration_placeholders():
    text = _read("set-service-env.ps1")
    assert "skip empty" in text
    assert "These variables are still empty" not in text
    assert "tools\\nssm.exe" in text


def test_scheduled_backup_tightens_acl():
    """W1.5: ban backup off-drive CHUA secrets (app.env + dump) -> thu muc phai
    bi siet ACL (icacls SID) de Users/Everyone khong doc duoc."""
    text = _read("5-lich-backup.ps1")
    assert "icacls" in text
    assert "/inheritance:r" in text
    assert "S-1-5-18" in text and "S-1-5-32-544" in text   # SID, locale-safe


def test_all_expected_scripts_exist():
    present = set(_scripts())
    missing = [s for s in EXPECTED_SCRIPTS if s not in present]
    assert missing == [], f"missing deployment scripts: {missing}"


@pytest.mark.parametrize("name", EXPECTED_SCRIPTS)
def test_scripts_are_pure_ascii(name):
    """Non-ASCII in a .ps1 breaks Windows PowerShell 5.1 parsing when the
    file has no BOM."""
    path = os.path.join(DEPLOY_DIR, name)
    with open(path, "rb") as f:
        raw = f.read()

    non_ascii = [(i, b) for i, b in enumerate(raw) if b > 127]
    assert non_ascii == [], (
        f"{name} contains non-ASCII bytes at offsets "
        f"{[i for i, _ in non_ascii[:5]]} — PowerShell 5.1 will misparse it"
    )


@pytest.mark.parametrize("name", EXPECTED_SCRIPTS)
def test_scripts_have_no_bom(name):
    """A BOM would also work, but mixing conventions invites confusion —
    ASCII-only is the rule here."""
    with open(os.path.join(DEPLOY_DIR, name), "rb") as f:
        assert not f.read(3).startswith(b"\xef\xbb\xbf")


@pytest.mark.parametrize("name", EXPECTED_SCRIPTS)
def test_scripts_set_error_action_stop(name):
    """Without this, a failed step keeps going and can leave a half-
    installed server that looks successful."""
    with open(os.path.join(DEPLOY_DIR, name), encoding="ascii") as f:
        assert "$ErrorActionPreference = 'Stop'" in f.read()


def test_caddyfile_example_exists_and_binds_loopback():
    path = os.path.join(DEPLOY_DIR, "Caddyfile.example")
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "app.lttstudios.com" in content
    # The app must never be proxied from a public bind address.
    #
    # Asserted on the loopback prefix, not on a specific port number: the port
    # is a deployment detail that legitimately changes (it moved 8000 -> 8100
    # when this host turned out to already run another service on 8000), while
    # "never proxy a publicly-bound address" is the actual invariant. Pinning
    # the number made a routine port change look like a security regression.
    assert "reverse_proxy 127.0.0.1:" in content
    for public_bind in ("reverse_proxy 0.0.0.0:", "reverse_proxy :"):
        assert public_bind not in content, public_bind


def test_no_secret_values_in_deploy_scripts():
    """Scripts may reference secret NAMES, never values."""
    for name in _scripts() + ["Caddyfile.example"]:
        path = os.path.join(DEPLOY_DIR, name)
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        for var in ("LTT_SESSION_SECRET", "LTT_ADMIN_PASSWORD_HASH",
                    "LTT_TOKEN_ENCRYPTION_KEY"):
            for line in content.splitlines():
                if var not in line or "=" not in line:
                    continue
                tail = line.split(var, 1)[1].lstrip()
                if not tail.startswith("="):
                    continue
                # Strip PowerShell array/string punctuation so only the
                # assigned value remains:  'LTT_X=',  ->  ''
                assigned = tail[1:].strip().strip("'\"").rstrip(",").strip("'\"")
                assert assigned == "", (
                    f"{name}: {var} must ship empty, got {assigned!r}"
                )


# ─── Server 2016 bootstrap ─────────────────────────────────────────────────────

def test_server2016_bootstrap_exists_and_is_ascii():
    path = os.path.join(DEPLOY_DIR, "bootstrap-server2016.ps1")
    assert os.path.exists(path)
    with open(path, "rb") as f:
        assert [b for b in f.read() if b > 127] == []


def test_server2016_bootstrap_handles_the_2016_specific_gaps():
    """Server 2016 has no OpenSSH Feature-on-Demand and defaults to TLS 1.0
    for web requests. Both break a naive install."""
    with open(os.path.join(DEPLOY_DIR, "bootstrap-server2016.ps1"), encoding="ascii") as f:
        src = f.read()

    assert "Tls12" in src, "Server 2016 defaults to TLS 1.0; downloads fail without this"
    assert "Win32-OpenSSH" in src, "OpenSSH must come from GitHub on Server 2016"
    assert "install-sshd.ps1" in src
    assert "administrators_authorized_keys" in src, (
        "admin accounts use this file, not ~/.ssh/authorized_keys"
    )
    assert "icacls" in src, "OpenSSH ignores the key file if permissions are too open"
    assert "DefaultShell" in src, "without this an SSH session lands in cmd.exe"


def test_server2016_bootstrap_pins_python_312_not_313():
    """Server 2016 runs the Windows 10 1607 kernel; 3.12 is the last line
    well-tested there, and the app only needs 3.10+."""
    with open(os.path.join(DEPLOY_DIR, "bootstrap-server2016.ps1"), encoding="ascii") as f:
        src = f.read()
    assert "3.12" in src
    assert "$PythonVersion = '3.13" not in src
