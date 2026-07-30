"""
audit_service.py — TikTok audit readiness (web port of gui/audit_tab.py).

`core.tiktok.audit_checklist.run_checklist()` makes 3+ outbound HTTPS calls
(privacy URL HEAD, privacy body GET, terms HEAD) with 6-8s timeouts. The
desktop ran it synchronously on the UI thread and froze for a second or two;
on the web that would block a request and, worse, re-run per page view.

So it runs in a background thread with a cached result, and the page shows
the cached report plus a "refresh" action. That also protects the operator's
own site from being probed on every page load.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from server.services import ui_constants as UI

CACHE_TTL_S = 600          # a checklist result is not volatile


@dataclass
class AuditItem:
    name: str
    result: str            # "PASS" | "WARN" | "FAIL"
    message: str
    fix_hint: str = ""

    @property
    def icon(self) -> str:
        return {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(self.result, "?")

    @property
    def colour(self) -> str:
        return {"PASS": UI.COLORS["green"], "WARN": UI.COLORS["amber"],
                "FAIL": UI.COLORS["red"]}.get(self.result, UI.COLORS["muted2"])

    @property
    def show_fix(self) -> bool:
        return bool(self.fix_hint) and self.result != "PASS"


@dataclass
class AuditReport:
    items: list = field(default_factory=list)
    scopes: list = field(default_factory=list)
    summary: str = ""
    summary_colour: str = ""
    ready: bool = False
    generated_at: float = 0.0
    error: str = ""
    running: bool = False

    @property
    def counts(self) -> dict:
        c = {"PASS": 0, "WARN": 0, "FAIL": 0}
        for i in self.items:
            if i.result in c:
                c[i.result] += 1
        return c

    @property
    def age_text(self) -> str:
        if not self.generated_at:
            return "chưa chạy"
        secs = int(time.time() - self.generated_at)
        if secs < 60:
            return f"{secs} giây trước"
        return f"{secs // 60} phút trước"


SCOPE_EXPLAIN = {
    "user.info.basic": "Đọc username + avatar để hiển thị account đã connect trong bot.",
    "video.upload": "Gửi video vào Inbox của user (Draft mode). User vẫn publish thủ công.",
    "video.publish": "Đăng video trực tiếp từ bot (sau khi user xác nhận từng lần).",
    "video.list": "Đọc danh sách video đã đăng để fetch insights/analytics.",
    "comment.create": "Đăng comment tự động dưới video (theo config Settings).",
}
SCOPE_UNKNOWN = "(custom scope — bot must justify usage)"


class AuditRunner:
    """Cached, single-flight checklist runner."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._report = AuditReport()
        self._inflight = False

    def report(self) -> AuditReport:
        with self._lock:
            self._report.running = self._inflight
            return self._report

    def is_stale(self) -> bool:
        with self._lock:
            if self._inflight:
                return False
            return (time.time() - self._report.generated_at) > CACHE_TTL_S

    def refresh_async(self, config: dict) -> None:
        with self._lock:
            if self._inflight:
                return          # single-flight: drop the duplicate request
            self._inflight = True
        threading.Thread(target=self._run, args=(dict(config),),
                         daemon=True, name="AuditChecklist").start()

    def _run(self, config: dict) -> None:
        report = AuditReport(generated_at=time.time())
        try:
            from core.tiktok.audit_checklist import run_checklist
            raw = run_checklist(config)
            for item in getattr(raw, "items", []):
                report.items.append(AuditItem(
                    name=str(getattr(item, "name", "")),
                    result=_result_name(getattr(item, "result", None)),
                    message=str(getattr(item, "message", "")),
                    fix_hint=str(getattr(item, "fix_hint", "") or ""),
                ))
            report.ready = getattr(raw, "ready_to_submit", None)
            if report.ready is None:
                report.ready = report.counts["FAIL"] == 0
            report.summary, report.summary_colour = _summary(report)
        except Exception as exc:
            report.error = f"{type(exc).__name__}: {exc}"
            report.summary = f"❌ Không chạy được checklist: {report.error}"
            report.summary_colour = UI.COLORS["red"]

        report.scopes = _scopes(config)
        with self._lock:
            self._report = report
            self._inflight = False


def _result_name(value) -> str:
    """ChecklistResult may be an enum; normalise to PASS/WARN/FAIL."""
    name = getattr(value, "name", None) or str(value)
    name = name.rsplit(".", 1)[-1].upper()
    return name if name in ("PASS", "WARN", "FAIL") else "WARN"


def _summary(report: AuditReport) -> tuple[str, str]:
    c = report.counts
    if c["FAIL"]:
        return (f"❌ Chưa submit được — {c['FAIL']} blocking, {c['WARN']} warn, "
                f"{c['PASS']} pass", UI.COLORS["red"])
    if c["WARN"]:
        return (f"🟡 Có thể submit nhưng còn {c['WARN']} cảnh báo "
                f"({c['PASS']} pass, {c['WARN']} warn)", UI.COLORS["amber"])
    return (f"✅ Sẵn sàng submit TikTok audit ({c['PASS']} checks pass)",
            UI.COLORS["green"])


def _scopes(config: dict) -> list:
    raw = str(config.get("tiktok_scopes", "")
              or "user.info.basic,video.upload,video.publish")
    out = []
    for scope in [s.strip() for s in raw.split(",") if s.strip()]:
        out.append({"scope": scope,
                    "explain": SCOPE_EXPLAIN.get(scope, SCOPE_UNKNOWN)})
    return out


_runner = AuditRunner()


def runner() -> AuditRunner:
    return _runner
