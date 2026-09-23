"""Hai trang HTML của app Agent. Tách khỏi `legacy_runs.py` khi luồng plan/run
v1 bị gỡ (spec §17.4) — hai trang này KHÔNG thuộc runtime v1, chúng chỉ ở nhờ.

`/agent/canvas` là nơi bundle `agent-canvas` được phục vụ; mất nó là mất Canvas
cho mọi người, nên nó có phép kiểm riêng (`test_1726`).
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from apps.agent.routes._shared import (_canvas_presentation_mode,
                                       _page_context, router)
from platform_core.frontend_bundle import bundle_assets
from platform_core.i18n import _ as _t
from server.auth.session import require_login
from server.templating import templates


@router.get("", response_class=HTMLResponse)
def page(request: Request, _identity: str = Depends(require_login)):
    return templates.TemplateResponse(request, "agent.html",
                                      _page_context(request))


@router.get("/canvas", response_class=HTMLResponse)
def canvas_page(request: Request, _identity: str = Depends(require_login)):
    canvas_js, canvas_css = bundle_assets("agent-canvas")
    if not canvas_js:
        raise HTTPException(status_code=503,
                            detail=_t('Canvas bundle chưa được build.'))
    context = _page_context(request)
    context.update({"canvas_js": canvas_js, "canvas_css": canvas_css,
                    "canvas_presentation": _canvas_presentation_mode()})
    return templates.TemplateResponse(request, "agent_canvas.html", context)
