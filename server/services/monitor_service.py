"""
monitor_service.py — data for the Monitor page (web port of gui/monitor_tab.py).

Two defects in the desktop tab are FIXED here rather than reproduced (both
found by the parity analysis):

  1. `monitor_tab.py:388` calls `get_fb_default_store()`, but that name is
     only bound inside a different method's local import. At that line it
     raises NameError, which the surrounding bare `except` swallows — so
     `_accounts_by_name` was always empty and the **Pages column always
     rendered 0**. Here the join is done properly.

  2. The `_Empty` fallback used when `collect_snapshot()` raises is missing
     `n_pages_dead`, `n_pages_throttled`, `n_bot_flat_targets`,
     `page_health_warnings` and `time_intel_warnings`, all of which the
     renderer reads — turning one failure into a second AttributeError.
     Here the fallback is fully populated.

Note on data sources: upload metrics, the recent-log ring buffer and the
circuit-breaker state all live in **process memory**. With one orchestrator
process (ADR-005) that is still correct; if the app is ever scaled to
multiple workers these must move to shared storage.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from server.services import ui_constants as UI


@dataclass
class TokenRow:
    name: str
    days: int
    status: str
    pages_selected: int = 0
    pages_total: int = 0

    @property
    def token_text(self) -> str:
        return "∞" if self.days == -1 else f"{self.days} ngày"

    @property
    def colour(self) -> str:
        return {
            "ok": UI.COLORS["green"], "permanent": UI.COLORS["green"],
            "warning": UI.COLORS["amber"], "expired": UI.COLORS["red"],
        }.get(self.status, UI.COLORS["muted2"])


@dataclass
class MetricRow:
    page: str
    uploads_done: int
    avg_wait_s: float
    total_upload_s: float

    @property
    def avg_upload_s(self) -> float:
        return self.total_upload_s / self.uploads_done if self.uploads_done else 0.0


@dataclass
class MonitorData:
    tokens: list = field(default_factory=list)
    token_error: str = ""
    metrics: list = field(default_factory=list)
    antispam_summary: str = "—"
    antispam_colour: str = ""
    antispam_details: list = field(default_factory=list)
    logs: list = field(default_factory=list)


def collect_token_health(config: dict) -> tuple[list, str]:
    """Token expiry per account, joined with its selected-page count.

    The join is the part the desktop got wrong (see module docstring).
    """
    try:
        from core.token_store import get_default_store

        store = get_default_store()
        if getattr(store, "is_unreadable", False):
            # Bail out before importing the refresher: nothing downstream can
            # do anything useful with a store that will not decrypt.
            return [], store.load_error or "Không đọc được kho token."

        from core.token_refresher import TokenRefresher

        # name -> (selected, total). This is the join the desktop lost to a
        # swallowed NameError.
        page_counts = {
            acc.name: (len(acc.get_selected_pages()), len(acc.get_pages_list()))
            for acc in store.all_accounts()
        }

        rows = []
        for entry in TokenRefresher(config, store).health_summary():
            sel, total = page_counts.get(entry.get("name", ""), (0, 0))
            rows.append(TokenRow(
                name=str(entry.get("name", ""))[:40],
                days=int(entry.get("days", 0)),
                status=str(entry.get("status", "")),
                pages_selected=sel, pages_total=total,
            ))
        return rows, ""
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"


def collect_metrics() -> list:
    """Per-page upload metrics for this process (core.rate_limiter)."""
    try:
        from core.rate_limiter import get_global_page_metrics
        snapshot = get_global_page_metrics() or {}
    except Exception:
        return []
    rows = [
        MetricRow(
            page=str(page)[:40],
            uploads_done=int(m.get("uploads_done", 0)),
            avg_wait_s=float(m.get("avg_wait_s", 0.0)),
            total_upload_s=float(m.get("total_upload_s", 0.0)),
        )
        for page, m in snapshot.items()
    ]
    return sorted(rows, key=lambda r: r.page)


def reset_metrics() -> None:
    from core.rate_limiter import reset_global_metrics
    reset_global_metrics()


class _EmptySnapshot:
    """Fully-populated fallback.

    The desktop's equivalent omitted five attributes the renderer reads, so
    a failed snapshot produced a second, more confusing AttributeError.
    """
    n_critical_tokens = 0
    n_warn_tokens = 0
    token_messages: list = []
    open_breakers: list = []
    halfopen_breakers: list = []
    total_attempts_7d = 0
    total_successes_7d = 0
    success_rate_7d = 0.0
    targets_with_abuse: list = []
    targets_with_rate: list = []
    recommendations: list = []
    total_content_records = 0
    page_health_warnings: list = []
    n_pages_throttled = 0
    n_pages_dead = 0
    meta_app_status = "unknown"
    meta_app_message = ""
    meta_app_pool_healthy = 0
    meta_app_pool_total = 0
    tiktok_app_status = "unknown"
    tiktok_app_message = ""
    tiktok_client_pool_healthy = 0
    tiktok_client_pool_total = 0
    time_intel_warnings: list = []
    n_bot_flat_targets = 0


def collect_antispam(config: dict) -> tuple[str, str, list]:
    """(summary, colour, detail lines) — mirrors _render_antispam."""
    failure = ""
    format_oneline = None
    try:
        from core.anti_spam_analytics import collect_snapshot, format_oneline
        snap = collect_snapshot(config)
    except Exception as exc:
        # Keep rendering from the fallback instead of bailing out — that is
        # exactly where the desktop raised its second AttributeError.
        snap = _EmptySnapshot()
        failure = f"⚠ Không thu thập được số liệu chống spam: {type(exc).__name__}: {exc}"

    if failure:
        summary = failure
    else:
        try:
            summary = format_oneline(snap)
        except Exception as exc:
            summary = f"⚠ Không định dạng được số liệu: {type(exc).__name__}: {exc}"
            failure = summary

    def n(attr, default=0):
        return getattr(snap, attr, default)

    if failure:
        colour = UI.COLORS["amber"]
    elif (n("n_critical_tokens") or n("targets_with_abuse")
            or n("n_pages_dead") or n("n_pages_throttled")):
        colour = UI.COLORS["red"]
    elif (n("n_warn_tokens") or n("open_breakers")
          or n("targets_with_rate") or n("n_bot_flat_targets")):
        colour = UI.COLORS["amber"]
    else:
        colour = UI.COLORS["green"]

    details: list = []
    if n("total_attempts_7d"):
        details.append(
            f"📊 7d: {n('total_successes_7d')}/{n('total_attempts_7d')} thành công "
            f"({n('success_rate_7d', 0.0) * 100:.0f}%)")
    breakers = n("open_breakers") or []
    if breakers:
        joined = ", ".join(f"{k} ({s / 60:.0f}p)" for k, s in breakers[:3])
        details.append(f"⏸ Breaker OPEN: {joined}")
    if n("targets_with_abuse"):
        details.append("🚨 Abuse signal: " + ", ".join(n("targets_with_abuse")[:3]))
    if n("targets_with_rate"):
        details.append("🟠 Rate-limited: " + ", ".join(n("targets_with_rate")[:3]))
    details.extend(list(n("token_messages") or [])[:2])
    details.extend(list(n("page_health_warnings") or [])[:3])
    details.extend(list(n("time_intel_warnings") or [])[:2])
    recs = n("recommendations") or []
    if recs:
        details.append(f"💡 {len(recs)} đề xuất tinh chỉnh — xem log")
        for r in recs[:2]:
            details.append(
                f"   • {getattr(r, 'metric', '?')}: {getattr(r, 'current_value', 0):g}"
                f"→{getattr(r, 'suggested', 0):g} "
                f"({getattr(r, 'direction', '')}, {getattr(r, 'confidence', '')})")
    if n("total_content_records"):
        details.append(f"📚 Content history: {n('total_content_records')} bản ghi")

    return summary, colour, details


def collect_logs(limit: int = 80) -> list:
    """Newest-first, same as the desktop panel. Secrets are already redacted
    by utils.logger before they reach the buffer."""
    try:
        from utils.logger import get_recent_logs
        entries = get_recent_logs(limit) or []
    except Exception:
        return []
    out = []
    for e in reversed(entries):
        level = str(e.get("level", "info"))
        message = str(e.get("formatted") or e.get("msg") or "")
        # Colour first: the prefix would push "[W3]" off the start of the
        # string and the per-worker colour would silently fall back to the
        # level colour.
        colour = UI.log_colour(level, message)
        # Worker lines are coloured per worker, so severity has to be spelled
        # out or an error hides among routine lines.
        if UI.is_worker_line(message):
            message = UI.severity_prefix(level) + message
        out.append({"level": level, "message": message, "colour": colour})
    return out


def collect(config: dict) -> MonitorData:
    tokens, token_error = collect_token_health(config)
    summary, colour, details = collect_antispam(config)
    return MonitorData(
        tokens=tokens, token_error=token_error,
        metrics=collect_metrics(),
        antispam_summary=summary, antispam_colour=colour,
        antispam_details=details,
        logs=collect_logs(),
    )
