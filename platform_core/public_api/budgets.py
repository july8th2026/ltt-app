"""Spending limits a customer sets for themselves, and the alerts around them.

Three ideas kept apart on purpose, because merging any two of them is how a
budget feature ends up lying about money:

**The ledger is untouched.** A budget observes spending; it never writes a credit
entry, never adjusts one, never hides one. Everything here reads
``credit_entries`` and stops.

**Soft and hard are different promises.** A soft budget notifies. A hard cap
refuses the call. A customer who asked to be *told* at 80% must not discover
that being told also meant being stopped.

**The account's own limit never overrides the operator's.** If the deployment
caps daily spend and the customer sets a higher budget, the deployment still
wins — a self-service field cannot buy more headroom than the platform sells.
The effective ceiling is the *lower* of the two, always, and the refusal names
which one applied so support is not guesswork.

Scope is user or project. Project-scoped budgets exist because the whole point
of a project (EXT-04) is to be the unit you can revoke and bound separately.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from platform_core.public_api.tables import ApiBudget

PERIOD_DAY = "day"
PERIOD_MONTH = "month"
PERIODS = (PERIOD_DAY, PERIOD_MONTH)

SCOPE_ACCOUNT = "account"
SCOPE_PROJECT = "project"
SCOPES = (SCOPE_ACCOUNT, SCOPE_PROJECT)

#: Where a customer is warned. Bounded rather than free-form: an alert at 3% is
#: noise, and noise is how people learn to ignore the one at 100%.
DEFAULT_THRESHOLDS = (50, 80, 100)
MIN_THRESHOLD = 10
MAX_BUDGETS_PER_USER = 10

#: A budget below this cannot express anything useful — the cheapest tool costs
#: 2 credits — and a budget of 0 would mean "refuse everything", which is what
#: revoking a key is for.
MIN_AMOUNT = 10


class BudgetError(Exception):
    """Refusal a human caused and a human can fix."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def window_start(period: str, *, now: datetime | None = None) -> datetime:
    """When the current period began.

    A *calendar* day and month, not a rolling window: a customer reading
    "monthly budget" means the month, and a rolling 30 days would put their
    reset date somewhere they cannot predict.
    """
    current = now or _now()
    if period == PERIOD_MONTH:
        return current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return current.replace(hour=0, minute=0, second=0, microsecond=0)


def normalize_thresholds(values) -> list:
    cleaned = []
    for value in values or DEFAULT_THRESHOLDS:
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise BudgetError(f"{value!r} is not a percentage.") from exc
        if not MIN_THRESHOLD <= number <= 100:
            raise BudgetError(
                f"Thresholds must be between {MIN_THRESHOLD} and 100.")
        if number not in cleaned:
            cleaned.append(number)
    return sorted(cleaned)


def create(db, *, user_id: str, amount: int, period: str = PERIOD_MONTH,
           scope: str = SCOPE_ACCOUNT, project_id: str = "",
           thresholds=None, hard_cap: bool = False,
           now: datetime | None = None) -> ApiBudget:
    owner = str(user_id or "").strip()
    if not owner:
        raise BudgetError("A budget must belong to an account.")
    if period not in PERIODS:
        raise BudgetError(f"Period must be one of {', '.join(PERIODS)}.")
    if scope not in SCOPES:
        raise BudgetError(f"Scope must be one of {', '.join(SCOPES)}.")
    if scope == SCOPE_PROJECT and not project_id:
        raise BudgetError("A project budget needs a project.")
    try:
        credit = int(amount)
    except (TypeError, ValueError) as exc:
        raise BudgetError("Amount must be a whole number of credits.") from exc
    if credit < MIN_AMOUNT:
        raise BudgetError(f"A budget must be at least {MIN_AMOUNT} credits.")

    existing = list_for(db, user_id=owner)
    if len(existing) >= MAX_BUDGETS_PER_USER:
        raise BudgetError(
            f"This account already has {MAX_BUDGETS_PER_USER} budgets.")
    for row in existing:
        if row.period == period and row.scope == scope and \
                str(row.project_id or "") == str(project_id or ""):
            raise BudgetError("A budget for that scope and period exists.")

    budget = ApiBudget(
        id=str(uuid.uuid4()), user_id=owner, scope=scope,
        project_id=str(project_id or ""), period=period, amount=credit,
        thresholds=normalize_thresholds(thresholds), hard_cap=bool(hard_cap),
        created_at=now or _now())
    db.add(budget)
    return budget


def list_for(db, *, user_id: str) -> list:
    return list(db.execute(select(ApiBudget).where(
        ApiBudget.user_id == str(user_id or "")).order_by(
            ApiBudget.created_at)).scalars().all())


def get_owned(db, *, user_id: str, budget_id: str):
    return db.execute(select(ApiBudget).where(
        ApiBudget.id == str(budget_id or ""),
        ApiBudget.user_id == str(user_id or ""))).scalar_one_or_none()


def api_spend_since(db, *, user_id: str, since: datetime,
                    project_id: str = "") -> int:
    """Credit committed **through the API** in a window.

    Holds minus what came back, counting only jobs the API created. Counting
    every credit entry — which is what the daily ceiling did before EXT-11 —
    meant a customer using the web app could exhaust their own integration's
    allowance, which is the opposite of what a limit on an API key is for
    (decision D3).
    """
    from platform_core.models import (CREDIT_HOLD, CREDIT_REFUND, CREDIT_SETTLE,
                                      CreditEntry, Job)
    from platform_core.public_api.invocation import API_META_KEY

    rows = db.execute(
        select(CreditEntry.delta, Job.params)
        .join(Job, Job.id == CreditEntry.job_id)
        .where(CreditEntry.user_id == str(user_id or ""),
               CreditEntry.created_at >= since,
               CreditEntry.kind.in_((CREDIT_HOLD, CREDIT_SETTLE,
                                     CREDIT_REFUND)))).all()
    total = 0
    for delta, params in rows:
        meta = (params or {}).get(API_META_KEY)
        if not isinstance(meta, dict):
            continue                      # made in the UI, not through the API
        if project_id and str(meta.get("project_id") or "") != str(project_id):
            continue
        total += int(delta or 0)
    return max(0, -total)


def status(db, budget, *, now: datetime | None = None) -> dict:
    """Where this budget stands right now."""
    current = now or _now()
    start = window_start(budget.period, now=current)
    spent = api_spend_since(db, user_id=budget.user_id, since=start,
                            project_id=budget.project_id or "")
    amount = max(1, int(budget.amount))
    percent = int(spent * 100 / amount)
    return {"budget": budget, "spent": spent, "amount": int(budget.amount),
            "percent": percent, "remaining": max(0, int(budget.amount) - spent),
            "window_start": start,
            "crossed": [value for value in (budget.thresholds or ())
                        if percent >= int(value)]}


def effective_cap(db, *, user_id: str, project_id: str = "",
                  operator_daily: int = 0, now: datetime | None = None) -> dict:
    """The ceiling that actually applies, and which rule set it.

    The lower of the operator's daily allowance and any hard-capped budget of
    the customer's own. Returned rather than enforced here so the caller can
    name the reason in its refusal.
    """
    current = now or _now()
    found = {"limit": 0, "spent": 0, "source": "", "period": ""}

    if operator_daily and operator_daily > 0:
        spent = api_spend_since(db, user_id=user_id,
                                since=window_start(PERIOD_DAY, now=current))
        found = {"limit": int(operator_daily), "spent": spent,
                 "source": "operator", "period": PERIOD_DAY}

    for budget in list_for(db, user_id=user_id):
        if not budget.hard_cap:
            continue
        if budget.scope == SCOPE_PROJECT and \
                str(budget.project_id or "") != str(project_id or ""):
            continue
        state = status(db, budget, now=current)
        remaining_here = state["amount"] - state["spent"]
        remaining_found = (found["limit"] - found["spent"]) if found["limit"] \
            else None
        if remaining_found is None or remaining_here < remaining_found:
            found = {"limit": state["amount"], "spent": state["spent"],
                     "source": "budget", "period": budget.period}
    return found
