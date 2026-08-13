"""Surface-wide guards for ``/api/v1``: the read-only switch and the size cap.

These run as middleware on the public sub-application rather than as route
dependencies, and that is the whole point: an emergency switch has to hold for
every route the surface serves — including the ones added by later prompts, and
including a route whose author forgot the dependency. A kill switch you can
forget to attach is not a kill switch.

Because a middleware short-circuits above the exception handlers, it renders the
problem document itself instead of raising :class:`ApiError`, and stamps the
correlation id on the response so a refused request is still traceable.
"""
from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware

from platform_core.public_api import metrics, protocol
from platform_core.public_api.config import PublicApiConfig
from platform_core.public_api.errors import ApiError
from server.api.context import client_ip, request_id
from server.api.deps import enforce_body_limit, enforce_read_only
from server.api.errors import problem_response

log = logging.getLogger("ltt.public_api.access")


class PublicApiGuardMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, config: PublicApiConfig):
        super().__init__(app)
        self._config = config

    async def dispatch(self, request, call_next):
        correlation_id = request_id(request)
        started = time.perf_counter()
        try:
            enforce_read_only(request, self._config)
            enforce_body_limit(request, self._config)
        except ApiError as exc:
            response = problem_response(exc.problem(
                instance=request.url.path, request_id=correlation_id))
            self._stamp(response, request, correlation_id)
            self._record(request, response.status_code, started, correlation_id)
            return response
        response = await call_next(request)
        self._stamp(response, request, correlation_id)
        self._record(request, response.status_code, started, correlation_id)
        return response

    def _stamp(self, response, request, correlation_id: str) -> None:
        """Correlation id and API version on **every** response.

        Until EXT-02 the correlation id was only stamped on responses this
        middleware refused itself. A caller whose successful-then-mysterious
        request needed support had nothing to quote, and the audit found it: the
        id existed in the server's log and nowhere the customer could see.
        """
        response.headers[protocol.HEADER_CORRELATION_ID] = correlation_id
        response.headers[protocol.HEADER_API_VERSION] = protocol.API_VERSION
        route = _declared_route(request)
        # RFC 8594. Nothing is deprecated today; the hook exists so that
        # retiring an endpoint is a data change in the inventory rather than a
        # code change here, at the moment when getting it right matters.
        if route is not None and route.deprecated_on:
            response.headers[protocol.HEADER_DEPRECATION] = route.deprecated_on
            if route.sunset_on:
                response.headers[protocol.HEADER_SUNSET] = route.sunset_on

    def _record(self, request, status: int, started: float,
                correlation_id: str) -> None:
        """One structured line per request, and the counters behind it.

        Every field here is either public (a route, a status, a duration) or a
        public identifier (`key_id`, the owner's account id). The bearer token,
        the request body and any provider text are not logged — and cannot be,
        because they are never passed in.
        """
        latency_ms = (time.perf_counter() - started) * 1000.0
        principal = getattr(request.state, "api_principal", None)
        metrics.increment(metrics.REQUESTS)
        metrics.observe(metrics.LATENCY_REQUEST, latency_ms)
        if 400 <= status < 500:
            metrics.increment(metrics.RESPONSES_4XX)
        elif status >= 500:
            metrics.increment(metrics.RESPONSES_5XX)
        if status == 429:
            metrics.increment(metrics.RATE_LIMITED)

        log.info(
            "api request_id=%s method=%s route=%s status=%s latency_ms=%.1f "
            "key_id=%s owner=%s tool=%s job_id=%s credit_delta=%s ip=%s",
            correlation_id, request.method,
            # The templated path, not the filled-in one: a job id in a log line
            # is fine, but grouping by route is what makes the log usable.
            _route_of(request), status, latency_ms,
            getattr(principal, "key_id", "-") or "-",
            getattr(principal, "user_id", "-") or "-",
            getattr(request.state, "api_tool", "-") or "-",
            getattr(request.state, "api_job_id", "-") or "-",
            getattr(request.state, "api_credit_delta", 0) or 0,
            client_ip(request, getattr(self._config, "trusted_proxies", ())),
        )


def _route_of(request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", "") if route is not None else ""
    return path or request.url.path


def _declared_route(request):
    """The inventory entry for this request, or None for an unmatched path."""
    from server.api.inventory import API_V1_ROUTES, API_V1_PREFIX

    path = _route_of(request)
    if not path.startswith(API_V1_PREFIX):
        path = API_V1_PREFIX + path
    for route in API_V1_ROUTES:
        if route.path == path and route.method == request.method:
            return route
    return None
