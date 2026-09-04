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
import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Directories never included, at any depth.
EXCLUDED_DIRS = {
    ".git", ".pytest_cache", ".venv", "venv", "__pycache__", "build", "dist",
    "data", "secrets", "logs", "profiles", "temp_videos", "temp_videos_test",
    "_recovery", "node_modules", ".claude",
    # Benchmark captures are evidence, not runtime code.  The RTX canary set
    # is ~2.8 GB and must never turn a normal code release into a multi-GB
    # upload; evidence remains under docs/.codex and the benchmark directories.
    "bench",
    # Snapshot/log tam cua Playwright MCP - khong bao gio thuoc release, va chua
    # nhieu chuoi hex lam trip may quet secret. Chi la rac dieu khien trinh duyet.
    ".playwright-mcp", ".playwright-cli", "tmp", "test-results",
}

EXCLUDED_DIR_PREFIXES = (".backup_",)

# Files never included, matched on basename.
EXCLUDED_FILES = {
    "config.json", ".env", "app.env",
}

EXCLUDED_SUFFIXES = (
    ".enc", ".db", ".sqlite", ".sqlite3", ".jsonl", ".log", ".pyc",
    ".zip", ".token.json", ".tsbuildinfo",
)

# Directories that MUST be present in the archive for it to be usable.
REQUIRED_ENTRIES = (
    "server/app.py",
    "job_worker.py",
    "requirements.txt",
    "requirements-server.txt",
    "deploy/windows/install.ps1",
    "tools/doctor.py",
    "frontend/agent-canvas/package.json",
    "frontend/agent-canvas/package-lock.json",
    "server/static/agent-canvas/.vite/manifest.json",
    "server/static/agent-canvas/build-meta.json",
    "frontend/autosub-studio/package.json",
    "frontend/autosub-studio/package-lock.json",
    "server/static/autosub-studio/.vite/manifest.json",
    "server/static/autosub-studio/build-meta.json",
    "frontend/prompt-ai-ommi/package.json",
    "frontend/prompt-ai-ommi/package-lock.json",
    "server/static/prompt-ai-ommi/.vite/manifest.json",
    "server/static/prompt-ai-ommi/build-meta.json",
    "frontend/chatltt/package.json",
    "frontend/chatltt/package-lock.json",
    "server/static/chatltt/.vite/manifest.json",
    "server/static/chatltt/build-meta.json",
)

CANVAS_SOURCE = "frontend/agent-canvas"
CANVAS_OUTPUT = "server/static/agent-canvas"
AUTOSUB_SOURCE = "frontend/autosub-studio"
AUTOSUB_OUTPUT = "server/static/autosub-studio"
OMMI_SOURCE = "frontend/prompt-ai-ommi"
OMMI_OUTPUT = "server/static/prompt-ai-ommi"
CHATLTT_SOURCE = "frontend/chatltt"
CHATLTT_OUTPUT = "server/static/chatltt"

#: Node pin cho MOI bundle. Doi o day thi doi luon .nvmrc va package.json cua
#: tung frontend — ba cho phai khop, va test_95 chot dieu do.
PINNED_NODE = "24.17.0"
CANVAS_IGNORED_FILES = {
    "tsconfig.app.tsbuildinfo", "tsconfig.node.tsbuildinfo",
    "vite.config.d.ts", "vite.config.js",
}


def _frontend_source_sha256(root: str, relative_source: str) -> str:
    """Hash the exact frontend inputs used by write-build-meta.mjs."""
    source = os.path.join(root, relative_source)
    digest = hashlib.sha256()
    inputs = []
    for dirpath, dirnames, filenames in os.walk(source):
        dirnames[:] = sorted(d for d in dirnames if d not in {"node_modules", ".pytest_cache"})
        for name in filenames:
            if name not in CANVAS_IGNORED_FILES:
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, source).replace("\\", "/")
                inputs.append((rel, full))
    for rel, full in sorted(inputs):
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        with open(full, "rb") as handle:
            digest.update(handle.read())
        digest.update(b"\0")
    return digest.hexdigest()


def canvas_source_sha256(root: str) -> str:
    return _frontend_source_sha256(root, CANVAS_SOURCE)


def ommi_source_sha256(root: str) -> str:
    return _frontend_source_sha256(root, OMMI_SOURCE)


def autosub_source_sha256(root: str) -> str:
    return _frontend_source_sha256(root, AUTOSUB_SOURCE)


def chatltt_source_sha256(root: str) -> str:
    return _frontend_source_sha256(root, CHATLTT_SOURCE)


def _verify_one_frontend(root: str, *, source: str, output: str,
                         node: str, digest: str) -> None:
    meta_path = os.path.join(root, output, "build-meta.json")
    manifest_path = os.path.join(root, output, ".vite", "manifest.json")
    try:
        with open(meta_path, encoding="utf-8") as handle:
            meta = json.load(handle)
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"{source} bundle metadata is invalid: {exc}") from exc
    if meta != {"schema": 1, "source_sha256": digest,
                "node": node, "sourcemap": False}:
        raise SystemExit(f"{source} bundle is stale or built with the wrong Node")
    entry = manifest.get("src/main.tsx")
    if not isinstance(entry, dict) or not entry.get("isEntry"):
        raise SystemExit(f"{source} manifest has no src/main.tsx entry")
    assets = [entry.get("file"), *entry.get("css", [])]
    hashed = re.compile(r"^assets/.+-[A-Za-z0-9_-]{8,}\.(?:js|css)$")
    for asset in assets:
        if not isinstance(asset, str) or not hashed.fullmatch(asset):
            raise SystemExit(f"{source} manifest contains an unhashed asset: {asset!r}")
        if not os.path.isfile(os.path.join(root, output, *asset.split("/"))):
            raise SystemExit(f"{source} bundle asset is missing: {asset}")
    for dirpath, _dirs, filenames in os.walk(os.path.join(root, output)):
        if any(name.endswith(".map") for name in filenames):
            raise SystemExit(f"{source} source map found in release bundle: {dirpath}")


def verify_frontend_bundle(root: str) -> None:
    """Reject stale, incomplete, or development-only frontend bundles."""
    _verify_one_frontend(root, source=CANVAS_SOURCE, output=CANVAS_OUTPUT,
                         node=PINNED_NODE, digest=canvas_source_sha256(root))
    _verify_one_frontend(root, source=AUTOSUB_SOURCE, output=AUTOSUB_OUTPUT,
                         node=PINNED_NODE, digest=autosub_source_sha256(root))
    _verify_one_frontend(root, source=OMMI_SOURCE, output=OMMI_OUTPUT,
                         node=PINNED_NODE, digest=ommi_source_sha256(root))
    _verify_one_frontend(root, source=CHATLTT_SOURCE, output=CHATLTT_OUTPUT,
                         node=PINNED_NODE, digest=chatltt_source_sha256(root))


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

    from tools.scan_source_secrets import (TEXT_EXTENSIONS, _is_excluded_dir,
                                           _is_excluded_file as scanner_excludes_file,
                                           _scan_line)

    findings = []
    for full, rel in files:
        if os.path.splitext(rel)[1].lower() not in TEXT_EXTENSIONS:
            continue
        # Generated profile mirrors the selected repository sources. Originals
        # are scanned below at their canonical paths, so scanning the mirror
        # would duplicate results (and resurrect samples from excluded vendor
        # code). The file still ships and is freshness/integrity checked.
        if scanner_excludes_file(Path("."), Path(rel)):
            continue
        # Ton trong cung danh sach loai tru dir cua scan_source_secrets (vd engine
        # vendored `cutclipshort` — ma ben thu ba, co vi du sha256 rut gon lam trip).
        # File van SHIP trong archive; chi khong quet secret.
        if any(_is_excluded_dir(p) for p in Path(rel).parts):
            continue
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as f:
                for lineno, line in enumerate(f, start=1):
                    findings.extend(_scan_line(Path(rel), lineno, line))
        except OSError:
            continue
    return findings


def build(root: str, output_dir: str) -> str:
    verify_frontend_bundle(root)
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
