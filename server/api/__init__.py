"""HTTP surface of the Public API — the ``/api/v1`` kernel (Q92).

What this package is: routing, the error boundary, request context, kill
switches, size policy and the OpenAPI document for the public surface. What it
is not: business logic. Quotes, credit, jobs, uploads and artifacts stay in
``platform_core`` where the UI already uses them; this layer only adapts them to
a machine-callable contract.

**Why a mounted sub-application rather than a router on the main app.** Three
properties fall out of it, each of which had to be hand-built otherwise:

* *inventory* — the sub-app's routes are its own, so "what does ``/api/v1``
  serve" is a list, not a walk over ``_IncludedRouter`` wrappers (this FastAPI
  no longer flattens ``include_router``, see ``tests/test_152``);
* *spec isolation* — its ``/openapi.json`` describes the public routes and only
  their schemas. The platform's own spec stays development-only because it
  enumerates every internal route;
* *error boundary* — exception handlers registered on the sub-app apply to
  everything inside it and to nothing outside, so the Q88 contract for
  ``/health`` and ``/<slug>/api/*`` cannot be changed by accident.

Mounting is opt-in. With ``LTT_PUBLIC_API`` unset nothing is mounted, so an
installation that has not opted in serves exactly the routes it serves today.
"""
from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from platform_core.public_api import protocol
from platform_core.public_api.config import PublicApiConfig, load_public_api_config
from platform_core.public_api.principal import Principal
from server.api.auth import install_database_resolver, require_principal
from server.api.errors import install_api_error_handlers
from server.api.guard import PublicApiGuardMiddleware
from server.api.inventory import API_V1_PREFIX, API_V1_ROUTES, capability_areas
from server.api.jobs import register_job_routes
from server.api.tools import register_tool_routes
from server.api.uploads import register_upload_routes
from server.api.usage_routes import register_usage_routes
from server.api.webhook_routes import register_webhook_routes

PUBLIC_API_TAG = "public-api"
PUBLIC_API_TITLE = "LTT Studios Public API"
_NO_STORE = {"Cache-Control": "no-store"}


def build_public_api_app(config: PublicApiConfig) -> FastAPI:
    """Build the ``/api/v1`` sub-application. Caller decides whether to mount."""
    api = FastAPI(
        title=PUBLIC_API_TITLE,
        version=config.api_version,
        description="Public, machine-callable surface of the LTT platform.",
        # Interactive docs are a Prompt 15 (portal) decision; the machine-readable
        # document is enough for a kernel and has no HTML/asset surface.
        docs_url=None, redoc_url=None, openapi_url="/openapi.json",
    )
    api.state.public_api_config = config
    # Middleware, not a route dependency: the kill switch has to cover every
    # route on this surface, including the ones later prompts add. A dependency
    # only covers routes someone remembered to attach it to.
    api.add_middleware(PublicApiGuardMiddleware, config=config)
    if config.cors_origins:
        # Explicit origins only — never a wildcard, and never with credentials:
        # this API authenticates with a header a browser does not attach by
        # itself, so `allow_credentials` would buy nothing and cost a lot.
        from starlette.middleware.cors import CORSMiddleware

        api.add_middleware(
            CORSMiddleware, allow_origins=list(config.cors_origins),
            allow_credentials=False, allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
            max_age=600)
    install_api_error_handlers(api)
    # Credential verification is a platform capability, installed once. Tests
    # override it through `server.api.deps.set_principal_resolver`.
    install_database_resolver()

    # `description=` is passed explicitly on every route: without it FastAPI
    # publishes the handler docstring into the OpenAPI document, and these
    # docstrings explain internal design (other routes, internal rules) to the
    # next maintainer, not to a customer. Reasoning stays in the code; the spec
    # says only what a caller needs.
    @api.get("/health", tags=[PUBLIC_API_TAG],
             summary="Liveness of the public API surface",
             description="Returns ok while this API surface is serving requests.")
    def api_health() -> JSONResponse:
        """Deliberately shallow.

        A public health endpoint that probes the database or the worker hands an
        anonymous caller a way to measure internal outages and a cheap amplifier
        for load. Readiness for operators already exists at ``/health/ready``.
        """
        return JSONResponse({"status": "ok", "api_version": config.api_version},
                            headers=_NO_STORE)

    @api.get("/capabilities", tags=[PUBLIC_API_TAG],
             summary="Which public capabilities this deployment serves",
             description=("Reports the API version, whether writes are "
                          "currently accepted, and the capabilities available "
                          "to callers."))
    def api_capabilities() -> JSONResponse:
        """Only what a caller must know to plan a request.

        No provider names, no model ids, no storage backend, no flag dump: those
        describe how the platform is built, and a public surface must not expose
        internal wiring (COMMON_RULES §3).
        """
        return JSONResponse(
            {
                "api_version": config.api_version,
                # A client needs this to know whether a write will be refused
                # right now; it says nothing about why.
                "read_only": bool(config.read_only),
                # Feature areas of this API version — not this deployment's tool
                # list, which belongs behind a key at `/tools`.
                "capabilities": list(capability_areas()),
                # Which execution modes this version can actually honour. A
                # client library reads this to know whether to compile in its
                # streaming or batching path at all, instead of discovering the
                # answer from a 400 in production.
                "execution_modes": list(protocol.MODES_IN_USE),
            },
            headers=_NO_STORE,
        )

    @api.get("/me", tags=[PUBLIC_API_TAG],
             summary="Identity and permissions of the calling API key",
             description=("Returns the calling key's public id, the account it "
                          "bills to, its scopes and its tool allowlist."))
    def api_me(principal: Principal = Depends(require_principal)) -> JSONResponse:
        """The one authenticated route the kernel owns.

        It answers only about the credential that was presented — no account
        profile, no email, no billing detail. A developer needs it to confirm
        which key a deployment is actually using, which is otherwise guesswork
        once several keys exist.
        """
        return JSONResponse(
            {
                "key_id": principal.key_id,
                "account_id": principal.user_id,
                "scopes": sorted(principal.scopes),
                "allowed_tools": sorted(principal.allowed_tools),
            },
            headers=_NO_STORE,
        )

    register_tool_routes(api, config, PUBLIC_API_TAG)
    register_job_routes(api, config, PUBLIC_API_TAG)
    register_upload_routes(api, config, PUBLIC_API_TAG)
    register_webhook_routes(api, config, PUBLIC_API_TAG)
    register_usage_routes(api, config, PUBLIC_API_TAG)
    return api


def mount_public_api(app, *, env: dict | None = None) -> PublicApiConfig:
    """Mount ``/api/v1`` when enabled. Returns the resolved configuration.

    The parent application keeps a problem+json branch for this prefix even when
    the surface is off (see ``server/app.py``): a client must not discover the
    switch by receiving an HTML error page.
    """
    config = load_public_api_config(env)
    if config.enabled:
        api = build_public_api_app(config)
        # The quote signer reuses the platform session secret (same choice as
        # `apps/taovideo/quotes.py` — one secret to rotate, not two). It lives on
        # the sub-app's state rather than in `PublicApiConfig` so it cannot be
        # printed by a stray repr of the configuration.
        settings = getattr(app.state, "server_settings", None)
        api.state.quote_secret = getattr(settings, "session_secret", "") or ""
        app.mount(API_V1_PREFIX, api, name="public_api")
    return config


def public_api_routes(api: FastAPI) -> set:
    """``(method, absolute path)`` served by a built sub-application."""
    found = set()
    for route in api.routes:
        path = str(getattr(route, "path", ""))
        if not path:
            continue
        for method in sorted(getattr(route, "methods", set()) or set()):
            if method in {"HEAD", "OPTIONS"}:
                continue
            found.add((method, f"{API_V1_PREFIX}{path}"))
    return found


__all__ = ["API_V1_PREFIX", "API_V1_ROUTES", "PUBLIC_API_TAG", "PUBLIC_API_TITLE",
           "build_public_api_app", "mount_public_api", "public_api_routes"]
