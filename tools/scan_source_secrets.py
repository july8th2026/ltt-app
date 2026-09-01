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
    "node_modules",
    "profiles",
    "secrets",
    "temp_videos",
    "temp_videos_test",
    # Snapshot/log tam cua Playwright MCP (dieu khien trinh duyet). Khong phai
    # source; chua nhieu chuoi hex 32 ky tu tu dashboard lam trip may quet.
    ".playwright-mcp",
    ".playwright-cli",
    # Runtime-only browser/test fixtures. These directories are never source
    # and may contain authenticated Chromium profile material.
    "tmp",
    "test-results",
    ".claude",
    # Engine vendored tu D:/FULL AUTO VIDEO (Tao Clip ngan). Ma van hanh cua ben thu
    # ba (khong chua secret cua ta — luong lam-file-truc-tiep khong can key); co chuoi
    # hex 32 ky tu trong VI DU tai lieu (sha256 rut gon) lam trip may quet.
    "cutclipshort",
}

EXCLUDED_DIR_PREFIXES = (".backup_",)

# Generated, deterministic mirror of repository sources. Scanning it would
# duplicate every finding from the original file and would also re-surface the
# documented synthetic hashes in the already-excluded vendored cutclipshort
# tree. Its inputs are scanned at their original paths; profile scope and
# freshness are independently enforced by test_177 and tools/gate.py.
EXCLUDED_FILE_NAMES = {"ho_so_he_thong.txt"}

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
               session_secret|token_encryption_key|encryption_key|
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


def _duoi_thu_vien_nhung(relative: Path) -> bool:
    """`server/static/**/vendor/**` — thu vien ben thu ba nhung nguyen ban.

    HEP CO Y. Loai tru ca `server/static/` thi de hon nhung sai: do la cho rat
    de co nguoi vo tinh de lo mot khoa trong mot tep JS cau hinh, va mot bo quet
    bi noi rong la mot bo quet da tat.

    Vi sao khong sua thang file vendor: no la ma nguyen ban cua ben thu ba. Sua
    no la tao mot ban re nhanh im lang, va lan cap nhat thu vien sau se ghi de
    mat — roi gate lai do ma khong ai nho vi sao. (noVNC v1.7.0 nhung 24/08:
    `vendor/pako/lib/zlib/trees.js` co bang hang so cua thuat toan nen, 32 ky tu
    hex vi no la DU LIEU chu khong phai vi no la khoa.)
    """
    phan = relative.as_posix()
    return phan.startswith("server/static/") and "/vendor/" in phan


def _is_excluded_file(root: Path, path: Path) -> bool:
    relative = path.relative_to(root)
    if path.name in EXCLUDED_FILE_NAMES:
        return True
    if _duoi_thu_vien_nhung(relative):
        return True
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


#: Mot dong CHECKSUM theo khuon `md5sum` / `sha1sum` / `certutil`:
#:
#:     d41d8cd9...ecf8427e *video.mp4
#:     d41d8cd9...ecf8427e  video.mp4
#:
#: (vi du tren CO Y viet tat: mot chuoi 32 hex THAT o day se tu
#:  kich hoat chinh luat nay — da dinh mot lan khi viet no.)
#:
#: 🔴 Vi sao dung mot phep mien tru RIENG chu khong noi long luat hex:
#:    mot checksum **khong bao gio la bi mat** — no la ban tom tat cong
#:    khai cua mot tep, va viec cua no la duoc cong bo. Nhung mot chuoi 32
#:    hex tran thi RAT co the la mot khoa API, nen luat kia phai giu nguyen
#:    do gat.
#:
#: ⭐ Khuon nay khong nhap nhang: bam, khoang trang, roi mot TEN TEP co
#:    duoi. Mot khoa API khong nam canh mot ten tep nhu vay.
#:
#: ⚠️ Da bat gap that: ba dong md5 cua ba tep .mp4 trong mot bao cao lam do
#:    gate chung cua MOI phien, va chung khong phai bi mat gi ca.
_DONG_CHECKSUM = re.compile(
    r"^\s*[0-9a-fA-F]{32,128}\s+\*?[\w.@+-]+\.[A-Za-z0-9]{1,8}\s*$")


def _scan_line(path: Path, line_number: int, line: str) -> list[Finding]:
    findings: list[Finding] = []
    la_checksum = bool(_DONG_CHECKSUM.match(line))
    for rule in RULES:
        if la_checksum and rule.name == "bare_32_char_hex":
            continue
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
