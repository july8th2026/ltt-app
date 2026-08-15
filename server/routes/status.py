"""
/status — the doctor health report, in the browser (PB-2).

Two pages live here, and the difference between them is the point:

* ``/status/api`` is **public**. It groups by capability and says nothing about
  how the platform is built;
* ``/status`` is **operator-only**. It is the doctor report, and it names the
  database, the disk, the tunnel and the credential pool.

A page that mixed them would either be useless to a customer or dangerous to
publish (EXT-17).

Reuses tools/doctor.py rather than reimplementing the checks, so the CLI
and the dashboard can never disagree about whether the bot can publish.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from server.deps import get_db, require_operator
from server.templating import templates

router = APIRouter(tags=["status"])


@router.get("/status/api", response_class=HTMLResponse)
def public_api_status(request: Request, db: Session = Depends(get_db)):
    """Is the API working — for anyone, without an account.

    Deliberately **not** behind `require_operator`, unlike `/status` below. A
    status page a customer cannot read during an incident is a status page that
    does not exist; the whole point is that it answers when support does not.

    Equally deliberately, it says nothing about how the platform is built. The
    operator report names the database, the disk, the tunnel and the credential
    pool; publishing that during an outage would tell somebody planning the next
    one which door is currently unlocked.
    """
    from platform_core.public_api.config import load_public_api_config
    from platform_core.public_api.status import public_status

    config = getattr(request.app.state, "public_api", None)
    if config is None:
        config = load_public_api_config()

    report = public_status(db, config)
    response = templates.TemplateResponse(request, "status_api.html", {
        "nav": "status",
        "report": report,
    })
    # An incident page must never be served from a cache that predates the
    # incident.
    response.headers["Cache-Control"] = "no-store"
    return response


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
