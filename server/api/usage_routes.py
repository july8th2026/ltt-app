"""``/api/v1/credits/balance`` and ``/api/v1/usage``.

Both read the credit ledger directly (see ``platform_core.public_api.usage``),
so what a customer sees here and what the platform charges cannot drift apart.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from platform_core.public_api import usage
from platform_core.public_api.pagination import Page, PageRequest
from platform_core.public_api.principal import Principal
from platform_core.public_api.scopes import SCOPE_CREDITS_READ, SCOPE_USAGE_READ
from server.api.auth import require_scope
from server.deps import get_db

_NO_STORE = {"Cache-Control": "no-store"}


def register_usage_routes(api, config, tag: str) -> None:

    @api.get("/credits/balance", tags=[tag], summary="Current credit balance",
             description="The account's credit balance, from the credit ledger.")
    def credit_balance(
        principal: Principal = Depends(require_scope(SCOPE_CREDITS_READ)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        return JSONResponse(
            {"balance": usage.balance(db, principal.user_id), "unit": "credit",
             "as_of": datetime.now(timezone.utc).isoformat()},
            headers=_NO_STORE)

    @api.get("/usage", tags=[tag], summary="Credit usage for this account",
             description=("Per-job credit usage in a time window, plus window "
                          "totals. Defaults to the last 30 days."))
    def usage_report(
        since: str = Query(default=""),
        until: str = Query(default=""),
        tool: str = Query(default=""),
        key_id: str = Query(default=""),
        limit: int = Query(default=None),
        offset: int = Query(default=None),
        principal: Principal = Depends(require_scope(SCOPE_USAGE_READ)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        window_start, window_end = usage.parse_window(since, until)
        page_request = PageRequest.parse(limit, offset)
        lines = usage.usage_lines(
            db, user_id=principal.user_id, since=window_start, until=window_end,
            tool=tool, key_id=key_id, limit=page_request.fetch_limit,
            offset=page_request.offset)
        page = Page.of(lines, page_request).to_dict()
        # Totals come from the ledger for the whole window, not from the page:
        # a total that only counts one page is a bug that looks like an answer.
        page["totals"] = usage.usage_totals(
            db, user_id=principal.user_id, since=window_start, until=window_end)
        page["window"] = {"since": window_start.isoformat(),
                          "until": window_end.isoformat()}
        return JSONResponse(page, headers=_NO_STORE)
