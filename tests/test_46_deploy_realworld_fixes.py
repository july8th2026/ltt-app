"""
Two bugs found during the first real deployment to a Windows Server 2022
VM. Both only appear on a real target, which is why the earlier local
"clean-install rehearsal" missed them.

  1. tools/doctor.py crashed with UnicodeEncodeError on a fresh Windows
     console (legacy cp1252 codepage) because the report contains
     Vietnamese text and status icons. The diagnostic tool died exactly
     when it was needed to diagnose.

  2. install.ps1 created the data directory but never put a config.json
     in it, so the service started and reported /health/ready = 503
     forever with no obvious cause.
"""
from __future__ import annotations

import os
import subprocess
import sys

DEPLOY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deploy", "windows",
)


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─── Bug 1: doctor must survive a legacy console codepage ─────────────────────

def test_doctor_declares_utf8_hardening():
    with open(os.path.join(_project_root(), "tools", "doctor.py"), encoding="utf-8") as f:
        src = f.read()
    assert "_force_utf8_output" in src
    assert 'errors="replace"' in src


def test_doctor_runs_under_legacy_codepage_without_crashing():
    """Reproduces the real failure: force a legacy ANSI codepage for the
    child process and confirm doctor still produces output and a clean
    exit code instead of a UnicodeEncodeError traceback."""
    env = dict(os.environ)
    # cp1252 is what the Windows Server console used when this crashed.
    env["PYTHONIOENCODING"] = "cp1252"
    env.pop("PYTHONUTF8", None)
    env["LTT_CONFIG_PATH"] = os.path.join(_project_root(), "does_not_exist.json")

    result = subprocess.run(
        [sys.executable, os.path.join("tools", "doctor.py")],
        cwd=_project_root(), capture_output=True, text=True, timeout=120, env=env,
        # The child now emits UTF-8 (that is the fix); decode it as such.
        # Without this the *parent* would fail on cp1252, masking the result.
        encoding="utf-8", errors="replace",
    )

    combined = (result.stdout or "") + (result.stderr or "")
    assert "UnicodeEncodeError" not in combined, combined[-800:]
    assert "Traceback" not in combined, combined[-800:]
    # Exit code 1 is expected (missing config is a blocker) — the point is
    # that it reported rather than crashed.
    assert result.returncode in (0, 1)
    assert result.stdout.strip(), "doctor produced no output"


def test_doctor_json_mode_also_survives_legacy_codepage():
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "cp1252"
    env.pop("PYTHONUTF8", None)

    result = subprocess.run(
        [sys.executable, os.path.join("tools", "doctor.py"), "--json"],
        cwd=_project_root(), capture_output=True, text=True, timeout=120, env=env,
        # The child now emits UTF-8 (that is the fix); decode it as such.
        # Without this the *parent* would fail on cp1252, masking the result.
        encoding="utf-8", errors="replace",
    )
    assert "UnicodeEncodeError" not in (result.stdout + result.stderr)


# ─── Bug 2: install.ps1 must provision config.json ────────────────────────────

def _install_script() -> str:
    with open(os.path.join(DEPLOY_DIR, "install.ps1"), encoding="ascii") as f:
        return f.read()


def test_install_provisions_config_from_example():
    src = _install_script()
    assert "config.example.json" in src, (
        "install.ps1 must seed data\\config.json, otherwise the service "
        "starts but /health/ready returns 503 forever"
    )
    assert "Provisioning runtime configuration" in src


def test_install_never_overwrites_an_existing_config():
    """Overwriting would destroy the operator's real column mapping on
    every update — the mapping that the 2026-07-30 audit showed is
    hand-tuned per sheet tab."""
    src = _install_script()
    idx = src.index("Provisioning runtime configuration")
    section = src[idx: idx + 900]
    assert "if (Test-Path $cfg)" in section
    assert "kept untouched" in section


def test_install_fails_loudly_if_example_config_is_missing():
    src = _install_script()
    assert "throw" in src[src.index("Provisioning runtime configuration"):][:900]


def test_install_script_still_pure_ascii():
    """Regression guard — PowerShell 5.1 misparses non-ASCII .ps1 files."""
    with open(os.path.join(DEPLOY_DIR, "install.ps1"), "rb") as f:
        raw = f.read()
    assert [b for b in raw if b > 127] == []


# ─── Bug 3: an empty data dir must not abort update.ps1 ───────────────────────

def test_backup_treats_empty_data_dir_as_skip_not_error():
    """update.ps1 backs up before touching anything. backup.ps1 used to
    `throw 'Nothing to back up.'` on a fresh install, which aborted the
    entire update — found on the first real deployment."""
    with open(os.path.join(DEPLOY_DIR, "backup.ps1"), encoding="ascii") as f:
        src = f.read()

    assert "throw 'Nothing to back up.'" not in src, (
        "an empty data directory is a legitimate fresh-install state, "
        "not a failure that should abort the caller"
    )
    assert "[SKIP]" in src

    # Truoc H35.9 duong nay la `exit 0`. Khong con nua, va co chu y: ban sao
    # secrets duoc ghi SAU khoi nay, nen thoat som se lam mot may moi cai
    # co app.env nhung KHONG co ban sao nao cua no. Chot bang cau truc:
    # nhanh rong phai la mot `else`, khong duoc thoat khoi script.
    empty_branch = src[src.index("[SKIP]"):]
    assert "exit" not in empty_branch.split("}", 1)[0], (
        "nhanh 'khong co du lieu' khong duoc exit: ban sao secrets nam sau no"
    )
    assert src.index("[SKIP]") < src.index("ltt_secrets_$Stamp"), (
        "khoi secrets phai chay sau nhanh skip, khong bi no cat mat"
    )


def test_update_still_backs_up_before_changing_anything():
    """The skip above must not weaken the real safety property: a populated
    data directory is still backed up before the release is replaced."""
    with open(os.path.join(DEPLOY_DIR, "update.ps1"), encoding="ascii") as f:
        src = f.read()
    backup_at = src.index("backup.ps1")
    extract_at = src.index("Expand-Archive")
    assert backup_at < extract_at, "backup must run before the release is replaced"


def test_update_self_heals_a_missing_config():
    """An install made by an older installer has no config.json; update
    must seed it rather than leaving the service stuck at 503."""
    with open(os.path.join(DEPLOY_DIR, "update.ps1"), encoding="ascii") as f:
        src = f.read()
    assert "Ensuring runtime configuration exists" in src
    assert "config.example.json" in src
    section = src[src.index("Ensuring runtime configuration exists"):][:900]
    assert "if (Test-Path $cfg)" in section
    assert "kept untouched" in section


def test_update_script_still_pure_ascii():
    with open(os.path.join(DEPLOY_DIR, "update.ps1"), "rb") as f:
        assert [b for b in f.read() if b > 127] == []


# ─── doctor must not send operators to the retired desktop app ────────────────

def test_doctor_fix_hints_never_reference_the_desktop_app():
    """The desktop is retired (docs/_luutru/WEB_PARITY_PLAN.md). A fix hint saying
    "open the app" sends the operator somewhere that no longer exists."""
    with open(os.path.join(_project_root(), "tools", "doctor.py"),
              encoding="utf-8") as f:
        src = f.read()
    for phrase in ("Mở app →", "app desktop", "desktop app"):
        assert phrase not in src, f"doctor.py still references the desktop: {phrase!r}"


def test_doctor_explains_a_sheets_403_as_a_sharing_problem():
    """A 403 from Sheets is almost always "the spreadsheet was never shared
    with the service account" — telling the operator to check the file path
    sends them to the wrong place. Found live on the VPS."""
    with open(os.path.join(_project_root(), "tools", "doctor.py"),
              encoding="utf-8") as f:
        src = f.read()
    assert "_service_account_email" in src
    assert "chưa được chia sẻ" in src
    assert "403" in src
