"""
content_tools.py — the three Content Vault actions from the desktop Settings
tab (gui/settings_tab.py:815-940).

Ported, not reinvented; the underlying calls are the same
`core.content_vault` / `core.content_calendar` functions. What changes is the
transport:

  * export used `filedialog.asksaveasfilename` and wrote to a path the
    operator picked on the bot's own machine. On a server that path would be
    on the VPS, where nobody can reach it — so the CSV streams to the browser
    as a download instead.
  * import used `filedialog.askopenfilename`; the web takes an upload.
  * both reported through `messagebox`; the web renders into the page.

One desktop limitation is kept deliberately: CSV import parses and previews
but does not write to the Sheet. The desktop docstring is explicit that the
Sheet writer was never built. Pretending otherwise here would silently drop
the operator's rows.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

MAX_IMPORT_BYTES = 5 * 1024 * 1024      # a content calendar is text, not video
PREVIEW_ROWS = 5                        # matches the desktop preview
MAX_ERROR_LINES = 10                    # matches the desktop preview
MAX_DUPLICATE_GROUPS = 15               # matches the desktop preview
MAX_TARGETS_SHOWN = 4                   # matches the desktop preview


def export_filename() -> str:
    """Same naming as the desktop's default filename."""
    return f"content_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"


def export_history_csv() -> tuple[str, int]:
    """(csv_text, row_count).

    `core.content_vault.export_to_csv` writes to a path, so it is given a temp
    file and the bytes are read back — that keeps a single implementation of
    the column layout rather than duplicating it for the web.
    """
    import os
    import tempfile

    from core.content_vault import export_to_csv

    fd, tmp = tempfile.mkstemp(suffix=".csv", prefix="ltt_export_")
    os.close(fd)
    try:
        count = export_to_csv(tmp)
        with open(tmp, "r", encoding="utf-8", newline="") as fh:
            return fh.read(), int(count)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


@dataclass
class DuplicateGroup:
    video_hash: str
    count: int
    targets: list = field(default_factory=list)

    @property
    def hash_short(self) -> str:
        return self.video_hash[:12]

    @property
    def targets_text(self) -> str:
        shown = ", ".join(self.targets[:MAX_TARGETS_SHOWN])
        return shown + ("..." if len(self.targets) > MAX_TARGETS_SHOWN else "")


@dataclass
class DuplicateReport:
    groups: list = field(default_factory=list)
    total: int = 0
    error: str = ""

    @property
    def summary(self) -> str:
        if self.error:
            return self.error
        if not self.total:
            # The desktop's exact framing: no duplicates is good news, and
            # saying so stops the operator hunting for a problem.
            return ("Không có video nào upload lên nhiều target. Đây là setup "
                    "tốt — mỗi page có content riêng.")
        return f"Tìm thấy {self.total} nhóm video dùng cho nhiều target."


def find_duplicates() -> DuplicateReport:
    try:
        from core.content_vault import find_cross_target_duplicates
        raw = find_cross_target_duplicates(min_targets=2) or []
    except Exception as exc:
        return DuplicateReport(error=f"{type(exc).__name__}: {exc}")

    groups = [
        DuplicateGroup(
            video_hash=str(getattr(g, "video_hash", "")),
            count=int(getattr(g, "count", 0)),
            targets=list(getattr(g, "targets", []) or []),
        )
        for g in raw[:MAX_DUPLICATE_GROUPS]
    ]
    return DuplicateReport(groups=groups, total=len(raw))


@dataclass
class ImportReport:
    ok_rows: int = 0
    preview: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    error_overflow: int = 0
    row_overflow: int = 0
    fatal: str = ""

    @property
    def has_result(self) -> bool:
        return bool(self.ok_rows or self.errors or self.fatal)


def import_calendar_csv(filename: str, data: bytes) -> ImportReport:
    """Parse an uploaded content-calendar CSV and report what it contains.

    Deliberately does NOT write to the Sheet — see the module docstring.
    """
    if not filename:
        return ImportReport(fatal="Chưa chọn file CSV.")
    if not filename.lower().endswith(".csv"):
        return ImportReport(fatal="Chỉ nhận file .csv.")
    if not data:
        return ImportReport(fatal="File rỗng.")
    if len(data) > MAX_IMPORT_BYTES:
        return ImportReport(fatal=(
            f"File {len(data) / 1024 / 1024:.1f} MB — vượt giới hạn "
            f"{MAX_IMPORT_BYTES // 1024 // 1024} MB. Lịch content là file "
            f"văn bản, dung lượng này thường là chọn nhầm file."))

    import os
    import tempfile

    from core.content_calendar import import_csv

    fd, tmp = tempfile.mkstemp(suffix=".csv", prefix="ltt_import_")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        result = import_csv(tmp)
    except Exception as exc:
        return ImportReport(fatal=f"{type(exc).__name__}: {exc}")
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass

    rows = list(getattr(result, "rows", []) or [])
    errors = list(getattr(result, "errors", []) or [])
    return ImportReport(
        ok_rows=len(rows),
        preview=[
            f"{getattr(r, 'platform', '?')}/{getattr(r, 'target_page', '') or '?'}"
            f" — {str(getattr(r, 'title', ''))[:40]}"
            for r in rows[:PREVIEW_ROWS]
        ],
        errors=[str(e) for e in errors[:MAX_ERROR_LINES]],
        error_overflow=max(0, len(errors) - MAX_ERROR_LINES),
        row_overflow=max(0, len(rows) - PREVIEW_ROWS),
    )
