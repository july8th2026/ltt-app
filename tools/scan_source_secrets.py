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
    # Cay lam viec cua phien Codex (.codex/worktrees/*): la BAN SAO cua chinh kho
    # nay, da duoc quet o cay goc; giu lai chi lam may quet bao trung + trip vi
    # file vendor (pako/zlib). Doi xung voi ".claude" ngay tren.
    ".codex",
    # Bao cao cua agent (.superpowers/sdd/*): tep LAM VIEC, nam trong .gitignore
    # nen khong bao gio len kho hay len production. Chung ghi BANG CHUNG do duoc
    # — md5, sha, checksum — va do chinh la thu lam trip `bare_32_char_hex`
    # (24/09: mot md5 chung minh HTML /gia-api khong doi bi bao la secret).
    # Doi xung voi ".claude" va ".codex" ngay tren: cung la thu muc cong cu, cung
    # khong phai nguon.
    ".superpowers",
    # Engine vendored tu D:/FULL AUTO VIDEO (Tao Clip ngan). Ma van hanh cua ben thu
    # ba (khong chua secret cua ta — luong lam-file-truc-tiep khong can key); co chuoi
    # hex 32 ky tu trong VI DU tai lieu (sha256 rut gon) lam trip may quet.
    "cutclipshort",
    # Ngu lieu do token (Task 7, tests/fixtures/ngu_lieu_token): hex.json CO Y la
    # chuoi hex 32 ky tu ngau nhien do sinh.py tao, so voi dem that cua engine.
    "ngu_lieu_token",
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

#: Hai HINH DANG cua mot chuoi 32 hex **khong phai bi mat**, nhan dien bang
#: NGU CANH ngay tren cung dong.
#:
#: 🔴 Vi sao thu hep theo HINH DANG chu khong mien tru ca THU MUC. `EXCLUDED_DIR_NAMES`
#:    o tren da phinh ra vi moi lan gap bao dong gia lai them mot thu muc — va moi
#:    thu muc them vao la mot vung **khong con duoc quet**. Neu mot khoa that lot
#:    vao `.superpowers/` hay `docs/` thi khong cua nao keu. Thu hep theo hinh dang
#:    giu nguyen do phu: moi tep van duoc quet, chi hai DANG cu the duoc tha.
#:
#: ⛔ Ca hai mau deu doi NGU CANH, khong chi doi hinh chuoi hex — mot chuoi hex
#:    tran, khong tien to, khong ten khoa, **van bi bat**.
KHONG_PHAI_BI_MAT = (
    # `vc_<32 hex>` — ma dinh danh CONG KHAI cua clip giong (`UU_TIEN_KHO_CHUNG`
    # trong `rang_giong.py` ghi kem ten nguoi: Owen, Clara). No duoc gui cho
    # trinh duyet cua khach, nen no khong the la bi mat.
    re.compile(r"(?i)vc_[0-9a-f]{32}"),
    # Gia tri cua mot khoa ten `*md5*` / `*sha*` / `*checksum*` / `*hash*` /
    # `*van_tay*`: **bang chung do duoc**, dung de chung minh hai tep giong nhau
    # tung byte. Ghi lai chung chinh la muc dich cua tep bang chung.
    re.compile(r'(?i)"[a-z0-9_]*(?:md5|sha\d*|checksum|hash|van_tay)[a-z0-9_]*"'
               r'\s*[:=]\s*"[0-9a-f]{32}"'),
    # Mot bam DA BI CAT de hien thi: `<hex>...<hex>`.
    #
    # ⭐ Bat theo HINH DANG, ⛔ KHONG theo ten khoa. Cho nay la `khoa_chung` —
    #    `hashlib.sha256(...).hexdigest()` cua dau vao giai doan, tuc mot khoa
    #    CACHE theo noi dung (`cache_chung.py:149`). Nhung chu "khoa" la dung thu
    #    may quet NEN nghi, nen tha theo ten la mot tien le xau: lan sau mot bien
    #    ten `khoa_*` that su chua bi mat se di qua.
    # ⭐ Hinh dang `...` o giua thi an toan hon han: mot bi mat viet co `...` o
    #    giua **khong dung duoc nua** — no da mat mot phan. Nen ca khi lo tha
    #    nham, thu tha ra khong phai mot thong tin dung duoc.
    re.compile(r"(?i)[0-9a-f]{4,}\.\.\.[0-9a-f]{4,}"),
)


#: Chu bao "day la mot BAM", va chu bao "day la mot THONG TIN DANG NHAP".
#:
#: ⭐ Dung cho van xuoi va bang markdown, noi khong co cu phap `"khoa": "gia tri"`.
#:    Vi du that: `bam remux toi gian   acd497e...   3205 goi` (`L_FIX_QC_AM.md`).
#: ⛔ Va no doi CA HAI ve: co chu bam **va khong** co chu dang nhap tren cung dong.
#:    Mot dong nhu `api_key sha  <32 hex>` **van bi bat** — dung vay, vi luc do
#:    chu "sha" khong con noi len duoc dieu gi.
_CHU_BAM = re.compile(r"(?i)\b(?:bam|van[_ ]tay|md5|sha\d*|checksum|hash|digest)\b")
_CHU_DANG_NHAP = re.compile(
    r"(?i)\b(?:key|token|secret|password|passwd|pwd|credential|api[_-]?key)\b")


def _duoc_tha(dong: str, vi_tri: int) -> bool:
    """Chuoi hex o `vi_tri` co nam trong mot hinh dang KHONG-phai-bi-mat khong."""
    for mau in KHONG_PHAI_BI_MAT:
        for m in mau.finditer(dong):
            if m.start() <= vi_tri < m.end():
                return True
    # Van xuoi / bang: co chu bao "bam" TRUOC chuoi hex, va khong chu dang nhap nao.
    truoc = dong[:vi_tri]
    return bool(_CHU_BAM.search(truoc)) and not _CHU_DANG_NHAP.search(dong)


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
    if _duoi_thu_vien_nhung(relative):
        return True
    if any(_is_excluded_dir(part) for part in relative.parts[:-1]):
        return True
    if relative.parts and relative.parts[0].lower() == "data":
        # `data/conn/`: bộ công cụ Node (node.exe + npm CLI, ~104 MB) mà lượt
        # cài marketplace vendor về để chạy `npm ci` BÊN TRONG vỏ AppContainer
        # (`platform_core/workflow/marketplace.py`). ⛔ Không phải nguồn:
        #   · `.gitignore:64` ⇒ ⛔ không bao giờ lên kho;
        #   · `robocopy /XD data` của trình cài ⇒ ⛔ không bao giờ lên production.
        # Tài liệu của chính npm CLI có ví dụ cấu hình chứa `private_key_block`
        # ⇒ máy quét báo hai findings cho một tệp tài liệu của bên thứ ba.
        #
        # ⚠️ Loại theo ĐƯỜNG DẪN `data/conn/`, ⛔ không thêm `"conn"` vào
        #    `EXCLUDED_DIRS`: cái sau sẽ làm mù máy quét với **mọi** thư mục tên
        #    `conn` ở bất kỳ đâu, kể cả một thư mục nguồn thật mai này.
        if len(relative.parts) > 1 and relative.parts[1].lower() == "conn":
            return True
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
            if rule.name == "bare_32_char_hex" and _duoc_tha(line, match.start()):
                continue
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
