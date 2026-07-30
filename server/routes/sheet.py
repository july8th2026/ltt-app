"""
Sheet Runner page — the web equivalent of the desktop "Sheet FB" /
"Sheet TikTok" tabs (gui/sheet_runner_tab.py).

Layout, card titles, column headers, worker limits and state colours are
taken from `server/services/ui_constants.py`, which ports them verbatim
from the desktop source. Worker CRUD writes the same `data/workers.json`
the desktop wrote, so both see one list.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.services import ui_constants as UI
from server.services.sheet_service import (
    SheetServiceError,
    add_worker,
    list_page_options,
    list_sheet_options,
    list_tabs,
    queue_preview,
    remove_worker,
    stored_workers,
)
from server.services.worker_control import (
    NoWorkersConfiguredError,
    WorkerBusyError,
    get_controller,
)
from server.templating import templates

router = APIRouter(tags=["sheet"])

VALID_PLATFORMS = ("facebook", "tiktok")


def _platform(value: str) -> str:
    v = (value or "facebook").strip().lower()
    return v if v in VALID_PLATFORMS else "facebook"


def _config(request: Request) -> dict:
    cs = getattr(request.app.state, "core_settings", None)
    return dict(cs.config) if cs else {}


def _context(request: Request, user: str, platform: str, **extra) -> dict:
    cfg = _context_config = _config(request)
    snapshot = get_controller().snapshot()
    ctx = {
        "user": user,
        "nav": "sheet_fb" if platform == "facebook" else "sheet_tiktok",
        "platform": platform,
        "platform_label": "Sheet FB" if platform == "facebook" else "Sheet TikTok",
        "cards": UI.SHEET_CARDS,
        "colors": UI.COLORS,
        "account_col": UI.ACCOUNT_COL_HEADER[platform],
        "account_label": UI.ACCOUNT_SELECTOR_LABEL[platform],
        "queue_columns": UI.QUEUE_COLUMNS,
        "max_workers": UI.MAX_WORKERS,
        "workers": stored_workers(platform),
        "sheet_options": list_sheet_options(cfg),
        "page_options": list_page_options(platform),
        "csrf_token": issue_csrf_token(request),
        "snapshot": snapshot,
        # A run started for the *other* platform still occupies the single
        # orchestrator (ADR-005), so this page must say so rather than
        # offering a Start button that will 409.
        "running_here": snapshot.running and snapshot.platform == platform,
        "running_elsewhere": snapshot.running and snapshot.platform != platform,
        "tabs": [],
        "queue": None,
        "error": "",
        "notice": "",
    }
    ctx.update(extra)
    return ctx


@router.get("/sheet/{platform}", response_class=HTMLResponse)
def sheet_page(platform: str, request: Request, user: str = Depends(require_login)):
    p = _platform(platform)
    return templates.TemplateResponse(request, "sheet.html", _context(request, user, p))


@router.post("/sheet/{platform}/tabs", response_class=HTMLResponse)
def load_tabs(
    platform: str,
    request: Request,
    csrf_token: str = Form(...),
    sheet_id: str = Form(""),
    user: str = Depends(require_login),
):
    """Desktop equivalent: the 🔄 button next to the Tab dropdown."""
    p = _platform(platform)
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "sheet.html",
            _context(request, user, p, error="Phiên đã hết hạn, tải lại trang."),
            status_code=400)

    if not sheet_id:
        return templates.TemplateResponse(
            request, "sheet.html",
            _context(request, user, p,
                     error="Chưa chọn Sheet (dropdown trên). "
                           "Vào Cài đặt → Google Sheets để thêm sheet."),
            status_code=400)

    try:
        tabs = list_tabs(_config(request), sheet_id)
    except SheetServiceError as exc:
        return templates.TemplateResponse(
            request, "sheet.html",
            _context(request, user, p, error=str(exc)), status_code=502)

    return templates.TemplateResponse(
        request, "sheet.html",
        _context(request, user, p, tabs=tabs, selected_sheet=sheet_id,
                 notice=f"Đã tải {len(tabs)} tab." if tabs
                        else "(Không tìm thấy tab)"))


@router.post("/sheet/{platform}/workers/add")
def worker_add(
    platform: str,
    request: Request,
    csrf_token: str = Form(...),
    sheet_id: str = Form(""),
    tab: str = Form(""),
    page: str = Form(""),
    user: str = Depends(require_login),
):
    p = _platform(platform)
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "sheet.html",
            _context(request, user, p, error="Phiên đã hết hạn, tải lại trang."),
            status_code=400)
    try:
        add_worker(p, sheet_id=sheet_id, tab=tab, page_label=page)
    except SheetServiceError as exc:
        return templates.TemplateResponse(
            request, "sheet.html",
            _context(request, user, p, error=str(exc)), status_code=400)
    return RedirectResponse(f"/sheet/{p}", status_code=303)


@router.post("/sheet/{platform}/workers/remove")
def worker_remove(
    platform: str,
    request: Request,
    csrf_token: str = Form(...),
    index: int = Form(...),
    user: str = Depends(require_login),
):
    p = _platform(platform)
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "sheet.html",
            _context(request, user, p, error="Phiên đã hết hạn, tải lại trang."),
            status_code=400)
    remove_worker(p, index)
    return RedirectResponse(f"/sheet/{p}", status_code=303)


@router.post("/sheet/{platform}/queue", response_class=HTMLResponse)
def refresh_queue(
    platform: str,
    request: Request,
    csrf_token: str = Form(...),
    user: str = Depends(require_login),
):
    """Desktop equivalent: the "🔄  Làm mới" button in the action bar."""
    p = _platform(platform)
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "sheet.html",
            _context(request, user, p, error="Phiên đã hết hạn, tải lại trang."),
            status_code=400)
    try:
        queue = queue_preview(_config(request), p)
    except SheetServiceError as exc:
        return templates.TemplateResponse(
            request, "sheet.html",
            _context(request, user, p, error=str(exc)), status_code=502)
    return templates.TemplateResponse(
        request, "sheet.html", _context(request, user, p, queue=queue))


@router.post("/sheet/{platform}/start")
def sheet_start(
    platform: str,
    request: Request,
    csrf_token: str = Form(...),
    user: str = Depends(require_login),
):
    p = _platform(platform)
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "sheet.html",
            _context(request, user, p, error="Phiên đã hết hạn, tải lại trang."),
            status_code=400)
    try:
        get_controller().start(
            workers=stored_workers(p), config=_config(request), platform=p)
    except (WorkerBusyError, NoWorkersConfiguredError) as exc:
        return templates.TemplateResponse(
            request, "sheet.html",
            _context(request, user, p, error=str(exc)), status_code=409)
    except Exception as exc:
        # Ownership conflict with another runner lands here; the message
        # names the host/pid holding the lock.
        return templates.TemplateResponse(
            request, "sheet.html",
            _context(request, user, p, error=str(exc)), status_code=409)
    return RedirectResponse(f"/sheet/{p}", status_code=303)


@router.post("/sheet/{platform}/stop")
def sheet_stop(
    platform: str,
    request: Request,
    csrf_token: str = Form(...),
    user: str = Depends(require_login),
):
    p = _platform(platform)
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "sheet.html",
            _context(request, user, p, error="Phiên đã hết hạn, tải lại trang."),
            status_code=400)
    get_controller().stop()
    return RedirectResponse(f"/sheet/{p}", status_code=303)
