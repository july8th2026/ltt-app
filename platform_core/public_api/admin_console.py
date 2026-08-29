"""What an operator needs to know and change about the API platform.

Why this module exists at all
-----------------------------

Everything the developer portal reads is scoped to one account, because that is
what a customer may see. An operator answering "which key is burning credit at
3am" or "is this account's integration broken or is our tool broken" needs the
same facts *across* accounts — and until now the only way to get them was a
database shell, which is both slow and unauditable.

So this module holds the cross-account reads and the two mutations an operator
genuinely needs (disable a key, revoke a key). It is deliberately thin: the
mutations delegate to ``keys.revoke`` / ``keys.set_enabled``, the same functions
the customer's own portal calls. A second implementation of "revoked" would be a
second definition of it, and the two would disagree the first time one changed.

Three rules this module keeps
-----------------------------

**No secret recovery.** Nothing here reads ``verifier_digest``, and there is no
path that reveals a key, a webhook secret or a provider credential. The digest
is one-way by construction; an operator surface that appeared to "look up a key"
would be a lie at best and an exfiltration route at worst.

**Every page is paginated and every query is indexed.** These tables grow with
traffic, not with customers. An operator page that does a full scan is a page
that takes the site down on the day it is most needed.

**Reads here, writes audited by the caller.** This module does not know who is
asking; the admin views do, and they write ``nhat_ky_admin`` in the same
transaction as the change (F-06).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from platform_core.i18n import _ as _t

from platform_core.models import (CreditEntry, Job, User, CREDIT_HOLD,
                                  CREDIT_REFUND, CREDIT_SETTLE, JOB_DONE,
                                  JOB_ERROR)
from platform_core.public_api.tables import (ApiBudget, ApiProject,
                                             ApiRequestLog, DeveloperApiKey,
                                             DEVKEY_ACTIVE, PROJECT_ACTIVE,
                                             WebhookDelivery,
                                             WebhookSubscription,
                                             WEBHOOK_DEAD, WEBHOOK_PENDING)

#: Rows per operator page. Small enough to render fast, large enough that the
#: common question ("what happened in the last hour") fits on one screen.
PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _window(hours: int) -> datetime:
    return _now() - timedelta(hours=max(1, int(hours)))


class Page:
    """One page of rows plus enough to draw the pager.

    ``total`` is counted rather than guessed: an operator deciding whether to
    act needs to know if they are looking at 12 keys or the first 50 of 4,000.
    """

    __slots__ = ("rows", "offset", "limit", "total")

    def __init__(self, rows: list, *, offset: int, limit: int, total: int):
        self.rows = rows
        self.offset = int(offset)
        self.limit = int(limit)
        self.total = int(total)

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.rows) < self.total

    @property
    def next_offset(self) -> int:
        return self.offset + self.limit

    @property
    def prev_offset(self) -> int:
        return max(0, self.offset - self.limit)


def clamp_page(limit, offset) -> tuple[int, int]:
    try:
        size = int(limit or PAGE_SIZE)
    except (TypeError, ValueError):
        size = PAGE_SIZE
    try:
        start = int(offset or 0)
    except (TypeError, ValueError):
        start = 0
    return max(1, min(size, MAX_PAGE_SIZE)), max(0, start)


# ── Overview ─────────────────────────────────────────────────────────────────

def overview(db, *, hours: int = 24) -> dict:
    """The numbers an operator looks at first, for one window.

    Chosen so that each one changes the decision: credentials in circulation,
    whether calls are succeeding, whether money is moving, and whether the
    callbacks customers depend on are being delivered. Anything that would only
    ever be interesting is left out — a dashboard nobody can act on gets
    ignored, and then the one number that mattered gets ignored with it.
    """
    since = _window(hours)

    keys_total = db.execute(select(func.count()).select_from(
        DeveloperApiKey)).scalar_one()
    keys_live = db.execute(select(func.count()).select_from(
        DeveloperApiKey).where(DeveloperApiKey.revoked_at.is_(None),
                               DeveloperApiKey.enabled.is_(True),
                               DeveloperApiKey.mode == "live")).scalar_one()
    keys_test = db.execute(select(func.count()).select_from(
        DeveloperApiKey).where(DeveloperApiKey.revoked_at.is_(None),
                               DeveloperApiKey.enabled.is_(True),
                               DeveloperApiKey.mode == "test")).scalar_one()
    keys_revoked = db.execute(select(func.count()).select_from(
        DeveloperApiKey).where(DeveloperApiKey.revoked_at.is_not(None))
    ).scalar_one()

    projects_active = db.execute(select(func.count()).select_from(
        ApiProject).where(ApiProject.status == PROJECT_ACTIVE)).scalar_one()
    accounts = db.execute(select(func.count(func.distinct(
        DeveloperApiKey.user_id)))).scalar_one()

    requests = db.execute(select(func.count()).select_from(
        ApiRequestLog).where(ApiRequestLog.created_at >= since)).scalar_one()
    failures = db.execute(select(func.count()).select_from(
        ApiRequestLog).where(ApiRequestLog.created_at >= since,
                             ApiRequestLog.status >= 400)).scalar_one()
    # Only failures and non-GET calls are recorded (EXT-09), so this is a
    # failure count over recorded traffic — not over all traffic. Naming it
    # here keeps the number from being read as an overall error rate.
    by_code = db.execute(
        select(ApiRequestLog.code, func.count())
        .where(ApiRequestLog.created_at >= since, ApiRequestLog.status >= 400)
        .group_by(ApiRequestLog.code)
        .order_by(func.count().desc()).limit(8)).all()

    # ⭐ API jobs only. Until 2026-08-29 these two counted **every** job on the
    #    platform, `_api` block or not — so an API dashboard reported a number
    #    that included the web UI's work, and clicking it landed on an API-only
    #    list that was smaller than the figure just clicked.
    #
    #    Same filter `jobs_page()` has used all along; the two now agree.
    from platform_core.public_api.invocation import API_META_KEY

    la_api = Job.params[(API_META_KEY, "tool")].as_string().is_not(None)
    jobs_done = db.execute(select(func.count()).select_from(Job).where(
        Job.created_at >= since, Job.status == JOB_DONE, la_api)).scalar_one()
    jobs_failed = db.execute(select(func.count()).select_from(Job).where(
        Job.created_at >= since, Job.status == JOB_ERROR, la_api)).scalar_one()

    held = db.execute(select(func.coalesce(func.sum(CreditEntry.delta), 0))
                      .where(CreditEntry.created_at >= since,
                             CreditEntry.kind == CREDIT_HOLD)).scalar_one()
    settled = db.execute(select(func.coalesce(func.sum(CreditEntry.delta), 0))
                         .where(CreditEntry.created_at >= since,
                                CreditEntry.kind == CREDIT_SETTLE)).scalar_one()
    refunded = db.execute(select(func.coalesce(func.sum(CreditEntry.delta), 0))
                          .where(CreditEntry.created_at >= since,
                                 CreditEntry.kind == CREDIT_REFUND)).scalar_one()

    webhooks_total = db.execute(select(func.count()).select_from(
        WebhookSubscription)).scalar_one()
    deliveries_pending = db.execute(select(func.count()).select_from(
        WebhookDelivery).where(WebhookDelivery.status == WEBHOOK_PENDING)
    ).scalar_one()
    deliveries_dead = db.execute(select(func.count()).select_from(
        WebhookDelivery).where(WebhookDelivery.status == WEBHOOK_DEAD,
                               WebhookDelivery.created_at >= since)).scalar_one()

    return {
        "hours": int(hours),
        "since": since,
        "accounts_with_keys": int(accounts),
        "keys": {"total": int(keys_total), "live": int(keys_live),
                 "test": int(keys_test), "revoked": int(keys_revoked)},
        "projects_active": int(projects_active),
        "requests_recorded": int(requests),
        "requests_failed": int(failures),
        "failures_by_code": [(str(code or "—"), int(count))
                             for code, count in by_code],
        "jobs": {"succeeded": int(jobs_done), "failed": int(jobs_failed)},
        # Net charged is what customers actually paid in the window: held, less
        # what came back through settlement adjustment and refunds.
        "credit": {"held": int(-held), "settled": int(settled),
                   "refunded": int(refunded),
                   "net_charged": max(0, int(-held) - int(settled)
                                      - int(refunded))},
        "webhooks": {"subscriptions": int(webhooks_total),
                     "pending": int(deliveries_pending),
                     "dead": int(deliveries_dead)},
    }


# ── Accounts and their projects ──────────────────────────────────────────────

def accounts_page(db, *, query: str = "", limit: int = PAGE_SIZE,
                  offset: int = 0, hours: int = 168) -> Page:
    """Accounts that hold at least one developer key, newest credential first.

    Filtered to key holders on purpose: the platform's user table is the whole
    customer base, and an operator on the API console is asking about the ones
    who use the API. The general user list already exists elsewhere.
    """
    size, start = clamp_page(limit, offset)
    since = _window(hours)

    # Labelled `key_count`, not `keys`: `subquery().c.keys` resolves to
    # ``ColumnCollection.keys`` — the method — and SQLAlchemy then refuses it as
    # a SQL expression several frames away from the cause.
    owners = select(DeveloperApiKey.user_id.label("user_id"),
                    func.count().label("key_count"),
                    func.max(DeveloperApiKey.created_at).label("newest"))
    owners = owners.group_by(DeveloperApiKey.user_id).subquery()

    statement = (select(User, owners.c.key_count, owners.c.newest)
                 .join(owners, owners.c.user_id == User.id))
    wanted = str(query or "").strip()
    if wanted:
        statement = statement.where(User.email.ilike(f"%{wanted}%"))

    total = db.execute(select(func.count()).select_from(
        statement.subquery())).scalar_one()
    rows = db.execute(statement.order_by(owners.c.newest.desc())
                      .offset(start).limit(size)).all()

    out = []
    for user, key_count, newest in rows:
        spend = db.execute(
            select(func.coalesce(func.sum(CreditEntry.delta), 0)).where(
                CreditEntry.user_id == user.id,
                CreditEntry.created_at >= since,
                CreditEntry.kind == CREDIT_HOLD)).scalar_one()
        projects = db.execute(select(func.count()).select_from(
            ApiProject).where(ApiProject.user_id == user.id,
                              ApiProject.status == PROJECT_ACTIVE)).scalar_one()
        out.append({
            "user": user, "keys": int(key_count), "newest_key_at": newest,
            "projects": int(projects), "held_in_window": int(-spend),
        })
    return Page(out, offset=start, limit=size, total=int(total))


def account_detail(db, *, user_id: str, hours: int = 168) -> dict | None:
    """Everything about one account's use of the API, on one page.

    The point is to remove the step where an operator copies a UUID between
    four pages and joins them by hand — the same reason the platform already has
    a per-user detail page for credit and jobs (F-04).
    """
    user = db.get(User, str(user_id))
    if user is None:
        return None
    since = _window(hours)

    projects = db.execute(select(ApiProject).where(
        ApiProject.user_id == user.id).order_by(
            ApiProject.created_at.desc())).scalars().all()
    keys = db.execute(select(DeveloperApiKey).where(
        DeveloperApiKey.user_id == user.id).order_by(
            DeveloperApiKey.created_at.desc())).scalars().all()
    budgets = db.execute(select(ApiBudget).where(
        ApiBudget.user_id == user.id)).scalars().all()
    subscriptions = db.execute(select(WebhookSubscription).where(
        WebhookSubscription.user_id == user.id)).scalars().all()

    recent = db.execute(
        select(ApiRequestLog).where(ApiRequestLog.user_id == user.id)
        .order_by(ApiRequestLog.created_at.desc()).limit(20)).scalars().all()
    failures = db.execute(
        select(func.count()).select_from(ApiRequestLog).where(
            ApiRequestLog.user_id == user.id,
            ApiRequestLog.created_at >= since,
            ApiRequestLog.status >= 400)).scalar_one()

    from platform_core import credit

    return {
        "user": user,
        "balance": credit.so_du(db, user.id),
        "projects": list(projects),
        "keys": list(keys),
        "budgets": list(budgets),
        "subscriptions": list(subscriptions),
        "recent_requests": list(recent),
        "failures_in_window": int(failures),
        "hours": int(hours),
    }


# ── Keys ─────────────────────────────────────────────────────────────────────

def keys_page(db, *, query: str = "", status: str = "", mode: str = "",
              user_id: str = "", limit: int = PAGE_SIZE,
              offset: int = 0) -> Page:
    """Every developer credential on the platform, newest first.

    ``status`` filters on the *derived* state (active / disabled / revoked /
    expired) rather than on a column, because that is the word an operator uses
    and the one the customer's own portal shows. Deriving it in two places with
    two meanings is how a "revoked" key ends up looking active on one screen.
    """
    size, start = clamp_page(limit, offset)
    statement = select(DeveloperApiKey, User).join(
        User, User.id == DeveloperApiKey.user_id)

    wanted = str(query or "").strip()
    if wanted:
        statement = statement.where(
            User.email.ilike(f"%{wanted}%") |
            DeveloperApiKey.key_id.ilike(f"%{wanted}%") |
            DeveloperApiKey.name.ilike(f"%{wanted}%"))
    if user_id:
        statement = statement.where(DeveloperApiKey.user_id == str(user_id))
    if mode in ("live", "test"):
        statement = statement.where(DeveloperApiKey.mode == mode)

    now = _now()
    if status == "revoked":
        statement = statement.where(DeveloperApiKey.revoked_at.is_not(None))
    elif status == "disabled":
        statement = statement.where(DeveloperApiKey.revoked_at.is_(None),
                                    DeveloperApiKey.enabled.is_(False))
    elif status == "expired":
        statement = statement.where(DeveloperApiKey.revoked_at.is_(None),
                                    DeveloperApiKey.expires_at.is_not(None),
                                    DeveloperApiKey.expires_at <= now)
    elif status == DEVKEY_ACTIVE:
        statement = statement.where(
            DeveloperApiKey.revoked_at.is_(None),
            DeveloperApiKey.enabled.is_(True),
            (DeveloperApiKey.expires_at.is_(None)
             | (DeveloperApiKey.expires_at > now)))

    total = db.execute(select(func.count()).select_from(
        statement.subquery())).scalar_one()
    rows = db.execute(statement.order_by(DeveloperApiKey.created_at.desc())
                      .offset(start).limit(size)).all()

    projects = {row.id: row for row in db.execute(select(ApiProject)).scalars()}
    out = [{"key": key, "user": user,
            "project": projects.get(str(key.project_id or "")),
            "status": key.status(now=now)}
           for key, user in rows]
    return Page(out, offset=start, limit=size, total=int(total))


def key_by_id(db, key_id: str):
    return db.execute(select(DeveloperApiKey).where(
        DeveloperApiKey.key_id == str(key_id))).scalar_one_or_none()


def key_usage(db, *, key_id: str, hours: int = 168) -> dict:
    """Recent behaviour of one credential — the evidence for acting on it.

    An operator about to revoke a key should be able to see what it has been
    doing without leaving the page, because "revoke the noisy key" and "revoke
    the customer's only working key" look identical from a list.
    """
    since = _window(hours)
    calls = db.execute(select(func.count()).select_from(ApiRequestLog).where(
        ApiRequestLog.key_id == str(key_id),
        ApiRequestLog.created_at >= since)).scalar_one()
    failed = db.execute(select(func.count()).select_from(ApiRequestLog).where(
        ApiRequestLog.key_id == str(key_id),
        ApiRequestLog.created_at >= since,
        ApiRequestLog.status >= 400)).scalar_one()
    spent = db.execute(
        select(func.coalesce(func.sum(ApiRequestLog.credit_delta), 0)).where(
            ApiRequestLog.key_id == str(key_id),
            ApiRequestLog.created_at >= since,
            ApiRequestLog.credit_delta < 0)).scalar_one()
    recent = db.execute(
        select(ApiRequestLog).where(ApiRequestLog.key_id == str(key_id))
        .order_by(ApiRequestLog.created_at.desc()).limit(10)).scalars().all()
    return {"hours": int(hours), "calls": int(calls), "failed": int(failed),
            "credit_spent": int(-spent), "recent": list(recent)}


class AdminActionError(Exception):
    """A refusal an operator should read, not a bug."""


def disable_key(db, key, *, reason: str):
    """Turn a key off. Reversible, and that is exactly why it exists.

    An operator who suspects a leak needs an action that stops the bleeding
    without destroying a customer's integration on a suspicion. Revocation is
    the irreversible one; this is not.
    """
    from platform_core.public_api import keys as devkeys

    _require_reason(reason)
    if key.revoked_at is not None:
        raise AdminActionError(
            _t("Khoá đã thu hồi thì không tắt/bật được nữa."))
    devkeys.set_enabled(db, key, False)
    return key


def enable_key(db, key, *, reason: str):
    from platform_core.public_api import keys as devkeys

    _require_reason(reason)
    if key.revoked_at is not None:
        raise AdminActionError(_t("Khoá đã thu hồi thì không bật lại được."))
    devkeys.set_enabled(db, key, True)
    return key


def revoke_key(db, key, *, reason: str):
    """Kill a credential for good. One way, on purpose.

    Delegates to the same ``keys.revoke`` the customer's portal calls: an
    operator-only definition of "revoked" would be a second definition, and the
    two would drift.
    """
    from platform_core.public_api import keys as devkeys

    _require_reason(reason)
    if key.revoked_at is not None:
        raise AdminActionError(_t("Khoá này đã bị thu hồi rồi."))
    devkeys.revoke(db, key)
    return key


#: Long enough that "spam" does not pass, short enough that it is not an essay.
MIN_REASON = 8


def _require_reason(reason: str) -> None:
    """A destructive operator action must say why, in the operator's own words.

    Not decoration: the audit row is read months later by somebody who was not
    in the room, and "revoked" without a reason is a fact without a meaning.
    """
    if len(str(reason or "").strip()) < MIN_REASON:
        raise AdminActionError(_t(
            "Phải ghi lý do (ít nhất {n} ký tự) cho thao tác này."
        ).format(n=MIN_REASON))


# ── Tools ────────────────────────────────────────────────────────────────────

def tools_page(db, config, *, hours: int = 168) -> list:
    """Published tools with the two things an operator asks about each one.

    Exposure — is it actually reachable, and by what rule — and health, meaning
    what has happened when customers called it. A catalog without health is a
    list of names; health without exposure cannot answer "why can nobody call
    this".
    """
    from platform_core.public_api.catalog import build_catalog
    from platform_core.registry import discover

    since = _window(hours)
    declared = []
    for item in discover():
        if item.error or item.manifest is None:
            continue
        for tool in item.manifest.tools:
            if tool.api_exposed:
                declared.append((item.manifest, tool))

    published = {tool.name: tool for tool in build_catalog(config)}

    counts = dict(db.execute(
        select(ApiRequestLog.tool, func.count())
        .where(ApiRequestLog.created_at >= since, ApiRequestLog.tool != "")
        .group_by(ApiRequestLog.tool)).all())
    failures = dict(db.execute(
        select(ApiRequestLog.tool, func.count())
        .where(ApiRequestLog.created_at >= since, ApiRequestLog.tool != "",
               ApiRequestLog.status >= 400)
        .group_by(ApiRequestLog.tool)).all())

    from platform_core.public_api.catalog import project_tool

    out = []
    for manifest, tool in declared:
        public = project_tool(manifest, tool)
        name = public.name
        live = name in published
        out.append({
            "name": name,
            "app": manifest.slug,
            "execution_mode": public.execution_mode,
            "deprecated": public.deprecated,
            # Declared public by its app, but the deployment's own allowlist
            # decides. Both are shown because "the app says yes and the
            # operator says no" is a normal state, not a fault.
            "declared": True,
            "published": live,
            "calls": int(counts.get(name, 0)),
            "failed": int(failures.get(name, 0)),
        })
    return sorted(out, key=lambda row: row["name"])


def jobs_by_tool(db, *, hours: int = 24) -> list:
    """Terminal job outcomes per tool, from the jobs themselves.

    Separate from the request counts above because they answer different
    questions: a request can succeed while the job it created fails an hour
    later, and a tool that is broken shows up here first.
    """
    since = _window(hours)
    rows = db.execute(
        select(Job.job_type, Job.status, func.count())
        .where(Job.created_at >= since)
        .group_by(Job.job_type, Job.status)).all()
    by_type: dict = {}
    for job_type, status, count in rows:
        bucket = by_type.setdefault(str(job_type), {"done": 0, "error": 0,
                                                    "other": 0})
        if status == JOB_DONE:
            bucket["done"] += int(count)
        elif status == JOB_ERROR:
            bucket["error"] += int(count)
        else:
            bucket["other"] += int(count)
    return sorted(({"job_type": name, **counts}
                   for name, counts in by_type.items()),
                  key=lambda row: row["job_type"])


__all__ = [
    "AdminActionError", "MIN_REASON", "PAGE_SIZE", "Page", "account_detail",
    "accounts_page", "clamp_page", "disable_key", "enable_key", "jobs_by_tool",
    "key_by_id", "key_usage", "keys_page", "overview", "revoke_key",
    "tools_page",
]


# ── Operations: cross-account reads (EXT-16) ──────────────────────────────────
#
# The customer-facing modules answer these questions for one account. An operator
# needs the same facts across all of them, and needs the parts a customer is
# deliberately not shown: the worker, the queue delay, the raw error.

def requests_page(db, *, query: str = "", status: str = "", code: str = "",
                  hours: int = 24, limit: int = PAGE_SIZE,
                  offset: int = 0) -> Page:
    """Recorded requests from every account, newest first.

    Remember what is in this table: failures and non-GET calls only (EXT-09).
    That is a deliberate throughput decision, not an omission, and any count
    taken from here is a count of *recorded* traffic.
    """
    size, start = clamp_page(limit, offset)
    statement = select(ApiRequestLog).where(
        ApiRequestLog.created_at >= _window(hours))

    wanted = str(query or "").strip()
    if wanted:
        statement = statement.where(
            ApiRequestLog.request_id.ilike(f"%{wanted}%")
            | ApiRequestLog.key_id.ilike(f"%{wanted}%")
            | ApiRequestLog.route.ilike(f"%{wanted}%")
            | ApiRequestLog.tool.ilike(f"%{wanted}%"))
    if status == "failed":
        statement = statement.where(ApiRequestLog.status >= 400)
    elif status == "ok":
        statement = statement.where(ApiRequestLog.status < 400)
    if code:
        statement = statement.where(ApiRequestLog.code == str(code))

    total = db.execute(select(func.count()).select_from(
        statement.subquery())).scalar_one()
    rows = db.execute(statement.order_by(ApiRequestLog.created_at.desc())
                      .offset(start).limit(size)).scalars().all()

    emails = _emails_for(db, {row.user_id for row in rows})
    out = [{"row": row, "email": emails.get(row.user_id, "")} for row in rows]
    return Page(out, offset=start, limit=size, total=int(total))


def jobs_page(db, *, status: str = "", tool: str = "", hours: int = 24,
              limit: int = PAGE_SIZE, offset: int = 0) -> Page:
    """API jobs with the three numbers a customer's page never shows.

    Queue delay separates "we were slow" from "the queue was full", which is the
    first fork in almost every latency complaint; the worker id says *which*
    machine; the attempt count says whether it had already failed once.
    """
    size, start = clamp_page(limit, offset)
    from platform_core.public_api.invocation import API_META_KEY

    statement = select(Job).where(Job.created_at >= _window(hours))
    # API jobs only: a job with no `_api` block came from the web UI, and this
    # console is about the API platform.
    statement = statement.where(
        Job.params[(API_META_KEY, "tool")].as_string().is_not(None))
    if status:
        statement = statement.where(Job.status == str(status))
    if tool:
        statement = statement.where(
            Job.params[(API_META_KEY, "tool")].as_string() == str(tool))

    total = db.execute(select(func.count()).select_from(
        statement.subquery())).scalar_one()
    rows = db.execute(statement.order_by(Job.created_at.desc())
                      .offset(start).limit(size)).scalars().all()

    emails = _emails_for(db, {row.user_id for row in rows})
    out = []
    for job in rows:
        out.append({
            "job": job,
            "email": emails.get(job.user_id, ""),
            "tool": _api_tool(job),
            "queue_delay_ms": _delay_ms(job.created_at, job.started_at),
            "run_ms": _delay_ms(job.started_at, job.finished_at),
            "held": credit_held(db, job.id),
        })
    return Page(out, offset=start, limit=size, total=int(total))


def failing_webhooks(db, *, hours: int = 24, limit: int = PAGE_SIZE) -> list:
    """Deliveries that failed or died, across accounts.

    Dead ones first: a `failed` delivery will be retried, a `dead` one will not,
    and only the second is a customer who is silently missing their callbacks.
    """
    from platform_core.public_api.tables import WEBHOOK_FAILED

    rows = db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.created_at >= _window(hours),
               WebhookDelivery.status.in_((WEBHOOK_DEAD, WEBHOOK_FAILED)))
        .order_by(WebhookDelivery.status.desc(),
                  WebhookDelivery.created_at.desc())
        .limit(max(1, min(int(limit), MAX_PAGE_SIZE)))).scalars().all()
    emails = _emails_for(db, {row.user_id for row in rows})
    return [{"row": row, "email": emails.get(row.user_id, "")} for row in rows]


def credit_held(db, job_id: str) -> int:
    from platform_core import credit

    return credit.so_da_giu(db, str(job_id))


def _emails_for(db, user_ids) -> dict:
    """One query for every owner on the page, not one per row."""
    clean = {str(value) for value in user_ids if value}
    if not clean:
        return {}
    rows = db.execute(select(User.id, User.email).where(
        User.id.in_(clean))).all()
    return {str(user_id): str(email) for user_id, email in rows}


def _api_tool(job) -> str:
    from platform_core.public_api.invocation import api_meta

    return str(api_meta(job).get("tool") or "")


def _delay_ms(start, end) -> int | None:
    if not start or not end:
        return None
    start = start if start.tzinfo else start.replace(tzinfo=timezone.utc)
    end = end if end.tzinfo else end.replace(tzinfo=timezone.utc)
    return max(0, int((end - start).total_seconds() * 1000))
