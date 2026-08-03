"""
/status — the doctor health report, in the browser (PB-2).

Reuses tools/doctor.py rather than reimplementing the checks, so the CLI
and the dashboard can never disagree about whether the bot can publish.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from server.deps import require_operator
from server.templating import templates

router = APIRouter(tags=["status"])


@router.get("/status", response_class=HTMLResponse)
def status_page(
    request: Request,
    check_sheet: str = "",
    user: str = Depends(require_operator),
):
    from tools import doctor

    # Sheet checks hit the Google API, so they are opt-in per request
    # rather than running on every page view.
    want_sheet = check_sheet == "1"
    report = doctor.run(check_sheet_flag=want_sheet)

    return templates.TemplateResponse(request, "status.html", {
        "user": user,
        "nav": "status",
        "sections": report.sections,
        "blockers": [s for s in report.sections if s["status"] == doctor.BLOCK],
        "checked_sheet": want_sheet,
    })
