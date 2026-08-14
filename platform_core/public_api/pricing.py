"""What a call costs, which regime said so, and why that can never change later.

The one decision this module is built around
--------------------------------------------

**Price is computed by the app, not by a table here.** Every app declares
``credit_cost(params)`` in its manifest, and ``registry.credit_for()`` is the
only thing that turns a call into a number. A pricing table that *replaced* that
would be a second pricing engine, and the first time the two disagreed there
would be no way to say which one the customer was actually charged by
(COMMON_RULES §3 — no parallel engines).

So a **pricing version** does not price anything. It records *which regime was in
force*, with its window, its bounds and its formula reference, and that label is
stamped onto the quote and onto the job. Reconciling a charge months later then
means reading two facts that were both written at the time, rather than
re-running today's code against yesterday's call and hoping.

Why that makes "no retroactive price mutation" structural
---------------------------------------------------------

A quote is signed (``itsdangerous``) and carries both the credit amount and the
version label. A job carries the same pair in its meta. Neither can be edited
without breaking a signature or rewriting history, and nothing in this module
offers a path to either. Publishing a new version writes a **new row**; it never
touches an old one. Retiring closes a window; it does not reprice what happened
inside it.

That is a stronger guarantee than a rule saying "do not change prices
retroactively", because there is no code that could.

The ledger is still the billing truth
-------------------------------------

Nothing here writes, adjusts or hides a credit entry — same separation the
budgets in EXT-11 keep. A pricing version is a *description* of what was charged;
the ledger is *what was charged*. When they disagree, the ledger is right and
this module has a bug.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from platform_core.i18n import _ as _t
from platform_core.public_api.tables import (ApiPricingVersion, PRICE_ACTIVE,
                                             PRICE_DRAFT, PRICE_RETIRED,
                                             PRICE_SCHEDULED, PRICE_STATUSES)

#: What goes on a quote and a job when no version has ever been published.
#: Deployments that never open the pricing console still get a stable, honest
#: label rather than an empty string that later reads as "lost".
UNVERSIONED = "unversioned"

MIN_REASON = 8

ROUNDING_MODES = ("up", "down", "nearest")


class PricingError(Exception):
    """A refusal an operator should read, not a bug."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value):
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(
        tzinfo=timezone.utc)


# ── Reading the regime in force ──────────────────────────────────────────────

def active_for(db, *, tool: str, model: str = "",
               now: datetime | None = None) -> ApiPricingVersion | None:
    """The version whose window contains ``now``, most specific first.

    A row naming a model beats a row naming only the tool: an operator who
    priced one model differently meant that to win. Among equally specific rows,
    the one that started most recently wins — windows are not supposed to
    overlap, and when they do the later intent is the live one.
    """
    moment = now or _now()
    rows = db.execute(select(ApiPricingVersion).where(
        ApiPricingVersion.tool == str(tool))).scalars().all()

    live = [row for row in rows
            if row.status in (PRICE_ACTIVE, PRICE_SCHEDULED)
            and _aware(row.effective_from) <= moment
            and (row.effective_until is None
                 or _aware(row.effective_until) > moment)]
    if not live:
        return None
    live.sort(key=lambda row: (bool(row.model and row.model == model),
                              _aware(row.effective_from)), reverse=True)
    # A row that names a *different* model must not win over a tool-wide row.
    for row in live:
        if not row.model or row.model == model:
            return row
    return None


def stamp_for(db, *, tool: str, model: str = "",
              now: datetime | None = None) -> str:
    """The label to write onto a quote or a job. Never empty."""
    row = active_for(db, tool=tool, model=model, now=now)
    return row.label if row is not None else UNVERSIONED


def apply_bounds(credit: int, version: ApiPricingVersion | None) -> int:
    """Clamp and round a computed price to what the published regime promised.

    Applied to the number the app computed rather than replacing it: the app
    still decides the price, and the version says what the platform committed to
    publicly. If the two ever disagree, the published bound wins — a customer
    was shown that bound and cannot be charged past it.
    """
    value = int(credit)
    if version is None:
        return value
    step = int(version.rounding or 0)
    if step > 1:
        mode = str(version.rounding_mode or "nearest")
        if mode == "up":
            value = -(-value // step) * step
        elif mode == "down":
            value = (value // step) * step
        else:
            value = int(round(value / step)) * step
    if version.min_credit is not None:
        value = max(int(version.min_credit), value)
    if version.max_credit is not None:
        value = min(int(version.max_credit), value)
    return max(0, value)


# ── Writing: publish, schedule, retire ───────────────────────────────────────

def create_version(db, *, tool: str, label: str, model: str = "",
                   effective_from: datetime | None = None,
                   effective_until: datetime | None = None,
                   min_credit: int | None = None,
                   max_credit: int | None = None,
                   rounding: int | None = None,
                   rounding_mode: str = "nearest",
                   formula_ref: str = "", notes: str = "",
                   created_by: str = "",
                   now: datetime | None = None) -> ApiPricingVersion:
    """Draft a version. Nothing is in force until it is published."""
    clean_tool = str(tool or "").strip()
    clean_label = str(label or "").strip()
    if not clean_tool:
        raise PricingError(_t("Phiên bản giá phải gắn với một công cụ."))
    if not clean_label:
        raise PricingError(_t("Phiên bản giá phải có nhãn."))
    if db.execute(select(ApiPricingVersion).where(
            ApiPricingVersion.tool == clean_tool,
            ApiPricingVersion.label == clean_label)).scalar_one_or_none():
        raise PricingError(_t("Công cụ này đã có phiên bản trùng nhãn."))
    if rounding_mode not in ROUNDING_MODES:
        raise PricingError(_t("Kiểu làm tròn không hợp lệ."))
    if (min_credit is not None and max_credit is not None
            and int(min_credit) > int(max_credit)):
        raise PricingError(_t("Giá sàn không được lớn hơn giá trần."))

    moment = now or _now()
    start = _aware(effective_from) or moment
    end = _aware(effective_until)
    if end is not None and end <= start:
        raise PricingError(_t("Cửa sổ hiệu lực phải kết thúc sau khi bắt đầu."))

    row = ApiPricingVersion(
        id=str(uuid.uuid4()), tool=clean_tool, model=str(model or ""),
        label=clean_label, status=PRICE_DRAFT, effective_from=start,
        effective_until=end,
        min_credit=None if min_credit is None else int(min_credit),
        max_credit=None if max_credit is None else int(max_credit),
        rounding=None if rounding is None else max(0, int(rounding)),
        rounding_mode=rounding_mode,
        # Which code actually computes the number. Recorded rather than copied:
        # the formula lives in the app, and duplicating it here would be the
        # second pricing engine this module exists to avoid.
        formula_ref=str(formula_ref or "")[:200],
        notes=str(notes or "")[:1000], created_by=str(created_by or "")[:255],
        created_at=moment)
    db.add(row)
    db.flush()
    return row


def publish(db, version: ApiPricingVersion, *, published_by: str = "",
            now: datetime | None = None) -> ApiPricingVersion:
    """Put a draft into force — now, or at the start of its window.

    Publishing **closes the window of whatever it replaces** rather than editing
    it. The old row keeps its dates, its bounds and every charge that referenced
    it; what changes is only where the boundary between them falls.
    """
    moment = now or _now()
    if version.status == PRICE_RETIRED:
        raise PricingError(_t("Phiên bản đã ngừng thì không phát hành lại."))

    start = _aware(version.effective_from) or moment
    version.status = PRICE_SCHEDULED if start > moment else PRICE_ACTIVE
    version.published_at = moment
    version.published_by = str(published_by or "")[:255]

    for other in db.execute(select(ApiPricingVersion).where(
            ApiPricingVersion.tool == version.tool,
            ApiPricingVersion.model == version.model,
            ApiPricingVersion.id != version.id)).scalars():
        if other.status not in (PRICE_ACTIVE, PRICE_SCHEDULED):
            continue
        if other.effective_until is None or _aware(other.effective_until) > start:
            other.effective_until = start
            if _aware(other.effective_from) >= start:
                # Fully eclipsed before it ever applied.
                other.status = PRICE_RETIRED
    db.flush()
    return version


def retire(db, version: ApiPricingVersion, *,
           now: datetime | None = None) -> ApiPricingVersion:
    """Stop a version applying from now on. What it already priced stands."""
    moment = now or _now()
    version.status = PRICE_RETIRED
    if version.effective_until is None or _aware(version.effective_until) > moment:
        version.effective_until = moment
    db.flush()
    return version


def list_for(db, *, tool: str = "") -> list:
    statement = select(ApiPricingVersion)
    if tool:
        statement = statement.where(ApiPricingVersion.tool == str(tool))
    return list(db.execute(statement.order_by(
        ApiPricingVersion.tool, ApiPricingVersion.effective_from.desc())
    ).scalars())


def version_by_id(db, version_id: str):
    return db.get(ApiPricingVersion, str(version_id))


@dataclass(frozen=True)
class Timeline:
    """What is charging now, what takes over, and what already stopped."""

    current: ApiPricingVersion | None
    upcoming: list
    history: list


def timeline(db, *, tool: str, model: str = "",
             now: datetime | None = None) -> Timeline:
    moment = now or _now()
    rows = [row for row in list_for(db, tool=tool)
            if not model or not row.model or row.model == model]
    current = active_for(db, tool=tool, model=model, now=moment)
    # A draft belongs in "upcoming" whatever its start date says. It has never
    # been in force, so it cannot be history — and a freshly created draft whose
    # window opens *now* would otherwise land in the past, where the person who
    # just created it would never look for it. Found by making one.
    upcoming = [row for row in rows
                if row.status == PRICE_DRAFT
                or (row.status == PRICE_SCHEDULED
                    and _aware(row.effective_from) > moment)]
    history = [row for row in rows
               if row is not current and row not in upcoming]
    return Timeline(current=current, upcoming=upcoming, history=history)


# ── The simulator ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Simulation:
    """A price, and everything needed to trust it — without a charge."""

    tool: str
    credit: int
    raw_credit: int
    pricing_version: str
    bounded: bool
    detail: str = ""


def simulate(db, *, tool, params: dict, now: datetime | None = None) -> Simulation:
    """Price a hypothetical call with the **production** formula, charge nothing.

    Deliberately the same call the real quote path makes, not a copy of it. A
    simulator with its own arithmetic answers a question nobody asked: what
    matters is what the customer would actually be billed, and that only stays
    true if the same code produces both numbers.

    No quote token is minted and no credit moves, so a simulation cannot be
    presented at ``POST /jobs`` — it is an answer, not a promise.
    """
    from platform_core.public_api import invocation

    raw = invocation.price(tool, dict(params or {}))
    version = active_for(db, tool=tool.name, now=now)
    final = apply_bounds(raw, version)
    return Simulation(
        tool=tool.name, credit=final, raw_credit=int(raw),
        pricing_version=version.label if version is not None else UNVERSIONED,
        bounded=final != int(raw),
        detail=(f"clamped by {version.label}" if final != int(raw) and version
                else ""))


__all__ = [
    "MIN_REASON", "PRICE_ACTIVE", "PRICE_DRAFT", "PRICE_RETIRED",
    "PRICE_SCHEDULED", "PRICE_STATUSES", "PricingError", "ROUNDING_MODES",
    "Simulation", "Timeline", "UNVERSIONED", "active_for", "apply_bounds",
    "create_version", "list_for", "publish", "retire", "simulate", "stamp_for",
    "timeline", "version_by_id",
]
