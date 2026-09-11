"""Attach trusted scheduler origin/priority to each HTTP request."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware

from platform_core.job_ingress import trusted_scope


class JobIngressMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):  # noqa: ANN001
        path = request.url.path
        public_api = path == "/api/v1" or path.startswith("/api/v1/")
        origin = "public_api" if public_api else "web"
        priority = "external" if public_api else "internal"
        with trusted_scope(origin, priority):
            return await call_next(request)
