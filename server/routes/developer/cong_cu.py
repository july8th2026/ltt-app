"""Danh muc cong cu cong khai cua /api/v1."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_core import credit
from platform_core.i18n import N_, _ as _t
from platform_core.models import Job
from platform_core.public_api import keys as devkeys, projects, sandbox, usage
from platform_core.public_api.catalog import build_catalog
from platform_core.public_api.config import load_public_api_config
from platform_core.public_api.invocation import api_meta
from platform_core.public_api.scopes import DEFAULT_SCOPES, KNOWN_SCOPES
from platform_core.public_api.tables import WebhookSubscription
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import get_db, user_hien_tai
from server.templating import templates

from server.routes.developer._chung import (  # noqa: F401
    _example_request, _public_api_config, _redirect, _render, _tham_so, _the_cong_cu, _vi_du_outputs, require_account, router)

@router.get("/tools", response_class=HTMLResponse)
def developer_tools(request: Request, q: str = "", capability: str = "",
                    user=Depends(require_account),
                    db: Session = Depends(get_db)):
    from platform_core.public_api.catalog import build_models, capabilities_of

    config = _public_api_config(request)
    catalog = build_catalog(config)
    needle = str(q or "").strip().lower()
    wanted = str(capability or "").strip()

    def _matches(tool) -> bool:
        if wanted and tool.capability != wanted:
            return False
        if not needle:
            return True
        # Search the parameter names too: "aspect_ratio" is how somebody looks
        # for the tool that takes it.
        haystack = " ".join([tool.name, tool.description,
                             " ".join(tool.input_schema.get("properties", {}))])
        return needle in haystack.lower()

    shown = [tool for tool in catalog if _matches(tool)]
    return _render(request, db, user, "tools", "dev_tools.html",
                   query=needle, capability=wanted,
                   capabilities=capabilities_of(catalog),
                   catalog=[_the_cong_cu(tool) for tool in shown],
                   models=[model.to_public_dict()
                           for model in build_models(shown)])


@router.get("/tools/{tool_name}", response_class=HTMLResponse)
def developer_tool_detail(request: Request, tool_name: str,
                          user=Depends(require_account),
                          db: Session = Depends(get_db)):
    """The reference page for one tool, rendered from its contract.

    Nothing here is written twice: every field comes from the same catalog the
    API serves, so a page cannot describe a parameter the server does not
    accept. That is the whole point of generating it (EXT-06).
    """
    from platform_core.public_api.catalog import build_models, require_tool
    from platform_core.public_api.error_registry import as_rows
    from platform_core.public_api.protocol import MODE_RULES
    from platform_core.public_api.webhooks import TERMINAL_EVENTS

    config = _public_api_config(request)
    catalog = build_catalog(config)
    try:
        tool = require_tool(catalog, tool_name)
    except Exception as exc:  # noqa: BLE001 - a missing tool is a 404 page
        from platform_core.public_api.errors import ApiError

        if not isinstance(exc, ApiError):
            raise
        raise _redirect("/developers/tools", status_code=404) from exc

    body = tool.to_public_dict()
    params = _tham_so(body["input_schema"])
    example = _example_request(tool, params)
    outputs = body["output_schema"].get("properties", {})
    return _render(
        request, db, user, "tools", "dev_tool_detail.html",
        section_title=tool.name, tool=body, params=params,
        mode_rule=MODE_RULES.get(tool.execution_mode, ""),
        example_request=example,
        has_artifacts=any(str(spec.get("type", "")).startswith("artifact")
                          for spec in outputs.values()),
        # Hình dạng THẬT của `outputs[]`, dựng từ chính `output_schema` — không
        # gõ tay, nên nó không thể lệch khỏi thứ job trả về. Xem chú thích trong
        # template: khách trước nay đi tìm `result.<tên trường>` và không thấy.
        vi_du_outputs=_vi_du_outputs(outputs),
        models=[model.to_public_dict() for model in build_models([tool])],
        events=sorted(TERMINAL_EVENTS),
        errors=as_rows(),
        limits={"request_rpm": config.request_rpm,
                "create_rpm": config.create_rpm,
                "max_active_jobs": config.max_active_jobs,
                "daily_credit_limit": config.daily_credit_limit,
                "max_body_kib": config.max_body_bytes // 1024})
