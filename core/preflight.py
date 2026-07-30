"""
preflight.py — verify a config's column mapping against a real sheet tab
before a run starts (PA-3).

Motivation (docs/AUDIT_REPORT.md finding B3): the live audit found 0 of 26
tabs matched the configured column names. The mandatory `col_schedule_time`
was configured as `schedule_time_fb_dai` while the default tab actually
uses `schedule_time` — a one-word difference that surfaced only as a
runtime error mid-run, and `col_error` pointed at a column that does not
exist anywhere, silently disabling error write-back.

This module turns that class of mistake into an up-front, actionable
report: what is missing, how bad it is, and which existing header was
probably meant.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    ERROR   = "error"     # the run cannot work at all
    WARNING = "warning"   # the run works but loses something important


# Columns the runner cannot function without.
# Kept in sync with utils/sheet_client.get_next_pending_row(), which raises
# when either of these is absent.
MANDATORY_COLUMNS = (
    ("col_schedule_time", "lịch đăng — bot chỉ xử lý row đã đặt lịch"),
    ("col_status",        "trạng thái — bot không biết row nào đã xử lý"),
)

# Columns whose absence degrades the run without stopping it. The
# consequence text matters more than the column name: mark_done/mark_error
# silently skip missing columns, so an operator otherwise sees rows change
# state with no explanation.
IMPORTANT_COLUMNS = (
    ("col_video_drive", "link video nguồn — không có thì không tải được video"),
    ("col_error",       "thông báo lỗi sẽ KHÔNG được ghi ngược lại sheet"),
    ("col_fb_link",     "link bài đăng sẽ không được ghi lại"),
    ("col_title",       "tiêu đề bài đăng sẽ trống"),
)


@dataclass(frozen=True)
class Finding:
    severity:    Severity
    config_key:  str
    configured:  str          # the column name the config asks for
    consequence: str
    suggestion:  str = ""     # closest actual header, if one looks similar

    def format(self) -> str:
        line = f"[{self.severity.value.upper()}] {self.config_key} = '{self.configured}' không có trong sheet"
        line += f"\n    → {self.consequence}"
        if self.suggestion:
            line += f"\n    → Ý bạn là '{self.suggestion}'?"
        return line


@dataclass
class PreflightResult:
    tab:      str
    headers:  list = field(default_factory=list)
    findings: list = field(default_factory=list)

    @property
    def errors(self) -> list:
        return [f for f in self.findings if f.severity is Severity.ERROR]

    @property
    def warnings(self) -> list:
        return [f for f in self.findings if f.severity is Severity.WARNING]

    @property
    def ok(self) -> bool:
        """True when nothing blocks a run. Warnings do not block."""
        return not self.errors

    def format(self) -> str:
        if not self.findings:
            return f"✅ Tab '{self.tab}': tất cả cột khớp cấu hình."
        head = (
            f"Tab '{self.tab}': {len(self.errors)} lỗi, "
            f"{len(self.warnings)} cảnh báo"
        )
        return "\n".join([head] + [f.format() for f in self.findings])


def _suggest(configured: str, headers: list) -> str:
    """Closest existing header name, or '' when nothing is close enough.

    cutoff=0.6 is deliberately loose enough to catch the real audit case
    ('schedule_time_fb_dai' vs 'schedule_time') without proposing an
    unrelated column for a genuine typo-free mismatch.
    """
    if not configured or not headers:
        return ""
    matches = difflib.get_close_matches(configured, headers, n=1, cutoff=0.6)
    return matches[0] if matches else ""


def check_columns(config: dict, headers: list, *, tab: str = "") -> PreflightResult:
    """Compare a config's column mapping against a tab's real headers.

    Pure function — takes headers as data so it is testable without any
    network access, and so callers can reuse headers they already fetched.
    """
    headers = [str(h).strip() for h in headers if str(h).strip()]
    result = PreflightResult(tab=tab, headers=headers)

    for severity, columns in (
        (Severity.ERROR,   MANDATORY_COLUMNS),
        (Severity.WARNING, IMPORTANT_COLUMNS),
    ):
        for key, consequence in columns:
            configured = str(config.get(key, "") or "").strip()
            if not configured:
                result.findings.append(Finding(
                    severity=severity, config_key=key, configured="(chưa đặt)",
                    consequence=consequence,
                ))
                continue
            if configured in headers:
                continue
            result.findings.append(Finding(
                severity=severity, config_key=key, configured=configured,
                consequence=consequence,
                suggestion=_suggest(configured, headers),
            ))

    return result


def check_tab(config: dict, sheet_client, tab: str) -> PreflightResult:
    """Fetch headers for *tab* via an already-connected SheetClient, then
    run check_columns(). Kept separate from check_columns so the pure
    comparison stays network-free."""
    sheet_client.switch_tab(tab)
    return check_columns(config, sheet_client.get_header_names(), tab=tab)
