"""
P8 — release artifact build tests.

The exit criterion that matters: "No secret/runtime data exists in the
artifact." A release that carries data/tokens.enc or data/config.json to a
server is a credential leak, and one that carries a database would
overwrite production data on extract (ADR-009).
"""
from __future__ import annotations

import os
import zipfile

import pytest

from tools.build_release import (
    EXCLUDED_DIRS,
    REQUIRED_ENTRIES,
    _is_excluded_dir,
    _is_excluded_file,
    build,
    collect_files,
    scan_for_secrets,
)


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─── exclusion rules ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", [
    "data", "secrets", "logs", "temp_videos", ".git", "__pycache__",
    ".venv", "venv", "dist", "build", "_recovery",
])
def test_sensitive_and_build_dirs_are_excluded(name):
    assert _is_excluded_dir(name) is True


def test_backup_dir_prefix_excluded():
    assert _is_excluded_dir(".backup_multisheet") is True


@pytest.mark.parametrize("name", [
    "tokens.enc", "tiktok_tokens.enc", "content_history.db", "app.sqlite3",
    "audit_log.jsonl", "config.json", "app.env", "creds.token.json",
])
def test_sensitive_files_are_excluded(name):
    assert _is_excluded_file(name) is True


@pytest.mark.parametrize("name", [
    "app.py", "requirements.txt", "config.example.json", "install.ps1",
])
def test_needed_files_are_not_excluded(name):
    assert _is_excluded_file(name) is False


def test_example_config_is_kept_but_real_config_is_not():
    """config.example.json must ship (it is the template); config.json
    must never ship (it holds real credentials)."""
    assert _is_excluded_file("config.example.json") is False
    assert _is_excluded_file("config.json") is True


# ─── collection over the real tree ─────────────────────────────────────────────

def test_collected_files_contain_no_sensitive_paths():
    files = collect_files(_project_root())
    rels = [rel for _full, rel in files]

    for rel in rels:
        low = rel.lower()
        assert not low.startswith("data/"), f"runtime data would ship: {rel}"
        assert not low.startswith("secrets/"), f"secrets would ship: {rel}"
        assert not low.startswith("logs/"), f"logs would ship: {rel}"
        assert not low.endswith(".enc"), f"token store would ship: {rel}"
        assert not low.endswith(".db"), f"database would ship: {rel}"


def test_all_required_entries_are_collected():
    rels = {rel for _full, rel in collect_files(_project_root())}
    missing = [r for r in REQUIRED_ENTRIES if r not in rels]
    assert missing == [], f"release would be unusable, missing: {missing}"


def test_release_contents_pass_the_secret_scanner():
    findings = scan_for_secrets(collect_files(_project_root()))
    assert findings == [], f"{len(findings)} secret finding(s) in release contents"


# ─── end-to-end build ──────────────────────────────────────────────────────────

def test_build_produces_a_usable_archive(tmp_path):
    archive = build(_project_root(), str(tmp_path))

    assert os.path.exists(archive)
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())

    for required in REQUIRED_ENTRIES:
        assert required in names

    for name in names:
        low = name.lower()
        assert not low.startswith(("data/", "secrets/", "logs/"))
        assert not low.endswith((".enc", ".db", ".sqlite3"))


def test_secret_abort_path_reports_location_and_exits(tmp_path, capsys, monkeypatch):
    """The abort branch was dead code until a real finding hit it, and it
    crashed with AttributeError ('line_number'/'rule_name' do not exist on
    Finding) — i.e. the guard failed exactly when it mattered. Exercise it."""
    import tools.build_release as br

    monkeypatch.setattr(br, "scan_for_secrets", lambda files: [_FakeFinding()])

    with pytest.raises(SystemExit) as exc:
        br.build(_project_root(), str(tmp_path))

    assert "1 secret finding" in str(exc.value)
    err = capsys.readouterr().err
    assert "leaked/file.py:7" in err
    assert "generic_secret_assignment" in err
    # Never echo the matched value.
    assert "hunter2" not in err
    assert not list(tmp_path.glob("*.zip")), "no archive may be written on abort"


class _FakeFinding:
    """Mirrors the real Finding attribute names the reporter must use."""
    path = "leaked/file.py"
    line = 7
    rule = "generic_secret_assignment"
    value = "hunter2"


def test_fake_finding_matches_the_real_finding_fields():
    """If Finding is ever renamed, this fails instead of the reporter silently
    going back to crashing only on real findings."""
    from tools.scan_source_secrets import Finding
    real = {f.name for f in Finding.__dataclass_fields__.values()}
    for attr in ("path", "line", "rule"):
        assert attr in real, f"reporter reads Finding.{attr}, which no longer exists"
