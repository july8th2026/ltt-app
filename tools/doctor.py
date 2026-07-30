"""
doctor.py — one-command health report (PA-4).

Answers "can this bot actually publish right now?" without a debugging
session. Every check the 2026-07-29 audit had to perform by hand is
automated here.

Never prints a token, secret, or credential value — only names, counts,
and states.

Usage:
    python tools/doctor.py                    # config + tokens + workers
    python tools/doctor.py --check-sheet      # also hits the Google Sheets API
    python tools/doctor.py --json             # machine-readable

Exit codes:
    0 = no blocking problem
    1 = at least one blocker (bot cannot publish)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# Allow running as `python tools/doctor.py` from the project root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _force_utf8_output() -> None:
    """Make output safe on a legacy Windows console.

    A fresh Windows Server console runs a legacy codepage (cp1252 / cp437).
    This report contains Vietnamese text and status icons, so printing it
    raised UnicodeEncodeError and killed the process — the diagnostic tool
    crashing exactly when an operator needs it. Reconfiguring to UTF-8 with
    errors="replace" degrades an unprintable glyph to '?' instead.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass   # non-reconfigurable stream (pipe, pytest capture) — fine


_force_utf8_output()

OK    = "ok"
WARN  = "warning"
BLOCK = "blocker"


class Report:
    def __init__(self) -> None:
        self.sections: list[dict] = []

    def add(self, name: str, status: str, detail: str = "", fix: str = "") -> None:
        self.sections.append(
            {"check": name, "status": status, "detail": detail, "fix": fix}
        )

    @property
    def has_blocker(self) -> bool:
        return any(s["status"] == BLOCK for s in self.sections)

    def to_text(self) -> str:
        icon = {OK: "✅", WARN: "⚠️ ", BLOCK: "❌"}
        lines = ["", "=" * 62, "  LTT BOT — BÁO CÁO SỨC KHOẺ", "=" * 62]
        for s in self.sections:
            lines.append(f"{icon[s['status']]} {s['check']}")
            if s["detail"]:
                for d in s["detail"].splitlines():
                    lines.append(f"     {d}")
            if s["fix"]:
                lines.append(f"     → CÁCH SỬA: {s['fix']}")
        lines.append("-" * 62)
        blockers = [s for s in self.sections if s["status"] == BLOCK]
        if blockers:
            lines.append(f"KẾT LUẬN: BOT KHÔNG CHẠY ĐƯỢC — {len(blockers)} lỗi chặn:")
            for b in blockers:
                lines.append(f"  • {b['check']}")
        else:
            warns = [s for s in self.sections if s["status"] == WARN]
            lines.append(
                f"KẾT LUẬN: Không có lỗi chặn. {len(warns)} cảnh báo."
                if warns else "KẾT LUẬN: Tất cả đều tốt."
            )
        lines.append("=" * 62)
        return "\n".join(lines)


# ─── individual checks ────────────────────────────────────────────────────────

def check_environment(report: Report, env: dict) -> None:
    from core.runtime_paths import resolve_runtime_paths
    from core.settings import resolve_environment

    try:
        environment = resolve_environment(env)
    except Exception as exc:
        report.add("Môi trường", BLOCK, str(exc), "Đặt LTT_ENV hợp lệ")
        return
    paths = resolve_runtime_paths(env)
    report.add(
        "Môi trường", OK,
        f"profile={environment.value}\nconfig={paths.config_path}\ndata={paths.data_dir}",
    )


def check_config(report: Report, env: dict) -> dict | None:
    from core.config_validator import ConfigValidationError
    from core.settings import MissingConfigError, load_settings

    try:
        settings = load_settings(env=env)
    except MissingConfigError as exc:
        report.add("Cấu hình", BLOCK, str(exc),
                   "Copy config.example.json thành data/config.json rồi điền giá trị")
        return None
    except ConfigValidationError as exc:
        report.add("Cấu hình", BLOCK, str(exc), "Sửa các trường báo lỗi ở trên")
        return None
    except Exception as exc:
        report.add("Cấu hình", BLOCK, f"{type(exc).__name__}: {exc}")
        return None

    report.add("Cấu hình", OK, f"Đọc và kiểm tra hợp lệ: {settings.paths.config_path}")
    return settings.config


def check_tokens(report: Report) -> None:
    """Reports readability + usable account counts. Never prints a token."""
    specs = [
        ("Tài khoản Facebook", "core.token_store", "TokenStore",
         "Mở /facebook → dán token System User (Business Manager). "
         "Đây là cách kết nối chạy được trên máy chủ, không cần trình duyệt."),
        ("Tài khoản TikTok", "core.tiktok.token_store", "TikTokTokenStore",
         "TikTok bắt buộc OAuth qua trình duyệt — chức năng này đang được "
         "chuyển sang web (xem docs/WEB_PARITY_PLAN.md W5)."),
    ]
    for label, module_name, cls_name, fix in specs:
        try:
            module = __import__(module_name, fromlist=[cls_name])
            store = getattr(module, cls_name)()
        except Exception as exc:
            report.add(label, BLOCK, f"Không mở được kho token: {type(exc).__name__}")
            continue

        if store.is_unreadable:
            report.add(label, BLOCK, store.load_error or "Không đọc được", fix)
            continue

        count = store.count()
        if count == 0:
            report.add(label, BLOCK, "Chưa có tài khoản nào được kết nối.", fix)
        else:
            report.add(label, OK, f"{count} tài khoản đã kết nối.")


def check_workers(report: Report, config: dict | None) -> list:
    from core.worker_store import load_workers

    workers = load_workers()
    if workers:
        detail = "\n".join(
            f"- tab='{w.get('tab','')}' page='{w.get('page','')}'" for w in workers
        )
        report.add("Danh sách worker", OK, f"{len(workers)} worker đã lưu:\n{detail}")
        return workers

    report.add(
        "Danh sách worker", WARN,
        "Chưa lưu worker nào (data/workers.json trống hoặc không có).",
        "Mở /sheet/facebook hoặc /sheet/tiktok → chọn Sheet + Tab + Page → "
        "nhấn '+ Thêm'. Danh sách được lưu và dùng chung.",
    )
    return []


def _service_account_email(config: dict) -> str:
    """client_email from the credentials file. Not a secret, and the
    operator needs it to share the Sheet."""
    import json as _json
    path = str(config.get("google_credentials_path", "") or "")
    if not path or not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return str(_json.load(f).get("client_email", ""))
    except Exception:
        return ""


def check_sheet(report: Report, config: dict, workers: list) -> None:
    from core.preflight import check_tab
    from utils.sheet_client import SheetClient

    try:
        client = SheetClient(config)
        client.connect()
        tabs = client.get_all_tabs()
    except Exception as exc:
        detail = f"{type(exc).__name__}: {str(exc)[:200]}"
        fix = "Kiểm tra google_credentials_path trong Cài đặt"
        if "403" in str(exc) or "does not have permission" in str(exc):
            email = _service_account_email(config)
            fix = (
                "Google Sheet chưa được chia sẻ cho service account. "
                f"Mở Sheet → Share → thêm {email or 'email service account'} "
                "với quyền Editor. Đây là nguyên nhân của gần như mọi lỗi 403."
            )
        report.add("Kết nối Google Sheet", BLOCK, detail, fix)
        return

    report.add("Kết nối Google Sheet", OK, f"{len(tabs)} tab.")

    target_tabs = [w.get("tab", "") for w in workers if w.get("tab")]
    if not target_tabs:
        report.add("Kiểm tra cột của sheet", WARN,
                   "Bỏ qua — chưa có worker nào để biết cần kiểm tra tab nào.")
        return

    for tab in target_tabs:
        if tab not in tabs:
            report.add(f"Cột của tab '{tab}'", BLOCK,
                       "Tab không tồn tại trong spreadsheet.",
                       f"Chọn lại tab; hiện có: {', '.join(tabs[:6])}...")
            continue
        try:
            result = check_tab(config, client, tab)
        except Exception as exc:
            report.add(f"Cột của tab '{tab}'", BLOCK, f"{type(exc).__name__}: {exc}")
            continue
        status = OK if not result.findings else (BLOCK if result.errors else WARN)
        report.add(f"Cột của tab '{tab}'", status, result.format())


# ─── entrypoint ────────────────────────────────────────────────────────────────

def run(check_sheet_flag: bool = False, env: dict | None = None) -> Report:
    env = os.environ if env is None else env
    report = Report()
    check_environment(report, env)
    config = check_config(report, env)
    check_tokens(report)
    workers = check_workers(report, config)
    if check_sheet_flag and config is not None:
        check_sheet(report, config, workers)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LTT bot health report")
    parser.add_argument("--check-sheet", action="store_true",
                        help="Also connect to Google Sheets (slower, needs network)")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    args = parser.parse_args(argv)

    report = run(check_sheet_flag=args.check_sheet)
    if args.json:
        print(json.dumps(report.sections, ensure_ascii=False, indent=2))
    else:
        print(report.to_text())
    return 1 if report.has_blocker else 0


if __name__ == "__main__":
    sys.exit(main())
