"""Error boundary for ``/api/v1``.

Everything leaving this surface is ``application/problem+json`` with a stable
``code`` and the request's correlation id — including the failures nobody wrote
a handler for (routing 404, method 405, request validation, and an unhandled
exception in a route).

Handlers are registered on the **mounted sub-application**, never on the parent.
Starlette resolves exception handlers per application, and the platform already
owns handlers for ``StarletteHTTPException`` and ``Exception`` (Q88 — HTML for
pages, ``{"detail": …}`` for ``/health`` and ``/<slug>/api/*``). Registering a
second handler for those classes on the parent would silently replace that
contract everywhere; scoping them to the sub-app makes the two surfaces
independent by construction.

``server/app.py`` keeps one small branch for the case the sub-app cannot cover:
requests to ``/api/v1`` while the surface is switched **off**, where there is no
sub-app to answer and the caller must still get a problem document.
"""
from __future__ import annotations

import logging

from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from platform_core.public_api import errors as api_errors, protocol
from platform_core.public_api.errors import (ApiError, ApiProblem,
                                             PROBLEM_CONTENT_TYPE)
from server.api.context import request_id


def is_public_api_path(path: str, prefix: str = "/api/v1") -> bool:
    """True for the Public API surface only — never for app-nested APIs."""
    return path == prefix or path.startswith(prefix + "/")


def problem_response(problem: ApiProblem) -> JSONResponse:
    body = problem.to_dict()
    headers = {"Cache-Control": "no-store"}
    # `retry_after` has been in the body since the limiter shipped, which the
    # platform's own SDKs read. Every other HTTP client in the world reads the
    # header instead — a proxy, a load generator, `requests` with a retry
    # adapter — so the same number goes in both places (EXT-02).
    retry_after = body.get("retry_after")
    if isinstance(retry_after, int) and retry_after > 0:
        headers[protocol.HEADER_RETRY_AFTER] = str(retry_after)
    return JSONResponse(
        body, status_code=problem.status, media_type=PROBLEM_CONTENT_TYPE,
        headers=headers,
    )


def api_error_response(request: Request, exc: ApiError) -> JSONResponse:
    # Remembered for the request log: the stable code is what a developer
    # branches on, and the only part of a failure worth storing.
    request.state.api_error_code = exc.code
    return problem_response(exc.problem(
        instance=request.url.path, request_id=request_id(request)))


def status_problem_response(request: Request, status: int,
                            detail: object = "") -> JSONResponse:
    """Render a framework-raised status (404/405/…) as a problem document."""
    problem = api_errors.problem_for_status(
        status, detail, instance=request.url.path,
        request_id=request_id(request))
    request.state.api_error_code = problem.code
    return problem_response(problem)


async def validation_error_handler(request: Request, exc: RequestValidationError):
    """422 as problem+json for ``/api/v1``; untouched elsewhere.

    The non-API branch delegates to FastAPI's own handler rather than a copy of
    it, so installing this cannot change what any existing route returns.
    """
    if not is_public_api_path(request.url.path):
        return await request_validation_exception_handler(request, exc)
    return problem_response(ApiProblem(
        status=422, code=api_errors.CODE_UNPROCESSABLE,
        detail=exc.errors(), instance=request.url.path,
        request_id=request_id(request),
    ))


def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Routing/framework statuses (404, 405, 401 from a dependency, …)."""
    return status_problem_response(request, exc.status_code, exc.detail)


def unhandled_exception_handler(request: Request, exc: Exception):
    """Last resort: a fixed 500 body, never the exception text.

    Provider SDKs put credentials and customer payloads in exception messages,
    and a traceback is free reconnaissance. The real cause is logged with the
    correlation id, which is what support needs.
    """
    logging.getLogger(__name__).exception(
        "unhandled public api error [%s] %s %s", request_id(request),
        request.method, request.url.path)
    return status_problem_response(request, 500)


def install_api_error_handlers(api) -> None:
    """Register the handlers on the public sub-application only."""
    api.add_exception_handler(ApiError, api_error_response)
    api.add_exception_handler(RequestValidationError, validation_error_handler)
    api.add_exception_handler(StarletteHTTPException, http_exception_handler)
    api.add_exception_handler(Exception, unhandled_exception_handler)
