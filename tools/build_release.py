"""
build_release.py — produce a deployable release archive (P8).

Ships source + deploy scripts only. Runtime data, secrets, tokens,
databases, logs, caches and build artifacts are excluded, so a release can
never carry a credential to the server and can never overwrite production
data on extract (ADR-009).

The archive is scanned for secrets before it is written; a finding aborts
the build rather than producing a poisoned artifact.

Usage:
    python tools/build_release.py                 # -> dist/ltt-release-<version>.zip
    python tools/build_release.py --output C:\\Temp
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Directories never included, at any depth.
EXCLUDED_DIRS = {
    ".git", ".pytest_cache", ".venv", "venv", "__pycache__", "build", "dist",
    "data", "secrets", "logs", "profiles", "temp_videos", "temp_videos_test",
    "_recovery", "node_modules", ".claude",
    # Snapshot/log tam cua Playwright MCP - khong bao gio thuoc release, va chua
    # nhieu chuoi hex lam trip may quet secret. Chi la rac dieu khien trinh duyet.
    ".playwright-mcp",
}

EXCLUDED_DIR_PREFIXES = (".backup_",)

# Files never included, matched on basename.
EXCLUDED_FILES = {
    "config.json", ".env", "app.env",
}

EXCLUDED_SUFFIXES = (
    ".enc", ".db", ".sqlite", ".sqlite3", ".jsonl", ".log", ".pyc",
    ".zip", ".token.json",
)

# Directories that MUST be present in the archive for it to be usable.
REQUIRED_ENTRIES = (
    "server/app.py",
    "core/worker_app.py",
    "requirements.txt",
    "requirements-server.txt",
    "deploy/windows/install.ps1",
    "tools/doctor.py",
)


def _version() -> str:
    try:
        from version import APP_VERSION
        return str(APP_VERSION)
    except Exception:
        return "0.0.0"


def _is_excluded_dir(name: str) -> bool:
    return name in EXCLUDED_DIRS or name.startswith(EXCLUDED_DIR_PREFIXES)


def _is_excluded_file(name: str) -> bool:
    return name in EXCLUDED_FILES or name.lower().endswith(EXCLUDED_SUFFIXES)


def collect_files(root: str) -> list:
    collected = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not _is_excluded_dir(d)]
        for fn in filenames:
            if _is_excluded_file(fn):
                continue
            full = os.path.join(dirpath, fn)
            collected.append((full, os.path.relpath(full, root).replace("\\", "/")))
    return sorted(collected, key=lambda p: p[1])


def scan_for_secrets(files: list) -> list:
    """Run the repo's own scanner rules over exactly what will ship."""
    from pathlib import Path

    from tools.scan_source_secrets import TEXT_EXTENSIONS, _scan_line

    findings = []
    for full, rel in files:
        if os.path.splitext(rel)[1].lower() not in TEXT_EXTENSIONS:
            continue
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as f:
                for lineno, line in enumerate(f, start=1):
                    findings.extend(_scan_line(Path(rel), lineno, line))
        except OSError:
            continue
    return findings


def build(root: str, output_dir: str) -> str:
    files = collect_files(root)

    missing = [
        req for req in REQUIRED_ENTRIES
        if not any(rel == req for _full, rel in files)
    ]
    if missing:
        raise SystemExit(f"Release would be incomplete — missing: {missing}")

    findings = scan_for_secrets(files)
    if findings:
        # Report location only; never echo the matched value.
        for f in findings[:20]:
            print(f"  SECRET: {f.path}:{f.line}: {f.rule}", file=sys.stderr)
        raise SystemExit(
            f"Aborted — {len(findings)} secret finding(s) in the release contents."
        )

    os.makedirs(output_dir, exist_ok=True)
    archive = os.path.join(output_dir, f"ltt-release-{_version()}.zip")

    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for full, rel in files:
            zf.write(full, rel)

    digest = hashlib.sha256()
    with open(archive, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)

    size_mb = os.path.getsize(archive) / (1024 * 1024)
    print(f"Release : {archive}")
    print(f"Files   : {len(files)}")
    print(f"Size    : {size_mb:.1f} MB")
    print(f"SHA-256 : {digest.hexdigest()}")
    print("Secret scan: PASS (0 findings)")
    return archive


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a deployable release archive")
    parser.add_argument("--output", default="dist")
    args = parser.parse_args(argv)

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build(root, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
