"""VPS V4 R6 — the gateway helper can never drop or reassign a protected mapping.

Runs the real `tools/vps_gateway/ltt-gwnat.sh` under Git Bash against a copy
whose system paths point into tmp_path, with `nft`/`ip`/`flock` stubbed. The
live gateway is never touched.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
# Override only to prove the tests fail on a previous helper revision.
SCRIPT = Path(os.environ.get("LTT_TEST_GWNAT_SCRIPT")
              or ROOT / "tools" / "vps_gateway" / "ltt-gwnat.sh")
GIT_BASH = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "bin" / "bash.exe"

PROTECTED_ROWS = "10.50.0.11 203.0.113.11 VM101\n10.50.0.12 203.0.113.12 VM102\n"

def _stub(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_bytes(("#!/bin/bash\n" + body + "\n").encode("ascii"))


def _setup(tmp_path: Path, map_rows: str):
    etc = tmp_path / "etc"
    etc.mkdir()
    (etc / "map").write_bytes(map_rows.encode("ascii"))
    (etc / "protected").write_bytes(PROTECTED_ROWS.encode("ascii"))
    (etc / "netplan").write_bytes(b"# old\n")
    (etc / "nft.conf").write_bytes(b"# old\n")
    run = tmp_path / "run"
    run.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _stub(bin_dir, "flock", "exit 0")
    _stub(bin_dir, "nft", 'if [[ "$*" == "list ruleset" ]]; then echo "table ip gwnat {}"; fi; exit 0')
    _stub(bin_dir, "ip", "exit 0")

    text = SCRIPT.read_text(encoding="ascii")
    for old, new in (
        ("/etc/wireguard/anh-xa-ip.txt", (etc / "map").as_posix()),
        ("/etc/ltt-vps/protected-gwnat.conf", (etc / "protected").as_posix()),
        ("/etc/netplan/60-ip-bo-sung.yaml", (etc / "netplan").as_posix()),
        ("/etc/nftables.conf", (etc / "nft.conf").as_posix()),
        ("/run/lock/ltt-gwnat.lock", (run / "lock").as_posix()),
        ("/run/ltt-gwnat.", (run / "ltt-gwnat.").as_posix()),
    ):
        assert old in text, old
        # Quoted: the temp root may contain spaces; the live paths do not.
        text = text.replace(old, '"' + new + '"')
    script = tmp_path / "ltt-gwnat.sh"
    script.write_bytes(text.encode("ascii"))
    return script, etc / "map", bin_dir


def _run(script: Path, bin_dir: Path, *args: str) -> subprocess.CompletedProcess:
    # Not a skip: a guard that silently stops running protects nothing. The
    # project runs on Windows with Git installed (bánh cóc bỏ qua, test_306).
    assert GIT_BASH.exists(), f"Git Bash is required to execute the helper: {GIT_BASH}"
    env = dict(os.environ)
    env["PATH"] = bin_dir.as_posix() + os.pathsep + env.get("PATH", "")
    command = 'export PATH="{}:$PATH"; bash "{}" {}'.format(
        bin_dir.as_posix(), script.as_posix(), " ".join(args))
    return subprocess.run([str(GIT_BASH), "-c", command], capture_output=True,
                          text=True, timeout=60, env=env)


def test_ensure_new_address_keeps_every_protected_row(tmp_path):
    script, map_file, bin_dir = _setup(tmp_path, PROTECTED_ROWS)
    result = _run(script, bin_dir, "ensure", "203.0.113.20", "10.50.0.20")
    assert result.returncode == 0, result.stderr
    rows = map_file.read_text(encoding="ascii")
    assert "10.50.0.20 203.0.113.20 LTTMANAGED" in rows
    for line in PROTECTED_ROWS.splitlines():
        assert line in rows


@pytest.mark.parametrize("public,private", [
    ("203.0.113.11", "10.50.0.30"),     # protected public address
    ("203.0.113.30", "10.50.0.12"),     # protected private address
])
def test_ensure_refuses_any_protected_address(tmp_path, public, private):
    # The protected row is absent from the map on purpose: the old helper saw
    # no conflict there and would have assigned the address.
    script, map_file, bin_dir = _setup(tmp_path, PROTECTED_ROWS)
    before = map_file.read_bytes()
    result = _run(script, bin_dir, "ensure", public, private)
    assert result.returncode == 5, result.stderr
    assert map_file.read_bytes() == before


def test_any_change_refused_when_map_already_lost_a_protected_row(tmp_path):
    only_one = PROTECTED_ROWS.splitlines()[0] + "\n"
    script, map_file, bin_dir = _setup(tmp_path, only_one)
    before = map_file.read_bytes()
    result = _run(script, bin_dir, "ensure", "203.0.113.20", "10.50.0.20")
    assert result.returncode == 5, result.stderr
    assert map_file.read_bytes() == before


def test_remove_protected_mapping_is_still_refused(tmp_path):
    script, map_file, bin_dir = _setup(tmp_path, PROTECTED_ROWS)
    result = _run(script, bin_dir, "remove", "203.0.113.11", "10.50.0.11")
    assert result.returncode == 5, result.stderr
