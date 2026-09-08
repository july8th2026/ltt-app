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

from platform_core.public_api.protocol import (ASYNC_JOB, STREAM, SYNC,
                                              SYNC_BILLED)

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
    # The second chargeable operation, and the only SYNC_BILLED one (Q106): it
    # bills like /jobs but answers in the request. It carries no quote because
    # the price depends on tokens that do not exist until the model has run, so
    # the Idempotency-Key is the only thing standing between a network retry and
    # paying twice — `check_mode_rules` refuses the declaration without it.
    ApiRoute("POST", f"{API_V1_PREFIX}/chat/completions",
             "Chat completion, answered in the request", authenticated=True,
             execution_mode=SYNC_BILLED),
    # The streaming pair (Q107). They exist because every CLI worth serving
    # requires streaming and each speaks exactly one protocol: Claude Code and
    # Claude Desktop speak Anthropic Messages, Codex speaks OpenAI Responses.
    #
    # Neither carries an Idempotency-Key — no CLI sends one — so what protects
    # the money is settling from the tokens actually produced rather than from
    # the hold. `check_mode_rules` refuses a STREAM contract that does not
    # declare exactly that.
    ApiRoute("POST", f"{API_V1_PREFIX}/messages",
             "Chat completion as an Anthropic Messages stream",
             authenticated=True, execution_mode=STREAM),
    ApiRoute("POST", f"{API_V1_PREFIX}/responses",
             "Chat completion as an OpenAI Responses stream",
             authenticated=True, execution_mode=STREAM),
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
    # ── WF-802: chạy workflow qua API công khai ─────────────────────────────
    #
    # `02 §WF-802` đòi đúng bộ này, và đòi nó đi qua **hạ tầng đã có** —
    # inventory, scope, idempotency, rate limit, `SYNC`/`ASYNC_JOB`, webhook
    # HMAC: *"Không dựng bộ máy API thứ hai."*
    #
    # ⭐ Vì sao có `/quotes` riêng thay vì dùng `POST /quotes` sẵn có: báo giá
    #    của một tool gắn với `(tool, input)`; báo giá của một workflow gắn với
    #    **graph đã publish**, và nó trả **HAI** số (`M8`) chứ không một. Cùng
    #    bộ máy ký (`quotes.issue`), khác thứ được ký.
    ApiRoute("POST", f"{API_V1_PREFIX}/workflows/{{workflow_id}}/quotes",
             "Price a workflow run before starting it", authenticated=True),
    # Chargeable ASYNC_JOB thứ hai của bề mặt. `check_mode_rules` bắt nó phải
    # đòi CẢ quote LẪN Idempotency-Key, và điều đó chỉ trung thực từ khi
    # `platform_core/workflow/tien.py` thật sự giữ chỗ (08/09/2026) — trước đó
    # khai `chargeable=True` là một lời hứa không có gì đứng sau.
    ApiRoute("POST", f"{API_V1_PREFIX}/workflows/{{workflow_id}}/runs",
             "Start a quoted workflow run", authenticated=True,
             execution_mode=ASYNC_JOB),
    ApiRoute("GET", f"{API_V1_PREFIX}/runs/{{run_id}}",
             "Read one workflow run", authenticated=True),
    ApiRoute("POST", f"{API_V1_PREFIX}/runs/{{run_id}}/cancel",
             "Cancel a workflow run", authenticated=True),
    ApiRoute("GET", f"{API_V1_PREFIX}/runs/{{run_id}}/artifacts",
             "List artifacts produced by a run", authenticated=True),
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
