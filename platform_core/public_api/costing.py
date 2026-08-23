"""What a job cost us, separated from what the customer paid.

Two numbers that must never be confused
---------------------------------------

**Revenue** is the credit ledger. It is what the customer was actually charged,
it is auditable, and it is the billing truth. Nothing in this module writes,
adjusts or hides a ledger row — the same separation the budgets in EXT-11 keep.

**Cost** is what serving that job consumed. It is *not* auditable in the same
way, and pretending otherwise would be the most expensive kind of wrong: a
margin dashboard that looks precise gets used to set prices.

So this module records **measured quantities** as evidence, and converts them to
money only through configured rates that are labelled as estimates, every time,
in the data rather than in a footnote.

What the platform can actually measure
--------------------------------------

Honest inventory, because the brief says "cost only from evidence":

* **duration** — ``job_events`` already carries ``duration_ms`` per job. Real
  evidence, measured by the worker that ran the work;
* **artifact bytes** — the size of what was stored. Real evidence;
* **provider tokens** — ``api_keys.total_tokens`` is a running total **per
  credential**, not per job. It cannot be attributed to one call, so this module
  will not pretend it can. A per-job token figure appears here only when a
  handler reports one in its result.

And what it cannot: the money value of a GPU-second, a stored byte or a provider
token. Those are contract prices that live outside the system, entered by an
operator. Every figure derived from them is therefore an **estimate**, and is
stored with ``is_estimate=True`` so no query can accidentally present it as
settled.

The consequence, stated plainly: **margin here is an estimate**, and the admin
page says so. A number that cannot be reconciled must not look like one that
can.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from platform_core.i18n import _ as _t

from platform_core.models import (CREDIT_HOLD, CREDIT_REFUND, CREDIT_SETTLE,
                                  CreditEntry)
from platform_core.public_api.tables import (ApiCostObservation, COST_BYTES,
                                             COST_DURATION_MS, COST_KINDS,
                                             COST_PROVIDER_CALL, COST_TOKENS)

#: Key a handler puts in its result to declare what it bought from a provider.
#:
#: Shape: ``[{"model": "<internal model id>", "count": <n>, "tham_chieu": bool}]``
#:
#: ⭐ **The handler reports this, not the platform** — and that is the whole point.
#: The platform could guess "one image key means one provider call", but a handler
#: that retried once, or fell back to a second model, would make that guess wrong
#: in the direction that *understates* cost. The thing that made the call is the
#: only thing that knows how many calls it made.
KHOA_GOI_PROVIDER = "provider_calls"

#: Micro-units per credit-equivalent, so a rate like "0.0004 per second" is an
#: integer here. Floats in money arithmetic accumulate error nobody can trace.
MICROS = 1_000_000

#: Configured unit costs, in micros per unit. Zero means "not configured", and a
#: zero rate produces no observation at all rather than a confident zero — a
#: cost of exactly nothing is a claim, and this module is not entitled to it.
RATE_ENV = {
    COST_DURATION_MS: "LTT_COST_MICROS_PER_MS",
    COST_BYTES: "LTT_COST_MICROS_PER_BYTE",
    COST_TOKENS: "LTT_COST_MICROS_PER_TOKEN",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def rates(env: dict | None = None) -> dict:
    """Configured unit costs. Absent is absent, not zero."""
    import os

    values = os.environ if env is None else env
    out: dict = {}
    for kind, name in RATE_ENV.items():
        raw = str(values.get(name, "") or "").strip()
        if not raw:
            continue
        try:
            rate = int(raw)
        except (TypeError, ValueError):
            continue
        if rate > 0:
            out[kind] = rate
    return out


def observe(db, *, job_id: str, tool: str, kind: str, quantity: int,
            unit_cost_micros: int = 0, is_estimate: bool = True,
            source: str = "configured_rate",
            now: datetime | None = None) -> ApiCostObservation | None:
    """Record one measured quantity and what it is believed to have cost.

    Returns ``None`` when there is no rate configured for the kind: an
    observation whose money value is unknown is better absent than stored as
    zero, because a zero flows into a margin and reads as "free".
    """
    if kind not in COST_KINDS:
        raise ValueError(f"unknown cost kind: {kind}")
    amount = max(0, int(quantity))
    if amount == 0 or unit_cost_micros <= 0:
        return None
    row = ApiCostObservation(
        id=str(uuid.uuid4()), job_id=str(job_id), tool=str(tool or ""),
        kind=kind, quantity=amount, unit_cost_micros=int(unit_cost_micros),
        cost_micros=amount * int(unit_cost_micros),
        is_estimate=bool(is_estimate), source=str(source)[:32],
        created_at=now or _now())
    db.add(row)
    return row


def record_job(db, job, *, env: dict | None = None,
               now: datetime | None = None) -> list:
    """Turn what a finished job actually measured into cost observations.

    Called from the worker after a job reaches a terminal state. Reads the
    evidence that already exists — it does not instrument anything new, and it
    never guesses a quantity it did not measure.
    """
    from platform_core.public_api.invocation import api_meta

    configured = rates(env)
    tool = api_meta(job).get("tool") or ""
    made: list = []

    # ⭐ KHÔNG bị chặn bởi `configured`. Ba loại dưới cần một suất giá do người vận
    #    hành nhập; loại này thì **giá đã biết** — nó nằm ở `gia_von.json`, tra từ
    #    bảng giá công bố của nhà cung cấp. Bắt nó chờ một biến môi trường là bắt
    #    khoản chi lớn nhất của một job ảnh chờ một thứ nó không cần.
    made.extend(_goi_provider(db, job, tool=tool, now=now))

    if not configured:
        return made

    duration = _duration_ms(db, job)
    if duration and COST_DURATION_MS in configured:
        row = observe(db, job_id=job.id, tool=tool, kind=COST_DURATION_MS,
                      quantity=duration,
                      unit_cost_micros=configured[COST_DURATION_MS],
                      source="evidence:job_events", now=now)
        if row is not None:
            made.append(row)

    tokens = _tokens(job)
    if tokens and COST_TOKENS in configured:
        row = observe(db, job_id=job.id, tool=tool, kind=COST_TOKENS,
                      quantity=tokens,
                      unit_cost_micros=configured[COST_TOKENS],
                      source="evidence:handler", now=now)
        if row is not None:
            made.append(row)
    return made


def _goi_provider(db, job, *, tool: str, now: datetime | None = None) -> list:
    """Cost observations for what this job bought from a provider.

    Reads ``result[KHOA_GOI_PROVIDER]`` — evidence written by the handler that
    made the calls — and prices each entry from ``platform_core.gia_von``.

    ⛔ **Không biết giá thì KHÔNG ghi gì.** `gia_von` ném `KhongBietGiaVon` cho model
    lạ, và bắt được nó ở đây rồi ghi 0 sẽ tạo ra đúng thứ cả module này chống: một
    con số 0 chảy vào biên lợi nhuận và đọc thành *"phục vụ cái này miễn phí"*.
    Vắng mặt là trung thực; số 0 là một lời nói dối có định dạng đẹp.

    ⚠️ `is_estimate=True` dù giá lấy từ bảng giá **công bố**. Bảng giá không phải
    hoá đơn: giảm giá theo lô, bậc dùng, hay tỉ giá đổi đều làm số thật lệch đi.
    `source="gia_von"` để phân biệt với suất giá người vận hành nhập — hai nguồn
    khác nhau thì độ tin khác nhau, và trang admin cần đọc ra điều đó.
    """
    from platform_core import gia_von

    muc = (getattr(job, "result", None) or {}).get(KHOA_GOI_PROVIDER)
    if not isinstance(muc, list):
        return []

    ra: list = []
    for m in muc:
        if not isinstance(m, dict):
            continue
        model_id = str(m.get("model") or "")
        try:
            so = max(0, int(m.get("count", 1)))
        except (TypeError, ValueError):
            continue
        if not model_id or so == 0:
            continue
        try:
            don_gia_mcredit = gia_von.mot_anh(model_id,
                                              tham_chieu=bool(m.get("tham_chieu")))
        except gia_von.KhongBietGiaVon:
            continue                     # xem docstring: vang con hon mot so 0
        # mcredit -> micro-credit: cung don vi MICROS ma bang nay dung.
        don_gia_micros = don_gia_mcredit * (MICROS // gia_von.MCREDIT_MOI_CREDIT)
        row = observe(db, job_id=job.id, tool=tool, kind=COST_PROVIDER_CALL,
                      quantity=so, unit_cost_micros=don_gia_micros,
                      is_estimate=True, source="gia_von", now=now)
        if row is not None:
            ra.append(row)
    return ra


def _duration_ms(db, job) -> int:
    """How long the work took, from the event the worker already writes."""
    from platform_core.models import JobEvent

    rows = db.execute(select(JobEvent.details).where(
        JobEvent.job_id == job.id)).scalars().all()
    for details in reversed(rows):
        if isinstance(details, dict) and details.get("duration_ms"):
            try:
                return int(details["duration_ms"])
            except (TypeError, ValueError):
                continue
    return 0


def _tokens(job) -> int:
    """Provider tokens, only when the handler reported them for this job.

    Never taken from ``api_keys.total_tokens``: that is a running total per
    credential shared by every job it served, and splitting it would be
    invention rather than measurement.
    """
    result = job.result if isinstance(job.result, dict) else {}
    for field in ("tokens", "total_tokens", "usage_tokens"):
        value = result.get(field)
        if isinstance(value, int) and value > 0:
            return value
    return 0


# ── Margin ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Margin:
    """Revenue from the ledger, cost from estimates, and the gap between them."""

    since: datetime
    until: datetime
    revenue_credit: int
    cost_micros: int
    observations: int
    #: Always true today. Kept as a field rather than a comment so a caller has
    #: to handle it, and so it can become false the day real invoices are
    #: reconciled in.
    cost_is_estimate: bool = True

    @property
    def margin_micros(self) -> int:
        return self.revenue_credit * MICROS - self.cost_micros

    @property
    def is_negative(self) -> bool:
        return self.margin_micros < 0


def margin(db, *, since: datetime, until: datetime | None = None,
           tool: str = "") -> Margin:
    """Revenue minus estimated cost for a window.

    Revenue is computed from the ledger, never from the cost table: the two are
    independent by design, and a margin that read both sides from the same place
    would hide exactly the disagreement it exists to reveal.
    """
    end = until or _now()

    held = db.execute(select(func.coalesce(func.sum(CreditEntry.delta), 0))
                      .where(CreditEntry.created_at >= since,
                             CreditEntry.created_at <= end,
                             CreditEntry.kind == CREDIT_HOLD)).scalar_one()
    settled = db.execute(select(func.coalesce(func.sum(CreditEntry.delta), 0))
                         .where(CreditEntry.created_at >= since,
                                CreditEntry.created_at <= end,
                                CreditEntry.kind == CREDIT_SETTLE)).scalar_one()
    refunded = db.execute(select(func.coalesce(func.sum(CreditEntry.delta), 0))
                          .where(CreditEntry.created_at >= since,
                                 CreditEntry.created_at <= end,
                                 CreditEntry.kind == CREDIT_REFUND)).scalar_one()
    revenue = max(0, int(-held) - int(settled) - int(refunded))

    statement = select(func.coalesce(func.sum(ApiCostObservation.cost_micros), 0),
                       func.count()).where(
        ApiCostObservation.created_at >= since,
        ApiCostObservation.created_at <= end)
    if tool:
        statement = statement.where(ApiCostObservation.tool == str(tool))
    cost, count = db.execute(statement).one()

    return Margin(since=since, until=end, revenue_credit=revenue,
                  cost_micros=int(cost), observations=int(count))


def margin_by_tool(db, *, since: datetime,
                   until: datetime | None = None) -> list:
    """Per-tool cost, so an operator can see which one is upside down."""
    end = until or _now()
    rows = db.execute(
        select(ApiCostObservation.tool,
               func.coalesce(func.sum(ApiCostObservation.cost_micros), 0),
               func.count())
        .where(ApiCostObservation.created_at >= since,
               ApiCostObservation.created_at <= end)
        .group_by(ApiCostObservation.tool)).all()
    return sorted(({"tool": str(tool or "—"), "cost_micros": int(cost),
                    "observations": int(count)} for tool, cost, count in rows),
                  key=lambda row: row["cost_micros"], reverse=True)


def _alert_kind() -> str:
    """The kind, from the module that owns the allowlist.

    Not a literal repeated here: `notifications.KINDS` is a closed set, and a
    second copy of the string is the one that eventually disagrees.
    """
    from platform_core.public_api import notifications

    return notifications.MARGIN_NEGATIVE


#: Kept as a module attribute for callers and tests that want to name it.
ALERT_KIND = "margin.negative"


def scan_for_alerts(db, *, hours: int = 24, now: datetime | None = None) -> list:
    """Tell the operators when the estimated margin goes negative.

    Reuses the EXT-11 notification channel rather than adding a second alerting
    path, and dedupes on the same subject so a persistent condition does not
    become a persistent stream.

    Addressed to each **admin account** rather than to a null user: the
    notification table's `user_id` is a foreign key to a real person, and it
    should stay that way — a nullable owner would make every query on that table
    handle a case that exists for one alert.
    """
    from platform_core.models import User
    from platform_core.public_api import notifications

    moment = now or _now()
    window = margin(db, since=moment - timedelta(hours=max(1, int(hours))),
                    until=moment)
    if not window.is_negative or window.observations == 0:
        return []

    shortfall = -window.margin_micros // MICROS
    operators = db.execute(select(User).where(
        User.role == "admin", User.is_active.is_(True))).scalars().all()
    raised = []
    for operator in operators:
        row = notifications.raise_alert(
            db, user_id=operator.id, kind=_alert_kind(),
            subject=f"margin:{hours}h",
            title=_t("Biên lợi nhuận ước tính đang âm"),
            # The wording carries the caveat on purpose: this number is built
            # from configured rates, and an operator reading it in a hurry must
            # not act on it as though it were reconciled.
            body=_t("Trong {hours} giờ gần nhất, chi phí ước tính vượt doanh "
                    "thu khoảng {shortfall} credit. Con số chi phí là ƯỚC "
                    "LƯỢNG, dựng từ đơn giá cấu hình — hãy đối chiếu hoá đơn "
                    "thật trước khi đổi giá.").format(hours=hours,
                                                     shortfall=shortfall),
            now=moment)
        if row is not None:
            raised.append(row)
    return raised


#: Long enough to compare this quarter against the same quarter last year, which
#: is the longest look-back anybody has asked a margin question over. Cost rows
#: are estimates, not books — the ledger keeps the part that must survive.
RETENTION_DAYS = 400


def purge_expired(db, *, days: int = RETENTION_DAYS,
                  now: datetime | None = None) -> int:
    """Drop cost observations past their window. Caller commits."""
    cutoff = (now or _now()) - timedelta(days=max(1, int(days)))
    rows = db.execute(select(ApiCostObservation).where(
        ApiCostObservation.created_at < cutoff)).scalars().all()
    for row in rows:
        db.delete(row)
    return len(rows)


__all__ = [
    "ALERT_KIND", "MICROS", "RETENTION_DAYS", "Margin", "RATE_ENV", "margin", "margin_by_tool",
    "observe", "purge_expired", "rates", "record_job",
    "scan_for_alerts",
]
