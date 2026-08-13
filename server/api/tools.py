"""``/api/v1/tools`` — the public catalog endpoints.

The routes are thin on purpose: gating and projection live in
``platform_core.public_api.catalog`` so they can be tested without HTTP, and so
a second caller (the portal, an SDK generator) sees exactly the same answer.
"""
from __future__ import annotations

from fastapi import Depends, Query
from fastapi.responses import JSONResponse

from platform_core.public_api.catalog import build_catalog, require_tool, visible_to
from platform_core.public_api.pagination import Page, PageRequest
from platform_core.public_api.principal import Principal
from platform_core.public_api.scopes import SCOPE_TOOLS_READ
from server.api.auth import require_scope

_NO_STORE = {"Cache-Control": "no-store"}


def register_tool_routes(api, config, tag: str) -> None:
    """Attach the catalog routes straight onto the public sub-application.

    Directly, not through ``include_router``: this FastAPI version keeps an
    included router as an opaque wrapper without ``.path`` (see
    ``server/api/__init__`` and ``tests/test_152``), which would make the route
    inventory — the thing that stops undeclared routes shipping — blind to
    exactly the routes it exists to check.
    """
    router = api

    @router.get("/tools", tags=[tag],
                summary="List the tools this API key may call",
                description=("Returns the public tool catalog, narrowed to what "
                             "the calling key is allowed to use."))
    def list_tools(
        limit: int = Query(default=None, description="Page size (max 100)."),
        offset: int = Query(default=None, description="Rows to skip."),
        principal: Principal = Depends(require_scope(SCOPE_TOOLS_READ)),
    ) -> JSONResponse:
        page_request = PageRequest.parse(limit, offset)
        catalog = visible_to(build_catalog(config), principal)
        window = catalog[page_request.offset:
                         page_request.offset + page_request.fetch_limit]
        page = Page.of([tool.to_public_dict() for tool in window], page_request)
        return JSONResponse(page.to_dict(), headers=_NO_STORE)

    @router.get("/tools/{tool_name}", tags=[tag], summary="Contract for one tool",
                description=("Returns the input/output contract of a single "
                             "tool. Unknown or unavailable tools answer 404."))
    def get_tool(
        tool_name: str,
        principal: Principal = Depends(require_scope(SCOPE_TOOLS_READ)),
    ) -> JSONResponse:
        tool = require_tool(build_catalog(config), tool_name, principal)
        return JSONResponse(tool.to_public_dict(), headers=_NO_STORE)
