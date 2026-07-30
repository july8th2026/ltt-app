"""
sheet_service.py — Sheet Runner data access for the web UI.

Reproduces the behaviour of `gui/sheet_runner_tab.py`'s selectors, worker
CRUD and queue preview, but as plain functions with no widget dependency.
Everything goes through the shared `core/` code and the shared
`data/workers.json`, so the web and any other client see one list
(ADR-003).
"""
from __future__ import annotations

from core.worker_store import load_workers, save_workers
from server.services import ui_constants as UI


class SheetServiceError(RuntimeError):
    """Something the operator needs to read and act on."""


# ── Selectors ─────────────────────────────────────────────────────────────────

def list_sheet_options(config: dict) -> list:
    """Sheet dropdown, mirroring _reload_sheets().

    Falls back to a synthetic "Default" entry built from the legacy
    top-level `sheet_id` when `sheets` is empty, exactly as the desktop did.
    """
    sheets = config.get("sheets") or []
    options = [
        {"id": str(s.get("id", "")).strip(),
         "alias": str(s.get("alias", "") or "Sheet").strip(),
         "label": f"{s.get('alias') or 'Sheet'}  ({str(s.get('id',''))[:10]}…)"}
        for s in sheets if str(s.get("id", "")).strip()
    ]
    if not options:
        legacy = str(config.get("sheet_id", "") or "").strip()
        if legacy:
            options = [{"id": legacy, "alias": "Default",
                        "label": f"Default  ({legacy[:10]}…)"}]
    return options


def list_tabs(config: dict, sheet_id: str) -> list:
    """Tab dropdown — hits the Google Sheets API."""
    from utils.sheet_client import SheetClient
    try:
        client = SheetClient(config, sheet_id_override=sheet_id)
        client.connect()
        return client.get_all_tabs()
    except Exception as exc:
        raise SheetServiceError(f"Lỗi kết nối: {exc}") from exc


def list_page_options(platform: str) -> list:
    """Page / TikTok-account dropdown.

    facebook -> TokenStore.all_page_options(), label "Page  ← Account"
    tiktok   -> TikTokTokenStore accounts, label = display_name or open_id

    An unreadable token store yields [] plus a readable reason, so the page
    can say "kho token không đọc được" instead of silently showing nothing.
    """
    if platform == "tiktok":
        try:
            from core.tiktok.token_store import get_default_store
            store = get_default_store()
            if getattr(store, "is_unreadable", False):
                return []
            return [{"label": a.display_name or a.open_id,
                     "page_id": "", "account_id": a.open_id,
                     "account_name": a.display_name or a.open_id}
                    for a in store.all_accounts()]
        except Exception:
            return []

    try:
        from core.token_store import get_default_store
        store = get_default_store()
        if getattr(store, "is_unreadable", False):
            return []
        store.reload()          # desktop forces a re-read here too
        return [{"label": o["label"], "page_id": o["page_id"],
                 "account_id": o["account_id"], "account_name": o["account_name"],
                 "page_name": o["page_name"]}
                for o in store.all_page_options()]
    except Exception:
        return []


def _resolve_page(platform: str, label: str) -> dict:
    """Reverse-map a dropdown label to ids, mirroring _resolve_page_label()."""
    label = (label or "").strip()
    for opt in list_page_options(platform):
        if opt["label"] == label:
            if platform == "tiktok":
                return {"page": label, "page_id": "",
                        "account_id": opt.get("account_id", ""),
                        "account_name": opt.get("account_name", label)}
            return {"page": opt.get("page_name", label),
                    "page_id": opt.get("page_id", ""),
                    "account_id": opt.get("account_id", ""),
                    "account_name": opt.get("account_name", "")}
    # Free-typed / stale label: keep it, with no ids. The desktop did the same.
    if platform == "tiktok":
        return {"page": label, "page_id": "", "account_id": "",
                "account_name": label}
    return {"page": label, "page_id": "", "account_id": "", "account_name": ""}


# ── Worker CRUD (shared data/workers.json) ────────────────────────────────────

def stored_workers(platform: str) -> list:
    try:
        return load_workers(platform=platform)
    except Exception:
        return []


def add_worker(platform: str, *, sheet_id: str, tab: str, page_label: str) -> None:
    """Same validation order and messages as _add_worker()."""
    sheet_id = (sheet_id or "").strip()
    tab = (tab or "").strip()

    if not sheet_id:
        raise SheetServiceError("Chưa chọn Sheet (dropdown đầu).")
    if not tab or tab.startswith("⏳"):
        raise SheetServiceError("Chọn Tab Sheet trước (nhấn 🔄 để tải)")

    workers = stored_workers(platform)
    if len(workers) >= UI.MAX_WORKERS:
        raise SheetServiceError(f"Tối đa {UI.MAX_WORKERS} workers")

    resolved = _resolve_page(platform, page_label)
    new_id = resolved["page_id"] or resolved["page"]
    for w in workers:
        existing_id = w.get("page_id") or w.get("page", "")
        if w.get("sheet_id", "") == sheet_id and w.get("tab") == tab \
                and existing_id == new_id:
            raise SheetServiceError(
                f"({sheet_id[:10]}…, '{tab}', '{resolved['page']}') đã được thêm")

    workers.append({
        "sheet_id": sheet_id,
        "tab": tab,
        "page": resolved["page"],
        "page_id": resolved["page_id"],
        "account_id": resolved["account_id"],
    })
    save_workers(workers, platform=platform)


def remove_worker(platform: str, index: int) -> None:
    workers = stored_workers(platform)
    if 0 <= index < len(workers):
        workers.pop(index)
        save_workers(workers, platform=platform)


# ── Queue preview ─────────────────────────────────────────────────────────────

def queue_preview(config: dict, platform: str, limit: int = 20) -> dict:
    """Mirrors _refresh_queue_preview(): first worker's sheet+tab, skip DONE /
    SKIPPED, cap at 20 rows, report the real spreadsheet row number."""
    workers = stored_workers(platform)
    if not workers:
        raise SheetServiceError(
            "Chưa có worker — thêm ít nhất 1 Tab Sheet + Page")

    w0 = workers[0]
    tab = w0.get("tab", "")
    sheet_id = w0.get("sheet_id", "") or str(config.get("sheet_id", ""))
    if not tab or not sheet_id:
        raise SheetServiceError("Worker đầu tiên thiếu sheet_id hoặc tab")

    from utils.sheet_client import SheetClient
    try:
        client = SheetClient(config, sheet_id_override=sheet_id)
        client.connect()
        client.switch_tab(tab)
        data_rows = client.get_all_rows()          # header already excluded
        status_idx = client.get_column_index("col_status")
        title_idx = client.get_column_index("col_title")
        sched_idx = client.get_column_index("col_schedule_time")
    except Exception as exc:
        raise SheetServiceError(str(exc)[:200]) from exc

    def cell(row, idx, limit_chars):
        # `idx is not None` — column A is index 0 and must not read as missing.
        if idx is None or idx >= len(row):
            return "—"
        return str(row[idx])[:limit_chars]

    rows = []
    for i, row in enumerate(data_rows, start=2):
        if not any(row):
            continue
        status = (str(row[status_idx]).strip().upper()
                  if status_idx is not None and status_idx < len(row) else "")
        if status in ("DONE", "SKIPPED"):
            continue
        rows.append({
            "seq": len(rows) + 1,
            "row_idx": i,
            "title": cell(row, title_idx, 35),
            "schedule": cell(row, sched_idx, 16),
            "status": status or "PENDING",
            "colour": {"RUNNING": UI.COLORS["blue"],
                       "ERROR": UI.COLORS["red"]}.get(status, UI.COLORS["muted"]),
        })
        if len(rows) >= limit:
            break

    return {"tab": tab, "rows": rows, "count": len(rows)}
