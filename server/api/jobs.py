"""``/api/v1/quotes`` and ``/api/v1/jobs`` — the chargeable control plane.

Every route here is thin: parse, authorise, delegate to
``platform_core.public_api.invocation`` and the platform services underneath.
The transaction boundary is the request itself (``server.deps.get_db`` commits
when the handler returns and rolls back when it raises), which is what makes
"hold and job commit together, or neither does" true without any ceremony.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Body, Depends, Header, Path, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_core import credit, jobs as jobq
from platform_core.models import (JOB_CANCELLED, JOB_DONE, JOB_ERROR, JOB_QUEUED,
                                  JOB_RUNNING, Job)
from platform_core.public_api import (capacity, idempotency, invocation,
                                      limits, media, metrics, policy, quotes,
                                      sandbox)
from platform_core.public_api.catalog import build_catalog, require_tool
from platform_core.public_api.errors import (insufficient_credit,
                                             invalid_request, price_changed,
                                             service_unavailable)
from server.api.inventory import API_V1_PREFIX
from platform_core.public_api.pagination import Page, PageRequest
from platform_core.public_api.principal import Principal, ensure_owner
from platform_core.public_api.scopes import (SCOPE_JOBS_CANCEL, SCOPE_JOBS_CREATE,
                                             SCOPE_JOBS_READ)
from server.api.auth import require_scope
from server.api.uploads import resolve_upload_reference
from server.deps import get_db

_NO_STORE = {"Cache-Control": "no-store"}
OPERATION_CREATE_JOB = "jobs.create"

# What a caller may filter on. Internal job states are the same words, but the
# mapping is explicit so a future internal rename does not break clients.
PUBLIC_STATUSES = {
    "queued": JOB_QUEUED, "running": JOB_RUNNING, "succeeded": JOB_DONE,
    "failed": JOB_ERROR, "cancelled": JOB_CANCELLED,
}
_INTERNAL_TO_PUBLIC = {value: key for key, value in PUBLIC_STATUSES.items()}
_TERMINAL = {JOB_DONE, JOB_ERROR, JOB_CANCELLED}


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    aware = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return aware.isoformat()


def _refuse_if_tool_switched_off(db, principal, tool) -> None:
    """A tool an operator has switched off refuses here, not at the provider.

    Checked with the tool named, which the authentication boundary could not do:
    it knows the caller, not what the caller is about to call.
    """
    from platform_core.public_api.tables import KILL_TOOL

    refusal = policy.check(db, principal=principal, tool_name=tool.name,
                           is_write=True)
    if refusal is None or refusal.scope != KILL_TOOL:
        # Every other scope was already refused at authentication; re-raising
        # them here would only change where the same 403 comes from.
        return
    metrics.increment(metrics.KILL_SWITCH_REFUSED)
    raise service_unavailable(
        f"This tool is temporarily unavailable: {refusal.reason}",
        retry_after=refusal.retry_after, tool=tool.name)


def _refuse_if_no_capacity(db, tool) -> None:
    """Refuse work the machinery cannot do — before the hold, never after.

    Refusing costs the caller nothing. Holding credit for a job that is certain
    to fail costs a refund to reconcile and a support conversation to have.
    """
    manifest = _manifest_of(tool)
    missing = capacity.check(db, tool=tool, manifest=manifest)
    if missing is None:
        return
    metrics.increment(metrics.CAPACITY_REFUSED)
    raise service_unavailable(missing.detail,
                              retry_after=missing.retry_after,
                              resource=missing.resource)


def _manifest_of(tool):
    from platform_core.registry import discover

    for item in discover():
        if item.error or item.manifest is None:
            continue
        if item.manifest.slug == tool.app_slug:
            return item.manifest
    return None


def _public_job(db, job: Job, tool=None) -> dict:
    """The customer-safe view of a job.

    Left out on purpose: ``job_type``, ``app_slug``, ``worker_id``, raw
    ``error`` and ``params``. The first two are implementation detail a public
    contract must not pin down; the worker id is infrastructure; and the raw
    error can carry provider text (Q76 — customers see a cleaned timeline, not
    internal diagnostics).
    """
    meta = invocation.api_meta(job)
    held = credit.so_da_giu(db, job.id)
    charged = held - _adjustment(db, job.id) if job.status in _TERMINAL else 0
    body = {
        "id": job.id,
        "tool": meta.get("tool") or None,
        "status": _INTERNAL_TO_PUBLIC.get(job.status, job.status),
        "progress": int(job.progress or 0),
        "created_at": _iso(job.created_at),
        "started_at": _iso(job.started_at),
        "finished_at": _iso(job.finished_at),
        "credit": {"held": held, "charged": max(0, charged)},
        # Named on every job, not only test ones: a caller reading a response
        # should never have to infer which world produced it (EXT-12).
        "mode": meta.get("mode") or sandbox.MODE_LIVE,
    }
    if job.status == JOB_ERROR:
        body["error"] = {"message": "The job could not be completed."}
    if job.status == JOB_DONE and tool is not None:
        # Artifact ids only. The keys behind them stay internal, and each id
        # is resolvable solely by this job's owner.
        body["outputs"] = media.artifacts_of(job, tool)
        # Data outputs (a prompt package, a storyboard) are the product for
        # some tools, so they are returned inline — but only the fields the
        # published contract declares, never the whole handler result.
        result = media.results_of(job, tool)
        if result:
            body["result"] = result
    return body


def _adjustment(db, job_id: str) -> int:
    from platform_core.models import CREDIT_REFUND, CREDIT_SETTLE, CreditEntry
    from sqlalchemy import func

    return int(db.execute(
        select(func.coalesce(func.sum(CreditEntry.delta), 0)).where(
            CreditEntry.job_id == job_id,
            CreditEntry.kind.in_((CREDIT_SETTLE, CREDIT_REFUND)),
        )).scalar_one())


def _quote_secret(request: Request) -> str:
    """The signing secret, handed to the sub-app at mount time.

    Read from the sub-application's own state: inside a mounted app,
    ``request.app`` is that sub-app, so reaching for the parent's settings here
    would find nothing and silently disable quoting.
    """
    return getattr(request.app.state, "quote_secret", "") or ""


def register_job_routes(api, config, tag: str) -> None:
    """Attach the chargeable routes directly onto the public sub-application."""

    def _resource_of(tool) -> str:
        from platform_core.registry import discover

        for item in discover():
            if item.manifest.slug == tool.app_slug:
                return limits.resource_class(item.manifest)
        return "api"

    def _class_slugs(tool) -> list:
        """Apps competing for the same scarce resource as this tool."""
        from platform_core.registry import discover

        resource = _resource_of(tool)
        return [item.manifest.slug for item in discover()
                if not item.error and limits.resource_class(item.manifest) == resource]

    def _tool_of(job: Job):
        """The public tool a job came from, or None for a job made in the UI."""
        name = invocation.api_meta(job).get("tool") or ""
        if not name:
            return None
        for entry in build_catalog(config):
            if entry.name == name:
                return entry
        return None

    def _media_sessions(db, principal, tool, clean: dict) -> dict:
        """Validate every media reference the caller passed, before any money."""
        wanted = invocation.media_params(tool)
        return {name: resolve_upload_reference(db, principal, tool, name,
                                               clean[name])
                for name in wanted if name in clean}

    @api.post("/quotes", tags=[tag], summary="Price a tool call before running it",
              description=("Returns a signed quote bound to this account, tool "
                           "and input. Submit it to POST /jobs to run the call."))
    def create_quote(
        request: Request,
        body: dict = Body(...),
        principal: Principal = Depends(require_scope(SCOPE_JOBS_CREATE)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        tool_name = str((body or {}).get("tool") or "")
        tool = require_tool(build_catalog(config), tool_name, principal)
        clean = invocation.validate_public_input(tool, (body or {}).get("input"))
        sessions = _media_sessions(db, principal, tool, clean)
        # Placeholder keys: nothing is promoted at quote time because nothing
        # has paid yet (Q85). Pricing never depends on the key itself.
        params = invocation.build_job_params(
            tool, clean, media_values={name: f"upload:{session.id}"
                                       for name, session in sessions.items()})
        cost = invocation.price(tool, params)

        token, payload = quotes.issue(
            secret=_quote_secret(request), user_id=principal.user_id,
            key_id=principal.key_id, tool_name=tool.name, params=clean,
            credit=cost)
        return JSONResponse(
            {
                "quote": token,
                "tool": tool.name,
                "credit": cost,
                "expires_in": quotes.QUOTE_TTL_S,
                # What the caller can spend right now, so a client can tell the
                # difference between "too expensive" and "broken" before trying.
                "balance": credit.so_du(db, principal.user_id),
            },
            headers=_NO_STORE,
        )

    @api.post("/jobs", tags=[tag], summary="Run a quoted tool call",
              description=("Holds the quoted credit and queues the job. "
                           "Requires an Idempotency-Key header."))
    def create_job(
        request: Request,
        body: dict = Body(...),
        idempotency_key: str = Header(default="", alias="Idempotency-Key"),
        principal: Principal = Depends(require_scope(SCOPE_JOBS_CREATE)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        key = idempotency.require_key(idempotency_key)
        payload = body or {}
        tool_name = str(payload.get("tool") or "")
        tool = require_tool(build_catalog(config), tool_name, principal)

        # Validation first: a typo must never reach the ledger.
        clean = invocation.validate_public_input(tool, payload.get("input"))
        quote = quotes.verify(secret=_quote_secret(request),
                              token=str(payload.get("quote") or ""),
                              user_id=principal.user_id)
        quotes.check_matches(quote, tool_name=tool.name, params=clean)

        request_hash = idempotency.canonical_hash(
            {"tool": tool.name, "input": clean, "intent": quote.get("intent")})
        record, replay = idempotency.begin(
            db, key_id=principal.key_id, user_id=principal.user_id,
            operation=OPERATION_CREATE_JOB, key=key, request_hash=request_hash)
        if replay:
            # Same key, same request: hand back the first answer. No second
            # hold, no second job — that is the whole point of the header.
            metrics.increment(metrics.IDEMPOTENCY_REPLAY)
            request.state.api_job_id = record.job_id
            request.state.api_tool = tool.name
            return JSONResponse(record.response, status_code=200,
                                headers={**_NO_STORE, "Idempotency-Replayed": "true"})

        sessions = _media_sessions(db, principal, tool, clean)
        params = invocation.build_job_params(
            tool, clean, media_values={name: f"upload:{session.id}"
                                       for name, session in sessions.items()})
        cost = invocation.price(tool, params)
        if cost != int(quote.get("credit", -1)):
            # Price moved between quote and submit. Refusing is the only answer
            # that keeps the quote a promise (Q84).
            raise price_changed(
                "The price for this call has changed; request a new quote.",
                quoted_credit=int(quote.get("credit", 0)), current_credit=cost)

        # Admission control, after validation and before any money moves. The
        # order matters: a caller over its limits must not be charged, and a
        # caller under them must not be able to open unbounded work.
        #
        # Limits are resolved once, here, with the tool named — the tool step is
        # the narrowest in the chain and only this route knows which tool is
        # being called (EXT-14).
        resolved = policy.resolve(db, config=config, principal=principal,
                                  tool_name=tool.name)
        _refuse_if_tool_switched_off(db, principal, tool)
        _refuse_if_no_capacity(db, tool)
        limits.enforce_create_rate(key_id=principal.key_id, config=config,
                                   limits=resolved,
                                   user_id=principal.user_id)
        limits.enforce_active_jobs(
            db, principal=principal, config=config, app_slug=tool.app_slug,
            class_slugs=_class_slugs(tool), resource=_resource_of(tool),
            limits=resolved)
        # Spending limits apply to spending. A test call moves no credit, so a
        # daily ceiling or a budget would be metering something that cannot
        # happen — and requiring a balance would shut the sandbox to exactly the
        # developer it exists for, one who has not paid yet. The rate and
        # concurrency limits above still apply: those protect the machine, which
        # a test call uses like any other (EXT-12).
        testing = sandbox.is_test(principal.mode)
        if not testing:
            limits.enforce_daily_credit(db, principal=principal, config=config,
                                        cost=cost, limits=resolved)
            # …and the customer's own hard cap, which may be stricter than the
            # operator's. Whichever allows less wins (EXT-11).
            limits.enforce_budget(db, principal=principal, cost=cost)

        promotions: list = []
        try:
            job = invocation.submit(db, principal=principal, tool=tool,
                                    params=params, quote=quote,
                                    idempotency_key=key)
            if sessions:
                # After the hold, never before it: an input that becomes
                # durable without a paid job is the orphan Q85 prevents.
                from platform_core.storage import get_storage

                promotions = invocation.promote_media(
                    db, get_storage(), job=job, sessions=sessions)
            response = _public_job(db, job, tool)
            idempotency.complete(db, record, response=response, job_id=job.id)
            # Commit here rather than leaving it to the request teardown: a
            # commit that failed afterwards would be outside any handler that
            # could put the promoted files back, and object storage does not
            # roll back with the database.
            db.commit()
            metrics.increment(metrics.JOBS_CREATED)
            metrics.increment(metrics.CREDIT_HELD, 0 if testing else cost)
            request.state.api_job_id = job.id
            request.state.api_tool = tool.name
            # The quote still says what this call would cost live, so an
            # integrator sees real pricing; what is recorded as spent is zero,
            # because zero is what moved.
            request.state.api_credit_delta = 0 if testing else -cost
        except credit.ThieuCreditError as exc:
            # 402 would be more evocative but is not in the platform's error
            # vocabulary; 409 with a stable code keeps the contract machine
            # readable, and the balance tells the client what to do next. The
            # hold never happened, so there is nothing promoted to compensate.
            db.rollback()
            raise insufficient_credit(
                "Not enough credit for this call.", required_credit=cost,
                balance=credit.so_du(db, principal.user_id)) from exc
        except Exception:
            db.rollback()
            if promotions:
                from platform_core import upload_sessions
                from platform_core.storage import get_storage

                upload_sessions.compensate(get_storage(), promotions)
            raise

        # 201 rather than 202: the work is asynchronous but a resource really
        # was created and is addressable right now, so the caller gets its
        # address the way any other created resource would give it (EXT-02).
        return JSONResponse(
            response, status_code=201,
            headers={**_NO_STORE,
                     "Location": f"{API_V1_PREFIX}/jobs/{job.id}"})

    @api.get("/jobs", tags=[tag], summary="List this account's jobs",
             description="Owner-scoped, newest first, with optional status filter.")
    def list_jobs(
        status: str = Query(default=""),
        limit: int = Query(default=None),
        offset: int = Query(default=None),
        principal: Principal = Depends(require_scope(SCOPE_JOBS_READ)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        page_request = PageRequest.parse(limit, offset)
        statement = sandbox.restrict_to_mode(
            select(Job).where(Job.user_id == principal.user_id), Job, principal)
        wanted = str(status or "").strip()
        if wanted:
            if wanted not in PUBLIC_STATUSES:
                raise invalid_request(
                    f"status must be one of: {', '.join(sorted(PUBLIC_STATUSES))}.")
            statement = statement.where(Job.status == PUBLIC_STATUSES[wanted])
        rows = db.execute(
            statement.order_by(Job.created_at.desc())
            .offset(page_request.offset).limit(page_request.fetch_limit)
        ).scalars().all()
        page = Page.of([_public_job(db, job, _tool_of(job)) for job in rows],
                       page_request)
        return JSONResponse(page.to_dict(), headers=_NO_STORE)

    @api.get("/jobs/{job_id}", tags=[tag], summary="Read one job",
             description="Owner-scoped. Unknown or foreign ids answer 404.")
    def get_job(
        job_id: str = Path(...),
        principal: Principal = Depends(require_scope(SCOPE_JOBS_READ)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        job = sandbox.ensure_same_mode(
            ensure_owner(db.get(Job, str(job_id)), principal), principal)
        return JSONResponse(_public_job(db, job, _tool_of(job)),
                            headers=_NO_STORE)

    @api.post("/jobs/{job_id}/cancel", tags=[tag], summary="Cancel a job",
              description=("Cancels a queued or running job and refunds the "
                           "held credit. Repeating the call is safe."))
    def cancel_job(
        request: Request,
        job_id: str = Path(...),
        principal: Principal = Depends(require_scope(SCOPE_JOBS_CANCEL)),
        db: Session = Depends(get_db),
    ) -> JSONResponse:
        job = sandbox.ensure_same_mode(
            ensure_owner(db.get(Job, str(job_id)), principal), principal)
        refunded = credit.so_da_giu(db, job.id)
        if jobq.cancel(db, job):
            # Same transaction as the cancel: a refund that commits without the
            # cancellation (or the other way round) is a ledger that disagrees
            # with reality.
            credit.hoan(db, job.user_id, job.id)
            metrics.increment(metrics.JOBS_CANCELLED)
            metrics.increment(metrics.CREDIT_REFUNDED, refunded)
            request.state.api_credit_delta = refunded
        request.state.api_job_id = job.id
        # Already-terminal jobs answer 200 with their current state rather than
        # an error: a client retrying a cancel it already made is not wrong.
        return JSONResponse(_public_job(db, job), headers=_NO_STORE)
