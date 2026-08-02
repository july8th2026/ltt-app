"""Early request-body cap for Agent JSON endpoints."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

AGENT_BODY_LIMIT = 128 * 1024


class AgentBodyLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, limit: int = AGENT_BODY_LIMIT):
        super().__init__(app)
        self._limit = int(limit)

    async def dispatch(self, request, call_next):
        if (request.method not in {"POST", "PUT", "PATCH"}
                or not request.url.path.startswith("/agent/")):
            return await call_next(request)
        try:
            declared = int(request.headers.get("content-length", "0") or 0)
        except ValueError:
            declared = self._limit + 1
        if declared > self._limit:
            return JSONResponse({"detail": "Dữ liệu Agent vượt giới hạn 128 KiB."},
                                status_code=413)
        body = await request.body()
        if len(body) > self._limit:
            return JSONResponse({"detail": "Dữ liệu Agent vượt giới hạn 128 KiB."},
                                status_code=413)
        # BaseHTTPMiddleware keeps the consumed body cached for downstream Request.
        return await call_next(request)
