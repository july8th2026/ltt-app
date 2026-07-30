"""Fail-safe source-boundary secret scanner.

The scanner reports only rule name and file/line metadata. It never prints the
matched value. It is intended as a pre-commit safety gate, not as a replacement
for credential rotation or a dedicated enterprise secret-scanning product.

Usage:
    python tools/scan_source_secrets.py
    python tools/scan_source_secrets.py --root .
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TEXT_EXTENSIONS = {
    "",
    ".bat",
    ".cfg",
    ".conf",
    ".css",
    ".csv",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".spec",
    ".sql",
    ".svg",
    ".toml",
    ".ts",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}

EXCLUDED_DIR_NAMES = {
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "logs",
    "profiles",
    "secrets",
    "temp_videos",
    "temp_videos_test",
}

EXCLUDED_DIR_PREFIXES = (".backup_",)

EXCLUDED_DATA_PATTERNS = (
    re.compile(r"^config(?:\..*)?\.json$", re.IGNORECASE),
    re.compile(r"^retry_.*\.json$", re.IGNORECASE),
    re.compile(r".*\.db$", re.IGNORECASE),
    re.compile(r".*\.sqlite3?$", re.IGNORECASE),
    re.compile(r".*\.enc$", re.IGNORECASE),
    re.compile(r".*\.jsonl$", re.IGNORECASE),
)

PLACEHOLDER_MARKERS = {
    "",
    "changeme",
    "change_me",
    "dummy",
    "example",
    "fake",
    "legacy",
    "mock",
    "none",
    "null",
    "placeholder",
    "redacted",
    "replace_me",
    "sample",
    "secret",
    "synthetic",
    "test",
    "token",
    "your_secret_here",
}


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]
    captured_value_group: int | None = None


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    rule: str


RULES = (
    Rule(
        "private_key_block",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    ),
    Rule("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    Rule("github_token", re.compile(r"\bgh[pousr]_[0-9A-Za-z]{30,}\b")),
    Rule("slack_token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{20,}\b")),
    Rule("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    Rule(
        "facebook_access_token",
        re.compile(r"\bEAA[0-9A-Za-z]{20,}\b"),
    ),
    Rule(
        "jwt_token",
        re.compile(
            r"\beyJ[0-9A-Za-z_-]{8,}\.[0-9A-Za-z_-]{8,}"
            r"\.[0-9A-Za-z_-]{8,}\b"
        ),
    ),
    Rule(
        "generic_secret_assignment",
        re.compile(
            r"""(?ix)
            ["']?
            (?:app_secret|client_secret|access_token|refresh_token|
               relay_secret|api_key|private_key|telegram_bot_token|
               password|passwd)
            ["']?
            \s*[:=]\s*
            ["']([^"'\r\n]{12,})["']
            """
        ),
        captured_value_group=1,
    ),
    Rule(
        "bare_32_char_hex",
        re.compile(r"(?i)(?<![0-9a-f])[0-9a-f]{32}(?![0-9a-f])"),
    ),
)


def _is_excluded_dir(name: str) -> bool:
    return name in EXCLUDED_DIR_NAMES or name.startswith(EXCLUDED_DIR_PREFIXES)


def _is_excluded_file(root: Path, path: Path) -> bool:
    relative = path.relative_to(root)
    if any(_is_excluded_dir(part) for part in relative.parts[:-1]):
        return True
    if relative.parts and relative.parts[0].lower() == "data":
        return any(pattern.fullmatch(path.name) for pattern in EXCLUDED_DATA_PATTERNS)
    return False


def _iter_source_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file() or _is_excluded_file(root, path):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        yield path


def _looks_like_placeholder(value: str) -> bool:
    normalized = re.sub(r"[^a-z0-9_]+", "", value.strip().lower())
    if normalized in PLACEHOLDER_MARKERS:
        return True
    return any(
        marker and marker in normalized for marker in PLACEHOLDER_MARKERS
    )


def _looks_like_generic_secret(value: str) -> bool:
    """Apply a conservative entropy proxy to generic key/value assignments.

    Provider-specific token formats are handled by dedicated rules. Generic
    assignments are reported only when the value resembles machine-generated
    secret material, avoiding help text and obvious synthetic fixtures.
    """
    stripped = value.strip()
    if _looks_like_placeholder(stripped):
        return False
    if len(stripped) < 20 or any(char.isspace() for char in stripped):
        return False
    if len(set(stripped)) < 10:
        return False
    classes = (
        any(char.islower() for char in stripped),
        any(char.isupper() for char in stripped),
        any(char.isdigit() for char in stripped),
        any(not char.isalnum() for char in stripped),
    )
    return sum(classes) >= 2


def _scan_line(path: Path, line_number: int, line: str) -> list[Finding]:
    findings: list[Finding] = []
    for rule in RULES:
        for match in rule.pattern.finditer(line):
            if rule.captured_value_group is not None:
                value = match.group(rule.captured_value_group)
                if not _looks_like_generic_secret(value):
                    continue
            findings.append(Finding(path=path, line=line_number, rule=rule.name))
    return findings


def scan(root: Path) -> tuple[list[Finding], int, int]:
    findings: list[Finding] = []
    files_scanned = 0
    lines_scanned = 0

    for path in _iter_source_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                text = path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                continue
        except OSError:
            continue

        files_scanned += 1
        for line_number, line in enumerate(text.splitlines(), start=1):
            lines_scanned += 1
            findings.extend(_scan_line(path, line_number, line))

    return findings, files_scanned, lines_scanned


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan prospective source files without printing secret values."
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Project root to scan (default: parent of tools directory).",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: scan root is not a directory: {root}")
        return 2

    findings, files_scanned, lines_scanned = scan(root)
    print(f"Scanned files: {files_scanned}")
    print(f"Scanned lines: {lines_scanned}")
    print(f"Findings: {len(findings)}")

    for finding in findings:
        relative = finding.path.relative_to(root)
        print(f"{relative}:{finding.line}: {finding.rule}")

    if findings:
        print("RESULT: FAIL")
        return 1

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
