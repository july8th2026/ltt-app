"""``/developers`` — the portal where a customer manages their API keys.

This is the **session** surface, not the API one, and the difference is the
whole point:

* it authenticates with the platform's login session and therefore **must** have
  CSRF protection on every state-changing POST — a browser attaches session
  cookies to cross-site requests automatically. ``/api/v1`` is the opposite: it
  refuses cookies and needs no CSRF (see ``server/api/auth.py``);
* it is the only place a developer key is ever created, and the plaintext is
  shown **once**, on the response to the request that created it. A refresh
  cannot bring it back, because nothing on the server can reproduce it.

Deliberately not here: any provider credential. ``platform_core.api_keys`` holds
the platform's own keys for Gemini and friends; a customer has no business
seeing that they exist, let alone their preview.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_core import credit
from platform_core.i18n import N_, _ as _t
from platform_core.models import Job
from platform_core.public_api import keys as devkeys, projects, sandbox, usage
from platform_core.public_api.catalog import build_catalog
from platform_core.public_api.config import load_public_api_config
from platform_core.public_api.invocation import api_meta
from platform_core.public_api.scopes import DEFAULT_SCOPES, KNOWN_SCOPES
from platform_core.public_api.tables import WebhookSubscription
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import get_db, user_hien_tai
from server.templating import templates

_log = logging.getLogger("ltt.developers")

router = APIRouter(prefix="/developers", tags=["developers"])

# How many finished/queued API jobs the portal shows. Enough to answer "did my
# integration work"; not a job browser — that is what `/api/v1/jobs` is for.
RECENT_JOBS = 10


def require_account(request: Request):
    """The signed-in database user. The admin-env path has no account to bill.

    Declared **before** the database dependency on every route below, so an
    anonymous visitor is bounced to the login page instead of first opening a
    session — which on a server with no database configured turned a redirect
    into a 500.
    """
    require_login(request)
    user = user_hien_tai(request)
    if user is None:
        # Break-glass admin (Q29) has no `users` row, so no keys and no credit.
        raise _redirect("/login?next=/developers")
    return user


def _redirect(location: str, status_code: int = 303):
    from fastapi import HTTPException

    return HTTPException(status_code=status_code, headers={"Location": location})


def _webhooks(db: Session, user_id: str) -> list:
    return list(db.execute(select(WebhookSubscription).where(
        WebhookSubscription.user_id == user_id,
        WebhookSubscription.enabled.is_(True),
    ).order_by(WebhookSubscription.created_at.desc())).scalars().all())


def _all_webhooks(db: Session, user_id: str) -> list:
    """Including the disabled ones: an endpoint you turned off is still part of
    the story its delivery history tells."""
    return list(db.execute(select(WebhookSubscription).where(
        WebhookSubscription.user_id == user_id,
    ).order_by(WebhookSubscription.created_at.desc())).scalars().all())


def _recent_api_jobs(db: Session, user_id: str) -> list:
    """Jobs this account created through the API, newest first."""
    rows = db.execute(select(Job).where(Job.user_id == user_id)
                      .order_by(Job.created_at.desc()).limit(50)).scalars().all()
    found = []
    for job in rows:
        meta = api_meta(job)
        if not meta:
            continue        # made in the UI, not through the API
        found.append({"id": job.id, "tool": meta.get("tool") or "",
                      "status": job.status, "created_at": job.created_at,
                      "key_id": meta.get("key_id") or ""})
        if len(found) >= RECENT_JOBS:
            break
    return found


def _public_api_config(request: Request):
    """The configuration this application was mounted with.

    Read from app state rather than the environment: the portal must describe
    the API this process is actually serving, and an app built with an explicit
    env mapping (tests, a second instance) would otherwise be described by
    whatever the process environment happens to say.
    """
    config = getattr(request.app.state, "public_api", None)
    return config if config is not None else load_public_api_config()


# The area's information architecture, in one place. `href=None` means the
# section is named but not built yet: EXT-08 owns the playground, EXT-09 the
# request logs, EXT-11 the notifications. Showing them greyed is honest about
# the shape of the area; a link that 404s is not. OAuth apps are absent rather
# than greyed, because D1 decided not to build them at all.
SECTIONS = (
    ("overview", "/developers", N_("Tổng quan")),
    ("quickstart", "/developers/quickstart", N_("Bắt đầu nhanh")),
    ("projects", "/developers/projects", N_("Project")),
    ("keys", "/developers/keys", N_("Khóa API")),
    ("tools", "/developers/tools", N_("Công cụ & model")),
    ("playground", "/developers/playground", N_("Playground")),
    ("pricing", "/developers/pricing", N_("Giá & mô phỏng")),
    ("logs", "/developers/logs", N_("Nhật ký request")),
    ("jobs", "/developers/jobs", N_("Job")),
    ("usage", "/developers/usage", N_("Sử dụng & credit")),
    ("webhooks", "/developers/webhooks", N_("Webhook")),
    ("notifications", "/developers/notifications", N_("Thông báo")),
    ("docs", "/developers/docs", N_("Tài liệu & SDK")),
    ("settings", "/developers/settings", N_("Cài đặt & bảo mật")),
)


def _nav(active: str) -> list:
    return [{"key": key, "href": href, "label": _t(label),
             "active": key == active}
            for key, href, label in SECTIONS]


def _title(active: str) -> str:
    for key, _href, label in SECTIONS:
        if key == active:
            return _t(label)
    return _t(N_("Tổng quan"))


def _base_context(request: Request, db: Session, user, active: str,
                  error: str = "") -> dict:
    """What every section needs: navigation, service state, CSRF."""
    config = _public_api_config(request)
    return {
        "csrf_token": issue_csrf_token(request),
        "api_enabled": config.enabled,
        "read_only": config.read_only,
        "nav": _nav(active),
        "section_title": _title(active),
        "error": error,
    }


def _projects_context(db: Session, user) -> dict:
    rows = projects.list_for(db, user_id=user.id)
    return {"projects": [
        {"id": project.id, "name": project.name, "slug": project.slug,
         "created_at": project.created_at,
         "key_count": len(projects.keys_of(db, project_id=project.id))}
        for project in rows]}


def _keys_context(db: Session, user, config) -> dict:
    now = datetime.now(timezone.utc)
    names = {project.id: project.name
             for project in projects.list_for(db, user_id=user.id,
                                              include_archived=True)}
    return {
        "keys": [
            {
                "key_id": key.key_id, "name": key.name,
                "status": key.status(now=now),
                "scopes": list(key.scopes or ()),
                "allowed_tools": list(key.allowed_tools or ()),
                "allowed_ips": list(key.allowed_ips or ()),
                "project": names.get(str(key.project_id or ""), ""),
                "mode": str(getattr(key, "mode", "live") or "live"),
                "created_at": key.created_at,
                "last_used_at": key.last_used_at,
                "expires_at": key.expires_at,
            }
            for key in devkeys.list_for_user(db, user.id)
        ],
        "scopes": sorted(KNOWN_SCOPES),
        "default_scopes": list(DEFAULT_SCOPES),
        "modes": list(sandbox.MODES),
        "tools": [tool.name for tool in build_catalog(config)],
    }


def _usage_context(db: Session, user, config) -> dict:
    now = datetime.now(timezone.utc)
    window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "balance": credit.so_du(db, user.id),
        "usage_today": usage.usage_totals(db, user_id=user.id,
                                          since=window_start, until=now),
        "limits": {
            "request_rpm": config.request_rpm,
            "create_rpm": config.create_rpm,
            "max_active_jobs": config.max_active_jobs,
            "daily_credit_limit": config.daily_credit_limit,
        },
    }


def _overview_counts(db: Session, user) -> dict:
    """The numbers the overview answers "is anything wrong?" with."""
    from sqlalchemy import func

    from platform_core.public_api.tables import (WEBHOOK_DEAD, WEBHOOK_FAILED,
                                                 WebhookDelivery)

    now = datetime.now(timezone.utc)
    active_keys = sum(1 for key in devkeys.list_for_user(db, user.id)
                      if key.is_usable(now=now))
    failures = int(db.execute(
        select(func.count(WebhookDelivery.id)).where(
            WebhookDelivery.user_id == user.id,
            WebhookDelivery.status.in_((WEBHOOK_FAILED, WEBHOOK_DEAD)),
        )).scalar_one())
    since = now - timedelta(days=30)
    api_jobs = sum(1 for job in db.execute(
        select(Job).where(Job.user_id == user.id,
                          Job.created_at >= since)).scalars().all()
        if api_meta(job))
    return {
        "projects": len(projects.list_for(db, user_id=user.id)),
        "active_keys": active_keys,
        "webhooks": len(_webhooks(db, user.id)),
        "webhook_failures": failures,
        "api_jobs": api_jobs,
    }


def _render(request: Request, db: Session, user, active: str, template: str,
            **extra) -> HTMLResponse:
    context = _base_context(request, db, user, active,
                            error=str(extra.pop("error", "") or ""))
    context.update(extra)
    return templates.TemplateResponse(request, template, context)


def _keys_page(request: Request, db: Session, user, *, revealed: str = "",
               error: str = "", created_key=None) -> HTMLResponse:
    config = _public_api_config(request)
    return _render(request, db, user, "keys", "dev_keys.html",
                   error=error, revealed_secret=revealed,
                   created_key=created_key,
                   **_projects_context(db, user),
                   **_keys_context(db, user, config))


@router.get("", response_class=HTMLResponse)
def developer_overview(request: Request, user=Depends(require_account),
                       db: Session = Depends(get_db)):
    config = _public_api_config(request)
    return _render(request, db, user, "overview", "dev_overview.html",
                   counts=_overview_counts(db, user),
                   **_usage_context(db, user, config))


@router.get("/projects", response_class=HTMLResponse)
def developer_projects(request: Request, user=Depends(require_account),
                       db: Session = Depends(get_db)):
    return _render(request, db, user, "projects", "dev_projects.html",
                   **_projects_context(db, user))


@router.get("/keys", response_class=HTMLResponse)
def developer_keys(request: Request, user=Depends(require_account),
                   db: Session = Depends(get_db)):
    return _keys_page(request, db, user)


@router.get("/quickstart", response_class=HTMLResponse)
def developer_quickstart(request: Request, tool: str = "",
                         user=Depends(require_account),
                         db: Session = Depends(get_db)):
    """Everything a new integration needs, generated from the live catalog.

    The snippets are not written here and not stored anywhere: they are built
    from the same contract the API validates against, so an example cannot
    describe a call the server would reject.
    """
    from platform_core.public_api import examples

    config = _public_api_config(request)
    catalog = build_catalog(config)
    chosen = None
    for candidate in catalog:
        if candidate.name == str(tool or "") or (not tool and chosen is None):
            chosen = candidate
            if tool:
                break

    snippets = []
    if chosen is not None:
        snippets = [
            ("cURL — " + _t("báo giá"), examples.curl_quote(chosen)),
            ("cURL — " + _t("chạy job"), examples.curl_submit(chosen)),
            ("Python", examples.python_snippet(chosen)),
            ("TypeScript", examples.typescript_snippet(chosen)),
            ("PowerShell", examples.powershell_snippet(chosen)),
            ("HTTP", examples.raw_http_snippet(chosen)),
        ]
    return _render(
        request, db, user, "quickstart", "dev_quickstart.html",
        env_vars=examples.ENV_VARS, shells=examples.SHELL_EXPORTS,
        no_code=examples.NO_CODE_RECIPES,
        tool={"name": chosen.name} if chosen is not None else None,
        tool_names=[item.name for item in catalog],
        snippets=snippets,
        retry_snippet=RETRY_EXAMPLE)


# One idempotency key per logical call, reused on every retry of it. Written
# out rather than described, because "reuse the key" is the sentence everyone
# agrees with and then implements as `uuid4()` inside the retry loop.
RETRY_EXAMPLE = """key = str(uuid.uuid4())          # ONCE, outside the loop

for attempt in range(5):
    try:
        job = call("POST", "/jobs", body, {"Idempotency-Key": key})
        break
    except Timeout:               # the request may have succeeded
        time.sleep(2 ** attempt)  # same key -> replay, not a second job"""

@router.get("/pricing", response_class=HTMLResponse)
def developer_pricing(request: Request, user=Depends(require_account),
                      db: Session = Depends(get_db)):
    """What a call would cost, priced by the code that really charges.

    The number here comes from `invocation.price` — the same function the quote
    route calls — bounded by the same published regime. A simulator with its own
    arithmetic would answer a question nobody asked: what matters is what the
    customer will actually be billed, and that stays true only while one piece
    of code produces both numbers.

    Nothing is charged and no quote token is minted, so a simulation cannot be
    presented at `POST /jobs`.
    """
    from platform_core.public_api import examples, pricing

    config = _public_api_config(request)
    catalog = build_catalog(config)
    wanted = str(request.query_params.get("tool") or "")
    tool = next((item for item in catalog if item.name == wanted),
                catalog[0] if catalog else None)

    raw_input = str(request.query_params.get("input") or "").strip()
    payload, error, result = {}, "", None
    if tool is not None:
        if raw_input:
            import json

            try:
                payload = json.loads(raw_input)
                if not isinstance(payload, dict):
                    raise ValueError(_t("input phải là một object JSON"))
            except (ValueError, TypeError) as exc:
                error = str(exc)
                payload = {}
        else:
            payload = examples.example_input(tool)

        if not error:
            try:
                result = pricing.simulate(db, tool=tool, params=payload)
            except Exception as exc:  # noqa: BLE001 - shown to this customer
                # Surfaced rather than swallowed: a price that cannot be
                # computed is exactly what somebody came here to find out.
                _log.warning("mo phong gia that bai cho %s: %s: %s",
                             tool.name, type(exc).__name__, exc)
                error = _t("Không tính được giá cho đầu vào này.")

    import json as _json

    return _render(request, db, user, "pricing", "dev_pricing.html",
                   tools=[item.name for item in catalog],
                   chosen=tool.name if tool is not None else "",
                   input_json=_json.dumps(payload, ensure_ascii=False,
                                          indent=2),
                   result=result, error=error)


@router.get("/playground", response_class=HTMLResponse)
def developer_playground(request: Request, user=Depends(require_account),
                         db: Session = Depends(get_db)):
    """A request builder that calls the public API the way a customer does.

    The page holds no credential and the server mints none for it: the browser
    sends the developer's own key straight to `/api/v1`. A portal endpoint that
    borrowed the session instead would be a second road to the chargeable path,
    and the platform has exactly one on purpose — a policy bug on the second one
    costs real money.
    """
    import json

    config = _public_api_config(request)
    catalog = build_catalog(config)
    published = [tool.to_public_dict() for tool in catalog]
    return _render(request, db, user, "playground", "dev_playground.html",
                   catalog=[{"name": item["name"],
                             "execution_mode": item["execution_mode"]}
                            for item in published],
                   # Escaped for embedding in a <script> block: a schema that
                   # happened to contain "</script>" would otherwise end the
                   # element and become markup.
                   catalog_json=json.dumps(published, ensure_ascii=False)
                   .replace("<", "\\u003c"))


#: Status filters people actually think in. "4xx" is a question, "412" is not.
STATUS_CHOICES = (("2xx", N_("Thành công (2xx)")),
                  ("4xx", N_("Lỗi của request (4xx)")),
                  ("401", N_("Không xác thực được (401)")),
                  ("403", N_("Thiếu quyền (403)")),
                  ("409", N_("Xung đột (409)")),
                  ("422", N_("Sai dữ liệu (422)")),
                  ("429", N_("Vượt hạn mức (429)")),
                  ("5xx", N_("Lỗi máy chủ (5xx)")))


@router.get("/logs", response_class=HTMLResponse)
def developer_logs(request: Request, request_id: str = "", status: str = "",
                   tool: str = "", key_id: str = "",
                   user=Depends(require_account),
                   db: Session = Depends(get_db)):
    """This account's own API calls — including the ones that never ran.

    A job explains a job. Nothing else explained the 401 that stopped an
    integration, the 403 that named a scope the developer thought they had, or
    the 429 that arrived when their queue backed up; those are exactly the calls
    somebody needs to look up, and until now only an operator could.
    """
    from platform_core.public_api import request_log

    config = _public_api_config(request)
    since = datetime.now(timezone.utc) - timedelta(days=7)
    rows = request_log.list_for(db, user_id=user.id, request_id=request_id,
                                status=status, tool=tool, key_id=key_id,
                                limit=100)
    return _render(
        request, db, user, "logs", "dev_logs.html",
        rows=rows,
        counts=request_log.counts(db, user_id=user.id, since=since),
        retention_days=request_log.RETENTION_DAYS,
        tools=[item.name for item in build_catalog(config)],
        keys=[{"key_id": key.key_id, "name": key.name}
              for key in devkeys.list_for_user(db, user.id)],
        status_choices=[(value, _t(label)) for value, label in STATUS_CHOICES],
        filters={"request_id": request_id, "status": status, "tool": tool,
                 "key_id": key_id,
                 "any": bool(request_id or status or tool or key_id)})


@router.get("/logs/{wanted_id}", response_class=HTMLResponse)
def developer_log_detail(request: Request, wanted_id: str,
                         user=Depends(require_account),
                         db: Session = Depends(get_db)):
    """One request, and everything reachable from it.

    Assembled from rows that already exist — the job, its customer-visible
    events, the ledger entries, the artifacts, the webhook deliveries. Storing a
    second copy of any of that would be a second thing to keep true.
    """
    from platform_core.public_api import request_log
    from platform_core.public_api.error_registry import REGISTRY

    row = request_log.get_owned(db, user_id=user.id, request_id=wanted_id)
    if row is None:
        # Same 404 a request that never existed gets: a log page must not
        # confirm that somebody else's request id is real.
        raise _redirect("/developers/logs", status_code=404)
    spec = REGISTRY.get(row.code)
    names = {project.id: project.name
             for project in projects.list_for(db, user_id=user.id,
                                              include_archived=True)}
    return _render(
        request, db, user, "logs", "dev_log_detail.html",
        section_title=row.request_id[:8],
        row=row, timeline=request_log.timeline(db, row),
        project_name=names.get(row.project_id, ""),
        advice=({"action": spec.action, "retry": spec.retry,
                 "reuse_idempotency_key": spec.reuse_idempotency_key}
                if spec is not None else None))

@router.get("/tools", response_class=HTMLResponse)
def developer_tools(request: Request, q: str = "", capability: str = "",
                    user=Depends(require_account),
                    db: Session = Depends(get_db)):
    from platform_core.public_api.catalog import build_models, capabilities_of

    config = _public_api_config(request)
    catalog = build_catalog(config)
    needle = str(q or "").strip().lower()
    wanted = str(capability or "").strip()

    def _matches(tool) -> bool:
        if wanted and tool.capability != wanted:
            return False
        if not needle:
            return True
        # Search the parameter names too: "aspect_ratio" is how somebody looks
        # for the tool that takes it.
        haystack = " ".join([tool.name, tool.description,
                             " ".join(tool.input_schema.get("properties", {}))])
        return needle in haystack.lower()

    shown = [tool for tool in catalog if _matches(tool)]
    return _render(request, db, user, "tools", "dev_tools.html",
                   query=needle, capability=wanted,
                   capabilities=capabilities_of(catalog),
                   catalog=[{"name": tool.name, "description": tool.description,
                             "capability": tool.capability,
                             "execution_mode": tool.execution_mode,
                             "scopes": list(tool.scopes)}
                            for tool in shown],
                   models=[model.to_public_dict()
                           for model in build_models(shown)])


@router.get("/tools/{tool_name}", response_class=HTMLResponse)
def developer_tool_detail(request: Request, tool_name: str,
                          user=Depends(require_account),
                          db: Session = Depends(get_db)):
    """The reference page for one tool, rendered from its contract.

    Nothing here is written twice: every field comes from the same catalog the
    API serves, so a page cannot describe a parameter the server does not
    accept. That is the whole point of generating it (EXT-06).
    """
    from platform_core.public_api.catalog import build_models, require_tool
    from platform_core.public_api.error_registry import as_rows
    from platform_core.public_api.protocol import MODE_RULES
    from platform_core.public_api.webhooks import TERMINAL_EVENTS

    config = _public_api_config(request)
    catalog = build_catalog(config)
    try:
        tool = require_tool(catalog, tool_name)
    except Exception as exc:  # noqa: BLE001 - a missing tool is a 404 page
        from platform_core.public_api.errors import ApiError

        if not isinstance(exc, ApiError):
            raise
        raise _redirect("/developers/tools", status_code=404) from exc

    body = tool.to_public_dict()
    schema = body["input_schema"]
    required = set(schema.get("required", ()))
    params = []
    for name, spec in schema.get("properties", {}).items():
        bounds = ""
        if "minimum" in spec or "maximum" in spec:
            bounds = f"{spec.get('minimum', '')}–{spec.get('maximum', '')}"
        elif "maxLength" in spec:
            bounds = _t("tối đa %(n)s ký tự") % {"n": spec["maxLength"]}
        params.append({
            "name": name, "type": spec.get("type", "string"),
            "required": name in required, "enum": spec.get("enum"),
            "bounds": bounds, "default": spec.get("default"),
            "description": spec.get("description", ""),
            "example": (spec.get("examples") or [None])[0],
        })

    example = _example_request(tool, params)
    outputs = body["output_schema"].get("properties", {})
    return _render(
        request, db, user, "tools", "dev_tool_detail.html",
        section_title=tool.name, tool=body, params=params,
        mode_rule=MODE_RULES.get(tool.execution_mode, ""),
        example_request=example,
        has_artifacts=any(str(spec.get("type", "")).startswith("artifact")
                          for spec in outputs.values()),
        models=[model.to_public_dict() for model in build_models([tool])],
        events=sorted(TERMINAL_EVENTS),
        errors=as_rows(),
        limits={"request_rpm": config.request_rpm,
                "create_rpm": config.create_rpm,
                "max_active_jobs": config.max_active_jobs,
                "daily_credit_limit": config.daily_credit_limit,
                "max_body_kib": config.max_body_bytes // 1024})


def _example_request(tool, params) -> str:
    """A quote call a reader can paste, built from the tool's own examples."""
    import json

    payload = {}
    for param in params:
        if param["example"] is not None:
            payload[param["name"]] = param["example"]
        elif param["required"] and param["default"] is None:
            payload[param["name"]] = f"<{param['type']}>"
    body = json.dumps({"tool": tool.name, "input": payload},
                      ensure_ascii=False, indent=2)
    return (f'curl -X POST "$LTT_BASE_URL/api/v1/quotes" \\\n'
            f'  -H "Authorization: Bearer $LTT_API_KEY" \\\n'
            f'  -H "Content-Type: application/json" \\\n'
            f"  -d '{body}'")


@router.get("/jobs", response_class=HTMLResponse)
def developer_jobs(request: Request, user=Depends(require_account),
                   db: Session = Depends(get_db)):
    return _render(request, db, user, "jobs", "dev_jobs.html",
                   recent_jobs=_recent_api_jobs(db, user.id))


@router.get("/usage", response_class=HTMLResponse)
def developer_usage(request: Request, tool: str = "", key_id: str = "",
                    status: str = "", user=Depends(require_account),
                    db: Session = Depends(get_db)):
    return _usage_page(request, db, user, tool=tool, key_id=key_id,
                       status=status)


def _usage_page(request: Request, db: Session, user, *, tool: str = "",
                key_id: str = "", status: str = "",
                error: str = "") -> HTMLResponse:
    from platform_core.public_api import budgets as budget_mod

    config = _public_api_config(request)
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=30)
    lines = usage.usage_lines(db, user_id=user.id, since=window_start,
                              until=now, tool=tool, key_id=key_id, limit=50)
    if status:
        lines = [line for line in lines if line.get("status") == status]

    names = {project.id: project.name
             for project in projects.list_for(db, user_id=user.id,
                                              include_archived=True)}
    rows = []
    for budget in budget_mod.list_for(db, user_id=user.id):
        state = budget_mod.status(db, budget)
        rows.append({
            "budget": budget, "spent": state["spent"],
            "amount": state["amount"], "percent": state["percent"],
            "scope_label": (names.get(budget.project_id, budget.project_id)
                            if budget.scope == budget_mod.SCOPE_PROJECT
                            else _t("cả tài khoản")),
        })

    return _render(
        request, db, user, "usage", "dev_usage.html", error=error,
        budgets=rows, lines=lines,
        tools=[item.name for item in build_catalog(config)],
        keys=[{"key_id": key.key_id, "name": key.name}
              for key in devkeys.list_for_user(db, user.id)],
        statuses=["queued", "running", "succeeded", "failed", "cancelled"],
        filters={"tool": tool, "key_id": key_id, "status": status},
        **_projects_context(db, user),
        **_usage_context(db, user, config))


@router.post("/budgets", response_class=HTMLResponse)
def developer_create_budget(request: Request, amount: str = Form(""),
                            period: str = Form("month"),
                            project_id: str = Form(""),
                            hard_cap: str = Form(""),
                            csrf_token: str = Form(""),
                            user=Depends(require_account),
                            db: Session = Depends(get_db)):
    from platform_core.public_api import budgets as budget_mod

    if not verify_csrf_token(request, csrf_token):
        raise _redirect("/developers/usage")
    scope = (budget_mod.SCOPE_PROJECT if project_id
             else budget_mod.SCOPE_ACCOUNT)
    try:
        budget_mod.create(db, user_id=user.id, amount=amount, period=period,
                          scope=scope, project_id=project_id,
                          hard_cap=bool(hard_cap))
    except budget_mod.BudgetError as exc:
        db.rollback()
        return _usage_page(request, db, user, error=str(exc))
    db.commit()
    raise _redirect("/developers/usage")


@router.post("/budgets/{budget_id}/delete")
def developer_delete_budget(request: Request, budget_id: str,
                            csrf_token: str = Form(""),
                            user=Depends(require_account),
                            db: Session = Depends(get_db)):
    from platform_core.public_api import budgets as budget_mod

    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers/usage", status_code=303)
    budget = budget_mod.get_owned(db, user_id=user.id, budget_id=budget_id)
    if budget is not None:
        db.delete(budget)
        db.commit()
    return RedirectResponse("/developers/usage", status_code=303)


@router.get("/notifications", response_class=HTMLResponse)
def developer_notifications(request: Request, user=Depends(require_account),
                            db: Session = Depends(get_db)):
    from platform_core.public_api import notifications

    return _render(request, db, user, "notifications",
                   "dev_notifications.html",
                   rows=notifications.list_for(db, user_id=user.id))


@router.post("/notifications/read")
def developer_notifications_read(request: Request, csrf_token: str = Form(""),
                                 user=Depends(require_account),
                                 db: Session = Depends(get_db)):
    from platform_core.public_api import notifications

    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers/notifications", status_code=303)
    notifications.mark_all_read(db, user_id=user.id)
    db.commit()
    return RedirectResponse("/developers/notifications", status_code=303)


#: Session slot for a value that must be shown once and never persisted.
SECRET_ONCE_KEY = "webhook_secret_once"

VERIFY_SNIPPET = """import hmac, hashlib, time

def verify(secret, headers, body):                 # body = raw bytes
    stamp = int(headers["X-LTT-Timestamp"])
    if abs(time.time() - stamp) > 300:             # replay window
        return False
    signed = f"{stamp}.{headers['X-LTT-Event-Id']}.".encode() + body
    expected = "v1=" + hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    # The header may carry several signatures during a secret rotation.
    return any(hmac.compare_digest(expected, part.strip())
               for part in headers["X-LTT-Signature"].split(","))"""


@router.get("/webhooks", response_class=HTMLResponse)
def developer_webhooks(request: Request, user=Depends(require_account),
                       db: Session = Depends(get_db)):
    from platform_core.public_api import webhook_console, webhooks as hooks

    catalog = [
        (hooks.EVENT_JOB_SUCCEEDED, _t("Job kết thúc thành công.")),
        (hooks.EVENT_JOB_FAILED, _t("Job hỏng — credit đã được hoàn.")),
        (hooks.EVENT_JOB_CANCELLED, _t("Job bị hủy — credit đã được hoàn.")),
        (webhook_console.EVENT_TEST,
         _t("Bạn bấm Gửi thử. Không job nào chạy, không credit nào chuyển.")),
    ]
    return _render(
        request, db, user, "webhooks", "dev_webhooks.html",
        subscriptions=_all_webhooks(db, user.id),
        deliveries=webhook_console.deliveries_for(db, user_id=user.id),
        health=webhook_console.health(db, user_id=user.id),
        event_catalog=catalog, payload_version=hooks.SIGNATURE_VERSION,
        headers={"signature": hooks.SIGNATURE_HEADER,
                 "timestamp": hooks.TIMESTAMP_HEADER,
                 "event": hooks.EVENT_HEADER},
        verify_snippet=VERIFY_SNIPPET,
        tolerance_s=300,
        grace_hours=int(webhook_console.ROTATION_GRACE.total_seconds() // 3600),
        # Popped: shown on exactly one render, and gone even if the page is
        # reloaded or shared.
        revealed_secret=request.session.pop(SECRET_ONCE_KEY, ""))


@router.post("/webhooks/{subscription_id}/test")
def developer_webhook_test(request: Request, subscription_id: str,
                           csrf_token: str = Form(""),
                           user=Depends(require_account),
                           db: Session = Depends(get_db)):
    """Queue a test event. Nothing runs and nothing is charged."""
    from platform_core.public_api import webhook_console

    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers/webhooks", status_code=303)
    subscription = webhook_console.owned_subscription(
        db, user_id=user.id, subscription_id=subscription_id)
    if subscription is not None and subscription.enabled:
        webhook_console.send_test(db, subscription)
        db.commit()
    return RedirectResponse("/developers/webhooks", status_code=303)


@router.post("/webhooks/{subscription_id}/rotate")
def developer_webhook_rotate(request: Request, subscription_id: str,
                             csrf_token: str = Form(""),
                             user=Depends(require_account),
                             db: Session = Depends(get_db)):
    from platform_core.public_api import webhook_console

    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers/webhooks", status_code=303)
    subscription = webhook_console.owned_subscription(
        db, user_id=user.id, subscription_id=subscription_id)
    if subscription is None:
        return RedirectResponse("/developers/webhooks", status_code=303)
    secret = webhook_console.rotate_secret(db, subscription)
    db.commit()
    # Handed over through the session, not the URL: a query string ends up in
    # browser history, in the Referer of the next click and in every access log
    # between here and the browser. The next render pops it.
    request.session[SECRET_ONCE_KEY] = secret
    return RedirectResponse("/developers/webhooks", status_code=303)


@router.post("/webhooks/{subscription_id}/disable")
def developer_webhook_disable(request: Request, subscription_id: str,
                              csrf_token: str = Form(""),
                              user=Depends(require_account),
                              db: Session = Depends(get_db)):
    from datetime import datetime as _dt

    from platform_core.public_api import webhook_console

    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers/webhooks", status_code=303)
    subscription = webhook_console.owned_subscription(
        db, user_id=user.id, subscription_id=subscription_id)
    if subscription is not None:
        # Disabled, not deleted: the delivery history is the evidence of what
        # this endpoint was told, and deleting the subscription would orphan it.
        subscription.enabled = False
        subscription.disabled_at = _dt.now(timezone.utc)
        db.commit()
    return RedirectResponse("/developers/webhooks", status_code=303)


@router.post("/webhooks/deliveries/{delivery_id}/resend")
def developer_webhook_resend(request: Request, delivery_id: str,
                             csrf_token: str = Form(""),
                             user=Depends(require_account),
                             db: Session = Depends(get_db)):
    """Try the same event again — same id, same payload, no job, no credit."""
    from platform_core.public_api import webhook_console

    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers/webhooks", status_code=303)
    delivery = webhook_console.owned_delivery(db, user_id=user.id,
                                              delivery_id=delivery_id)
    if delivery is None:
        return RedirectResponse("/developers/webhooks", status_code=303)
    try:
        webhook_console.resend(db, delivery)
        db.commit()
    except webhook_console.WebhookConsoleError:
        db.rollback()
    return RedirectResponse("/developers/webhooks", status_code=303)


@router.get("/docs", response_class=HTMLResponse)
def developer_docs(request: Request, user=Depends(require_account),
                   db: Session = Depends(get_db)):
    # The origin as the caller's browser sees it, so the copyable curl example
    # works on a laptop, behind the tunnel and in a test alike.
    return _render(request, db, user, "docs", "dev_docs.html",
                   base_url=str(request.base_url).rstrip("/"))


@router.get("/openapi/download")
def developer_openapi_download(request: Request,
                               user=Depends(require_account)):
    """The spec as a file, with the API version in its name.

    The same document `/api/v1/openapi.json` serves — fetched from the running
    app rather than rebuilt, because two ways of producing a spec is one way
    too many. What this adds is a *name*: a generated client is only debuggable
    six months later if you can tell which spec produced it.
    """
    import json

    from starlette.responses import Response

    from platform_core.public_api import protocol
    from server.api.inventory import API_V1_PREFIX

    document = None
    for route in request.app.routes:
        sub = getattr(route, "app", None)
        if sub is not None and getattr(route, "path", "") == "/api/v1" \
                and hasattr(sub, "openapi"):
            document = sub.openapi()
            break
    if document is None:
        raise _redirect("/developers/docs")

    # FastAPI adds `servers` when it *serves* the document, from the mount
    # path — so a copy taken straight from `sub.openapi()` would arrive without
    # one, and a client generated from it would have no base URL to call. Caught
    # by comparing the two byte for byte, which is the only way this kind of
    # difference gets noticed.
    document.setdefault("servers", [{"url": API_V1_PREFIX}])

    name = f"ltt-public-api-{protocol.API_VERSION}-openapi.json"
    return Response(
        json.dumps(document, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{name}"',
                 "Cache-Control": "no-store"})


@router.get("/settings", response_class=HTMLResponse)
def developer_settings(request: Request, user=Depends(require_account),
                       db: Session = Depends(get_db)):
    return _render(request, db, user, "settings", "dev_settings.html")


@router.post("/keys", response_class=HTMLResponse)
def create_key(request: Request, name: str = Form(""),
               scopes: list[str] = Form(default=[]),
               allowed_tools: list[str] = Form(default=[]),
               project_id: str = Form(""), allowed_ips: str = Form(""),
               expires_in_days: str = Form(""), mode: str = Form("live"),
               csrf_token: str = Form(""), user=Depends(require_account),
               db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        raise _redirect("/developers/keys")
    try:
        project = (projects.get_owned(db, user_id=user.id, project_id=project_id)
                   if project_id else projects.default_for(db, user_id=user.id))
        if project is None or not project.is_active():
            # Ownership is resolved from the session user, so a forged id
            # simply does not resolve — it never reaches the key.
            return _keys_page(request, db, user,
                              error=_t("Không tìm thấy project."))
        expiry = _expiry_from_days(expires_in_days)
        key, token = devkeys.issue(
            db, user_id=user.id, name=name, scopes=scopes,
            allowed_tools=allowed_tools, project_id=project.id,
            allowed_ips=_split_ips(allowed_ips), expires_at=expiry,
            mode=(sandbox.MODE_TEST if mode == sandbox.MODE_TEST
                  else sandbox.MODE_LIVE))
    except Exception as exc:  # noqa: BLE001 - message is for this one customer
        from platform_core.public_api.scopes import ScopeError

        if not isinstance(exc, (devkeys.DeveloperKeyError, ScopeError,
                                projects.ProjectError)):
            raise
        db.rollback()
        return _keys_page(request, db, user, error=str(exc))
    # The plaintext exists only in this response. Nothing stores it, and the
    # page below says so — a customer who closes the tab must create a new key.
    return _keys_page(request, db, user, revealed=token,
                      created_key=key.key_id)


@router.post("/keys/{key_id}/revoke")
def revoke_key(request: Request, key_id: str, csrf_token: str = Form(""),
               user=Depends(require_account), db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers/keys", status_code=303)
    key = devkeys.get_owned(db, user_id=user.id, key_id=key_id)
    if key is not None:
        devkeys.revoke(db, key)
    # Same redirect whether or not the key existed: a portal must not become a
    # way to find out which key ids belong to somebody else.
    return RedirectResponse("/developers/keys", status_code=303)


@router.post("/keys/{key_id}/rotate", response_class=HTMLResponse)
def rotate_key(request: Request, key_id: str, csrf_token: str = Form(""),
               user=Depends(require_account), db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        raise _redirect("/developers/keys")
    key = devkeys.get_owned(db, user_id=user.id, key_id=key_id)
    if key is None:
        return _keys_page(request, db, user, error=_t("Không tìm thấy khóa."))
    try:
        token = devkeys.rotate(db, key)
    except devkeys.DeveloperKeyError as exc:
        return _keys_page(request, db, user, error=str(exc))
    return _keys_page(request, db, user, revealed=token,
                      created_key=key.key_id)


def _split_ips(value: str) -> list:
    """Accept commas, newlines or spaces — people paste all three."""
    raw = str(value or "").replace("\n", ",").replace(" ", ",")
    return [part.strip() for part in raw.split(",") if part.strip()]


def _expiry_from_days(value: str):
    """Turn "90" into a timestamp, or nothing at all.

    A key with no expiry is the default because most integrations run for years
    and a surprise expiry at 3am is worse than a long-lived key that can be
    revoked in one click. An expiry is offered because a key handed to a
    contractor should stop working on its own.
    """
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        days = int(raw)
    except ValueError as exc:
        raise devkeys.DeveloperKeyError(
            _t("Số ngày hết hạn phải là một số nguyên.")) from exc
    if days <= 0:
        raise devkeys.DeveloperKeyError(
            _t("Số ngày hết hạn phải lớn hơn 0."))
    return datetime.now(timezone.utc) + timedelta(days=days)


@router.post("/projects", response_class=HTMLResponse)
def create_project(request: Request, name: str = Form(""),
                   csrf_token: str = Form(""), user=Depends(require_account),
                   db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        raise _redirect("/developers/projects")
    try:
        projects.create(db, user_id=user.id, name=name)
    except projects.ProjectError as exc:
        db.rollback()
        return _render(request, db, user, "projects", "dev_projects.html",
                       error=str(exc), **_projects_context(db, user))
    db.commit()
    raise _redirect("/developers/projects")


@router.post("/projects/{project_id}/archive")
def archive_project(request: Request, project_id: str,
                    csrf_token: str = Form(""), user=Depends(require_account),
                    db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers/projects", status_code=303)
    project = projects.get_owned(db, user_id=user.id, project_id=project_id)
    if project is not None:
        # Archiving revokes the project's keys and touches nothing else: jobs,
        # ledger entries and usage rows record money that moved, and retiring an
        # integration cannot make them untrue.
        projects.archive(db, project)
        db.commit()
    return RedirectResponse("/developers/projects", status_code=303)
