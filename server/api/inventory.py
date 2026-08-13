"""The declared route inventory of ``/api/v1``.

COMMON_RULES §3: *no V1 route outside the registry and the contract tests*. A
public API grows by accident otherwise — someone adds a debug endpoint, it ships,
and now it is a contract that has to be supported and security-reviewed forever.

This tuple is that registry. ``tests/test_178_public_api_kernel.py`` asserts the
mounted routes and the published OpenAPI document match it exactly, in both
directions, so adding a route without declaring it fails the gate, and declaring
one without building it fails too.
"""
from __future__ import annotations

from dataclasses import dataclass

from platform_core.public_api.protocol import ASYNC_JOB, SYNC

API_V1_PREFIX = "/api/v1"


@dataclass(frozen=True)
class ApiRoute:
    method: str
    path: str
    summary: str
    authenticated: bool
    in_schema: bool = True
    #: How this operation executes (EXT-02). Defaulting to SYNC is safe here in
    #: a way it would not be for a tool: a route that forgets to declare is a
    #: read, and `test_194` refuses any SYNC route that touches the queue.
    execution_mode: str = SYNC
    #: RFC 8594 dates, emitted as headers when set. Empty until something is on
    #: its way out.
    deprecated_on: str = ""
    sunset_on: str = ""


# Prompt 02 kernel surface. Later prompts extend this list together with the
# routes they add (tools/quotes/jobs/uploads/artifacts/usage/webhooks).
API_V1_ROUTES: tuple = (
    ApiRoute("GET", f"{API_V1_PREFIX}/health",
             "Liveness of the public API surface", authenticated=False),
    ApiRoute("GET", f"{API_V1_PREFIX}/capabilities",
             "Which public capabilities this deployment serves",
             authenticated=False),
    ApiRoute("GET", f"{API_V1_PREFIX}/me",
             "Identity and permissions of the calling API key",
             authenticated=True),
    ApiRoute("GET", f"{API_V1_PREFIX}/tools",
             "List the tools this API key may call", authenticated=True),
    ApiRoute("GET", f"{API_V1_PREFIX}/tools/{{tool_name}}",
             "Contract for one tool", authenticated=True),
    ApiRoute("GET", f"{API_V1_PREFIX}/models",
             "List the model aliases this API key may use", authenticated=True),
    ApiRoute("GET", f"{API_V1_PREFIX}/models/{{model_name}}",
             "Details of one model alias", authenticated=True),
    ApiRoute("POST", f"{API_V1_PREFIX}/quotes",
             "Price a tool call before running it", authenticated=True),
    # The one chargeable operation on the surface, and the only ASYNC_JOB route:
    # everything else here reads or arranges, this one buys.
    ApiRoute("POST", f"{API_V1_PREFIX}/jobs",
             "Run a quoted tool call", authenticated=True,
             execution_mode=ASYNC_JOB),
    ApiRoute("GET", f"{API_V1_PREFIX}/jobs",
             "List this account's jobs", authenticated=True),
    ApiRoute("GET", f"{API_V1_PREFIX}/jobs/{{job_id}}",
             "Read one job", authenticated=True),
    ApiRoute("POST", f"{API_V1_PREFIX}/jobs/{{job_id}}/cancel",
             "Cancel a job", authenticated=True),
    ApiRoute("POST", f"{API_V1_PREFIX}/uploads",
             "Create an upload ticket", authenticated=True),
    ApiRoute("POST", f"{API_V1_PREFIX}/uploads/{{upload_id}}/content",
             "Upload file content (fallback path)", authenticated=True),
    ApiRoute("POST", f"{API_V1_PREFIX}/uploads/{{upload_id}}/confirm",
             "Confirm an uploaded file", authenticated=True),
    ApiRoute("GET", f"{API_V1_PREFIX}/artifacts/{{artifact_id}}",
             "Get a short-lived download URL for a job output",
             authenticated=True),
    ApiRoute("GET", f"{API_V1_PREFIX}/artifacts/{{artifact_id}}/content",
             "Download a job output (fallback path)", authenticated=True),
    ApiRoute("POST", f"{API_V1_PREFIX}/webhooks",
             "Subscribe to job events", authenticated=True),
    ApiRoute("GET", f"{API_V1_PREFIX}/webhooks",
             "List webhook subscriptions", authenticated=True),
    ApiRoute("GET", f"{API_V1_PREFIX}/webhooks/deliveries",
             "List webhook delivery attempts", authenticated=True),
    ApiRoute("DELETE", f"{API_V1_PREFIX}/webhooks/{{webhook_id}}",
             "Delete a webhook subscription", authenticated=True),
    ApiRoute("GET", f"{API_V1_PREFIX}/credits/balance",
             "Current credit balance", authenticated=True),
    ApiRoute("GET", f"{API_V1_PREFIX}/usage",
             "Credit usage for this account", authenticated=True),
    ApiRoute("GET", f"{API_V1_PREFIX}/openapi.json",
             "OpenAPI document for the public surface only",
             authenticated=False, in_schema=False),
)


def execution_modes() -> dict:
    """Route → declared execution mode, for `/capabilities` and the tests."""
    return {f"{route.method} {route.path}": route.execution_mode
            for route in API_V1_ROUTES}


def capability_areas() -> tuple:
    """Feature areas this API version serves, derived from the inventory.

    Deliberately *not* the deployment's tool list: ``/capabilities`` answers
    anonymous callers, and "which resources does this API have" is a property of
    the version, while "which tools are published" belongs behind a key.
    ``health``/``capabilities``/``openapi.json``/``me`` are the kernel itself and
    say nothing about capability, so they are excluded.
    """
    kernel = {"health", "capabilities", "openapi.json", "me"}
    areas = []
    for route in API_V1_ROUTES:
        segment = route.path[len(API_V1_PREFIX):].strip("/").split("/")[0]
        if segment and segment not in kernel and segment not in areas:
            areas.append(segment)
    return tuple(areas)


def declared_paths() -> frozenset:
    return frozenset((route.method, route.path) for route in API_V1_ROUTES)


def documented_paths() -> frozenset:
    return frozenset((route.method, route.path) for route in API_V1_ROUTES
                     if route.in_schema)
