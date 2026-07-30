"""Settings page — full config editing on the web (GUI parity phase 1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse

from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.services.credentials_service import (
    describe_stored,
    store_credentials,
    test_sheet_connection,
)
from server.services import content_tools
from server.services.settings_schema import GROUPS, all_field_keys
from server.services.settings_service import (
    apply_form,
    config_path,
    list_backups,
    load_config,
    save_config,
    view_model,
)
from server.templating import templates

router = APIRouter(tags=["settings"])


def _context(request: Request, user: str, config: dict, **extra) -> dict:
    ctx = {
        "user": user,
        "nav": "settings",
        "groups": GROUPS,
        "values": view_model(config),
        "csrf_token": issue_csrf_token(request),
        "config_path": config_path(),
        "total_fields": len(all_field_keys()),
        "backup_count": len(list_backups()),
        "creds": describe_stored(),
        "field_errors": {},
        "dup": None,
        "imported": None,
        "errors": [],
        "warnings": [],
        "saved": False,
        "restart_needed": False,
    }
    ctx.update(extra)
    return ctx


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, user: str = Depends(require_login)):
    return templates.TemplateResponse(
        request, "settings.html", _context(request, user, load_config()),
    )


@router.post("/settings", response_class=HTMLResponse)
async def settings_save(request: Request, user: str = Depends(require_login)):
    form = await request.form()

    if not verify_csrf_token(request, str(form.get("csrf_token", ""))):
        return templates.TemplateResponse(
            request, "settings.html",
            _context(request, user, load_config(),
                     errors=["Phiên đã hết hạn, tải lại trang rồi thử lại."]),
            status_code=400,
        )

    current = load_config()
    candidate, field_errors = apply_form(current, form)

    # Per-field parse errors (bad number, bad JSON) stop the save before it
    # can reach validation, and the form is re-rendered with what the user
    # typed so nothing they entered is lost.
    if field_errors:
        return templates.TemplateResponse(
            request, "settings.html",
            _context(request, user, candidate,
                     field_errors=field_errors,
                     errors=["Có trường nhập sai — chưa lưu gì cả."]),
            status_code=400,
        )

    saved, errors, warnings = save_config(candidate)
    if not saved:
        return templates.TemplateResponse(
            request, "settings.html",
            _context(request, user, candidate, errors=errors, warnings=warnings),
            status_code=400,
        )

    # Reload from disk so the page shows exactly what was persisted.
    from server.services.worker_control import get_controller
    return templates.TemplateResponse(
        request, "settings.html",
        _context(request, user, load_config(),
                 saved=True, warnings=warnings,
                 restart_needed=get_controller().snapshot().running),
    )


@router.post("/settings/credentials", response_class=HTMLResponse)
async def upload_credentials(
    request: Request,
    csrf_token: str = Form(...),
    file: UploadFile = File(...),
    user: str = Depends(require_login),
):
    """Upload the Google service-account JSON.

    Replaces the desktop's native file picker. Rejects OAuth-client files,
    which would otherwise produce a config that looks fine and then blocks
    forever waiting for a browser (docs/_luutru/WEB_PARITY_PLAN.md B-1).
    """
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "settings.html",
            _context(request, user, load_config(),
                     errors=["Phiên đã hết hạn, tải lại trang rồi thử lại."]),
            status_code=400)

    raw = await file.read()
    ok, message, info = store_credentials(raw)
    if not ok:
        return templates.TemplateResponse(
            request, "settings.html",
            _context(request, user, load_config(), errors=[message]),
            status_code=400)

    # Point the config at the stored file so SheetClient finds it without
    # the operator having to type a server-side path by hand.
    from server.services.credentials_service import credentials_path
    config = load_config()
    config["google_credentials_path"] = credentials_path()
    saved, errors, warnings = save_config(config)

    return templates.TemplateResponse(
        request, "settings.html",
        _context(request, user, load_config(),
                 saved=saved, errors=errors,
                 warnings=[message] + list(warnings)))


@router.post("/settings/test-sheet", response_class=HTMLResponse)
def test_sheet(
    request: Request,
    csrf_token: str = Form(...),
    user: str = Depends(require_login),
):
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "settings.html",
            _context(request, user, load_config(),
                     errors=["Phiên đã hết hạn, tải lại trang."]),
            status_code=400)

    config = load_config()
    ok, message = test_sheet_connection(config)
    key = "warnings" if ok else "errors"
    return templates.TemplateResponse(
        request, "settings.html",
        _context(request, user, config, **{key: [message]}),
        status_code=200 if ok else 400)


# ── Content Vault actions (gui/settings_tab.py:815-940) ────────────────────────

@router.post("/settings/export-history")
def export_history(
    request: Request,
    csrf_token: str = Form(...),
    user: str = Depends(require_login),
):
    """Stream content_history as a CSV download.

    The desktop wrote to a path chosen with a file dialog. On a server that
    path is on the VPS, where the operator cannot reach it — so the file comes
    down through the browser instead.
    """
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "settings.html",
            _context(request, user, load_config(),
                     errors=["Phiên đã hết hạn — tải lại trang rồi thử lại."]),
            status_code=400)
    try:
        text, _count = content_tools.export_history_csv()
    except Exception as exc:
        return templates.TemplateResponse(
            request, "settings.html",
            _context(request, user, load_config(),
                     errors=[f"Export lỗi: {type(exc).__name__}: {exc}"]),
            status_code=500)

    name = content_tools.export_filename()
    return StreamingResponse(
        iter([text.encode("utf-8-sig")]),   # BOM so Excel reads UTF-8 correctly
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.post("/settings/duplicates", response_class=HTMLResponse)
def show_duplicates(
    request: Request,
    csrf_token: str = Form(...),
    user: str = Depends(require_login),
):
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "settings.html", _context(request, user, load_config()),
            status_code=400)
    return templates.TemplateResponse(
        request, "settings.html",
        _context(request, user, load_config(), dup=content_tools.find_duplicates()),
    )


@router.post("/settings/import-calendar", response_class=HTMLResponse)
async def import_calendar(
    request: Request,
    csrf_token: str = Form(...),
    csv_file: UploadFile = File(None),
    user: str = Depends(require_login),
):
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "settings.html", _context(request, user, load_config()),
            status_code=400)

    filename = getattr(csv_file, "filename", "") or ""
    data = await csv_file.read() if csv_file is not None else b""
    report = content_tools.import_calendar_csv(filename, data)
    return templates.TemplateResponse(
        request, "settings.html",
        _context(request, user, load_config(), imported=report),
    )
