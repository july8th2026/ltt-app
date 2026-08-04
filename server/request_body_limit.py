"""Early request-body cap for Agent JSON endpoints."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

AGENT_BODY_LIMIT = 128 * 1024
AGENT_ASSET_BODY_LIMIT = 91 * 1024 * 1024


class AgentBodyLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, limit: int = AGENT_BODY_LIMIT,
                 asset_limit: int = AGENT_ASSET_BODY_LIMIT):
        super().__init__(app)
        self._limit = int(limit)
        self._asset_limit = int(asset_limit)

    async def dispatch(self, request, call_next):
        if (request.method not in {"POST", "PUT", "PATCH"}
                or not request.url.path.startswith("/agent/")):
            return await call_next(request)
        is_asset_upload = (
            request.method == "POST"
            and request.url.path == "/agent/api/assets"
            and request.headers.get("content-type", "").lower().startswith(
                "multipart/form-data"
            )
        )
        try:
            declared = int(request.headers.get("content-length", "0") or 0)
        except ValueError:
            declared = (self._asset_limit if is_asset_upload else self._limit) + 1
        active_limit = self._asset_limit if is_asset_upload else self._limit
        if declared > active_limit:
            if is_asset_upload:
                return JSONResponse(
                    {"detail": "Asset vượt giới hạn request 91 MiB."},
                    status_code=413,
                )
            return JSONResponse({"detail": "Dữ liệu Agent vượt giới hạn 128 KiB."},
                                status_code=413)
        if is_asset_upload:
            # Không đọc/copy multipart lớn tại middleware. Endpoint asset tiếp tục
            # xác minh MIME, bytes thật, ownership và giới hạn file 90 MiB.
            return await call_next(request)
        body = await request.body()
        if len(body) > self._limit:
            return JSONResponse({"detail": "Dữ liệu Agent vượt giới hạn 128 KiB."},
                                status_code=413)
        # BaseHTTPMiddleware keeps the consumed body cached for downstream Request.
        return await call_next(request)
